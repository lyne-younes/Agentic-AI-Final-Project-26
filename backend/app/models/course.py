import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class CourseStatus(enum.StrEnum):
    active = "active"
    completed = "completed"


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        # A student's own courses can't share a name (case-insensitive); see 0005_unique_names.
        Index("uq_courses_user_id_lower_name", "user_id", text("lower(name)"), unique=True),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(Text)
    semester: Mapped[str] = mapped_column(Text)
    year: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(Text)
    icon_url: Mapped[str | None] = mapped_column(Text)
    status: Mapped[CourseStatus] = mapped_column(
        Enum(CourseStatus, name="course_status"), server_default=CourseStatus.active.value
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
