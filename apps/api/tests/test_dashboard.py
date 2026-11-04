from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.dashboard.service import COUNT_DEFAULTS, school_today
from app.dashboard.snapshot import record_daily_snapshot
from app.db import SessionLocal
from app.main import app
from app.models import (
    AuditEvent,
    Campaign,
    DashboardMetricDaily,
    FeeBalance,
    Guardian,
    ImportBatch,
    User,
)

from .campaign_helpers import clean_campaign_tables
from .messaging_helpers import create_campaign_messages


@pytest.fixture(autouse=True)
def clean_dashboard_state() -> None:
    _clean()
    yield
    _clean()


def _clean() -> None:
    clean_campaign_tables()
    with SessionLocal() as db:
        db.execute(delete(DashboardMetricDaily))
        db.commit()


def _admin_id() -> str:
    with SessionLocal() as db:
        user_id = db.scalar(select(User.id).where(User.username == "admin_test"))
    assert user_id
    return user_id


def _add_balances(entries: list[dict]) -> dict:
    now = datetime.now(timezone.utc)
    batch_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            ImportBatch(
                id=batch_id,
                source_filename="dashboard-balances.xlsx",
                file_hash=uuid4().hex + uuid4().hex,
                file_type="xlsx",
                uploaded_by=_admin_id(),
                status="confirmed",
                total_rows=len(entries),
                valid_rows=len(entries),
                totals_by_currency={},
                confirmed_at=now,
                confirmed_by=_admin_id(),
            )
        )
        guardians: dict[str, Guardian] = {}
        for entry in entries:
            key = entry["key"]
            guardian = guardians.get(key)
            if guardian is None:
                guardian = Guardian(
                    id=str(uuid4()),
                    full_name=entry.get("name", key),
                    normalized_name=entry.get("name", key),
                    status="active",
                )
                db.add(guardian)
                db.flush()
                guardians[key] = guardian
            amount = Decimal(str(entry["amount"])).quantize(Decimal("0.01"))
            db.add(
                FeeBalance(
                    id=str(uuid4()),
                    guardian_id=guardian.id,
                    import_batch_id=batch_id,
                    total_fee=amount,
                    amount_paid=Decimal("0.00"),
                    remaining_balance_source=amount,
                    remaining_balance_calculated=None,
                    currency=entry.get("currency", "SYP"),
                    record_status=entry.get("status", "confirmed"),
                    reviewed_by=_admin_id(),
                    reviewed_at=now,
                )
            )
        db.commit()
    return {"batch_id": batch_id, "guardian_ids": [g.id for g in guardians.values()]}


def _add_import(status: str) -> str:
    batch_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            ImportBatch(
                id=batch_id,
                source_filename=f"dashboard-{status}.xlsx",
                file_hash=uuid4().hex + uuid4().hex,
                file_type="xlsx",
                uploaded_by=_admin_id(),
                status=status,
                totals_by_currency={},
            )
        )
        db.commit()
    return batch_id


def _add_campaign(status: str) -> str:
    campaign_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            Campaign(
                id=campaign_id,
                name=f"dashboard {status} {uuid4().hex[:8]}",
                status=status,
                channel="sms",
                recipient_count=0,
                created_by=_admin_id(),
            )
        )
        db.commit()
    return campaign_id


def _add_audit_event(
    *,
    action: str,
    entity_id: str,
    actor_user_id: str | None,
    created_at: datetime,
    before: dict | None = None,
    after: dict | None = None,
) -> str:
    event_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            AuditEvent(
                id=event_id,
                actor_user_id=actor_user_id,
                action=action,
                entity_type="dashboard_test",
                entity_id=entity_id,
                before_data=before,
                after_data=after,
                created_at=created_at,
            )
        )
        db.commit()
    return event_id


def _add_snapshot(metric_date: date, totals: dict, counts: dict | None = None) -> str:
    row_id = str(uuid4())
    with SessionLocal() as db:
        db.add(
            DashboardMetricDaily(
                id=row_id,
                metric_date=metric_date,
                totals_by_currency=totals,
                counts=counts or dict(COUNT_DEFAULTS),
            )
        )
        db.commit()
    return row_id


def test_totals_separate_currencies_and_use_decimal_strings(
    staff_client: tuple[TestClient, str],
) -> None:
    client, _ = staff_client
    _add_balances(
        [
            {"key": "a", "name": "ولي أمر أ", "amount": "100.10", "currency": "SYP"},
            {"key": "a", "name": "ولي أمر أ", "amount": "50.20", "currency": "SYP"},
            {"key": "b", "name": "ولي أمر ب", "amount": "7.05", "currency": "USD"},
            {"key": "c", "name": "ولي أمر ج", "amount": "-10.00", "currency": "SYP"},
            {"key": "c", "name": "ولي أمر ج", "amount": "0.00", "currency": "SYP"},
            {
                "key": "d",
                "name": "ولي أمر د",
                "amount": "99.99",
                "currency": "EUR",
                "status": "pending",
            },
        ]
    )

    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["totals_by_currency"] == {"SYP": "150.30", "USD": "7.05"}
    assert all(isinstance(value, str) for value in payload["totals_by_currency"].values())
    assert payload["counts"]["outstanding_records"] == 3
    assert payload["counts"]["outstanding_guardians"] == 2


def test_action_queue_uses_recent_messages_and_exact_targets(
    staff_client: tuple[TestClient, str],
) -> None:
    client, _ = staff_client
    for status in ("review_required", "review_required", "ready_to_confirm", "uploaded"):
        _add_import(status)
    _add_campaign("awaiting_approval")
    _add_campaign("awaiting_approval")

    now = datetime.now(timezone.utc)
    create_campaign_messages(
        [
            {"message_status": "failed"},
            {"message_status": "failed", "created_at": now - timedelta(days=31)},
            {"message_status": "unknown"},
            {"message_status": "unknown", "created_at": now - timedelta(days=31)},
            {"message_status": "delivered"},
        ],
        campaign_status="approved",
    )

    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["counts"]["imports_total"] == 4
    assert payload["counts"]["imports_awaiting_review"] == 3
    assert payload["counts"]["imports_processing"] == 1
    assert payload["counts"]["messages_failed_recent"] == 1
    assert payload["counts"]["messages_unknown_recent"] == 1
    assert payload["action_queue"] == [
        {
            "code": "IMPORTS_AWAITING_REVIEW",
            "count": 3,
            "severity": "warning",
            "target": "/statements",
        },
        {
            "code": "CAMPAIGNS_AWAITING_APPROVAL",
            "count": 2,
            "severity": "warning",
            "target": "/campaigns?status=awaiting_approval",
        },
        {
            "code": "MESSAGES_FAILED",
            "count": 1,
            "severity": "danger",
            "target": "/messages?status=failed",
        },
    ]


def test_action_queue_omits_zero_counts(
    staff_client: tuple[TestClient, str],
) -> None:
    client, _ = staff_client

    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200, response.text
    assert response.json()["action_queue"] == []


def test_recent_activity_limit_actor_join_and_no_payload_leak(
    admin_client: tuple[TestClient, str],
) -> None:
    client, _ = admin_client
    admin_id = _admin_id()
    base = datetime.now(timezone.utc) + timedelta(seconds=10)
    first = _add_audit_event(
        action="dashboard.test.first",
        entity_id=str(uuid4()),
        actor_user_id=admin_id,
        created_at=base,
        before={"secret": "top-secret-before"},
    )
    second = _add_audit_event(
        action="dashboard.test.second",
        entity_id=str(uuid4()),
        actor_user_id=admin_id,
        created_at=base + timedelta(seconds=1),
        after={"secret": "top-secret-after"},
    )
    third = _add_audit_event(
        action="dashboard.test.third",
        entity_id=str(uuid4()),
        actor_user_id=None,
        created_at=base + timedelta(seconds=2),
    )

    response = client.get("/api/v1/dashboard", params={"activity_limit": 2})
    assert response.status_code == 200, response.text
    payload = response.json()

    assert len(payload["recent_activity"]) == 2
    assert [item["id"] for item in payload["recent_activity"]] == [third, second]
    assert payload["recent_activity"][0]["actor_name"] is None
    assert payload["recent_activity"][1]["actor_name"] == "admin_test"
    assert payload["recent_activity"][1]["actor_user_id"] == admin_id
    assert payload["recent_activity"][1]["status"] == "recorded"
    assert set(payload["recent_activity"][1]) == {
        "id",
        "action",
        "actor_user_id",
        "actor_name",
        "entity_type",
        "entity_id",
        "created_at",
        "status",
    }
    assert first not in [item["id"] for item in payload["recent_activity"]]
    assert "top-secret" not in response.text


@pytest.mark.parametrize("query", ["activity_limit=0", "activity_limit=21", "trend_days=6"])
def test_dashboard_bounds_are_validated(
    staff_client: tuple[TestClient, str],
    query: str,
) -> None:
    client, _ = staff_client
    response = client.get(f"/api/v1/dashboard?{query}")
    assert response.status_code == 422, response.text


def test_trends_unavailable_without_history(
    staff_client: tuple[TestClient, str],
) -> None:
    client, _ = staff_client

    response = client.get("/api/v1/dashboard", params={"trend_days": 7})
    assert response.status_code == 200, response.text
    trends = response.json()["trends"]

    assert trends["available"] is False
    assert trends["basis_days"] == 7
    assert trends["deltas"] == {}
    assert trends["series"] == []


def test_trends_available_with_baseline_previous_and_null_pct(
    staff_client: tuple[TestClient, str],
) -> None:
    client, _ = staff_client
    _add_balances(
        [
            {"key": "a", "name": "ولي أمر أ", "amount": "120.00", "currency": "SYP"},
            {"key": "b", "name": "ولي أمر ب", "amount": "5.00", "currency": "USD"},
            {"key": "c", "name": "ولي أمر ج", "amount": "2.00", "currency": "EUR"},
        ]
    )
    with SessionLocal() as db:
        as_of = school_today(db)
    baseline = as_of - timedelta(days=7)
    mid = as_of - timedelta(days=1)

    _add_snapshot(
        baseline,
        {"SYP": "100.00", "USD": "0.00"},
        {**COUNT_DEFAULTS, "outstanding_records": 2},
    )
    _add_snapshot(
        mid,
        {"SYP": "110.00", "USD": "4.00", "EUR": "2.00"},
        {**COUNT_DEFAULTS, "outstanding_records": 3},
    )
    _add_snapshot(
        as_of,
        {"SYP": "115.00", "USD": "5.00", "EUR": "2.00"},
        {**COUNT_DEFAULTS, "outstanding_records": 3},
    )

    response = client.get("/api/v1/dashboard", params={"trend_days": 7})
    assert response.status_code == 200, response.text
    payload = response.json()
    trends = payload["trends"]

    assert trends["available"] is True
    assert trends["basis_days"] == 7
    assert trends["deltas"]["SYP"] == {
        "previous": "100.00",
        "pct": 20.0,
    }
    assert trends["deltas"]["USD"] == {"previous": "0.00", "pct": None}
    assert trends["deltas"]["EUR"] == {"previous": None, "pct": None}
    assert [point["date"] for point in trends["series"]] == [
        mid.isoformat(),
        as_of.isoformat(),
    ]
    assert trends["series"][0]["totals_by_currency"] == {
        "EUR": "2.00",
        "SYP": "110.00",
        "USD": "4.00",
    }
    assert trends["series"][1]["counts"]["outstanding_records"] == 3


def test_snapshot_is_idempotent_and_refreshes_values() -> None:
    metric_date = date(2026, 1, 2)
    _add_balances(
        [{"key": "a", "name": "ولي أمر أ", "amount": "10.00", "currency": "SYP"}]
    )
    with SessionLocal() as db:
        first = record_daily_snapshot(db, metric_date)

    _add_balances(
        [{"key": "b", "name": "ولي أمر ب", "amount": "5.00", "currency": "USD"}]
    )
    with SessionLocal() as db:
        second = record_daily_snapshot(db, metric_date)
        row_count = db.scalar(
            select(func.count())
            .select_from(DashboardMetricDaily)
            .where(DashboardMetricDaily.metric_date == metric_date)
        )

    assert row_count == 1
    assert first.id == second.id
    assert second.totals_by_currency == {"SYP": "10.00", "USD": "5.00"}
    assert second.counts["outstanding_records"] == 2
    assert second.counts["outstanding_guardians"] == 2


def test_staff_and_admin_access_and_anonymous_denied(
    staff_client: tuple[TestClient, str],
    admin_client: tuple[TestClient, str],
) -> None:
    staff, _ = staff_client
    admin, _ = admin_client

    assert staff.get("/api/v1/dashboard").status_code == 200
    assert admin.get("/api/v1/dashboard").status_code == 200

    anonymous = TestClient(app).get("/api/v1/dashboard")
    assert anonymous.status_code == 401, anonymous.text
    assert anonymous.json()["error"]["code"] in {"UNAUTHORIZED", "SESSION_EXPIRED"}
