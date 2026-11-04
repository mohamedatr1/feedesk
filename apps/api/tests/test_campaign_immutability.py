from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from app.db import SessionLocal
from app.models import CampaignRecipient

from .campaign_helpers import (
    clean_campaign_tables,
    create_campaign,
    create_confirmed_import,
    create_template,
    install_recipient_trigger,
)


@pytest.fixture(autouse=True)
def campaign_environment() -> None:
    clean_campaign_tables()
    install_recipient_trigger()
    yield
    clean_campaign_tables()


def test_approved_recipient_snapshots_are_immutable(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر 001",
                "phone": "+963993000001",
                "amount": "600000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر 002",
                "phone": "+963993000002",
                "amount": "400",
                "currency": "USD",
            },
        ]
    )
    template = create_template(client, csrf)
    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=template["id"],
    )
    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 0},
    )
    assert submitted.status_code == 200
    approved = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": 1, "acknowledge_warnings": False},
    )
    assert approved.status_code == 200, approved.text

    with SessionLocal() as db:
        recipient = db.scalar(
            select(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign["id"])
            .order_by(CampaignRecipient.currency_snapshot.asc())
        )
        assert recipient is not None
        recipient_id = recipient.id
        original_name = recipient.guardian_name_snapshot

        with pytest.raises(DBAPIError):
            db.execute(
                update(CampaignRecipient)
                .where(CampaignRecipient.id == recipient_id)
                .values(guardian_name_snapshot="تعديل غير مسموح")
            )
            db.flush()
        db.rollback()

        with pytest.raises(DBAPIError):
            db.execute(
                delete(CampaignRecipient).where(
                    CampaignRecipient.id == recipient_id
                )
            )
            db.flush()
        db.rollback()

    with SessionLocal() as db:
        recipient = db.get(CampaignRecipient, recipient_id)
        total = db.scalar(
            select(func.count())
            .select_from(CampaignRecipient)
            .where(CampaignRecipient.campaign_id == campaign["id"])
        )
    assert recipient is not None
    assert recipient.guardian_name_snapshot == original_name
    assert total == 2
