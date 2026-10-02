"""orchestrator node: the supervisor.

Runs again after every delegation and picks one action each time: delegate to a specialist, ask
the student, or finish. Each decision is checked in code (no repeats, creating content needs an
explicit request, no finishing before delegating); a rejected decision goes back to the model.

Planner sessions have only one specialist, so they skip the model call.
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.agents.graph import results
from app.agents.graph.state import AgentResult, AgentState, Intent, NeedsClarification
from app.models import Course, Material

logger = logging.getLogger(__name__)

MAX_ORCHESTRATOR_STEPS = 6
MAX_DECISION_RETRIES = 2  # re-asks after a rejected decision, per orchestrator step
MAX_LISTED_MATERIALS = 50
MAX_RESULT_CHARS = 300

VALID_INTENTS: tuple[Intent, ...] = ("qa_agent", "study_tools_agent", "summary_agent")
CREATING_INTENTS: tuple[Intent, ...] = ("study_tools_agent", "summary_agent")
STUDY_TOOL_KINDS = ("quiz", "flashcards", "unclear")
DELEGATE_TOOL_PREFIX = "delegate_to_"
ASK_TOOL_NAME = "ask_student"
FINISH_TOOL_NAME = "finish"

FALLBACK_QUESTION = "Could you say a bit more about what you'd like?"

AGENT_DESCRIPTIONS = {
    "qa_agent": (
        "explains and answers questions about this course's material, and questions about this "
        "conversation itself (e.g. what was generated earlier). Creates and saves nothing."
    ),
    "study_tools_agent": (
        "creates and saves ONE new quiz or ONE new flashcard set per delegation, from this "
        "course's materials."
    ),
    "summary_agent": (
        "writes the course summary from its materials, or rewrites it as the student asks (e.g. "
        "shorter, more detail on a topic), and saves it, replacing the saved one."
    ),
}

_QUERY = {"type": "string", "description": "What to search this course's materials for."}
_FOCUS = {
    "type": "string",
    "description": (
        "Which part of the student's message this delegation is for, e.g. 'explain the first "
        "point'. Set it whenever the message has several parts, so the specialist does only its "
        "own part. If the delegation acts on feedback the student gave earlier (e.g. they said "
        "the summary was too long and now say 'ok, fix it'), restate that feedback here - the "
        "specialist works from this, not from the whole conversation."
    ),
}
_USE_PREVIOUS = {
    "type": "boolean",
    "description": (
        "True only if this should work from the most recent completed result (listed under "
        "'Completed for this request', e.g. flashcard the summary just generated), instead of "
        "searching the course materials fresh."
    ),
}
_REQUEST_QUOTE = {
    "type": "string",
    "description": (
        "Copy, word for word, the words in the student's latest message (or the paused request) "
        "that ask you to create this now, e.g. 'make an easy quiz'."
    ),
}
_STUDY_TOOL = {
    "type": "string",
    "enum": list(STUDY_TOOL_KINDS),
    "description": (
        "Which single item to create. 'unclear' only if the student asked for study material "
        "without saying whether they want a quiz or flashcards."
    ),
}


def _delegate_tool(intent: Intent) -> dict[str, Any]:
    properties: dict[str, Any] = {"query": _QUERY}
    required = ["query"]
    if intent == "study_tools_agent":
        properties["tool"] = _STUDY_TOOL
        required.append("tool")
    if intent in CREATING_INTENTS:
        properties["request_quote"] = _REQUEST_QUOTE
        required.append("request_quote")
    properties["focus"] = _FOCUS
    properties["use_previous_result"] = _USE_PREVIOUS
    return {
        "type": "function",
        "function": {
            "name": f"{DELEGATE_TOOL_PREFIX}{intent}",
            "description": f"Delegate to {intent}, which {AGENT_DESCRIPTIONS[intent]}",
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


ASK_TOOL = {
    "type": "function",
    "function": {
        "name": ASK_TOOL_NAME,
        "description": (
            "Ask the student one clarifying question and pause this turn. Only for when you "
            "yourself can't tell what the student wants."
        ),
        "parameters": {
            "type": "object",
            "properties": {"question": {"type": "string", "description": "In Markdown."}},
            "required": ["question"],
        },
    },
}

FINISH_TOOL = {
    "type": "function",
    "function": {
        "name": FINISH_TOOL_NAME,
        "description": (
            "Stop delegating - every part of the student's latest message has been handled. Does "
            "not write the reply itself; that's composed afterward from what you've delegated."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
}

TOOLS = [_delegate_tool(intent) for intent in VALID_INTENTS] + [ASK_TOOL, FINISH_TOOL]

SYSTEM_PROMPT = """\
You are the orchestrator for a student's course assistant. You never talk to the student \
directly - the only ways anything reaches them are the ask_student question, or the reply that \
gets composed from your specialists' results once you finish.

This chat belongs to one course:
Course: {name} ({semester} {year})
Description: {description}
Materials in this course:
{materials}

The student's other courses (each has its own chat):
{other_courses}

Specialists:
- qa_agent: {qa}
- study_tools_agent: {study_tools}
- summary_agent: {summary}

Rules:
1. Act only on the student's latest message{resume_rule}. Earlier requests in the conversation \
were already handled: never redo them, and never create anything because of them. The assistant \
messages in the conversation describe work that really happened.
2. summary_agent and study_tools_agent create and save new content. Delegate to them only when \
the latest message explicitly asks you to create it now (e.g. "summarize the course", "make \
flashcards", "quiz me"), and pass request_quote with the student's exact words asking for it. \
An explicit request in the latest message to change something made earlier is a new request too: \
"make the summary shorter" goes to summary_agent, "another quiz, but harder" to \
study_tools_agent. Questions - "what are the key ideas?", "explain point 7", "give me an \
overview", "why didn't you make the quiz?" - go to qa_agent, never to a creating specialist.
3. One item per delegation, each at most once per request. For "flashcards and a quiz" delegate to \
study_tools_agent twice: tool="flashcards", then tool="quiz". Never delegate anything listed under \
"Completed for this request" again.
4. A message with several parts: delegate each part to the specialist that owns it, one at a time, \
and say which part with focus. Only qa_agent explains or answers. Set use_previous_result when a \
part builds on the most recent completed result (e.g. "summarize the course and quiz me on it": \
the quiz uses the summary) - it stays available after a clarification question too.
5. A request about a different subject - one of the student's other courses, or anything unrelated \
to this course - goes to qa_agent only; it tells the student where to go. Never create a summary, \
quiz or flashcards for it.
6. ask_student only when you yourself can't tell what the student wants. The specialists ask for \
their own missing details (e.g. quiz format and difficulty) - don't ask for those yourself.
7. finish once every part of the latest message{resume_rule} has been handled. Delegate at least \
once before finishing.

Completed for this request (do not repeat):
{completed}
{resume_context}\
"""

RESUME_RULE = " and the paused request it replies to"
RESUME_CONTEXT = """
You paused the student's request "{request}" to ask them: "{question}" ({reason}). Their latest \
message is the reply: carry on with the parts of that request not completed above. If the reply \
is instead a new, unrelated request, handle that instead.\
"""


async def orchestrator_agent(
    state: AgentState, *, db: AsyncSession, course: Course | None
) -> dict[str, Any]:
    if course is None:
        return _global_step(state)
    return await _course_step(state, db, course)


def _global_step(state: AgentState) -> dict[str, Any]:
    """Planner session: delegate on the first visit, finish (or let it ask) on the second.

    The first visit clears needs_clarification left over from the previous turn.
    """
    if state["orchestrator_steps"] > 0:
        if len(state["agent_results"]) > state["reported_count"]:
            return {"done": True}
        return {}
    return {
        "pending_delegation": "study_planner_agent",
        "delegation_kind": "plan",
        "use_previous_result": False,
        "needs_clarification": None,
        "orchestrator_steps": 1,
    }


async def _course_step(state: AgentState, db: AsyncSession, course: Course) -> dict[str, Any]:
    if state["needs_clarification"] and state["orchestrator_steps"] > 0:
        # A specialist asked for clarification this turn: pause.
        logger.info("Course %s: pausing for a specialist's clarification", course.id)
        return {}

    step = state["orchestrator_steps"] + 1
    if step > MAX_ORCHESTRATOR_STEPS:
        logger.warning("Course %s: orchestrator hit the %s-step limit", course.id, step - 1)
        return {"done": True, "orchestrator_steps": step, "needs_clarification": None}

    materials = list(
        await db.scalars(
            select(Material).where(Material.course_id == course.id).order_by(Material.created_at)
        )
    )
    other_courses = list(
        await db.scalars(
            select(Course)
            .where(Course.user_id == course.user_id, Course.id != course.id)
            .order_by(Course.name)
        )
    )
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _system_prompt(course, materials, other_courses, state)},
        *({"role": role, "content": content} for role, content in state["messages"]),
        {"role": "user", "content": state["raw_message"]},
        *({"role": role, "content": content} for role, content in state["scratchpad"]),
    ]

    for attempt in range(MAX_DECISION_RETRIES + 1):
        reply = await llm.complete(messages, tools=TOOLS, tool_choice="required")
        call = reply.tool_calls[0] if reply.tool_calls else None
        decision, rejection = _check(state, call, step)
        if decision is not None:
            logger.info("Course %s: orchestrator step %s: %s", course.id, step, _describe(call))
            return decision
        logger.info(
            "Course %s: orchestrator step %s rejected (attempt %s): %s",
            course.id,
            step,
            attempt + 1,
            rejection,
        )
        messages.append(
            {"role": "user", "content": f"(Your decision was rejected: {rejection} Decide again.)"}
        )

    logger.warning("Course %s: orchestrator made no acceptable decision", course.id)
    if _new_results(state):
        return {"done": True, "orchestrator_steps": step, "needs_clarification": None}
    return _default_delegation(step)


def _check(
    state: AgentState, call: llm.ToolCall | None, step: int
) -> tuple[dict[str, Any] | None, str | None]:
    """(state update, None) for an acceptable decision, or (None, why it was rejected)."""
    if call is None:
        return None, "Call exactly one of your tools."

    if call.name == ASK_TOOL_NAME:
        return _handle_ask(state, call.arguments, step), None

    if call.name == FINISH_TOOL_NAME:
        if not _new_results(state):
            return None, (
                "Nothing has been delegated for the student's latest message yet. Delegate to a "
                "specialist first - qa_agent if nothing else fits."
            )
        return {"done": True, "orchestrator_steps": step, "needs_clarification": None}, None

    intent = call.name.removeprefix(DELEGATE_TOOL_PREFIX)
    if not call.name.startswith(DELEGATE_TOOL_PREFIX) or intent not in VALID_INTENTS:
        return None, f"{call.name} is not one of your tools."

    arguments = call.arguments
    focus = str(arguments.get("focus") or "").strip()
    kind = _delegation_kind(intent, arguments, focus)
    if kind is None:
        return None, "Set tool to quiz, flashcards or unclear."

    earlier = _find_result(state["agent_results"], intent, kind)
    if earlier is not None:
        return None, (
            f"{intent} already did this for this request ({earlier['summary']}). Don't repeat "
            "it: delegate a part that isn't done yet, or finish."
        )

    if intent in CREATING_INTENTS:
        quote = str(arguments.get("request_quote") or "").strip()
        sources = [state["raw_message"]]
        if state["resumed_from"]:
            sources.append(state["request_message"])
        if not results.quote_found(quote, sources):
            return None, (
                f'request_quote "{quote}" is not in the student\'s latest message. Only delegate '
                f"to {intent} when the latest message itself explicitly asks to create this; "
                "questions go to qa_agent."
            )

    return _handle_delegate(state, intent, kind, focus, arguments, step), None


def _delegation_kind(intent: Intent, arguments: dict[str, Any], focus: str) -> str | None:
    if intent == "study_tools_agent":
        tool = arguments.get("tool")
        return tool if tool in STUDY_TOOL_KINDS else None
    if intent == "summary_agent":
        return "summary"
    return "answer:" + " ".join(results.words(focus))


def _find_result(results: list[AgentResult], intent: Intent, kind: str) -> AgentResult | None:
    if kind == "unclear":  # study tools will ask which one; nothing to compare yet
        return None
    return next(
        (r for r in results if r["agent"] == intent and r.get("kind", r["agent"]) == kind), None
    )


def _new_results(state: AgentState) -> bool:
    """Whether this turn produced any result of its own (a resumed turn inherits earlier ones)."""
    return len(state["agent_results"]) > state["reported_count"]


def _describe(call: llm.ToolCall | None) -> str:
    return f"{call.name} {call.arguments}" if call else "(no tool call)"


def _default_delegation(step: int) -> dict[str, Any]:
    """Fallback when no decision was accepted: qa_agent, which creates nothing."""
    return {
        "pending_delegation": "qa_agent",
        "delegation_kind": "answer:",
        "retrieval_query": "",
        "delegation_focus": "",
        "use_previous_result": False,
        "needs_clarification": None,
        "orchestrator_steps": step,
    }


def _handle_delegate(
    state: AgentState,
    intent: Intent,
    kind: str,
    focus: str,
    arguments: dict[str, Any],
    step: int,
) -> dict[str, Any]:
    query = str(arguments.get("query") or "").strip()
    what = f" ({kind})" if intent == "study_tools_agent" else ""
    note = f"Delegating to {intent}{what}: {focus or query or '(no query given)'}"
    return {
        "pending_delegation": intent,
        "delegation_kind": kind,
        "retrieval_query": query,
        "delegation_focus": focus,
        "use_previous_result": bool(arguments.get("use_previous_result", False)),
        "needs_clarification": None,
        "scratchpad": [*state["scratchpad"], ("assistant", note)],
        "orchestrator_steps": step,
    }


def _handle_ask(state: AgentState, arguments: dict[str, Any], step: int) -> dict[str, Any]:
    question = str(arguments.get("question") or "").strip() or FALLBACK_QUESTION
    clarification: NeedsClarification = {
        "pending_agent": None,
        "reason": "the orchestrator requested clarification",
        "suggested_question": question,
    }
    return {"needs_clarification": clarification, "orchestrator_steps": step}


def _system_prompt(
    course: Course, materials: list[Material], other_courses: list[Course], state: AgentState
) -> str:
    listed = "\n".join(f"- {material.title}" for material in materials[:MAX_LISTED_MATERIALS])
    others = "\n".join(f"- {other.name}" for other in other_courses)
    resumed = state["resumed_from"]
    return SYSTEM_PROMPT.format(
        name=course.name,
        semester=course.semester,
        year=course.year,
        description=course.description or "(none)",
        materials=listed or "(none uploaded yet)",
        other_courses=others or "(none)",
        qa=AGENT_DESCRIPTIONS["qa_agent"],
        study_tools=AGENT_DESCRIPTIONS["study_tools_agent"],
        summary=AGENT_DESCRIPTIONS["summary_agent"],
        resume_rule=RESUME_RULE if resumed else "",
        completed=_describe_results(state["agent_results"]) or "(nothing yet)",
        resume_context=(
            RESUME_CONTEXT.format(
                request=state["request_message"],
                question=resumed["suggested_question"],
                reason=resumed["reason"],
            )
            if resumed
            else ""
        ),
    )


def _describe_results(results: list[AgentResult]) -> str:
    lines = []
    for result in results:
        label = result["agent"]
        if label == "study_tools_agent":
            label += f" ({result.get('kind', 'unclear')})"
        summary = result["summary"]
        if len(summary) > MAX_RESULT_CHARS:  # a Q&A result is the whole answer
            summary = summary[:MAX_RESULT_CHARS].rstrip() + "…"
        lines.append(f"- {label}: {summary}")
    return "\n".join(lines)
