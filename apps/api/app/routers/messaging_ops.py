"""Admin-only, read-only messaging operations/reconciliation API.

Every route is GET-only and is protected by ``settings.manage``.  There are no
action endpoints: operators can inspect unknown/failed work but the API can
never re-arm a job, resend an unknown message, or mutate a credential.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_permission
from ..errors import ApiError
from ..messaging import ops
from ..models import User

router = APIRouter(prefix="/messaging/ops", tags=["messaging-ops"])


def _validation_error(message_ar: str, message_en: str) -> ApiError:
    return ApiError(422, "VALIDATION_ERROR", message_ar, message_en)


@router.get("/summary")
def read_summary(
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> dict:
    return ops.summary(db)


@router.get("/jobs")
def read_jobs(
    status: str | None = Query(default=None, max_length=32),
    campaign_id: str | None = Query(default=None, max_length=36),
    due_only: bool = Query(default=False),
    stale_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> dict:
    if status is not None and status not in ops.JOB_STATUSES:
        raise _validation_error(
            "حالة المهمة غير صالحة.",
            "Invalid job status filter.",
        )
    return ops.list_jobs(
        db,
        status=status,
        campaign_id=campaign_id,
        due_only=due_only,
        stale_only=stale_only,
        page=page,
        page_size=page_size,
    )


@router.get("/issues")
def read_issues(
    kind: str = Query(default="unknown", max_length=16),
    campaign_id: str | None = Query(default=None, max_length=36),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> dict:
    if kind not in ops.ISSUE_KINDS:
        raise _validation_error(
            "نوع المشكلة غير صالح.",
            "Invalid issue kind filter.",
        )
    return ops.list_issues(
        db,
        kind=kind,
        campaign_id=campaign_id,
        page=page,
        page_size=page_size,
    )


@router.get("/messages/{message_id}")
def read_message_detail(
    message_id: str,
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> dict:
    payload = ops.get_message_detail(db, message_id)
    if payload is None:
        raise ApiError(
            404,
            "MESSAGE_NOT_FOUND",
            "الرسالة غير موجودة.",
            "Message not found.",
        )
    return payload
