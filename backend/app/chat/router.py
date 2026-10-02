import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app import llm
from app.agents.graph import runner
from app.auth.dependencies import CurrentUser, DbSession
from app.chat import created_items
from app.chat.schemas import (
    AgentReply,
    ChatMessageOut,
    ChatSessionCreate,
    ChatSessionOut,
    CreatedItemOut,
    MessageCreate,
)
from app.courses.dependencies import OwnedCourse
from app.models import (
    ChatMessage,
    ChatSession,
    ChatSessionType,
    Course,
    MessageRole,
    Quiz,
    QuizAttempt,
)
from app.rag import embeddings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["chat"])

HISTORY_LIMIT = 20  # earlier messages given to the agent so follow-up questions make sense
TITLE_LENGTH = 60


async def get_owned_session(session_id: int, user: CurrentUser, db: DbSession) -> ChatSession:
    session = await db.scalar(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user.id)
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chat not found")
    return session


OwnedChatSession = Annotated[ChatSession, Depends(get_owned_session)]


@router.get("/courses/{course_id}/chat/sessions")
async def list_chat_sessions(
    course: OwnedCourse, user: CurrentUser, db: DbSession
) -> list[ChatSessionOut]:
    first_question = (
        select(ChatMessage.content)
        .where(ChatMessage.session_id == ChatSession.id, ChatMessage.role == MessageRole.user)
        .order_by(ChatMessage.id)
        .limit(1)
        .scalar_subquery()
    )
    last_message_at = (
        select(func.max(ChatMessage.created_at))
        .where(ChatMessage.session_id == ChatSession.id)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(ChatSession, first_question, last_message_at)
        .where(ChatSession.course_id == course.id, ChatSession.user_id == user.id)
        .order_by(
            func.coalesce(last_message_at, ChatSession.created_at).desc(), ChatSession.id.desc()
        )
    )
    listed = rows.all()
    first_items = await created_items.first_item_by_session(
        db, course.id, [session.id for session, _, _ in listed]
    )
    return [
        _session_out(session, question, last_at, first_items.get(session.id))
        for session, question, last_at in listed
    ]


@router.post("/courses/{course_id}/chat/sessions", status_code=status.HTTP_201_CREATED)
async def create_chat_session(
    course: OwnedCourse, user: CurrentUser, db: DbSession, body: ChatSessionCreate | None = None
) -> ChatSessionOut:
    session = ChatSession(course_id=course.id, user_id=user.id, type=ChatSessionType.course_chat)
    if body is not None:
        # The attempt must be on one of this course's quizzes (so, the student's own).
        attempt_id = await db.scalar(
            select(QuizAttempt.id)
            .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
            .where(QuizAttempt.id == body.source_quiz_attempt_id, Quiz.course_id == course.id)
        )
        if attempt_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Quiz attempt not found")
        session.source_quiz_attempt_id = attempt_id
        session.source_kind = body.source_kind
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_out(session, None, None)


@router.get("/chat/sessions/{session_id}/messages")
async def list_messages(session: OwnedChatSession, db: DbSession) -> list[ChatMessageOut]:
    messages = list(
        await db.scalars(
            select(ChatMessage).where(ChatMessage.session_id == session.id).order_by(ChatMessage.id)
        )
    )
    items: dict = {}
    if session.course_id is not None:
        items = await created_items.items_by_timestamp(
            db,
            session.course_id,
            (m.created_at for m in messages if m.role == MessageRole.assistant),
        )
    out = []
    for message in messages:
        entry = ChatMessageOut.model_validate(message)
        if message.role == MessageRole.assistant:
            entry.created_items = items.get(message.created_at, [])
        out.append(entry)
    return out


@router.get("/planner/sessions")
async def list_planner_sessions(user: CurrentUser, db: DbSession) -> list[ChatSessionOut]:
    """The Study Planner's chats: global, not nested under a course."""
    first_question = (
        select(ChatMessage.content)
        .where(ChatMessage.session_id == ChatSession.id, ChatMessage.role == MessageRole.user)
        .order_by(ChatMessage.id)
        .limit(1)
        .scalar_subquery()
    )
    last_message_at = (
        select(func.max(ChatMessage.created_at))
        .where(ChatMessage.session_id == ChatSession.id)
        .scalar_subquery()
    )
    rows = await db.execute(
        select(ChatSession, first_question, last_message_at)
        .where(
            ChatSession.user_id == user.id,
            ChatSession.type == ChatSessionType.study_planner,
        )
        .order_by(
            func.coalesce(last_message_at, ChatSession.created_at).desc(), ChatSession.id.desc()
        )
    )
    return [_session_out(session, question, last_at) for session, question, last_at in rows.all()]


@router.post("/planner/sessions", status_code=status.HTTP_201_CREATED)
async def create_planner_session(user: CurrentUser, db: DbSession) -> ChatSessionOut:
    session = ChatSession(course_id=None, user_id=user.id, type=ChatSessionType.study_planner)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_out(session, None, None)


@router.post("/chat/sessions/{session_id}/messages")
async def send_message(
    body: MessageCreate, session: OwnedChatSession, user: CurrentUser, db: DbSession
) -> AgentReply:
    """The single endpoint that runs the agents, for course chats and the planner."""
    course = None
    if session.type == ChatSessionType.course_chat:
        if session.course_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
        course = await db.get(Course, session.course_id)
        if course is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")

    recent = await db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.id.desc())
        .limit(HISTORY_LIMIT)
    )
    history = [(message.role.value, message.content) for message in reversed(list(recent))]

    try:
        result = await runner.run_turn(db, session, course, user, history, body.content)
    except (llm.LlmError, embeddings.EmbeddingError) as exc:
        logger.warning("Chat session %s: agent failed: %s", session.id, exc)
        # Discard everything this turn created (except calendar writes, committed in confirm_plan).
        await db.rollback()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The assistant is unavailable right now. Please try again in a moment.",
        ) from exc

    db.add_all(
        [
            ChatMessage(session_id=session.id, role=MessageRole.user, content=body.content),
            ChatMessage(
                session_id=session.id,
                role=MessageRole.assistant,
                content=result.message,
                handled_by=result.handled_by,
                follow_ups=result.follow_ups or None,
            ),
        ]
    )
    await db.commit()
    return AgentReply(
        status=result.status,
        message=result.message,
        handled_by=result.handled_by,
        follow_ups=result.follow_ups,
    )


def _session_out(
    session: ChatSession,
    first_question: str | None,
    last_message_at,
    first_item: CreatedItemOut | None = None,
) -> ChatSessionOut:
    return ChatSessionOut(
        id=session.id,
        course_id=session.course_id,
        type=session.type,
        title=_title(created_items.item_title(first_item) if first_item else first_question),
        created_at=session.created_at,
        last_message_at=last_message_at,
    )


def _title(first_question: str | None) -> str:
    if not first_question:
        return "New chat"
    text = " ".join(first_question.split())
    return text if len(text) <= TITLE_LENGTH else f"{text[: TITLE_LENGTH - 1].rstrip()}…"
