from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..campaigns import service
from ..campaigns.constants import ALLOWED_VARIABLES
from ..db import get_db
from ..deps import require_csrf, require_permission
from ..models import MessageTemplate, User
from ..schemas import (
    TemplateCreate,
    TemplateDetailOut,
    TemplateListOut,
    TemplateVariablesOut,
)

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=TemplateListOut)
def list_templates(
    channel: str = Query(default="sms", max_length=30),
    language: str | None = Query(default=None, max_length=10),
    active_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission("templates.view")),
    db: Session = Depends(get_db),
) -> dict:
    conditions = [MessageTemplate.channel == channel]
    if language:
        conditions.append(MessageTemplate.language == language)
    if active_only:
        conditions.append(MessageTemplate.is_active.is_(True))
    total = db.scalar(
        select(func.count()).select_from(MessageTemplate).where(*conditions)
    ) or 0
    templates = list(
        db.scalars(
            select(MessageTemplate)
            .where(*conditions)
            .order_by(
                MessageTemplate.name.asc(),
                MessageTemplate.version.desc(),
                MessageTemplate.created_at.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {
        "items": [service.template_summary(db, template) for template in templates],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


@router.get("/active", response_model=TemplateDetailOut)
def get_active_template(
    channel: str = Query(default="sms", max_length=30),
    language: str = Query(default="ar", max_length=10),
    _: User = Depends(require_permission("templates.view")),
    db: Session = Depends(get_db),
) -> dict:
    template = service.active_template(db, channel=channel, language=language)
    return service.template_detail(db, template)


@router.get("/variables", response_model=TemplateVariablesOut)
def list_template_variables(
    _: User = Depends(require_permission("templates.view")),
) -> dict:
    return {"variables": [dict(item) for item in ALLOWED_VARIABLES]}


@router.get("/{template_id}", response_model=TemplateDetailOut)
def get_template(
    template_id: str,
    _: User = Depends(require_permission("templates.view")),
    db: Session = Depends(get_db),
) -> dict:
    template = service.get_template(db, template_id)
    return service.template_detail(db, template)


@router.post("", response_model=TemplateDetailOut, status_code=201)
def create_template(
    payload: TemplateCreate,
    request: Request,
    current: User = Depends(require_permission("templates.manage")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    template = service.create_template(
        db,
        request=request,
        user=current,
        name=payload.name,
        language=payload.language,
        channel=payload.channel,
        template_body=payload.template_body,
    )
    return service.template_detail(db, template)


@router.post("/{template_id}/activate", response_model=TemplateDetailOut)
def activate_template(
    template_id: str,
    request: Request,
    current: User = Depends(require_permission("templates.manage")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    template = service.get_template(db, template_id)
    template = service.activate_template(
        db, template, request=request, user=current
    )
    return service.template_detail(db, template)
