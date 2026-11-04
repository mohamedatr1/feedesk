from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AuditEvent, User
from app.security import hash_password

from .conftest import SessionLocal, login


def _create_user(username: str, *, role: str = "staff") -> str:
    with SessionLocal() as db:
        user = User(
            username=username,
            password_hash=hash_password("TargetUser!2026"),
            role=role,
            job_title="موظف",
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id


def _current_user_id(client: TestClient) -> str:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    return response.json()["user"]["id"]


def test_create_user_rejects_case_insensitive_duplicate(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    _create_user("CaseTest")
    response = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={
            "username": "casetest",
            "password": "DuplicateCase!2026",
            "role": "staff",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "USERNAME_EXISTS"


def test_admin_can_update_role_job_title_and_email_with_audit(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    user_id = _create_user("update_target")
    admin_id = _current_user_id(client)

    response = client.patch(
        f"/api/v1/users/{user_id}",
        headers={"X-CSRF-Token": csrf},
        json={
            "role": "admin",
            "job_title": "مدير مالي",
            "email": "updated@example.com",
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["role"] == "admin"
    assert body["job_title"] == "مدير مالي"
    assert body["email"] == "updated@example.com"

    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.action == "user.update",
                AuditEvent.entity_id == user_id,
            )
            .order_by(AuditEvent.created_at.desc())
        )
        assert event is not None
        assert event.actor_user_id == admin_id
        assert event.before_data is not None
        assert event.after_data is not None
        assert event.before_data["role"] == "staff"
        assert event.before_data["job_title"] == "موظف"
        assert event.after_data["role"] == "admin"
        assert event.after_data["job_title"] == "مدير مالي"
        assert event.after_data["email"] == "updated@example.com"
        assert "password_hash" not in event.before_data
        assert "password_hash" not in event.after_data


def test_admin_cannot_deactivate_self(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client
    admin_id = _current_user_id(client)

    response = client.patch(
        f"/api/v1/users/{admin_id}",
        headers={"X-CSRF-Token": csrf},
        json={"is_active": False},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SELF_DEACTIVATE"
    with SessionLocal() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        assert admin.is_active is True


def test_admin_cannot_demote_self(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client
    admin_id = _current_user_id(client)

    response = client.patch(
        f"/api/v1/users/{admin_id}",
        headers={"X-CSRF-Token": csrf},
        json={"role": "staff"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "SELF_DEMOTE"
    with SessionLocal() as db:
        admin = db.get(User, admin_id)
        assert admin is not None
        assert admin.role == "admin"


def test_create_user_requires_csrf(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client

    response = client.post(
        "/api/v1/users",
        json={
            "username": "csrf_missing_user",
            "password": "CsrfMissing!2026",
            "role": "staff",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.username == "csrf_missing_user")) is None


def test_update_user_requires_csrf(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client
    user_id = _create_user("csrf_update_target")

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={"job_title": "بدون رمز"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.job_title == "موظف"


def test_update_user_rejects_null_role(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client
    user_id = _create_user("null_role_target")

    response = client.patch(
        f"/api/v1/users/{user_id}",
        headers={"X-CSRF-Token": csrf},
        json={"role": None},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_reset_password_requires_csrf(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client
    user_id = _create_user("csrf_reset_target")

    response = client.post(f"/api/v1/users/{user_id}/reset-password")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"


def test_password_reset_clears_lockout(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client
    user_id = _create_user("reset_lockout_target")
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        user.failed_login_count = 5
        user.locked_until = now + timedelta(minutes=10)
        user.last_failed_login_at = now
        db.commit()

    response = client.post(
        f"/api/v1/users/{user_id}/reset-password",
        headers={"X-CSRF-Token": csrf},
    )

    assert response.status_code == 200, response.text
    temporary_password = response.json()["temporary_password"]
    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.failed_login_count == 0
        assert user.locked_until is None
        assert user.last_failed_login_at is None

    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": "reset_lockout_target", "password": temporary_password},
    )
    assert login_response.status_code == 200, login_response.text


def test_last_active_admin_cannot_be_demoted(client: TestClient) -> None:
    target_id = _create_user("last_admin_target", role="admin")
    try:
        with SessionLocal() as db:
            for admin in db.scalars(select(User).where(User.role == "admin")):
                if admin.id != target_id:
                    admin.is_active = False
            db.commit()

        csrf = login(client, "last_admin_target", "TargetUser!2026")
        response = client.patch(
            f"/api/v1/users/{target_id}",
            headers={"X-CSRF-Token": csrf},
            json={"role": "staff"},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "LAST_ADMIN"
        with SessionLocal() as db:
            target = db.get(User, target_id)
            assert target is not None
            assert target.role == "admin"
    finally:
        with SessionLocal() as db:
            for admin in db.scalars(select(User).where(User.role == "admin")):
                admin.is_active = True
            db.commit()
