from __future__ import annotations

from fastapi.testclient import TestClient

from .conftest import login


def test_login_me_and_logout(client: TestClient) -> None:
    csrf = login(client, "admin_test", "AdminTest!2026")

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    body = me.json()
    assert body["user"]["username"] == "admin_test"
    assert body["user"]["role"] == "admin"
    assert body["csrf_token"] == csrf

    logout = client.post("/api/v1/auth/logout", headers={"X-CSRF-Token": csrf})
    assert logout.status_code == 200

    after = client.get("/api/v1/auth/me")
    assert after.status_code == 401


def test_logout_requires_csrf(client: TestClient) -> None:
    login(client, "admin_test", "AdminTest!2026")
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"


def test_login_is_case_insensitive(client: TestClient) -> None:
    login(client, "ADMIN_TEST", "AdminTest!2026")
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["username"] == "admin_test"


def test_invalid_password_returns_generic_error(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin_test", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_password_change_is_required_and_unlocks_protected_work(client: TestClient) -> None:
    csrf = login(client, "must_change_test", "MustChange!2026")

    blocked = client.get("/api/v1/settings")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    changed = client.post(
        "/api/v1/auth/change-password",
        headers={"X-CSRF-Token": csrf},
        json={
            "current_password": "MustChange!2026",
            "new_password": "MustChange!2026-New",
        },
    )
    assert changed.status_code == 200, changed.text
    assert client.get("/api/v1/settings").status_code == 200
