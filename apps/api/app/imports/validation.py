from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ImportBatch, StagedRow
from .constants import CANONICAL_FIELDS, EDITABLE_NORMALIZED_FIELDS
from .errors import ImportIssue
from .normalization import (
    clean_text,
    issue,
    money_to_string,
    normalize_name_key,
    normalize_phone,
    parse_currency,
    parse_money,
)


@dataclass
class NormalizedRow:
    data: dict[str, Any]
    issues: list[ImportIssue]


def inputs_from_raw(raw_data: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
    inputs: dict[str, Any] = {}
    for canonical, header in mapping.items():
        if canonical in CANONICAL_FIELDS:
            inputs[canonical] = raw_data.get(header)
    return inputs


def inputs_from_normalized(normalized: dict[str, Any]) -> dict[str, Any]:
    return {
        "guardian_name": normalized.get("guardian_name"),
        "guardian_phone": normalized.get("guardian_phone_original"),
        "student_name": normalized.get("student_name"),
        "total_fee": normalized.get("total_fee"),
        "amount_paid": normalized.get("amount_paid"),
        "remaining_balance": normalized.get("remaining_balance"),
        "currency": normalized.get("currency"),
        "fee_period": normalized.get("fee_period"),
    }


def normalize_row(inputs: dict[str, Any]) -> NormalizedRow:
    issues: list[ImportIssue] = []

    guardian_name = clean_text(inputs.get("guardian_name"))
    if not guardian_name:
        issues.append(issue("MISSING_GUARDIAN"))

    phone = normalize_phone(inputs.get("guardian_phone"))
    if phone.status == "missing":
        issues.append(issue("MISSING_PHONE"))
    elif phone.status == "invalid":
        issues.append(issue("INVALID_PHONE"))

    student_name = clean_text(inputs.get("student_name")) or None

    remaining = parse_money(inputs.get("remaining_balance"))
    if remaining.status == "empty":
        issues.append(issue("MISSING_BALANCE"))
    elif remaining.status == "ambiguous":
        issues.append(issue("AMBIGUOUS_MONEY"))
    elif remaining.value is not None and remaining.value < 0:
        issues.append(issue("NEGATIVE_BALANCE"))
    elif remaining.value == 0:
        issues.append(issue("ZERO_BALANCE"))

    total = parse_money(inputs.get("total_fee"))
    if total.status == "ambiguous":
        issues.append(issue("AMBIGUOUS_MONEY"))
    paid = parse_money(inputs.get("amount_paid"))
    if paid.status == "ambiguous":
        issues.append(issue("AMBIGUOUS_MONEY"))

    calculated: Decimal | None = None
    if total.value is not None and paid.value is not None:
        calculated = total.value - paid.value
        if remaining.value is not None and calculated != remaining.value:
            issues.append(issue("TOTAL_DISCREPANCY"))

    currency = parse_currency(inputs.get("currency"))
    if currency is None:
        issues.append(issue("MISSING_CURRENCY"))

    fee_period = clean_text(inputs.get("fee_period")) or None

    has_error = any(item.severity == "error" for item in issues)
    is_eligible = (
        not has_error
        and phone.status == "ok"
        and remaining.value is not None
        and remaining.value > 0
    )

    data = {
        "guardian_name": guardian_name or None,
        "guardian_phone_original": phone.original or None,
        "guardian_phone_normalized": phone.normalized,
        "student_name": student_name,
        "total_fee": money_to_string(total.value),
        "amount_paid": money_to_string(paid.value),
        "remaining_balance": money_to_string(remaining.value),
        "remaining_balance_calculated": money_to_string(calculated),
        "currency": currency,
        "fee_period": fee_period,
        "is_eligible": is_eligible,
    }
    return NormalizedRow(data=data, issues=issues)


def _phone_key(normalized: dict[str, Any]) -> str:
    phone = normalized.get("guardian_phone_normalized")
    if phone:
        return str(phone)
    original = normalized.get("guardian_phone_original") or ""
    return re.sub(r"\D", "", str(original))


def row_fingerprint(normalized: dict[str, Any]) -> str:
    parts = [
        normalize_name_key(normalized.get("guardian_name")),
        _phone_key(normalized),
        normalize_name_key(normalized.get("student_name")),
        normalize_name_key(normalized.get("fee_period")),
        normalized.get("remaining_balance") or "",
        normalized.get("currency") or "",
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _row_order(row: StagedRow) -> tuple[int, str]:
    return (row.position, row.id)


def revalidate_batch(db: Session, batch: ImportBatch) -> list[StagedRow]:
    rows = list(
        db.scalars(
            select(StagedRow).where(StagedRow.import_batch_id == batch.id)
        ).all()
    )
    rows.sort(key=_row_order)

    normalized_by_row: dict[str, dict[str, Any]] = {}
    issues_by_row: dict[str, list[ImportIssue]] = {}
    for row in rows:
        existing = row.normalized_data or {}
        if existing:
            inputs = inputs_from_normalized(existing)
        else:
            inputs = inputs_from_raw(row.raw_data or {}, batch.column_mapping or {})
        result = normalize_row(inputs)
        extra = [
            ImportIssue(
                code=item.get("code", "ROW_WARNING"),
                field=item.get("field", "source"),
                message_ar=item.get("message_ar", ""),
                severity=item.get("severity", "warning"),
            )
            for item in (row.parser_warnings or [])
        ]
        normalized_by_row[row.id] = result.data
        issues_by_row[row.id] = extra + result.issues

    active = [row for row in rows if not row.is_excluded]
    seen: dict[str, str] = {}
    for row in active:
        fingerprint = row_fingerprint(normalized_by_row[row.id])
        if fingerprint in seen:
            issues_by_row[row.id].append(issue("DUPLICATE_ROW"))
        else:
            seen[fingerprint] = row.id

    phone_names: dict[str, set[str]] = {}
    for row in active:
        data = normalized_by_row[row.id]
        phone = data.get("guardian_phone_normalized")
        if not phone:
            continue
        phone_names.setdefault(str(phone), set()).add(
            normalize_name_key(data.get("guardian_name"))
        )
    shared = {phone for phone, names in phone_names.items() if len(names) > 1}
    for row in active:
        data = normalized_by_row[row.id]
        if data.get("guardian_phone_normalized") in shared:
            codes = {item.code for item in issues_by_row[row.id]}
            if "SHARED_PHONE" not in codes:
                issues_by_row[row.id].append(issue("SHARED_PHONE"))

    valid_rows = 0
    invalid_rows = 0
    duplicate_rows = 0
    error_counts: dict[str, int] = {}
    for row in rows:
        row_issues = issues_by_row[row.id]
        data = normalized_by_row[row.id]
        data["is_excluded"] = row.is_excluded
        row.normalized_data = data
        row.validation_errors = [item.as_dict() for item in row_issues]
        if row.is_excluded:
            row.validation_status = "excluded"
            continue
        errors = [item for item in row_issues if item.severity == "error"]
        if errors:
            row.validation_status = "invalid"
            invalid_rows += 1
            for item in errors:
                error_counts[item.code] = error_counts.get(item.code, 0) + 1
            if any(item.code == "DUPLICATE_ROW" for item in errors):
                duplicate_rows += 1
        elif any(item.severity == "warning" for item in row_issues):
            row.validation_status = "warning"
            valid_rows += 1
        else:
            row.validation_status = "valid"
            valid_rows += 1

    batch.total_rows = len(rows)
    batch.valid_rows = valid_rows
    batch.invalid_rows = invalid_rows
    batch.duplicate_rows = duplicate_rows
    batch.excluded_rows = sum(1 for row in rows if row.is_excluded)

    totals: dict[str, Decimal] = {}
    for row in rows:
        if row.is_excluded or row.validation_status == "invalid":
            continue
        data = normalized_by_row[row.id]
        currency = data.get("currency")
        remaining = data.get("remaining_balance")
        if not currency or remaining is None:
            continue
        totals[str(currency)] = totals.get(str(currency), Decimal("0")) + Decimal(
            str(remaining)
        )
    batch.totals_by_currency = {
        currency: money_to_string(value) for currency, value in sorted(totals.items())
    }

    batch.error_summary = (
        {"count": invalid_rows, "by_code": error_counts} if invalid_rows else None
    )

    has_warnings = bool(batch.warnings) or any(
        row.validation_status == "warning" for row in rows if not row.is_excluded
    )
    active_count = sum(1 for row in rows if not row.is_excluded)
    if batch.status not in {"uploaded", "failed", "confirmed", "cancelled"}:
        if invalid_rows == 0 and active_count > 0 and not has_warnings:
            batch.status = "ready_to_confirm"
        else:
            batch.status = "review_required"

    db.flush()
    return rows


def apply_normalized_patch(
    row: StagedRow,
    patch: dict[str, Any],
) -> list[str]:
    normalized = dict(row.normalized_data or {})
    changed: list[str] = []
    for key, value in patch.items():
        if key not in EDITABLE_NORMALIZED_FIELDS:
            continue
        normalized[key] = value
        changed.append(key)
    row.normalized_data = normalized
    return changed
