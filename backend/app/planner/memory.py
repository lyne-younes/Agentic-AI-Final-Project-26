"""Planner memory that persists across sessions: event resolutions and student preferences."""

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import CalendarEventResolution, StudentPreferences


async def resolutions_for(
    db: AsyncSession, user_id: int, keys: list[tuple[str, date]]
) -> dict[tuple[str, date], CalendarEventResolution]:
    """Saved resolutions for these event instances, matched by (google_event_id, event_date)."""
    if not keys:
        return {}
    event_ids = {event_id for event_id, _ in keys}
    rows = await db.scalars(
        select(CalendarEventResolution).where(
            CalendarEventResolution.user_id == user_id,
            CalendarEventResolution.google_event_id.in_(event_ids),
        )
    )
    wanted = set(keys)
    found = {}
    for row in rows:
        key = (row.google_event_id, row.event_date)
        if key in wanted:
            found[key] = row
    return found


async def save_resolution(
    db: AsyncSession,
    user_id: int,
    *,
    google_event_id: str,
    event_date: date,
    event_title: str,
    course_id: int | None,
    materials_covered: str,
) -> CalendarEventResolution:
    """Remember a resolution, updating in place if this event instance was resolved before."""
    existing = await db.scalar(
        select(CalendarEventResolution).where(
            CalendarEventResolution.user_id == user_id,
            CalendarEventResolution.google_event_id == google_event_id,
            CalendarEventResolution.event_date == event_date,
        )
    )
    if existing is None:
        existing = CalendarEventResolution(
            user_id=user_id, google_event_id=google_event_id, event_date=event_date
        )
        db.add(existing)
    existing.event_title = event_title
    existing.course_id = course_id
    existing.materials_covered = materials_covered
    return existing


async def forget_event(db: AsyncSession, user_id: int, google_event_id: str) -> None:
    """Drop what was remembered about an event that was deleted from the calendar."""
    await db.execute(
        delete(CalendarEventResolution).where(
            CalendarEventResolution.user_id == user_id,
            CalendarEventResolution.google_event_id == google_event_id,
        )
    )


async def get_preferences(db: AsyncSession, user_id: int) -> StudentPreferences | None:
    return await db.scalar(select(StudentPreferences).where(StudentPreferences.user_id == user_id))


async def save_preferences(
    db: AsyncSession,
    user_id: int,
    *,
    preferred_study_time: str | None = None,
    sleep_start: str | None = None,
    sleep_end: str | None = None,
    time_zone: str | None = None,
) -> StudentPreferences:
    """Update the student's preferences in place; only the supplied fields change."""
    from datetime import time

    def _as_time(value: str | None) -> time | None:
        if not value:
            return None
        try:
            return time.fromisoformat(value)
        except ValueError:
            return None

    preferences = await get_preferences(db, user_id)
    if preferences is None:
        preferences = StudentPreferences(user_id=user_id)
        db.add(preferences)

    if preferred_study_time is not None:
        preferences.preferred_study_time = preferred_study_time
    if sleep_start is not None:
        preferences.sleep_start = _as_time(sleep_start)
    if sleep_end is not None:
        preferences.sleep_end = _as_time(sleep_end)
    if time_zone is not None:
        preferences.time_zone = time_zone
    return preferences


def describe_preferences(preferences: StudentPreferences | None) -> str:
    """A short line for the planner's prompt."""
    if preferences is None:
        return "None recorded yet - ask before planning."
    parts = []
    if preferences.preferred_study_time:
        parts.append(f"prefers studying in the {preferences.preferred_study_time}")
    if preferences.sleep_start and preferences.sleep_end:
        parts.append(f"sleeps {preferences.sleep_start:%H:%M}-{preferences.sleep_end:%H:%M}")
    if preferences.time_zone:
        parts.append(f"timezone {preferences.time_zone}")
    return "; ".join(parts) if parts else "None recorded yet - ask before planning."
