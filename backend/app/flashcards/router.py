from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.auth.dependencies import CurrentUser, DbSession
from app.courses.dependencies import OwnedCourse
from app.flashcards.schemas import (
    FlashcardOut,
    FlashcardSetDetail,
    FlashcardSetListItem,
    FlashcardSetOut,
)
from app.models import Course, Flashcard, FlashcardSet

router = APIRouter(tags=["flashcards"])


async def get_owned_flashcard_set(set_id: int, user: CurrentUser, db: DbSession) -> FlashcardSet:
    flashcard_set = await db.scalar(
        select(FlashcardSet)
        .join(Course, Course.id == FlashcardSet.course_id)
        .where(FlashcardSet.id == set_id, Course.user_id == user.id)
    )
    if flashcard_set is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Flashcard set not found")
    return flashcard_set


OwnedFlashcardSet = Annotated[FlashcardSet, Depends(get_owned_flashcard_set)]


@router.get("/courses/{course_id}/flashcard-sets")
async def list_flashcard_sets(course: OwnedCourse, db: DbSession) -> list[FlashcardSetListItem]:
    card_count = (
        select(func.count())
        .where(Flashcard.flashcard_set_id == FlashcardSet.id)
        .correlate(FlashcardSet)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(FlashcardSet, card_count)
        .where(FlashcardSet.course_id == course.id)
        .order_by(FlashcardSet.created_at.desc(), FlashcardSet.id.desc())
    )
    return [
        FlashcardSetListItem(
            **FlashcardSetOut.model_validate(flashcard_set).model_dump(), card_count=count
        )
        for flashcard_set, count in rows.all()
    ]


@router.get("/flashcard-sets/{set_id}")
async def get_flashcard_set(flashcard_set: OwnedFlashcardSet, db: DbSession) -> FlashcardSetDetail:
    cards = await db.scalars(
        select(Flashcard)
        .where(Flashcard.flashcard_set_id == flashcard_set.id)
        .order_by(Flashcard.order)
    )
    return FlashcardSetDetail(
        **FlashcardSetOut.model_validate(flashcard_set).model_dump(),
        cards=[FlashcardOut.model_validate(card) for card in cards],
    )
