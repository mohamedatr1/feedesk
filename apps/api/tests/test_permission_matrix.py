"""OPS-02: full API permission matrix.

This module is intentionally the single source of truth for the HTTP surface:

* ``ROUTE_MATRIX`` lists every FastAPI route/method registered by the app.
* ``test_route_matrix_covers_openapi`` fails when a route is added or removed
  without updating the matrix.
* ``test_dependency_introspection_matches_matrix`` reads the real
  ``require_permission`` closure values and ``require_csrf`` dependencies from
  ``APIRoute.dependant`` and fails on drift.
* The identity/CSRF/object-isolation tests exercise each route with valid
  fixtures.  Mutating routes are always called with real state, never against
  a provider (messaging is not dispatched by any of these routes).

Every route is exercised live; there are no static-only entries.  Routes with
state-dependent service checks (campaign submit/approve/cancel) accept the
documented 409/422 outcomes in addition to success.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.config import settings
from app.db import SessionLocal
from app.deps import require_csrf
from app.main import app
from app.models import (
    AuditEvent,
    Campaign,
    DashboardMetricDaily,
    ImportBatch,
    MessageTemplate,
    ProviderCredential,
    SchoolSettings,
    SourceFile,
    StagedRow,
    User,
)
from app.security import has_permission, hash_password

from .campaign_helpers import clean_campaign_tables, create_confirmed_import
from .conftest import login
from .messaging_helpers import create_campaign_messages

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
XLSX_SAMPLE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "xlsx"
    / "sample-01-multi-sheet.xlsx"
)
CAMPAIGN_TEMPLATE_BODY = (
    "عزيزنا {{guardian_name}}، المبلغ المتبقي {{amount}} {{currency}} "
    "عن {{fee_period}}."
)
IDENTITIES = ("anonymous", "staff", "admin", "auditor")


@dataclass(frozen=True)
class RouteSpec:
    """Declared contract for one HTTP route."""

    path: str
    method: str
    permission: str | None
    csrf_required: bool
    allowed_roles: frozenset[str]
    fixture: str
    success_status: frozenset[int] = field(default_factory=lambda: frozenset({200}))
    public: bool = False
    static_only: bool = False


def _spec(
    method: str,
    path: str,
    *,
    permission: str | None = None,
    csrf_required: bool = False,
    allowed_roles: frozenset[str] | set[str] = frozenset(),
    fixture: str = "none",
    success_status: set[int] | frozenset[int] = frozenset({200}),
    public: bool = False,
    static_only: bool = False,
) -> RouteSpec:
    return RouteSpec(
        path=path,
        method=method,
        permission=permission,
        csrf_required=csrf_required,
        allowed_roles=frozenset(allowed_roles),
        fixture=fixture,
        success_status=frozenset(success_status),
        public=public,
        static_only=static_only,
    )


_STAFF_ADMIN = frozenset({"staff", "admin"})
_ADMIN = frozenset({"admin"})
_AUTHENTICATED = frozenset({"staff", "admin", "auditor"})
_ALL_IDENTITIES = frozenset(IDENTITIES)

ROUTE_MATRIX: dict[tuple[str, str], RouteSpec] = {
    ("GET", "/health/live"): _spec(
        "GET",
        "/health/live",
        allowed_roles=_ALL_IDENTITIES,
        public=True,
    ),
    ("GET", "/health/ready"): _spec(
        "GET",
        "/health/ready",
        allowed_roles=_ALL_IDENTITIES,
        public=True,
    ),
    ("GET", "/"): _spec(
        "GET",
        "/",
        allowed_roles=_ALL_IDENTITIES,
        public=True,
    ),
    ("POST", "/api/v1/auth/login"): _spec(
        "POST",
        "/api/v1/auth/login",
        allowed_roles=_ALL_IDENTITIES,
        fixture="login",
        public=True,
    ),
    ("GET", "/api/v1/auth/me"): _spec(
        "GET",
        "/api/v1/auth/me",
        allowed_roles=_AUTHENTICATED,
    ),
    ("POST", "/api/v1/auth/logout"): _spec(
        "POST",
        "/api/v1/auth/logout",
        csrf_required=True,
        allowed_roles=_AUTHENTICATED,
    ),
    ("POST", "/api/v1/auth/change-password"): _spec(
        "POST",
        "/api/v1/auth/change-password",
        csrf_required=True,
        allowed_roles=_AUTHENTICATED,
        fixture="change_password",
    ),
    ("GET", "/api/v1/users"): _spec(
        "GET",
        "/api/v1/users",
        permission="users.manage",
        allowed_roles=_ADMIN,
    ),
    ("POST", "/api/v1/users"): _spec(
        "POST",
        "/api/v1/users",
        permission="users.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="user_create",
        success_status={201},
    ),
    ("PATCH", "/api/v1/users/{user_id}"): _spec(
        "PATCH",
        "/api/v1/users/{user_id}",
        permission="users.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="user_update",
    ),
    ("POST", "/api/v1/users/{user_id}/reset-password"): _spec(
        "POST",
        "/api/v1/users/{user_id}/reset-password",
        permission="users.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="user_reset",
    ),
    ("GET", "/api/v1/settings"): _spec(
        "GET",
        "/api/v1/settings",
        permission="settings.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("PUT", "/api/v1/settings"): _spec(
        "PUT",
        "/api/v1/settings",
        permission="settings.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="settings_update",
    ),
    ("GET", "/api/v1/audit"): _spec(
        "GET",
        "/api/v1/audit",
        permission="audit.view",
        allowed_roles=_ADMIN,
    ),
    ("GET", "/api/v1/dashboard"): _spec(
        "GET",
        "/api/v1/dashboard",
        permission="dashboard.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("GET", "/api/v1/files/{file_id}"): _spec(
        "GET",
        "/api/v1/files/{file_id}",
        permission="files.download",
        allowed_roles=_STAFF_ADMIN,
        fixture="file",
    ),
    ("POST", "/api/v1/imports"): _spec(
        "POST",
        "/api/v1/imports",
        permission="imports.upload",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="import_upload",
        success_status={201},
    ),
    ("GET", "/api/v1/imports"): _spec(
        "GET",
        "/api/v1/imports",
        permission="imports.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("GET", "/api/v1/imports/{import_id}"): _spec(
        "GET",
        "/api/v1/imports/{import_id}",
        permission="imports.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="import_detail",
    ),
    ("GET", "/api/v1/imports/{import_id}/rows"): _spec(
        "GET",
        "/api/v1/imports/{import_id}/rows",
        permission="imports.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="import_rows",
    ),
    ("GET", "/api/v1/imports/{import_id}/guardian-candidates"): _spec(
        "GET",
        "/api/v1/imports/{import_id}/guardian-candidates",
        permission="imports.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="import_guardian_candidates",
    ),
    ("POST", "/api/v1/imports/{import_id}/process"): _spec(
        "POST",
        "/api/v1/imports/{import_id}/process",
        permission="imports.review",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="import_process",
    ),
    ("PATCH", "/api/v1/imports/{import_id}/rows/{row_id}"): _spec(
        "PATCH",
        "/api/v1/imports/{import_id}/rows/{row_id}",
        permission="imports.review",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="import_row_patch",
    ),
    ("POST", "/api/v1/imports/{import_id}/rows/exclusion"): _spec(
        "POST",
        "/api/v1/imports/{import_id}/rows/exclusion",
        permission="imports.review",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="import_bulk_exclusion",
    ),
    ("POST", "/api/v1/imports/{import_id}/confirm"): _spec(
        "POST",
        "/api/v1/imports/{import_id}/confirm",
        permission="imports.confirm",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="import_confirm",
    ),
    ("POST", "/api/v1/imports/{import_id}/cancel"): _spec(
        "POST",
        "/api/v1/imports/{import_id}/cancel",
        permission="imports.review",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="import_cancel",
    ),
    ("GET", "/api/v1/templates"): _spec(
        "GET",
        "/api/v1/templates",
        permission="templates.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("GET", "/api/v1/templates/active"): _spec(
        "GET",
        "/api/v1/templates/active",
        permission="templates.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="template_active",
    ),
    ("GET", "/api/v1/templates/variables"): _spec(
        "GET",
        "/api/v1/templates/variables",
        permission="templates.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("GET", "/api/v1/templates/{template_id}"): _spec(
        "GET",
        "/api/v1/templates/{template_id}",
        permission="templates.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="template_get",
    ),
    ("POST", "/api/v1/templates"): _spec(
        "POST",
        "/api/v1/templates",
        permission="templates.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="template_create",
        success_status={201},
    ),
    ("POST", "/api/v1/templates/{template_id}/activate"): _spec(
        "POST",
        "/api/v1/templates/{template_id}/activate",
        permission="templates.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="template_activate",
    ),
    ("GET", "/api/v1/campaigns"): _spec(
        "GET",
        "/api/v1/campaigns",
        permission="campaigns.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("POST", "/api/v1/campaigns"): _spec(
        "POST",
        "/api/v1/campaigns",
        permission="campaigns.create",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign_create",
        success_status={201},
    ),
    ("GET", "/api/v1/campaigns/{campaign_id}"): _spec(
        "GET",
        "/api/v1/campaigns/{campaign_id}",
        permission="campaigns.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign",
    ),
    ("GET", "/api/v1/campaigns/{campaign_id}/results"): _spec(
        "GET",
        "/api/v1/campaigns/{campaign_id}/results",
        permission="campaigns.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign",
    ),
    ("GET", "/api/v1/campaigns/{campaign_id}/preview"): _spec(
        "GET",
        "/api/v1/campaigns/{campaign_id}/preview",
        permission="campaigns.preview",
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign",
    ),
    ("PATCH", "/api/v1/campaigns/{campaign_id}"): _spec(
        "PATCH",
        "/api/v1/campaigns/{campaign_id}",
        permission="campaigns.edit",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign_update",
    ),
    ("POST", "/api/v1/campaigns/{campaign_id}/submit"): _spec(
        "POST",
        "/api/v1/campaigns/{campaign_id}/submit",
        permission="campaigns.submit",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign_submit",
        success_status={200, 409, 422},
    ),
    ("POST", "/api/v1/campaigns/{campaign_id}/approve"): _spec(
        "POST",
        "/api/v1/campaigns/{campaign_id}/approve",
        permission="campaigns.approve",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="campaign_approve",
        success_status={200, 409, 422},
    ),
    ("POST", "/api/v1/campaigns/{campaign_id}/cancel"): _spec(
        "POST",
        "/api/v1/campaigns/{campaign_id}/cancel",
        permission="campaigns.edit",
        csrf_required=True,
        allowed_roles=_STAFF_ADMIN,
        fixture="campaign_cancel",
        success_status={200, 409},
    ),
    ("GET", "/api/v1/messages"): _spec(
        "GET",
        "/api/v1/messages",
        permission="messages.view",
        allowed_roles=_STAFF_ADMIN,
    ),
    ("GET", "/api/v1/messages/{message_id}"): _spec(
        "GET",
        "/api/v1/messages/{message_id}",
        permission="messages.view",
        allowed_roles=_STAFF_ADMIN,
        fixture="message",
    ),
    ("GET", "/api/v1/messaging/provider"): _spec(
        "GET",
        "/api/v1/messaging/provider",
        permission="settings.manage",
        allowed_roles=_ADMIN,
    ),
    ("PUT", "/api/v1/messaging/provider/credential"): _spec(
        "PUT",
        "/api/v1/messaging/provider/credential",
        permission="settings.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="provider_credential_update",
    ),
    ("POST", "/api/v1/messaging/provider/revoke"): _spec(
        "POST",
        "/api/v1/messaging/provider/revoke",
        permission="settings.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
    ),
    ("POST", "/api/v1/messaging/test-send"): _spec(
        "POST",
        "/api/v1/messaging/test-send",
        permission="settings.manage",
        csrf_required=True,
        allowed_roles=_ADMIN,
        fixture="messaging_test_send",
    ),
    ("GET", "/api/v1/messaging/balance"): _spec(
        "GET",
        "/api/v1/messaging/balance",
        permission="settings.manage",
        allowed_roles=_ADMIN,
    ),
    ("GET", "/api/v1/messaging/ops/summary"): _spec(
        "GET",
        "/api/v1/messaging/ops/summary",
        permission="settings.manage",
        allowed_roles=_ADMIN,
    ),
    ("GET", "/api/v1/messaging/ops/jobs"): _spec(
        "GET",
        "/api/v1/messaging/ops/jobs",
        permission="settings.manage",
        allowed_roles=_ADMIN,
    ),
    ("GET", "/api/v1/messaging/ops/issues"): _spec(
        "GET",
        "/api/v1/messaging/ops/issues",
        permission="settings.manage",
        allowed_roles=_ADMIN,
    ),
    ("GET", "/api/v1/messaging/ops/messages/{message_id}"): _spec(
        "GET",
        "/api/v1/messaging/ops/messages/{message_id}",
        permission="settings.manage",
        allowed_roles=_ADMIN,
        fixture="message",
    ),
}


# ---------------------------------------------------------------------------
# Fixtures / database helpers
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def matrix_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    # The matrix exercises the credential rotation route live; use a synthetic
    # Fernet key and the safe fake provider with a fixed allowlisted recipient.
    monkeypatch.setattr(
        settings, "provider_credential_key", Fernet.generate_key().decode()
    )
    monkeypatch.setattr(settings, "messaging_provider", "fake")
    monkeypatch.setattr(settings, "fake_provider_scenario", "delivered")
    monkeypatch.setattr(settings, "messaging_allowlist", "+963993000701")
    # The matrix performs one live dry-run send; keep the throttle out of the
    # way of the permission assertions (the throttle itself is unit tested).
    monkeypatch.setattr(settings, "messaging_test_send_limit", 1000)
    monkeypatch.setattr(settings, "messaging_test_send_window_seconds", 60)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    _reset_data()
    yield
    _reset_data()


def _reset_data() -> None:
    clean_campaign_tables()
    with SessionLocal() as db:
        db.execute(delete(ProviderCredential))
        db.execute(delete(DashboardMetricDaily))
        for model in (StagedRow, SourceFile, ImportBatch):
            db.execute(delete(model))
        db.commit()


def _admin_id() -> str:
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.username == "admin_test"))
    assert user_id
    return user_id


def _audit_count() -> int:
    with SessionLocal() as db:
        return int(db.scalar(select(func.count()).select_from(AuditEvent)) or 0)


def _add_user(*, role: str = "staff") -> str:
    user_id = str(uuid4())
    username = f"matrix_{role}_{uuid4().hex[:10]}"
    with SessionLocal() as db:
        db.add(
            User(
                id=user_id,
                username=username,
                password_hash=hash_password("MatrixUser!2026"),
                role=role,
                is_active=True,
                must_change_password=False,
            )
        )
        db.commit()
    return user_id


def _add_template(*, active: bool = True) -> str:
    template_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            MessageTemplate(
                id=template_id,
                name=f"قالب المصفوفة {uuid4().hex[:10]}",
                language="ar",
                channel="sms",
                template_body=CAMPAIGN_TEMPLATE_BODY,
                version=1,
                is_active=active,
                created_by=_admin_id(),
            )
        )
        db.commit()
    return template_id


def _add_batch(*, status: str = "uploaded") -> str:
    batch_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            ImportBatch(
                id=batch_id,
                source_filename="matrix.xlsx",
                file_hash=uuid4().hex + uuid4().hex,
                file_type="xlsx",
                uploaded_by=_admin_id(),
                status=status,
                totals_by_currency={},
            )
        )
        db.commit()
    return batch_id


def _add_staged_row(batch_id: str) -> str:
    row_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            StagedRow(
                id=row_id,
                import_batch_id=batch_id,
                position=0,
                source_row_number=2,
                raw_data={"guardian": "ولي أمر المصفوفة"},
                normalized_data={
                    "guardian_name": "ولي أمر المصفوفة",
                    "guardian_phone_original": "+963993000999",
                    "guardian_phone_normalized": "+963993000999",
                    "student_name": "طالب المصفوفة",
                    "total_fee": "100.00",
                    "amount_paid": "0.00",
                    "remaining_balance": "100.00",
                    "remaining_balance_calculated": "100.00",
                    "currency": "SYP",
                    "fee_period": "الفصل الأول",
                    "is_eligible": True,
                },
                parser_warnings=[],
                validation_status="valid",
                validation_errors=[],
                is_excluded=False,
            )
        )
        db.commit()
    return row_id


def _write_upload(relative_key: str, data: bytes) -> str:
    root = Path(settings.upload_dir).resolve()
    target = (root / relative_key).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return relative_key


def _add_source_file(storage_key: str, *, filename: str) -> str:
    file_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            SourceFile(
                id=file_id,
                storage_key=storage_key,
                original_filename=filename,
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                file_size=1,
                sha256_hash="0" * 64,
            )
        )
        db.commit()
    return file_id


def _add_campaign(*, status: str = "draft") -> str:
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر الحملة",
                "phone": "+963993000123",
                "amount": "100",
                "currency": "SYP",
                "student": "طالب الحملة",
                "period": "الفصل الأول",
            }
        ]
    )
    template_id = _add_template()
    campaign_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            Campaign(
                id=campaign_id,
                name=f"حملة المصفوفة {uuid4().hex[:8]}",
                source_import_id=import_data["batch_id"],
                status=status,
                channel="sms",
                template_id=template_id,
                template_version=1,
                recipient_count=0,
                revision=0,
                created_by=_admin_id(),
            )
        )
        db.commit()
    return campaign_id


def _current_school_name() -> str:
    with SessionLocal() as db:
        row = db.get(SchoolSettings, 1)
        assert row is not None
        return row.school_name


# ---------------------------------------------------------------------------
# Per-route request context builders
# ---------------------------------------------------------------------------


@dataclass
class RequestContext:
    path: str
    kwargs: dict[str, Any] = field(default_factory=dict)


def _context_none(path: str) -> RequestContext:
    return RequestContext(path)


def _context_login(path: str) -> RequestContext:
    return RequestContext(
        path,
        {"json": {"username": "admin_test", "password": "AdminTest!2026"}},
    )


def _context_change_password(path: str) -> RequestContext:
    return RequestContext(
        path,
        {
            "json": {
                "current_password": "AdminTest!2026",
                "new_password": "MatrixChange!2026",
            }
        },
    )


def _context_user_create(path: str) -> RequestContext:
    return RequestContext(
        path,
        {
            "json": {
                "username": f"matrix_created_{uuid4().hex[:10]}",
                "password": "MatrixPass!2026",
                "role": "staff",
                "job_title": "موظف مصفوفة",
            }
        },
    )


def _context_user_update(path: str) -> RequestContext:
    return RequestContext(
        path.format(user_id=_add_user()),
        {"json": {"job_title": "موظف محدّث"}},
    )


def _context_user_reset(path: str) -> RequestContext:
    return RequestContext(path.format(user_id=_add_user()), {})


def _context_settings_update(path: str) -> RequestContext:
    # Keep the stored value unchanged so this matrix run cannot affect other
    # tests that assert the seeded school name.
    return RequestContext(path, {"json": {"school_name": _current_school_name()}})


def _context_file(path: str) -> RequestContext:
    key = _write_upload("matrix/file.csv", b"guardian,amount\n")
    return RequestContext(path.format(file_id=_add_source_file(key, filename="file.csv")), {})


def _context_import_upload(path: str) -> RequestContext:
    return RequestContext(
        path,
        {
            "files": {
                "file": (
                    XLSX_SAMPLE.name,
                    XLSX_SAMPLE.read_bytes(),
                    XLSX_MIME,
                )
            },
            "data": {},
        },
    )


def _context_import_detail(path: str) -> RequestContext:
    return RequestContext(path.format(import_id=_add_batch()), {})


def _context_import_rows(path: str) -> RequestContext:
    batch_id = _add_batch(status="review_required")
    _add_staged_row(batch_id)
    return RequestContext(path.format(import_id=batch_id), {})


def _context_import_guardian_candidates(path: str) -> RequestContext:
    batch_id = _add_batch(status="review_required")
    _add_staged_row(batch_id)
    return RequestContext(path.format(import_id=batch_id), {})


def _context_import_process(path: str) -> RequestContext:
    batch_id = _add_batch(status="uploaded")
    key = _write_upload("matrix/process.xlsx", XLSX_SAMPLE.read_bytes())
    _add_source_file(key, filename=XLSX_SAMPLE.name)
    with SessionLocal() as db:
        source = db.scalar(select(SourceFile).where(SourceFile.storage_key == key))
        assert source is not None
        source.import_batch_id = batch_id
        db.commit()
    return RequestContext(
        path.format(import_id=batch_id),
        {"json": {"worksheet_name": "الفصل الأول"}},
    )


def _context_import_row_patch(path: str) -> RequestContext:
    batch_id = _add_batch(status="review_required")
    row_id = _add_staged_row(batch_id)
    return RequestContext(
        path.format(import_id=batch_id, row_id=row_id),
        {"json": {"is_excluded": True}},
    )


def _context_import_bulk_exclusion(path: str) -> RequestContext:
    batch_id = _add_batch(status="review_required")
    row_id = _add_staged_row(batch_id)
    return RequestContext(
        path.format(import_id=batch_id),
        {
            "json": {
                "is_excluded": True,
                "scope": "selected",
                "row_ids": [row_id],
            }
        },
    )


def _context_import_confirm(path: str) -> RequestContext:
    batch_id = _add_batch(status="review_required")
    _add_staged_row(batch_id)
    return RequestContext(
        path.format(import_id=batch_id),
        {"json": {"acknowledge_warnings": True}},
    )


def _context_import_cancel(path: str) -> RequestContext:
    return RequestContext(path.format(import_id=_add_batch(status="uploaded")), {})


def _context_template_active(path: str) -> RequestContext:
    _add_template(active=True)
    return RequestContext(path, {})


def _context_template_get(path: str) -> RequestContext:
    return RequestContext(path.format(template_id=_add_template()), {})


def _context_template_create(path: str) -> RequestContext:
    return RequestContext(
        path,
        {
            "json": {
                "name": f"قالب منشأ {uuid4().hex[:10]}",
                "language": "ar",
                "channel": "sms",
                "template_body": CAMPAIGN_TEMPLATE_BODY,
            }
        },
    )


def _context_template_activate(path: str) -> RequestContext:
    return RequestContext(path.format(template_id=_add_template(active=False)), {})


def _context_campaign(path: str) -> RequestContext:
    return RequestContext(path.format(campaign_id=_add_campaign()), {})


def _context_campaign_create(path: str) -> RequestContext:
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر إنشاء الحملة",
                "phone": "+963993000456",
                "amount": "50",
                "currency": "SYP",
                "student": "طالب الإنشاء",
                "period": "الفصل الأول",
            }
        ]
    )
    _add_template()
    return RequestContext(
        path,
        {
            "json": {
                "name": f"حملة منشأة {uuid4().hex[:8]}",
                "source_import_id": import_data["batch_id"],
            }
        },
    )


def _context_campaign_update(path: str) -> RequestContext:
    return RequestContext(
        path.format(campaign_id=_add_campaign(status="draft")),
        {"json": {"name": f"حملة محدّثة {uuid4().hex[:8]}"}},
    )


def _context_campaign_submit(path: str) -> RequestContext:
    return RequestContext(
        path.format(campaign_id=_add_campaign(status="draft")),
        {"json": {"expected_revision": 0}},
    )


def _context_campaign_approve(path: str) -> RequestContext:
    return RequestContext(
        path.format(campaign_id=_add_campaign(status="awaiting_approval")),
        {"json": {"expected_revision": 0, "acknowledge_warnings": True}},
    )


def _context_campaign_cancel(path: str) -> RequestContext:
    return RequestContext(
        path.format(campaign_id=_add_campaign(status="draft")),
        {"json": {"reason": "matrix test"}},
    )


def _context_message(path: str) -> RequestContext:
    data = create_campaign_messages([{}])
    return RequestContext(path.format(message_id=data["message_ids"][0]), {})


def _context_provider_credential_update(path: str) -> RequestContext:
    return RequestContext(
        path,
        {
            "json": {
                "api_key": f"matrix-provider-key-{uuid4().hex}",
                "sender_id": "FEEDESK",
                "channel": "local_sms",
            }
        },
    )


def _context_messaging_test_send(path: str) -> RequestContext:
    return RequestContext(
        path,
        {"json": {"recipient": "+963993000701", "message": "matrix dry run"}},
    )


_CONTEXT_BUILDERS = {
    "none": _context_none,
    "login": _context_login,
    "change_password": _context_change_password,
    "user_create": _context_user_create,
    "user_update": _context_user_update,
    "user_reset": _context_user_reset,
    "settings_update": _context_settings_update,
    "file": _context_file,
    "import_upload": _context_import_upload,
    "import_detail": _context_import_detail,
    "import_rows": _context_import_rows,
    "import_guardian_candidates": _context_import_guardian_candidates,
    "import_process": _context_import_process,
    "import_row_patch": _context_import_row_patch,
    "import_bulk_exclusion": _context_import_bulk_exclusion,
    "import_confirm": _context_import_confirm,
    "import_cancel": _context_import_cancel,
    "template_active": _context_template_active,
    "template_get": _context_template_get,
    "template_create": _context_template_create,
    "template_activate": _context_template_activate,
    "campaign": _context_campaign,
    "campaign_create": _context_campaign_create,
    "campaign_update": _context_campaign_update,
    "campaign_submit": _context_campaign_submit,
    "campaign_approve": _context_campaign_approve,
    "campaign_cancel": _context_campaign_cancel,
    "message": _context_message,
    "provider_credential_update": _context_provider_credential_update,
    "messaging_test_send": _context_messaging_test_send,
}


def _build_context(spec: RouteSpec) -> RequestContext:
    builder = _CONTEXT_BUILDERS[spec.fixture]
    return builder(spec.path)


# ---------------------------------------------------------------------------
# Route / dependency introspection
# ---------------------------------------------------------------------------


def _api_routes() -> list[tuple[str, APIRoute]]:
    """Return ``(full_path, APIRoute)`` for the current FastAPI router layout.

    Depending on the FastAPI version, included routers may be flattened into
    ``app.routes`` (older releases) or wrapped in ``_IncludedRouter`` entries
    whose child ``APIRoute.path`` values exclude the include prefix (newer
    releases).  Both layouts are normalised here so introspection always uses
    the same path templates as ``app.openapi()``.
    """
    routes: list[tuple[str, APIRoute]] = []
    for route in app.routes:
        if isinstance(route, APIRoute):
            routes.append((route.path, route))
            continue
        original_router = getattr(route, "original_router", None)
        if original_router is None:
            continue
        include_context = getattr(route, "include_context", None)
        prefix = getattr(include_context, "prefix", "")
        for child in original_router.routes:
            if isinstance(child, APIRoute):
                routes.append((f"{prefix}{child.path}", child))
    return routes


def _route_for(method: str, path: str) -> APIRoute:
    for full_path, route in _api_routes():
        if full_path == path and method in route.methods:
            return route
    raise AssertionError(f"Route not registered: {method} {path}")


def _dependency_chain(dependant: Any) -> list[Any]:
    dependencies: list[Any] = []
    for dependency in dependant.dependencies:
        dependencies.append(dependency)
        dependencies.extend(_dependency_chain(dependency))
    return dependencies


def _closure_value(function: Any, name: str) -> Any:
    if function is None or function.__closure__ is None:
        return None
    for free_name, cell in zip(
        function.__code__.co_freevars, function.__closure__, strict=False
    ):
        if free_name == name:
            return cell.cell_contents
    return None


def _route_permissions(route: APIRoute) -> list[str]:
    permissions: list[str] = []
    for dependency in _dependency_chain(route.dependant):
        value = _closure_value(dependency.call, "permission")
        if value is not None:
            permissions.append(str(value))
    return permissions


def _route_has_csrf(route: APIRoute) -> bool:
    return any(
        dependency.call is require_csrf
        for dependency in _dependency_chain(route.dependant)
    )


def _route_ids() -> list[str]:
    return [f"{method} {path}" for method, path in ROUTE_MATRIX]


# ---------------------------------------------------------------------------
# Matrix completeness and drift tests
# ---------------------------------------------------------------------------


def test_route_matrix_covers_openapi() -> None:
    openapi_routes = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }

    assert set(ROUTE_MATRIX) == openapi_routes, (
        "ROUTE_MATRIX drifted from app.openapi(). "
        f"Missing from matrix: {sorted(openapi_routes - set(ROUTE_MATRIX))}; "
        f"Stale matrix entries: {sorted(set(ROUTE_MATRIX) - openapi_routes)}"
    )


def test_matrix_paths_are_registered_apiroutes() -> None:
    for method, path in ROUTE_MATRIX:
        route = _route_for(method, path)
        assert method in route.methods


def test_dependency_introspection_matches_matrix() -> None:
    for (method, path), spec in ROUTE_MATRIX.items():
        route = _route_for(method, path)

        expected_permissions = [] if spec.permission is None else [spec.permission]
        assert _route_permissions(route) == expected_permissions, (
            f"{method} {path}: expected permission {expected_permissions!r}, "
            f"found {_route_permissions(route)!r}"
        )
        assert _route_has_csrf(route) is spec.csrf_required, (
            f"{method} {path}: CSRF dependency drift "
            f"(expected {spec.csrf_required}, found {_route_has_csrf(route)})"
        )


def test_csrf_requirement_matches_http_method() -> None:
    for (method, path), spec in ROUTE_MATRIX.items():
        mutating = method not in {"GET", "HEAD", "OPTIONS"}
        if (method, path) == ("POST", "/api/v1/auth/login"):
            assert spec.csrf_required is False
            continue
        assert spec.csrf_required is mutating, f"{method} {path}: CSRF flag drift"


def test_matrix_roles_match_role_permissions() -> None:
    for (method, path), spec in ROUTE_MATRIX.items():
        if spec.public:
            continue
        if spec.permission is None:
            # Session-only routes are available to every authenticated role.
            assert spec.allowed_roles == _AUTHENTICATED, f"{method} {path}"
            continue

        expected = frozenset(
            role
            for role in ("staff", "admin", "auditor")
            if has_permission(role, spec.permission)
        )
        assert spec.allowed_roles == expected, (
            f"{method} {path}: matrix roles {sorted(spec.allowed_roles)} != "
            f"RBAC roles {sorted(expected)} for {spec.permission}"
        )


def test_public_routes_are_explicit() -> None:
    public = {(method, path) for (method, path), spec in ROUTE_MATRIX.items() if spec.public}
    assert public == {
        ("GET", "/health/live"),
        ("GET", "/health/ready"),
        ("GET", "/"),
        ("POST", "/api/v1/auth/login"),
    }


def test_no_matrix_entry_is_static_only() -> None:
    static = [key for key, spec in ROUTE_MATRIX.items() if spec.static_only]
    assert static == [], f"Unexpected static-only entries: {static}"


# ---------------------------------------------------------------------------
# Identity matrix
# ---------------------------------------------------------------------------


@pytest.fixture()
def matrix_clients(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> dict[str, tuple[TestClient, str | None]]:
    auditor = _auditor_client()
    return {
        "anonymous": (TestClient(app), None),
        "staff": staff_client,
        "admin": admin_client,
        "auditor": auditor,
    }


def _auditor_client() -> tuple[TestClient, str]:
    username = "matrix_auditor"
    password = "AuditorTest!2026"
    with SessionLocal() as db:
        existing = db.scalar(select(User).where(User.username == username))
        if existing is None:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role="auditor",
                    is_active=True,
                    must_change_password=False,
                )
            )
            db.commit()
    client = TestClient(app)
    return client, login(client, username, password)


def _ephemeral_role_client(role: str) -> tuple[TestClient, str, str]:
    username = f"matrix_changepw_{role}_{uuid4().hex[:8]}"
    password = "Ephemeral!2026"
    with SessionLocal() as db:
        db.add(
            User(
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=True,
                must_change_password=False,
            )
        )
        db.commit()
    client = TestClient(app)
    return client, login(client, username, password), password


def _error_code(response: Any) -> str | None:
    try:
        return response.json()["error"]["code"]
    except (KeyError, TypeError, ValueError):
        return None


def _call(
    client: TestClient,
    method: str,
    context: RequestContext,
    *,
    csrf: str | None,
) -> Any:
    headers = {"X-CSRF-Token": csrf} if csrf else {}
    return client.request(method, context.path, headers=headers, **context.kwargs)


@pytest.mark.parametrize("route_key", list(ROUTE_MATRIX), ids=_route_ids())
def test_identity_matrix(
    route_key: tuple[str, str],
    matrix_clients: dict[str, tuple[TestClient, str | None]],
) -> None:
    method, path = route_key
    spec = ROUTE_MATRIX[route_key]

    for identity in IDENTITIES:
        _reset_data()

        if path == "/api/v1/auth/change-password" and identity != "anonymous":
            # Use a disposable account so this matrix never rewrites the shared
            # admin/staff credentials used by the rest of the suite.
            client, csrf, current_password = _ephemeral_role_client(identity)
            context = RequestContext(
                path,
                {
                    "json": {
                        "current_password": current_password,
                        "new_password": "ChangedMatrix!2026",
                    }
                },
            )
        elif path == "/api/v1/auth/change-password":
            client = TestClient(app)
            csrf = None
            context = RequestContext(
                path,
                {
                    "json": {
                        "current_password": "unused",
                        "new_password": "ChangedMatrix!2026",
                    }
                },
            )
        else:
            client, csrf = matrix_clients[identity]
            context = _build_context(spec)

        audit_before = _audit_count()
        response = _call(client, method, context, csrf=csrf)
        audit_after = _audit_count()

        label = f"{identity} {method} {path} -> {response.status_code} {response.text[:300]}"
        if spec.public:
            assert response.status_code in spec.success_status, label
            continue

        if identity == "anonymous":
            assert response.status_code == 401, label
            assert _error_code(response) in {"UNAUTHORIZED", "SESSION_EXPIRED"}, label
            if method not in {"GET", "HEAD", "OPTIONS"}:
                assert audit_after == audit_before, (
                    f"Anonymous request mutated state before failing: {method} {path}"
                )
            continue

        if identity in spec.allowed_roles:
            assert response.status_code in spec.success_status, label
        else:
            assert response.status_code == 403, label
            assert _error_code(response) in {"FORBIDDEN", "PASSWORD_CHANGE_REQUIRED"}, label


# ---------------------------------------------------------------------------
# CSRF matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "route_key",
    [
        key
        for key, spec in ROUTE_MATRIX.items()
        if spec.csrf_required
    ],
    ids=[
        f"{method} {path}"
        for (method, path), spec in ROUTE_MATRIX.items()
        if spec.csrf_required
    ],
)
def test_mutating_routes_reject_missing_csrf(
    route_key: tuple[str, str],
    admin_client: tuple[TestClient, str],
) -> None:
    method, path = route_key
    spec = ROUTE_MATRIX[route_key]
    client, _ = admin_client

    _reset_data()
    context = _build_context(spec)
    audit_before = _audit_count()

    response = client.request(method, context.path, **context.kwargs)

    assert response.status_code == 403, response.text
    assert _error_code(response) == "CSRF_INVALID", response.text
    assert _audit_count() == audit_before, (
        f"{method} {path} mutated before CSRF rejection"
    )


def test_login_is_explicitly_not_csrf_protected() -> None:
    spec = ROUTE_MATRIX[("POST", "/api/v1/auth/login")]
    assert spec.public is True
    assert spec.csrf_required is False
    assert _route_has_csrf(_route_for("POST", "/api/v1/auth/login")) is False


# ---------------------------------------------------------------------------
# Object-level authorization / isolation
# ---------------------------------------------------------------------------


def test_import_row_is_scoped_to_its_batch(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    batch_a = _add_batch(status="review_required")
    batch_b = _add_batch(status="review_required")
    row_b = _add_staged_row(batch_b)

    response = client.patch(
        f"/api/v1/imports/{batch_a}/rows/{row_b}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": True},
    )

    assert response.status_code == 404, response.text
    assert _error_code(response) == "ROW_NOT_FOUND"
    with SessionLocal() as db:
        row = db.get(StagedRow, row_b)
        assert row is not None
        assert row.is_excluded is False


def test_files_and_messages_do_not_cross_object_boundaries(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client

    key_a = _write_upload("matrix/a.csv", b"object=a\n")
    key_b = _write_upload("matrix/b.csv", b"object=b\n")
    file_a = _add_source_file(key_a, filename="a.csv")
    file_b = _add_source_file(key_b, filename="b.csv")

    response_a = client.get(f"/api/v1/files/{file_a}")
    response_b = client.get(f"/api/v1/files/{file_b}")
    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert response_a.content == b"object=a\n"
    assert response_b.content == b"object=b\n"

    campaign_a = create_campaign_messages([{"guardian_name": "أ" * 3}])
    campaign_b = create_campaign_messages([{"guardian_name": "ب" * 3}])
    message_a = campaign_a["message_ids"][0]
    message_b = campaign_b["message_ids"][0]

    detail_a = client.get(f"/api/v1/messages/{message_a}")
    detail_b = client.get(f"/api/v1/messages/{message_b}")
    assert detail_a.status_code == 200
    assert detail_b.status_code == 200
    assert detail_a.json()["id"] == message_a
    assert detail_b.json()["id"] == message_b

    filtered = client.get(
        "/api/v1/messages", params={"campaign_id": campaign_a["campaign_id"]}
    )
    assert filtered.status_code == 200
    ids = {item["id"] for item in filtered.json()["items"]}
    assert message_a in ids
    assert message_b not in ids

    assert client.get(f"/api/v1/messages/{uuid4()}").status_code == 404
    assert client.get(f"/api/v1/files/{uuid4()}").status_code == 404
