"""RAG index: material_chunks table and materials.indexing_status

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-14

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0002"
down_revision: str | Sequence[str] | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    indexing_status = sa.Enum("pending", "indexed", "failed", name="indexing_status")
    indexing_status.create(op.get_bind())
    op.add_column(
        "materials",
        sa.Column("indexing_status", indexing_status, server_default="pending", nullable=False),
    )

    op.create_table(
        "material_chunks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "material_id",
            sa.Integer(),
            sa.ForeignKey("materials.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(1536), nullable=False),
        sa.Column("chunk_order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_material_chunks_material_id", "material_chunks", ["material_id"])
    op.create_index("ix_material_chunks_course_id", "material_chunks", ["course_id"])
    op.create_index(
        "ix_material_chunks_embedding",
        "material_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    op.drop_table("material_chunks")
    op.drop_column("materials", "indexing_status")
    op.execute("DROP TYPE indexing_status")
