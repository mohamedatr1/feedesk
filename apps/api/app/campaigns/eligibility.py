from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..imports.normalization import normalize_phone
from ..models import (
    FeeBalance,
    Guardian,
    GuardianContact,
    MessageTemplate,
    SchoolSettings,
    Student,
)
from .constants import MESSAGES_AR
from .rendering import find_unknown_variables, render_template

_REASON_ORDER = (
    "MISSING_CURRENCY",
    "ZERO_BALANCE",
    "NEGATIVE_BALANCE",
    "GUARDIAN_INACTIVE",
    "MISSING_PHONE",
    "INVALID_PHONE",
)
_PHONE_REASONS = {"MISSING_PHONE", "INVALID_PHONE"}


def _amount_plain(value: Decimal | str | None) -> str:
    if value is None:
        return "0.00"
    return f"{Decimal(str(value)).quantize(Decimal('0.01')):f}"


def _notice(code: str, *, count: int | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message_ar": MESSAGES_AR[code]}
    if count is not None:
        payload["count"] = count
    return payload


def _destination_phone(
    contacts: list[GuardianContact],
) -> tuple[str | None, str | None]:
    if not contacts:
        return None, "MISSING_PHONE"
    if not any((contact.original_phone or "").strip() for contact in contacts):
        return None, "MISSING_PHONE"
    for contact in contacts:
        for candidate in (contact.normalized_phone, contact.original_phone):
            result = normalize_phone(candidate)
            if result.status == "ok" and result.normalized:
                return result.normalized, None
    return None, "INVALID_PHONE"


def _ordered_contacts(
    contacts: list[GuardianContact],
) -> list[GuardianContact]:
    return sorted(
        contacts,
        key=lambda contact: (
            0 if contact.is_primary else 1,
            contact.created_at or datetime.min.replace(tzinfo=timezone.utc),
            contact.id,
        ),
    )


def _group_reasons(
    *,
    total: Decimal,
    currency: str,
    guardian_active: bool,
    phone_reason: str | None,
) -> list[str]:
    reasons: list[str] = []
    if len(currency) != 3 or not currency.isalpha():
        reasons.append("MISSING_CURRENCY")
    if total == 0:
        reasons.append("ZERO_BALANCE")
    elif total < 0:
        reasons.append("NEGATIVE_BALANCE")
    if not guardian_active:
        reasons.append("GUARDIAN_INACTIVE")
    if phone_reason:
        reasons.append(phone_reason)
    return sorted(set(reasons), key=_REASON_ORDER.index)


def _school_contact(settings_row: SchoolSettings | None) -> str | None:
    if settings_row is None:
        return None
    return (settings_row.contact_phone or "").strip() or (
        settings_row.contact_email or ""
    ).strip() or None


def build_preview(
    db: Session,
    *,
    source_import_id: str | None,
    template: MessageTemplate | None,
    school_settings: SchoolSettings | None,
) -> dict[str, Any]:
    """Compute the deterministic recipient preview for a confirmed import."""
    previewed_at = datetime.now(timezone.utc)
    template_body = template.template_body if template is not None else ""
    unknown_template_variables = set(find_unknown_variables(template_body))

    if not source_import_id:
        rows: list[tuple[FeeBalance, Guardian, Student | None]] = []
    else:
        rows = list(
            db.execute(
                select(FeeBalance, Guardian, Student)
                .join(Guardian, FeeBalance.guardian_id == Guardian.id)
                .outerjoin(Student, FeeBalance.student_id == Student.id)
                .where(
                    FeeBalance.import_batch_id == source_import_id,
                    FeeBalance.record_status == "confirmed",
                )
                .order_by(FeeBalance.created_at.asc(), FeeBalance.id.asc())
            ).all()
        )

    guardian_ids = {guardian.id for _, guardian, _ in rows}
    contacts_by_guardian: dict[str, list[GuardianContact]] = {}
    if guardian_ids:
        contacts = list(
            db.scalars(
                select(GuardianContact).where(
                    GuardianContact.guardian_id.in_(guardian_ids)
                )
            ).all()
        )
        for contact in _ordered_contacts(contacts):
            contacts_by_guardian.setdefault(contact.guardian_id, []).append(contact)

    groups: dict[tuple[str, str], dict[str, Any]] = {}
    for balance, guardian, student in rows:
        currency = (balance.currency or "").strip().upper()
        key = (guardian.id, currency)
        group = groups.get(key)
        if group is None:
            group = {
                "guardian": guardian,
                "currency": currency,
                "total": Decimal("0.00"),
                "fee_balance_ids": [],
                "student_names": set(),
                "fee_periods": set(),
            }
            groups[key] = group
        group["total"] += Decimal(balance.remaining_balance_source or 0)
        group["fee_balance_ids"].append(balance.id)
        if student is not None and (student.full_name or "").strip():
            group["student_names"].add(student.full_name.strip())
        if (balance.fee_period or "").strip():
            group["fee_periods"].add(balance.fee_period.strip())

    recipients: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    unresolved: set[str] = set()
    invalid_contact_count = 0

    for (guardian_id, currency), group in groups.items():
        guardian: Guardian = group["guardian"]
        total: Decimal = group["total"]
        contacts = contacts_by_guardian.get(guardian_id, [])
        phone, phone_reason = _destination_phone(contacts)
        reasons = _group_reasons(
            total=total,
            currency=currency,
            guardian_active=guardian.status == "active",
            phone_reason=phone_reason,
        )
        fee_balance_ids = sorted(group["fee_balance_ids"])
        student_names = sorted(group["student_names"])
        fee_periods = sorted(group["fee_periods"])
        if reasons:
            if any(code in _PHONE_REASONS for code in reasons):
                invalid_contact_count += 1
            excluded.append(
                {
                    "key": f"{guardian_id}:{currency or 'MISSING'}",
                    "guardian_id": guardian_id,
                    "guardian_name": guardian.full_name,
                    "phone": phone,
                    "amount": _amount_plain(total),
                    "currency": currency or None,
                    "reasons": [_notice(code) for code in reasons],
                    "fee_balance_ids": fee_balance_ids,
                }
            )
            continue

        rendered = render_template(
            template_body,
            guardian_name=guardian.full_name,
            student_names=student_names,
            amount=total,
            currency=currency,
            fee_periods=fee_periods,
            school_name=school_settings.school_name if school_settings else None,
            school_contact=_school_contact(school_settings),
        )
        unresolved.update(rendered.unresolved_variables)
        recipients.append(
            {
                "id": None,
                "key": f"{guardian_id}:{currency}",
                "guardian_id": guardian_id,
                "guardian_name": guardian.full_name,
                "phone": phone,
                "student_names": student_names,
                "fee_periods": fee_periods,
                "amount": _amount_plain(total),
                "currency": currency,
                "message": rendered.body,
                "validation_status": "valid",
                "warnings": [],
                "fee_balance_ids": fee_balance_ids,
            }
        )

    recipients.sort(key=lambda item: (item["guardian_name"], item["guardian_id"], item["currency"]))
    excluded.sort(key=lambda item: (item["guardian_name"], item["guardian_id"], item["currency"] or ""))

    guardians_by_phone: dict[str, set[str]] = {}
    for recipient in recipients:
        guardians_by_phone.setdefault(recipient["phone"], set()).add(
            recipient["guardian_id"]
        )
    shared_phones = {
        phone: guardians
        for phone, guardians in guardians_by_phone.items()
        if len(guardians) > 1
    }
    warnings: list[dict[str, Any]] = []
    if shared_phones:
        warning = _notice(
            "SHARED_PHONE",
            count=sum(len(guardians) for guardians in shared_phones.values()),
        )
        warnings.append(warning)
        for recipient in recipients:
            if recipient["phone"] in shared_phones:
                recipient["warnings"] = [
                    {"code": "SHARED_PHONE", "message_ar": MESSAGES_AR["SHARED_PHONE"]}
                ]
                recipient["validation_status"] = "warning"

    totals: dict[str, Decimal] = {}
    for recipient in recipients:
        totals[recipient["currency"]] = totals.get(
            recipient["currency"], Decimal("0.00")
        ) + Decimal(recipient["amount"].replace(",", ""))
    totals_by_currency = {
        currency: _amount_plain(value) for currency, value in sorted(totals.items())
    }

    blocking: list[dict[str, Any]] = []
    if template is None:
        blocking.append(_notice("TEMPLATE_NOT_FOUND"))
    elif not template.is_active:
        blocking.append(_notice("TEMPLATE_INACTIVE"))

    unresolved.update(unknown_template_variables)
    if unresolved:
        blocking.append(
            _notice("UNRESOLVED_VARIABLES", count=len(unresolved))
        )
    if not recipients:
        blocking.append(_notice("NO_ELIGIBLE_RECIPIENTS"))

    return {
        "template_body": template_body,
        "previewed_at": previewed_at,
        "recipients": recipients,
        "excluded": excluded,
        "warnings": warnings,
        "blocking_reasons": blocking,
        "totals_by_currency": totals_by_currency,
        "recipient_count": len(recipients),
        "excluded_count": len(excluded),
        "invalid_contact_count": invalid_contact_count,
    }
