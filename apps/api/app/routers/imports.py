from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_csrf, require_permission
from ..errors import ApiError
from ..imports import service, storage
from ..imports.constants import CANONICAL_FIELDS, MESSAGES_AR
from ..models import ImportBatch, StagedRow, User
from ..schemas import (
    ImportConfirmRequest,
    ImportDetailOut,
    ImportListOut,
    ImportProcessRequest,
    ImportRowPatch,
    ImportRowsBulkExclusionRequest,
    ImportRowsOut,
    StagedRowOut,
)

router = APIRouter(prefix="/imports", tags=["imports"])

_ROW_STATUSES = {"valid", "warning", "invalid", "excluded"}
_BATCH_STATUSES = {
    "uploaded",
    "processing",
    "review_required",
    "ready_to_confirm",
    "confirmed",
    "cancelled",
    "failed",
}


def _mapping_from_form(raw: str | None) -> dict[str, str] | None:
    if raw is None or not raw.strip():
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ApiError(
            422,
            "INVALID_MAPPING",
            MESSAGES_AR["INVALID_MAPPING"],
            "mapping must be a JSON object of canonical field to source header.",
        ) from exc
    if not isinstance(parsed, dict):
        raise ApiError(
            422,
            "INVALID_MAPPING",
            MESSAGES_AR["INVALID_MAPPING"],
            "mapping must be a JSON object.",
        )
    for key, value in parsed.items():
        if key not in CANONICAL_FIELDS or not isinstance(value, str):
            raise ApiError(
                422,
                "INVALID_MAPPING",
                MESSAGES_AR["INVALID_MAPPING"],
                "mapping keys must be canonical fields and values must be header text.",
                {"invalid_key": key},
            )
    return parsed


@router.post("", response_model=ImportDetailOut, status_code=201)
async def upload_import(
    request: Request,
    file: UploadFile = File(...),
    worksheet_name: str | None = Form(default=None),
    mapping: str | None = Form(default=None),
    force_duplicate: bool = Form(default=False),
    duplicate_reason: str | None = Form(default=None),
    current: User = Depends(require_permission("imports.upload")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    data = await storage.read_upload(file)
    batch = service.create_import(
        db,
        request=request,
        user=current,
        filename=file.filename or "statement.xlsx",
        content_type=file.content_type,
        data=data,
        worksheet_name=worksheet_name,
        mapping=_mapping_from_form(mapping),
        force_duplicate=force_duplicate,
        duplicate_reason=duplicate_reason,
    )
    return service.batch_detail(db, batch)


@router.get("", response_model=ImportListOut)
def list_imports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    _: User = Depends(require_permission("imports.view")),
    db: Session = Depends(get_db),
) -> dict:
    if status is not None and status not in _BATCH_STATUSES:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "حالة الاستيراد غير صالحة.",
            "Invalid import status filter.",
        )
    conditions = []
    if status:
        conditions.append(ImportBatch.status == status)
    total = db.scalar(
        select(func.count()).select_from(ImportBatch).where(*conditions)
    ) or 0
    items = list(
        db.scalars(
            select(ImportBatch)
            .where(*conditions)
            .order_by(ImportBatch.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {
        "items": [service.batch_summary(db, batch) for batch in items],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


@router.get("/{import_id}", response_model=ImportDetailOut)
def get_import(
    import_id: str,
    _: User = Depends(require_permission("imports.view")),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.get_batch(db, import_id)
    return service.batch_detail(db, batch)


@router.get("/{import_id}/rows", response_model=ImportRowsOut)
def list_import_rows(
    import_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=200),
    _: User = Depends(require_permission("imports.view")),
    db: Session = Depends(get_db),
) -> dict:
    if status is not None and status not in _ROW_STATUSES:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "حالة الصف غير صالحة.",
            "Invalid staged row status filter.",
        )
    batch = service.get_batch(db, import_id)
    rows, total = service.list_rows(
        db,
        batch,
        page=page,
        page_size=page_size,
        status=status,
        query=q,
    )
    return {
        "items": [service.row_payload(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{import_id}/guardian-candidates")
def list_guardian_candidates(
    import_id: str,
    _: User = Depends(require_permission("imports.view")),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.get_batch(db, import_id)
    return service.guardian_candidates(db, batch)


@router.post("/{import_id}/process", response_model=ImportDetailOut)
def process_import(
    import_id: str,
    payload: ImportProcessRequest,
    request: Request,
    current: User = Depends(require_permission("imports.review")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.get_batch(db, import_id)
    if payload.mapping:
        invalid = sorted(set(payload.mapping) - set(CANONICAL_FIELDS))
        if invalid:
            raise ApiError(
                422,
                "INVALID_MAPPING",
                MESSAGES_AR["INVALID_MAPPING"],
                "mapping keys must be canonical fields.",
                {"fields": invalid},
            )
    batch = service.process_import(
        db,
        batch,
        request=request,
        user=current,
        worksheet_name=payload.worksheet_name,
        mapping=payload.mapping,
    )
    return service.batch_detail(db, batch)


@router.post("/{import_id}/rows/exclusion", response_model=ImportDetailOut)
def bulk_exclude_import_rows(
    import_id: str,
    payload: ImportRowsBulkExclusionRequest,
    request: Request,
    current: User = Depends(require_permission("imports.review")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.get_batch(db, import_id)
    batch = service.bulk_set_row_exclusion(
        db,
        batch,
        request=request,
        user=current,
        is_excluded=payload.is_excluded,
        scope=payload.scope,
        row_ids=payload.row_ids,
    )
    return service.batch_detail(db, batch)


@router.patch("/{import_id}/rows/{row_id}", response_model=StagedRowOut)
def patch_import_row(
    import_id: str,
    row_id: str,
    payload: ImportRowPatch,
    request: Request,
    current: User = Depends(require_permission("imports.review")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.get_batch(db, import_id)
    row = db.get(StagedRow, row_id)
    if row is None or row.import_batch_id != batch.id:
        raise ApiError(
            404,
            "ROW_NOT_FOUND",
            "الصف غير موجود.",
            "Staged row not found.",
        )
    row = service.update_row(
        db,
        batch,
        row,
        request=request,
        user=current,
        normalized_data=payload.normalized_data,
        is_excluded=payload.is_excluded,
        guardian_resolution=(
            payload.guardian_resolution.model_dump()
            if payload.guardian_resolution is not None
            else None
        ),
    )
    return service.row_payload(row)


@router.post("/{import_id}/confirm", response_model=ImportDetailOut)
def confirm_import(
    import_id: str,
    payload: ImportConfirmRequest,
    request: Request,
    current: User = Depends(require_permission("imports.confirm")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.confirm_import(
        db,
        import_id,
        request=request,
        user=current,
        acknowledge_warnings=payload.acknowledge_warnings,
    )
    return service.batch_detail(db, batch)


@router.post("/{import_id}/cancel", response_model=ImportDetailOut)
def cancel_import(
    import_id: str,
    request: Request,
    current: User = Depends(require_permission("imports.review")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    batch = service.get_batch(db, import_id)
    batch = service.cancel_import(
        db,
        batch,
        request=request,
        user=current,
    )
    return service.batch_detail(db, batch)
