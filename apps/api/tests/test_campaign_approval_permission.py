"""FND-08: configurable per-user campaign approval permission."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.db import SessionLocal, engine
from app.main import app
from app.models import AuditEvent, User
from app.security import ROLE_PERMISSIONS, hash_password

from .campaign_helpers import (
    clean_campaign_tables,
    create_campaign,
    create_confirmed_import,
    create_template,
)
from .conftest import login

REVISION = "d3e4f5a6b7c8"


@pytest.fixture(autouse=True)
def campaign_environment() -> None:
    clean_campaign_tables()
    yield
    clean_campaign_tables()


def _create_staff(*, can_approve_campaigns: bool = False) -> tuple[str, str]:
    username = f"approval_staff_{uuid4().hex[:10]}"
    with SessionLocal() as db:
        user = User(
            username=username,
            password_hash=hash_password("ApprovalStaff!2026"),
            role="staff",
            job_title="موظف اعتماد",
            can_approve_campaigns=can_approve_campaigns,
            is_active=True,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id, username


def _staff_session(username: str) -> tuple[TestClient, str]:
    client = TestClient(app)
    csrf = login(client, username, "ApprovalStaff!2026")
    return client, csrf


def _awaiting_campaign(
    admin_client: tuple[TestClient, str],
) -> tuple[str, int]:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": f"ولي أمر {uuid4().hex[:8]}",
                "phone": "+963993000321",
                "amount": "100",
                "currency": "SYP",
                "student": "طالب الاعتماد",
                "period": "الفصل الأول",
            }
        ]
    )
    template = create_template(
        client,
        csrf,
        name=f"قالب اعتماد {uuid4().hex[:8]}",
    )
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
    assert submitted.status_code == 200, submitted.text
    body = submitted.json()
    assert body["status"] == "awaiting_approval"
    return campaign["id"], body["revision"]


def _approve(
    client: TestClient,
    csrf: str,
    campaign_id: str,
    revision: int,
    *,
    expect: int = 200,
) -> dict:
    response = client.post(
        f"/api/v1/campaigns/{campaign_id}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": revision, "acknowledge_warnings": False},
    )
    assert response.status_code == expect, response.text
    return response.json()


def test_staff_without_flag_is_denied_campaign_approval(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    admin, admin_csrf = admin_client
    staff, staff_csrf = staff_client
    campaign_id, revision = _awaiting_campaign(admin_client)

    me = staff.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["can_approve_campaigns"] is False
    assert "campaigns.approve" not in me.json()["permissions"]

    detail = staff.get(f"/api/v1/campaigns/{campaign_id}")
    assert detail.status_code == 200
    assert detail.json()["can_approve"] is False

    denied = staff.post(
        f"/api/v1/campaigns/{campaign_id}/approve",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": revision, "acknowledge_warnings": False},
    )
    assert denied.status_code == 403, denied.text
    assert denied.json()["error"]["code"] == "FORBIDDEN"

    approved = _approve(admin, admin_csrf, campaign_id, revision)
    denied_cancel = staff.post(
        f"/api/v1/campaigns/{campaign_id}/cancel",
        headers={"X-CSRF-Token": staff_csrf},
        json={"expected_revision": approved["revision"], "reason": "محاولة إلغاء"},
    )
    assert denied_cancel.status_code == 403, denied_cancel.text
    assert denied_cancel.json()["error"]["code"] == "FORBIDDEN"


def test_admin_toggle_grants_and_revokes_campaign_approval(
    admin_client: tuple[TestClient, str],
) -> None:
    admin, admin_csrf = admin_client
    user_id, username = _create_staff(can_approve_campaigns=False)

    granted = admin.patch(
        f"/api/v1/users/{user_id}",
        headers={"X-CSRF-Token": admin_csrf},
        json={"can_approve_campaigns": True},
    )
    assert granted.status_code == 200, granted.text
    assert granted.json()["can_approve_campaigns"] is True

    with SessionLocal() as db:
        user = db.get(User, user_id)
        assert user is not None
        assert user.can_approve_campaigns is True
        event = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.action == "user.update",
                AuditEvent.entity_id == user_id,
            )
            .order_by(AuditEvent.created_at.desc())
        )
        assert event is not None
        assert event.before_data is not None and event.after_data is not None
        assert event.before_data["can_approve_campaigns"] is False
        assert event.after_data["can_approve_campaigns"] is True
        # The audit payload is the same non-secret user projection; no PII or
        # credential field is introduced by the new flag.
        assert set(event.after_data) == {
            "id",
            "username",
            "email",
            "role",
            "job_title",
            "can_approve_campaigns",
            "is_active",
            "must_change_password",
        }
        assert "password_hash" not in event.before_data
        assert "password_hash" not in event.after_data

    client, csrf = _staff_session(username)
    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    assert me.json()["user"]["can_approve_campaigns"] is True
    assert {
        permission
        for permission in me.json()["permissions"]
        if permission not in ROLE_PERMISSIONS["staff"]
    } == {"campaigns.approve"}

    campaign_id, revision = _awaiting_campaign(admin_client)
    detail = client.get(f"/api/v1/campaigns/{campaign_id}")
    assert detail.status_code == 200
    assert detail.json()["can_approve"] is True

    approved = _approve(client, csrf, campaign_id, revision)
    assert approved["status"] == "approved"
    assert approved["approved_by_name"] == username
    assert approved["can_cancel"] is True

    second_id, second_revision = _awaiting_campaign(admin_client)
    second = _approve(client, csrf, second_id, second_revision)
    cancelled = client.post(
        f"/api/v1/campaigns/{second_id}/cancel",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": second["revision"], "reason": "إلغاء معتمد"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"

    revoked = admin.patch(
        f"/api/v1/users/{user_id}",
        headers={"X-CSRF-Token": admin_csrf},
        json={"can_approve_campaigns": False},
    )
    assert revoked.status_code == 200, revoked.text
    assert revoked.json()["can_approve_campaigns"] is False

    me_after = client.get("/api/v1/auth/me")
    assert me_after.status_code == 200
    assert "campaigns.approve" not in me_after.json()["permissions"]

    third_id, third_revision = _awaiting_campaign(admin_client)
    _approve(client, csrf, third_id, third_revision, expect=403)


def test_campaign_approval_flag_does_not_grant_other_permissions(
    admin_client: tuple[TestClient, str],
) -> None:
    user_id, username = _create_staff(can_approve_campaigns=True)
    client, csrf = _staff_session(username)

    me = client.get("/api/v1/auth/me")
    assert me.status_code == 200
    permissions = set(me.json()["permissions"])
    assert "campaigns.approve" in permissions
    assert permissions.isdisjoint({"users.manage", "settings.manage", "templates.manage"})

    assert client.get("/api/v1/users").status_code == 403
    assert (
        client.patch(
            f"/api/v1/users/{user_id}",
            headers={"X-CSRF-Token": csrf},
            json={"can_approve_campaigns": True},
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/api/v1/settings",
            headers={"X-CSRF-Token": csrf},
            json={"school_name": "غير مسموح"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/v1/templates",
            headers={"X-CSRF-Token": csrf},
            json={
                "name": f"قالب غير مسموح {uuid4().hex[:8]}",
                "language": "ar",
                "channel": "sms",
                "template_body": "نص",
            },
        ).status_code
        == 403
    )


def test_user_api_exposes_campaign_approval_flag(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    username = f"api_flag_{uuid4().hex[:10]}"

    created = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={
            "username": username,
            "password": "ApiFlagUser!2026",
            "role": "staff",
            "can_approve_campaigns": True,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["can_approve_campaigns"] is True
    user_id = body["id"]

    with SessionLocal() as db:
        stored = db.get(User, user_id)
        assert stored is not None
        assert stored.can_approve_campaigns is True

    listed = client.get("/api/v1/users")
    assert listed.status_code == 200
    listed_user = next(user for user in listed.json() if user["id"] == user_id)
    assert listed_user["can_approve_campaigns"] is True

    updated = client.patch(
        f"/api/v1/users/{user_id}",
        headers={"X-CSRF-Token": csrf},
        json={"can_approve_campaigns": False},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["can_approve_campaigns"] is False

    default_user = client.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": csrf},
        json={
            "username": f"api_default_{uuid4().hex[:10]}",
            "password": "ApiDefaultUser!2026",
            "role": "staff",
        },
    )
    assert default_user.status_code == 201, default_user.text
    assert default_user.json()["can_approve_campaigns"] is False


def test_campaign_approval_permission_migration_head_and_column() -> None:
    columns = {
        column["name"]: column for column in inspect(engine).get_columns("users")
    }
    column = columns["can_approve_campaigns"]
    assert column["nullable"] is False
    assert "false" in str(column["default"]).lower()

    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    assert script.get_current_head() == REVISION
    revision = script.get_revision(REVISION)
    assert revision.down_revision == "b2c3d4e5f6a7"
