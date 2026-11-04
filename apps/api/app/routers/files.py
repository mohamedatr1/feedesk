from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import settings
from ..db import get_db
from ..deps import require_permission
from ..errors import ApiError
from ..models import SourceFile, User

router = APIRouter(prefix="/files", tags=["files"])


def _safe_path(storage_key: str) -> Path:
    root = Path(settings.upload_dir).resolve()
    candidate = (root / storage_key).resolve()
    if candidate != root and root not in candidate.parents:
        raise ApiError(400, "INVALID_PATH", "مسار الملف غير صالح.", "Invalid file path.")
    return candidate


@router.get("/{file_id}")
def download_file(
    file_id: str,
    request: Request,
    current: User = Depends(require_permission("files.download")),
    db: Session = Depends(get_db),
) -> FileResponse:
    row = db.get(SourceFile, file_id)
    if row is None:
        raise ApiError(404, "FILE_NOT_FOUND", "الملف غير موجود.", "File not found.")
    path = _safe_path(row.storage_key)
    if not path.exists() or not path.is_file():
        raise ApiError(404, "FILE_NOT_FOUND", "الملف غير موجود.", "File not found.")
    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="file.download",
        entity_type="source_file",
        entity_id=row.id,
    )
    db.commit()
    return FileResponse(
        path,
        media_type=row.content_type,
        filename=row.original_filename,
    )
