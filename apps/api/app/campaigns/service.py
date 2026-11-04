from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Request
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..errors import ApiError
from ..models import (
    Campaign,
    CampaignRecipient,
    ImportBatch,
    Message,
    MessageTemplate,
    SchoolSettings,
    SendJob,
    User,
)
from ..privacy import mask_phone
from ..security import user_has_permission
from .constants import MESSAGES_AR
from .eligibility import build_preview
from .rendering import find_unknown_variables

_CAMPAIGNABLE_STATUSES = {"draft", "awaiting_approval", "approved"}
_CANCELLABLE_STATUSES = {"draft", "awaiting_approval", "approved"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _username(db: Session, user_id: str | None) -> str | None:
    if not user_id:
        return None
    return db.scalar(select(User.username).where(User.id == user_id))


def _template_body_preview(body: str) -> str:
    return " ".join((body or "").split())[:180]


def _template_summary(db: Session, template: MessageTemplate) -> dict[str, Any]:
    return {
        "id": template.id,
        "name": template.name,
        "language": template.language,
        "channel": template.channel,
        "version": template.version,
        "is_active": template.is_active,
        "body_preview": _template_body_preview(template.template_body),
        "unknown_variables": find_unknown_variables(template.template_body),
        "created_by_name": _username(db, template.created_by),
        "created_at": template.created_at,
    }


def template_summary(db: Session, template: MessageTemplate) -> dict[str, Any]:
    return _template_summary(db, template)


def template_detail(db: Session, template: MessageTemplate) -> dict[str, Any]:
    payload = _template_summary(db, template)
    payload["template_body"] = template.template_body
    return payload


def get_template(db: Session, template_id: str) -> MessageTemplate:
    template = db.get(MessageTemplate, template_id)
    if template is None:
        raise ApiError(
            404,
            "TEMPLATE_NOT_FOUND",
            MESSAGES_AR["TEMPLATE_NOT_FOUND_404"],
            "Template not found.",
        )
    return template


def active_template(db: Session, *, channel: str = "sms", language: str = "ar") -> MessageTemplate:
    template = db.scalar(
        select(MessageTemplate)
        .where(
            MessageTemplate.channel == channel,
            MessageTemplate.language == language,
            MessageTemplate.is_active.is_(True),
        )
        .order_by(MessageTemplate.version.desc(), MessageTemplate.created_at.desc())
        .limit(1)
    )
    if template is None:
        raise ApiError(
            404,
            "TEMPLATE_NOT_FOUND",
            MESSAGES_AR["TEMPLATE_NOT_FOUND_404"],
            "No active template exists for the requested channel and language.",
        )
    return template


def create_template(
    db: Session,
    *,
    request: Request,
    user: User,
    name: str,
    language: str,
    channel: str,
    template_body: str,
) -> MessageTemplate:
    name = name.strip()
    template_body = template_body.strip()
    if not name or not template_body:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "اسم القالب ونصه مطلوبان.",
            "Template name and body are required.",
        )
    latest = db.scalar(
        select(MessageTemplate)
        .where(MessageTemplate.name == name)
        .order_by(MessageTemplate.version.desc())
        .limit(1)
    )
    version = (latest.version + 1) if latest is not None else 1
    if latest is not None:
        db.execute(
            update(MessageTemplate)
            .where(MessageTemplate.name == name)
            .values(is_active=False, updated_at=_now())
        )
    template = MessageTemplate(
        id=str(uuid4()),
        name=name,
        language=language,
        channel=channel,
        template_body=template_body,
        version=version,
        is_active=True,
        created_by=user.id,
    )
    db.add(template)
    db.flush()
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="template.create",
        entity_type="message_template",
        entity_id=template.id,
        after={
            "name": template.name,
            "language": template.language,
            "channel": template.channel,
            "version": template.version,
            "is_active": template.is_active,
            "unknown_variables": find_unknown_variables(template.template_body),
        },
    )
    db.commit()
    db.refresh(template)
    return template


def activate_template(
    db: Session,
    template: MessageTemplate,
    *,
    request: Request,
    user: User,
) -> MessageTemplate:
    before_active = template.is_active
    db.execute(
        update(MessageTemplate)
        .where(MessageTemplate.name == template.name)
        .values(is_active=False, updated_at=_now())
    )
    template.is_active = True
    template.updated_at = _now()
    db.flush()
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="template.activate",
        entity_type="message_template",
        entity_id=template.id,
        before={"is_active": before_active},
        after={"is_active": True, "version": template.version, "name": template.name},
    )
    db.commit()
    db.refresh(template)
    return template


def _school_settings(db: Session) -> SchoolSettings | None:
    return db.get(SchoolSettings, 1)


def _campaign_template(db: Session, campaign: Campaign) -> MessageTemplate | None:
    if not campaign.template_id:
        return None
    return db.get(MessageTemplate, campaign.template_id)


def _preview_for(db: Session, campaign: Campaign) -> dict[str, Any]:
    return build_preview(
        db,
        source_import_id=campaign.source_import_id,
        template=_campaign_template(db, campaign),
        school_settings=_school_settings(db),
    )


def _preview_for_storage(preview: dict[str, Any]) -> dict[str, Any]:
    payload = dict(preview)
    previewed_at = payload.get("previewed_at")
    if isinstance(previewed_at, datetime):
        payload["previewed_at"] = previewed_at.isoformat()
    return payload


def _apply_preview(campaign: Campaign, preview: dict[str, Any]) -> None:
    campaign.recipient_count = int(preview["recipient_count"])
    campaign.excluded_count = int(preview["excluded_count"])
    campaign.invalid_contact_count = int(preview["invalid_contact_count"])
    campaign.totals_by_currency = dict(preview["totals_by_currency"])
    campaign.warnings = list(preview["warnings"])
    campaign.excluded_snapshot = list(preview["excluded"])
    campaign.previewed_at = preview["previewed_at"]
    campaign.preview_snapshot = _preview_for_storage(preview)


def campaign_summary(db: Session, campaign: Campaign) -> dict[str, Any]:
    source_filename = None
    if campaign.source_import_id:
        source_filename = db.scalar(
            select(ImportBatch.source_filename).where(
                ImportBatch.id == campaign.source_import_id
            )
        )
    template_name = None
    if campaign.template_id:
        template_name = db.scalar(
            select(MessageTemplate.name).where(
                MessageTemplate.id == campaign.template_id
            )
        )
    return {
        "id": campaign.id,
        "name": campaign.name,
        "status": campaign.status,
        "channel": campaign.channel,
        "source_import_id": campaign.source_import_id,
        "source_filename": source_filename,
        "template_id": campaign.template_id,
        "template_name": template_name,
        "template_version": campaign.template_version,
        "recipient_count": campaign.recipient_count,
        "excluded_count": campaign.excluded_count,
        "invalid_contact_count": campaign.invalid_contact_count,
        "totals_by_currency": dict(campaign.totals_by_currency or {}),
        "warnings": list(campaign.warnings or []),
        "created_by": campaign.created_by,
        "created_by_name": _username(db, campaign.created_by),
        "created_at": campaign.created_at,
        "updated_at": campaign.updated_at,
        "submitted_at": campaign.submitted_at,
        "approved_by": campaign.approved_by,
        "approved_by_name": _username(db, campaign.approved_by),
        "approved_at": campaign.approved_at,
        "cancelled_at": campaign.cancelled_at,
        "cancelled_by": campaign.cancelled_by,
        "cancel_reason": campaign.cancel_reason,
        "snapshot_hash": campaign.snapshot_hash,
        "revision": campaign.revision,
    }


def _stored_recipients(db: Session, campaign: Campaign) -> list[dict[str, Any]]:
    rows = list(
        db.scalars(
            select(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign.id)
            .order_by(
                CampaignRecipient.guardian_name_snapshot.asc(),
                CampaignRecipient.guardian_id.asc(),
                CampaignRecipient.currency_snapshot.asc(),
            )
        ).all()
    )
    recipients: list[dict[str, Any]] = []
    for row in rows:
        details = dict(row.fee_details_snapshot or {})
        warnings = list(details.get("warnings") or [])
        recipients.append(
            {
                "id": row.id,
                "key": details.get("key")
                or f"{row.guardian_id}:{row.currency_snapshot}",
                "guardian_id": row.guardian_id,
                "guardian_name": row.guardian_name_snapshot,
                "phone": row.destination_phone_snapshot,
                "student_names": list(details.get("student_names") or []),
                "fee_periods": list(details.get("fee_periods") or []),
                "amount": _amount_string(row.amount_snapshot),
                "currency": row.currency_snapshot,
                "message": row.message_body_snapshot,
                "validation_status": "warning" if warnings else "valid",
                "warnings": warnings,
                "fee_balance_ids": list(details.get("fee_balance_ids") or []),
            }
        )
    return recipients


def _amount_string(value: Decimal | str | None) -> str:
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)).quantize(Decimal('0.01')):f}"


def _has_snapshots(db: Session, campaign: Campaign) -> bool:
    count = db.scalar(
        select(func.count())
        .select_from(CampaignRecipient)
        .where(CampaignRecipient.campaign_id == campaign.id)
    )
    return bool(count)


def _delivery_counts(db: Session, campaign: Campaign) -> tuple[int, int]:
    """Return created message count and currently pending job count.

    These are counts only. They never imply delivery, and they are zero until
    approval has frozen the campaign and created messages/jobs.
    """
    if campaign.status in {"draft", "awaiting_approval"}:
        return 0, 0
    message_count = db.scalar(
        select(func.count())
        .select_from(Message)
        .where(Message.campaign_id == campaign.id)
    ) or 0
    pending_job_count = db.scalar(
        select(func.count())
        .select_from(SendJob)
        .join(Message, SendJob.message_id == Message.id)
        .where(
            Message.campaign_id == campaign.id,
            SendJob.status == "pending",
        )
    ) or 0
    return int(message_count), int(pending_job_count)


def _can_cancel(campaign: Campaign, user: User) -> bool:
    if campaign.status in {"draft", "awaiting_approval"}:
        return user_has_permission(user, "campaigns.edit")
    if campaign.status == "approved":
        return user_has_permission(user, "campaigns.approve")
    return False


def _recipient_for_response(
    recipient: dict[str, Any], *, reveal: bool
) -> dict[str, Any]:
    """Serialize a recipient for detail (masked) or preview (full) mode.

    ``phone_masked`` is always list-safe.  Detail mode also replaces ``phone``
    with the masked value and removes the rendered SMS body and student names,
    so ``campaigns.view`` alone never returns bulk PII.
    """
    item = dict(recipient)
    masked = mask_phone(item.get("phone"))
    item["phone_masked"] = masked
    # Compute the count before detail mode clears the names, so the UI can show
    # a non-sensitive student count without receiving student PII.
    item["student_count"] = len(item.get("student_names") or [])
    if not reveal:
        item["phone"] = masked
        item["message"] = ""
        item["student_names"] = []
    return item


def _excluded_for_response(
    record: dict[str, Any], *, reveal: bool
) -> dict[str, Any]:
    item = dict(record)
    masked = mask_phone(item.get("phone"))
    item["phone_masked"] = masked
    if not reveal:
        item["phone"] = masked
    return item


def _campaign_detail_payload(
    payload: dict[str, Any], *, reveal: bool
) -> dict[str, Any]:
    payload["recipients"] = [
        _recipient_for_response(recipient, reveal=reveal)
        for recipient in payload.get("recipients") or []
    ]
    payload["excluded"] = [
        _excluded_for_response(record, reveal=reveal)
        for record in payload.get("excluded") or []
    ]
    return payload


def campaign_detail(
    db: Session,
    campaign: Campaign,
    user: User,
    *,
    reveal: bool = False,
) -> dict[str, Any]:
    payload = campaign_summary(db, campaign)
    stored = dict(campaign.preview_snapshot or {})
    live_statuses = {"draft", "awaiting_approval"}

    if campaign.status in live_statuses:
        preview = _preview_for(db, campaign)
        payload.update(
            {
                "template_body": preview["template_body"],
                "previewed_at": preview["previewed_at"],
                "blocking_reasons": preview["blocking_reasons"],
                "recipients": preview["recipients"],
                "excluded": preview["excluded"],
                "recipient_count": preview["recipient_count"],
                "excluded_count": preview["excluded_count"],
                "invalid_contact_count": preview["invalid_contact_count"],
                "totals_by_currency": preview["totals_by_currency"],
                "warnings": preview["warnings"],
                "can_submit": bool(
                    campaign.status == "draft"
                    and not preview["blocking_reasons"]
                    and preview["recipient_count"] > 0
                    and user_has_permission(user, "campaigns.submit")
                ),
                "can_approve": bool(
                    campaign.status == "awaiting_approval"
                    and not preview["blocking_reasons"]
                    and user_has_permission(user, "campaigns.approve")
                ),
                "can_cancel": _can_cancel(campaign, user),
                "message_count": 0,
                "pending_job_count": 0,
            }
        )
    else:
        if campaign.status == "approved":
            recipients = _stored_recipients(db, campaign)
            blocked = []
        elif _has_snapshots(db, campaign):
            recipients = _stored_recipients(db, campaign)
            blocked = list(stored.get("blocking_reasons") or [])
        else:
            recipients = list(stored.get("recipients") or [])
            blocked = list(stored.get("blocking_reasons") or [])
        message_count, pending_job_count = _delivery_counts(db, campaign)
        payload.update(
            {
                "template_body": stored.get("template_body"),
                "previewed_at": campaign.previewed_at,
                "blocking_reasons": blocked,
                "recipients": recipients,
                "excluded": list(
                    campaign.excluded_snapshot or stored.get("excluded") or []
                ),
                "can_submit": False,
                "can_approve": False,
                "can_cancel": _can_cancel(campaign, user),
                "message_count": message_count,
                "pending_job_count": pending_job_count,
            }
        )
    return _campaign_detail_payload(payload, reveal=reveal)


def get_campaign(db: Session, campaign_id: str, *, lock: bool = False) -> Campaign:
    statement = select(Campaign).where(Campaign.id == campaign_id)
    if lock:
        statement = statement.with_for_update()
    campaign = db.scalar(statement)
    if campaign is None:
        raise ApiError(
            404,
            "CAMPAIGN_NOT_FOUND",
            MESSAGES_AR["CAMPAIGN_NOT_FOUND"],
            "Campaign not found.",
        )
    return campaign


def _resolve_template(
    db: Session, template_id: str | None
) -> MessageTemplate:
    if template_id:
        template = db.get(MessageTemplate, template_id)
        if template is None:
            raise ApiError(
                404,
                "TEMPLATE_NOT_FOUND",
                MESSAGES_AR["TEMPLATE_NOT_FOUND_404"],
                "Template not found.",
            )
        return template
    template = db.scalar(
        select(MessageTemplate)
        .where(
            MessageTemplate.channel == "sms",
            MessageTemplate.language == "ar",
            MessageTemplate.is_active.is_(True),
        )
        .order_by(MessageTemplate.version.desc(), MessageTemplate.created_at.desc())
        .limit(1)
    )
    if template is None:
        raise ApiError(
            422,
            "NO_ACTIVE_TEMPLATE",
            MESSAGES_AR["NO_ACTIVE_TEMPLATE"],
            "No active Arabic SMS template exists.",
        )
    return template


def create_campaign(
    db: Session,
    *,
    request: Request,
    user: User,
    name: str,
    source_import_id: str,
    template_id: str | None,
) -> Campaign:
    batch = db.get(ImportBatch, source_import_id)
    if batch is None or batch.status != "confirmed":
        raise ApiError(
            422,
            "IMPORT_NOT_CONFIRMED",
            MESSAGES_AR["IMPORT_NOT_CONFIRMED"],
            "The source import must exist and be confirmed.",
        )
    template = _resolve_template(db, template_id)
    now = _now()
    campaign = Campaign(
        id=str(uuid4()),
        name=name.strip(),
        source_import_id=batch.id,
        status="draft",
        channel=template.channel or "sms",
        template_id=template.id,
        template_version=template.version,
        created_by=user.id,
        revision=0,
    )
    db.add(campaign)
    db.flush()
    preview = _preview_for(db, campaign)
    _apply_preview(campaign, preview)
    campaign.updated_at = now
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="campaign.create",
        entity_type="campaign",
        entity_id=campaign.id,
        after={
            "name": campaign.name,
            "status": campaign.status,
            "source_import_id": campaign.source_import_id,
            "template_id": campaign.template_id,
            "template_version": campaign.template_version,
            "recipient_count": campaign.recipient_count,
            "excluded_count": campaign.excluded_count,
            "totals_by_currency": dict(campaign.totals_by_currency or {}),
        },
    )
    db.commit()
    db.refresh(campaign)
    return campaign


def update_campaign(
    db: Session,
    campaign: Campaign,
    *,
    request: Request,
    user: User,
    name: str | None,
    template_id: str | None,
) -> Campaign:
    campaign = get_campaign(db, campaign.id, lock=True)
    if campaign.status != "draft":
        raise ApiError(
            409,
            "CAMPAIGN_STATE_INVALID",
            MESSAGES_AR["CAMPAIGN_STATE_INVALID"],
            "Only draft campaigns can be edited.",
            {"status": campaign.status},
        )
    before = {
        "name": campaign.name,
        "template_id": campaign.template_id,
        "template_version": campaign.template_version,
        "revision": campaign.revision,
    }
    if name is not None:
        campaign.name = name.strip()
    if template_id is not None:
        template = _resolve_template(db, template_id)
        campaign.template_id = template.id
        campaign.template_version = template.version
        campaign.channel = template.channel or campaign.channel
    db.flush()
    preview = _preview_for(db, campaign)
    _apply_preview(campaign, preview)
    campaign.revision += 1
    campaign.updated_at = _now()
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="campaign.update",
        entity_type="campaign",
        entity_id=campaign.id,
        before=before,
        after={
            "name": campaign.name,
            "template_id": campaign.template_id,
            "template_version": campaign.template_version,
            "revision": campaign.revision,
            "recipient_count": campaign.recipient_count,
            "excluded_count": campaign.excluded_count,
            "totals_by_currency": dict(campaign.totals_by_currency or {}),
        },
    )
    db.commit()
    db.refresh(campaign)
    return campaign


def _revision_guard(campaign: Campaign, expected_revision: int | None) -> None:
    if expected_revision is not None and expected_revision != campaign.revision:
        raise ApiError(
            409,
            "CAMPAIGN_CHANGED",
            MESSAGES_AR["CAMPAIGN_CHANGED"],
            "The campaign revision does not match.",
            {
                "expected_revision": expected_revision,
                "current_revision": campaign.revision,
            },
        )


def _blocked(db: Session, campaign: Campaign) -> dict[str, Any]:
    preview = _preview_for(db, campaign)
    reasons = list(preview["blocking_reasons"])
    if preview["recipient_count"] == 0 and not any(
        reason["code"] == "NO_ELIGIBLE_RECIPIENTS" for reason in reasons
    ):
        reasons.append(
            {
                "code": "NO_ELIGIBLE_RECIPIENTS",
                "message_ar": MESSAGES_AR["NO_ELIGIBLE_RECIPIENTS"],
            }
        )
    return {"preview": preview, "reasons": reasons}


def submit_campaign(
    db: Session,
    campaign_id: str,
    *,
    request: Request,
    user: User,
    expected_revision: int,
) -> Campaign:
    campaign = get_campaign(db, campaign_id, lock=True)
    if campaign.status != "draft":
        raise ApiError(
            409,
            "CAMPAIGN_STATE_INVALID",
            MESSAGES_AR["CAMPAIGN_STATE_INVALID"],
            "Only draft campaigns can be submitted.",
            {"status": campaign.status},
        )
    _revision_guard(campaign, expected_revision)
    checked = _blocked(db, campaign)
    if checked["reasons"]:
        raise ApiError(
            422,
            "CAMPAIGN_BLOCKED",
            MESSAGES_AR["CAMPAIGN_BLOCKED"],
            "The campaign has blocking reasons and cannot be submitted.",
            {"reasons": checked["reasons"]},
        )
    _apply_preview(campaign, checked["preview"])
    campaign.status = "awaiting_approval"
    campaign.submitted_at = _now()
    campaign.revision += 1
    campaign.updated_at = campaign.submitted_at
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="campaign.submit",
        entity_type="campaign",
        entity_id=campaign.id,
        before={"status": "draft", "revision": campaign.revision - 1},
        after={
            "status": campaign.status,
            "revision": campaign.revision,
            "recipient_count": campaign.recipient_count,
            "totals_by_currency": dict(campaign.totals_by_currency or {}),
        },
    )
    db.commit()
    db.refresh(campaign)
    return campaign


def _snapshot_payload(
    *,
    campaign: Campaign,
    template: MessageTemplate,
    approver: User,
    approved_at: datetime,
    recipients: list[dict[str, Any]],
) -> dict[str, Any]:
    canonical_recipients = sorted(
        (
            {
                "guardian_id": recipient["guardian_id"],
                "guardian_name": recipient["guardian_name"],
                "phone": recipient["phone"],
                "amount": recipient["amount"],
                "currency": recipient["currency"],
                "message": recipient["message"],
                "fee_balance_ids": sorted(recipient["fee_balance_ids"]),
                "student_names": sorted(recipient.get("student_names") or []),
                "fee_periods": sorted(recipient.get("fee_periods") or []),
            }
            for recipient in recipients
        ),
        key=lambda item: (item["guardian_id"], item["currency"]),
    )
    return {
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "channel": campaign.channel,
        "source_import_id": campaign.source_import_id,
        "template": {
            "id": template.id,
            "version": template.version,
            "body": template.template_body,
        },
        "approved_by": approver.id,
        "approved_at": approved_at.astimezone(timezone.utc).isoformat(),
        "recipients": canonical_recipients,
    }


def _snapshot_hash(
    *,
    campaign: Campaign,
    template: MessageTemplate,
    approver: User,
    approved_at: datetime,
    recipients: list[dict[str, Any]],
) -> str:
    payload = _snapshot_payload(
        campaign=campaign,
        template=template,
        approver=approver,
        approved_at=approved_at,
        recipients=recipients,
    )
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _idempotency_key(campaign_id: str, recipient_id: str) -> str:
    # Two UUIDs plus a separator: 73 characters, within the String(80) column.
    # Stable for a given frozen recipient and unique per campaign recipient.
    return f"{campaign_id}:{recipient_id}"


def approve_campaign(
    db: Session,
    campaign_id: str,
    *,
    request: Request,
    user: User,
    expected_revision: int,
    acknowledge_warnings: bool,
) -> Campaign:
    campaign = get_campaign(db, campaign_id, lock=True)
    if campaign.status == "approved":
        return campaign
    if campaign.status != "awaiting_approval":
        raise ApiError(
            409,
            "CAMPAIGN_STATE_INVALID",
            MESSAGES_AR["CAMPAIGN_STATE_INVALID"],
            "Only campaigns awaiting approval can be approved.",
            {"status": campaign.status},
        )
    _revision_guard(campaign, expected_revision)

    try:
        checked = _blocked(db, campaign)
        if checked["reasons"]:
            raise ApiError(
                422,
                "CAMPAIGN_BLOCKED",
                MESSAGES_AR["CAMPAIGN_BLOCKED"],
                "The campaign has blocking reasons and cannot be approved.",
                {"reasons": checked["reasons"]},
            )
        preview = checked["preview"]
        template = _campaign_template(db, campaign)
        if template is None or not template.is_active:
            raise ApiError(
                422,
                "CAMPAIGN_BLOCKED",
                MESSAGES_AR["CAMPAIGN_BLOCKED"],
                "The campaign template is missing or inactive.",
                {"reasons": checked["reasons"]},
            )
        if preview["warnings"] and not acknowledge_warnings:
            raise ApiError(
                422,
                "WARNINGS_UNACKNOWLEDGED",
                MESSAGES_AR["WARNINGS_UNACKNOWLEDGED"],
                "Warnings must be acknowledged before approval.",
                {"warning_count": len(preview["warnings"])},
            )

        _apply_preview(campaign, preview)
        approved_at = _now()
        recipients = preview["recipients"]
        db.execute(
            delete(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id)
        )
        db.flush()
        for recipient in recipients:
            recipient_id = str(uuid4())
            warnings = list(recipient.get("warnings") or [])
            details = {
                "key": recipient["key"],
                "student_names": list(recipient.get("student_names") or []),
                "fee_periods": list(recipient.get("fee_periods") or []),
                "fee_balance_ids": list(recipient.get("fee_balance_ids") or []),
                "warnings": warnings,
            }
            db.add(
                CampaignRecipient(
                    id=recipient_id,
                    campaign_id=campaign.id,
                    guardian_id=recipient["guardian_id"],
                    destination_phone_snapshot=recipient["phone"],
                    guardian_name_snapshot=recipient["guardian_name"],
                    amount_snapshot=Decimal(recipient["amount"]),
                    currency_snapshot=recipient["currency"],
                    fee_details_snapshot=details,
                    message_body_snapshot=recipient["message"],
                    eligibility_status="warning" if warnings else "eligible",
                )
            )
            message = Message(
                id=str(uuid4()),
                campaign_id=campaign.id,
                campaign_recipient_id=recipient_id,
                provider="rasel",
                channel="sms",
                internal_status="pending",
                idempotency_key=_idempotency_key(campaign.id, recipient_id),
            )
            db.add(message)
            db.flush()
            db.add(
                SendJob(
                    id=str(uuid4()),
                    message_id=message.id,
                    status="pending",
                    attempt_count=0,
                    next_attempt_at=None,
                )
            )

        hash_value = _snapshot_hash(
            campaign=campaign,
            template=template,
            approver=user,
            approved_at=approved_at,
            recipients=recipients,
        )
        campaign.status = "approved"
        campaign.approved_by = user.id
        campaign.approved_at = approved_at
        campaign.snapshot_hash = hash_value
        campaign.template_version = template.version
        campaign.revision += 1
        campaign.updated_at = approved_at
        record_audit(
            db,
            request=request,
            actor_user_id=user.id,
            action="campaign.approve",
            entity_type="campaign",
            entity_id=campaign.id,
            before={"status": "awaiting_approval", "revision": campaign.revision - 1},
            after={
                "status": "approved",
                "revision": campaign.revision,
                "approved_by": user.id,
                "approved_at": approved_at.isoformat(),
                "snapshot_hash": hash_value,
                "recipient_count": campaign.recipient_count,
                "excluded_count": campaign.excluded_count,
                "totals_by_currency": dict(campaign.totals_by_currency or {}),
                "template_id": template.id,
                "template_version": template.version,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(campaign)
    return campaign


def _require_cancel_permission(campaign: Campaign, user: User) -> None:
    permission = "campaigns.approve" if campaign.status == "approved" else "campaigns.edit"
    if not user_has_permission(user, permission):
        raise ApiError(
            403,
            "FORBIDDEN",
            "ليس لديك صلاحية لهذا الإجراء.",
            "Permission denied.",
        )


def cancel_campaign(
    db: Session,
    campaign_id: str,
    *,
    request: Request,
    user: User,
    reason: str | None,
    expected_revision: int | None,
) -> Campaign:
    campaign = get_campaign(db, campaign_id, lock=True)
    if campaign.status == "cancelled":
        return campaign
    if campaign.status not in _CANCELLABLE_STATUSES:
        raise ApiError(
            409,
            "CAMPAIGN_STATE_INVALID",
            MESSAGES_AR["CAMPAIGN_STATE_INVALID"],
            "The campaign cannot be cancelled in its current state.",
            {"status": campaign.status},
        )
    _require_cancel_permission(campaign, user)
    _revision_guard(campaign, expected_revision)
    previous_status = campaign.status
    now = _now()
    cancelled_message_count = 0
    retained_message_count = 0
    if previous_status == "approved":
        # Preserve terminal provider outcomes. Cancelling must not rewrite
        # delivered/failed/unknown/accepted messages or their jobs.
        cancellable_message_ids = list(
            db.scalars(
                select(Message.id).where(
                    Message.campaign_id == campaign.id,
                    Message.internal_status.in_(("pending", "submitting")),
                )
            ).all()
        )
        total_messages = db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.campaign_id == campaign.id)
        ) or 0
        cancelled_message_count = len(cancellable_message_ids)
        retained_message_count = int(total_messages) - cancelled_message_count
        if cancellable_message_ids:
            db.execute(
                update(Message)
                .where(Message.id.in_(cancellable_message_ids))
                .values(internal_status="cancelled", updated_at=now)
            )
            db.execute(
                update(SendJob)
                .where(
                    SendJob.message_id.in_(cancellable_message_ids),
                    SendJob.status.in_(("pending", "retry", "claimed")),
                )
                .values(status="cancelled", updated_at=now)
            )
    campaign.status = "cancelled"
    campaign.cancelled_at = now
    campaign.cancelled_by = user.id
    campaign.cancel_reason = (reason or "").strip() or None
    campaign.revision += 1
    campaign.updated_at = now
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="campaign.cancel",
        entity_type="campaign",
        entity_id=campaign.id,
        before={"status": previous_status, "revision": campaign.revision - 1},
        after={
            "status": "cancelled",
            "revision": campaign.revision,
            "reason": campaign.cancel_reason,
            "snapshots_retained": previous_status == "approved",
            "messages_cancelled": cancelled_message_count,
            "messages_retained": retained_message_count,
        },
    )
    db.commit()
    db.refresh(campaign)
    return campaign
