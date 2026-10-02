import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ChatSessionType(enum.StrEnum):
    course_chat = "course_chat"
    study_planner = "study_planner"


class ChatSessionSource(enum.StrEnum):
    """Why a chat was opened, when a page opened it for a purpose (not the student's own chat)."""

    quiz_explain = "quiz_explain"  # "Explain my mistakes" on a quiz attempt
    quiz_flashcards = "quiz_flashcards"  # "Turn mistakes into flashcards" on a quiz attempt


class MessageRole(enum.StrEnum):
    user = "user"
    assistant = "assistant"


class ChatSession(Base):
    """One conversation thread; a course can have many."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Null for the global Study Planner chat.
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[ChatSessionType] = mapped_column(Enum(ChatSessionType, name="chat_session_type"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Saved agent state while waiting for the answer to a clarification question.
    pending_state: Mapped[dict | None] = mapped_column(JSONB)
    # Set when the quiz page opened this chat for an attempt.
    source_quiz_attempt_id: Mapped[int | None] = mapped_column(
        ForeignKey("quiz_attempts.id", ondelete="SET NULL"), index=True
    )
    source_kind: Mapped[ChatSessionSource | None] = mapped_column(
        Enum(ChatSessionSource, name="chat_session_source")
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole, name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    # Which agent(s) produced an assistant message; one row even when several agents contributed.
    handled_by: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    # Q&A's suggested next questions for an assistant message; shown as chips under the reply.
    follow_ups: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
