from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db
from ..schemas import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=HealthOut)
def live() -> HealthOut:
    return HealthOut(status="ok", service="feedesk-api")


@router.get("/health/ready", response_model=HealthOut)
def ready(response: Response, db: Session = Depends(get_db)) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
        return HealthOut(status="ok", service="feedesk-api", database="ok")
    except Exception:
        response.status_code = 503
        return HealthOut(status="degraded", service="feedesk-api", database="unavailable")
