import { ArrowLeft, ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { Link, useOutletContext, useParams } from "react-router";
import { useFlashcardSet } from "../../../api/flashcards";
import type { Course } from "../../../api/types";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/ErrorState";
import "./study-tools.css";

/** Flip-card review: click or step through the cards. */
export function FlashcardSetPage() {
  const course = useOutletContext<Course>();
  const setId = Number(useParams().setId);
  const flashcardSet = useFlashcardSet(setId);
  const [index, setIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);

  if (flashcardSet.error) {
    return (
      <ErrorState
        message={flashcardSet.error.message}
        onRetry={() => void flashcardSet.refetch()}
      />
    );
  }
  if (!flashcardSet.data) {
    return <div className="skeleton" style={{ height: 200 }} />;
  }

  const { title, cards } = flashcardSet.data;
  const card = cards[index];

  function go(delta: number) {
    setIndex((current) => Math.min(Math.max(current + delta, 0), cards.length - 1));
    setFlipped(false);
  }

  return (
    <div className="page">
      <Link to={`/courses/${course.id}/study-tools`} className="back-link">
        <ArrowLeft size={16} />
        Study Tools
      </Link>

      <h1 className="page-title">{title}</h1>

      {card && (
        <div className="flashcard-review">
          <button
            type="button"
            className={`flashcard${flipped ? " flashcard-back" : ""}`}
            onClick={() => setFlipped((value) => !value)}
          >
            {flipped ? card.back_text : card.front_text}
          </button>
          <p className="flashcard-hint">Click the card to flip it</p>

          <div className="flashcard-nav">
            <Button iconOnly aria-label="Previous card" disabled={index === 0} onClick={() => go(-1)}>
              <ChevronLeft size={18} />
            </Button>
            <span className="text-muted">
              {index + 1} of {cards.length}
            </span>
            <Button
              iconOnly
              aria-label="Next card"
              disabled={index === cards.length - 1}
              onClick={() => go(1)}
            >
              <ChevronRight size={18} />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
