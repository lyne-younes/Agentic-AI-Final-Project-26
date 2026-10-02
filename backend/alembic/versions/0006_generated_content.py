"""Generated content: summaries, quizzes, flashcards, and chat_sessions.pending_state

Revision ID: 0006
Revises: 0005
Create Date: 2026-09-16

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("pending_state", postgresql.JSONB(), nullable=True))

    op.create_table(
        "summaries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_edited", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "summary_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "archived_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_summary_history_course_id", "summary_history", ["course_id"])

    op.create_table(
        "quizzes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "format",
            sa.Enum("mcq", "true_false", "short_answer", "mixed", name="quiz_format"),
            nullable=False,
        ),
        sa.Column(
            "difficulty",
            sa.Enum("easy", "medium", "hard", name="quiz_difficulty"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_quizzes_course_id", "quizzes", ["course_id"])

    op.create_table(
        "quiz_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column(
            "question_type",
            sa.Enum("mcq", "true_false", "short_answer", name="question_type"),
            nullable=False,
        ),
        sa.Column("options", postgresql.JSONB(), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_quiz_questions_quiz_id", "quiz_questions", ["quiz_id"])

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "quiz_id", sa.Integer(), sa.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("score", sa.Numeric(5, 2), nullable=False),
        sa.Column(
            "attempted_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_quiz_attempts_quiz_id", "quiz_attempts", ["quiz_id"])

    op.create_table(
        "flashcard_sets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_flashcard_sets_course_id", "flashcard_sets", ["course_id"])

    op.create_table(
        "flashcards",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "flashcard_set_id",
            sa.Integer(),
            sa.ForeignKey("flashcard_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("front_text", sa.Text(), nullable=False),
        sa.Column("back_text", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
    )
    op.create_index("ix_flashcards_flashcard_set_id", "flashcards", ["flashcard_set_id"])


def downgrade() -> None:
    op.drop_table("flashcards")
    op.drop_table("flashcard_sets")
    op.drop_table("quiz_attempts")
    op.drop_table("quiz_questions")
    op.drop_table("quizzes")
    op.drop_table("summary_history")
    op.drop_table("summaries")
    op.drop_column("chat_sessions", "pending_state")
    op.execute("DROP TYPE question_type")
    op.execute("DROP TYPE quiz_difficulty")
    op.execute("DROP TYPE quiz_format")
