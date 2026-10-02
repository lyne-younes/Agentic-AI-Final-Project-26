import { Flame } from "lucide-react";
import { useAuth } from "../../auth/AuthContext";
import { initials } from "../../lib/format";
import { formatScore, type Level, type Streaks } from "./stats";

interface PlayerCardProps {
  level: Level;
  xp: number;
  attempts: number;
  average: number | null;
  personalBest: number | null;
  streak: Streaks;
}

/** The student's all-time profile: level and XP up front, then the numbers behind it. */
export function PlayerCard({ level, xp, attempts, average, personalBest, streak }: PlayerCardProps) {
  const { user } = useAuth();
  const progress = level.xpForNext ? level.xpIntoLevel / level.xpForNext : 0;

  return (
    <section className="lb-card player-card" aria-label="Your profile">
      <div className="player-identity">
        <span className="player-avatar" aria-hidden="true">
          {initials(user?.name)}
          <span className="player-level-badge">{level.level}</span>
        </span>
        <div className="player-level">
          <p className="player-level-value">Level {level.level}</p>
          <p className="player-level-title">{level.title}</p>
        </div>
      </div>

      <div className="player-xp">
        <div className="player-xp-labels">
          <span>{xp.toLocaleString()} XP</span>
          <span className="text-subtle">
            {(level.xpForNext - level.xpIntoLevel).toLocaleString()} XP to level {level.level + 1}
          </span>
        </div>
        <div
          className="meter"
          role="progressbar"
          aria-label={`Progress to level ${level.level + 1}`}
          aria-valuemin={0}
          aria-valuemax={level.xpForNext}
          aria-valuenow={level.xpIntoLevel}
        >
          <span className="meter-fill" style={{ width: `${Math.max(progress * 100, 2)}%` }} />
        </div>
        <p className="player-xp-hint">
          Every attempt earns its score in XP, ×1.25 on medium and ×1.5 on hard.
        </p>
      </div>

      <dl className="player-stats">
        <div className="stat-tile">
          <dt>Attempts</dt>
          <dd>{attempts}</dd>
        </div>
        <div className="stat-tile">
          <dt>Average score</dt>
          <dd>{average === null ? "–" : formatScore(average)}</dd>
        </div>
        <div className="stat-tile">
          <dt>Personal best</dt>
          <dd>{personalBest === null ? "–" : formatScore(personalBest)}</dd>
        </div>
        <div className={`stat-tile streak-tile${streak.current > 0 ? " streak-live" : ""}`}>
          <dt>Day streak</dt>
          <dd>
            <Flame size={18} aria-hidden="true" className="streak-flame" />
            {streak.current}
          </dd>
          <p className="stat-sub">
            {streak.current > 0 && !streak.activeToday
              ? "Quiz today to keep it going"
              : `Longest: ${streak.longest} ${streak.longest === 1 ? "day" : "days"}`}
          </p>
        </div>
      </dl>
    </section>
  );
}
