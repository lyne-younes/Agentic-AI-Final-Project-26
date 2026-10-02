"""Unique course names per student, unique material titles per course

Revision ID: 0005
Revises: 0004
Create Date: 2026-09-15

Existing duplicates (case-insensitive) are renamed with a " (2)", " (3)", ... suffix, keeping the
oldest row's name untouched, so the new unique indexes can be created without failing.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DEDUPE_SQL = """
WITH ranked AS (
    SELECT id, row_number() OVER (
        PARTITION BY {partition_by}, lower({name_column}) ORDER BY created_at, id
    ) AS rn
    FROM {table}
)
UPDATE {table}
SET {name_column} = {table}.{name_column} || ' (' || ranked.rn || ')'
FROM ranked
WHERE {table}.id = ranked.id AND ranked.rn > 1
"""


def upgrade() -> None:
    op.execute(_DEDUPE_SQL.format(table="courses", partition_by="user_id", name_column="name"))
    op.execute(
        _DEDUPE_SQL.format(table="materials", partition_by="course_id", name_column="title")
    )

    op.create_index(
        "uq_courses_user_id_lower_name",
        "courses",
        ["user_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "uq_materials_course_id_lower_title",
        "materials",
        ["course_id", sa.text("lower(title)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_materials_course_id_lower_title", table_name="materials")
    op.drop_index("uq_courses_user_id_lower_name", table_name="courses")
