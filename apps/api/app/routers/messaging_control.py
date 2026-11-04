from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import phonenumbers
from fastapi import APIRouter, Depends, Request
from phonenumbers import PhoneNumberFormat
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import settings
from ..db import get_db
from ..deps import require_csrf, require_permission
from ..errors import ApiError
from ..messaging.credentials import (
    CredentialError,
    credential_status,
    revoke_credential,
    upsert_credential,
)
from ..messaging.factory import provider_configuration_error, provider_name
from ..messaging.fake import FakeProvider
from ..models import AuditEvent, ProviderCredential, User
from ..privacy import mask_phone
from ..schemas import (
    MessagingBalanceOut,
    ProviderCredentialUpdate,
    ProviderStatusOut,
    TestSendOut,
    TestSendRequest,
)

router = APIRouter(prefix="/messaging", tags=["messaging-control"])

_ALLOWLIST_REGION = "SY"


def _snapshot(row: ProviderCredential | None) -> dict | None:
    if row is None:
        return None
    return {
        "provider": row.provider,
        "sender_id": row.sender_id,
        "channel": row.channel,
        "key_version": row.key_version,
        "active": bool(row.is_active),
    }


def _existing(db: Session) -> ProviderCredential | None:
    return db.scalar(
        select(ProviderCredential).where(
            ProviderCredential.provider == "rasel"
        )
    )


def _provider_status(db: Session) -> ProviderStatusOut:
    provider = provider_name()
    credential = credential_status(db)
    # ``configured`` always reflects the stored/environment credential, never
    # whether the fake provider is usable for dry-run test sends.
    configured = bool(credential["configured"])
    if provider == "fake":
        # A fake-only deployment needs no provider credential; do not surface
        # an "incomplete credential" error on the credential card.
        error = None
    else:
        error = credential["credential_error"]
        if not configured and not error:
            error = (
                provider_configuration_error(settings)
                or "Provider credentials are not configured."
            )
    return ProviderStatusOut(
        provider=provider,
        configured=configured,
        credential_source=credential["credential_source"],
        credential_error=error,
        sender_id=credential["sender_id"],
        channel=credential["channel"],
        key_version=credential["key_version"],
        rotated_at=credential["rotated_at"],
        rotated_by_name=credential["rotated_by_name"],
        test_send_mode="fake" if provider == "fake" else "disabled",
        live_send_available=False,
    )


def _normalize_recipient(raw: str) -> str:
    try:
        number = phonenumbers.parse((raw or "").strip(), _ALLOWLIST_REGION)
    except phonenumbers.NumberParseException:
        number = None
    if number is None or not phonenumbers.is_valid_number(number):
        raise ApiError(
            422,
            "INVALID_PHONE",
            "رقم الهاتف غير صالح.",
            "Recipient phone number is invalid.",
        )
    return phonenumbers.format_number(number, PhoneNumberFormat.E164)


def _check_test_send_throttle(db: Session, user: User) -> None:
    """Reject test sends over the per-actor audit-backed window.

    Counting append-only audit rows makes the limit survive process restarts
    and is scoped to the acting admin, so one operator cannot exhaust another's
    allowance.
    """
    limit = int(settings.messaging_test_send_limit)
    window = int(settings.messaging_test_send_window_seconds)
    if limit <= 0:
        attempts = limit
    else:
        since = datetime.now(timezone.utc) - timedelta(seconds=max(1, window))
        attempts = db.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(
                AuditEvent.action == "messaging.test_send",
                AuditEvent.actor_user_id == user.id,
                AuditEvent.created_at >= since,
            )
        ) or 0
    if attempts >= limit:
        raise ApiError(
            429,
            "RATE_LIMITED",
            "تم تجاوز حد الإرسال التجريبي. حاول لاحقًا.",
            "Test-send rate limit exceeded. Try again shortly.",
        )


def _normalized_allowlist() -> set[str]:
    allowed: set[str] = set()
    for part in (settings.messaging_allowlist or "").split(","):
        token = part.strip()
        if not token:
            continue
        try:
            number = phonenumbers.parse(token, _ALLOWLIST_REGION)
        except phonenumbers.NumberParseException:
            continue
        if phonenumbers.is_valid_number(number):
            allowed.add(phonenumbers.format_number(number, PhoneNumberFormat.E164))
    return allowed


@router.get("/provider", response_model=ProviderStatusOut)
def read_provider_status(
    _: User = Depends(require_permission("settings.manage")),
    db: Session = Depends(get_db),
) -> ProviderStatusOut:
    return _provider_status(db)


@router.put("/provider/credential", response_model=ProviderStatusOut)
def rotate_provider_credential(
    payload: ProviderCredentialUpdate,
    request: Request,
    current: User = Depends(require_permission("settings.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> ProviderStatusOut:
    before = _snapshot(_existing(db))
    try:
        row = upsert_credential(
            db,
            provider="rasel",
            api_key=payload.api_key,
            sender_id=payload.sender_id,
            channel=payload.channel,
            user=current,
        )
    except CredentialError:
        db.rollback()
        raise ApiError(
            503,
            "CREDENTIAL_KEY_UNAVAILABLE",
            "تشفير بيانات المزوّد غير متاح.",
            "Provider credential encryption is unavailable.",
        ) from None
    except ValueError:
        db.rollback()
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "بيانات المزوّد غير صالحة.",
            "Provider credential is invalid.",
        ) from None
    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="messaging.credential.rotate",
        entity_type="provider_credential",
        entity_id=row.id,
        before=before,
        after=_snapshot(row),
    )
    db.commit()
    db.refresh(row)
    return _provider_status(db)


@router.post("/provider/revoke", response_model=ProviderStatusOut)
def revoke_provider_credential(
    request: Request,
    current: User = Depends(require_permission("settings.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> ProviderStatusOut:
    before = _snapshot(_existing(db))
    row = revoke_credential(db, provider="rasel", user=current)
    after = _snapshot(row) or {
        "provider": "rasel",
        "sender_id": None,
        "channel": None,
        "key_version": None,
        "active": False,
    }
    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="messaging.credential.revoke",
        entity_type="provider_credential",
        entity_id=row.id if row is not None else "rasel",
        before=before,
        after=after,
    )
    db.commit()
    return _provider_status(db)


@router.post("/test-send", response_model=TestSendOut)
def test_send(
    payload: TestSendRequest,
    request: Request,
    current: User = Depends(require_permission("settings.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    recipient = _normalize_recipient(payload.recipient)
    allowlist = _normalized_allowlist()
    if not allowlist:
        raise ApiError(
            422,
            "ALLOWLIST_REQUIRED",
            "قائمة الأرقام المسموح بها للاختبار غير مهيأة.",
            "A test-send allowlist is required.",
        )
    if recipient not in allowlist:
        raise ApiError(
            422,
            "RECIPIENT_NOT_ALLOWLISTED",
            "رقم المستلم غير موجود في قائمة الاختبار.",
            "Recipient is not on the test-send allowlist.",
        )

    provider = provider_name()
    if provider != "fake":
        raise ApiError(
            409,
            "LIVE_TEST_SEND_BLOCKED",
            "الإرسال التجريبي الحقيقي محجوب قبل G0.",
            "Live test-send is blocked; only the fake provider is allowed.",
        )

    _check_test_send_throttle(db, current)

    fake = FakeProvider(scenario=settings.fake_provider_scenario)
    result = fake.send(
        to=recipient,
        text=payload.message,
        idempotency_key=f"test-send:{uuid4()}",
        channel="local_sms",
    )
    sent_at = datetime.now(timezone.utc)
    recipient_masked = mask_phone(recipient) or ""
    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="messaging.test_send",
        entity_type="messaging_provider",
        entity_id=provider,
        after={
            "provider": provider,
            "recipient_masked": recipient_masked,
            "outcome": result.outcome,
            "dry_run": True,
            "error_code": result.error_code,
        },
    )
    db.commit()
    return {
        "provider": provider,
        "dry_run": True,
        "outcome": result.outcome,
        "provider_status": result.provider_status,
        "error_code": result.error_code,
        "error_summary": result.error_summary,
        "provider_message_id": result.provider_message_id,
        "recipient_masked": recipient_masked,
        "sent_at": sent_at,
    }


@router.get("/balance", response_model=MessagingBalanceOut)
def read_balance(
    _: User = Depends(require_permission("settings.manage")),
) -> dict:
    provider = provider_name()
    if provider == "fake":
        return {
            "provider": provider,
            "available": True,
            "balance": "unlimited",
            "currency": "SMS",
            "preflight": True,
            "reason": None,
        }
    return {
        "provider": provider,
        "available": False,
        "balance": None,
        "currency": None,
        "preflight": True,
        "reason": "live_provider_blocked",
    }
