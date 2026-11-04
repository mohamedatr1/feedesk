from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class DashboardCountsOut(BaseModel):
    outstanding_records: int
    outstanding_guardians: int
    imports_total: int
    imports_awaiting_review: int
    imports_processing: int
    campaigns_total: int
    campaigns_awaiting_approval: int
    campaigns_active: int
    messages_failed_recent: int
    messages_unknown_recent: int


class ActionQueueItemOut(BaseModel):
    code: str
    count: int
    severity: str
    target: str


class RecentActivityOut(BaseModel):
    id: str
    action: str
    actor_user_id: str | None = None
    actor_name: str | None = None
    entity_type: str
    entity_id: str | None = None
    created_at: datetime
    status: str = "recorded"


class CurrencyDeltaOut(BaseModel):
    previous: str | None = None
    pct: float | None = None


class TrendSeriesPointOut(BaseModel):
    date: date
    totals_by_currency: dict[str, str] = Field(default_factory=dict)
    counts: DashboardCountsOut


class DashboardTrendsOut(BaseModel):
    available: bool
    basis_days: int
    deltas: dict[str, CurrencyDeltaOut] = Field(default_factory=dict)
    series: list[TrendSeriesPointOut] = Field(default_factory=list)


class DashboardOut(BaseModel):
    generated_at: datetime
    as_of_date: date
    totals_by_currency: dict[str, str] = Field(default_factory=dict)
    counts: DashboardCountsOut
    action_queue: list[ActionQueueItemOut] = Field(default_factory=list)
    recent_activity: list[RecentActivityOut] = Field(default_factory=list)
    trends: DashboardTrendsOut
