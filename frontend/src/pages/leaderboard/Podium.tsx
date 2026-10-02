import { Trophy } from "lucide-react";
import type { CSSProperties } from "react";
import { courseColor } from "../../lib/courseColor";
import { formatScore, type QuizStats } from "./stats";

const PLACES = ["1st", "2nd", "3rd"];
const MEDALS = ["gold", "silver", "bronze"];
// Classic podium order: 2nd, 1st, 3rd.
const DISPLAY_ORDER = [1, 0, 2];

interface PodiumProps {
  top: QuizStats[]; // up to three, best first
  onSelect: (quizId: number) => void;
}

/** The top three by points. Steps have fixed heights, like a real podium; the points are text. */
export function Podium({ top, onSelect }: PodiumProps) {
  return (
    <section className="lb-card podium-card" aria-labelledby="podium-heading">
      <div className="lb-card-header">
        <h2 id="podium-heading" className="lb-section-title">
          Hall of fame
        </h2>
        <span className="text-subtle">Top 3 by points</span>
      </div>
      {top.length === 0 ? (
        <div className="podium-empty">
          <Trophy size={28} aria-hidden="true" />
          <p>Take a quiz to claim the top spot.</p>
        </div>
      ) : (
        <ol className="podium">
          {DISPLAY_ORDER.map((place) => {
            const stats = top[place];
            if (!stats) return <li key={place} className="podium-slot podium-slot-empty" />;
            const style = { "--course-color": courseColor(stats.entry.course_id) } as CSSProperties;
            return (
              <li
                key={stats.entry.quiz_id}
                className={`podium-slot podium-${MEDALS[place]}`}
                style={{ ...style, order: DISPLAY_ORDER.indexOf(place) }}
              >
                <button
                  type="button"
                  className="podium-entry"
                  onClick={() => onSelect(stats.entry.quiz_id)}
                  aria-label={`${PLACES[place]}: ${stats.entry.title}, ${stats.points} points. Show details`}
                >
                  <span className="medal" aria-hidden="true">
                    {place + 1}
                  </span>
                  <span className="podium-title">{stats.entry.title}</span>
                  <span className="podium-course">
                    <span className="course-dot" aria-hidden="true" />
                    <span className="truncate">{stats.entry.course_name}</span>
                  </span>
                  <span className="podium-points">{stats.points} pts</span>
                  <span className="podium-best">Best {formatScore(stats.best ?? 0)}</span>
                </button>
                <span className="podium-step" aria-hidden="true">
                  {PLACES[place]}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
