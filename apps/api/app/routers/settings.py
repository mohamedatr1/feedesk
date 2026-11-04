from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import settings
from ..db import get_db
from ..deps import require_csrf, require_permission
from ..models import SchoolSettings, User
from ..schemas import SchoolSettingsOut, SchoolSettingsUpdate

router = APIRouter(prefix="/settings", tags=["settings"])


def _get_or_create(db: Session) -> SchoolSettings:
    row = db.get(SchoolSettings, 1)
    if row is None:
        row = SchoolSettings(
            id=1,
            school_name=settings.seed_school_name,
            default_currency=settings.seed_currency,
            currency_symbol=settings.seed_currency_symbol,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _as_dict(row: SchoolSettings) -> dict:
    return SchoolSettingsOut.model_validate(row).model_dump(mode="json")


@router.get("", response_model=SchoolSettingsOut)
def read_settings(
    _: User = Depends(require_permission("settings.view")),
    db: Session = Depends(get_db),
) -> SchoolSettings:
    return _get_or_create(db)


@router.put("", response_model=SchoolSettingsOut)
def update_settings(
    payload: SchoolSettingsUpdate,
    request: Request,
    current: User = Depends(require_permission("settings.manage")),
    _: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> SchoolSettings:
    row = _get_or_create(db)
    before = _as_dict(row)
    changes = payload.model_dump(exclude_unset=True)
    if "default_currency" in changes and changes["default_currency"]:
        changes["default_currency"] = changes["default_currency"].upper()
    for key, value in changes.items():
        setattr(row, key, value)
    db.flush()
    record_audit(
        db,
        request=request,
        actor_user_id=current.id,
        action="settings.update",
        entity_type="school_settings",
        entity_id=str(row.id),
        before=before,
        after=_as_dict(row),
    )
    db.commit()
    db.refresh(row)
    return row
