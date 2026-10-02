from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

MAX_CONTENT_LENGTH = 200_000


class SummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    content: str
    is_edited: bool
    updated_at: datetime


class SummaryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)


class SummaryHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    version_number: int
    archived_at: datetime
