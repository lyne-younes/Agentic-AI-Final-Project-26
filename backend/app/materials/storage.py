"""Uploaded files on disk, grouped per course: <UPLOAD_DIR>/<course_id>/<uuid><ext>."""

import shutil
import uuid
from pathlib import Path

from app.config import get_settings


def _root() -> Path:
    return Path(get_settings().upload_dir)


def save_file(course_id: int, data: bytes, suffix: str) -> str:
    relative = Path(str(course_id)) / f"{uuid.uuid4().hex}{suffix}"
    target = _root() / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return relative.as_posix()  # stored in materials.file_path


def absolute_path(relative: str) -> Path:
    return _root() / relative


def delete_file(relative: str) -> None:
    absolute_path(relative).unlink(missing_ok=True)


def delete_course_files(course_id: int) -> None:
    shutil.rmtree(_root() / str(course_id), ignore_errors=True)
