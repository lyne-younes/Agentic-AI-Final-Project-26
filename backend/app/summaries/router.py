from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.auth.dependencies import DbSession
from app.courses.dependencies import OwnedCourse
from app.models import Summary, SummaryHistory
from app.summaries.schemas import SummaryHistoryOut, SummaryOut, SummaryUpdate

router = APIRouter(tags=["summaries"])


@router.get("/courses/{course_id}/summary")
async def get_summary(course: OwnedCourse, db: DbSession) -> SummaryOut:
    summary = await db.scalar(select(Summary).where(Summary.course_id == course.id))
    if summary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No summary yet for this course")
    return SummaryOut.model_validate(summary)


@router.patch("/courses/{course_id}/summary")
async def update_summary(body: SummaryUpdate, course: OwnedCourse, db: DbSession) -> SummaryOut:
    summary = await db.scalar(select(Summary).where(Summary.course_id == course.id))
    if summary is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No summary yet for this course")
    summary.content = body.content
    summary.is_edited = True
    await db.commit()
    await db.refresh(summary)
    return SummaryOut.model_validate(summary)


@router.get("/courses/{course_id}/summary/history")
async def list_summary_history(course: OwnedCourse, db: DbSession) -> list[SummaryHistoryOut]:
    rows = await db.scalars(
        select(SummaryHistory)
        .where(SummaryHistory.course_id == course.id)
        .order_by(SummaryHistory.version_number.desc())
    )
    return [SummaryHistoryOut.model_validate(row) for row in rows]
