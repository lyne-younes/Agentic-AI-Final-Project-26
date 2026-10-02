import {
  Crosshair,
  Crown,
  Flame,
  Footprints,
  Library,
  Lock,
  Mountain,
  TrendingUp,
  Zap,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Achievement, AchievementId } from "./stats";

const ICONS: Record<AchievementId, ReactNode> = {
  "first-steps": <Footprints size={20} />,
  perfectionist: <Crown size={20} />,
  "hard-mode": <Mountain size={20} />,
  comeback: <TrendingUp size={20} />,
  marathon: <Zap size={20} />,
  "on-fire": <Flame size={20} />,
  polymath: <Library size={20} />,
  sharpshooter: <Crosshair size={20} />,
};

/** All-time badges, each with its progress so a locked one says how close it is. */
export function Achievements({ list }: { list: Achievement[] }) {
  const unlocked = list.filter((a) => a.unlocked).length;
  return (
    <section className="lb-card" aria-labelledby="achievements-heading">
      <div className="lb-card-header">
        <h2 id="achievements-heading" className="lb-section-title">
          Achievements
        </h2>
        <span className="text-subtle">
          {unlocked} of {list.length} unlocked
        </span>
      </div>
      <ul className="achievements">
        {list.map((achievement) => (
          <li
            key={achievement.id}
            className={`achievement${achievement.unlocked ? " achievement-unlocked" : ""}`}
          >
            <span className="achievement-icon" aria-hidden="true">
              {ICONS[achievement.id]}
              {!achievement.unlocked && (
                <span className="achievement-lock">
                  <Lock size={10} />
                </span>
              )}
            </span>
            <div className="achievement-text">
              <p className="achievement-title">
                {achievement.title}
                <span className="visually-hidden">
                  {achievement.unlocked ? " (unlocked)" : " (locked)"}
                </span>
              </p>
              <p className="achievement-description">{achievement.description}</p>
              {!achievement.unlocked && (
                <div className="achievement-progress">
                  <div className="meter meter-sm" aria-hidden="true">
                    <span
                      className="meter-fill"
                      style={{ width: `${(achievement.current / achievement.target) * 100}%` }}
                    />
                  </div>
                  <span>
                    {Math.round(achievement.current)}/{achievement.target}
                  </span>
                </div>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
