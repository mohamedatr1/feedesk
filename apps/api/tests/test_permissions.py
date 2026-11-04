from __future__ import annotations

from fastapi.testclient import TestClient


def test_admin_can_read_and_update_settings(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client
    before = client.get("/api/v1/settings")
    assert before.status_code == 200
    assert before.json()["school_name"] == "مدرسة الاختبار"

    response = client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf},
        json={"school_name": "مدرسة الروض", "currency_symbol": "د.س"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["school_name"] == "مدرسة الروض"
    assert body["default_currency"] == "SYP"


def test_staff_can_read_but_not_update_settings(staff_client: tuple[TestClient, str]) -> None:
    client, csrf = staff_client
    assert client.get("/api/v1/settings").status_code == 200

    response = client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf},
        json={"school_name": "غير مسموح"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_settings_update_requires_csrf(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client

    response = client.put(
        "/api/v1/settings",
        json={"school_name": "بدون رمز"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CSRF_INVALID"


def test_settings_rejects_invalid_currency(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client

    response = client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf},
        json={"default_currency": "12A"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_settings_rejects_invalid_timezone(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client

    response = client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf},
        json={"timezone": "Mars/Olympus"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_settings_rejects_null_required_value(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client

    response = client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf},
        json={"default_currency": None},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_settings_normalizes_valid_currency(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client

    response = client.put(
        "/api/v1/settings",
        headers={"X-CSRF-Token": csrf},
        json={"default_currency": "syp", "timezone": "Asia/Damascus"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["default_currency"] == "SYP"


def test_staff_cannot_list_users(staff_client: tuple[TestClient, str]) -> None:
    client, _ = staff_client
    response = client.get("/api/v1/users")
    assert response.status_code == 403


def test_admin_can_list_users(admin_client: tuple[TestClient, str]) -> None:
    client, _ = admin_client
    response = client.get("/api/v1/users")
    assert response.status_code == 200
    usernames = {user["username"] for user in response.json()}
    assert {"admin_test", "staff_test"}.issubset(usernames)


def test_admin_can_create_user(admin_client: tuple[TestClient, str]) -> None:
    client, csrf = admin_client
    response = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={
            "username": "new_staff",
            "password": "NewStaff!2026",
            "role": "staff",
            "job_title": "موظف إداري",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["username"] == "new_staff"
    assert response.json()["must_change_password"] is True


def test_audit_log_is_admin_only(admin_client: tuple[TestClient, str], staff_client: tuple[TestClient, str]) -> None:
    admin, _ = admin_client
    staff, _ = staff_client
    assert admin.get("/api/v1/audit").status_code == 200
    assert staff.get("/api/v1/audit").status_code == 403
