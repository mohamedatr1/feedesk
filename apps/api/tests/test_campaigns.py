from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update

from app.campaigns import service as campaign_service
from app.db import SessionLocal
from app.models import (
    AuditEvent,
    Campaign,
    CampaignRecipient,
    FeeBalance,
    Guardian,
    GuardianContact,
    ImportBatch,
    Message,
    MessageTemplate,
    ProviderEvent,
    SendJob,
    User,
)

from .campaign_helpers import (
    clean_campaign_tables,
    create_campaign,
    create_confirmed_import,
    create_template,
    install_recipient_trigger,
)
from .conftest import login
from .messaging_helpers import create_campaign_messages


@pytest.fixture(autouse=True)
def campaign_environment() -> None:
    clean_campaign_tables()
    install_recipient_trigger()
    yield
    clean_campaign_tables()


def _two_recipient_import() -> dict:
    return create_confirmed_import(
        [
            {
                "name": "ولي أمر 001",
                "phone": "+963993000001",
                "amount": "600000",
                "currency": "SYP",
                "student": "طالب 001",
                "period": "الفصل الأول",
            },
            {
                "name": "ولي أمر 002",
                "phone": "+963993000002",
                "amount": "400",
                "currency": "USD",
                "student": "طالب 002",
                "period": "الفصل الثاني",
            },
        ]
    )


def _audit_actions(entity_id: str) -> list[str]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == entity_id)
            ).all()
        )


def test_campaign_create_list_detail_preview_patch_and_errors(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = _two_recipient_import()

    no_template = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json={"name": "بلا قالب", "source_import_id": import_data["batch_id"]},
    )
    assert no_template.status_code == 422
    assert no_template.json()["error"]["code"] == "NO_ACTIVE_TEMPLATE"

    missing_template = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "قالب مفقود",
            "source_import_id": import_data["batch_id"],
            "template_id": "missing-template",
        },
    )
    assert missing_template.status_code == 404
    assert missing_template.json()["error"]["code"] == "TEMPLATE_NOT_FOUND"

    template = create_template(client, csrf)
    default_campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        name="حملة بالقالب النشط",
    )
    assert default_campaign["template_id"] == template["id"]
    assert default_campaign["template_version"] == template["version"]
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    assert campaign["recipient_count"] == 2
    assert campaign["totals_by_currency"] == {"SYP": "600000.00", "USD": "400.00"}
    assert campaign["created_by_name"] == "admin_test"
    assert campaign["template_name"] == "قالب تذكير"
    assert campaign["can_submit"] is True
    assert campaign["can_approve"] is False
    assert campaign["revision"] == 0

    listing = client.get("/api/v1/campaigns", params={"status": "draft"}).json()
    assert listing["total"] == 2
    assert any(item["id"] == campaign["id"] for item in listing["items"])
    listed = next(item for item in listing["items"] if item["id"] == campaign["id"])
    assert listed["recipient_count"] == 2

    detail = client.get(f"/api/v1/campaigns/{campaign['id']}")
    preview = client.get(f"/api/v1/campaigns/{campaign['id']}/preview")
    assert detail.status_code == 200
    assert preview.status_code == 200
    detail_body = detail.json()
    preview_body = preview.json()
    assert detail_body["message_count"] == 0
    assert detail_body["pending_job_count"] == 0
    detail_by_key = {item["key"]: item for item in detail_body["recipients"]}
    preview_by_key = {item["key"]: item for item in preview_body["recipients"]}
    assert detail_by_key.keys() == preview_by_key.keys()
    for key, detail_recipient in detail_by_key.items():
        preview_recipient = preview_by_key[key]
        assert detail_recipient["phone"] == detail_recipient["phone_masked"]
        assert preview_recipient["phone_masked"] == detail_recipient["phone_masked"]
        assert preview_recipient["phone"] != preview_recipient["phone_masked"]
        assert detail_recipient["message"] == ""
        assert detail_recipient["student_names"] == []
        assert preview_recipient["message"]
        assert preview_recipient["student_names"]

    patched = client.patch(
        f"/api/v1/campaigns/{campaign['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"name": "اسم محدث"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["name"] == "اسم محدث"
    assert patched.json()["revision"] == 1

    source_change = client.patch(
        f"/api/v1/campaigns/{campaign['id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "اسم آخر",
            "source_import_id": import_data["batch_id"],
        },
    )
    assert source_change.status_code == 422

    unconfirmed = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json={"name": "غير مؤكد", "source_import_id": str(uuid4())},
    )
    assert unconfirmed.status_code == 422
    assert unconfirmed.json()["error"]["code"] == "IMPORT_NOT_CONFIRMED"

    with SessionLocal() as db:
        db.execute(
            update(ImportBatch)
            .where(ImportBatch.id == import_data["batch_id"])
            .values(status="review_required")
        )
        db.commit()
    not_confirmed = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json={"name": "استيراد تحت المراجعة", "source_import_id": import_data["batch_id"]},
    )
    assert not_confirmed.status_code == 422
    assert not_confirmed.json()["error"]["code"] == "IMPORT_NOT_CONFIRMED"

    assert client.get(f"/api/v1/campaigns/{uuid4()}").status_code == 404
    bad_filter = client.get("/api/v1/campaigns", params={"status": "nonsense"})
    assert bad_filter.status_code == 422


def test_draft_detail_refreshes_live_counts_totals_and_warnings(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر مباشر أ",
                "phone": "+963993000031",
                "amount": "600000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر مباشر ب",
                "phone": "+963993000032",
                "amount": "400",
                "currency": "USD",
            },
        ]
    )
    template = create_template(client, csrf)
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    assert campaign["recipient_count"] == 2
    assert campaign["excluded_count"] == 0
    assert campaign["totals_by_currency"] == {
        "SYP": "600000.00",
        "USD": "400.00",
    }
    assert campaign["warnings"] == []

    # Source changes after creation: one recipient becomes a zero-balance
    # exclusion, and a new confirmed balance shares the first recipient's phone.
    with SessionLocal() as db:
        db.execute(
            update(FeeBalance)
            .where(
                FeeBalance.guardian_id
                == import_data["guardian_ids"]["ولي أمر مباشر ب"]
            )
            .values(remaining_balance_source=Decimal("0.00"))
        )
        guardian = Guardian(
            id=str(uuid4()),
            full_name="ولي أمر مباشر ج",
            normalized_name="ولي أمر مباشر ج",
            status="active",
        )
        db.add(guardian)
        db.flush()
        db.add(
            GuardianContact(
                id=str(uuid4()),
                guardian_id=guardian.id,
                original_phone="+963993000031",
                normalized_phone="+963993000031",
                contact_type="mobile",
                is_primary=True,
                is_verified=False,
            )
        )
        db.add(
            FeeBalance(
                id=str(uuid4()),
                guardian_id=guardian.id,
                student_id=None,
                import_batch_id=import_data["batch_id"],
                fee_period=None,
                total_fee=Decimal("300000.00"),
                amount_paid=Decimal("0.00"),
                remaining_balance_source=Decimal("300000.00"),
                remaining_balance_calculated=None,
                currency="SYP",
                record_status="confirmed",
            )
        )
        db.commit()

    detail = client.get(f"/api/v1/campaigns/{campaign['id']}").json()
    preview = client.get(f"/api/v1/campaigns/{campaign['id']}/preview").json()
    assert detail["recipient_count"] == 2
    assert detail["excluded_count"] == 1
    assert detail["totals_by_currency"] == {"SYP": "900000.00"}
    assert detail["warnings"] == [
        {
            "code": "SHARED_PHONE",
            "message_ar": "رقم هاتف مشترك بين أكثر من ولي أمر.",
            "count": 2,
        }
    ]
    assert detail["can_submit"] is True
    assert preview["recipient_count"] == detail["recipient_count"]
    assert preview["excluded_count"] == detail["excluded_count"]
    assert preview["totals_by_currency"] == detail["totals_by_currency"]
    assert preview["warnings"] == detail["warnings"]

    # The list intentionally keeps the persisted summary until a mutating
    # action recomputes and stores it.
    listing = client.get("/api/v1/campaigns", params={"status": "draft"}).json()
    listed = next(item for item in listing["items"] if item["id"] == campaign["id"])
    assert listed["recipient_count"] == 2
    assert listed["excluded_count"] == 0
    assert listed["totals_by_currency"] == {
        "SYP": "600000.00",
        "USD": "400.00",
    }
    assert listed["warnings"] == []


def test_submit_and_approve_persist_fresh_preview_summary(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر اعتماد أ",
                "phone": "+963993000041",
                "amount": "600000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر اعتماد ب",
                "phone": "+963993000042",
                "amount": "400",
                "currency": "USD",
            },
        ]
    )
    template = create_template(client, csrf)
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    assert campaign["recipient_count"] == 2
    assert campaign["excluded_count"] == 0
    assert campaign["totals_by_currency"] == {
        "SYP": "600000.00",
        "USD": "400.00",
    }

    # Source changes after draft creation. Submission and approval must persist
    # the fresh preview rather than the stale creation summary.
    with SessionLocal() as db:
        db.execute(
            update(FeeBalance)
            .where(
                FeeBalance.guardian_id
                == import_data["guardian_ids"]["ولي أمر اعتماد ب"]
            )
            .values(remaining_balance_source=Decimal("0.00"))
        )
        guardian = Guardian(
            id=str(uuid4()),
            full_name="ولي أمر اعتماد ج",
            normalized_name="ولي أمر اعتماد ج",
            status="active",
        )
        db.add(guardian)
        db.flush()
        db.add(
            GuardianContact(
                id=str(uuid4()),
                guardian_id=guardian.id,
                original_phone="+963993000041",
                normalized_phone="+963993000041",
                contact_type="mobile",
                is_primary=True,
                is_verified=False,
            )
        )
        db.add(
            FeeBalance(
                id=str(uuid4()),
                guardian_id=guardian.id,
                student_id=None,
                import_batch_id=import_data["batch_id"],
                fee_period=None,
                total_fee=Decimal("300000.00"),
                amount_paid=Decimal("0.00"),
                remaining_balance_source=Decimal("300000.00"),
                remaining_balance_calculated=None,
                currency="SYP",
                record_status="confirmed",
            )
        )
        db.commit()

    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200, submitted.text
    submitted_body = submitted.json()
    assert submitted_body["recipient_count"] == 2
    assert submitted_body["excluded_count"] == 1
    assert submitted_body["totals_by_currency"] == {"SYP": "900000.00"}
    assert submitted_body["warnings"][0]["code"] == "SHARED_PHONE"

    approved = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_revision": submitted_body["revision"],
            "acknowledge_warnings": True,
        },
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["recipient_count"] == len(body["recipients"]) == 2
    assert body["excluded_count"] == len(body["excluded"]) == 1
    assert body["invalid_contact_count"] == 0
    assert body["totals_by_currency"] == {"SYP": "900000.00"}
    assert body["warnings"] == [
        {
            "code": "SHARED_PHONE",
            "message_ar": "رقم هاتف مشترك بين أكثر من ولي أمر.",
            "count": 2,
        }
    ]
    assert {recipient["guardian_name"] for recipient in body["recipients"]} == {
        "ولي أمر اعتماد أ",
        "ولي أمر اعتماد ج",
    }
    assert body["excluded"][0]["guardian_name"] == "ولي أمر اعتماد ب"
    assert body["excluded"][0]["reasons"][0]["code"] == "ZERO_BALANCE"

    with SessionLocal() as db:
        campaign_row = db.get(Campaign, campaign["id"])
        messages = list(
            db.scalars(
                select(Message).where(Message.campaign_id == campaign["id"])
            ).all()
        )
        snapshot_excluded = list(campaign_row.excluded_snapshot)
        snapshot_totals = dict(campaign_row.totals_by_currency)
        snapshot_warnings = list(campaign_row.warnings)
        preview_snapshot = dict(campaign_row.preview_snapshot)
    assert campaign_row is not None
    assert campaign_row.recipient_count == 2
    assert campaign_row.excluded_count == 1
    assert snapshot_totals == {"SYP": "900000.00"}
    # ``phone_masked`` is derived at the response layer, not persisted.
    assert snapshot_excluded == [
        {key: value for key, value in record.items() if key != "phone_masked"}
        for record in body["excluded"]
    ]
    assert snapshot_warnings == body["warnings"]
    assert preview_snapshot["recipient_count"] == 2
    assert preview_snapshot["excluded_count"] == 1
    assert len(messages) == 2
    assert all(message.internal_status == "pending" for message in messages)


def test_submit_approve_snapshot_messages_jobs_hash_and_idempotency(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    staff, staff_csrf = staff_client
    import_data = _two_recipient_import()
    template = create_template(client, csrf)
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )

    conflict = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 99},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CAMPAIGN_CHANGED"

    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200, submitted.text
    submitted_body = submitted.json()
    assert submitted_body["status"] == "awaiting_approval"
    assert submitted_body["submitted_at"]
    assert submitted_body["revision"] == 1
    assert submitted_body["can_approve"] is True

    again = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 1},
    )
    assert again.status_code == 409

    staff_approve = staff.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert staff_approve.status_code == 403

    stale_approve = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 0, "acknowledge_warnings": False},
    )
    assert stale_approve.status_code == 409
    assert stale_approve.json()["error"]["code"] == "CAMPAIGN_CHANGED"
    assert stale_approve.json()["error"]["details"]["current_revision"] == 1

    approved = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "approved"
    assert body["approved_by_name"] == "admin_test"
    assert body["approved_at"]
    assert body["revision"] == 2
    assert len(body["snapshot_hash"]) == 64
    assert body["can_cancel"] is True
    assert body["message_count"] == 2
    assert body["pending_job_count"] == 2
    assert all(recipient["id"] for recipient in body["recipients"])
    assert {recipient["phone"] for recipient in body["recipients"]} == {
        "+963993000001",
        "+963993000002",
    }
    assert "600,000.00" in next(
        recipient["message"]
        for recipient in body["recipients"]
        if recipient["currency"] == "SYP"
    )

    with SessionLocal() as db:
        messages = list(
            db.scalars(
                select(Message).where(Message.campaign_id == campaign["id"])
            ).all()
        )
        jobs = list(
            db.scalars(
                select(SendJob).where(
                    SendJob.message_id.in_([message.id for message in messages])
                )
            ).all()
        )
        recipient_rows = list(
            db.scalars(
                select(CampaignRecipient).where(
                    CampaignRecipient.campaign_id == campaign["id"]
                )
            ).all()
        )
        provider_events = db.scalar(
            select(func.count()).select_from(ProviderEvent)
        )
        campaign_row = db.get(Campaign, campaign["id"])
        stored_template = db.get(MessageTemplate, campaign["template_id"])
        approver = db.scalar(select(User).where(User.username == "admin_test"))
        approval_event = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.entity_id == campaign["id"],
                AuditEvent.action == "campaign.approve",
            )
            .order_by(AuditEvent.created_at.desc())
        )

    assert len(messages) == 2
    assert len(jobs) == 2
    assert len(recipient_rows) == 2
    assert provider_events == 0
    assert all(message.internal_status == "pending" for message in messages)
    assert all(message.provider == "rasel" for message in messages)
    assert all(message.channel == "sms" for message in messages)
    assert all(message.submitted_at is None for message in messages)
    assert all(message.provider_request_id is None for message in messages)
    assert all(job.status == "pending" for job in jobs)
    assert all(job.attempt_count == 0 for job in jobs)
    assert all(job.next_attempt_at is None for job in jobs)
    assert len({job.message_id for job in jobs}) == 2
    assert all(len(message.idempotency_key) <= 80 for message in messages)
    assert len({message.idempotency_key for message in messages}) == 2
    assert all(row.eligibility_status == "eligible" for row in recipient_rows)

    # The hash is reproducible from the frozen snapshot.
    assert campaign_row is not None and stored_template is not None and approver is not None
    stored_recipients = [
        {
            "guardian_id": row.guardian_id,
            "guardian_name": row.guardian_name_snapshot,
            "phone": row.destination_phone_snapshot,
            "amount": f"{row.amount_snapshot:.2f}",
            "currency": row.currency_snapshot,
            "message": row.message_body_snapshot,
            "fee_balance_ids": list(row.fee_details_snapshot["fee_balance_ids"]),
            "student_names": list(row.fee_details_snapshot["student_names"]),
            "fee_periods": list(row.fee_details_snapshot["fee_periods"]),
        }
        for row in recipient_rows
    ]
    preview_recipients = list(campaign_row.preview_snapshot["recipients"])
    stored_payload = campaign_service._snapshot_payload(
        campaign=campaign_row,
        template=stored_template,
        approver=approver,
        approved_at=campaign_row.approved_at,
        recipients=stored_recipients,
    )
    preview_payload = campaign_service._snapshot_payload(
        campaign=campaign_row,
        template=stored_template,
        approver=approver,
        approved_at=campaign_row.approved_at,
        recipients=preview_recipients,
    )
    assert stored_payload == preview_payload
    assert approval_event is not None
    assert datetime.fromisoformat(approval_event.after_data["approved_at"]) == (
        campaign_row.approved_at
    )
    recomputed = campaign_service._snapshot_hash(
        campaign=campaign_row,
        template=stored_template,
        approver=approver,
        approved_at=campaign_row.approved_at,
        recipients=stored_recipients,
    )
    assert recomputed == body["snapshot_hash"]

    actions = _audit_actions(campaign["id"])
    assert "campaign.create" in actions
    assert "campaign.submit" in actions
    assert "campaign.approve" in actions
    with SessionLocal() as db:
        approve_event = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.entity_id == campaign["id"],
                AuditEvent.action == "campaign.approve",
            )
            .order_by(AuditEvent.created_at.desc())
        )
    assert approve_event is not None
    assert approve_event.after_data["snapshot_hash"] == body["snapshot_hash"]
    assert approve_event.after_data["recipient_count"] == 2
    assert approve_event.after_data["totals_by_currency"] == {
        "SYP": "600000.00",
        "USD": "400.00",
    }

    repeated = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 2, "acknowledge_warnings": False},
    )
    assert repeated.status_code == 200
    assert repeated.json()["snapshot_hash"] == body["snapshot_hash"]
    assert repeated.json()["revision"] == body["revision"]

    with SessionLocal() as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.campaign_id == campaign["id"])
            )
            == 2
        )
        assert (
            db.scalar(select(func.count()).select_from(SendJob)) == 2
        )

    # Source edits after approval do not alter the snapshot or hash.
    with SessionLocal() as db:
        db.execute(
            update(GuardianContact)
            .where(GuardianContact.guardian_id == import_data["guardian_ids"]["ولي أمر 001"])
            .values(normalized_phone="+963999000099")
        )
        db.execute(
            update(FeeBalance)
            .where(FeeBalance.import_batch_id == import_data["batch_id"])
            .values(remaining_balance_source=Decimal("1.00"))
        )
        db.commit()
    after_edit = client.get(f"/api/v1/campaigns/{campaign['id']}").json()
    assert after_edit["snapshot_hash"] == body["snapshot_hash"]
    assert {recipient["phone"] for recipient in after_edit["recipients"]} == {
        "+963 9•• ••• 001",
        "+963 9•• ••• 002",
    }
    assert all(
        recipient["phone"] == recipient["phone_masked"]
        for recipient in after_edit["recipients"]
    )
    assert all(recipient["message"] == "" for recipient in after_edit["recipients"])
    assert all(
        recipient["student_names"] == []
        for recipient in after_edit["recipients"]
    )
    assert {recipient["amount"] for recipient in after_edit["recipients"]} == {
        "600000.00",
        "400.00",
    }
    assert not hasattr(campaign_service, "httpx")
    assert not hasattr(campaign_service, "requests")


def test_approval_transaction_rolls_back_on_failure(
    admin_client: tuple[TestClient, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = admin_client
    import_data = _two_recipient_import()
    template = create_template(client, csrf)
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200

    safe_client = TestClient(client.app, raise_server_exceptions=False)
    safe_csrf = login(safe_client, "admin_test", "AdminTest!2026")

    def boom(*args, **kwargs):
        raise RuntimeError("forced audit failure")

    monkeypatch.setattr(campaign_service, "record_audit", boom)
    failed = safe_client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": safe_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert failed.status_code == 500

    with SessionLocal() as db:
        campaign_row = db.get(Campaign, campaign["id"])
        recipients = db.scalar(
            select(func.count())
            .select_from(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign["id"])
        )
        messages = db.scalar(
            select(func.count())
            .select_from(Message)
            .where(Message.campaign_id == campaign["id"])
        )
        jobs = db.scalar(select(func.count()).select_from(SendJob))
    assert campaign_row is not None
    assert campaign_row.status == "awaiting_approval"
    assert campaign_row.revision == 1
    assert campaign_row.approved_by is None
    assert campaign_row.snapshot_hash is None
    assert recipients == 0
    assert messages == 0
    assert jobs == 0

    monkeypatch.undo()
    succeeded = safe_client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": safe_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert succeeded.status_code == 200, succeeded.text
    assert succeeded.json()["status"] == "approved"


def test_cancel_rules_idempotency_and_snapshot_retention(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    admin, admin_csrf = admin_client
    staff, staff_csrf = staff_client
    import_data = _two_recipient_import()
    template = create_template(admin, admin_csrf)

    draft = create_campaign(
        staff,
        staff_csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    conflict = staff.post(
        f"/api/v1/campaigns/{draft['id']}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 9, "reason": "سبب"},
    )
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "CAMPAIGN_CHANGED"

    cancelled = staff.post(
        f"/api/v1/campaigns/{draft['id']}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0, "reason": "لم يعد مطلوبًا"},
    )
    assert cancelled.status_code == 200, cancelled.text
    cancelled_body = cancelled.json()
    assert cancelled_body["status"] == "cancelled"
    assert cancelled_body["cancelled_at"]
    assert cancelled_body["cancel_reason"] == "لم يعد مطلوبًا"
    assert cancelled_body["revision"] == 1
    assert cancelled_body["can_cancel"] is False
    assert "campaign.cancel" in _audit_actions(draft["id"])

    cancelled_listing = staff.get(
        "/api/v1/campaigns", params={"status": "cancelled"}
    ).json()
    listed = next(
        item for item in cancelled_listing["items"] if item["id"] == draft["id"]
    )
    assert listed["cancel_reason"] == "لم يعد مطلوبًا"
    assert listed["cancelled_at"] == cancelled_body["cancelled_at"]

    repeated = staff.post(
        f"/api/v1/campaigns/{draft['id']}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0},
    )
    assert repeated.status_code == 200
    assert repeated.json()["revision"] == 1

    approved_campaign = create_campaign(
        staff,
        staff_csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    submitted = staff.post(
        f"/api/v1/campaigns/{approved_campaign['id']}/submit",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200
    approved = admin.post(
        f"/api/v1/campaigns/{approved_campaign['id']}/approve",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert approved.status_code == 200
    approved_body = approved.json()
    original_recipients = approved_body["recipients"]

    staff_cancel = staff.post(
        f"/api/v1/campaigns/{approved_campaign['id']}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": approved_body["revision"], "reason": "محاولة"},
    )
    assert staff_cancel.status_code == 403

    admin_cancel = admin.post(
        f"/api/v1/campaigns/{approved_campaign['id']}/cancel",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_revision": approved_body["revision"], "reason": "إلغاء معتمد"},
    )
    assert admin_cancel.status_code == 200, admin_cancel.text
    final = admin_cancel.json()
    assert final["status"] == "cancelled"
    assert final["cancel_reason"] == "إلغاء معتمد"
    assert final["snapshot_hash"] == approved_body["snapshot_hash"]
    assert final["recipients"] == original_recipients
    assert final["message_count"] == 2
    assert final["pending_job_count"] == 0

    with SessionLocal() as db:
        messages = list(
            db.scalars(
                select(Message).where(
                    Message.campaign_id == approved_campaign["id"]
                )
            ).all()
        )
        jobs = list(
            db.scalars(
                select(SendJob).where(
                    SendJob.message_id.in_([message.id for message in messages])
                )
            ).all()
        )
        recipients = db.scalar(
            select(func.count())
            .select_from(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == approved_campaign["id"])
        )
    assert len(messages) == 2
    assert all(message.internal_status == "cancelled" for message in messages)
    assert len(jobs) == 2
    assert all(job.status == "cancelled" for job in jobs)
    assert recipients == 2


def test_approved_excluded_and_warnings_snapshot_is_frozen(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر مشترك أ",
                "phone": "+963993000021",
                "amount": "600000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر مشترك ب",
                "phone": "+963993000021",
                "amount": "700000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر هاتف خاطئ",
                "phone": "INVALID",
                "amount": "500000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر بلا هاتف",
                "phone": None,
                "amount": "500000",
                "currency": "SYP",
            },
        ]
    )
    template = create_template(client, csrf)
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    assert campaign["recipient_count"] == 2
    assert campaign["excluded_count"] == 2
    assert campaign["invalid_contact_count"] == 2
    assert campaign["warnings"][0]["code"] == "SHARED_PHONE"
    assert campaign["warnings"][0]["count"] == 2

    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 1, "acknowledge_warnings": True},
    )
    assert approved.status_code == 200, approved.text
    approved_body = approved.json()
    frozen_excluded = approved_body["excluded"]
    frozen_warnings = approved_body["warnings"]
    assert {
        record["guardian_name"] for record in frozen_excluded
    } == {"ولي أمر هاتف خاطئ", "ولي أمر بلا هاتف"}
    assert frozen_warnings == [
        {
            "code": "SHARED_PHONE",
            "message_ar": "رقم هاتف مشترك بين أكثر من ولي أمر.",
            "count": 2,
        }
    ]

    # If the preview were recomputed, both excluded records and the shared
    # phone warning would disappear. The approved detail must stay frozen.
    with SessionLocal() as db:
        db.execute(
            update(GuardianContact)
            .where(
                GuardianContact.guardian_id
                == import_data["guardian_ids"]["ولي أمر هاتف خاطئ"]
            )
            .values(
                original_phone="+963993000022",
                normalized_phone="+963993000022",
            )
        )
        db.add(
            GuardianContact(
                id=str(uuid4()),
                guardian_id=import_data["guardian_ids"]["ولي أمر بلا هاتف"],
                original_phone="+963993000023",
                normalized_phone="+963993000023",
                contact_type="mobile",
                is_primary=True,
                is_verified=False,
            )
        )
        db.execute(
            update(GuardianContact)
            .where(
                GuardianContact.guardian_id
                == import_data["guardian_ids"]["ولي أمر مشترك أ"]
            )
            .values(normalized_phone="+963993000024")
        )
        db.execute(
            update(GuardianContact)
            .where(
                GuardianContact.guardian_id
                == import_data["guardian_ids"]["ولي أمر مشترك ب"]
            )
            .values(normalized_phone="+963993000025")
        )
        db.commit()

    after_edit = client.get(f"/api/v1/campaigns/{campaign['id']}").json()
    assert after_edit["excluded"] == frozen_excluded
    assert after_edit["warnings"] == frozen_warnings
    assert after_edit["excluded_count"] == 2
    assert after_edit["invalid_contact_count"] == 2
    with SessionLocal() as db:
        campaign_row = db.get(Campaign, campaign["id"])
    assert campaign_row is not None
    assert campaign_row.excluded_snapshot == [
        {key: value for key, value in record.items() if key != "phone_masked"}
        for record in frozen_excluded
    ]

    cancelled = client.post(
        f"/api/v1/campaigns/{campaign['id']}/cancel",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_revision": approved_body["revision"],
            "reason": "إلغاء بعد الاعتماد",
        },
    )
    assert cancelled.status_code == 200, cancelled.text
    cancelled_body = cancelled.json()
    assert cancelled_body["excluded"] == frozen_excluded
    assert cancelled_body["warnings"] == frozen_warnings


def test_detail_action_flags_are_permission_aware(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    admin, admin_csrf = admin_client
    staff, staff_csrf = staff_client
    import_data = _two_recipient_import()
    template = create_template(admin, admin_csrf)
    campaign = create_campaign(
        staff,
        staff_csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )

    staff_draft = staff.get(f"/api/v1/campaigns/{campaign['id']}").json()
    admin_draft = admin.get(f"/api/v1/campaigns/{campaign['id']}").json()
    assert staff_draft["can_submit"] is True
    assert staff_draft["can_approve"] is False
    assert staff_draft["can_cancel"] is True
    assert admin_draft["can_submit"] is True
    assert admin_draft["can_approve"] is False
    assert admin_draft["can_cancel"] is True

    submitted = staff.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200, submitted.text

    staff_awaiting = staff.get(f"/api/v1/campaigns/{campaign['id']}").json()
    admin_awaiting = admin.get(f"/api/v1/campaigns/{campaign['id']}").json()
    assert staff_awaiting["can_submit"] is False
    assert staff_awaiting["can_approve"] is False
    assert staff_awaiting["can_cancel"] is True
    assert admin_awaiting["can_submit"] is False
    assert admin_awaiting["can_approve"] is True
    assert admin_awaiting["can_cancel"] is True

    approved = admin.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["can_cancel"] is True

    staff_approved = staff.get(f"/api/v1/campaigns/{campaign['id']}").json()
    admin_approved = admin.get(f"/api/v1/campaigns/{campaign['id']}").json()
    assert staff_approved["can_submit"] is False
    assert staff_approved["can_approve"] is False
    assert staff_approved["can_cancel"] is False
    assert admin_approved["can_submit"] is False
    assert admin_approved["can_approve"] is False
    assert admin_approved["can_cancel"] is True

    listing = staff.get("/api/v1/campaigns", params={"status": "approved"}).json()
    listed = next(item for item in listing["items"] if item["id"] == campaign["id"])
    assert "can_submit" not in listed
    assert "can_approve" not in listed
    assert "can_cancel" not in listed


def test_campaign_csrf_and_rbac(
    client: TestClient,
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    assert client.get("/api/v1/campaigns").status_code == 401

    admin, admin_csrf = admin_client
    import_data = _two_recipient_import()
    template = create_template(admin, admin_csrf)

    staff, staff_csrf = staff_client
    no_csrf = staff.post(
        "/api/v1/campaigns",
        json={"name": "بلا حماية", "source_import_id": import_data["batch_id"]},
    )
    assert no_csrf.status_code == 403
    assert no_csrf.json()["error"]["code"] == "CSRF_INVALID"

    campaign = create_campaign(
        staff,
        staff_csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    assert staff.get("/api/v1/campaigns").status_code == 200
    assert staff.get(f"/api/v1/campaigns/{campaign['id']}").status_code == 200
    assert (
        staff.get(f"/api/v1/campaigns/{campaign['id']}/preview").status_code == 200
    )
    submitted = staff.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200
    forbidden = staff.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    approved = admin.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": admin_csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert approved.status_code == 200

    draft_again = create_campaign(
        staff,
        staff_csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    cancelled = staff.post(
        f"/api/v1/campaigns/{draft_again['id']}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0},
    )
    assert cancelled.status_code == 200


def test_cancel_preserves_terminal_message_and_job_outcomes() -> None:
    created = create_campaign_messages(
        [
            {"message_status": "pending", "job_status": "pending"},
            {
                "message_status": "submitting",
                "job_status": "claimed",
                "attempt_count": 1,
                "locked_by": "active-worker",
                "claim_token": "live-token",
            },
            {"message_status": "provider_accepted", "job_status": "completed"},
            {"message_status": "queued_by_provider", "job_status": "completed"},
            {"message_status": "delivered", "job_status": "completed"},
            {"message_status": "failed", "job_status": "failed"},
            {"message_status": "unknown", "job_status": "unknown"},
        ]
    )
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == "admin_test"))
        assert user is not None
        campaign_service.cancel_campaign(
            db,
            created["campaign_id"],
            request=None,
            user=user,
            reason="إيقاف الحملة",
            expected_revision=0,
        )

    expected_after = {
        0: ("cancelled", "cancelled"),
        1: ("cancelled", "cancelled"),
        2: ("provider_accepted", "completed"),
        3: ("queued_by_provider", "completed"),
        4: ("delivered", "completed"),
        5: ("failed", "failed"),
        6: ("unknown", "unknown"),
    }
    with SessionLocal() as db:
        messages = list(
            db.scalars(
                select(Message)
                .where(Message.campaign_id == created["campaign_id"])
                .order_by(Message.created_at)
            ).all()
        )
        jobs = {
            job.message_id: job
            for job in db.scalars(
                select(SendJob).where(
                    SendJob.message_id.in_(created["message_ids"])
                )
            ).all()
        }
        event = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.action == "campaign.cancel",
                AuditEvent.entity_id == created["campaign_id"],
            )
            .order_by(AuditEvent.created_at.desc())
        )
    by_message = {message.id: message for message in messages}
    for index, (message_status, job_status) in expected_after.items():
        message_id = created["message_ids"][index]
        assert by_message[message_id].internal_status == message_status
        assert jobs[message_id].status == job_status
    assert event is not None
    assert event.after_data is not None
    assert event.after_data["messages_cancelled"] == 2
    assert event.after_data["messages_retained"] == 5


def test_cancel_route_requires_edit_permission_not_view(
    client: TestClient, monkeypatch, staff_client: tuple[TestClient, str]
) -> None:
    from app import security
    from app.security import hash_password

    monkeypatch.setitem(
        security.ROLE_PERMISSIONS, "viewer", {"campaigns.view"}
    )
    with SessionLocal() as db:
        db.add(
            User(
                username="viewer_cancel_test",
                password_hash=hash_password("ViewerTest!2026"),
                role="viewer",
                is_active=True,
                must_change_password=False,
            )
        )
        db.commit()

    created = create_campaign_messages(campaign_status="draft")
    viewer_csrf = login(client, "viewer_cancel_test", "ViewerTest!2026")
    denied = client.post(
        f"/api/v1/campaigns/{created['campaign_id']}/cancel",
        headers={"X-CSRF-Token": viewer_csrf},
        json={"expected_revision": 0},
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"

    staff, staff_csrf = staff_client
    allowed = staff.post(
        f"/api/v1/campaigns/{created['campaign_id']}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": 0},
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["status"] == "cancelled"
