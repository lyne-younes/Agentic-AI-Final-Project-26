"""Study planner: study_plans, study_plan_sessions, calendar_event_resolutions, student_preferences

Revision ID: 0007
Revises: 0006
Create Date: 2026-09-19 14:55:24.264571

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "student_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preferred_study_time", sa.Text(), nullable=True),
        sa.Column("sleep_start", sa.Time(), nullable=True),
        sa.Column("sleep_end", sa.Time(), nullable=True),
        sa.Column("time_zone", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_student_preferences_user_id"), "student_preferences", ["user_id"], unique=True
    )
    op.create_table(
        "study_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date_range_start", sa.Date(), nullable=False),
        sa.Column("date_range_end", sa.Date(), nullable=False),
        sa.Column(
            "status", sa.Enum("draft", "confirmed", name="study_plan_status"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_study_plans_user_id"), "study_plans", ["user_id"], unique=False)
    op.create_table(
        "calendar_event_resolutions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("google_event_id", sa.Text(), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("event_title", sa.Text(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("materials_covered", sa.Text(), nullable=False),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "google_event_id", "event_date", name="uq_resolution_user_event_date"
        ),
    )
    op.create_index(
        op.f("ix_calendar_event_resolutions_user_id"),
        "calendar_event_resolutions",
        ["user_id"],
        unique=False,
    )
    op.create_table(
        "study_plan_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("study_plan_id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("google_calendar_event_id", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["study_plan_id"], ["study_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_study_plan_sessions_study_plan_id"),
        "study_plan_sessions",
        ["study_plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_study_plan_sessions_study_plan_id"), table_name="study_plan_sessions")
    op.drop_table("study_plan_sessions")
    op.drop_index(
        op.f("ix_calendar_event_resolutions_user_id"), table_name="calendar_event_resolutions"
    )
    op.drop_table("calendar_event_resolutions")
    op.drop_index(op.f("ix_study_plans_user_id"), table_name="study_plans")
    op.drop_table("study_plans")
    op.drop_index(op.f("ix_student_preferences_user_id"), table_name="student_preferences")
    op.drop_table("student_preferences")
    op.execute("DROP TYPE study_plan_status")
