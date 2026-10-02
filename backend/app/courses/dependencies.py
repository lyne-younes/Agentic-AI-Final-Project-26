from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DbSession
from app.models import Course


async def get_owned_course(course_id: int, user: CurrentUser, db: DbSession) -> Course:
    # Someone else's course is reported as missing, not forbidden, so ids can't be probed.
    course = await db.scalar(
        select(Course).where(Course.id == course_id, Course.user_id == user.id)
    )
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found")
    return course


OwnedCourse = Annotated[Course, Depends(get_owned_course)]
