"""Study Planner tables: planner memory (event resolutions, preferences) and the plans."""

import enum
from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class StudyPlanStatus(enum.StrEnum):
    draft = "draft"
    confirmed = "confirmed"


class CalendarEventResolution(Base):
    """Which course and materials a calendar exam or deadline covers.

    Keyed by (user_id, google_event_id, event_date), so each event instance is asked about once.
    """

    __tablename__ = "calendar_event_resolutions"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "google_event_id", "event_date", name="uq_resolution_user_event_date"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    google_event_id: Mapped[str] = mapped_column(Text)
    event_date: Mapped[date] = mapped_column(Date)
    event_title: Mapped[str] = mapped_column(Text)  # kept for display; never used for matching
    # Nullable until the student confirms which course the event belongs to.
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=True
    )
    materials_covered: Mapped[str] = mapped_column(Text, default="")
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class StudentPreferences(Base):
    """One row per student, updated in place."""

    __tablename__ = "student_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    preferred_study_time: Mapped[str | None] = mapped_column(Text, nullable=True)
    sleep_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    sleep_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    # IANA zone read from the student's calendar, so sessions land at the right local hour.
    time_zone: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class StudyPlan(Base):
    """A plan for one date range, e.g. "next week"."""

    __tablename__ = "study_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    date_range_start: Mapped[date] = mapped_column(Date)
    date_range_end: Mapped[date] = mapped_column(Date)
    status: Mapped[StudyPlanStatus] = mapped_column(
        Enum(StudyPlanStatus, name="study_plan_status"), default=StudyPlanStatus.draft
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set on a revision of a confirmed plan; confirming it reuses that plan's calendar events.
    replaces_plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("study_plans.id", ondelete="SET NULL"), nullable=True
    )


class StudyPlanSession(Base):
    """One study block. `google_calendar_event_id` is set when the plan is confirmed."""

    __tablename__ = "study_plan_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    study_plan_id: Mapped[int] = mapped_column(
        ForeignKey("study_plans.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    topic: Mapped[str] = mapped_column(Text)
    google_calendar_event_id: Mapped[str | None] = mapped_column(Text, nullable=True)
