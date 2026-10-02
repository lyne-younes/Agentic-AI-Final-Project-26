from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models import CourseStatus


def _blank_to_none(value: str | None) -> str | None:
    return value or None


class CourseCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    semester: str = Field(min_length=1, max_length=50)
    year: int = Field(ge=2000, le=2100)
    description: str | None = Field(default=None, max_length=2000)

    _description = field_validator("description")(_blank_to_none)


class CourseUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    semester: str | None = Field(default=None, min_length=1, max_length=50)
    year: int | None = Field(default=None, ge=2000, le=2100)
    description: str | None = Field(default=None, max_length=2000)
    status: CourseStatus | None = None

    _description = field_validator("description")(_blank_to_none)

    @model_validator(mode="after")
    def _required_fields_not_null(self) -> "CourseUpdate":
        for field in ("name", "semester", "year", "status"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    semester: str
    year: int
    description: str | None
    icon_url: str | None
    status: CourseStatus
    created_at: datetime
    material_count: int = 0


class CourseListItem(CourseOut):
    """GET /courses only: what a library card shows beyond the course. Derived, not stored."""

    materials_pending: int = 0  # still being indexed
    materials_failed: int = 0  # indexing failed; needs a retry from the Materials tab
    quiz_count: int = 0
    flashcard_set_count: int = 0
    # Latest of: a chat message, a quiz attempt, a material change. None if nothing happened yet.
    last_activity_at: datetime | None = None
    last_chat_session_id: int | None = None  # the chat with the most recent message
    last_chat_at: datetime | None = None
