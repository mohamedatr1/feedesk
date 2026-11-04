from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import (
    AuditEvent,
    Campaign,
    DashboardMetricDaily,
    FeeBalance,
    ImportBatch,
    Message,
    SchoolSettings,
    User,
)
from .schemas import (
    ActionQueueItemOut,
    CurrencyDeltaOut,
    DashboardCountsOut,
    DashboardOut,
    DashboardTrendsOut,
    RecentActivityOut,
    TrendSeriesPointOut,
)

IMPORT_REVIEW_STATUSES = ("review_required", "ready_to_confirm")
IMPORT_PROCESSING_STATUSES = ("uploaded", "processing")
CAMPAIGN_ACTIVE_STATUSES = ("queued", "sending")
RECENT_MESSAGE_DAYS = 30
MONEY_QUANTUM = Decimal("0.01")

COUNT_DEFAULTS: dict[str, int] = {
    "outstanding_records": 0,
    "outstanding_guardians": 0,
    "imports_total": 0,
    "imports_awaiting_review": 0,
    "imports_processing": 0,
    "campaigns_total": 0,
    "campaigns_awaiting_approval": 0,
    "campaigns_active": 0,
    "messages_failed_recent": 0,
    "messages_unknown_recent": 0,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> str:
    return str(value.quantize(MONEY_QUANTUM))


def school_timezone(db: Session) -> Any:
    row = db.get(SchoolSettings, 1)
    name = (row.timezone if row is not None else None) or "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def school_today(db: Session) -> date:
    return datetime.now(school_timezone(db)).date()


def collect_totals_by_currency(db: Session) -> dict[str, str]:
    """Sum positive confirmed balances per stored ISO currency.

    Money is summed with SQL ``Numeric``/``Decimal`` and formatted exactly to
    two places. Currencies are never combined and floats are never used.
    """
    rows = db.execute(
        select(FeeBalance.currency, func.sum(FeeBalance.remaining_balance_source))
        .where(
            FeeBalance.record_status == "confirmed",
            FeeBalance.remaining_balance_source > 0,
        )
        .group_by(FeeBalance.currency)
        .order_by(FeeBalance.currency)
    ).all()
    return {str(currency): _money(amount) for currency, amount in rows if currency}


def collect_counts(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    counts = dict(COUNT_DEFAULTS)
    counts["outstanding_records"] = int(
        db.scalar(
            select(func.count())
            .select_from(FeeBalance)
            .where(
                FeeBalance.record_status == "confirmed",
                FeeBalance.remaining_balance_source > 0,
            )
        )
        or 0
    )
    counts["outstanding_guardians"] = int(
        db.scalar(
            select(func.count(func.distinct(FeeBalance.guardian_id))).where(
                FeeBalance.record_status == "confirmed",
                FeeBalance.remaining_balance_source > 0,
            )
        )
        or 0
    )
    counts["imports_total"] = int(
        db.scalar(select(func.count()).select_from(ImportBatch)) or 0
    )
    counts["imports_awaiting_review"] = int(
        db.scalar(
            select(func.count())
            .select_from(ImportBatch)
            .where(ImportBatch.status.in_(IMPORT_REVIEW_STATUSES))
        )
        or 0
    )
    counts["imports_processing"] = int(
        db.scalar(
            select(func.count())
            .select_from(ImportBatch)
            .where(ImportBatch.status.in_(IMPORT_PROCESSING_STATUSES))
        )
        or 0
    )
    counts["campaigns_total"] = int(
        db.scalar(select(func.count()).select_from(Campaign)) or 0
    )
    counts["campaigns_awaiting_approval"] = int(
        db.scalar(
            select(func.count())
            .select_from(Campaign)
            .where(Campaign.status == "awaiting_approval")
        )
        or 0
    )
    counts["campaigns_active"] = int(
        db.scalar(
            select(func.count())
            .select_from(Campaign)
            .where(Campaign.status.in_(CAMPAIGN_ACTIVE_STATUSES))
        )
        or 0
    )

    cutoff = (now or _utcnow()) - timedelta(days=RECENT_MESSAGE_DAYS)
    counts["messages_failed_recent"] = int(
        db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.internal_status == "failed",
                Message.created_at >= cutoff,
            )
        )
        or 0
    )
    counts["messages_unknown_recent"] = int(
        db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.internal_status == "unknown",
                Message.created_at >= cutoff,
            )
        )
        or 0
    )
    return counts


def build_action_queue(counts: dict[str, int]) -> list[ActionQueueItemOut]:
    definitions = (
        (
            "IMPORTS_AWAITING_REVIEW",
            counts["imports_awaiting_review"],
            "warning",
            "/statements",
        ),
        (
            "CAMPAIGNS_AWAITING_APPROVAL",
            counts["campaigns_awaiting_approval"],
            "warning",
            "/campaigns?status=awaiting_approval",
        ),
        (
            "MESSAGES_FAILED",
            counts["messages_failed_recent"],
            "danger",
            "/messages?status=failed",
        ),
    )
    return [
        ActionQueueItemOut(
            code=code,
            count=count,
            severity=severity,
            target=target,
        )
        for code, count, severity, target in definitions
        if count > 0
    ]


def build_recent_activity(db: Session, limit: int) -> list[RecentActivityOut]:
    rows = db.execute(
        select(AuditEvent, User.username)
        .outerjoin(User, AuditEvent.actor_user_id == User.id)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .limit(limit)
    ).all()
    return [
        RecentActivityOut(
            id=event.id,
            action=event.action,
            actor_user_id=event.actor_user_id,
            actor_name=actor_name,
            entity_type=event.entity_type,
            entity_id=event.entity_id,
            created_at=event.created_at,
            status="recorded",
        )
        for event, actor_name in rows
    ]


def _normalise_totals(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    totals: dict[str, str] = {}
    for currency, value in raw.items():
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            continue
        totals[str(currency)] = _money(amount)
    return dict(sorted(totals.items()))


def _normalise_counts(raw: Any) -> DashboardCountsOut:
    values = dict(COUNT_DEFAULTS)
    if isinstance(raw, dict):
        for key in COUNT_DEFAULTS:
            if key in raw:
                try:
                    values[key] = int(raw[key])
                except (TypeError, ValueError):
                    continue
    return DashboardCountsOut(**values)


def _delta_map(
    current_totals: dict[str, str], previous_totals: dict[str, str]
) -> dict[str, CurrencyDeltaOut]:
    deltas: dict[str, CurrencyDeltaOut] = {}
    for currency in sorted(set(current_totals) | set(previous_totals)):
        previous_raw = previous_totals.get(currency)
        previous = Decimal(previous_raw) if previous_raw is not None else None
        current = Decimal(current_totals.get(currency, "0.00"))
        if previous is None:
            deltas[currency] = CurrencyDeltaOut(previous=None, pct=None)
            continue
        if previous == 0:
            deltas[currency] = CurrencyDeltaOut(previous=_money(previous), pct=None)
            continue
        pct = ((current - previous) / previous * Decimal("100")).quantize(MONEY_QUANTUM)
        deltas[currency] = CurrencyDeltaOut(previous=_money(previous), pct=float(pct))
    return deltas


def build_trends(
    db: Session,
    *,
    as_of_date: date,
    trend_days: int,
    current_totals: dict[str, str],
) -> DashboardTrendsOut:
    cutoff = as_of_date - timedelta(days=trend_days)
    baseline = db.scalar(
        select(DashboardMetricDaily)
        .where(DashboardMetricDaily.metric_date <= cutoff)
        .order_by(DashboardMetricDaily.metric_date.desc())
        .limit(1)
    )
    if baseline is None:
        return DashboardTrendsOut(
            available=False,
            basis_days=trend_days,
            deltas={},
            series=[],
        )

    previous_totals = _normalise_totals(baseline.totals_by_currency)
    series_start = as_of_date - timedelta(days=trend_days - 1)
    rows = db.scalars(
        select(DashboardMetricDaily)
        .where(
            DashboardMetricDaily.metric_date >= series_start,
            DashboardMetricDaily.metric_date <= as_of_date,
        )
        .order_by(DashboardMetricDaily.metric_date.asc())
    ).all()
    series = [
        TrendSeriesPointOut(
            date=row.metric_date,
            totals_by_currency=_normalise_totals(row.totals_by_currency),
            counts=_normalise_counts(row.counts),
        )
        for row in rows
    ]
    return DashboardTrendsOut(
        available=True,
        basis_days=trend_days,
        deltas=_delta_map(current_totals, previous_totals),
        series=series,
    )


def build_dashboard(
    db: Session, *, activity_limit: int, trend_days: int
) -> DashboardOut:
    now = _utcnow()
    as_of_date = school_today(db)
    totals = collect_totals_by_currency(db)
    counts = collect_counts(db, now=now)
    return DashboardOut(
        generated_at=now,
        as_of_date=as_of_date,
        totals_by_currency=totals,
        counts=DashboardCountsOut(**counts),
        action_queue=build_action_queue(counts),
        recent_activity=build_recent_activity(db, activity_limit),
        trends=build_trends(
            db,
            as_of_date=as_of_date,
            trend_days=trend_days,
            current_totals=totals,
        ),
    )
