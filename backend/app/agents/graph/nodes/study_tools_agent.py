"""study_tools_agent node: generates quizzes and flashcard sets.

One model call resolves the request (type, coverage, quiz format/difficulty, count), a second
generates the items. One delegation makes one item. Nothing is saved here: the draft goes to
verifier_agent, which saves what passes and may send it back for a top-up round.
"""

import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.agents.graph import results
from app.agents.graph.nodes import qa_agent
from app.agents.graph.state import AgentState, StudyDraft
from app.models import (
    Course,
    Flashcard,
    FlashcardSet,
    QuestionType,
    Quiz,
    QuizDifficulty,
    QuizFormat,
    QuizQuestion,
)

logger = logging.getLogger(__name__)

AGENT_NAME = "study_tools_agent"
DEFAULT_QUIZ_COUNT = 10
DEFAULT_FLASHCARD_COUNT = 15
QUIZ_FORMATS = {f.value for f in QuizFormat}
QUIZ_DIFFICULTIES = {d.value for d in QuizDifficulty}
QUESTION_TYPES = {t.value for t in QuestionType}

# How a student spells out a quiz format, for `_fill_stated_quiz_details`.
STATED_FORMATS = (
    ("mcq", r"\bmcqs?\b|multiple[\s-]*choice"),
    ("true_false", r"\btrue\s*(?:/|or|-|and)?\s*false\b|\bt/f\b"),
    ("short_answer", r"short[\s-]*answers?"),
    ("mixed", r"\bmixed\b"),
)

GENERATION_FAILED_MESSAGE = "I wasn't able to generate that just now. Please try again."

RESOLVE_TOOL_NAME = "resolve_request"
RESOLVE_TOOL = {
    "type": "function",
    "function": {
        "name": RESOLVE_TOOL_NAME,
        "description": "Decide what study material to generate, before generating it.",
        "parameters": {
            "type": "object",
            "properties": {
                "study_tool_type": {
                    "type": "string",
                    "enum": ["quiz", "flashcards", "unclear"],
                    "description": (
                        "unclear only if the request genuinely doesn't say whether the student "
                        "wants a quiz or flashcards (e.g. 'help me study chapter 3')."
                    ),
                },
                "covered": {
                    "type": "boolean",
                    "description": (
                        "True if the retrieved passages give enough to generate from and the "
                        "topic is on-topic for this course. False if the requested topic isn't "
                        "covered by any uploaded material - study material must never be "
                        "generated on content the student never uploaded."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": sorted(QUIZ_FORMATS),
                    "description": "Quiz only. Omit if the student didn't specify one.",
                },
                "difficulty": {
                    "type": "string",
                    "enum": sorted(QUIZ_DIFFICULTIES),
                    "description": "Quiz only. Omit if the student didn't specify one.",
                },
                "count": {
                    "type": "integer",
                    "description": (
                        "Only when the student gives an explicit number ('5 questions', '20 "
                        "cards'). 'a quiz', 'a flashcard' or 'some flashcards' is not a number - "
                        "omit it."
                    ),
                },
            },
            "required": ["study_tool_type", "covered"],
        },
    },
}

RESOLVE_SYSTEM_PROMPT = """\
You generate study material (quizzes and flashcards) for a student's course.

Course: {name} ({semester} {year})
Description: {description}

Passages retrieved from the course's uploaded materials for this request:
{context}

Read the conversation and call {tool} to say what to do next. If you've been given a task \
that is one part of the student's message, resolve that task only - other parts are handled \
separately. Format and difficulty are only relevant for a quiz; leave them out for flashcards or \
when unspecified.{assigned}\
"""

# Added when the orchestrator already named the item type.
ASSIGNED_ITEM = """

You have been asked to make {article} {item}: set study_tool_type to {item}, and take its details \
(covered, count{quiz_details}) from anything the conversation says about the {item}."""

SUBMIT_QUIZ_TOOL_NAME = "submit_quiz"
SUBMIT_QUIZ_TOOL = {
    "type": "function",
    "function": {
        "name": SUBMIT_QUIZ_TOOL_NAME,
        "description": "Submit the generated quiz.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "questions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "question_text": {"type": "string"},
                            "question_type": {"type": "string", "enum": sorted(QUESTION_TYPES)},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "MCQ choices only; omit for other question types.",
                            },
                            "correct_answer": {
                                "type": "string",
                                "description": (
                                    "For MCQ, exactly one of options. For true/false, 'true' or "
                                    "'false'. For short answer, the expected answer text."
                                ),
                            },
                        },
                        "required": ["question_text", "question_type", "correct_answer"],
                    },
                },
            },
            "required": ["title", "questions"],
        },
    },
}

GENERATE_QUIZ_SYSTEM_PROMPT = """\
Generate a {difficulty}-difficulty, {format}-format quiz for the course "{name}", with up to \
{count} questions - fewer only if the material below doesn't support that many good questions; \
never pad with filler. Ground every question in the passages below; do not invent facts.

Passages:
{context}
{previous}
Call {tool} with the finished quiz.\
"""

# Lists the previous quiz's questions / set's card fronts so they aren't repeated.
PREVIOUS_ITEMS_PROMPT = """
The most recent {label} for this course already used the {noun} below. Do not repeat these, \
and do not ask the same thing in different words - cover other points from the passages \
instead:
{items}
"""

# Keeps the prompt small.
MAX_PREVIOUS_ITEMS = 30

# Used on a top-up round, after verifier_agent rejected some items.
TOP_UP_PROMPT = """
You are adding to a {label} that is already in progress: write {wanted} new {noun} only.
"""
KEPT_ITEMS_PROMPT = """These {noun} are already in it and passed the check - don't repeat them:
{items}
"""
REJECTED_ITEMS_PROMPT = """These {noun} were turned down because the passages don't support them \
or their answer was wrong - don't write them again:
{items}
"""

SUBMIT_FLASHCARDS_TOOL_NAME = "submit_flashcards"
SUBMIT_FLASHCARDS_TOOL = {
    "type": "function",
    "function": {
        "name": SUBMIT_FLASHCARDS_TOOL_NAME,
        "description": "Submit the generated flashcards.",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "cards": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "front": {"type": "string"},
                            "back": {"type": "string"},
                        },
                        "required": ["front", "back"],
                    },
                },
            },
            "required": ["title", "cards"],
        },
    },
}

GENERATE_FLASHCARDS_SYSTEM_PROMPT = """\
Generate flashcards for the course "{name}", with up to {count} cards - fewer only if the \
material below doesn't support that many good cards; never pad with filler. Ground every card in \
the passages below; do not invent facts. Keep each front a short prompt and each back a concise \
answer.

Passages:
{context}
{previous}
Call {tool} with the finished set.\
"""


async def study_tools_agent(state: AgentState, *, db: AsyncSession, course: Course) -> dict:
    draft = state.get("study_draft")
    if draft:
        # verifier_agent rejected some items: generate only the missing ones.
        return await _generate_round(db, course, state, draft)

    if state["context_status"] == "empty_course":
        return results.success(state, AGENT_NAME, qa_agent.EMPTY_COURSE_MESSAGE)
    if state["context_status"] == "not_ready":
        return results.success(state, AGENT_NAME, qa_agent.NOT_READY_MESSAGE)

    resolution = await _resolve(state, course)
    if state["delegation_kind"] in ("quiz", "flashcards"):
        # The orchestrator named the item; the resolve call only fills in its details.
        resolution["study_tool_type"] = state["delegation_kind"]

    if resolution["study_tool_type"] == "unclear":
        return results.clarify(
            AGENT_NAME, "quiz vs flashcards is ambiguous", "Would you like a quiz or flashcards?"
        )

    if not resolution["covered"]:
        kind = resolution["study_tool_type"]
        return results.success(state, AGENT_NAME, _refusal_message(), kind=kind)

    if resolution["study_tool_type"] == "quiz":
        _fill_stated_quiz_details(resolution, state)
        if not resolution.get("format") or not resolution.get("difficulty"):
            return results.clarify(
                AGENT_NAME,
                "quiz format/difficulty not specified",
                "What format would you like (multiple choice, true/false, short answer, or "
                "mixed) and what difficulty (easy, medium, or hard)?",
            )
        return await _draft_quiz(db, course, state, resolution)

    return await _draft_flashcards(db, course, state, resolution)


async def _resolve(state: AgentState, course: Course) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": _resolve_prompt(
                course, state["retrieved_context"], state["delegation_kind"]
            ),
        },
        *({"role": role, "content": content} for role, content in state["messages"]),
        {"role": "user", "content": results.task_message(state)},
    ]
    reply = await llm.complete(messages, tools=[RESOLVE_TOOL], tool_choice="required")
    call = next((c for c in reply.tool_calls if c.name == RESOLVE_TOOL_NAME), None)
    return _parse_resolution(call.arguments if call else {})


def _fill_stated_quiz_details(resolution: dict[str, Any], state: AgentState) -> None:
    """Fills in a quiz format/difficulty the student clearly stated but the model missed."""
    text = " ".join(
        [state["delegation_focus"], state["raw_message"], state["request_message"]]
    ).lower()
    if not resolution.get("format"):
        formats = {name for name, pattern in STATED_FORMATS if re.search(pattern, text)}
        if len(formats) == 1:
            resolution["format"] = formats.pop()
    if not resolution.get("difficulty"):
        difficulties = set(re.findall(r"\b(easy|medium|hard)\b", text))
        if len(difficulties) == 1:
            resolution["difficulty"] = difficulties.pop()


def _parse_resolution(arguments: dict[str, Any]) -> dict[str, Any]:
    study_tool_type = arguments.get("study_tool_type")
    if study_tool_type not in ("quiz", "flashcards", "unclear"):
        study_tool_type = "unclear"
    return {
        "study_tool_type": study_tool_type,
        "covered": bool(arguments.get("covered", False)),
        "format": arguments.get("format") if arguments.get("format") in QUIZ_FORMATS else None,
        "difficulty": (
            arguments.get("difficulty")
            if arguments.get("difficulty") in QUIZ_DIFFICULTIES
            else None
        ),
        "count": arguments.get("count") if isinstance(arguments.get("count"), int) else None,
    }


async def _draft_quiz(
    db: AsyncSession, course: Course, state: AgentState, resolution: dict[str, Any]
) -> dict:
    draft: StudyDraft = {
        "kind": "quiz",
        "title": f"{course.name} Quiz",
        "format": resolution["format"],
        "difficulty": resolution["difficulty"],
        "count": resolution["count"] or DEFAULT_QUIZ_COUNT,
        "candidates": [],
        "accepted": [],
        "rejected": [],
        "rounds": 0,
    }
    return await _generate_round(db, course, state, draft)


async def _draft_flashcards(
    db: AsyncSession, course: Course, state: AgentState, resolution: dict[str, Any]
) -> dict:
    draft: StudyDraft = {
        "kind": "flashcards",
        "title": f"{course.name} Flashcards",
        "format": None,
        "difficulty": None,
        "count": resolution["count"] or DEFAULT_FLASHCARD_COUNT,
        "candidates": [],
        "accepted": [],
        "rejected": [],
        "rounds": 0,
    }
    return await _generate_round(db, course, state, draft)


async def _generate_round(
    db: AsyncSession, course: Course, state: AgentState, draft: StudyDraft
) -> dict:
    """One generation round: all items first, then only the missing ones on a top-up."""
    wanted = draft["count"] - len(draft["accepted"])
    if draft["kind"] == "quiz":
        items, title = await _generate_quiz_items(db, course, state, draft, wanted)
    else:
        items, title = await _generate_flashcard_items(db, course, state, draft, wanted)

    if not items and draft["rounds"] == 0:
        logger.warning("Course %s: study_tools_agent produced no %s", course.id, draft["kind"])
        return results.success(state, AGENT_NAME, GENERATION_FAILED_MESSAGE, kind=draft["kind"])

    if draft["rounds"] > 0:
        logger.info(
            "Course %s: study_tools_agent top-up round %s: %s new %s for %s missing",
            course.id,
            draft["rounds"] + 1,
            len(items),
            draft["kind"],
            wanted,
        )
    updated: StudyDraft = {
        **draft,
        "title": title if draft["rounds"] == 0 and title else draft["title"],
        "candidates": items[:wanted],
        "rounds": draft["rounds"] + 1,
    }
    return {"study_draft": updated}


async def _generate_quiz_items(
    db: AsyncSession, course: Course, state: AgentState, draft: StudyDraft, wanted: int
) -> tuple[list[dict], str]:
    quiz_format = str(draft["format"])
    messages = [
        {
            "role": "system",
            "content": GENERATE_QUIZ_SYSTEM_PROMPT.format(
                name=course.name,
                format=quiz_format,
                difficulty=draft["difficulty"],
                count=wanted,
                context=state["retrieved_context"],
                previous=await _previous_quiz_questions(db, course.id)
                + _in_progress_prompt(draft, "quiz", "questions", wanted),
                tool=SUBMIT_QUIZ_TOOL_NAME,
            ),
        },
        {"role": "user", "content": results.task_message(state)},
    ]
    reply = await llm.complete(messages, tools=[SUBMIT_QUIZ_TOOL], tool_choice="required")
    call = next((c for c in reply.tool_calls if c.name == SUBMIT_QUIZ_TOOL_NAME), None)
    raw = (call.arguments.get("questions") if call else None) or []
    items = []
    for question in raw if isinstance(raw, list) else []:
        if not isinstance(question, dict):
            continue
        question_type = _question_type(quiz_format, question.get("question_type"))
        options = question.get("options") if question_type == QuestionType.mcq else None
        items.append(
            {
                "question_text": str(question.get("question_text") or "").strip(),
                "question_type": question_type.value,
                "options": [str(o) for o in options] if isinstance(options, list) else None,
                "correct_answer": str(question.get("correct_answer") or "").strip(),
            }
        )
    title = str((call.arguments.get("title") if call else None) or "")
    return items, title


async def _generate_flashcard_items(
    db: AsyncSession, course: Course, state: AgentState, draft: StudyDraft, wanted: int
) -> tuple[list[dict], str]:
    messages = [
        {
            "role": "system",
            "content": GENERATE_FLASHCARDS_SYSTEM_PROMPT.format(
                name=course.name,
                count=wanted,
                context=state["retrieved_context"],
                previous=await _previous_flashcard_fronts(db, course.id)
                + _in_progress_prompt(draft, "flashcard set", "cards", wanted),
                tool=SUBMIT_FLASHCARDS_TOOL_NAME,
            ),
        },
        {"role": "user", "content": results.task_message(state)},
    ]
    reply = await llm.complete(messages, tools=[SUBMIT_FLASHCARDS_TOOL], tool_choice="required")
    call = next((c for c in reply.tool_calls if c.name == SUBMIT_FLASHCARDS_TOOL_NAME), None)
    raw = (call.arguments.get("cards") if call else None) or []
    items = [
        {
            "front": str(card.get("front") or "").strip(),
            "back": str(card.get("back") or "").strip(),
        }
        for card in (raw if isinstance(raw, list) else [])
        if isinstance(card, dict)
    ]
    title = str((call.arguments.get("title") if call else None) or "")
    return items, title


def _in_progress_prompt(draft: StudyDraft, label: str, noun: str, wanted: int) -> str:
    """On a top-up round: what this item already has, and what the verifier turned down."""
    if draft["rounds"] == 0:
        return ""
    text_key = "question_text" if draft["kind"] == "quiz" else "front"
    accepted = [item[text_key] for item in draft["accepted"]]
    prompt = TOP_UP_PROMPT.format(label=label, noun=noun, wanted=wanted)
    if accepted:
        prompt += KEPT_ITEMS_PROMPT.format(noun=noun, items=_bullets(accepted))
    if draft["rejected"]:
        prompt += REJECTED_ITEMS_PROMPT.format(noun=noun, items=_bullets(draft["rejected"]))
    return prompt


def _bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items[:MAX_PREVIOUS_ITEMS])


async def save_draft(db: AsyncSession, course: Course, draft: StudyDraft) -> tuple[str, str]:
    """Saves the verified items. Returns (student-facing summary, fuller content)."""
    if draft["kind"] == "quiz":
        return await _save_quiz(db, course, draft)
    return await _save_flashcards(db, course, draft)


async def _save_quiz(db: AsyncSession, course: Course, draft: StudyDraft) -> tuple[str, str]:
    questions = draft["accepted"]
    quiz_format, difficulty = str(draft["format"]), str(draft["difficulty"])
    quiz = Quiz(
        course_id=course.id,
        title=draft["title"],
        format=QuizFormat(quiz_format),
        difficulty=QuizDifficulty(difficulty),
    )
    db.add(quiz)
    await db.flush()  # need quiz.id for the question rows
    for order, question in enumerate(questions):
        db.add(
            QuizQuestion(
                quiz_id=quiz.id,
                question_text=question["question_text"],
                question_type=QuestionType(question["question_type"]),
                options=question["options"],
                correct_answer=question["correct_answer"],
                order=order,
            )
        )
    # flush, not commit: the chat endpoint commits the whole turn at once.
    await db.flush()

    generated = len(questions)
    summary = (
        f"Quiz created: {generated} {quiz_format} question(s), {difficulty} difficulty, "
        "saved to Study Tools."
    )
    if generated < draft["count"]:
        summary += _shortfall_note(generated, draft["count"], bool(draft["rejected"]))
    content = f'Generated quiz "{draft["title"]}": ' + "; ".join(
        question["question_text"] for question in questions
    )
    return summary, content


async def _save_flashcards(db: AsyncSession, course: Course, draft: StudyDraft) -> tuple[str, str]:
    cards = draft["accepted"]
    flashcard_set = FlashcardSet(course_id=course.id, title=draft["title"])
    db.add(flashcard_set)
    await db.flush()  # need flashcard_set.id for the card rows
    for order, card in enumerate(cards):
        db.add(
            Flashcard(
                flashcard_set_id=flashcard_set.id,
                front_text=card["front"],
                back_text=card["back"],
                order=order,
            )
        )
    # flush, not commit: see _save_quiz.
    await db.flush()

    generated = len(cards)
    summary = f"Flashcards created: {generated} card(s), saved to Study Tools."
    if generated < draft["count"]:
        summary += _shortfall_note(generated, draft["count"], bool(draft["rejected"]))
    content = f'Generated flashcard set "{draft["title"]}" with {generated} cards.'
    return summary, content


def _question_type(quiz_format: str, provided: Any) -> QuestionType:
    if quiz_format != QuizFormat.mixed.value:
        return QuestionType(quiz_format)
    if provided in QUESTION_TYPES:
        return QuestionType(provided)
    return QuestionType.short_answer


async def _previous_quiz_questions(db: AsyncSession, course_id: int) -> str:
    """The latest quiz's questions, as a "don't repeat these" prompt block."""
    quiz_id = await db.scalar(
        # By id: rows created in the same turn share a created_at.
        select(Quiz.id).where(Quiz.course_id == course_id).order_by(Quiz.id.desc()).limit(1)
    )
    if quiz_id is None:
        return ""
    questions = await db.scalars(
        select(QuizQuestion.question_text)
        .where(QuizQuestion.quiz_id == quiz_id)
        .order_by(QuizQuestion.order)
        .limit(MAX_PREVIOUS_ITEMS)
    )
    return _previous_items_prompt("quiz", "questions", list(questions))


async def _previous_flashcard_fronts(db: AsyncSession, course_id: int) -> str:
    """The latest set's card fronts, as a "don't repeat these" prompt block."""
    set_id = await db.scalar(
        select(FlashcardSet.id)
        .where(FlashcardSet.course_id == course_id)
        .order_by(FlashcardSet.id.desc())
        .limit(1)
    )
    if set_id is None:
        return ""
    fronts = await db.scalars(
        select(Flashcard.front_text)
        .where(Flashcard.flashcard_set_id == set_id)
        .order_by(Flashcard.order)
        .limit(MAX_PREVIOUS_ITEMS)
    )
    return _previous_items_prompt("flashcard set", "cards", list(fronts))


def _previous_items_prompt(label: str, noun: str, items: list[str]) -> str:
    listed = [item.strip() for item in items if item.strip()]
    if not listed:
        return ""
    return PREVIOUS_ITEMS_PROMPT.format(
        label=label, noun=noun, items="\n".join(f"- {item}" for item in listed)
    )


def _shortfall_note(generated: int, requested: int, verification_rejected: bool) -> str:
    if verification_rejected:
        return (
            f" Only {generated} of the {requested} requested passed the check against your "
            "materials — upload more material on this topic for a fuller set."
        )
    return (
        f" I could only generate {generated} of the {requested} requested — upload more "
        "material on this topic for a fuller set."
    )


def _refusal_message() -> str:
    return (
        "I can't generate study material on that — it isn't covered by any of your uploaded "
        "materials. Upload material on this topic, or ask about something that's already covered."
    )


def _resolve_prompt(course: Course, context: str, assigned: str) -> str:
    return RESOLVE_SYSTEM_PROMPT.format(
        name=course.name,
        semester=course.semester,
        year=course.year,
        description=course.description or "(none)",
        context=context or "(no matching passages found)",
        tool=RESOLVE_TOOL_NAME,
        assigned=_assigned_item(assigned),
    )


def _assigned_item(assigned: str) -> str:
    if assigned == "quiz":
        return ASSIGNED_ITEM.format(
            article="a", item="quiz", quiz_details=", format and difficulty"
        )
    if assigned == "flashcards":
        return ASSIGNED_ITEM.format(article="a set of", item="flashcards", quiz_details="")
    return ""
