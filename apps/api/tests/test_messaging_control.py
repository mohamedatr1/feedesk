from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.config import settings
from app.db import SessionLocal
from app.messaging.rasel import RaselProvider
from app.models import AuditEvent, Message, ProviderCredential, SendJob, User

ALLOWED_RECIPIENT = "+963993000701"
MESSAGE_BODY = "رسالة اختبار تجريبية خاصة 123"


@pytest.fixture(autouse=True)
def messaging_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    with SessionLocal() as db:
        db.execute(delete(ProviderCredential))
        db.commit()
    monkeypatch.setattr(settings, "messaging_provider", "fake")
    monkeypatch.setattr(settings, "fake_provider_scenario", "delivered")
    monkeypatch.setattr(settings, "messaging_allowlist", ALLOWED_RECIPIENT)
    monkeypatch.setattr(
        settings, "provider_credential_key", Fernet.generate_key().decode()
    )
    monkeypatch.setattr(settings, "rasel_api_key", "")
    monkeypatch.setattr(settings, "rasel_sender_id", "")
    # Other tests in this module must not trip the throttle; the dedicated
    # throttle test lowers the limit explicitly.
    monkeypatch.setattr(settings, "messaging_test_send_limit", 1000)
    monkeypatch.setattr(settings, "messaging_test_send_window_seconds", 60)
    yield
    with SessionLocal() as db:
        db.execute(delete(ProviderCredential))
        db.commit()


def _send(client: TestClient, csrf: str, **overrides):
    payload = {"recipient": ALLOWED_RECIPIENT, "message": MESSAGE_BODY}
    payload.update(overrides)
    return client.post(
        "/api/v1/messaging/test-send",
        headers={"X-CSRF-Token": csrf},
        json=payload,
    )


def _count(model) -> int:
    with SessionLocal() as db:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)


def test_fake_allowlisted_test_send_succeeds_without_message_rows(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    before_messages = _count(Message)
    before_jobs = _count(SendJob)

    response = _send(client, csrf)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "fake"
    assert body["dry_run"] is True
    assert body["outcome"] == "delivered"
    assert body["provider_status"] == "delivered"
    assert body["error_code"] is None
    assert body["provider_message_id"].startswith("fake-msg-")
    assert body["recipient_masked"] != ALLOWED_RECIPIENT
    assert ALLOWED_RECIPIENT not in response.text
    assert body["sent_at"] is not None

    assert _count(Message) == before_messages
    assert _count(SendJob) == before_jobs

    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent)
            .where(AuditEvent.action == "messaging.test_send")
            .order_by(AuditEvent.created_at.desc())
            .limit(1)
        )
    assert event is not None
    assert event.after_data is not None
    assert event.after_data["recipient_masked"] == body["recipient_masked"]
    assert event.after_data["outcome"] == "delivered"
    assert event.after_data["dry_run"] is True
    payload = json.dumps(event.after_data, ensure_ascii=False)
    assert ALLOWED_RECIPIENT not in payload
    assert MESSAGE_BODY not in payload


def test_fake_provider_credential_status_reflects_vault(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client

    initial = client.get("/api/v1/messaging/provider")
    assert initial.status_code == 200, initial.text
    initial_body = initial.json()
    assert initial_body["provider"] == "fake"
    assert initial_body["configured"] is False
    assert initial_body["credential_error"] is None
    assert initial_body["test_send_mode"] == "fake"

    rotated = client.put(
        "/api/v1/messaging/provider/credential",
        headers={"X-CSRF-Token": csrf},
        json={"api_key": "fake-mode-key", "sender_id": "FEEDESK", "channel": "local_sms"},
    )
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["configured"] is True
    assert rotated.json()["credential_source"] == "database"
    assert rotated.json()["credential_error"] is None
    assert rotated.json()["test_send_mode"] == "fake"

    revoked = client.post(
        "/api/v1/messaging/provider/revoke", headers={"X-CSRF-Token": csrf}
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["configured"] is False
    assert revoked.json()["credential_source"] == "database"
    assert revoked.json()["credential_error"] is None
    assert revoked.json()["test_send_mode"] == "fake"


def test_non_allowlisted_recipient_is_rejected(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client
    monkeypatch.setattr(settings, "messaging_allowlist", "+963993000799")

    response = _send(client, csrf)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "RECIPIENT_NOT_ALLOWLISTED"


def test_invalid_phone_is_rejected(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client

    response = _send(client, csrf, recipient="not-a-phone")
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "INVALID_PHONE"


def test_empty_allowlist_is_rejected(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client
    monkeypatch.setattr(settings, "messaging_allowlist", "")

    response = _send(client, csrf)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "ALLOWLIST_REQUIRED"


def test_non_fake_provider_is_blocked_and_makes_no_network_call(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client
    monkeypatch.setattr(settings, "messaging_provider", "rasel")

    def _no_network(*_: object, **__: object) -> None:
        raise AssertionError("provider network call attempted")

    monkeypatch.setattr(RaselProvider, "send", _no_network)
    monkeypatch.setattr(RaselProvider, "get_balance", _no_network)
    monkeypatch.setattr(RaselProvider, "health", _no_network)

    response = _send(client, csrf)
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "LIVE_TEST_SEND_BLOCKED"


def test_balance_preflight_fake_and_blocked(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = admin_client

    fake = client.get("/api/v1/messaging/balance")
    assert fake.status_code == 200, fake.text
    assert fake.json() == {
        "provider": "fake",
        "available": True,
        "balance": "unlimited",
        "currency": "SMS",
        "preflight": True,
        "reason": None,
    }

    def _no_network(*_: object, **__: object) -> None:
        raise AssertionError("provider network call attempted")

    monkeypatch.setattr(RaselProvider, "get_balance", _no_network)
    monkeypatch.setattr(settings, "messaging_provider", "rasel")
    blocked = client.get("/api/v1/messaging/balance")
    assert blocked.status_code == 200, blocked.text
    assert blocked.json() == {
        "provider": "rasel",
        "available": False,
        "balance": None,
        "currency": None,
        "preflight": True,
        "reason": "live_provider_blocked",
    }


def test_test_send_is_throttled_per_actor(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client
    window = 3600
    monkeypatch.setattr(settings, "messaging_test_send_window_seconds", window)
    since = datetime.now(timezone.utc) - timedelta(seconds=window)
    with SessionLocal() as db:
        actor_id = db.scalar(select(User.id).where(User.username == "admin_test"))
        existing = int(
            db.scalar(
                select(func.count())
                .select_from(AuditEvent)
                .where(
                    AuditEvent.action == "messaging.test_send",
                    AuditEvent.actor_user_id == actor_id,
                    AuditEvent.created_at >= since,
                )
            )
            or 0
        )
    # Two additional sends are allowed for this actor's current window.
    monkeypatch.setattr(settings, "messaging_test_send_limit", existing + 2)

    assert _send(client, csrf).status_code == 200
    assert _send(client, csrf).status_code == 200

    limited = _send(client, csrf)
    assert limited.status_code == 429, limited.text
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert ALLOWED_RECIPIENT not in limited.text


def test_staff_is_denied_all_messaging_control_routes(
    staff_client: tuple[TestClient, str],
) -> None:
    client, csrf = staff_client

    assert client.get("/api/v1/messaging/provider").status_code == 403
    assert client.get("/api/v1/messaging/balance").status_code == 403
    assert (
        client.put(
            "/api/v1/messaging/provider/credential",
            headers={"X-CSRF-Token": csrf},
            json={
                "api_key": "staff-key",
                "sender_id": "FEEDESK",
                "channel": "local_sms",
            },
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/messaging/provider/revoke",
            headers={"X-CSRF-Token": csrf},
        ).status_code
        == 403
    )
    assert _send(client, csrf).status_code == 403


def test_test_send_requires_csrf(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client

    response = client.post(
        "/api/v1/messaging/test-send",
        json={"recipient": ALLOWED_RECIPIENT, "message": MESSAGE_BODY},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
