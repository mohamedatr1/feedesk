from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..dashboard.schemas import DashboardOut
from ..dashboard.service import build_dashboard
from ..db import get_db
from ..deps import require_permission
from ..models import User

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardOut)
def read_dashboard(
    activity_limit: int = Query(default=5, ge=1, le=20),
    trend_days: int = Query(default=30, ge=7, le=90),
    _: User = Depends(require_permission("dashboard.view")),
    db: Session = Depends(get_db),
) -> DashboardOut:
    return build_dashboard(
        db,
        activity_limit=activity_limit,
        trend_days=trend_days,
    )
