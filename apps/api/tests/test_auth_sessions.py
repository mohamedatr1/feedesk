from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.models import AuditEvent, User, UserSession
from app.security import hash_password, hash_token

from .conftest import SessionLocal, login


def _add_user(username: str, password: str, *, is_active: bool = True) -> str:
    with SessionLocal() as db:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role="staff",
            is_active=is_active,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def _update_current_session(token: str, **values: Any) -> None:
    with SessionLocal() as db:
        session = db.scalar(
            select(UserSession).where(UserSession.token_hash == hash_token(token))
        )
        assert session is not None
        for key, value in values.items():
            setattr(session, key, value)
        db.commit()


def test_inactive_user_cannot_log_in(client: TestClient) -> None:
    _add_user("inactive_login", "Inactive!2026", is_active=False)

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "inactive_login", "password": "Inactive!2026"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_deactivating_user_invalidates_existing_session(client: TestClient) -> None:
    user_id = _add_user("deactivated_session", "Deactivated!2026")
    login(client, "deactivated_session", "Deactivated!2026")

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.is_active = False
        db.commit()

    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_expired_session_is_rejected(client: TestClient) -> None:
    login(client, "staff_test", "StaffTest!2026")
    token = client.cookies.get(settings.cookie_name)
    assert token
    _update_current_session(
        token, expires_at=datetime.now(timezone.utc) - timedelta(minutes=1)
    )

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_revoked_session_is_rejected(client: TestClient) -> None:
    login(client, "staff_test", "StaffTest!2026")
    token = client.cookies.get(settings.cookie_name)
    assert token
    _update_current_session(token, revoked_at=datetime.now(timezone.utc))

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_failed_logins_lock_account_and_are_audited(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "login_rate_limit", 100)
    monkeypatch.setattr(settings, "login_lockout_threshold", 3)
    user_id = _add_user("lockout_target", "Lockout!2026")

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "lockout_target", "password": "wrong-password"},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"

    locked = client.post(
        "/api/v1/auth/login",
        json={"username": "lockout_target", "password": "wrong-password"},
    )
    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "ACCOUNT_LOCKED"

    correct_password = client.post(
        "/api/v1/auth/login",
        json={"username": "lockout_target", "password": "Lockout!2026"},
    )
    assert correct_password.status_code == 429
    assert correct_password.json()["error"]["code"] == "ACCOUNT_LOCKED"

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.failed_login_count == 3
        assert user.locked_until is not None
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.action == "auth.login_failed",
                    AuditEvent.entity_id == user_id,
                )
            )
        )
        assert len(events) == 3
        for event in events:
            assert event.after_data is not None
            assert "password" not in event.after_data
            assert event.after_data["username"] == "lockout_target"


def test_expired_lockout_allows_login_and_resets_counter(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "login_lockout_threshold", 2)
    user_id = _add_user("lockout_expiry", "LockoutExpiry!2026")

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "lockout_expiry", "password": "wrong-password"},
        )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "ACCOUNT_LOCKED"

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/api/v1/auth/login",
        json={"username": "lockout_expiry", "password": "LockoutExpiry!2026"},
    )
    assert response.status_code == 200, response.text

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.failed_login_count == 0
        assert user.locked_until is None


def test_ip_rate_limit_is_db_backed(client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(settings, "login_rate_limit", 2)
    monkeypatch.setattr(settings, "trust_forwarded_for", True)
    headers = {
        "X-Forwarded-For": "198.51.100.77",
        "X-Request-ID": "rate-limit-check",
    }

    for _ in range(2):
        response = client.post(
            "/api/v1/auth/login",
            headers=headers,
            json={"username": "no_such_user", "password": "whatever"},
        )
        assert response.status_code == 401

    response = client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={"username": "no_such_user", "password": "whatever"},
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"


def test_logout_deletes_cookie_with_matching_security_flags(
    client: TestClient, monkeypatch
) -> None:
    csrf = login(client, "staff_test", "StaffTest!2026")
    monkeypatch.setattr(settings, "cookie_secure", True)

    response = client.post(
        "/api/v1/auth/logout", headers={"X-CSRF-Token": csrf}
    )

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie")
    assert set_cookie is not None
    assert set_cookie.startswith(f"{settings.cookie_name}=")
    assert "Path=/" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie


def test_api_responses_are_not_cacheable(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["pragma"] == "no-cache"


def test_unknown_username_failure_is_audited(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={"X-Request-ID": "unknown-user-audit"},
        json={"username": "no_such_audit_user", "password": "whatever"},
    )
    assert response.status_code == 401

    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.request_id == "unknown-user-audit")
        )
    assert event is not None
    assert event.action == "auth.login_failed"
    assert event.entity_type == "auth"
    assert event.after_data is not None
    assert event.after_data["username"] == "no_such_audit_user"
