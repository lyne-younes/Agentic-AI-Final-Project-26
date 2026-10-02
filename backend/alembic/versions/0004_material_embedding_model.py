"""materials.embedding_model: which embedding model produced a material's chunks

Revision ID: 0004
Revises: 0003
Create Date: 2026-09-15

Existing rows get NULL, which the backend treats as outdated and re-indexes on startup.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("materials", sa.Column("embedding_model", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("materials", "embedding_model")
