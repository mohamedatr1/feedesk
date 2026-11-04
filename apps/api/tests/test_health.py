from __future__ import annotations

import re

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import AuditEvent

from .conftest import SessionLocal


class _BrokenSession:
    def execute(self, *args, **kwargs):
        raise RuntimeError("database unavailable")


def test_live_health(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_health(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_ready_health_returns_503_when_database_unavailable(client: TestClient) -> None:
    app.dependency_overrides[get_db] = lambda: _BrokenSession()
    try:
        response = client.get("/health/ready")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
    assert response.json()["database"] == "unavailable"


def test_unauthenticated_settings_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/settings")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"
    assert response.headers["X-Request-ID"]


def test_safe_request_id_is_echoed(client: TestClient) -> None:
    response = client.get("/health/live", headers={"X-Request-ID": "req-123_ABC.def:1"})

    assert response.headers["X-Request-ID"] == "req-123_ABC.def:1"


def test_invalid_request_id_is_replaced(client: TestClient) -> None:
    for value in ["x" * 65, "bad value!", "bad/id"]:
        response = client.get("/health/live", headers={"X-Request-ID": value})
        generated = response.headers["X-Request-ID"]

        assert generated != value
        assert re.fullmatch(r"[0-9a-f-]{36}", generated)
        assert len(generated) <= 64


def test_safe_request_id_is_stored_in_audit(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={"X-Request-ID": "trace-123_ABC"},
        json={"username": "admin_test", "password": "AdminTest!2026"},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "auth.login",
                AuditEvent.request_id == "trace-123_ABC",
            )
        )
    assert event is not None


def test_forwarded_for_is_not_trusted_by_default(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        headers={
            "X-Request-ID": "xff-default-check",
            "X-Forwarded-For": "203.0.113.9",
        },
        json={"username": "admin_test", "password": "AdminTest!2026"},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.request_id == "xff-default-check")
        )
    assert event is not None
    assert event.ip_address != "203.0.113.9"


def test_forwarded_for_is_used_only_when_enabled(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "trust_forwarded_for", True)

    response = client.post(
        "/api/v1/auth/login",
        headers={
            "X-Request-ID": "xff-enabled-check",
            "X-Forwarded-For": "203.0.113.9, 10.0.0.1",
        },
        json={"username": "admin_test", "password": "AdminTest!2026"},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        event = db.scalar(
            select(AuditEvent).where(AuditEvent.request_id == "xff-enabled-check")
        )
    assert event is not None
    assert event.ip_address == "203.0.113.9"
