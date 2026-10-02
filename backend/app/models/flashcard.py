from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FlashcardSet(Base):
    __tablename__ = "flashcard_sets"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Flashcard(Base):
    __tablename__ = "flashcards"

    id: Mapped[int] = mapped_column(primary_key=True)
    flashcard_set_id: Mapped[int] = mapped_column(
        ForeignKey("flashcard_sets.id", ondelete="CASCADE"), index=True
    )
    front_text: Mapped[str] = mapped_column(Text)
    back_text: Mapped[str] = mapped_column(Text)
    order: Mapped[int] = mapped_column(Integer)
