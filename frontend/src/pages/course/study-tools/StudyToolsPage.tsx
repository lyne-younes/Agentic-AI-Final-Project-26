import { BookOpen, ChevronRight, Layers, LayoutList } from "lucide-react";
import { Link, useOutletContext } from "react-router";
import { useFlashcardSets } from "../../../api/flashcards";
import { useQuizzes } from "../../../api/quizzes";
import type { Course, FlashcardSetListItem, QuizListItem } from "../../../api/types";
import { ScoreRing } from "../../../components/ScoreRing";
import { EmptyState } from "../../../components/ui/EmptyState";
import { ErrorState } from "../../../components/ui/ErrorState";
import { formatDate, formatRelative, pluralize } from "../../../lib/format";
import "./study-tools.css";

/** Study Tools: quizzes and flashcard sets, generated only through the chat. */
export function StudyToolsPage() {
  const course = useOutletContext<Course>();
  const quizzes = useQuizzes(course.id);
  const flashcardSets = useFlashcardSets(course.id);

  if (quizzes.error) {
    return <ErrorState message={quizzes.error.message} onRetry={() => void quizzes.refetch()} />;
  }
  if (flashcardSets.error) {
    return (
      <ErrorState
        message={flashcardSets.error.message}
        onRetry={() => void flashcardSets.refetch()}
      />
    );
  }
  if (!quizzes.data || !flashcardSets.data) {
    return <div className="skeleton" style={{ height: 200 }} />;
  }

  if (quizzes.data.length === 0 && flashcardSets.data.length === 0) {
    return (
      <EmptyState
        icon={<Layers size={30} />}
        tone="violet"
        title="No quizzes or flashcards yet"
        description={`Ask the assistant to quiz you or make flashcards from the Chat tab for ${course.name}.`}
      />
    );
  }

  return (
    <div className="page">
      <section className="study-tools-section" aria-labelledby="quizzes-heading">
        <div className="section-header">
          <h2 id="quizzes-heading" className="section-title">
            Quizzes <span className="section-count">{quizzes.data.length}</span>
          </h2>
        </div>
        {quizzes.data.length === 0 ? (
          <p className="text-muted">No quizzes yet.</p>
        ) : (
          <ul className="study-list">
            {quizzes.data.map((quiz) => (
              <li key={quiz.id}>
                <QuizRow quiz={quiz} />
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="study-tools-section" aria-labelledby="flashcards-heading">
        <div className="section-header">
          <h2 id="flashcards-heading" className="section-title">
            Flashcards <span className="section-count">{flashcardSets.data.length}</span>
          </h2>
        </div>
        {flashcardSets.data.length === 0 ? (
          <p className="text-muted">No flashcard sets yet.</p>
        ) : (
          <ul className="study-list">
            {flashcardSets.data.map((set) => (
              <li key={set.id}>
                <FlashcardRow set={set} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function QuizRow({ quiz }: { quiz: QuizListItem }) {
  const attempted = quiz.best_score !== null;
  return (
    <Link to={`quiz/${quiz.id}`} className="study-row">
      <span className="icon-tile tone-violet">
        <BookOpen size={20} />
      </span>
      <span className="study-row-text">
        <span className="study-title">{quiz.title}</span>
        <span className="study-meta">
          {pluralize(quiz.question_count, "question")} · {formatFormat(quiz.format)} ·{" "}
          {formatDifficulty(quiz.difficulty)} · Created {formatDate(quiz.created_at)}
        </span>
      </span>
      {attempted ? (
        <span className="study-grade">
          <ScoreRing score={quiz.best_score ?? 0} />
          <span className="study-grade-text">
            <span className="study-grade-label">Best score</span>
            <span className="study-grade-detail">
              Last {Math.round(quiz.last_score ?? 0)}% · {pluralize(quiz.attempt_count, "attempt")}
            </span>
            {quiz.last_attempt_at && (
              <span className="study-grade-detail">{formatRelative(quiz.last_attempt_at)}</span>
            )}
          </span>
        </span>
      ) : (
        <span className="study-grade study-grade-empty">
          <span className="study-pill">Not attempted</span>
          <span className="study-start">
            Start
            <ChevronRight size={16} aria-hidden="true" />
          </span>
        </span>
      )}
    </Link>
  );
}

function FlashcardRow({ set }: { set: FlashcardSetListItem }) {
  return (
    <Link to={`flashcards/${set.id}`} className="study-row">
      <span className="icon-tile tone-teal">
        <LayoutList size={20} />
      </span>
      <span className="study-row-text">
        <span className="study-title">{set.title}</span>
        <span className="study-meta">Created {formatDate(set.created_at)}</span>
      </span>
      <span className="study-grade">
        <span className="study-count">
          <strong>{set.card_count}</strong>
          <span>{set.card_count === 1 ? "card" : "cards"}</span>
        </span>
        <span className="study-start">
          Review
          <ChevronRight size={16} aria-hidden="true" />
        </span>
      </span>
    </Link>
  );
}

function formatFormat(format: string): string {
  return {
    mcq: "Multiple choice",
    true_false: "True/false",
    short_answer: "Short answer",
    mixed: "Mixed",
  }[format] ?? format;
}

function formatDifficulty(difficulty: string): string {
  return difficulty[0].toUpperCase() + difficulty.slice(1);
}
