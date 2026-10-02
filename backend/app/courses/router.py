from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, DbSession
from app.courses.dependencies import OwnedCourse
from app.courses.schemas import CourseCreate, CourseListItem, CourseOut, CourseUpdate
from app.materials import storage
from app.models import (
    ChatMessage,
    ChatSession,
    Course,
    FlashcardSet,
    IndexingStatus,
    Material,
    Quiz,
    QuizAttempt,
)

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("")
async def list_courses(user: CurrentUser, db: DbSession) -> list[CourseListItem]:
    """Courses plus the figures shown on their cards (indexing status, counts, latest activity)."""

    def count(model, *where):
        return select(func.count()).select_from(model).where(*where).scalar_subquery()

    def materials_with(status_: IndexingStatus):
        return count(Material, Material.course_id == Course.id, Material.indexing_status == status_)

    last_message = (
        select(func.max(ChatMessage.created_at))
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.course_id == Course.id)
        .scalar_subquery()
    )
    last_chat_session = (
        select(ChatMessage.session_id)
        .join(ChatSession, ChatSession.id == ChatMessage.session_id)
        .where(ChatSession.course_id == Course.id)
        .order_by(ChatMessage.id.desc())
        .limit(1)
        .scalar_subquery()
    )
    last_attempt = (
        select(func.max(QuizAttempt.attempted_at))
        .join(Quiz, Quiz.id == QuizAttempt.quiz_id)
        .where(Quiz.course_id == Course.id)
        .scalar_subquery()
    )
    last_material = (
        select(func.max(Material.updated_at))
        .where(Material.course_id == Course.id)
        .scalar_subquery()
    )

    rows = await db.execute(
        select(
            Course,
            count(Material, Material.course_id == Course.id),
            materials_with(IndexingStatus.pending),
            materials_with(IndexingStatus.failed),
            count(Quiz, Quiz.course_id == Course.id),
            count(FlashcardSet, FlashcardSet.course_id == Course.id),
            last_message,
            last_chat_session,
            last_attempt,
            last_material,
        )
        .where(Course.user_id == user.id)
        .order_by(Course.created_at.desc())
    )
    items = []
    for (
        course,
        material_count,
        pending,
        failed,
        quizzes,
        flashcard_sets,
        chat_at,
        chat_session_id,
        attempt_at,
        material_at,
    ) in rows.all():
        moments = [moment for moment in (chat_at, attempt_at, material_at) if moment is not None]
        items.append(
            CourseListItem(
                **_to_out(course, material_count).model_dump(),
                materials_pending=pending,
                materials_failed=failed,
                quiz_count=quizzes,
                flashcard_set_count=flashcard_sets,
                last_activity_at=max(moments) if moments else None,
                last_chat_session_id=chat_session_id,
                last_chat_at=chat_at,
            )
        )
    return items


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_course(body: CourseCreate, user: CurrentUser, db: DbSession) -> CourseOut:
    course = Course(user_id=user.id, **body.model_dump())
    db.add(course)
    await _commit_or_duplicate_name(db, body.name)
    await db.refresh(course)
    return _to_out(course, 0)


@router.get("/{course_id}")
async def get_course(course: OwnedCourse, db: DbSession) -> CourseOut:
    return _to_out(course, await _material_count(db, course.id))


@router.patch("/{course_id}")
async def update_course(body: CourseUpdate, course: OwnedCourse, db: DbSession) -> CourseOut:
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(course, field, value)
    await _commit_or_duplicate_name(db, course.name)
    await db.refresh(course)
    return _to_out(course, await _material_count(db, course.id))


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(course: OwnedCourse, db: DbSession) -> None:
    course_id = course.id
    await db.delete(course)  # materials and chunks go with it via ON DELETE CASCADE
    await db.commit()
    storage.delete_course_files(course_id)


async def _commit_or_duplicate_name(db: AsyncSession, name: str) -> None:
    """Commit, turning the `uq_courses_user_id_lower_name` violation into a 409."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f'You already have a course named "{name}".'
        ) from exc


async def _material_count(db: AsyncSession, course_id: int) -> int:
    count = await db.scalar(
        select(func.count()).select_from(Material).where(Material.course_id == course_id)
    )
    return count or 0


def _to_out(course: Course, material_count: int) -> CourseOut:
    return CourseOut.model_validate(course).model_copy(update={"material_count": material_count})
