from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.config import settings
from app.db import SessionLocal
from app.main import app
from app.messaging.credentials import (
    CredentialError,
    decrypt_api_key,
    encrypt_api_key,
    resolve_rasel_credentials,
)
from app.models import AuditEvent, ProviderCredential

PROVIDER_KEY = "rasel-test-key-do-not-use-123456"


@pytest.fixture(autouse=True)
def credential_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    _clear_credentials()
    monkeypatch.setattr(settings, "messaging_provider", "rasel")
    monkeypatch.setattr(
        settings, "provider_credential_key", Fernet.generate_key().decode()
    )
    monkeypatch.setattr(settings, "rasel_api_key", "")
    monkeypatch.setattr(settings, "rasel_sender_id", "")
    monkeypatch.setattr(settings, "rasel_channel", "local_sms")
    yield
    _clear_credentials()


def _clear_credentials() -> None:
    with SessionLocal() as db:
        db.execute(delete(ProviderCredential))
        db.commit()


def _row() -> ProviderCredential | None:
    with SessionLocal() as db:
        return db.scalar(
            select(ProviderCredential).where(
                ProviderCredential.provider == "rasel"
            )
        )


def _rotate(
    client: TestClient,
    csrf: str,
    *,
    api_key: str = PROVIDER_KEY,
    sender_id: str = "FEEDESK",
    channel: str = "local_sms",
):
    return client.put(
        "/api/v1/messaging/provider/credential",
        headers={"X-CSRF-Token": csrf},
        json={"api_key": api_key, "sender_id": sender_id, "channel": channel},
    )


def _status(client: TestClient):
    return client.get("/api/v1/messaging/provider")


def test_admin_rotates_and_reads_credential_status(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client

    response = _rotate(client, csrf)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["provider"] == "rasel"
    assert body["configured"] is True
    assert body["credential_source"] == "database"
    assert body["credential_error"] is None
    assert body["sender_id"] == "FEEDESK"
    assert body["channel"] == "local_sms"
    assert body["key_version"] == 1
    assert body["rotated_at"] is not None
    assert body["rotated_by_name"] == "admin_test"
    assert body["test_send_mode"] == "disabled"
    assert body["live_send_available"] is False
    assert "api_key" not in body
    assert PROVIDER_KEY not in response.text

    row = _row()
    assert row is not None
    assert row.api_key_ciphertext is not None
    assert row.api_key_ciphertext != PROVIDER_KEY
    assert PROVIDER_KEY not in row.api_key_ciphertext
    assert decrypt_api_key(row.api_key_ciphertext) == PROVIDER_KEY
    assert row.is_active is True


def test_rotation_increments_key_version(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client

    assert _rotate(client, csrf, api_key="first-key").json()["key_version"] == 1
    second = _rotate(client, csrf, api_key="second-key")
    assert second.status_code == 200, second.text
    assert second.json()["key_version"] == 2

    row = _row()
    assert row is not None
    assert row.key_version == 2
    assert decrypt_api_key(row.api_key_ciphertext) == "second-key"
    assert row.api_key_ciphertext != "second-key"


def test_revoke_clears_ciphertext_and_deactivates(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    _rotate(client, csrf)

    response = client.post(
        "/api/v1/messaging/provider/revoke", headers={"X-CSRF-Token": csrf}
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["configured"] is False
    assert body["credential_source"] == "database"
    assert body["key_version"] == 1
    assert body["live_send_available"] is False

    row = _row()
    assert row is not None
    assert row.api_key_ciphertext is None
    assert row.is_active is False


def test_get_never_returns_key_or_ciphertext(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    _rotate(client, csrf)

    response = _status(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {
        "provider",
        "configured",
        "credential_source",
        "credential_error",
        "sender_id",
        "channel",
        "key_version",
        "rotated_at",
        "rotated_by_name",
        "test_send_mode",
        "live_send_available",
    }
    assert PROVIDER_KEY not in response.text
    assert "ciphertext" not in response.text


def test_staff_and_anonymous_are_denied(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    _rotate(*admin_client)

    staff, staff_csrf = staff_client
    staff_status = staff.get("/api/v1/messaging/provider")
    assert staff_status.status_code == 403
    assert staff_status.json()["error"]["code"] == "FORBIDDEN"

    staff_put = _rotate(staff, staff_csrf, api_key="staff-key")
    assert staff_put.status_code == 403

    anonymous = TestClient(app)
    assert anonymous.get("/api/v1/messaging/provider").status_code == 401
    assert _rotate(anonymous, "csrf", api_key="anonymous-key").status_code == 401


def test_mutations_require_csrf(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client

    put = client.put(
        "/api/v1/messaging/provider/credential",
        json={"api_key": PROVIDER_KEY, "sender_id": "FEEDESK", "channel": "local_sms"},
    )
    assert put.status_code == 403
    assert put.json()["error"]["code"] == "CSRF_INVALID"

    revoke = client.post("/api/v1/messaging/provider/revoke")
    assert revoke.status_code == 403
    assert revoke.json()["error"]["code"] == "CSRF_INVALID"
    assert _row() is None


def test_missing_or_invalid_encryption_key_is_handled_safely(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client

    monkeypatch.setattr(settings, "provider_credential_key", "")
    with pytest.raises(CredentialError) as missing:
        encrypt_api_key(PROVIDER_KEY)
    assert PROVIDER_KEY not in str(missing.value)

    missing_response = _rotate(client, csrf)
    assert missing_response.status_code == 503
    assert missing_response.json()["error"]["code"] == "CREDENTIAL_KEY_UNAVAILABLE"
    assert PROVIDER_KEY not in missing_response.text

    monkeypatch.setattr(settings, "provider_credential_key", "not-a-fernet-key")
    with pytest.raises(CredentialError) as invalid:
        encrypt_api_key(PROVIDER_KEY)
    assert "not-a-fernet-key" not in str(invalid.value)
    assert PROVIDER_KEY not in str(invalid.value)

    invalid_response = _rotate(client, csrf)
    assert invalid_response.status_code == 503
    assert PROVIDER_KEY not in invalid_response.text

    monkeypatch.setattr(
        settings, "provider_credential_key", Fernet.generate_key().decode()
    )
    _rotate(client, csrf)
    monkeypatch.setattr(settings, "provider_credential_key", "")

    status = _status(client)
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["configured"] is False
    assert body["credential_error"]
    assert PROVIDER_KEY not in status.text
    with SessionLocal() as db:
        assert resolve_rasel_credentials(db) is None


def test_audit_contains_metadata_but_never_the_secret(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    _rotate(client, csrf, api_key="audit-secret-value")
    client.post(
        "/api/v1/messaging/provider/revoke", headers={"X-CSRF-Token": csrf}
    )

    with SessionLocal() as db:
        events = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action.in_(
                    ["messaging.credential.rotate", "messaging.credential.revoke"]
                )
            )
        ).all()
    assert events
    for event in events:
        payload = json.dumps(
            {"before": event.before_data, "after": event.after_data},
            ensure_ascii=False,
        )
        assert "audit-secret-value" not in payload
        assert "api_key" not in payload
        assert "ciphertext" not in payload
        assert set(event.after_data or {}) <= {
            "provider",
            "sender_id",
            "channel",
            "key_version",
            "active",
        }
    assert any(
        (event.after_data or {}).get("key_version") == 2 for event in events
    )


def test_database_row_takes_precedence_over_environment(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client
    monkeypatch.setattr(settings, "rasel_api_key", "environment-key")
    monkeypatch.setattr(settings, "rasel_sender_id", "ENV-SENDER")

    env_status = _status(client)
    assert env_status.status_code == 200, env_status.text
    env_body = env_status.json()
    assert env_body["credential_source"] == "environment"
    assert env_body["configured"] is True
    assert env_body["sender_id"] == "ENV-SENDER"
    assert env_body["key_version"] is None
    with SessionLocal() as db:
        resolved = resolve_rasel_credentials(db)
    assert resolved is not None
    assert resolved.api_key == "environment-key"
    assert resolved.sender_id == "ENV-SENDER"
    assert resolved.channel == "local_sms"

    _rotate(client, csrf, api_key="database-key", sender_id="DB-SENDER")
    with SessionLocal() as db:
        resolved = resolve_rasel_credentials(db)
    assert resolved is not None
    assert resolved.api_key == "database-key"
    assert resolved.sender_id == "DB-SENDER"

    db_status = _status(client).json()
    assert db_status["credential_source"] == "database"
    assert db_status["sender_id"] == "DB-SENDER"
    assert db_status["key_version"] == 1
