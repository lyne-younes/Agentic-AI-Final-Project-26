"""What a chat turn created: the quiz, flashcard set or summary behind an assistant message.

Matched by timestamp: a turn is one transaction, and Postgres `now()` is the transaction start
time, so the message and the content created in that turn share the same timestamp.
"""

from collections.abc import Iterable
from datetime import datetime

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.schemas import CreatedItemOut
from app.models import (
    ChatMessage,
    Flashcard,
    FlashcardSet,
    MessageRole,
    Quiz,
    QuizQuestion,
    Summary,
)

FORMAT_LABELS = {
    "mcq": "MCQ",
    "true_false": "true/false",
    "short_answer": "short-answer",
    "mixed": "mixed",
}


def item_title(item: CreatedItemOut) -> str:
    """A chat title for a session whose first created item is this one."""
    if item.kind == "quiz":
        label = FORMAT_LABELS.get(item.format or "", item.format or "")
        return f"{(item.difficulty or '').capitalize()} {label} quiz – {item.title}".strip()
    if item.kind == "flashcards":
        return f"Flashcards – {item.title}"
    return "Course summary"


async def items_by_timestamp(
    db: AsyncSession, course_id: int, timestamps: Iterable[datetime]
) -> dict[datetime, list[CreatedItemOut]]:
    """Everything the course gained in the turns that ran at these timestamps, oldest first."""
    stamps = set(timestamps)
    found: dict[datetime, list[tuple[int, CreatedItemOut]]] = {}
    if not stamps:
        return {}

    question_count = (
        select(func.count())
        .where(QuizQuestion.quiz_id == Quiz.id)
        .correlate(Quiz)
        .scalar_subquery()
    )
    quizzes = await db.execute(
        select(Quiz, question_count).where(Quiz.course_id == course_id, Quiz.created_at.in_(stamps))
    )
    for quiz, count in quizzes.all():
        found.setdefault(quiz.created_at, []).append(
            (
                quiz.id,
                CreatedItemOut(
                    kind="quiz",
                    id=quiz.id,
                    title=quiz.title,
                    count=count,
                    format=quiz.format.value,
                    difficulty=quiz.difficulty.value,
                ),
            )
        )

    card_count = (
        select(func.count())
        .where(Flashcard.flashcard_set_id == FlashcardSet.id)
        .correlate(FlashcardSet)
        .scalar_subquery()
    )
    sets = await db.execute(
        select(FlashcardSet, card_count).where(
            FlashcardSet.course_id == course_id, FlashcardSet.created_at.in_(stamps)
        )
    )
    for flashcard_set, count in sets.all():
        found.setdefault(flashcard_set.created_at, []).append(
            (
                flashcard_set.id,
                CreatedItemOut(
                    kind="flashcards", id=flashcard_set.id, title=flashcard_set.title, count=count
                ),
            )
        )

    summary = await db.scalar(
        select(Summary).where(Summary.course_id == course_id, Summary.updated_at.in_(stamps))
    )
    if summary is not None:
        found.setdefault(summary.updated_at, []).append(
            (0, CreatedItemOut(kind="summary", id=summary.id, title="Course summary"))
        )

    # Creation order within a turn; the summary first.
    return {
        stamp: [item for _, item in sorted(items, key=lambda pair: pair[0])]
        for stamp, items in found.items()
    }


async def first_item_by_session(
    db: AsyncSession, course_id: int, session_ids: list[int]
) -> dict[int, CreatedItemOut]:
    """The first thing each session created, if anything."""
    if not session_ids:
        return {}
    rows = await db.execute(
        select(ChatMessage.session_id, ChatMessage.created_at)
        .where(
            and_(
                ChatMessage.session_id.in_(session_ids),
                ChatMessage.role == MessageRole.assistant,
            )
        )
        .order_by(ChatMessage.id)
    )
    turns = rows.all()
    items = await items_by_timestamp(db, course_id, (stamp for _, stamp in turns))
    first: dict[int, CreatedItemOut] = {}
    for session_id, stamp in turns:
        if session_id not in first and items.get(stamp):
            first[session_id] = items[stamp][0]
    return first
