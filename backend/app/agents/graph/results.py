"""Helpers for building a sub-agent node's state update, and for checking request quotes."""

import re
from difflib import SequenceMatcher

from app.agents.graph.state import AgentResult, AgentState, Intent, NeedsClarification


def success(
    state: AgentState,
    agent: Intent,
    message: str,
    *,
    content: str | None = None,
    kind: str | None = None,
    follow_ups: list[str] | None = None,
    helpers: list[str] | None = None,
) -> dict:
    """Appends a result. `kind` defaults to the orchestrator's `delegation_kind`."""
    entry: AgentResult = {
        "agent": agent,
        "kind": kind or state.get("delegation_kind") or agent,
        "summary": message,
        "content": content if content is not None else message,
    }
    if follow_ups:
        entry["follow_ups"] = follow_ups
    if helpers:
        entry["helpers"] = helpers
    return {"agent_results": [*state["agent_results"], entry], "needs_clarification": None}


def clarify(agent: Intent, reason: str, suggested_question: str) -> dict:
    pending: NeedsClarification = {
        "pending_agent": agent,
        "reason": reason,
        "suggested_question": suggested_question,
    }
    return {"needs_clarification": pending}


def task_message(state: AgentState) -> str:
    """The task for a specialist: the orchestrator's focus (if any) plus the latest message."""
    focus = state["delegation_focus"]
    if not focus:
        return state["raw_message"]
    return (
        f"Your task (your part of the student's request): {focus}\n\n"
        f"The student's latest message, for any details it gives: {state['raw_message']}"
    )


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def quote_found(quote: str, sources: list[str]) -> bool:
    """Whether the quote comes from one of the sources, tolerating small typos."""
    quoted = words(quote)
    if not quoted:
        return False
    if any(" ".join(quoted) in " ".join(words(source)) for source in sources):
        return True
    # Word by word, as a quote may mix the paused request with the reply.
    source_words = [word for source in sources for word in words(source)]
    matched = sum(1 for q in quoted if any(_similar(q, w) for w in source_words))
    return matched / len(quoted) >= 0.75


def _similar(a: str, b: str) -> bool:
    return a == b or (min(len(a), len(b)) > 3 and SequenceMatcher(None, a, b).ratio() >= 0.8)
