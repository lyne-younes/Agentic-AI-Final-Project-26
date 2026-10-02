"""Runs one turn of the orchestrator graph for the chat endpoint.

Builds the initial state (resuming from `session.pending_state` after a clarification) and updates
`session.pending_state`. The caller commits it together with the chat messages.
"""

from dataclasses import dataclass, field
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph.graph import build_graph
from app.agents.graph.state import RESUME_STATE_FIELDS, AgentState
from app.models import ChatSession, Course, User


@dataclass(frozen=True)
class TurnResult:
    status: Literal["done", "needs_clarification"]
    message: str
    handled_by: list[str]
    follow_ups: list[str] = field(default_factory=list)  # only on a finished ("done") turn


async def run_turn(
    db: AsyncSession,
    session: ChatSession,
    course: Course | None,
    user: User,
    history: list[tuple[str, str]],
    raw_message: str,
) -> TurnResult:
    initial = _initial_state(session, course, history, raw_message)
    graph = build_graph(db, course, user)
    final_state: AgentState = await graph.ainvoke(initial)

    clarification = final_state.get("needs_clarification")
    if clarification:
        session.pending_state = {field: final_state[field] for field in RESUME_STATE_FIELDS}
        return TurnResult(
            "needs_clarification", final_state["final_message"], final_state["handled_by"]
        )

    session.pending_state = None
    return TurnResult(
        "done",
        final_state["final_message"],
        final_state["handled_by"],
        final_state.get("follow_ups") or [],
    )


def _initial_state(
    session: ChatSession, course: Course | None, history: list[tuple[str, str]], raw_message: str
) -> AgentState:
    base: AgentState = {
        "messages": history,
        "course_id": course.id if course else None,
        "session_id": session.id,
        "raw_message": raw_message,
        "scratchpad": [],
        "orchestrator_steps": 0,
        "pending_delegation": None,
        "retrieval_query": "",
        "delegation_focus": "",
        "use_previous_result": False,
        "delegation_kind": "",
        "done": False,
        "context_status": "ok",
        "retrieved_context": "",
        "study_draft": None,
        "resumed_from": None,
        "needs_clarification": None,
        "agent_results": [],
        "reported_count": 0,
        "request_message": raw_message,
        "final_message": None,
        "handled_by": [],
        "follow_ups": [],
    }
    pending = session.pending_state
    if pending:
        base.update({field: pending.get(field, base[field]) for field in RESUME_STATE_FIELDS})
        base["resumed_from"] = base["needs_clarification"]
    return base
