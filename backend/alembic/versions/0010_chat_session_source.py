"""Chat sessions: source_quiz_attempt_id and source_kind, linking a chat to the quiz attempt that
opened it

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-24 17:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SOURCE = sa.Enum("quiz_explain", "quiz_flashcards", name="chat_session_source")


def upgrade() -> None:
    SOURCE.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "chat_sessions", sa.Column("source_quiz_attempt_id", sa.Integer(), nullable=True)
    )
    op.add_column("chat_sessions", sa.Column("source_kind", SOURCE, nullable=True))
    op.create_foreign_key(
        op.f("fk_chat_sessions_source_quiz_attempt_id_quiz_attempts"),
        "chat_sessions",
        "quiz_attempts",
        ["source_quiz_attempt_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_chat_sessions_source_quiz_attempt_id"),
        "chat_sessions",
        ["source_quiz_attempt_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_chat_sessions_source_quiz_attempt_id"), table_name="chat_sessions")
    op.drop_constraint(
        op.f("fk_chat_sessions_source_quiz_attempt_id_quiz_attempts"),
        "chat_sessions",
        type_="foreignkey",
    )
    op.drop_column("chat_sessions", "source_kind")
    op.drop_column("chat_sessions", "source_quiz_attempt_id")
    SOURCE.drop(op.get_bind(), checkfirst=True)
