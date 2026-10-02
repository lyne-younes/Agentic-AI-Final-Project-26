import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class QuizFormat(enum.StrEnum):
    mcq = "mcq"
    true_false = "true_false"
    short_answer = "short_answer"
    mixed = "mixed"


class QuizDifficulty(enum.StrEnum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class QuestionType(enum.StrEnum):
    """Per-question type; only meaningful for disambiguating a `mixed`-format quiz."""

    mcq = "mcq"
    true_false = "true_false"
    short_answer = "short_answer"


class Quiz(Base):
    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    format: Mapped[QuizFormat] = mapped_column(Enum(QuizFormat, name="quiz_format"))
    difficulty: Mapped[QuizDifficulty] = mapped_column(Enum(QuizDifficulty, name="quiz_difficulty"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class QuizQuestion(Base):
    """Immutable once created: regenerating creates a new quiz."""

    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    question_text: Mapped[str] = mapped_column(Text)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType, name="question_type"))
    options: Mapped[list[str] | None] = mapped_column(JSONB)  # MCQ choices; null otherwise
    correct_answer: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer)


class QuizAttempt(Base):
    """One row per attempt; retaking adds a row."""

    __tablename__ = "quiz_attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    quiz_id: Mapped[int] = mapped_column(ForeignKey("quizzes.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Numeric(5, 2))  # percent correct, 0-100
    # [{"question_id", "given_answer", "is_correct"}], for reviewing the attempt later.
    answers: Mapped[list[dict] | None] = mapped_column(JSONB)
    attempted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
