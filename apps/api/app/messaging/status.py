from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Campaign, Message, SendJob

MESSAGE_STATUSES = (
    "pending",
    "submitting",
    "provider_accepted",
    "queued_by_provider",
    "delivered",
    "failed",
    "unknown",
    "cancelled",
)

TERMINAL_MESSAGE_STATUSES = frozenset(
    {
        "provider_accepted",
        "queued_by_provider",
        "delivered",
        "failed",
        "unknown",
        "cancelled",
    }
)

ACTIVE_JOB_STATUSES = frozenset({"pending", "retry", "claimed"})

DERIVABLE_CAMPAIGN_STATUSES = frozenset(
    {"approved", "queued", "sending", "completed", "completed_with_errors", "failed"}
)


def empty_counts() -> dict[str, int]:
    return {status: 0 for status in MESSAGE_STATUSES}


def message_counts(db: Session, campaign_id: str) -> dict[str, int]:
    counts = empty_counts()
    rows = db.execute(
        select(Message.internal_status, func.count())
        .where(Message.campaign_id == campaign_id)
        .group_by(Message.internal_status)
    ).all()
    for status, count in rows:
        if status in counts:
            counts[status] = int(count)
        else:
            counts[status] = int(count)
    return counts


def derive_campaign_status(db: Session, campaign_id: str) -> str | None:
    """Derive and persist campaign status from message/job outcomes.

    The caller owns the transaction. Never treats provider acceptance as
    delivery, and never marks a campaign successful while work is outstanding.
    """
    campaign = db.get(Campaign, campaign_id)
    if campaign is None:
        return None
    if campaign.status == "cancelled" or campaign.cancelled_at is not None:
        return campaign.status
    if campaign.status not in DERIVABLE_CAMPAIGN_STATUSES:
        return campaign.status

    counts = message_counts(db, campaign_id)
    total = sum(counts.values())
    if total == 0:
        return campaign.status

    active_jobs = db.scalar(
        select(func.count())
        .select_from(SendJob)
        .join(Message, SendJob.message_id == Message.id)
        .where(
            Message.campaign_id == campaign_id,
            SendJob.status.in_(tuple(ACTIVE_JOB_STATUSES)),
        )
    ) or 0
    active_messages = counts.get("pending", 0) + counts.get("submitting", 0)

    if active_jobs or active_messages:
        new_status = "sending"
    elif counts.get("cancelled", 0) == total:
        new_status = "cancelled"
    elif counts.get("failed", 0) == total:
        new_status = "failed"
    elif counts.get("failed", 0) or counts.get("unknown", 0):
        new_status = "completed_with_errors"
    else:
        new_status = "completed"

    if campaign.status != new_status:
        campaign.status = new_status
    return new_status
