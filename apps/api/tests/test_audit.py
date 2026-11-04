from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.audit import record_audit
from app.db import engine
from app.models import AuditEvent
from app.privacy import _MASK_BULLET, mask_phone, redact_audit_payload

from .conftest import SessionLocal


def test_audit_events_are_append_only(admin_client: tuple[TestClient, str]) -> None:
    # Login writes an audit event, so there is always a row to probe.
    admin_client[0].get("/api/v1/auth/me")

    with engine.connect() as connection:
        trigger = connection.scalar(
            text(
                "SELECT tgname FROM pg_trigger "
                "WHERE tgname = 'audit_events_no_update_delete'"
            )
        )
    assert trigger == "audit_events_no_update_delete"

    with SessionLocal() as db:
        event_id = db.scalar(
            select(AuditEvent.id).order_by(AuditEvent.created_at.asc()).limit(1)
        )
    assert event_id is not None

    with engine.connect() as connection:
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(
                text("UPDATE audit_events SET action = 'tampered' WHERE id = :id"),
                {"id": event_id},
            )
        connection.rollback()

    with engine.connect() as connection:
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(
                text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id}
            )
        connection.rollback()

    with engine.connect() as connection:
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(text("TRUNCATE audit_events"))
        connection.rollback()

    with SessionLocal() as db:
        event = db.get(AuditEvent, event_id)
        assert event is not None
        assert event.action != "tampered"


def test_mask_phone_is_idempotent_for_masked_values() -> None:
    masked = mask_phone("+963993000701")
    assert masked == "+963 9•• ••• 701"
    assert mask_phone(masked) == masked


def test_redact_audit_payload_handles_nested_phone_keys() -> None:
    payload = {
        "row_id": "row-1",
        "normalized_data": {
            "guardian_phone_original": "+963993000701",
            "guardian_name": "ولي أمر أحمد",
            "remaining_balance": "100000.00",
        },
        "contacts": [
            {"mobile": "+963993000702", "is_primary": True},
            {"telephone_number": "0993000703"},
        ],
        "rows": [{"nested": {"Phone": "+963993000704"}}],
        "guardian_phone_normalized": "+963993000705",
        "amount": "600000.00",
    }

    redacted = redact_audit_payload(payload)
    serialized = str(redacted)

    for raw in (
        "+963993000701",
        "+963993000702",
        "0993000703",
        "+963993000704",
        "+963993000705",
    ):
        assert raw not in serialized
    assert redacted["normalized_data"]["guardian_phone_original"] == "+963 9•• ••• 701"
    assert redacted["contacts"][0]["mobile"] == "+963 9•• ••• 702"
    assert redacted["rows"][0]["nested"]["Phone"] == "+963 9•• ••• 704"
    # Non-phone fields are preserved verbatim.
    assert redacted["normalized_data"]["guardian_name"] == "ولي أمر أحمد"
    assert redacted["normalized_data"]["remaining_balance"] == "100000.00"
    assert redacted["amount"] == "600000.00"
    assert redacted["row_id"] == "row-1"


def test_redact_audit_payload_keeps_already_masked_values() -> None:
    payload = {"guardian_phone_original": "+963 9•• ••• 701"}

    redacted = redact_audit_payload(payload)

    assert redacted["guardian_phone_original"] == "+963 9•• ••• 701"
    assert _MASK_BULLET in redacted["guardian_phone_original"]


def test_record_audit_persists_only_redacted_phone_payloads() -> None:
    with SessionLocal() as db:
        event = record_audit(
            db,
            request=None,
            actor_user_id=None,
            action="test.audit_redaction",
            entity_type="test",
            entity_id="test-redaction",
            before={
                "normalized_data": {"guardian_phone_original": "+963993000701"},
                "contacts": [{"mobile": "+963993000702"}],
            },
            after={
                "nested": {
                    "telephone": "0993000703",
                    "already_masked": "+963 9•• ••• 704",
                },
                "guardian_name": "ولي أمر سارة",
            },
        )
        db.flush()
        event_id = event.id
        db.commit()

    with SessionLocal() as db:
        stored = db.get(AuditEvent, event_id)

    assert stored is not None
    payload = {"before": stored.before_data, "after": stored.after_data}
    serialized = str(payload)
    for raw in ("+963993000701", "+963993000702", "0993000703"):
        assert raw not in serialized
    assert stored.before_data["normalized_data"]["guardian_phone_original"] == (
        "+963 9•• ••• 701"
    )
    assert stored.before_data["contacts"][0]["mobile"] == "+963 9•• ••• 702"
    assert stored.after_data["nested"]["telephone"] == "+963 9•• ••• 703"
    assert stored.after_data["nested"]["already_masked"] == "+963 9•• ••• 704"
    assert stored.after_data["guardian_name"] == "ولي أمر سارة"

