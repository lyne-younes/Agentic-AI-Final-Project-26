"""Draft plans and `confirm_plan`, the only function that writes study sessions to the calendar.

Sessions with a stored event id are updated rather than created again. Confirming a revised plan
reuses the replaced plan's events and deletes any left over. `remove_sessions` deletes sessions the
student asks to drop.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp.calendar import CalendarMcpSession
from app.models import Course, StudyPlan, StudyPlanSession, StudyPlanStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DraftSession:
    """One proposed study block, before it exists on the calendar."""

    course_id: int
    start_time: datetime
    end_time: datetime
    topic: str


@dataclass(frozen=True)
class ConfirmationResult:
    written: int
    updated: int
    deleted: int
    failures: list[str]


async def save_draft(
    db: AsyncSession,
    user_id: int,
    *,
    date_range_start: date,
    date_range_end: date,
    sessions: list[DraftSession],
    plan_id: int | None = None,
) -> StudyPlan:
    """Create or overwrite a draft plan. Draft sessions are replaced on each regeneration."""
    plan = None
    if plan_id is not None:
        plan = await db.scalar(
            select(StudyPlan).where(StudyPlan.id == plan_id, StudyPlan.user_id == user_id)
        )
    if plan is None:
        plan = StudyPlan(user_id=user_id)
        db.add(plan)

    if plan.status == StudyPlanStatus.confirmed:
        # A confirmed plan is kept; the revision becomes a new draft that replaces it.
        plan = StudyPlan(user_id=user_id, replaces_plan_id=plan.id)
        db.add(plan)

    plan.date_range_start = date_range_start
    plan.date_range_end = date_range_end
    plan.status = StudyPlanStatus.draft
    await db.flush()

    await db.execute(delete(StudyPlanSession).where(StudyPlanSession.study_plan_id == plan.id))
    db.add_all(
        [
            StudyPlanSession(
                study_plan_id=plan.id,
                course_id=session.course_id,
                start_time=session.start_time,
                end_time=session.end_time,
                topic=session.topic,
            )
            for session in sessions
        ]
    )
    await db.flush()
    return plan


async def sessions_for(db: AsyncSession, plan_id: int) -> list[StudyPlanSession]:
    rows = await db.scalars(
        select(StudyPlanSession)
        .where(StudyPlanSession.study_plan_id == plan_id)
        .order_by(StudyPlanSession.start_time)
    )
    return list(rows)


async def own_event_ids(db: AsyncSession, plan: StudyPlan) -> set[str]:
    """Event ids owned by this plan or the plan it replaces (not counted as busy time)."""
    plan_ids = [plan.id] if plan.replaces_plan_id is None else [plan.id, plan.replaces_plan_id]
    rows = await db.scalars(
        select(StudyPlanSession.google_calendar_event_id).where(
            StudyPlanSession.study_plan_id.in_(plan_ids),
            StudyPlanSession.google_calendar_event_id.is_not(None),
        )
    )
    return {event_id for event_id in rows if event_id}


async def describe_plan(db: AsyncSession, plan: StudyPlan, time_zone: str | None = None) -> str:
    """A compact rendering of a plan's sessions in the student's local time, for the agent."""
    sessions = await sessions_for(db, plan.id)
    if not sessions:
        return "(no sessions)"
    try:
        zone = ZoneInfo(time_zone or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    names = await _course_names(db, {session.course_id for session in sessions})
    lines = []
    for session in sessions:
        course = names.get(session.course_id, "Unknown course")
        start = session.start_time.astimezone(zone)
        end = session.end_time.astimezone(zone)
        on_calendar = (
            f" [event_id={session.google_calendar_event_id}]"
            if session.google_calendar_event_id
            else ""
        )
        lines.append(
            f"- {start:%a %d %b %H:%M}-{end:%H:%M} {course} (course_id={session.course_id}): "
            f"{session.topic}{on_calendar}"
        )
    return "\n".join(lines)


async def _course_names(db: AsyncSession, course_ids: set[int]) -> dict[int, str]:
    if not course_ids:
        return {}
    rows = await db.execute(select(Course.id, Course.name).where(Course.id.in_(course_ids)))
    return {course_id: name for course_id, name in rows.all()}


async def confirm_plan(
    db: AsyncSession,
    *,
    plan: StudyPlan,
    mcp: CalendarMcpSession,
    access_token: str,
    time_zone: str | None = None,
) -> ConfirmationResult:
    """Write a plan's sessions to Google Calendar through MCP and record the event ids.

    For a revision, the replaced plan's events are moved to the new sessions first; leftovers
    are deleted.
    """
    sessions = await sessions_for(db, plan.id)
    names = await _course_names(db, {session.course_id for session in sessions})

    leftovers: list[StudyPlanSession] = []
    if plan.replaces_plan_id is not None:
        leftovers = [
            old
            for old in await sessions_for(db, plan.replaces_plan_id)
            if old.google_calendar_event_id
        ]
        for session in sessions:
            if session.google_calendar_event_id is None and leftovers:
                old = leftovers.pop(0)
                session.google_calendar_event_id = old.google_calendar_event_id
                old.google_calendar_event_id = None

    written = 0
    updated = 0
    deleted = 0
    failures: list[str] = []

    for session in sessions:
        course_name = names.get(session.course_id, "Study")
        title = f"Study: {session.topic} - {course_name}"
        arguments = {
            "title": title,
            "start_time": session.start_time.isoformat(),
            "end_time": session.end_time.isoformat(),
            "description": f"{course_name}: {session.topic}",
        }
        if time_zone:
            arguments["time_zone"] = time_zone

        outcome = None
        if session.google_calendar_event_id:
            outcome = await mcp.call_tool(
                "update_study_session",
                {**arguments, "event_id": session.google_calendar_event_id},
                access_token=access_token,
            )
            if not outcome.is_error:
                updated += 1
            elif outcome.event_gone:
                # The student deleted this event by hand; write the session again below.
                session.google_calendar_event_id = None
                outcome = None
        if outcome is None:
            outcome = await mcp.call_tool(
                "create_study_session", arguments, access_token=access_token
            )
            if not outcome.is_error and isinstance(outcome.content, dict):
                session.google_calendar_event_id = outcome.content.get("event_id")
                written += 1

        if outcome.is_error:
            logger.warning("confirm_plan: %s failed: %s", title, outcome.content)
            failures.append(f"{title}: {outcome.content}")

    for old in leftovers:
        outcome = await mcp.call_tool(
            "delete_study_session",
            {"event_id": old.google_calendar_event_id},
            access_token=access_token,
        )
        if outcome.is_error:
            # Keep the id: confirming this plan again retries the deletion.
            logger.warning("confirm_plan: deleting %s failed: %s", old.topic, outcome.content)
            failures.append(f"Removing old session {old.topic!r}: {outcome.content}")
        else:
            old.google_calendar_event_id = None
            deleted += 1

    if written or updated:
        plan.status = StudyPlanStatus.confirmed
        plan.confirmed_at = datetime.now(UTC)
    # Commit now: the events already exist in Google, so a later failure in this turn must not
    # roll back their stored ids (a retry would create duplicates).
    await db.commit()
    return ConfirmationResult(written=written, updated=updated, deleted=deleted, failures=failures)


@dataclass(frozen=True)
class RemovalResult:
    removed: int
    failures: list[str]


async def remove_sessions(
    db: AsyncSession,
    *,
    user_id: int,
    event_ids: list[str],
    mcp: CalendarMcpSession,
    access_token: str,
) -> RemovalResult:
    """Delete study sessions from the calendar, and from any of the student's plans.

    Works for sessions in no plan too, e.g. left on the calendar after the app's data was reset.
    The MCP server refuses any event that isn't a study session.
    """
    removed: list[str] = []
    failures: list[str] = []
    for event_id in event_ids:
        outcome = await mcp.call_tool(
            "delete_study_session", {"event_id": event_id}, access_token=access_token
        )
        if outcome.is_error:
            logger.warning("remove_sessions: deleting %s failed: %s", event_id, outcome.content)
            failures.append(f"{event_id}: {outcome.content}")
        else:
            removed.append(event_id)

    if removed:
        own_plans = select(StudyPlan.id).where(StudyPlan.user_id == user_id)
        await db.execute(
            delete(StudyPlanSession).where(
                StudyPlanSession.study_plan_id.in_(own_plans),
                StudyPlanSession.google_calendar_event_id.in_(removed),
            )
        )
    # Commit now, as confirm_plan does: the events are already gone from Google.
    await db.commit()
    return RemovalResult(removed=len(removed), failures=failures)


async def latest_plan(db: AsyncSession, user_id: int) -> StudyPlan | None:
    """The plan a bare "confirm" refers to: the student's most recent one."""
    return await db.scalar(
        select(StudyPlan).where(StudyPlan.user_id == user_id).order_by(StudyPlan.id.desc()).limit(1)
    )
