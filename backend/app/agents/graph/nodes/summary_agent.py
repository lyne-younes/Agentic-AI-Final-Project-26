"""summary_agent node: writes or regenerates the course summary from the uploaded materials.

On regeneration the previous version is archived to `summary_history`, and the recent conversation
is passed in as the student's feedback.
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.agents.graph import results
from app.agents.graph.nodes import qa_agent
from app.agents.graph.state import AgentState
from app.models import Course, Summary, SummaryHistory

logger = logging.getLogger(__name__)

AGENT_NAME = "summary_agent"
GENERATION_FAILED_MESSAGE = "I wasn't able to generate a summary just now. Please try again."
# Recent messages passed as feedback on a regeneration.
FEEDBACK_TURNS = 4

SUBMIT_SUMMARY_TOOL_NAME = "submit_summary"
SUBMIT_SUMMARY_TOOL = {
    "type": "function",
    "function": {
        "name": SUBMIT_SUMMARY_TOOL_NAME,
        "description": "Submit the generated summary.",
        "parameters": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The summary, in Markdown (headings/lists welcome).",
                },
            },
            "required": ["content"],
        },
    },
}

FRESH_SYSTEM_PROMPT = """\
Write a well-organized summary of the course "{name}" ({semester} {year}) from its uploaded \
materials below. Cover the main points; use Markdown headings/lists to organize by topic. Draw \
only from the material given - do not add outside information.

Materials:
{context}

Call {tool} with the finished summary.\
"""

REGENERATE_SYSTEM_PROMPT = """\
Regenerate the summary for the course "{name}" ({semester} {year}), incorporating the student's \
feedback on the previous version below. Draw only from the course materials given - do not \
add outside information, and do not summarize the previous summary itself.

The student's feedback so far (most recent last). The latest message may only refer back to \
feedback given earlier, e.g. "ok, fix it" - apply all of it, not just the last line:
{feedback}

Previous version:
{previous}

Course materials:
{context}

Call {tool} with the revised summary.\
"""


async def summary_agent(state: AgentState, *, db: AsyncSession, course: Course) -> dict:
    if state["context_status"] == "empty_course":
        return results.success(state, AGENT_NAME, qa_agent.EMPTY_COURSE_MESSAGE)
    if state["context_status"] == "not_ready":
        return results.success(state, AGENT_NAME, qa_agent.NOT_READY_MESSAGE)

    existing = await db.scalar(select(Summary).where(Summary.course_id == course.id))
    prompt = _system_prompt(course, state["retrieved_context"], existing, state["messages"])
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": results.task_message(state)},
    ]
    reply = await llm.complete(messages, tools=[SUBMIT_SUMMARY_TOOL], tool_choice="required")
    call = next((c for c in reply.tool_calls if c.name == SUBMIT_SUMMARY_TOOL_NAME), None)
    content = str((call.arguments.get("content") if call else None) or "").strip()
    if not content:
        logger.warning("Course %s: summary_agent produced no content", course.id)
        return results.success(state, AGENT_NAME, GENERATION_FAILED_MESSAGE)

    if existing is not None:
        version_count = await db.scalar(
            select(func.count())
            .select_from(SummaryHistory)
            .where(SummaryHistory.course_id == course.id)
        )
        db.add(
            SummaryHistory(
                course_id=course.id,
                content=existing.content,
                version_number=(version_count or 0) + 1,
            )
        )
        existing.content = content
        existing.is_edited = False
    else:
        db.add(Summary(course_id=course.id, content=content, is_edited=False))
    # flush, not commit: the chat endpoint commits the whole turn at once.
    await db.flush()

    verb = "regenerated" if existing is not None else "generated"
    summary = f"Summary {verb} and saved to Notes."
    return results.success(state, AGENT_NAME, summary, content=content)


def _system_prompt(
    course: Course, context: str, existing: Summary | None, history: list[tuple[str, str]]
) -> str:
    materials = context or "(no matching passages found)"
    if existing is None:
        return FRESH_SYSTEM_PROMPT.format(
            name=course.name,
            semester=course.semester,
            year=course.year,
            context=materials,
            tool=SUBMIT_SUMMARY_TOOL_NAME,
        )
    return REGENERATE_SYSTEM_PROMPT.format(
        name=course.name,
        semester=course.semester,
        year=course.year,
        feedback=_recent_turns(history),
        previous=existing.content,
        context=materials,
        tool=SUBMIT_SUMMARY_TOOL_NAME,
    )


def _recent_turns(history: list[tuple[str, str]]) -> str:
    """The last few messages, labelled by speaker."""
    recent = history[-FEEDBACK_TURNS:]
    if not recent:
        return "(nothing earlier in this conversation)"
    speaker = {"user": "Student", "assistant": "Assistant"}
    return "\n".join(f"{speaker.get(role, role)}: {content}" for role, content in recent)
