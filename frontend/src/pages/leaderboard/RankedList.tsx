import { ArrowDown, ArrowUp, ChevronDown, RotateCcw, Sparkles } from "lucide-react";
import { useState, type CSSProperties } from "react";
import { Link } from "react-router";
import type { QuizAttempt, QuizDifficulty, QuizFormat } from "../../api/types";
import { ScoreRing } from "../../components/ScoreRing";
import { courseColor } from "../../lib/courseColor";
import { formatRelative, pluralize } from "../../lib/format";
import { DIFFICULTY_MULTIPLIER, formatScore, type QuizStats, type SortKey } from "./stats";

const DIFFICULTY_LABELS: Record<QuizDifficulty, string> = {
  easy: "Easy",
  medium: "Medium",
  hard: "Hard",
};
const FORMAT_LABELS: Record<QuizFormat, string> = {
  mcq: "multiple choice",
  true_false: "true/false",
  short_answer: "short answer",
  mixed: "mixed format",
};
const attemptDate = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

interface RankedListProps {
  rows: QuizStats[];
  sort: SortKey;
  movement: Map<number, number | "new">;
  expandedId: number | null;
  onToggle: (quizId: number) => void;
}

export function RankedList({ rows, sort, movement, expandedId, onToggle }: RankedListProps) {
  return (
    <ol className="ranked-list">
      {rows.map((stats, index) => (
        <RankedRow
          key={stats.entry.quiz_id}
          rank={index + 1}
          stats={stats}
          sort={sort}
          move={sort === "points" ? movement.get(stats.entry.quiz_id) : undefined}
          expanded={expandedId === stats.entry.quiz_id}
          onToggle={() => onToggle(stats.entry.quiz_id)}
        />
      ))}
    </ol>
  );
}

function RankedRow({
  rank,
  stats,
  sort,
  move,
  expanded,
  onToggle,
}: {
  rank: number;
  stats: QuizStats;
  sort: SortKey;
  move: number | "new" | undefined;
  expanded: boolean;
  onToggle: () => void;
}) {
  const { entry } = stats;
  const panelId = `quiz-panel-${entry.quiz_id}`;
  const style = { "--course-color": courseColor(entry.course_id) } as CSSProperties;
  const medal = rank <= 3 ? ["gold", "silver", "bronze"][rank - 1] : null;

  return (
    <li
      id={`quiz-row-${entry.quiz_id}`}
      className={`ranked-row${expanded ? " ranked-row-open" : ""}`}
      style={style}
    >
      <button
        type="button"
        className="ranked-summary"
        aria-expanded={expanded}
        aria-controls={panelId}
        onClick={onToggle}
      >
        <span className={`rank${medal ? ` rank-${medal}` : ""}`}>
          <span className="visually-hidden">Rank </span>
          {rank}
        </span>
        <Movement move={move} />
        <span className="ranked-main">
          <span className="ranked-title">{entry.title}</span>
          <span className="ranked-meta">
            <span className="course-dot" aria-hidden="true" />
            <span className="truncate">{entry.course_name}</span>
            <span className={`difficulty difficulty-${entry.difficulty}`}>
              {DIFFICULTY_LABELS[entry.difficulty]}
            </span>
          </span>
        </span>
        <Sparkline scores={stats.attempts.map((a) => a.score)} />
        <span className="ranked-figure ranked-best">
          <ScoreRing score={stats.best ?? 0} />
        </span>
        <span className="ranked-figure ranked-played">
          <strong>{stats.attempts.length}</strong>
          <span>{stats.attempts.length === 1 ? "play" : "plays"}</span>
        </span>
        <span className={`ranked-figure ranked-key${sort === "points" ? "" : " ranked-key-alt"}`}>
          <strong>{keyFigure(stats, sort)}</strong>
          <span>{keyLabel(sort)}</span>
        </span>
        <ChevronDown size={18} className="ranked-chevron" aria-hidden="true" />
      </button>

      {expanded && (
        <div id={panelId} className="ranked-panel">
          <AttemptChart attempts={stats.attempts} best={stats.best ?? 0} />
          <QuizDetails stats={stats} />
        </div>
      )}
    </li>
  );
}

function keyFigure(stats: QuizStats, sort: SortKey): string {
  switch (sort) {
    case "improved":
      return `+${Math.round(stats.improvement)}`;
    case "recent":
      return stats.lastAttemptAt ? formatRelative(stats.lastAttemptAt) : "–";
    case "best":
      return formatScore(stats.best ?? 0);
    case "played":
      return String(stats.attempts.length);
    default:
      return String(stats.points);
  }
}

function keyLabel(sort: SortKey): string {
  return {
    points: "points",
    best: "best",
    improved: "points gained",
    played: "attempts",
    recent: "last played",
  }[sort];
}

function Movement({ move }: { move: number | "new" | undefined }) {
  if (move === undefined) return <span className="movement" aria-hidden="true" />;
  if (move === "new") {
    return (
      <span className="movement movement-new" title="Newly ranked with your latest attempt">
        <Sparkles size={12} aria-hidden="true" />
        New
      </span>
    );
  }
  const up = move > 0;
  return (
    <span
      className={`movement ${up ? "movement-up" : "movement-down"}`}
      title={`${up ? "Up" : "Down"} ${Math.abs(move)} since your latest attempt`}
    >
      {up ? <ArrowUp size={12} aria-hidden="true" /> : <ArrowDown size={12} aria-hidden="true" />}
      {Math.abs(move)}
      <span className="visually-hidden">
        {up ? " places up" : " places down"} since your latest attempt
      </span>
    </span>
  );
}

/** Up to the last 10 scores: a 2px line, the latest point marked in the accent. */
function Sparkline({ scores }: { scores: number[] }) {
  const recent = scores.slice(-10);
  const width = 72;
  const height = 28;
  const pad = 4;
  const x = (i: number) =>
    recent.length === 1 ? width / 2 : pad + (i * (width - 2 * pad)) / (recent.length - 1);
  const y = (score: number) => height - pad - (score / 100) * (height - 2 * pad);
  const points = recent.map((score, i) => `${x(i)},${y(score)}`).join(" ");
  const last = recent.length - 1;

  return (
    <svg className="sparkline" width={width} height={height} aria-hidden="true">
      <line className="sparkline-base" x1={pad} x2={width - pad} y1={y(0)} y2={y(0)} />
      {recent.length > 1 && <polyline className="sparkline-line" points={points} />}
      <circle className="sparkline-dot" cx={x(last)} cy={y(recent[last])} r={3.5} />
    </svg>
  );
}

/** Every attempt as a column (latest in the accent), with the personal best as a threshold. */
function AttemptChart({ attempts, best }: { attempts: QuizAttempt[]; best: number }) {
  const [active, setActive] = useState<number | null>(null);
  const shown = attempts.slice(-20);
  const offset = attempts.length - shown.length;

  return (
    <figure className="attempt-chart">
      <figcaption className="attempt-chart-caption">
        Score per attempt
        {offset > 0 && <span className="text-subtle"> · last {shown.length}</span>}
      </figcaption>
      <div className="attempt-plot">
        <div className="attempt-axis" aria-hidden="true">
          <span>100</span>
          <span>50</span>
          <span>0</span>
        </div>
        <div className="attempt-area">
          <div className="attempt-grid" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <div className="attempt-best" style={{ bottom: `${best}%` }} aria-hidden="true">
            <span>Best {formatScore(best)}</span>
          </div>
          <ol className="attempt-bars">
            {shown.map((attempt, i) => {
              const number = offset + i + 1;
              const latest = i === shown.length - 1;
              return (
                // The whole column is the hover target, not just the (possibly tiny) bar.
                <li
                  key={attempt.id}
                  className={`attempt-slot${active === i ? " attempt-slot-active" : ""}`}
                  onPointerEnter={() => setActive(i)}
                  onPointerLeave={() => setActive(null)}
                >
                  <button
                    type="button"
                    className={`attempt-bar${latest ? " attempt-bar-latest" : ""}`}
                    style={{ height: `${Math.max(attempt.score, 1.5)}%` }}
                    aria-label={`Attempt ${number}: ${formatScore(attempt.score)}, ${attemptDate.format(new Date(attempt.attempted_at))}`}
                    onFocus={() => setActive(i)}
                    onBlur={() => setActive(null)}
                  />
                  {active === i && (
                    <span
                      className="chart-tooltip attempt-tooltip"
                      style={{ bottom: `${Math.max(attempt.score, 1.5)}%` }}
                      aria-hidden="true"
                    >
                      <strong>{formatScore(attempt.score)}</strong>
                      <span>
                        Attempt {number} · {attemptDate.format(new Date(attempt.attempted_at))}
                      </span>
                    </span>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
      </div>
      <div className="attempt-xlabels" aria-hidden="true">
        {shown.map((attempt, i) => (
          <span key={attempt.id}>{offset + i + 1}</span>
        ))}
      </div>
    </figure>
  );
}

/** The numbers behind the chart, the "race against your best self", and the way back in. */
function QuizDetails({ stats }: { stats: QuizStats }) {
  const { entry } = stats;
  const latest = stats.latest ?? 0;
  const best = stats.best ?? 0;
  const gap = Math.round(best - latest);

  return (
    <div className="quiz-details">
      <dl className="quiz-details-figures">
        <div>
          <dt>First</dt>
          <dd>{formatScore(stats.first ?? 0)}</dd>
        </div>
        <div>
          <dt>Latest</dt>
          <dd>{formatScore(latest)}</dd>
        </div>
        <div>
          <dt>Best</dt>
          <dd>{formatScore(best)}</dd>
        </div>
        <div>
          <dt>Points</dt>
          <dd>
            {stats.points}
            <span className="quiz-details-multiplier">
              ×{DIFFICULTY_MULTIPLIER[entry.difficulty]}
            </span>
          </dd>
        </div>
      </dl>
      <p className="ghost-race">
        {best === 100 && latest === 100
          ? "Perfect score on your latest attempt. Nothing left to beat."
          : gap === 0
            ? `Your latest attempt is your best. Can you push past ${formatScore(best)}?`
            : `Your latest attempt was ${gap} ${gap === 1 ? "point" : "points"} behind your best.`}
      </p>
      <p className="text-subtle quiz-details-meta">
        {pluralize(entry.question_count, "question")} · {FORMAT_LABELS[entry.format]} · Last
        played {stats.lastAttemptAt ? formatRelative(stats.lastAttemptAt) : "never"}
      </p>
      <div className="quiz-details-actions">
        <Link
          to={`/courses/${entry.course_id}/study-tools/quiz/${entry.quiz_id}`}
          className="btn btn-sm btn-accent"
        >
          <RotateCcw size={15} />
          {best < 100 ? `Beat ${formatScore(best)}` : "Retake"}
        </Link>
        <Link to={`/courses/${entry.course_id}/study-tools`} className="btn btn-sm btn-ghost">
          Open {entry.course_name}
        </Link>
      </div>
    </div>
  );
}
