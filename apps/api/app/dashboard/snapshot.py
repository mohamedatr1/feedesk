"""Daily dashboard metric snapshot job (RPT-02).

Usage::

    python -m app.dashboard.snapshot --date YYYY-MM-DD

The date defaults to the current date in the school's configured timezone.
The snapshot is an idempotent upsert keyed by ``metric_date``; running it twice
for the same date leaves exactly one row and refreshes its stored values.
"""

from __future__ import annotations

import argparse
import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import DashboardMetricDaily
from .service import collect_counts, collect_totals_by_currency, school_today


def record_daily_snapshot(
    db: Session, metric_date: date | None = None
) -> DashboardMetricDaily:
    target_date = metric_date or school_today(db)
    totals = collect_totals_by_currency(db)
    counts = collect_counts(db)

    row = db.scalar(
        select(DashboardMetricDaily).where(
            DashboardMetricDaily.metric_date == target_date
        )
    )
    if row is None:
        row = DashboardMetricDaily(
            metric_date=target_date,
            totals_by_currency=totals,
            counts=counts,
        )
        db.add(row)
    else:
        # Assign new dicts so both PostgreSQL JSONB and JSON variants detect
        # the change without relying on in-place mutation tracking.
        row.totals_by_currency = totals
        row.counts = counts
    db.commit()
    db.refresh(row)
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Store one idempotent daily FeeDesk dashboard snapshot."
    )
    parser.add_argument(
        "--date",
        dest="metric_date",
        default=None,
        help="Snapshot date in YYYY-MM-DD (default: today in the school timezone).",
    )
    args = parser.parse_args(argv)

    metric_date: date | None = None
    if args.metric_date:
        try:
            metric_date = date.fromisoformat(args.metric_date)
        except ValueError:
            parser.error("--date must be a valid YYYY-MM-DD date")

    with SessionLocal() as db:
        row = record_daily_snapshot(db, metric_date)
        print(
            json.dumps(
                {
                    "metric_date": row.metric_date.isoformat(),
                    "totals_by_currency": row.totals_by_currency,
                    "counts": row.counts,
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
