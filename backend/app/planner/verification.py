"""Plan verifier: rule checks (in code, not a model) a study plan must pass before it is saved
or confirmed.

A session must not overlap sleep hours, a busy timed calendar event or another session, fall
outside the plan's dates, or start in the past. All-day events and the plan's own events are not
counted as busy.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.mcp.calendar import CalendarMcpSession
from app.planner.plans import DraftSession

NAME = "plan_verifier"


@dataclass(frozen=True)
class BusyEvent:
    title: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class SleepHours:
    start: time
    end: time
    zone: ZoneInfo


def find_conflicts(
    sessions: list[DraftSession],
    *,
    date_range_start: date,
    date_range_end: date,
    now: datetime,
    busy: Iterable[BusyEvent] = (),
    sleep: SleepHours | None = None,
    zone: ZoneInfo | None = None,
) -> list[str]:
    """Every rule each session breaks, as sentences. Empty means the plan passes."""
    local = zone or ZoneInfo("UTC")
    busy = list(busy)
    conflicts: list[str] = []
    for number, session in enumerate(sessions, start=1):
        label = f"Session {number} ({_describe(session.start_time, session.end_time, local)})"
        if session.end_time <= session.start_time:
            conflicts.append(f"{label} ends before it starts.")
            continue
        if session.start_time < now:
            conflicts.append(f"{label} starts in the past.")
        first_day = session.start_time.astimezone(local).date()
        last_day = session.end_time.astimezone(local).date()
        if first_day < date_range_start or last_day > date_range_end:
            conflicts.append(
                f"{label} is outside the plan's dates ({date_range_start} to {date_range_end})."
            )
        if sleep and _overlaps_sleep(session, sleep):
            conflicts.append(
                f"{label} overlaps the student's sleep hours "
                f"({sleep.start:%H:%M}-{sleep.end:%H:%M})."
            )
        for event in busy:
            if _overlap(session.start_time, session.end_time, event.start, event.end):
                conflicts.append(
                    f'{label} overlaps the calendar event "{event.title}" '
                    f"({_describe(event.start, event.end, local)})."
                )
        for other_number, other in enumerate(sessions[number:], start=number + 1):
            if other.end_time > other.start_time and _overlap(
                session.start_time, session.end_time, other.start_time, other.end_time
            ):
                conflicts.append(f"{label} overlaps session {other_number}.")
    return conflicts


async def busy_events(
    mcp: CalendarMcpSession,
    access_token: str,
    sessions: list[DraftSession],
    *,
    ignore_event_ids: set[str],
) -> list[BusyEvent]:
    """The calendar's timed, busy events across the sessions' span, read over MCP."""
    if not sessions:
        return []
    window_start = min(session.start_time for session in sessions)
    window_end = max(session.end_time for session in sessions)
    outcome = await mcp.call_tool(
        "get_calendar_events",
        {"time_min": _rfc3339(window_start), "time_max": _rfc3339(window_end)},
        access_token=access_token,
    )
    if outcome.is_error or not isinstance(outcome.content, list):
        raise CalendarReadError(str(outcome.content))
    events = []
    for raw in outcome.content:
        event = _busy_event(raw, ignore_event_ids)
        if event is not None:
            events.append(event)
    return events


class CalendarReadError(RuntimeError):
    """The calendar answered, but not with a list of events the check can use."""


def sleep_hours(preferences: Any, zone: ZoneInfo) -> SleepHours | None:
    """The student's stored sleep hours, or None if not given yet."""
    start = getattr(preferences, "sleep_start", None)
    end = getattr(preferences, "sleep_end", None)
    if start is None or end is None or start == end:
        return None
    return SleepHours(start=start, end=end, zone=zone)


def student_zone(preferences: Any) -> ZoneInfo:
    try:
        return ZoneInfo(getattr(preferences, "time_zone", None) or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def _busy_event(raw: Any, ignore_event_ids: set[str]) -> BusyEvent | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("all_day") or raw.get("busy") is False:
        return None
    if raw.get("event_id") in ignore_event_ids:
        return None
    try:
        start = _parse(str(raw["start"]))
        end = _parse(str(raw["end"]))
    except (KeyError, ValueError):
        return None
    return BusyEvent(title=str(raw.get("title") or "(no title)"), start=start, end=end)


def _overlaps_sleep(session: DraftSession, sleep: SleepHours) -> bool:
    """Checks each night the session could touch, including sleep hours past midnight."""
    first = session.start_time.astimezone(sleep.zone).date() - timedelta(days=1)
    last = session.end_time.astimezone(sleep.zone).date()
    day = first
    while day <= last:
        start = datetime.combine(day, sleep.start, tzinfo=sleep.zone)
        end_day = day + timedelta(days=1) if sleep.end <= sleep.start else day
        end = datetime.combine(end_day, sleep.end, tzinfo=sleep.zone)
        if _overlap(session.start_time, session.end_time, start, end):
            return True
        day += timedelta(days=1)
    return False


def _overlap(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _describe(start: datetime, end: datetime, zone: ZoneInfo) -> str:
    local_start, local_end = start.astimezone(zone), end.astimezone(zone)
    return f"{local_start:%a %d %b %H:%M}-{local_end:%H:%M}"


def _parse(timestamp: str) -> datetime:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp without an offset: {timestamp}")
    return parsed


def _rfc3339(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
