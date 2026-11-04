from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_permission
from ..models import AuditEvent, User
from ..schemas import AuditListOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditListOut)
def list_audit(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _: User = Depends(require_permission("audit.view")),
    db: Session = Depends(get_db),
) -> AuditListOut:
    total = db.scalar(select(func.count()).select_from(AuditEvent)) or 0
    items = list(
        db.scalars(
            select(AuditEvent)
            .order_by(AuditEvent.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return AuditListOut(items=items, total=total, page=page, page_size=page_size)
