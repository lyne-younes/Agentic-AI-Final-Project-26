from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.models import IndexingStatus, MaterialType

MAX_TAGS = 20
MAX_TAG_LENGTH = 40
MAX_NOTE_LENGTH = 200_000


def normalize_tags(tags: list[str]) -> list[str]:
    """Collapse whitespace, drop blanks, and de-duplicate case-insensitively (first one wins)."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in tags:
        tag = " ".join(raw.split())
        if not tag or tag.lower() in seen:
            continue
        if len(tag) > MAX_TAG_LENGTH:
            raise ValueError(f"Tags must be at most {MAX_TAG_LENGTH} characters")
        seen.add(tag.lower())
        result.append(tag)
    if len(result) > MAX_TAGS:
        raise ValueError(f"A material can have at most {MAX_TAGS} tags")
    return result


Tags = Annotated[list[str], AfterValidator(normalize_tags)]


class NoteCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200)
    content: str = Field(max_length=MAX_NOTE_LENGTH)
    tags: Tags = Field(default_factory=list)


class MaterialUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str | None = Field(default=None, min_length=1, max_length=200)
    tags: Tags | None = None
    content: str | None = Field(default=None, max_length=MAX_NOTE_LENGTH)  # authored notes only

    @model_validator(mode="after")
    def _fields_not_null(self) -> "MaterialUpdate":
        for field in ("title", "tags", "content"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null")
        return self


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    type: MaterialType
    title: str
    tags: list[str]
    indexing_status: IndexingStatus
    created_at: datetime
    updated_at: datetime


class MaterialDetail(MaterialOut):
    raw_text: str
