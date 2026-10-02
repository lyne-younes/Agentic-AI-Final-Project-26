from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FlashcardSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    created_at: datetime


class FlashcardSetListItem(FlashcardSetOut):
    """GET /courses/{id}/flashcard-sets: a set plus how many cards it holds."""

    card_count: int


class FlashcardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    front_text: str
    back_text: str
    order: int


class FlashcardSetDetail(FlashcardSetOut):
    cards: list[FlashcardOut]
