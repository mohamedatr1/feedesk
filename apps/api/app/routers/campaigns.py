from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..campaigns import service
from ..db import get_db
from ..deps import require_csrf, require_permission
from ..errors import ApiError
from ..messaging import queries as messaging_queries
from ..models import Campaign, User
from ..schemas import (
    CampaignApproveRequest,
    CampaignCancelRequest,
    CampaignCreate,
    CampaignDetailOut,
    CampaignListOut,
    CampaignResultsOut,
    CampaignSubmitRequest,
    CampaignUpdate,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

_CAMPAIGN_STATUSES = {
    "draft",
    "review_required",
    "awaiting_approval",
    "approved",
    "queued",
    "sending",
    "completed",
    "completed_with_errors",
    "failed",
    "cancelled",
}


@router.get("", response_model=CampaignListOut)
def list_campaigns(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: User = Depends(require_permission("campaigns.view")),
    db: Session = Depends(get_db),
) -> dict:
    if status is not None and status not in _CAMPAIGN_STATUSES:
        raise ApiError(
            422,
            "VALIDATION_ERROR",
            "حالة الحملة غير صالحة.",
            "Invalid campaign status filter.",
        )
    conditions = [Campaign.status == status] if status else []
    total = db.scalar(
        select(func.count()).select_from(Campaign).where(*conditions)
    ) or 0
    campaigns = list(
        db.scalars(
            select(Campaign)
            .where(*conditions)
            .order_by(Campaign.created_at.desc(), Campaign.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return {
        "items": [service.campaign_summary(db, campaign) for campaign in campaigns],
        "total": int(total),
        "page": page,
        "page_size": page_size,
    }


@router.post("", response_model=CampaignDetailOut, status_code=201)
def create_campaign(
    payload: CampaignCreate,
    request: Request,
    current: User = Depends(require_permission("campaigns.create")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.create_campaign(
        db,
        request=request,
        user=current,
        name=payload.name,
        source_import_id=payload.source_import_id,
        template_id=payload.template_id,
    )
    return service.campaign_detail(db, campaign, current, reveal=True)


@router.get("/{campaign_id}", response_model=CampaignDetailOut)
def get_campaign(
    campaign_id: str,
    current: User = Depends(require_permission("campaigns.view")),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.get_campaign(db, campaign_id)
    return service.campaign_detail(db, campaign, current)


@router.get("/{campaign_id}/results", response_model=CampaignResultsOut)
def get_campaign_results(
    campaign_id: str,
    _: User = Depends(require_permission("campaigns.view")),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.get_campaign(db, campaign_id)
    return messaging_queries.campaign_results(db, campaign)


@router.get("/{campaign_id}/preview", response_model=CampaignDetailOut)
def preview_campaign(
    campaign_id: str,
    current: User = Depends(require_permission("campaigns.preview")),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.get_campaign(db, campaign_id)
    return service.campaign_detail(db, campaign, current, reveal=True)


@router.patch("/{campaign_id}", response_model=CampaignDetailOut)
def update_campaign(
    campaign_id: str,
    payload: CampaignUpdate,
    request: Request,
    current: User = Depends(require_permission("campaigns.edit")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.get_campaign(db, campaign_id)
    campaign = service.update_campaign(
        db,
        campaign,
        request=request,
        user=current,
        name=payload.name,
        template_id=payload.template_id,
    )
    return service.campaign_detail(db, campaign, current, reveal=True)


@router.post("/{campaign_id}/submit", response_model=CampaignDetailOut)
def submit_campaign(
    campaign_id: str,
    payload: CampaignSubmitRequest,
    request: Request,
    current: User = Depends(require_permission("campaigns.submit")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.submit_campaign(
        db,
        campaign_id,
        request=request,
        user=current,
        expected_revision=payload.expected_revision,
    )
    return service.campaign_detail(db, campaign, current, reveal=True)


@router.post("/{campaign_id}/approve", response_model=CampaignDetailOut)
def approve_campaign(
    campaign_id: str,
    payload: CampaignApproveRequest,
    request: Request,
    current: User = Depends(require_permission("campaigns.approve")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.approve_campaign(
        db,
        campaign_id,
        request=request,
        user=current,
        expected_revision=payload.expected_revision,
        acknowledge_warnings=payload.acknowledge_warnings,
    )
    return service.campaign_detail(db, campaign, current, reveal=True)


@router.post("/{campaign_id}/cancel", response_model=CampaignDetailOut)
def cancel_campaign(
    campaign_id: str,
    payload: CampaignCancelRequest,
    request: Request,
    current: User = Depends(require_permission("campaigns.edit")),
    _csrf: None = Depends(require_csrf),
    db: Session = Depends(get_db),
) -> dict:
    campaign = service.cancel_campaign(
        db,
        campaign_id,
        request=request,
        user=current,
        reason=payload.reason,
        expected_revision=payload.expected_revision,
    )
    return service.campaign_detail(db, campaign, current, reveal=True)
