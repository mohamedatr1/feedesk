from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_permission
from ..errors import ApiError
from ..messaging import queries
from ..messaging.status import MESSAGE_STATUSES
from ..models import User
from ..schemas import MessageDetailOut, MessageListOut

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("", response_model=MessageListOut)
def list_messages(
    campaign_id: str | None = Query(default=None, max_length=36),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=120),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission("messages.view")),
    db: Session = Depends(get_db),
) -> dict:
    if status is not None and status not in MESSAGE_STATUSES:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "حالة الرسالة غير صالحة.",
            "Invalid message status filter.",
        )
    return queries.list_messages(
        db,
        campaign_id=campaign_id,
        status=status,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/{message_id}", response_model=MessageDetailOut)
def get_message(
    message_id: str,
    _: User = Depends(require_permission("messages.view")),
    db: Session = Depends(get_db),
) -> dict:
    payload = queries.get_message(db, message_id)
    if payload is None:
        raise ApiError(
            404,
            "MESSAGE_NOT_FOUND",
            "الرسالة غير موجودة.",
            "Message not found.",
        )
    return payload
