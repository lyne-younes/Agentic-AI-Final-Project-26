"""Google Calendar exposed as MCP tools over streamable HTTP.

Stateless: no OAuth flow and no stored credentials. The backend passes the student's access token
on every call. Only study sessions created here (tagged with a private marker) can be updated or
deleted as sessions; any other event is read-only, except that an exam or deadline can be deleted
with delete_exam_event when the student asks.
"""

import os
from typing import Any, Literal, NotRequired, TypedDict

import httpx
from mcp.server import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

CALENDAR_API = (
    os.environ.get("GOOGLE_CALENDAR_API_BASE") or "https://www.googleapis.com/calendar/v3"
)
REQUEST_TIMEOUT = 30.0

# Private extended property that marks study sessions created by this app.
STUDY_TAG = "studyAppSession"

# Error markers the backend recognises: refresh the token, or recreate a deleted event.
AUTH_MARKER = "google-auth-rejected"
EVENT_GONE_MARKER = "calendar-event-gone"

mcp = MCPServer("google-calendar")


class CalendarEvent(TypedDict):
    """One event, flattened to what the planner actually reasons over."""

    event_id: str
    title: str
    description: str
    start: str  # RFC3339 timestamp, or YYYY-MM-DD for an all-day event
    end: str
    all_day: bool
    busy: bool  # False for events marked "free", e.g. all-day reminders
    study_session: bool  # True if this app created it
    calendar_id: str


class BusyPeriod(TypedDict):
    start: str
    end: str


class CreatedEvent(TypedDict):
    event_id: str
    html_link: str


class DeletedEvent(TypedDict):
    event_id: str
    deleted: bool


class _EventTime(TypedDict):
    dateTime: NotRequired[str]
    date: NotRequired[str]
    timeZone: NotRequired[str]


async def _call_google(
    method: Literal["GET", "POST", "PATCH", "DELETE"],
    path: str,
    access_token: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    retry: bool = True,
) -> dict[str, Any]:
    """Calls the Calendar API and maps errors to ToolError. Writes never retry (no duplicates)."""
    if not access_token:
        raise ToolError("access_token is required: the backend must pass the student's token.")

    attempts = 2 if retry else 1
    response = None
    for attempt in range(1, attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.request(
                    method,
                    f"{CALENDAR_API}{path}",
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                    json=json,
                )
            break
        except httpx.HTTPError as exc:
            if attempt == attempts:
                detail = (
                    "Google Calendar didn't respond."
                    if retry
                    else "Google Calendar didn't respond, so the change may not have been saved."
                )
                raise ToolError(f"{detail} ({exc})") from exc

    assert response is not None  # the loop either breaks with a response or raises
    if response.status_code == 401:
        raise ToolError(f"{AUTH_MARKER}: Google rejected the access token.")
    if response.status_code == 403:
        raise ToolError(
            "Google refused the request. The student may not have granted Calendar access."
        )
    if response.status_code in (404, 410):
        raise ToolError(f"{EVENT_GONE_MARKER}: Google Calendar has no such event.")
    if response.status_code >= 400:
        raise ToolError(f"Google Calendar returned {response.status_code}: {response.text[:300]}")

    if response.status_code == 204 or not response.content:
        return {}
    return response.json()


def _is_study_session(raw: dict[str, Any]) -> bool:
    private = (raw.get("extendedProperties") or {}).get("private") or {}
    return bool(private.get(STUDY_TAG))


async def _require_study_session(event_id: str, calendar_id: str, access_token: str) -> None:
    """Refuse to change any event that isn't a study session created by this app."""
    raw = await _call_google("GET", f"/calendars/{calendar_id}/events/{event_id}", access_token)
    if raw.get("status") == "cancelled":
        raise ToolError(f"{EVENT_GONE_MARKER}: the event was deleted.")
    if not _is_study_session(raw):
        raise ToolError(
            "That event isn't a study session created by this app. Exams, deadlines and the "
            "student's own events can't be changed; an exam or deadline the student asks to "
            "remove goes through delete_exam_event."
        )


def _flatten_event(raw: dict[str, Any], calendar_id: str) -> CalendarEvent:
    start: _EventTime = raw.get("start") or {}
    end: _EventTime = raw.get("end") or {}
    return CalendarEvent(
        event_id=raw.get("id", ""),
        title=raw.get("summary", "(no title)"),
        description=raw.get("description", ""),
        start=start.get("dateTime") or start.get("date", ""),
        end=end.get("dateTime") or end.get("date", ""),
        all_day="date" in start,
        busy=raw.get("transparency") != "transparent",
        study_session=_is_study_session(raw),
        calendar_id=calendar_id,
    )


def _event_time(timestamp: str, time_zone: str | None) -> _EventTime:
    # Local time plus the student's time zone, so Google places it correctly.
    value: _EventTime = {"dateTime": timestamp}
    if time_zone:
        value["timeZone"] = time_zone
    return value


@mcp.tool()
async def get_calendar_events(
    access_token: str,
    time_min: str,
    time_max: str,
    calendar_id: str = "primary",
    max_results: int = 100,
) -> list[CalendarEvent]:
    """Read events in a time window. Use this for exams, deadlines and existing commitments.

    Recurring events are expanded into individual instances, so each event_id refers to one
    specific occurrence - which is what a resolution ("this exam covers chapters 1-3") is
    remembered against. Each event reports whether it blocks time (`busy`) and whether this app
    created it as a study session (`study_session`).

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        time_min: Start of the window, RFC3339 (e.g. "2026-09-21T00:00:00Z").
        time_max: End of the window, RFC3339.
        calendar_id: Which calendar to read; defaults to the student's primary calendar.
        max_results: Cap on events returned (1-250).
    """
    payload = await _call_google(
        "GET",
        f"/calendars/{calendar_id}/events",
        access_token,
        params={
            "timeMin": time_min,
            "timeMax": time_max,
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": max(1, min(max_results, 250)),
        },
    )
    return [
        _flatten_event(item, calendar_id)
        for item in payload.get("items", [])
        if item.get("status") != "cancelled"
    ]


@mcp.tool()
async def get_busy_times(
    access_token: str,
    time_min: str,
    time_max: str,
    calendar_id: str = "primary",
) -> list[BusyPeriod]:
    """Read when the student is already booked, to find the gaps a study plan can use.

    Returns only busy intervals - free time is whatever is left between them. Note this reflects
    the calendar as it stands, including any study sessions already written back.

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        time_min: Start of the window, RFC3339.
        time_max: End of the window, RFC3339.
        calendar_id: Which calendar to check; defaults to the student's primary calendar.
    """
    payload = await _call_google(
        "POST",
        "/freeBusy",
        access_token,
        json={"timeMin": time_min, "timeMax": time_max, "items": [{"id": calendar_id}]},
    )
    busy = (payload.get("calendars") or {}).get(calendar_id, {}).get("busy", [])
    return [BusyPeriod(start=slot["start"], end=slot["end"]) for slot in busy]


@mcp.tool()
async def create_study_session(
    access_token: str,
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
    calendar_id: str = "primary",
    time_zone: str | None = None,
) -> CreatedEvent:
    """Write one confirmed study session to the calendar. Returns the event_id to store.

    It always tags what it creates as a study session. For an exam or deadline the student asks
    to add, use create_exam_event instead. Store the returned event_id so a later revision
    updates this same event.

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        title: Event title, e.g. "Study: Chapter 3 - Calculus".
        start_time: Session start, RFC3339.
        end_time: Session end, RFC3339.
        description: Optional note about what to cover.
        calendar_id: Which calendar to write to; defaults to the student's primary calendar.
        time_zone: IANA zone (e.g. "Europe/Berlin"); omit if the timestamps carry an offset.
    """
    if not title.strip():
        raise ToolError("title can't be empty.")
    payload = await _call_google(
        "POST",
        f"/calendars/{calendar_id}/events",
        access_token,
        json={
            "summary": title.strip()[:200],
            "description": description[:1000] or "Study session from your study assistant.",
            "start": _event_time(start_time, time_zone),
            "end": _event_time(end_time, time_zone),
            "extendedProperties": {"private": {STUDY_TAG: "1"}},
        },
        retry=False,
    )
    return CreatedEvent(event_id=payload.get("id", ""), html_link=payload.get("htmlLink", ""))


@mcp.tool()
async def create_exam_event(
    access_token: str,
    title: str,
    start_time: str,
    end_time: str,
    description: str = "",
    calendar_id: str = "primary",
    time_zone: str | None = None,
) -> CreatedEvent:
    """Add an exam or deadline to the calendar, only when the student explicitly asks for it.

    The event is created as the student's own, without the study-session tag, so reading the
    calendar back treats it as a real commitment to plan around. It can't be changed through this
    server afterwards, only deleted with delete_exam_event if the student asks.

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        title: Event title naming the course, e.g. "LangGraph Exam" or "Calculus Assignment 2 due".
        start_time: Start, RFC3339. For a deadline, the time it is due.
        end_time: End, RFC3339. For a deadline, a short slot after the due time is fine.
        description: Optional note, e.g. what the exam covers.
        calendar_id: Which calendar to write to; defaults to the student's primary calendar.
        time_zone: IANA zone (e.g. "Europe/Berlin"); omit if the timestamps carry an offset.
    """
    if not title.strip():
        raise ToolError("title can't be empty.")
    payload = await _call_google(
        "POST",
        f"/calendars/{calendar_id}/events",
        access_token,
        json={
            "summary": title.strip()[:200],
            "description": description[:1000],
            "start": _event_time(start_time, time_zone),
            "end": _event_time(end_time, time_zone),
        },
        retry=False,
    )
    return CreatedEvent(event_id=payload.get("id", ""), html_link=payload.get("htmlLink", ""))


@mcp.tool()
async def delete_exam_event(
    access_token: str,
    event_id: str,
    calendar_id: str = "primary",
) -> DeletedEvent:
    """Delete an exam or deadline from the calendar, only when the student explicitly asks.

    Find the event first with get_calendar_events, so event_id is the one the student named.
    Refused for study sessions: those change only through the study plan.

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        event_id: The event's id, as get_calendar_events returned it.
        calendar_id: Which calendar the event lives on.
    """
    raw = await _call_google("GET", f"/calendars/{calendar_id}/events/{event_id}", access_token)
    if raw.get("status") == "cancelled":
        raise ToolError(f"{EVENT_GONE_MARKER}: the event was already deleted.")
    if _is_study_session(raw):
        raise ToolError(
            "That event is a study session from the study plan. Change the plan instead of "
            "deleting it here."
        )
    await _call_google(
        "DELETE", f"/calendars/{calendar_id}/events/{event_id}", access_token, retry=False
    )
    return DeletedEvent(event_id=event_id, deleted=True)


@mcp.tool()
async def update_study_session(
    access_token: str,
    event_id: str,
    title: str | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    description: str | None = None,
    calendar_id: str = "primary",
    time_zone: str | None = None,
) -> CalendarEvent:
    """Move or relabel a study session already on the calendar, by its stored event_id.

    Updating rather than recreating is what stops a revised plan leaving duplicate or orphaned
    events behind. Refused for any event that isn't a study session this app created.

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        event_id: The id returned by create_study_session.
        title: New title, if changing.
        start_time: New start, RFC3339, if changing.
        end_time: New end, RFC3339, if changing.
        description: New description, if changing.
        calendar_id: Which calendar the event lives on.
        time_zone: IANA zone for changed timestamps.
    """
    changes: dict[str, Any] = {}
    if title is not None:
        changes["summary"] = title.strip()[:200]
    if description is not None:
        changes["description"] = description[:1000]
    if start_time is not None:
        changes["start"] = _event_time(start_time, time_zone)
    if end_time is not None:
        changes["end"] = _event_time(end_time, time_zone)
    if not changes:
        raise ToolError("Nothing to update: pass at least one field to change.")

    await _require_study_session(event_id, calendar_id, access_token)
    payload = await _call_google(
        "PATCH",
        f"/calendars/{calendar_id}/events/{event_id}",
        access_token,
        json=changes,
        retry=False,
    )
    return _flatten_event(payload, calendar_id)


@mcp.tool()
async def delete_study_session(
    access_token: str,
    event_id: str,
    calendar_id: str = "primary",
) -> DeletedEvent:
    """Remove a study session that is no longer part of the plan.

    Refused for any event that isn't a study session this app created. A session the student
    already deleted by hand counts as removed.

    Args:
        access_token: The student's valid Google OAuth access token, supplied by the backend.
        event_id: The id returned by create_study_session.
        calendar_id: Which calendar the event lives on.
    """
    try:
        await _require_study_session(event_id, calendar_id, access_token)
        await _call_google(
            "DELETE", f"/calendars/{calendar_id}/events/{event_id}", access_token, retry=False
        )
    except ToolError as exc:
        if EVENT_GONE_MARKER not in str(exc):
            raise
    return DeletedEvent(event_id=event_id, deleted=True)


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "3333")),
        stateless_http=True,
    )
