import { CalendarDays, Dices, Search, Trophy, X } from "lucide-react";
import { useMemo, useState, type CSSProperties } from "react";
import { Link } from "react-router";
import { useLeaderboard } from "../../api/leaderboard";
import type { LeaderboardEntry, QuizDifficulty } from "../../api/types";
import { courseColor } from "../../lib/courseColor";
import { Button } from "../../components/ui/Button";
import { EmptyState } from "../../components/ui/EmptyState";
import { ErrorState } from "../../components/ui/ErrorState";
import { SegmentedControl } from "../../components/ui/SegmentedControl";
import { Achievements } from "./Achievements";
import { ActivityCalendar } from "./ActivityCalendar";
import { ChallengePicker } from "./ChallengePicker";
import "./leaderboard.css";
import { PlayerCard } from "./PlayerCard";
import { Podium } from "./Podium";
import { RankedList } from "./RankedList";
import {
  achievements,
  attemptsByDay,
  dayKey,
  levelFor,
  quizStats,
  rankMovement,
  ranked,
  streaks,
  totalXp,
  type SortKey,
} from "./stats";

type DifficultyFilter = "all" | QuizDifficulty;

const DIFFICULTY_OPTIONS: { value: DifficultyFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "easy", label: "Easy" },
  { value: "medium", label: "Medium" },
  { value: "hard", label: "Hard" },
];

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "points", label: "Points" },
  { value: "best", label: "Best score" },
  { value: "improved", label: "Most improved" },
  { value: "played", label: "Most played" },
  { value: "recent", label: "Recent" },
];

const dayLabel = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" });

/** The quiz leaderboard across all courses. The filter row scopes everything below it. */
export function LeaderboardPage() {
  const board = useLeaderboard();
  const [courseFilter, setCourseFilter] = useState<number | null>(null);
  const [difficulty, setDifficulty] = useState<DifficultyFilter>("all");
  const [search, setSearch] = useState("");
  const [day, setDay] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>("points");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [challengeOpen, setChallengeOpen] = useState(false);

  const entries = useMemo(() => board.data ?? [], [board.data]);

  // All-time profile.
  const profile = useMemo(() => {
    const allAttempts = entries.flatMap((entry) => entry.attempts);
    const days = attemptsByDay(entries);
    const streak = streaks(days);
    const xp = totalXp(entries);
    return {
      xp,
      level: levelFor(xp),
      streak,
      attempts: allAttempts.length,
      average: allAttempts.length
        ? allAttempts.reduce((sum, a) => sum + a.score, 0) / allAttempts.length
        : null,
      personalBest: allAttempts.length ? Math.max(...allAttempts.map((a) => a.score)) : null,
      achievements: achievements(entries, streak.longest),
    };
  }, [entries]);

  const courses = useMemo(() => {
    const seen = new Map<number, string>();
    for (const entry of entries) seen.set(entry.course_id, entry.course_name);
    return [...seen].map(([id, name]) => ({ id, name }));
  }, [entries]);

  // Course, difficulty and search scope everything below the filter row.
  const scoped = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return entries.filter(
      (entry) =>
        (courseFilter === null || entry.course_id === courseFilter) &&
        (difficulty === "all" || entry.difficulty === difficulty) &&
        (!needle ||
          entry.title.toLowerCase().includes(needle) ||
          entry.course_name.toLowerCase().includes(needle)),
    );
  }, [entries, courseFilter, difficulty, search]);

  const stats = useMemo(() => scoped.map((entry) => quizStats(entry)), [scoped]);
  const byPoints = useMemo(() => ranked(stats, "points"), [stats]);
  const movement = useMemo(() => rankMovement(stats), [stats]);
  const dayCounts = useMemo(() => attemptsByDay(scoped), [scoped]);
  // The day filter narrows only the list: the calendar keeps showing every day to pick from.
  const rows = useMemo(() => {
    const list = ranked(stats, sort);
    if (!day) return list;
    return list.filter((s) => s.attempts.some((a) => dayKey(new Date(a.attempted_at)) === day));
  }, [stats, sort, day]);
  const unranked = useMemo(() => stats.filter((s) => s.attempts.length === 0), [stats]);
  const challengePool = useMemo(
    () => stats.filter((s) => s.entry.course_status === "active"),
    [stats],
  );

  if (board.error) {
    return <ErrorState message={board.error.message} onRetry={() => void board.refetch()} />;
  }
  if (board.isPending) return <LeaderboardSkeleton />;
  if (entries.length === 0) {
    return (
      <EmptyState
        icon={<Trophy size={30} />}
        tone="amber"
        title="No quizzes to rank yet"
        description="Ask the assistant for a quiz in any course's Chat tab. Each quiz you take lands here, ranked by your best score."
        actions={
          <Link to="/courses" className="btn btn-primary">
            Go to My Library
          </Link>
        }
      />
    );
  }

  function selectFromPodium(quizId: number) {
    setSort("points");
    setDay(null);
    setExpandedId(quizId);
    // After the row has rendered open.
    requestAnimationFrame(() =>
      document
        .getElementById(`quiz-row-${quizId}`)
        ?.scrollIntoView({ behavior: "smooth", block: "center" }),
    );
  }

  const filtered = courseFilter !== null || difficulty !== "all" || search.trim() !== "" || day;

  return (
    <div className="page leaderboard">
      <header className="page-header">
        <div>
          <h1 className="page-title">Leaderboard</h1>
          <p className="text-muted">
            Your quizzes, ranked. Climb by beating your own best scores.
          </p>
        </div>
        <div className="page-header-actions">
          <Button variant="primary" onClick={() => setChallengeOpen(true)}>
            <Dices size={16} />
            Pick my next challenge
          </Button>
        </div>
      </header>

      <div className="lb-profile">
        <PlayerCard
          level={profile.level}
          xp={profile.xp}
          attempts={profile.attempts}
          average={profile.average}
          personalBest={profile.personalBest}
          streak={profile.streak}
        />
        <Achievements list={profile.achievements} />
      </div>

      <div className="lb-filters" role="group" aria-label="Filter the leaderboard">
        <div className="lb-course-chips">
          <button
            type="button"
            className="chip-filter"
            aria-pressed={courseFilter === null}
            onClick={() => setCourseFilter(null)}
          >
            All courses
          </button>
          {courses.map((course) => (
            <button
              key={course.id}
              type="button"
              className="chip-filter"
              aria-pressed={courseFilter === course.id}
              onClick={() => setCourseFilter(courseFilter === course.id ? null : course.id)}
              style={{ "--course-color": courseColor(course.id) } as CSSProperties}
            >
              <span className="course-dot" aria-hidden="true" />
              {course.name}
            </button>
          ))}
        </div>
        <SegmentedControl
          label="Difficulty"
          value={difficulty}
          options={DIFFICULTY_OPTIONS}
          onChange={setDifficulty}
        />
        <label className="lb-search">
          <Search size={16} aria-hidden="true" />
          <span className="visually-hidden">Search quizzes</span>
          <input
            type="search"
            value={search}
            placeholder="Search quizzes"
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        {day && (
          <button type="button" className="chip-filter lb-day-chip" onClick={() => setDay(null)}>
            <CalendarDays size={14} aria-hidden="true" />
            {dayLabel.format(parseDay(day))}
            <X size={14} aria-label="Clear day filter" />
          </button>
        )}
      </div>

      <div className="lb-overview">
        <Podium top={byPoints.slice(0, 3)} onSelect={selectFromPodium} />
        <ActivityCalendar counts={dayCounts} selectedDay={day} onSelectDay={setDay} />
      </div>

      <section className="lb-rankings" aria-labelledby="rankings-heading">
        <div className="lb-rankings-header">
          <div>
            <h2 id="rankings-heading" className="lb-section-title">
              Rankings
            </h2>
            <p className="text-subtle">
              {rows.length} ranked {rows.length === 1 ? "quiz" : "quizzes"}
              {filtered ? " matching your filters" : ""} · points = best score × difficulty (Easy
              ×1, Medium ×1.25, Hard ×1.5)
            </p>
          </div>
          <SegmentedControl label="Sort by" value={sort} options={SORT_OPTIONS} onChange={setSort} />
        </div>
        {rows.length === 0 ? (
          <p className="lb-no-results">
            {day
              ? "No quizzes taken on that day match your filters."
              : "No attempted quizzes match your filters yet."}
          </p>
        ) : (
          <RankedList
            rows={rows}
            sort={sort}
            movement={movement}
            expandedId={expandedId}
            onToggle={(quizId) => setExpandedId(expandedId === quizId ? null : quizId)}
          />
        )}
      </section>

      {unranked.length > 0 && !day && (
        <section className="lb-unranked" aria-labelledby="unranked-heading">
          <h2 id="unranked-heading" className="lb-section-title">
            Waiting for their first attempt
          </h2>
          <ul className="unranked-grid">
            {unranked.map(({ entry }) => (
              <UnrankedCard key={entry.quiz_id} entry={entry} />
            ))}
          </ul>
        </section>
      )}

      <ChallengePicker
        open={challengeOpen}
        onClose={() => setChallengeOpen(false)}
        pool={challengePool}
      />
    </div>
  );
}

function UnrankedCard({ entry }: { entry: LeaderboardEntry }) {
  return (
    <li
      className="unranked-card"
      style={{ "--course-color": courseColor(entry.course_id) } as CSSProperties}
    >
      <div className="unranked-text">
        <p className="unranked-title">{entry.title}</p>
        <p className="unranked-meta">
          <span className="course-dot" aria-hidden="true" />
          <span className="truncate">{entry.course_name}</span>
          <span className={`difficulty difficulty-${entry.difficulty}`}>
            {entry.difficulty.charAt(0).toUpperCase() + entry.difficulty.slice(1)}
          </span>
        </p>
      </div>
      <Link
        to={`/courses/${entry.course_id}/study-tools/quiz/${entry.quiz_id}`}
        className="btn btn-sm btn-secondary"
      >
        Take it
      </Link>
    </li>
  );
}

function parseDay(key: string): Date {
  const [year, month, date] = key.split("-").map(Number);
  return new Date(year, month - 1, date);
}

function LeaderboardSkeleton() {
  return (
    <div className="page leaderboard" aria-busy="true" aria-label="Loading leaderboard">
      <div className="skeleton" style={{ height: 44, width: 260 }} />
      <div className="lb-profile">
        <div className="skeleton" style={{ height: 220 }} />
        <div className="skeleton" style={{ height: 220 }} />
      </div>
      <div className="skeleton" style={{ height: 280 }} />
    </div>
  );
}
