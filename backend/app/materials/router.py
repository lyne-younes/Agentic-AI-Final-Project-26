from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser, DbSession
from app.courses.dependencies import OwnedCourse
from app.materials import extraction, storage
from app.materials.schemas import (
    MaterialDetail,
    MaterialOut,
    MaterialUpdate,
    NoteCreate,
    normalize_tags,
)
from app.models import Course, IndexingStatus, Material, MaterialType
from app.rag import indexing

router = APIRouter(tags=["materials"])

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MEDIA_TYPES = {
    MaterialType.pdf: "application/pdf",
    MaterialType.docx: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    MaterialType.text_file: "text/plain; charset=utf-8",
}


async def get_owned_material(material_id: int, user: CurrentUser, db: DbSession) -> Material:
    material = await db.scalar(
        select(Material)
        .join(Course, Course.id == Material.course_id)
        .where(Material.id == material_id, Course.user_id == user.id)
    )
    if material is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Material not found")
    return material


OwnedMaterial = Annotated[Material, Depends(get_owned_material)]


async def _commit_or_duplicate_title(db: AsyncSession, title: str) -> None:
    """Commit, turning the `uq_materials_course_id_lower_title` violation into a 409."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f'This course already has a material named "{title}".'
        ) from exc


@router.get("/courses/{course_id}/materials")
async def list_materials(
    course: OwnedCourse, db: DbSession, tag: str | None = None
) -> list[MaterialOut]:
    statement = (
        select(Material).where(Material.course_id == course.id).order_by(Material.created_at.desc())
    )
    if tag:
        statement = statement.where(Material.tags.contains([tag]))
    return [MaterialOut.model_validate(material) for material in await db.scalars(statement)]


@router.post("/courses/{course_id}/materials", status_code=status.HTTP_201_CREATED)
async def upload_material(
    course: OwnedCourse,
    db: DbSession,
    background_tasks: BackgroundTasks,
    file: UploadFile,
    title: Annotated[str | None, Form(max_length=200)] = None,
    tags: Annotated[list[str] | None, Form()] = None,
) -> MaterialOut:
    filename = file.filename or ""
    material_type = extraction.material_type_for(filename)
    if material_type is None:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "Upload a PDF, Word (.docx), or text (.txt, .md) file",
        )

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Files must be 25 MB or smaller")

    try:
        raw_text = extraction.extract_text(data, material_type)
        clean_tags = normalize_tags(tags or [])
    except (extraction.ExtractionError, ValueError) as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc

    suffix = Path(filename).suffix.lower()
    material = Material(
        course_id=course.id,
        type=material_type,
        title=(title or "").strip() or Path(filename).stem,
        file_path=storage.save_file(course.id, data, suffix),
        raw_text=raw_text,
        tags=clean_tags,
    )
    db.add(material)
    await _commit_or_duplicate_title(db, material.title)
    await db.refresh(material)

    # Extraction is quick and done inline; chunking + embedding runs after the response.
    background_tasks.add_task(indexing.index_material, material.id)
    return MaterialOut.model_validate(material)


@router.post("/courses/{course_id}/materials/note", status_code=status.HTTP_201_CREATED)
async def create_note(
    body: NoteCreate, course: OwnedCourse, db: DbSession, background_tasks: BackgroundTasks
) -> MaterialOut:
    material = Material(
        course_id=course.id,
        type=MaterialType.authored_note,
        title=body.title,
        raw_text=body.content,
        tags=body.tags,
    )
    db.add(material)
    await _commit_or_duplicate_title(db, material.title)
    await db.refresh(material)
    background_tasks.add_task(indexing.index_material, material.id)
    return MaterialOut.model_validate(material)


@router.get("/materials/{material_id}")
async def get_material(material: OwnedMaterial) -> MaterialDetail:
    return MaterialDetail.model_validate(material)


@router.patch("/materials/{material_id}")
async def update_material(
    body: MaterialUpdate,
    material: OwnedMaterial,
    db: DbSession,
    background_tasks: BackgroundTasks,
) -> MaterialDetail:
    changes = body.model_dump(exclude_unset=True)
    content = changes.pop("content", None)
    reindex = False

    if content is not None:
        if material.type != MaterialType.authored_note:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Only in-app notes can be edited. Upload a new version of the file instead.",
            )
        if content != material.raw_text:
            material.raw_text = content
            material.indexing_status = IndexingStatus.pending
            reindex = True

    for field, value in changes.items():
        setattr(material, field, value)
    await _commit_or_duplicate_title(db, material.title)
    await db.refresh(material)

    if reindex:
        background_tasks.add_task(indexing.index_material, material.id)
    return MaterialDetail.model_validate(material)


@router.delete("/materials/{material_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(material: OwnedMaterial, db: DbSession) -> None:
    file_path = material.file_path
    await db.delete(material)  # chunks go with it via ON DELETE CASCADE
    await db.commit()
    if file_path:
        storage.delete_file(file_path)


@router.get("/materials/{material_id}/file")
async def get_material_file(material: OwnedMaterial) -> FileResponse:
    if material.file_path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This material is a note, not a file")
    path = storage.absolute_path(material.file_path)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "The uploaded file is missing")
    return FileResponse(
        path,
        media_type=MEDIA_TYPES[material.type],
        filename=f"{material.title}{path.suffix}",
        content_disposition_type="inline",  # PDFs open in a browser tab instead of downloading
    )


@router.post("/materials/{material_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_material(
    material: OwnedMaterial, db: DbSession, background_tasks: BackgroundTasks
) -> MaterialOut:
    material.indexing_status = IndexingStatus.pending
    await db.commit()
    await db.refresh(material)
    background_tasks.add_task(indexing.index_material, material.id)
    return MaterialOut.model_validate(material)
