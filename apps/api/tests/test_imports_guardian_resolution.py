from __future__ import annotations

import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.imports.normalization import normalize_name_key, normalize_phone
from app.models import (
    AuditEvent,
    FeeBalance,
    Guardian,
    GuardianContact,
    GuardianStudentRelationship,
    ImportBatch,
    StagedRow,
    Student,
)

from .conftest import SessionLocal


def _clean_import_tables() -> None:
    with SessionLocal() as db:
        for model in (
            FeeBalance,
            GuardianStudentRelationship,
            GuardianContact,
            Student,
            Guardian,
            StagedRow,
            ImportBatch,
        ):
            db.execute(delete(model))
        db.commit()


@pytest.fixture(autouse=True)
def import_environment() -> None:
    _clean_import_tables()
    yield
    _clean_import_tables()


def _guardian(name: str, phone: str | None = None, *, status: str = "active") -> str:
    with SessionLocal() as db:
        guardian = Guardian(
            id=str(uuid4()),
            full_name=name,
            normalized_name=normalize_name_key(name)[:255],
            status=status,
        )
        db.add(guardian)
        db.flush()
        if phone:
            result = normalize_phone(phone)
            db.add(
                GuardianContact(
                    id=str(uuid4()),
                    guardian_id=guardian.id,
                    original_phone=result.original,
                    normalized_phone=result.normalized,
                    contact_type="mobile",
                    is_primary=True,
                    is_verified=False,
                )
            )
        db.commit()
        return guardian.id


def _normalized(
    name: str,
    phone: str | None = None,
    *,
    student: str | None = None,
    remaining: str = "600000.00",
) -> dict:
    phone_result = normalize_phone(phone)
    return {
        "guardian_name": name,
        "guardian_phone_original": phone_result.original or None,
        "guardian_phone_normalized": phone_result.normalized,
        "student_name": student,
        "total_fee": "1000.00",
        "amount_paid": "400.00",
        "remaining_balance": remaining,
        "remaining_balance_calculated": "600.00",
        "currency": "SYP",
        "fee_period": None,
        "is_eligible": True,
    }


def _create_batch(
    rows: list[dict],
    *,
    status: str = "review_required",
) -> tuple[str, list[str]]:
    batch_id = str(uuid4())
    row_ids: list[str] = []
    with SessionLocal() as db:
        db.add(
            ImportBatch(
                id=batch_id,
                source_filename="guardian-resolution.xlsx",
                file_hash=uuid4().hex + uuid4().hex,
                file_type="xlsx",
                status=status,
                total_rows=len(rows),
                valid_rows=len(rows),
                invalid_rows=0,
                duplicate_rows=0,
                excluded_rows=0,
                totals_by_currency={},
            )
        )
        db.flush()
        for position, row in enumerate(rows):
            row_id = str(uuid4())
            row_ids.append(row_id)
            db.add(
                StagedRow(
                    id=row_id,
                    import_batch_id=batch_id,
                    position=position,
                    raw_data={},
                    normalized_data=row["normalized_data"],
                    parser_warnings=[],
                    validation_status=row.get("validation_status", "valid"),
                    validation_errors=[],
                    is_excluded=row.get("is_excluded", False),
                    guardian_resolution_mode=row.get("mode", "auto"),
                    resolved_guardian_id=row.get("resolved_guardian_id"),
                )
            )
        db.commit()
    return batch_id, row_ids


def _confirm(client: TestClient, csrf: str, batch_id: str) -> object:
    return client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )


def test_guardian_candidates_statuses_and_masking(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    ahmed = _guardian("أحمد علي", "0991111111")
    _guardian("أحمد علي", "0992222222")
    samer = _guardian("سامر خالد", "0993333333")
    _guardian("نور حسن", "0994444444")
    _guardian("نور حسن", "0994444444")

    batch_id, row_ids = _create_batch(
        [
            {"normalized_data": _normalized("أحمد علي", "0991111111")},
            {"normalized_data": _normalized("أحمد علي", "0995555555")},
            {"normalized_data": _normalized("اسم مختلف", "0993333333")},
            {"normalized_data": _normalized("نور حسن", "0994444444")},
            {
                "normalized_data": _normalized("يدوي اختيار", None),
                "mode": "link_existing",
                "resolved_guardian_id": ahmed,
            },
        ]
    )

    response = client.get(f"/api/v1/imports/{batch_id}/guardian-candidates")
    assert response.status_code == 200, response.text
    body = response.json()

    by_row = {item["row_id"]: item for item in body["items"]}
    assert by_row[row_ids[0]]["status"] == "exact"
    assert by_row[row_ids[1]]["status"] == "same_name"
    assert by_row[row_ids[2]]["status"] == "shared_phone"
    assert by_row[row_ids[3]]["status"] == "ambiguous"
    assert by_row[row_ids[4]]["status"] == "manual"
    assert by_row[row_ids[4]]["resolved_guardian_id"] == ahmed
    assert by_row[row_ids[4]]["resolved_guardian_name"] == "أحمد علي"
    assert by_row[row_ids[4]]["candidates"] == []
    assert body["counts"] == {
        "ambiguous": 1,
        "same_name": 1,
        "shared_phone": 1,
        "manual": 1,
    }

    exact_candidates = by_row[row_ids[0]]["candidates"]
    assert exact_candidates
    assert exact_candidates[0]["guardian_id"] == ahmed
    assert exact_candidates[0]["match"] == "exact"
    assert exact_candidates[0]["phone_masked"]
    assert all(
        set(item) == {"guardian_id", "full_name", "phone_masked", "status", "match"}
        for item in exact_candidates
    )
    assert len(by_row[row_ids[3]]["candidates"]) == 2
    assert by_row[row_ids[2]]["candidates"][0]["guardian_id"] == samer

    serialized = json.dumps(body)
    assert "+963991111111" not in serialized
    assert "+963993333333" not in serialized
    assert "+963994444444" not in serialized


def test_row_patch_resolution_modes_validation_and_audit(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    target = _guardian("ولي أمر نشط", "0997777777")
    inactive = _guardian("ولي أمر معطّل", "0998888888", status="inactive")
    batch_id, row_ids = _create_batch(
        [{"normalized_data": _normalized("اسم في الملف", "0999999999")}]
    )
    row_id = row_ids[0]

    linked = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}",
        headers={"X-CSRF-Token": csrf},
        json={"guardian_resolution": {"mode": "link_existing", "guardian_id": target}},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["guardian_resolution_mode"] == "link_existing"
    assert linked.json()["resolved_guardian_id"] == target

    cleared = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}",
        headers={"X-CSRF-Token": csrf},
        json={"guardian_resolution": {"mode": "create_new"}},
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["guardian_resolution_mode"] == "create_new"
    assert cleared.json()["resolved_guardian_id"] is None

    auto = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}",
        headers={"X-CSRF-Token": csrf},
        json={"guardian_resolution": {"mode": "auto"}},
    )
    assert auto.status_code == 200, auto.text
    assert auto.json()["guardian_resolution_mode"] == "auto"
    assert auto.json()["resolved_guardian_id"] is None

    missing_target = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}",
        headers={"X-CSRF-Token": csrf},
        json={
            "guardian_resolution": {
                "mode": "link_existing",
                "guardian_id": str(uuid4()),
            }
        },
    )
    assert missing_target.status_code == 404
    assert missing_target.json()["error"]["code"] == "GUARDIAN_NOT_FOUND"

    inactive_target = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}",
        headers={"X-CSRF-Token": csrf},
        json={
            "guardian_resolution": {"mode": "link_existing", "guardian_id": inactive}
        },
    )
    assert inactive_target.status_code == 409
    assert inactive_target.json()["error"]["code"] == "GUARDIAN_INACTIVE"

    needs_id = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{row_id}",
        headers={"X-CSRF-Token": csrf},
        json={"guardian_resolution": {"mode": "link_existing"}},
    )
    assert needs_id.status_code == 422

    with SessionLocal() as db:
        events = list(
            db.scalars(
                select(AuditEvent)
                .where(
                    AuditEvent.entity_id == batch_id,
                    AuditEvent.action == "import.guardian.resolve",
                )
                .order_by(AuditEvent.created_at.asc())
            ).all()
        )
    assert len(events) == 3
    assert events[0].before_data["mode"] == "auto"
    assert events[0].after_data == {
        "row_id": row_id,
        "mode": "link_existing",
        "guardian_id": target,
    }
    assert events[2].after_data["mode"] == "auto"
    assert events[2].after_data["guardian_id"] is None
    assert "0997777777" not in json.dumps(
        [event.before_data for event in events]
        + [event.after_data for event in events]
    )


def test_confirm_blocks_ambiguous_guardian_without_partial_writes(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    _guardian("ولي أمر مكرر", "0996666666")
    _guardian("ولي أمر مكرر", "0996666666")
    batch_id, row_ids = _create_batch(
        [{"normalized_data": _normalized("ولي أمر مكرر", "0996666666")}]
    )

    blocked = _confirm(client, csrf, batch_id)
    assert blocked.status_code == 409, blocked.text
    error = blocked.json()["error"]
    assert error["code"] == "AMBIGUOUS_GUARDIAN"
    assert error["details"]["row_ids"] == row_ids[:50]

    with SessionLocal() as db:
        batch = db.get(ImportBatch, batch_id)
        assert batch is not None and batch.status == "review_required"
        assert len(list(db.scalars(select(Guardian)).all())) == 2
        assert list(db.scalars(select(FeeBalance)).all()) == []
        assert list(db.scalars(select(Student)).all()) == []


def test_confirm_link_existing_reuses_target_guardian(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    target = _guardian("الولي المستهدف", "0995555555")
    batch_id, _ = _create_batch(
        [
            {
                "normalized_data": _normalized(
                    "اسم مختلف في الملف", "0994444444", student="طالب مرتبط"
                ),
                "mode": "link_existing",
                "resolved_guardian_id": target,
            }
        ]
    )

    confirmed = _confirm(client, csrf, batch_id)
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"

    with SessionLocal() as db:
        guardians = list(db.scalars(select(Guardian)).all())
        balance = db.scalar(select(FeeBalance))
        contacts = list(db.scalars(select(GuardianContact)).all())
        event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.entity_id == batch_id, AuditEvent.action == "import.confirm")
            .order_by(AuditEvent.created_at.desc())
        )
    assert len(guardians) == 1
    assert guardians[0].id == target
    assert balance is not None and balance.guardian_id == target
    assert {contact.guardian_id for contact in contacts} == {target}
    assert event is not None
    assert event.after_data["guardian_resolution_counts"]["link_existing"] == 1


def test_confirm_create_new_ignores_exact_match(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    existing = _guardian("ولي أمر موجود", "0993333333")
    batch_id, _ = _create_batch(
        [
            {
                "normalized_data": _normalized("ولي أمر موجود", "0993333333"),
                "mode": "create_new",
            }
        ]
    )

    confirmed = _confirm(client, csrf, batch_id)
    assert confirmed.status_code == 200, confirmed.text

    with SessionLocal() as db:
        guardians = list(db.scalars(select(Guardian)).all())
        balance = db.scalar(select(FeeBalance))
        event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.entity_id == batch_id, AuditEvent.action == "import.confirm")
            .order_by(AuditEvent.created_at.desc())
        )
    assert len(guardians) == 2
    assert balance is not None
    assert balance.guardian_id != existing
    assert event is not None
    assert event.after_data["guardian_resolution_counts"]["create_new"] == 1


def test_confirm_auto_reuses_unique_exact_match(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    existing = _guardian("ولي أمر فريد", "0992222222")
    batch_id, _ = _create_batch(
        [{"normalized_data": _normalized("ولي أمر فريد", "0992222222")}]
    )

    confirmed = _confirm(client, csrf, batch_id)
    assert confirmed.status_code == 200, confirmed.text

    with SessionLocal() as db:
        guardians = list(db.scalars(select(Guardian)).all())
        balance = db.scalar(select(FeeBalance))
        event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.entity_id == batch_id, AuditEvent.action == "import.confirm")
            .order_by(AuditEvent.created_at.desc())
        )
    assert len(guardians) == 1
    assert guardians[0].id == existing
    assert balance is not None and balance.guardian_id == existing
    assert event is not None
    assert event.after_data["guardian_resolution_counts"]["auto"] == 1
