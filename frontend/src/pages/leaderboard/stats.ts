/** Leaderboard stats derived from the raw attempts (client-side, for local calendar days). */
import type { LeaderboardEntry, QuizAttempt, QuizDifficulty } from "../../api/types";

/** Harder quizzes are worth more: points = best score × multiplier. */
export const DIFFICULTY_MULTIPLIER: Record<QuizDifficulty, number> = {
  easy: 1,
  medium: 1.25,
  hard: 1.5,
};

export interface QuizStats {
  entry: LeaderboardEntry;
  attempts: QuizAttempt[]; // oldest first
  best: number | null;
  latest: number | null;
  first: number | null;
  points: number; // 0 when never attempted
  improvement: number; // best - first; 0 with fewer than two attempts
  lastAttemptAt: string | null;
}

export function quizStats(entry: LeaderboardEntry, attempts = entry.attempts): QuizStats {
  const scores = attempts.map((attempt) => attempt.score);
  const best = scores.length ? Math.max(...scores) : null;
  return {
    entry,
    attempts,
    best,
    latest: scores.at(-1) ?? null,
    first: scores[0] ?? null,
    points: best === null ? 0 : Math.round(best * DIFFICULTY_MULTIPLIER[entry.difficulty]),
    improvement: scores.length > 1 ? Math.max(0, (best ?? 0) - scores[0]) : 0,
    lastAttemptAt: attempts.at(-1)?.attempted_at ?? null,
  };
}

export type SortKey = "points" | "best" | "improved" | "played" | "recent";

const SORTERS: Record<SortKey, (a: QuizStats, b: QuizStats) => number> = {
  points: (a, b) => b.points - a.points || (b.best ?? 0) - (a.best ?? 0),
  best: (a, b) => (b.best ?? 0) - (a.best ?? 0) || b.points - a.points,
  improved: (a, b) => b.improvement - a.improvement || b.points - a.points,
  played: (a, b) => b.attempts.length - a.attempts.length || b.points - a.points,
  recent: (a, b) => (b.lastAttemptAt ?? "").localeCompare(a.lastAttemptAt ?? ""),
};

/** Attempted quizzes, best first by `sort`. Ties keep a stable order (quiz id). */
export function ranked(stats: QuizStats[], sort: SortKey): QuizStats[] {
  return stats
    .filter((s) => s.attempts.length > 0)
    .sort((a, b) => SORTERS[sort](a, b) || a.entry.quiz_id - b.entry.quiz_id);
}

/** How each quiz's rank moved with the latest attempt (positive = climbed, or "new"). */
export function rankMovement(stats: QuizStats[]): Map<number, number | "new"> {
  const moves = new Map<number, number | "new">();
  let latest: { quizId: number; at: string; id: number } | null = null;
  for (const s of stats) {
    const last = s.attempts.at(-1);
    if (!last) continue;
    if (
      !latest ||
      last.attempted_at > latest.at ||
      (last.attempted_at === latest.at && last.id > latest.id)
    ) {
      latest = { quizId: s.entry.quiz_id, at: last.attempted_at, id: last.id };
    }
  }
  if (!latest) return moves;

  const before = stats.map((s) =>
    s.entry.quiz_id === latest.quizId ? quizStats(s.entry, s.attempts.slice(0, -1)) : s,
  );
  const rankBefore = positions(ranked(before, "points"));
  const rankNow = positions(ranked(stats, "points"));
  for (const [quizId, now] of rankNow) {
    const then = rankBefore.get(quizId);
    if (then === undefined) moves.set(quizId, "new");
    else if (then !== now) moves.set(quizId, then - now);
  }
  return moves;
}

function positions(list: QuizStats[]): Map<number, number> {
  return new Map(list.map((s, index) => [s.entry.quiz_id, index + 1]));
}

// ---------- Levels ----------

const LEVEL_TITLES = ["Novice", "Apprentice", "Learner", "Scholar", "Expert", "Master", "Legend"];

/** Every attempt earns XP (score × multiplier), so retakes count too. */
export function totalXp(entries: LeaderboardEntry[]): number {
  return Math.round(
    entries.reduce(
      (sum, entry) =>
        sum +
        entry.attempts.reduce((s, a) => s + a.score * DIFFICULTY_MULTIPLIER[entry.difficulty], 0),
      0,
    ),
  );
}

/** XP needed to reach `level`: 0, 100, 300, 600, 1000, ... (each level asks 100 more). */
function xpForLevel(level: number): number {
  return 50 * (level - 1) * level;
}

export interface Level {
  level: number;
  title: string;
  xpIntoLevel: number;
  xpForNext: number; // size of this level's band
}

export function levelFor(xp: number): Level {
  let level = 1;
  while (xpForLevel(level + 1) <= xp) level += 1;
  const floor = xpForLevel(level);
  return {
    level,
    title: LEVEL_TITLES[Math.min(level, LEVEL_TITLES.length) - 1],
    xpIntoLevel: xp - floor,
    xpForNext: xpForLevel(level + 1) - floor,
  };
}

// ---------- Days, streaks & the activity calendar ----------

/** Local calendar day, e.g. "2026-09-24". */
export function dayKey(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${date.getFullYear()}-${month}-${day}`;
}

export function attemptsByDay(entries: LeaderboardEntry[]): Map<string, number> {
  const counts = new Map<string, number>();
  for (const entry of entries) {
    for (const attempt of entry.attempts) {
      const key = dayKey(new Date(attempt.attempted_at));
      counts.set(key, (counts.get(key) ?? 0) + 1);
    }
  }
  return counts;
}

function addDays(date: Date, days: number): Date {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

export interface Streaks {
  current: number; // alive if it reaches today or yesterday
  longest: number;
  activeToday: boolean;
}

export function streaks(days: Map<string, number>, today = new Date()): Streaks {
  const activeToday = days.has(dayKey(today));
  let current = 0;
  for (let cursor = activeToday ? today : addDays(today, -1); days.has(dayKey(cursor)); ) {
    current += 1;
    cursor = addDays(cursor, -1);
  }

  let longest = 0;
  for (const key of days.keys()) {
    const [y, m, d] = key.split("-").map(Number);
    const start = new Date(y, m - 1, d);
    if (days.has(dayKey(addDays(start, -1)))) continue; // not the start of a run
    let length = 0;
    while (days.has(dayKey(addDays(start, length)))) length += 1;
    longest = Math.max(longest, length);
  }
  return { current, longest, activeToday };
}

/** The last `weeks` weeks as columns of 7 days (Monday first), the last column holding today. */
export function calendarWeeks(weeks: number, today = new Date()): (Date | null)[][] {
  const mondayOffset = (today.getDay() + 6) % 7;
  const start = addDays(today, -mondayOffset - (weeks - 1) * 7);
  const columns: (Date | null)[][] = [];
  for (let w = 0; w < weeks; w += 1) {
    const column: (Date | null)[] = [];
    for (let d = 0; d < 7; d += 1) {
      const date = addDays(start, w * 7 + d);
      column.push(date > today ? null : date);
    }
    columns.push(column);
  }
  return columns;
}

/** 0-4 intensity step for a day's attempt count. */
export function activityLevel(count: number): 0 | 1 | 2 | 3 | 4 {
  if (count <= 0) return 0;
  if (count === 1) return 1;
  if (count === 2) return 2;
  if (count <= 4) return 3;
  return 4;
}

// ---------- Achievements ----------

export type AchievementId =
  | "first-steps"
  | "perfectionist"
  | "hard-mode"
  | "comeback"
  | "marathon"
  | "on-fire"
  | "polymath"
  | "sharpshooter";

export interface Achievement {
  id: AchievementId;
  title: string;
  description: string;
  current: number;
  target: number;
  unlocked: boolean;
}

export function achievements(entries: LeaderboardEntry[], longestStreak: number): Achievement[] {
  const stats = entries.map((entry) => quizStats(entry));
  const all = entries.flatMap((entry) => entry.attempts);
  const bestOverall = Math.max(0, ...stats.map((s) => s.best ?? 0));
  const bestHard = Math.max(
    0,
    ...stats.filter((s) => s.entry.difficulty === "hard").map((s) => s.best ?? 0),
  );
  const courses = new Set(stats.filter((s) => s.attempts.length).map((s) => s.entry.course_id));

  const list: Omit<Achievement, "unlocked">[] = [
    {
      id: "first-steps",
      title: "First steps",
      description: "Finish your first quiz",
      current: all.length,
      target: 1,
    },
    {
      id: "perfectionist",
      title: "Perfectionist",
      description: "Score 100% on any quiz",
      current: bestOverall,
      target: 100,
    },
    {
      id: "hard-mode",
      title: "Hard mode hero",
      description: "Score 80% or more on a hard quiz",
      current: bestHard,
      target: 80,
    },
    {
      id: "comeback",
      title: "Comeback kid",
      description: "Improve a quiz's score by 30 points",
      current: Math.max(0, ...stats.map((s) => s.improvement)),
      target: 30,
    },
    {
      id: "marathon",
      title: "Marathon",
      description: "Complete 10 quiz attempts",
      current: all.length,
      target: 10,
    },
    {
      id: "on-fire",
      title: "On fire",
      description: "Take a quiz 3 days in a row",
      current: longestStreak,
      target: 3,
    },
    {
      id: "polymath",
      title: "Polymath",
      description: "Take quizzes in 3 different courses",
      current: courses.size,
      target: 3,
    },
    {
      id: "sharpshooter",
      title: "Sharpshooter",
      description: "Score 80% or more five times",
      current: all.filter((attempt) => attempt.score >= 80).length,
      target: 5,
    },
  ];
  return list.map((a) => ({
    ...a,
    current: Math.min(a.current, a.target),
    unlocked: a.current >= a.target,
  }));
}

// ---------- The challenge picker ----------

export interface Challenge {
  stats: QuizStats;
  reason: string;
}

/** A weighted random pick that favours untried quizzes and weak scores. */
export function pickChallenge(stats: QuizStats[], random = Math.random): Challenge | null {
  if (stats.length === 0) return null;
  const weights = stats.map((s) => (s.best === null ? 120 : 110 - s.best));
  let roll = random() * weights.reduce((sum, w) => sum + w, 0);
  let index = 0;
  while (roll >= weights[index] && index < stats.length - 1) {
    roll -= weights[index];
    index += 1;
  }
  const chosen = stats[index];
  let reason: string;
  if (chosen.best === null) reason = "You haven't tried this one yet.";
  else if (chosen.best === 100) reason = "You've aced it before. Prove it wasn't luck.";
  else reason = `Your best is ${formatScore(chosen.best)}. Time to beat it.`;
  return { stats: chosen, reason };
}

export function formatScore(score: number): string {
  return `${Math.round(score)}%`;
}
