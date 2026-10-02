import {
  ArrowLeft,
  CircleCheck,
  History,
  Lightbulb,
  MessageSquare,
  Plus,
  RotateCcw,
  SquareStack,
} from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useOutletContext, useParams, useSearchParams } from "react-router";
import {
  useQuiz,
  useQuizAttempt,
  useQuizAttempts,
  useSubmitQuizAttempt,
} from "../../../api/quizzes";
import type {
  AttemptStudyLink,
  ChatSource,
  Course,
  QuizAnswerInput,
  QuizAnswerResult,
  QuizAttempt,
  QuizQuestion,
} from "../../../api/types";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/ErrorState";
import type { ChatLaunchState } from "../chat/ChatPage";
import { explainMistakesPrompt, mistakesFlashcardsPrompt, type Mistake } from "./mistakes";
import "./study-tools.css";

const TRUE_FALSE_OPTIONS = ["true", "false"];

const attemptDate = new Intl.DateTimeFormat(undefined, {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/**
 * Take or review a quiz. Without a parameter it's a new attempt; `?attempt=<id>` shows that
 * graded attempt.
 */
export function QuizPage() {
  const course = useOutletContext<Course>();
  const quizId = Number(useParams().quizId);
  const [searchParams, setSearchParams] = useSearchParams();
  const attemptParam = Number(searchParams.get("attempt"));
  const reviewingId = Number.isInteger(attemptParam) && attemptParam > 0 ? attemptParam : null;

  const quiz = useQuiz(quizId);
  const attempts = useQuizAttempts(quizId);
  const review = useQuizAttempt(quizId, reviewingId);
  const submit = useSubmitQuizAttempt(quizId);
  const navigate = useNavigate();
  const [answers, setAnswers] = useState<Record<number, string>>({});

  if (quiz.error) {
    return <ErrorState message={quiz.error.message} onRetry={() => void quiz.refetch()} />;
  }
  if (!quiz.data) {
    return <div className="skeleton" style={{ height: 200 }} />;
  }

  const data = quiz.data;
  const result = reviewingId !== null ? (review.data ?? null) : null;
  const graded = result?.has_answers ? result : null;
  const gradedByQuestion = new Map(graded?.answers.map((a) => [a.question_id, a]) ?? []);
  const allAnswered = data.questions.every((question) => (answers[question.id] ?? "").trim());
  const mistakes: (Mistake & { questionId: number })[] = data.questions.flatMap((question) => {
    const answer = gradedByQuestion.get(question.id);
    return answer && !answer.is_correct
      ? [
          {
            questionId: question.id,
            question: question.question_text,
            given: answer.given_answer,
            correct: answer.correct_answer,
          },
        ]
      : [];
  });

  // Attempts are listed newest first; number them oldest = 1.
  const history = attempts.data ?? [];
  const attemptNumber = (id: number) => {
    const index = history.findIndex((attempt) => attempt.id === id);
    return index === -1 ? null : history.length - index;
  };

  /** Opens a new course chat with this message, linked to the attempt being reviewed. */
  function askAssistant(prompt: string, kind: ChatSource) {
    const state: ChatLaunchState = {
      prompt,
      origin: reviewingId !== null ? { attemptId: reviewingId, kind } : undefined,
    };
    navigate(`/courses/${course.id}/chat`, { state });
  }

  const base = `/courses/${course.id}`;
  const chatPath = (link: AttemptStudyLink) => `${base}/chat/${link.chat_session_id}`;
  // Chats this attempt already has, so the buttons reopen them instead of making duplicates.
  const links = history.find((attempt) => attempt.id === reviewingId)?.study_links ?? [];
  const explainLink = links.filter((link) => link.kind === "quiz_explain").at(-1);
  const cardsLinks = links.filter((link) => link.kind === "quiz_flashcards");
  const cardsLink = cardsLinks.filter((link) => link.flashcard_set).at(-1) ?? cardsLinks.at(-1);

  function showAttempt(id: number | null) {
    setSearchParams(id === null ? {} : { attempt: String(id) }, { preventScrollReset: true });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function submitAttempt() {
    const payload: QuizAnswerInput[] = data.questions.map((question) => ({
      question_id: question.id,
      answer: answers[question.id] ?? "",
    }));
    submit.mutate(payload, {
      onSuccess: (attempt) => {
        setAnswers({});
        showAttempt(attempt.id);
      },
    });
  }

  function retake() {
    setAnswers({});
    submit.reset();
    showAttempt(null);
  }

  const reviewing = reviewingId !== null;
  const number = reviewingId !== null ? attemptNumber(reviewingId) : null;
  const latest = history[0]?.id === reviewingId;

  return (
    <div className="page">
      <Link to={`/courses/${course.id}/study-tools`} className="back-link">
        <ArrowLeft size={16} />
        Study Tools
      </Link>

      <h1 className="page-title">{data.title}</h1>
      <p className="text-muted">
        {data.questions.length} questions · {formatLabel(data.format)} ·{" "}
        {formatLabel(data.difficulty)}
      </p>

      {history.length > 0 && (
        <AttemptHistory attempts={history} selectedId={reviewingId} onSelect={showAttempt} />
      )}
      <StudyHelp attempts={history} base={base} />

      {reviewing && review.isPending && <div className="skeleton" style={{ height: 120 }} />}

      {reviewing && review.error && (
        <div className="quiz-score-banner">
          <p>That attempt couldn't be found. It may belong to a different quiz.</p>
          <Button variant="primary" onClick={retake}>
            Take the quiz
          </Button>
        </div>
      )}

      {result && (
        <div className="quiz-score-banner">
          <div className="quiz-score">
            <p className="quiz-score-caption">
              {number ? `Attempt ${number} of ${history.length}` : "Attempt"} ·{" "}
              {attemptDate.format(new Date(result.attempted_at))}
              {!latest && history.length > 0 && <span className="badge">Earlier attempt</span>}
            </p>
            <div className="quiz-score-value">{Math.round(result.score)}%</div>
            {graded && (
              <p className="text-muted">
                {graded.answers.filter((a) => a.is_correct).length} of {graded.answers.length}{" "}
                correct
              </p>
            )}
          </div>
          <div className="quiz-result-actions">
            {explainLink ? (
              <Link to={chatPath(explainLink)} className="btn btn-accent">
                <MessageSquare size={16} />
                Open explanation
              </Link>
            ) : (
              mistakes.length > 0 && (
                <Button
                  variant="accent"
                  onClick={() =>
                    askAssistant(explainMistakesPrompt(data.title, mistakes), "quiz_explain")
                  }
                >
                  <Lightbulb size={16} />
                  Explain my mistakes
                </Button>
              )
            )}
            {cardsLink?.flashcard_set ? (
              <Link
                to={`${base}/study-tools/flashcards/${cardsLink.flashcard_set.id}`}
                className="btn btn-secondary"
              >
                <SquareStack size={16} />
                Study flashcards ({cardsLink.flashcard_set.card_count})
              </Link>
            ) : cardsLink ? (
              <Link to={chatPath(cardsLink)} className="btn btn-secondary">
                <MessageSquare size={16} />
                Open flashcards chat
              </Link>
            ) : (
              mistakes.length > 0 && (
                <Button
                  onClick={() =>
                    askAssistant(mistakesFlashcardsPrompt(data.title, mistakes), "quiz_flashcards")
                  }
                >
                  <SquareStack size={16} />
                  Turn mistakes into flashcards
                </Button>
              )
            )}
            <Button variant="ghost" onClick={retake}>
              <RotateCcw size={16} />
              Retake
            </Button>
          </div>
          {mistakes.length > 0 && !(explainLink && cardsLink) && (
            <p className="quiz-result-hint">
              Opens a new chat where the assistant works from your course materials. It stays
              linked to this attempt, so you can reopen it from here or from Study help above.
            </p>
          )}
          {!result.has_answers && (
            <p className="quiz-result-hint">
              Only the score was saved for this attempt; answers are kept for attempts taken from
              now on.
            </p>
          )}
        </div>
      )}

      {/* The questions: answerable when taking the quiz, graded when reviewing an attempt. */}
      {(!reviewing || graded) &&
        data.questions.map((question, index) => {
          const answer = gradedByQuestion.get(question.id) ?? null;
          return (
            <div key={question.id} className="quiz-question">
              <p className="quiz-question-text">
                {index + 1}. {question.question_text}
              </p>
              <QuestionInput
                question={question}
                value={answer ? answer.given_answer : (answers[question.id] ?? "")}
                graded={answer}
                onChange={(value) =>
                  setAnswers((previous) => ({ ...previous, [question.id]: value }))
                }
              />
              <QuestionFeedback
                graded={answer}
                onExplain={() => {
                  const mistake = mistakes.find((m) => m.questionId === question.id);
                  if (mistake) {
                    askAssistant(explainMistakesPrompt(data.title, [mistake]), "quiz_explain");
                  }
                }}
              />
            </div>
          );
        })}

      {submit.error && (
        <p className="form-error" role="alert">
          {submit.error.message}
        </p>
      )}

      {!reviewing && (
        <div className="modal-actions">
          <Button
            variant="primary"
            loading={submit.isPending}
            disabled={!allAnswered}
            onClick={submitAttempt}
          >
            Submit answers
          </Button>
        </div>
      )}
    </div>
  );
}

/** "New attempt" plus every past attempt, newest first. */
function AttemptHistory({
  attempts,
  selectedId,
  onSelect,
}: {
  attempts: QuizAttempt[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}) {
  return (
    <nav className="attempt-history-section" aria-labelledby="attempts-heading">
      <h2 id="attempts-heading" className="attempt-history-title">
        <History size={16} aria-hidden="true" />
        Your attempts
      </h2>
      <ol className="attempt-history">
        <li>
          <button
            type="button"
            className={`attempt-chip attempt-chip-new${selectedId === null ? " attempt-chip-selected" : ""}`}
            aria-current={selectedId === null ? "true" : undefined}
            onClick={() => onSelect(null)}
          >
            <Plus size={14} aria-hidden="true" />
            New attempt
          </button>
        </li>
        {attempts.map((attempt, index) => {
          const selected = attempt.id === selectedId;
          return (
            <li key={attempt.id}>
              <button
                type="button"
                className={`attempt-chip${selected ? " attempt-chip-selected" : ""}`}
                aria-current={selected ? "true" : undefined}
                onClick={() => onSelect(attempt.id)}
                title={attempt.has_answers ? "Review this attempt" : "Only the score was saved"}
              >
                <span className="attempt-chip-number">#{attempts.length - index}</span>
                <strong>{Math.round(attempt.score)}%</strong>
                <span className="attempt-chip-date">
                  {attemptDate.format(new Date(attempt.attempted_at))}
                </span>
              </button>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/** Every explanation chat and flashcard set made from this quiz's attempts, newest first. */
function StudyHelp({ attempts, base }: { attempts: QuizAttempt[]; base: string }) {
  const items = attempts
    .flatMap((attempt, index) =>
      attempt.study_links.map((link) => ({ link, number: attempts.length - index })),
    )
    .sort((a, b) => b.link.created_at.localeCompare(a.link.created_at));
  if (items.length === 0) return null;

  return (
    <nav className="study-help" aria-labelledby="study-help-heading">
      <h2 id="study-help-heading" className="attempt-history-title">
        <Lightbulb size={16} aria-hidden="true" />
        Study help
      </h2>
      <ul className="study-help-list">
        {items.map(({ link, number }) => {
          const set = link.flashcard_set;
          const to = set
            ? `${base}/study-tools/flashcards/${set.id}`
            : `${base}/chat/${link.chat_session_id}`;
          let label = "Explanation";
          if (link.kind === "quiz_flashcards") {
            label = set
              ? `${set.title} · ${set.card_count} ${set.card_count === 1 ? "card" : "cards"}`
              : "Flashcards chat";
          }
          return (
            <li key={link.chat_session_id}>
              <Link to={to} className="study-help-link">
                {link.kind === "quiz_explain" ? (
                  <MessageSquare size={14} aria-hidden="true" />
                ) : (
                  <SquareStack size={14} aria-hidden="true" />
                )}
                <span>{label}</span>
                <span className="study-help-meta">Attempt #{number}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

function QuestionInput({
  question,
  value,
  graded,
  onChange,
}: {
  question: QuizQuestion;
  value: string;
  graded: QuizAnswerResult | null;
  onChange: (value: string) => void;
}) {
  const options = question.question_type === "true_false" ? TRUE_FALSE_OPTIONS : question.options;

  if (options) {
    return (
      <div className="quiz-options">
        {options.map((option) => (
          <button
            key={option}
            type="button"
            className={optionClassName(option, value, graded)}
            disabled={graded !== null}
            onClick={() => onChange(option)}
          >
            {question.question_type === "true_false" ? capitalize(option) : option}
          </button>
        ))}
      </div>
    );
  }

  return (
    <input
      className="input"
      value={value}
      disabled={graded !== null}
      onChange={(event) => onChange(event.target.value)}
      placeholder="Your answer"
    />
  );
}

/** After grading: a tick for a right answer; the right answer and a way to ask why otherwise. */
function QuestionFeedback({
  graded,
  onExplain,
}: {
  graded: QuizAnswerResult | null;
  onExplain: () => void;
}) {
  if (!graded) return null;
  if (graded.is_correct) {
    return (
      <p className="quiz-feedback quiz-feedback-correct">
        <CircleCheck size={16} aria-hidden="true" />
        Correct
      </p>
    );
  }
  return (
    <div className="quiz-feedback quiz-feedback-wrong">
      <p>
        Correct answer: <strong>{graded.correct_answer}</strong>
      </p>
      <Button size="sm" variant="ghost" onClick={onExplain}>
        <Lightbulb size={14} />
        Explain this
      </Button>
    </div>
  );
}

function optionClassName(option: string, selected: string, graded: QuizAnswerResult | null): string {
  if (!graded) {
    return `quiz-option${option === selected ? " quiz-option-selected" : ""}`;
  }
  const same = (a: string, b: string) => a.trim().toLowerCase() === b.trim().toLowerCase();
  if (same(option, graded.correct_answer)) return "quiz-option quiz-option-correct";
  if (same(option, selected)) return "quiz-option quiz-option-incorrect";
  return "quiz-option";
}

function capitalize(text: string): string {
  return text[0].toUpperCase() + text.slice(1);
}

function formatLabel(value: string): string {
  return value === "mcq" ? "Multiple choice" : capitalize(value.replace("_", " "));
}
