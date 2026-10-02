from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ChatSessionSource, ChatSessionType, MessageRole

MAX_MESSAGE_LENGTH = 4000


class ChatSessionOut(BaseModel):
    id: int
    course_id: int | None
    type: ChatSessionType
    title: str  # derived, not stored: the first item created, else the first question
    created_at: datetime
    last_message_at: datetime | None


class ChatSessionCreate(BaseModel):
    """Optional body, set when the quiz page opens a chat for an attempt."""

    source_quiz_attempt_id: int
    source_kind: ChatSessionSource


class CreatedItemOut(BaseModel):
    """Content created in an assistant message's turn."""

    kind: Literal["quiz", "flashcards", "summary"]
    id: int
    title: str
    count: int | None = None  # questions or cards
    format: str | None = None  # quizzes only
    difficulty: str | None = None  # quizzes only


class ChatMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: MessageRole
    content: str
    handled_by: list[str] | None
    follow_ups: list[str] | None = None
    created_at: datetime
    created_items: list[CreatedItemOut] = []


class MessageCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=MAX_MESSAGE_LENGTH)


class AgentReply(BaseModel):
    """Reply from the chat endpoint, for answers and clarification questions alike."""

    status: Literal["done", "needs_clarification"]
    message: str
    handled_by: list[str] | None
    follow_ups: list[str] = []  # suggested next questions; empty unless Q&A offered some
