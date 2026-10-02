from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.rag.embeddings import EMBEDDING_DIMENSIONS


class MaterialChunk(Base):
    """RAG index row: one chunk of a material's text plus its embedding."""

    __tablename__ = "material_chunks"
    __table_args__ = (
        Index(
            "ix_material_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), index=True
    )
    # Denormalized from materials.course_id: course-scoped similarity search is the hottest query.
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIMENSIONS))
    chunk_order: Mapped[int] = mapped_column(Integer)
