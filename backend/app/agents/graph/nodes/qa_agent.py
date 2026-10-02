"""qa_agent node: answers questions from the retrieved course passages.

Three tiers: grounded answer, general knowledge with a disclaimer, or a fixed refusal for questions
outside this course (pointing to another course's chat when one fits).
"""

import logging
import re
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.agents.graph import results
from app.agents.graph.state import AgentState
from app.models import Course

logger = logging.getLogger(__name__)

AGENT_NAME = "qa_agent"
MAX_ANSWER_RETRIES = 1
MAX_FOLLOW_UPS = 3
MAX_FOLLOW_UP_LENGTH = 120

EMPTY_COURSE_MESSAGE = (
    "This course doesn't have any materials yet. Upload your lecture notes, slides or readings in "
    "the **Materials** tab, and I'll answer questions based on them."
)
NOT_READY_MESSAGE = (
    "None of this course's materials are ready yet: they're still being indexed, or indexing "
    "failed. Check the **Materials** tab; once a material shows **Ready**, I can answer questions "
    "about it."
)
GENERAL_KNOWLEDGE_DISCLAIMER = (
    "*This isn't covered in your uploaded materials, so this answer is based on general knowledge.*"
)
OFF_TOPIC_MESSAGE = "This chat is for the **{course}** course, so I can only help with that here."
OTHER_COURSE_MESSAGE = (
    "This chat is for the **{course}** course. If you'd like to study {other}, you can switch to "
    "your **{other}** course."
)
FALLBACK_ANSWER = "I couldn't put together an answer to that. Could you rephrase the question?"
CUT_OFF_RETRY_PROMPT = (
    "(Your previous reply was cut off because it was too long. Call submit_answer again with a "
    "more concise answer: cover the main points and leave out lesser detail.)"
)
MISSING_ANSWER_RETRY_PROMPT = (
    "(Your submit_answer call had no answer text. Call submit_answer again with both relevance "
    "and answer.)"
)

# Some models leak the tool-call markup's closing tags into the end of the answer string.
LEAKED_TAGS = re.compile(r"(\s*</(?:answer|invoke|parameter|function_calls)>)+\s*$")

ANSWER_TOOL_NAME = "submit_answer"
ANSWER_TOOL = {
    "type": "function",
    "function": {
        "name": ANSWER_TOOL_NAME,
        "description": "Finish by giving the student your reply.",
        "parameters": {
            "type": "object",
            "properties": {
                "relevance": {
                    "type": "string",
                    "enum": ["grounded", "general_knowledge", "other_course", "off_topic"],
                    "description": (
                        "grounded: the retrieved passages (or, for a question about this "
                        "conversation, the conversation itself) support the answer. "
                        "general_knowledge: the question belongs to this course's subject but "
                        "the passages don't cover it. other_course: it's about the subject of "
                        "one of the student's other courses. off_topic: unrelated to this course."
                    ),
                },
                "other_course": {
                    "type": "string",
                    "description": "other_course only: that course's name, exactly as listed.",
                },
                "answer": {
                    "type": "string",
                    "description": "The reply to the student, in Markdown.",
                },
                "follow_ups": {
                    "type": "array",
                    "items": {"type": "string"},
                    "maxItems": MAX_FOLLOW_UPS,
                    "description": (
                        "grounded and general_knowledge only: 2-3 short questions the student "
                        "might ask next to go deeper into this course, written as the student "
                        "would ask them (e.g. 'How do volumes differ from bind mounts?'). Each "
                        "under 80 characters, not answered already above."
                    ),
                },
            },
            "required": ["relevance", "answer"],
        },
    },
}

SYSTEM_PROMPT = """\
You are the Q&A assistant for a student's course. This chat belongs to this course only.

Course: {name} ({semester} {year})
Description: {description}

The student's other courses (each has its own chat):
{other_courses}

Passages retrieved from the course's uploaded materials for this question:
{context}

Scope: you only explain and answer. If the student's message also asks for a quiz, flashcards, a \
summary or a study plan, do not produce or mention those - other assistants handle them - and \
answer only the explanation/question part.

The earlier assistant messages in this conversation were written by this app's team of \
assistants, including ones that really do create and save quizzes, flashcards and summaries. What \
those messages say was created was created: never contradict, disown or apologise for them. You \
can answer questions about the conversation itself (e.g. what was generated) from it; that counts \
as grounded.

Decide how the question relates to this course:
- grounded: the passages cover it. Answer from them. Do not cite sources or mention "materials", \
"passages" or "documents"; just answer.
- general_knowledge: the question belongs to this course's subject (judge from the course name, \
description and what kind of material was retrieved above, not only its literal wording), but the \
passages don't cover it. Answer from general knowledge. A disclaimer is added for you, so don't \
write one.
- other_course: the question is mainly about the subject of one of the student's other courses \
listed above - even if this course mentions that subject in passing - rather than about how it \
relates to this course's subject. Set other_course to that course's name. The student is pointed \
to that course's chat for you, so leave answer empty.
- off_topic: unrelated to this course's subject and not one of the other courses. A subject this \
course only mentions in passing is not its subject. The reply says for you that this chat is only \
for this course; in answer, add at most one short sentence on what you can help with instead.

For a grounded or general_knowledge answer, also suggest follow_ups: questions that build on \
this answer and stay within this course. Leave them out for other_course and off_topic.

Always finish by calling submit_answer. Write clearly and at a level suited to a student. For \
broad questions ("key ideas", "overview", "explain everything"), give a well-organized summary of \
the main points rather than every detail. Use Markdown (lists, code blocks) when it helps.\
"""


class Relevance(StrEnum):
    grounded = "grounded"
    general_knowledge = "general_knowledge"
    other_course = "other_course"
    off_topic = "off_topic"


async def qa_agent(state: AgentState, *, db: AsyncSession, course: Course) -> dict:
    if state["context_status"] == "empty_course":
        return results.success(state, AGENT_NAME, EMPTY_COURSE_MESSAGE)
    if state["context_status"] == "not_ready":
        return results.success(state, AGENT_NAME, NOT_READY_MESSAGE)

    other_courses = list(
        await db.scalars(
            select(Course.name)
            .where(Course.user_id == course.user_id, Course.id != course.id)
            .order_by(Course.name)
        )
    )
    system_prompt = _system_prompt(course, other_courses, state["retrieved_context"])
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *({"role": role, "content": content} for role, content in state["messages"]),
        # Only this delegation's part of the message, so the model doesn't answer every part.
        {"role": "user", "content": state["delegation_focus"] or state["raw_message"]},
    ]
    retries_left = MAX_ANSWER_RETRIES

    while True:
        reply = await llm.complete(messages, tools=[ANSWER_TOOL], tool_choice="required")

        if reply.truncated:
            retry_prompt, problem = CUT_OFF_RETRY_PROMPT, "reply was cut off at the output limit"
        elif not reply.tool_calls:
            # Some models (especially small local ones) ignore tool_choice and reply in plain text.
            text = (reply.content or "").strip()
            return results.success(state, AGENT_NAME, text or FALLBACK_ANSWER)
        else:
            call = next((c for c in reply.tool_calls if c.name == ANSWER_TOOL_NAME), None)
            final = _final_answer(call.arguments, course, other_courses) if call else None
            if final is not None:
                relevance, answer = final
                logger.info("Course %s: qa_agent answered (%s)", course.id, relevance)
                follow_ups = (
                    _follow_ups(call.arguments.get("follow_ups"))
                    if relevance in (Relevance.grounded, Relevance.general_knowledge)
                    else []
                )
                return results.success(state, AGENT_NAME, answer, follow_ups=follow_ups)
            retry_prompt = MISSING_ANSWER_RETRY_PROMPT
            problem = "submit_answer had no answer text"

        if retries_left == 0:
            logger.warning("Course %s: %s again; giving up", course.id, problem)
            return results.success(state, AGENT_NAME, FALLBACK_ANSWER)
        retries_left -= 1
        logger.warning("Course %s: %s; asking the model to answer again", course.id, problem)
        messages.append({"role": "user", "content": retry_prompt})


def _final_answer(
    arguments: dict[str, Any], course: Course, other_courses: list[str]
) -> tuple[str, str] | None:
    """(relevance, answer) with the tier's fixed wording applied, or None if text is missing."""
    answer = LEAKED_TAGS.sub("", str(arguments.get("answer") or "")).strip()
    try:
        relevance = Relevance(arguments.get("relevance"))
    except ValueError:
        # An unclassified answer might not be grounded; disclose rather than imply it is.
        relevance = Relevance.general_knowledge

    if relevance == Relevance.other_course:
        other = _match_course(str(arguments.get("other_course") or ""), other_courses)
        if other is not None:
            return relevance.value, OTHER_COURSE_MESSAGE.format(course=course.name, other=other)
        relevance = Relevance.off_topic  # not one of theirs: still say what this chat is for
        answer = ""
    if relevance == Relevance.off_topic:
        lead = OFF_TOPIC_MESSAGE.format(course=course.name)
        return relevance.value, f"{lead} {answer}" if answer else lead

    if not answer:
        return None
    if relevance == Relevance.general_knowledge:
        answer = f"{GENERAL_KNOWLEDGE_DISCLAIMER}\n\n{answer}"
    return relevance.value, answer


def _follow_ups(raw: Any) -> list[str]:
    """The model's suggested next questions, cleaned up and capped."""
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        text = " ".join(str(item).split()) if isinstance(item, str) else ""
        if not text or len(text) > MAX_FOLLOW_UP_LENGTH:
            continue
        if text.casefold() not in (seen.casefold() for seen in cleaned):
            cleaned.append(text)
    return cleaned[:MAX_FOLLOW_UPS]


def _match_course(name: str, other_courses: list[str]) -> str | None:
    """The student's course the model named, or None if it named one they don't have."""
    wanted = name.strip().casefold()
    if not wanted:
        return None
    for candidate in other_courses:
        if candidate.casefold() == wanted:
            return candidate
    for candidate in other_courses:
        if wanted in candidate.casefold() or candidate.casefold() in wanted:
            return candidate
    return None


def _system_prompt(course: Course, other_courses: list[str], context: str) -> str:
    return SYSTEM_PROMPT.format(
        name=course.name,
        semester=course.semester,
        year=course.year,
        description=course.description or "(none)",
        other_courses="\n".join(f"- {name}" for name in other_courses) or "(none)",
        context=context or "(no matching passages found)",
    )
