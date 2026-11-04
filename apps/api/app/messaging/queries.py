from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..campaigns import service as campaign_service
from ..models import Campaign, CampaignRecipient, Message, SendJob
from ..privacy import mask_phone
from .status import empty_counts, message_counts

DELIVERY_NOTE_AR = "قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط."

__all__ = ["amount_string", "campaign_results", "get_message", "list_messages", "mask_phone"]


def amount_string(value: Decimal | None) -> str:
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)).quantize(Decimal('0.01')):f}"


def _like_term(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _row_statement():
    return (
        select(Message, Campaign.name, CampaignRecipient, SendJob)
        .join(Campaign, Message.campaign_id == Campaign.id)
        .join(CampaignRecipient, Message.campaign_recipient_id == CampaignRecipient.id)
        .outerjoin(SendJob, SendJob.message_id == Message.id)
    )


def _summary(
    message: Message,
    campaign_name: str,
    recipient: CampaignRecipient,
    job: SendJob | None,
) -> dict[str, Any]:
    return {
        "id": message.id,
        "campaign_id": message.campaign_id,
        "campaign_name": campaign_name,
        "guardian_name": recipient.guardian_name_snapshot,
        "destination_phone_masked": mask_phone(
            recipient.destination_phone_snapshot
        ),
        "amount": amount_string(recipient.amount_snapshot),
        "currency": recipient.currency_snapshot,
        "channel": message.channel,
        "internal_status": message.internal_status,
        "provider_status": message.provider_status,
        "provider_message_id": message.provider_message_id,
        "last_error_code": message.last_error_code,
        "last_error_summary": message.last_error_summary,
        "submitted_at": message.submitted_at,
        "delivered_at": message.delivered_at,
        "next_attempt_at": job.next_attempt_at if job is not None else None,
        "created_at": message.created_at,
        "updated_at": message.updated_at,
    }


def list_messages(
    db: Session,
    *,
    campaign_id: str | None,
    status: str | None,
    q: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    conditions = []
    if campaign_id:
        conditions.append(Message.campaign_id == campaign_id)
    if status:
        conditions.append(Message.internal_status == status)
    if q and q.strip():
        term = _like_term(q.strip())
        conditions.append(
            or_(
                CampaignRecipient.guardian_name_snapshot.ilike(term, escape="\\"),
                CampaignRecipient.destination_phone_snapshot.ilike(term, escape="\\"),
            )
        )

    total = db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Campaign, Message.campaign_id == Campaign.id)
        .join(CampaignRecipient, Message.campaign_recipient_id == CampaignRecipient.id)
        .where(*conditions)
    ) or 0

    rows = db.execute(
        _row_statement()
        .where(*conditions)
        .order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    return {
        "items": [
            _summary(message, campaign_name, recipient, job)
            for message, campaign_name, recipient, job in rows
        ],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def get_message(db: Session, message_id: str) -> dict[str, Any] | None:
    row = db.execute(_row_statement().where(Message.id == message_id)).first()
    if row is None:
        return None
    message, campaign_name, recipient, job = row
    payload = _summary(message, campaign_name, recipient, job)
    payload.update(
        {
            "destination_phone": recipient.destination_phone_snapshot,
            "message_body_snapshot": recipient.message_body_snapshot,
            "provider_request_id": message.provider_request_id,
            "provider_payload_redacted": dict(message.provider_payload_redacted or {}),
            "attempt_count": job.attempt_count if job is not None else 0,
        }
    )
    return payload


def campaign_results(db: Session, campaign: Campaign) -> dict[str, Any]:
    payload = campaign_service.campaign_summary(db, campaign)
    counts = message_counts(db, campaign.id)
    for status in empty_counts():
        counts.setdefault(status, 0)
    last_activity_at: datetime | None = db.scalar(
        select(func.max(Message.updated_at)).where(Message.campaign_id == campaign.id)
    )
    payload.update(
        {
            "message_count": sum(counts.values()),
            "counts": counts,
            "last_activity_at": last_activity_at or campaign.updated_at,
            "delivery_note_ar": DELIVERY_NOTE_AR,
        }
    )
    return payload
