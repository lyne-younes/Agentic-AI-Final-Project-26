from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import CourseStatus, QuestionType, QuizDifficulty, QuizFormat


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    format: QuizFormat
    difficulty: QuizDifficulty
    created_at: datetime


class QuizListItem(QuizOut):
    """GET /courses/{id}/quizzes: a quiz plus the figures its Study Tools row shows."""

    question_count: int
    attempt_count: int
    best_score: float | None  # None until the first attempt
    last_score: float | None
    last_attempt_at: datetime | None


class QuizQuestionOut(BaseModel):
    """No `correct_answer` - this is what the student sees while taking the quiz."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    question_text: str
    question_type: QuestionType
    options: list[str] | None
    order: int


class QuizDetail(QuizOut):
    questions: list[QuizQuestionOut]


class LinkedFlashcardSet(BaseModel):
    id: int
    title: str
    card_count: int


class AttemptStudyLink(BaseModel):
    """A chat opened from this attempt, and the flashcard set it produced, if any."""

    kind: Literal["quiz_explain", "quiz_flashcards"]
    chat_session_id: int
    created_at: datetime
    flashcard_set: LinkedFlashcardSet | None = None


class QuizAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    score: float
    attempted_at: datetime
    has_answers: bool = True  # False for attempts taken before answers were recorded
    study_links: list[AttemptStudyLink] = []  # oldest first


class QuizAnswerIn(BaseModel):
    question_id: int
    answer: str = Field(max_length=2000)


class QuizAttemptCreate(BaseModel):
    answers: list[QuizAnswerIn] = Field(min_length=1)


class QuizAnswerResult(BaseModel):
    question_id: int
    given_answer: str
    correct_answer: str
    is_correct: bool


class QuizAttemptResult(BaseModel):
    """A graded attempt: the submit response, and GET /quizzes/{id}/attempts/{attempt_id}."""

    id: int
    score: float
    attempted_at: datetime
    has_answers: bool = True  # False (and `answers` empty) for an attempt recorded score-only
    answers: list[QuizAnswerResult]


class LeaderboardEntry(BaseModel):
    """One quiz with all its attempts, for the leaderboard (stats are computed client-side)."""

    quiz_id: int
    title: str
    course_id: int
    course_name: str
    course_status: CourseStatus
    format: QuizFormat
    difficulty: QuizDifficulty
    question_count: int
    created_at: datetime
    attempts: list[QuizAttemptOut]  # oldest first
