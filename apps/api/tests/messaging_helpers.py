from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.config import settings as default_settings
from app.db import SessionLocal
from app.models import (
    Campaign,
    CampaignRecipient,
    Guardian,
    Message,
    SendJob,
)

DEFAULT_BODY = "عزيزنا ولي الأمر، تذكير بالرسوم الدراسية."


def messaging_config(**updates: Any) -> Settings:
    base: dict[str, Any] = {
        "messaging_provider": "fake",
        "messaging_enabled": True,
        "messaging_kill_switch": False,
        "messaging_rate_limit_per_second": 1000.0,
        "messaging_max_attempts": 3,
        "messaging_lease_seconds": 60,
        "messaging_allowlist": "",
        "fake_provider_scenario": "delivered",
        "rasel_api_key": "",
        "rasel_sender_id": "",
    }
    base.update(updates)
    return default_settings.model_copy(update=base)


def create_campaign_messages(
    specs: list[dict[str, Any]] | None = None,
    *,
    campaign_status: str = "approved",
    campaign_channel: str = "sms",
    campaign_id: str | None = None,
) -> dict[str, Any]:
    """Create a campaign with frozen recipients, messages, and send jobs."""
    campaign_id = campaign_id or str(uuid4())
    specs = specs or [{}]
    message_ids: list[str] = []
    job_ids: list[str] = []
    with SessionLocal() as db:
        campaign = Campaign(
            id=campaign_id,
            name="حملة رسائل اختبار",
            status=campaign_status,
            channel=campaign_channel,
            recipient_count=len(specs),
        )
        db.add(campaign)
        db.flush()
        for index, spec in enumerate(specs):
            guardian = Guardian(
                id=str(uuid4()),
                full_name=spec.get("guardian_name", f"ولي أمر {index + 1}"),
                normalized_name=spec.get("guardian_name", f"ولي أمر {index + 1}"),
                status="active",
            )
            db.add(guardian)
            db.flush()
            recipient_id = str(uuid4())
            recipient = CampaignRecipient(
                id=recipient_id,
                campaign_id=campaign_id,
                guardian_id=guardian.id,
                destination_phone_snapshot=spec.get("phone", f"+96399300010{index}"),
                guardian_name_snapshot=spec.get("guardian_name", f"ولي أمر {index + 1}"),
                amount_snapshot=Decimal(str(spec.get("amount", "600000"))).quantize(
                    Decimal("0.01")
                ),
                currency_snapshot=spec.get("currency", "SYP"),
                fee_details_snapshot=dict(spec.get("fee_details") or {}),
                message_body_snapshot=spec.get("body", DEFAULT_BODY),
                eligibility_status="eligible",
            )
            db.add(recipient)
            db.flush()

            message_id = str(uuid4())
            message = Message(
                id=message_id,
                campaign_id=campaign_id,
                campaign_recipient_id=recipient_id,
                provider=spec.get("provider", "fake"),
                channel=spec.get("channel", "sms"),
                internal_status=spec.get("message_status", "pending"),
                provider_status=spec.get("provider_status"),
                provider_request_id=spec.get("provider_request_id"),
                provider_message_id=spec.get("provider_message_id"),
                idempotency_key=spec.get("idempotency_key")
                or f"{campaign_id}:{recipient_id}",
                provider_payload_redacted=dict(spec.get("payload") or {}),
                submitted_at=spec.get("submitted_at"),
                delivered_at=spec.get("delivered_at"),
                failed_at=spec.get("failed_at"),
                last_error_code=spec.get("last_error_code"),
                last_error_summary=spec.get("last_error_summary"),
            )
            if spec.get("created_at") is not None:
                message.created_at = spec["created_at"]
            if spec.get("updated_at") is not None:
                message.updated_at = spec["updated_at"]
            db.add(message)
            db.flush()

            job_id = str(uuid4())
            job = SendJob(
                id=job_id,
                message_id=message_id,
                status=spec.get("job_status", "pending"),
                attempt_count=spec.get("attempt_count", 0),
                next_attempt_at=spec.get("next_attempt_at"),
                locked_at=spec.get("locked_at"),
                locked_by=spec.get("locked_by"),
                claim_token=spec.get("claim_token"),
                lease_expires_at=spec.get("lease_expires_at"),
                heartbeat_at=spec.get("heartbeat_at"),
                last_error=spec.get("last_error"),
            )
            db.add(job)
            message_ids.append(message_id)
            job_ids.append(job_id)
        db.commit()
    return {
        "campaign_id": campaign_id,
        "message_ids": message_ids,
        "job_ids": job_ids,
    }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
