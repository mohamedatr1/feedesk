"""Read-only reconciliation and operations queries.

Every function here is side-effect free and never re-arms a job, resends an
unknown message, or mutates provider state.  Responses are deliberately
limited to masked phones and redacted payloads so the ops surface can be
shared with administrators without leaking message bodies, full phone numbers,
claim tokens, or credentials.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import (
    AuditEvent,
    Campaign,
    CampaignRecipient,
    Message,
    ProviderEvent,
    SendJob,
)
from ..privacy import mask_phone
from .credentials import credential_status
from .factory import provider_name, transport_configuration_error
from .queries import get_message
from .status import MESSAGE_STATUSES

JOB_STATUSES = frozenset(
    {"pending", "retry", "claimed", "completed", "failed", "unknown", "cancelled"}
)
ISSUE_KINDS = frozenset({"unknown", "failed"})
RECENT_AUDIT_LIMIT = 20


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _status_counts(db: Session, model: Any, column: Any) -> dict[str, int]:
    rows = db.execute(select(column, func.count()).group_by(column)).all()
    return {str(status): int(count) for status, count in rows if status is not None}


def _due_condition(now: datetime) -> Any:
    return and_(
        SendJob.status.in_(("pending", "retry")),
        or_(
            SendJob.next_attempt_at.is_(None),
            SendJob.next_attempt_at <= now,
        ),
    )


def _stale_condition(now: datetime) -> Any:
    return and_(
        SendJob.status == "claimed",
        SendJob.lease_expires_at.is_not(None),
        SendJob.lease_expires_at <= now,
    )


def _queue_summary(db: Session) -> dict[str, Any]:
    now = _utcnow()
    by_job_status = _status_counts(db, SendJob, SendJob.status)
    due_now = db.scalar(
        select(func.count()).select_from(SendJob).where(_due_condition(now))
    ) or 0
    stale_claims = db.scalar(
        select(func.count()).select_from(SendJob).where(_stale_condition(now))
    ) or 0
    return {
        "by_job_status": by_job_status,
        "pending": by_job_status.get("pending", 0),
        "claimed": by_job_status.get("claimed", 0),
        "retry": by_job_status.get("retry", 0),
        "due_now": int(due_now),
        "stale_claims": int(stale_claims),
        "oldest_pending_at": db.scalar(
            select(func.min(SendJob.created_at)).where(SendJob.status == "pending")
        ),
        "next_attempt_at": db.scalar(
            select(func.min(SendJob.next_attempt_at)).where(
                SendJob.status.in_(("pending", "retry")),
                SendJob.next_attempt_at.is_not(None),
            )
        ),
    }


def _message_summary(db: Session) -> dict[str, Any]:
    by_status = {status: 0 for status in MESSAGE_STATUSES}
    by_status.update(_status_counts(db, Message, Message.internal_status))
    total = sum(by_status.values())
    reconciliation_required = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.internal_status == "unknown")
    ) or 0
    return {
        "by_status": by_status,
        "total": total,
        "failed": by_status.get("failed", 0),
        "unknown": by_status.get("unknown", 0),
        "reconciliation_required": int(reconciliation_required),
    }


def _campaign_summary(db: Session) -> dict[str, Any]:
    by_status = _status_counts(db, Campaign, Campaign.status)
    return {
        "by_status": by_status,
        "sending": by_status.get("sending", 0),
    }


def _provider_summary(db: Session) -> dict[str, Any]:
    name = provider_name()
    credential = credential_status(db)
    configured = bool(credential["configured"])
    error = credential["credential_error"]
    if name == "fake":
        # Fake mode needs no credential; do not surface an incomplete-vault
        # message as an operational failure.
        error = None
    elif not configured and not error:
        error = (
            transport_configuration_error()
            or "Provider credentials are not configured."
        )
    return {
        "name": name,
        "configured": configured,
        "credential_source": credential["credential_source"],
        "key_version": credential["key_version"],
        "credential_error": error,
    }


def _provider_event_summary(db: Session) -> dict[str, Any]:
    unprocessed = db.scalar(
        select(func.count())
        .select_from(ProviderEvent)
        .where(ProviderEvent.processed_at.is_(None))
    ) or 0
    return {
        "unprocessed": int(unprocessed),
        "last_received_at": db.scalar(select(func.max(ProviderEvent.received_at))),
    }


def summary(db: Session) -> dict[str, Any]:
    """Return the admin reconciliation dashboard payload."""
    return {
        "generated_at": _utcnow(),
        "provider": _provider_summary(db),
        "queue": _queue_summary(db),
        "messages": _message_summary(db),
        "campaigns": _campaign_summary(db),
        "provider_events": _provider_event_summary(db),
    }


def _row_statement() -> Any:
    return (
        select(Message, Campaign.name, Campaign.status, CampaignRecipient, SendJob)
        .join(Campaign, Message.campaign_id == Campaign.id)
        .join(CampaignRecipient, Message.campaign_recipient_id == CampaignRecipient.id)
        .outerjoin(SendJob, SendJob.message_id == Message.id)
    )


def _job_item(
    message: Message,
    campaign_name: str,
    campaign_status: str,
    recipient: CampaignRecipient,
    job: SendJob | None,
    *,
    reconciliation_required: bool | None = None,
    retry_exhausted: bool | None = None,
) -> dict[str, Any]:
    item = {
        "job_id": job.id if job is not None else None,
        "message_id": message.id,
        "campaign_id": message.campaign_id,
        "campaign_name": campaign_name,
        "campaign_status": campaign_status,
        "message_status": message.internal_status,
        "job_status": job.status if job is not None else None,
        "attempt_count": job.attempt_count if job is not None else 0,
        "next_attempt_at": job.next_attempt_at if job is not None else None,
        "lease_expires_at": job.lease_expires_at if job is not None else None,
        "heartbeat_at": job.heartbeat_at if job is not None else None,
        "locked_by": job.locked_by if job is not None else None,
        "last_error": job.last_error if job is not None else None,
        "last_error_code": message.last_error_code,
        "last_error_summary": message.last_error_summary,
        "guardian_name": recipient.guardian_name_snapshot,
        "destination_phone_masked": mask_phone(recipient.destination_phone_snapshot),
        "created_at": job.created_at if job is not None else message.created_at,
        "updated_at": job.updated_at if job is not None else message.updated_at,
    }
    if reconciliation_required is not None:
        item["reconciliation_required"] = reconciliation_required
    if retry_exhausted is not None:
        item["retry_exhausted"] = retry_exhausted
    return item


def _job_conditions(
    *,
    status: str | None,
    campaign_id: str | None,
    due_only: bool,
    stale_only: bool,
    now: datetime,
) -> list[Any]:
    conditions: list[Any] = []
    if status:
        conditions.append(SendJob.status == status)
    if campaign_id:
        conditions.append(Message.campaign_id == campaign_id)
    if due_only:
        conditions.append(_due_condition(now))
    if stale_only:
        conditions.append(_stale_condition(now))
    return conditions


def list_jobs(
    db: Session,
    *,
    status: str | None,
    campaign_id: str | None,
    due_only: bool,
    stale_only: bool,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """List send jobs without claim tokens or full phone numbers."""
    now = _utcnow()
    conditions = _job_conditions(
        status=status,
        campaign_id=campaign_id,
        due_only=due_only,
        stale_only=stale_only,
        now=now,
    )
    base = _row_statement().where(*conditions)
    total = db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Campaign, Message.campaign_id == Campaign.id)
        .join(CampaignRecipient, Message.campaign_recipient_id == CampaignRecipient.id)
        .join(SendJob, SendJob.message_id == Message.id)
        .where(*conditions)
    ) or 0
    rows = db.execute(
        base.order_by(
            SendJob.next_attempt_at.asc().nulls_first(),
            SendJob.created_at.asc(),
            SendJob.id.asc(),
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            _job_item(message, campaign_name, campaign_status, recipient, job)
            for message, campaign_name, campaign_status, recipient, job in rows
        ],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def list_issues(
    db: Session,
    *,
    kind: str,
    campaign_id: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    """List unknown or failed messages that may need manual reconciliation."""
    conditions: list[Any] = [Message.internal_status == kind]
    if campaign_id:
        conditions.append(Message.campaign_id == campaign_id)
    base = _row_statement().where(*conditions)
    total = db.scalar(
        select(func.count())
        .select_from(Message)
        .join(Campaign, Message.campaign_id == Campaign.id)
        .join(CampaignRecipient, Message.campaign_recipient_id == CampaignRecipient.id)
        .where(*conditions)
    ) or 0
    rows = db.execute(
        base.order_by(Message.created_at.desc(), Message.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    max_attempts = max(1, int(settings.messaging_max_attempts))
    items = []
    for message, campaign_name, campaign_status, recipient, job in rows:
        attempts = job.attempt_count if job is not None else 0
        retry_exhausted = bool(
            job is not None
            and job.status == "failed"
            and attempts >= max_attempts
        )
        items.append(
            _job_item(
                message,
                campaign_name,
                campaign_status,
                recipient,
                job,
                reconciliation_required=(message.internal_status == "unknown"),
                retry_exhausted=retry_exhausted,
            )
        )
    return {
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


def _job_detail(job: SendJob | None) -> dict[str, Any] | None:
    if job is None:
        return None
    return {
        "job_id": job.id,
        "status": job.status,
        "attempt_count": job.attempt_count,
        "next_attempt_at": job.next_attempt_at,
        "lease_expires_at": job.lease_expires_at,
        "heartbeat_at": job.heartbeat_at,
        "locked_by": job.locked_by,
        "last_error": job.last_error,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }


def _provider_events(db: Session, provider_message_id: str | None) -> list[dict[str, Any]]:
    if not provider_message_id:
        return []
    events = db.scalars(
        select(ProviderEvent)
        .where(ProviderEvent.provider_message_id == provider_message_id)
        .order_by(ProviderEvent.received_at.desc(), ProviderEvent.id.desc())
        .limit(50)
    ).all()
    return [
        {
            "id": event.id,
            "provider": event.provider,
            "provider_event_id": event.provider_event_id,
            "provider_message_id": event.provider_message_id,
            "event_type": event.event_type,
            "event_payload_redacted": dict(event.event_payload_redacted or {}),
            "received_at": event.received_at,
            "processed_at": event.processed_at,
        }
        for event in events
    ]


def _recent_audit_actions(db: Session, message_id: str) -> list[dict[str, Any]]:
    # Action metadata only: audit before/after payloads can contain identifiers
    # that the ops surface does not need.
    rows = db.execute(
        select(AuditEvent.action, AuditEvent.created_at)
        .where(
            AuditEvent.entity_type == "message",
            AuditEvent.entity_id == message_id,
        )
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(RECENT_AUDIT_LIMIT)
    ).all()
    return [
        {"action": action, "created_at": created_at}
        for action, created_at in rows
    ]


def get_message_detail(db: Session, message_id: str) -> dict[str, Any] | None:
    """Return a masked message detail with job, events, and audit actions."""
    payload = get_message(db, message_id)
    if payload is None:
        return None
    # Full phone and body are intentionally removed from the ops surface.
    payload.pop("destination_phone", None)
    payload.pop("message_body_snapshot", None)
    job = db.scalar(select(SendJob).where(SendJob.message_id == message_id))
    payload["job"] = _job_detail(job)
    payload["provider_events"] = _provider_events(db, payload.get("provider_message_id"))
    payload["recent_audit_actions"] = _recent_audit_actions(db, message_id)
    return payload
