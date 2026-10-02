import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class MaterialType(enum.StrEnum):
    pdf = "pdf"
    docx = "docx"
    text_file = "text_file"
    authored_note = "authored_note"


class IndexingStatus(enum.StrEnum):
    """Progress of the background chunk + embed job that feeds material_chunks."""

    pending = "pending"
    indexed = "indexed"
    failed = "failed"


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (
        # A course's materials can't share a title (case-insensitive); see 0005_unique_names.
        Index("uq_materials_course_id_lower_title", "course_id", text("lower(title)"), unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    type: Mapped[MaterialType] = mapped_column(Enum(MaterialType, name="material_type"))
    title: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text)  # null for authored notes
    raw_text: Mapped[str] = mapped_column(Text, server_default="")  # source for chunking
    # Array column, not a join table: tags only pre-filter chunks before similarity search.
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    indexing_status: Mapped[IndexingStatus] = mapped_column(
        Enum(IndexingStatus, name="indexing_status"), server_default=IndexingStatus.pending.value
    )
    # Embedding model used for the chunks; a different model triggers re-indexing at startup.
    embedding_model: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
