"""Shared graph state.

Rebuilt every turn, except the resume-state fields, which are saved to
`chat_sessions.pending_state` while waiting for a clarification answer.
"""

from typing import Literal, NotRequired, TypedDict

Intent = Literal["qa_agent", "study_tools_agent", "summary_agent", "study_planner_agent"]
ContextStatus = Literal["empty_course", "not_ready", "ok"]


class NeedsClarification(TypedDict):
    pending_agent: Intent | None  # None when the orchestrator asks on its own initiative
    reason: str
    suggested_question: str


class AgentResult(TypedDict):
    agent: Intent
    kind: str  # what the delegation was for, e.g. "quiz", "flashcards", "summary"
    summary: str  # short, student-facing confirmation
    content: str  # fuller output, usable as input for a follow-up delegation
    follow_ups: NotRequired[list[str]]  # Q&A only: suggested next questions
    helpers: NotRequired[list[str]]  # other agents that worked on this result, e.g. the verifier


class StudyDraft(TypedDict):
    """A quiz or flashcard set waiting for verification before it is saved."""

    kind: Literal["quiz", "flashcards"]
    title: str
    format: str | None  # quiz only
    difficulty: str | None  # quiz only
    count: int  # how many the student asked for (or the default)
    candidates: list[dict]  # generated this round, not yet verified
    accepted: list[dict]  # verified; only these are ever saved
    rejected: list[str]  # question texts / card fronts that failed, so they aren't generated again
    rounds: int  # generation rounds so far, including the first


class AgentState(TypedDict):
    # Rebuilt every turn.
    messages: list[tuple[str, str]]  # (role, content) conversation history, oldest first
    course_id: int | None  # None for a global study-planner session
    session_id: int
    raw_message: str  # the student's latest message, unmodified

    # The orchestrator's notes on what it delegated this turn and what came back.
    scratchpad: list[tuple[str, str]]
    orchestrator_steps: int  # loop guard

    # The orchestrator's current delegation.
    pending_delegation: Intent | None
    retrieval_query: str
    delegation_focus: str  # which part of the student's message this delegation is for
    use_previous_result: bool  # use the previous result's content instead of a fresh search
    delegation_kind: str  # "summary", "quiz"/"flashcards"/"unclear", "answer:<focus>" or "plan"
    done: bool  # the orchestrator decided to stop delegating

    context_status: ContextStatus
    retrieved_context: str

    # Only set between study_tools_agent and verifier_agent.
    study_draft: StudyDraft | None

    # The clarification this turn is answering, or None on a fresh request.
    resumed_from: NeedsClarification | None

    # Resume state, saved to chat_sessions.pending_state while waiting for a clarification.
    needs_clarification: NeedsClarification | None
    agent_results: list[AgentResult]  # all results for the current request
    reported_count: int  # how many of agent_results the student has already been told about
    request_message: str  # the message that started the current request

    # Set by ask_clarification / compose_response.
    final_message: str | None
    handled_by: list[str]  # the agents whose results this turn's reply reports
    follow_ups: list[str]  # suggested next questions for a finished turn (compose_response)


RESUME_STATE_FIELDS = (
    "needs_clarification",
    "agent_results",
    "reported_count",
    "request_message",
)
