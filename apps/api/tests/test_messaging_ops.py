from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from app.db import SessionLocal
from app.main import app
from app.models import AuditEvent, ProviderCredential, ProviderEvent

from .campaign_helpers import clean_campaign_tables
from .messaging_helpers import DEFAULT_BODY, create_campaign_messages, utcnow

OPS_PREFIX = "/api/v1/messaging/ops"


@pytest.fixture(autouse=True)
def ops_environment() -> None:
    clean_campaign_tables()
    _clear_ops_tables()
    yield
    clean_campaign_tables()
    _clear_ops_tables()


def _clear_ops_tables() -> None:
    with SessionLocal() as db:
        db.execute(delete(ProviderEvent))
        db.execute(delete(ProviderCredential))
        db.commit()


def _summary(client: TestClient) -> dict:
    response = client.get(f"{OPS_PREFIX}/summary")
    assert response.status_code == 200, response.text
    return response.json()


def test_summary_reports_queue_message_campaign_and_event_counts(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    create_campaign_messages(
        [
            {
                "job_status": "pending",
                "message_status": "pending",
                "next_attempt_at": utcnow() - timedelta(seconds=5),
            },
            {
                "job_status": "retry",
                "message_status": "pending",
                "attempt_count": 1,
                "next_attempt_at": utcnow() - timedelta(seconds=1),
            },
            {
                "job_status": "claimed",
                "message_status": "submitting",
                "locked_by": "dead-worker",
                "lease_expires_at": utcnow() - timedelta(seconds=1),
            },
            {
                "job_status": "unknown",
                "message_status": "unknown",
                "last_error_code": "TIMEOUT",
            },
            {
                "job_status": "failed",
                "message_status": "failed",
                "last_error_code": "FAKE_FAILED",
            },
        ]
    )
    with SessionLocal() as db:
        db.add(
            ProviderEvent(
                provider="rasel",
                provider_event_id="evt-summary-1",
                provider_message_id="provider-msg-1",
                event_type="delivered",
                event_payload_redacted={"provider": "rasel"},
            )
        )
        db.commit()

    body = _summary(client)

    assert body["generated_at"] is not None
    assert body["provider"]["name"] == "fake"
    assert body["provider"]["credential_source"] in {"none", "environment", "database"}

    queue = body["queue"]
    assert queue["by_job_status"] == {
        "pending": 1,
        "retry": 1,
        "claimed": 1,
        "unknown": 1,
        "failed": 1,
    }
    assert queue["pending"] == 1
    assert queue["claimed"] == 1
    assert queue["retry"] == 1
    assert queue["due_now"] == 2
    assert queue["stale_claims"] == 1
    assert queue["oldest_pending_at"] is not None
    assert queue["next_attempt_at"] is not None

    messages = body["messages"]
    assert messages["total"] == 5
    assert messages["failed"] == 1
    assert messages["unknown"] == 1
    assert messages["reconciliation_required"] == 1
    assert messages["by_status"]["pending"] == 2
    assert messages["by_status"]["submitting"] == 1
    assert messages["by_status"]["delivered"] == 0

    assert body["campaigns"]["by_status"] == {"approved": 1}
    assert body["campaigns"]["sending"] == 0

    assert body["provider_events"]["unprocessed"] == 1
    assert body["provider_events"]["last_received_at"] is not None


def test_jobs_list_filters_and_paginates_without_pii(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    full_phone = "+963993000111"
    campaign_a = create_campaign_messages(
        [
            {
                "job_status": "pending",
                "message_status": "pending",
                "next_attempt_at": utcnow() - timedelta(seconds=5),
                "phone": full_phone,
                "body": DEFAULT_BODY,
            },
            {
                "job_status": "retry",
                "message_status": "pending",
                "attempt_count": 1,
                "next_attempt_at": utcnow() + timedelta(hours=1),
            },
            {
                "job_status": "completed",
                "message_status": "delivered",
            },
            {
                "job_status": "claimed",
                "message_status": "submitting",
                "locked_by": "dead-worker",
                "claim_token": "secret-claim-token",
                "lease_expires_at": utcnow() - timedelta(minutes=1),
            },
        ]
    )
    create_campaign_messages(
        [{"job_status": "pending", "message_status": "pending"}]
    )

    page_one = client.get(f"{OPS_PREFIX}/jobs", params={"page_size": 2, "page": 1})
    assert page_one.status_code == 200, page_one.text
    first = page_one.json()
    assert first["total"] == 5
    assert first["page"] == 1
    assert first["page_size"] == 2
    assert len(first["items"]) == 2

    page_three = client.get(f"{OPS_PREFIX}/jobs", params={"page_size": 2, "page": 3})
    assert page_three.status_code == 200, page_three.text
    assert len(page_three.json()["items"]) == 1

    by_campaign = client.get(
        f"{OPS_PREFIX}/jobs", params={"campaign_id": campaign_a["campaign_id"]}
    ).json()
    assert by_campaign["total"] == 4

    pending = client.get(f"{OPS_PREFIX}/jobs", params={"status": "pending"}).json()
    assert pending["total"] == 2
    assert {item["job_status"] for item in pending["items"]} == {"pending"}

    due = client.get(f"{OPS_PREFIX}/jobs", params={"due_only": "true"}).json()
    assert due["total"] == 2

    stale = client.get(f"{OPS_PREFIX}/jobs", params={"stale_only": "true"}).json()
    assert stale["total"] == 1
    assert stale["items"][0]["locked_by"] == "dead-worker"

    invalid = client.get(f"{OPS_PREFIX}/jobs", params={"status": "bogus"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    assert full_phone not in page_one.text
    assert DEFAULT_BODY not in page_one.text
    assert "secret-claim-token" not in page_one.text
    assert "claim_token" not in page_one.text

    item = first["items"][0]
    assert {
        "job_id",
        "message_id",
        "campaign_id",
        "campaign_name",
        "campaign_status",
        "message_status",
        "job_status",
        "attempt_count",
        "next_attempt_at",
        "lease_expires_at",
        "heartbeat_at",
        "locked_by",
        "last_error",
        "last_error_code",
        "last_error_summary",
        "guardian_name",
        "destination_phone_masked",
        "created_at",
        "updated_at",
    } <= set(item)


def test_issues_filters_unknown_and_failed_with_flags(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    unknown = create_campaign_messages(
        [
            {
                "message_status": "unknown",
                "job_status": "unknown",
                "attempt_count": 2,
                "last_error_code": "RECONCILIATION_REQUIRED",
            },
            {
                "message_status": "failed",
                "job_status": "failed",
                "attempt_count": 3,
                "last_error_code": "TEMPORARY_ERROR",
            },
            {
                "message_status": "failed",
                "job_status": "failed",
                "attempt_count": 1,
                "last_error_code": "FAKE_FAILED",
            },
            {"message_status": "delivered", "job_status": "completed"},
        ]
    )
    other = create_campaign_messages(
        [{"message_status": "unknown", "job_status": "unknown"}]
    )
    full_phone = "+963993000222"
    create_campaign_messages(
        [
            {
                "message_status": "unknown",
                "job_status": "unknown",
                "phone": full_phone,
                "body": DEFAULT_BODY,
            }
        ]
    )

    unknown_body = client.get(f"{OPS_PREFIX}/issues", params={"kind": "unknown"})
    assert unknown_body.status_code == 200, unknown_body.text
    unknown_payload = unknown_body.json()
    assert unknown_payload["total"] == 3
    assert len(unknown_payload["items"]) == 3
    single = client.get(
        f"{OPS_PREFIX}/issues",
        params={"kind": "unknown", "campaign_id": unknown["campaign_id"]},
    ).json()
    assert single["total"] == 1
    assert single["items"][0]["reconciliation_required"] is True
    assert single["items"][0]["retry_exhausted"] is False

    failed = client.get(
        f"{OPS_PREFIX}/issues",
        params={"kind": "failed", "campaign_id": unknown["campaign_id"]},
    ).json()
    assert failed["total"] == 2
    exhausted = [item for item in failed["items"] if item["retry_exhausted"]]
    assert len(exhausted) == 1
    assert exhausted[0]["attempt_count"] == 3
    assert failed["items"][0]["reconciliation_required"] is False

    assert other["campaign_id"] not in {
        item["campaign_id"] for item in single["items"]
    }
    assert full_phone not in unknown_body.text
    assert DEFAULT_BODY not in unknown_body.text

    invalid = client.get(f"{OPS_PREFIX}/issues", params={"kind": "other"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"


def test_message_detail_is_masked_and_has_no_claim_token_or_body(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    full_phone = "+963993000333"
    created = create_campaign_messages(
        [
            {
                "phone": full_phone,
                "body": "رسالة سرية لا يجب أن تظهر في لوحة العمليات",
                "message_status": "submitting",
                "job_status": "claimed",
                "claim_token": "secret-claim-token",
                "locked_by": "worker-x",
                "provider_message_id": "provider-msg-detail",
            }
        ]
    )
    message_id = created["message_ids"][0]
    with SessionLocal() as db:
        db.add(
            ProviderEvent(
                provider="rasel",
                provider_event_id="evt-detail-1",
                provider_message_id="provider-msg-detail",
                event_type="delivered",
                event_payload_redacted={"status": "delivered"},
            )
        )
        db.add(
            AuditEvent(
                action="message.provider_response",
                entity_type="message",
                entity_id=message_id,
                after_data={"secret": "must-not-leak"},
            )
        )
        db.commit()

    response = client.get(f"{OPS_PREFIX}/messages/{message_id}")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["id"] == message_id
    assert body["destination_phone_masked"] == "+963 9•• ••• 333"
    assert "destination_phone" not in body
    assert "message_body_snapshot" not in body
    assert full_phone not in response.text
    assert "رسالة سرية" not in response.text
    assert "secret-claim-token" not in response.text
    assert "claim_token" not in response.text
    assert "must-not-leak" not in response.text

    assert body["job"]["job_id"] is not None
    assert body["job"]["status"] == "claimed"
    assert "claim_token" not in body["job"]
    assert len(body["provider_events"]) == 1
    assert body["provider_events"][0]["event_type"] == "delivered"
    assert "message.provider_response" in {
        action["action"] for action in body["recent_audit_actions"]
    }

    missing = client.get(f"{OPS_PREFIX}/messages/{uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "MESSAGE_NOT_FOUND"


def test_ops_routes_are_admin_only(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    admin, _ = admin_client
    staff, _ = staff_client
    created = create_campaign_messages([{}])
    paths = [
        f"{OPS_PREFIX}/summary",
        f"{OPS_PREFIX}/jobs",
        f"{OPS_PREFIX}/issues",
        f"{OPS_PREFIX}/messages/{created['message_ids'][0]}",
    ]

    for path in paths:
        assert admin.get(path).status_code == 200
        assert staff.get(path).status_code == 403
        assert TestClient(app).get(path).status_code == 401


def test_ops_surface_is_get_only() -> None:
    paths = {
        path: set(operations)
        for path, operations in app.openapi()["paths"].items()
        if path.startswith(OPS_PREFIX)
    }
    assert paths
    assert all(methods == {"get"} for methods in paths.values())

    client = TestClient(app)
    for path in ("summary", "jobs", "issues"):
        response = client.post(f"{OPS_PREFIX}/{path}")
        assert response.status_code == 405, response.text
