"""verifier_agent node: checks a generated quiz or flashcard set before it is saved.

Each item is checked for well-formedness in code, then judged by the model against the retrieved
passages. Only items that pass are saved. If some were rejected, the draft goes back to
study_tools_agent to generate the missing items, for up to MAX_ROUNDS rounds.
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app import llm
from app.agents.graph import results
from app.agents.graph.nodes import study_tools_agent
from app.agents.graph.state import AgentState, StudyDraft
from app.models import Course, QuestionType

logger = logging.getLogger(__name__)

AGENT_NAME = "verifier_agent"
MAX_ROUNDS = 3  # generation rounds in total: the first one plus up to two top-ups

NOTHING_VERIFIED_MESSAGE = (
    "I generated that, but none of it passed the check against your materials, so I didn't save "
    "it. Try a topic your uploaded materials cover in more detail, or upload more material on it."
)

SUPPORTED = "supported"
VERDICT_TOOL_NAME = "submit_verdicts"
VERDICT_TOOL = {
    "type": "function",
    "function": {
        "name": VERDICT_TOOL_NAME,
        "description": "Submit one verdict for every item.",
        "parameters": {
            "type": "object",
            "properties": {
                "verdicts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item": {"type": "integer", "description": "The item's number."},
                            "verdict": {
                                "type": "string",
                                "enum": [SUPPORTED, "unsupported", "wrong_answer"],
                            },
                            "reason": {
                                "type": "string",
                                "description": "One short sentence, for the log.",
                            },
                        },
                        "required": ["item", "verdict", "reason"],
                    },
                },
            },
            "required": ["verdicts"],
        },
    },
}

SYSTEM_PROMPT = """\
You are a strict fact-checker for study material generated for a student's course. Check each \
{noun} below against the passages only - not against your own knowledge.

Passages from the course's uploaded materials:
{context}

Give every item one verdict:
- supported: the passages state what the item asks and its answer. For a quiz question the marked \
answer must be correct and, for multiple choice, the only correct option.
- unsupported: the passages don't cover it, or it adds facts they don't contain.
- wrong_answer: the passages cover it, but the marked answer (or the card's back) is wrong.

Judge each item on its own, and call {tool} once with a verdict for every item.\
"""


async def verifier_agent(state: AgentState, *, db: AsyncSession, course: Course) -> dict[str, Any]:
    draft = state["study_draft"]
    assert draft is not None  # route_after_study_tools only sends a draft here
    kind = draft["kind"]

    well_formed = [item for item in draft["candidates"] if _well_formed(kind, item)]
    malformed = [item for item in draft["candidates"] if not _well_formed(kind, item)]
    verdicts = (
        await judge_items(kind, well_formed, state["retrieved_context"]) if well_formed else []
    )
    passed = [item for item, ok in zip(well_formed, verdicts, strict=True) if ok]
    failed = malformed + [item for item, ok in zip(well_formed, verdicts, strict=True) if not ok]

    room = draft["count"] - len(draft["accepted"])
    checked: StudyDraft = {
        **draft,
        "candidates": [],
        "accepted": draft["accepted"] + passed[:room],
        "rejected": draft["rejected"] + [_label(kind, item) for item in failed],
    }
    logger.info(
        "Course %s: verifier round %s: %s of %s %s passed (%s malformed), %s of %s kept so far",
        course.id,
        draft["rounds"],
        len(passed),
        len(draft["candidates"]),
        kind,
        len(malformed),
        len(checked["accepted"]),
        draft["count"],
    )

    # Top up only when items were rejected, not when the generator came back short on its own.
    if len(checked["accepted"]) < draft["count"] and failed and draft["rounds"] < MAX_ROUNDS:
        return {"study_draft": checked}

    if not checked["accepted"]:
        outcome = results.success(
            state,
            study_tools_agent.AGENT_NAME,
            NOTHING_VERIFIED_MESSAGE,
            kind=kind,
            helpers=[AGENT_NAME],
        )
        return {**outcome, "study_draft": None}

    summary, content = await study_tools_agent.save_draft(db, course, checked)
    outcome = results.success(
        state,
        study_tools_agent.AGENT_NAME,
        summary,
        content=content,
        kind=kind,
        helpers=[AGENT_NAME],
    )
    return {**outcome, "study_draft": None}


def _well_formed(kind: str, item: dict) -> bool:
    """Shape checks only (non-empty text, valid answer for the question type)."""
    if kind == "flashcards":
        return bool(item.get("front")) and bool(item.get("back"))

    answer = item.get("correct_answer") or ""
    if not item.get("question_text") or not answer:
        return False
    if item.get("question_type") == QuestionType.mcq.value:
        options = [option.strip().casefold() for option in item.get("options") or []]
        return len(options) >= 2 and len(set(options)) == len(options) and _key(answer) in options
    if item.get("question_type") == QuestionType.true_false.value:
        return _key(answer) in ("true", "false")
    return True


async def judge_items(kind: str, items: list[dict], context: str) -> list[bool]:
    """One model call that judges every item; True means verified. Missing verdicts are False."""
    noun = "quiz question" if kind == "quiz" else "flashcard"
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.format(
                noun=noun, context=context or "(no passages)", tool=VERDICT_TOOL_NAME
            ),
        },
        {"role": "user", "content": _render(kind, items)},
    ]
    reply = await llm.complete(messages, tools=[VERDICT_TOOL], tool_choice="required")
    call = next((c for c in reply.tool_calls if c.name == VERDICT_TOOL_NAME), None)
    raw = (call.arguments.get("verdicts") if call else None) or []

    verified: dict[int, bool] = {}
    for verdict in raw if isinstance(raw, list) else []:
        if not isinstance(verdict, dict):
            continue
        number = verdict.get("item")
        if isinstance(number, int) and 1 <= number <= len(items) and number not in verified:
            verified[number] = verdict.get("verdict") == SUPPORTED
            if not verified[number]:
                logger.info(
                    "Verifier turned down %s %s (%s): %s",
                    noun,
                    number,
                    verdict.get("verdict"),
                    verdict.get("reason", ""),
                )
    missing = [n for n in range(1, len(items) + 1) if n not in verified]
    if missing:
        logger.warning("Verifier gave no verdict for %s %s; not verified", noun, missing)
    return [verified.get(number, False) for number in range(1, len(items) + 1)]


def _render(kind: str, items: list[dict]) -> str:
    lines = []
    for number, item in enumerate(items, start=1):
        if kind == "flashcards":
            lines.append(f"{number}. Front: {item['front']}\n   Back: {item['back']}")
            continue
        lines.append(f"{number}. [{item['question_type']}] {item['question_text']}")
        if item.get("options"):
            lines.append("   Options: " + " | ".join(item["options"]))
        lines.append(f"   Marked answer: {item['correct_answer']}")
    return "\n".join(lines)


def _label(kind: str, item: dict) -> str:
    """The text used to name a rejected item on a top-up round."""
    text = item.get("front") if kind == "flashcards" else item.get("question_text")
    return str(text or "(empty)")


def _key(text: str) -> str:
    return text.strip().casefold()
