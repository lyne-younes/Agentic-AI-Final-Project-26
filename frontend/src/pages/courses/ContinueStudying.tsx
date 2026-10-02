import { Dices, Flame, MessageSquare, Swords, Upload } from "lucide-react";
import { useMemo, useState, type ReactNode } from "react";
import { Link } from "react-router";
import type { CourseListItem, LeaderboardEntry } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { formatRelative } from "../../lib/format";
import { ChallengePicker } from "../leaderboard/ChallengePicker";
import {
  attemptsByDay,
  formatScore,
  levelFor,
  quizStats,
  streaks,
  totalXp,
} from "../leaderboard/stats";

interface ContinueStudyingProps {
  courses: CourseListItem[];
  quizzes: LeaderboardEntry[];
}

/** Three one-click ways back in: the latest chat, a quiz worth retaking, and the streak. */
export function ContinueStudying({ courses, quizzes }: ContinueStudyingProps) {
  const [challengeOpen, setChallengeOpen] = useState(false);
  const active = courses.filter((course) => course.status === "active");

  const pool = useMemo(
    () => quizzes.filter((q) => q.course_status === "active").map((q) => quizStats(q)),
    [quizzes],
  );
  const progress = useMemo(() => {
    const streak = streaks(attemptsByDay(quizzes));
    return { streak, level: levelFor(totalXp(quizzes)) };
  }, [quizzes]);

  if (active.length === 0) return null;

  // 1. The chat to resume, or a course to start one in.
  const lastChat = active
    .filter((course) => course.last_chat_at)
    .sort((a, b) => (b.last_chat_at ?? "").localeCompare(a.last_chat_at ?? ""))[0];
  const withMaterials = active.find((course) => course.material_count > 0);
  let chatTile: ReactNode;
  if (lastChat) {
    chatTile = (
      <Tile
        icon={<MessageSquare size={20} />}
        label="Pick up where you left off"
        to={`/courses/${lastChat.id}/chat/${lastChat.last_chat_session_id}`}
        title={`Resume your ${lastChat.name} chat`}
        sub={`Last message ${formatRelative(lastChat.last_chat_at!)}`}
      />
    );
  } else if (withMaterials) {
    chatTile = (
      <Tile
        icon={<MessageSquare size={20} />}
        label="Start studying"
        to={`/courses/${withMaterials.id}/chat`}
        title={`Ask ${withMaterials.name} anything`}
        sub="Answers come from your own materials"
      />
    );
  } else {
    chatTile = (
      <Tile
        icon={<Upload size={20} />}
        label="Get started"
        to={`/courses/${active[0].id}/materials`}
        title={`Add materials to ${active[0].name}`}
        sub="PDFs, Word documents, text files or notes"
      />
    );
  }

  // 2. The quiz most worth retaking: the weakest attempted one, else one not tried yet.
  const attempted = pool.filter((s) => s.best !== null && s.best < 100);
  const weakest = attempted.sort((a, b) => (a.best ?? 0) - (b.best ?? 0))[0];
  const untried = pool.find((s) => s.best === null);
  const target = weakest ?? untried;
  const quizTile =
    pool.length === 0 ? null : (
      <Tile
        icon={<Swords size={20} />}
        label={weakest ? "Beat your score" : untried ? "Try something new" : "All aced"}
        to={
          target
            ? `/courses/${target.entry.course_id}/study-tools/quiz/${target.entry.quiz_id}`
            : "/leaderboard"
        }
        title={
          weakest
            ? `Beat ${formatScore(weakest.best ?? 0)} on ${weakest.entry.title}`
            : untried
              ? `Take ${untried.entry.title}`
              : "Every quiz at 100%. Nice work."
        }
        sub={target ? target.entry.course_name : "See your rankings"}
        extra={
          <Button
            size="sm"
            variant="ghost"
            iconOnly
            aria-label="Pick a random challenge"
            title="Pick a random challenge"
            onClick={() => setChallengeOpen(true)}
          >
            <Dices size={16} />
          </Button>
        }
      />
    );

  // 3. The streak and level.
  const { streak, level } = progress;
  const streakTile = (
    <Tile
      icon={<Flame size={20} />}
      tone={streak.current > 0 ? "fire" : undefined}
      label={`Level ${level.level} · ${level.title}`}
      to="/leaderboard"
      title={streak.current > 0 ? `${streak.current}-day streak` : "Start a streak"}
      sub={
        streak.activeToday
          ? "You've studied today. See your leaderboard"
          : streak.current > 0
            ? "Take a quiz today to keep it going"
            : "Take a quiz today to start one"
      }
    />
  );

  return (
    <section className="continue" aria-labelledby="continue-heading">
      <h2 id="continue-heading" className="continue-heading">
        Continue studying
      </h2>
      <div className="continue-row">
        {chatTile}
        {quizTile}
        {streakTile}
      </div>
      <ChallengePicker open={challengeOpen} onClose={() => setChallengeOpen(false)} pool={pool} />
    </section>
  );
}

function Tile({
  icon,
  tone,
  label,
  to,
  title,
  sub,
  extra,
}: {
  icon: ReactNode;
  tone?: "fire";
  label: string;
  to: string;
  title: string;
  sub: string;
  extra?: ReactNode;
}) {
  return (
    <article className={`continue-tile${tone ? ` continue-tile-${tone}` : ""}`}>
      <span className="continue-icon" aria-hidden="true">
        {icon}
      </span>
      <div className="continue-text">
        <p className="continue-label">{label}</p>
        <h3 className="continue-title">
          <Link to={to} className="continue-link">
            {title}
          </Link>
        </h3>
        <p className="continue-sub">{sub}</p>
      </div>
      {extra && <div className="continue-extra">{extra}</div>}
    </article>
  );
}
