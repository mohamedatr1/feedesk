from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.main import app
from app.models import User
from app.security import hash_password

from .campaign_helpers import clean_campaign_tables
from .conftest import login
from .messaging_helpers import create_campaign_messages, utcnow


@pytest.fixture(autouse=True)
def campaign_environment() -> None:
    clean_campaign_tables()
    yield
    clean_campaign_tables()


def _fixture():
    now = utcnow()
    return create_campaign_messages(
        [
            {
                "guardian_name": "ولي أمر أحمد",
                "phone": "+963993000701",
                "amount": "600000",
                "currency": "SYP",
                "message_status": "delivered",
                "job_status": "completed",
                "attempt_count": 1,
                "provider_status": "delivered",
                "provider_request_id": "req-1",
                "provider_message_id": "msg-1",
                "submitted_at": now,
                "delivered_at": now,
                "created_at": now - timedelta(hours=1),
                "payload": {"provider": "fake", "status": "delivered"},
            },
            {
                "guardian_name": "ولي أمر سارة",
                "phone": "+963993000702",
                "amount": "400.50",
                "currency": "USD",
                "message_status": "failed",
                "job_status": "failed",
                "attempt_count": 2,
                "next_attempt_at": utcnow(),
                "last_error_code": "INVALID_RECIPIENT",
                "last_error_summary": "Provider rejected the recipient.",
                "created_at": now,
            },
        ]
    )


def test_message_list_filters_search_and_pager(
    staff_client: tuple[TestClient, str],
) -> None:
    data = _fixture()
    client, _ = staff_client

    response = client.get("/api/v1/messages")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["page_size"] == 20
    assert len(body["items"]) == 2
    first = body["items"][0]
    assert set(first) == {
        "id",
        "campaign_id",
        "campaign_name",
        "guardian_name",
        "destination_phone_masked",
        "amount",
        "currency",
        "channel",
        "internal_status",
        "provider_status",
        "provider_message_id",
        "last_error_code",
        "last_error_summary",
        "submitted_at",
        "delivered_at",
        "next_attempt_at",
        "created_at",
        "updated_at",
    }
    amounts = {item["guardian_name"]: item["amount"] for item in body["items"]}
    assert amounts["ولي أمر أحمد"] == "600000.00"
    assert amounts["ولي أمر سارة"] == "400.50"
    assert body["items"][0]["guardian_name"] == "ولي أمر سارة"
    assert body["items"][1]["guardian_name"] == "ولي أمر أحمد"
    masked_by_name = {
        item["guardian_name"]: item["destination_phone_masked"]
        for item in body["items"]
    }
    assert masked_by_name["ولي أمر أحمد"] == "+963 9•• ••• 701"
    assert masked_by_name["ولي أمر سارة"] == "+963 9•• ••• 702"
    assert "+963993000701" not in response.text
    assert "+963993000702" not in response.text
    assert "destination_phone" not in first

    by_campaign = client.get(
        "/api/v1/messages", params={"campaign_id": data["campaign_id"]}
    )
    assert by_campaign.status_code == 200
    assert by_campaign.json()["total"] == 2

    by_status = client.get("/api/v1/messages", params={"status": "failed"})
    assert by_status.status_code == 200
    assert by_status.json()["total"] == 1
    assert by_status.json()["items"][0]["last_error_code"] == "INVALID_RECIPIENT"

    by_name = client.get("/api/v1/messages", params={"q": "أحمد"})
    assert by_name.status_code == 200
    assert by_name.json()["total"] == 1

    by_phone = client.get("/api/v1/messages", params={"q": "000702"})
    assert by_phone.status_code == 200
    assert by_phone.json()["total"] == 1

    paged = client.get("/api/v1/messages", params={"page": 2, "page_size": 1})
    assert paged.status_code == 200
    assert paged.json()["total"] == 2
    assert len(paged.json()["items"]) == 1


def test_list_and_detail_expose_scheduled_retry_timestamp(
    staff_client: tuple[TestClient, str],
) -> None:
    retry_at = utcnow() + timedelta(minutes=2)
    data = create_campaign_messages(
        [
            {
                "message_status": "pending",
                "job_status": "retry",
                "attempt_count": 1,
                "next_attempt_at": retry_at,
            }
        ]
    )
    client, _ = staff_client

    listed = client.get("/api/v1/messages").json()["items"][0]
    assert listed["next_attempt_at"] is not None

    detail = client.get(f"/api/v1/messages/{data['message_ids'][0]}").json()
    assert detail["next_attempt_at"] is not None
    assert detail["attempt_count"] == 1


def test_message_detail_includes_frozen_body_and_redacted_payload(
    admin_client: tuple[TestClient, str],
) -> None:
    data = _fixture()
    client, _ = admin_client

    response = client.get(f"/api/v1/messages/{data['message_ids'][0]}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["message_body_snapshot"]
    assert body["provider_request_id"] == "req-1"
    assert body["provider_message_id"] == "msg-1"
    assert body["provider_payload_redacted"] == {"provider": "fake", "status": "delivered"}
    assert body["attempt_count"] == 1
    assert body["internal_status"] == "delivered"
    assert body["destination_phone"] == "+963993000701"
    assert body["destination_phone_masked"] == "+963 9•• ••• 701"
    assert "idempotency_key" not in body

    missing = client.get("/api/v1/messages/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "MESSAGE_NOT_FOUND"


def test_phone_masking_helper_preserves_country_code_and_edges() -> None:
    from app.messaging.queries import mask_phone

    assert mask_phone("+963993000701") == "+963 9•• ••• 701"
    assert mask_phone("+963900000005") == "+963 9•• ••• 005"
    assert mask_phone("0990000005") == "+963 9•• ••• 005"
    assert mask_phone(None) is None


def test_message_list_rejects_invalid_status(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    response = client.get("/api/v1/messages", params={"status": "sent-ish"})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_campaign_results_counts_states(
    staff_client: tuple[TestClient, str],
) -> None:
    data = _fixture()
    client, _ = staff_client

    response = client.get(f"/api/v1/campaigns/{data['campaign_id']}/results")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == data["campaign_id"]
    assert body["message_count"] == 2
    assert body["counts"] == {
        "pending": 0,
        "submitting": 0,
        "provider_accepted": 0,
        "queued_by_provider": 0,
        "delivered": 1,
        "failed": 1,
        "unknown": 0,
        "cancelled": 0,
    }
    assert body["last_activity_at"] is not None
    assert "قبول المزوّد لا يعني التسليم" in body["delivery_note_ar"]

    missing = client.get("/api/v1/campaigns/does-not-exist/results")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "CAMPAIGN_NOT_FOUND"


def test_message_endpoints_require_permissions() -> None:
    data = _fixture()
    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/messages").status_code == 401
    assert (
        anonymous.get(f"/api/v1/messages/{data['message_ids'][0]}").status_code == 401
    )
    assert (
        anonymous.get(f"/api/v1/campaigns/{data['campaign_id']}/results").status_code
        == 401
    )

    username = f"auditor_{uuid4().hex[:8]}"
    with SessionLocal() as db:
        db.add(
            User(
                id=str(uuid4()),
                username=username,
                password_hash=hash_password("Auditor!2026"),
                role="auditor",
                is_active=True,
                must_change_password=False,
            )
        )
        db.commit()

    limited = TestClient(app)
    login(limited, username, "Auditor!2026")
    assert limited.get("/api/v1/messages").status_code == 403
    assert (
        limited.get(f"/api/v1/messages/{data['message_ids'][0]}").status_code == 403
    )
    assert (
        limited.get(f"/api/v1/campaigns/{data['campaign_id']}/results").status_code
        == 403
    )


def test_no_send_or_resend_endpoint_exists(
    admin_client: tuple[TestClient, str],
) -> None:
    data = _fixture()
    client, csrf = admin_client
    response = client.post(
        f"/api/v1/messages/{data['message_ids'][0]}/send",
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code in {404, 405}
    campaign_send = client.post(
        f"/api/v1/campaigns/{data['campaign_id']}/send",
        headers={"X-CSRF-Token": csrf},
    )
    assert campaign_send.status_code in {404, 405}
