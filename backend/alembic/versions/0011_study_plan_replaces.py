"""Study plans: replaces_plan_id, linking a revision to the confirmed plan it replaces

Revision ID: 0011
Revises: 0010
Create Date: 2026-09-27 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | Sequence[str] | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("study_plans", sa.Column("replaces_plan_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f("fk_study_plans_replaces_plan_id_study_plans"),
        "study_plans",
        "study_plans",
        ["replaces_plan_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_study_plans_replaces_plan_id_study_plans"), "study_plans", type_="foreignkey"
    )
    op.drop_column("study_plans", "replaces_plan_id")
