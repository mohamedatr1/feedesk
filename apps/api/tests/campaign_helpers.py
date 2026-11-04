from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import delete, select, text, update

from app.db import SessionLocal, engine
from app.models import (
    Campaign,
    CampaignRecipient,
    FeeBalance,
    Guardian,
    GuardianContact,
    GuardianStudentRelationship,
    ImportBatch,
    Message,
    MessageTemplate,
    SendJob,
    SourceFile,
    StagedRow,
    Student,
    User,
)

CONFIRMED_FILENAME = "campaign-confirmed.xlsx"
DEFAULT_BODY = (
    "عزيزنا {{guardian_name}}، رسوم {{student_list}} عن {{fee_period}}: "
    "{{amount}} {{currency}}. للتواصل {{school_contact}}."
)


def clean_campaign_tables() -> None:
    with SessionLocal() as db:
        # The immutability trigger blocks recipient deletes for approved
        # campaigns, so neutralise status before removing fixtures.
        db.execute(update(Campaign).values(status="cancelled"))
        db.flush()
        for model in (
            SendJob,
            Message,
            CampaignRecipient,
            Campaign,
            MessageTemplate,
            FeeBalance,
            GuardianStudentRelationship,
            GuardianContact,
            Student,
            Guardian,
            StagedRow,
            SourceFile,
            ImportBatch,
        ):
            db.execute(delete(model))
        db.commit()


def install_recipient_trigger() -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                CREATE OR REPLACE FUNCTION prevent_approved_campaign_recipient_mutation()
                RETURNS trigger AS $$
                DECLARE
                    target_campaign_id text;
                    campaign_status text;
                BEGIN
                    IF TG_OP = 'DELETE' THEN
                        target_campaign_id := OLD.campaign_id;
                    ELSE
                        target_campaign_id := NEW.campaign_id;
                    END IF;
                    SELECT status INTO campaign_status
                    FROM campaigns
                    WHERE id = target_campaign_id;
                    IF campaign_status IN (
                        'approved', 'queued', 'sending', 'completed',
                        'completed_with_errors'
                    ) THEN
                        RAISE EXCEPTION
                            'campaign_recipients is immutable while campaign is %',
                            campaign_status;
                    END IF;
                    IF TG_OP = 'DELETE' THEN
                        RETURN OLD;
                    END IF;
                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;
                """
            )
        )
        connection.execute(
            text(
                "DROP TRIGGER IF EXISTS campaign_recipients_immutable "
                "ON campaign_recipients"
            )
        )
        connection.execute(
            text(
                """
                CREATE TRIGGER campaign_recipients_immutable
                BEFORE UPDATE OR DELETE ON campaign_recipients
                FOR EACH ROW EXECUTE FUNCTION prevent_approved_campaign_recipient_mutation();
                """
            )
        )


def _admin_id() -> str:
    with SessionLocal() as db:
        admin_id = db.scalar(select(User.id).where(User.username == "admin_test"))
    assert admin_id
    return admin_id


def create_confirmed_import(entries: list[dict]) -> dict:
    """Create a confirmed import with balances directly, bypassing parsing."""
    now = datetime.now(timezone.utc)
    batch_id = str(uuid4())
    admin_id = _admin_id()
    guardian_ids: dict[str, str] = {}
    with SessionLocal() as db:
        batch = ImportBatch(
            id=batch_id,
            source_filename=CONFIRMED_FILENAME,
            file_hash=uuid4().hex + uuid4().hex,
            file_type="xlsx",
            uploaded_by=admin_id,
            status="confirmed",
            total_rows=len(entries),
            valid_rows=len(entries),
            invalid_rows=0,
            duplicate_rows=0,
            excluded_rows=0,
            totals_by_currency={},
            confirmed_at=now,
            confirmed_by=admin_id,
        )
        db.add(batch)
        db.flush()

        guardians: dict[str, Guardian] = {}
        for entry in entries:
            key = entry.get("key") or entry["name"]
            guardian = guardians.get(key)
            if guardian is None:
                guardian = Guardian(
                    id=str(uuid4()),
                    full_name=entry["name"],
                    normalized_name=entry["name"],
                    status=entry.get("status", "active"),
                )
                db.add(guardian)
                db.flush()
                guardians[key] = guardian
                guardian_ids[key] = guardian.id

            phone = entry.get("phone")
            if phone is not None and not db.scalar(
                select(GuardianContact.id).where(
                    GuardianContact.guardian_id == guardian.id
                )
            ):
                if phone == "INVALID":
                    original_phone = "not-a-phone"
                    normalized_phone = None
                elif phone == "INVALID_POSSIBLE":
                    original_phone = "+963900000001"
                    normalized_phone = "+963900000001"
                else:
                    original_phone = phone
                    normalized_phone = phone
                db.add(
                    GuardianContact(
                        id=str(uuid4()),
                        guardian_id=guardian.id,
                        original_phone=original_phone,
                        normalized_phone=normalized_phone,
                        contact_type="mobile",
                        is_primary=True,
                        is_verified=False,
                    )
                )

            student = None
            if entry.get("student"):
                student = Student(
                    id=str(uuid4()),
                    full_name=entry["student"],
                    status="active",
                )
                db.add(student)
                db.flush()
                db.add(
                    GuardianStudentRelationship(
                        id=str(uuid4()),
                        guardian_id=guardian.id,
                        student_id=student.id,
                        relationship_type="guardian",
                        source_import_id=batch_id,
                    )
                )

            db.add(
                FeeBalance(
                    id=str(uuid4()),
                    guardian_id=guardian.id,
                    student_id=student.id if student is not None else None,
                    import_batch_id=batch_id,
                    fee_period=entry.get("period"),
                    total_fee=Decimal(str(entry["amount"])).quantize(Decimal("0.01")),
                    amount_paid=Decimal("0.00"),
                    remaining_balance_source=Decimal(str(entry["amount"])).quantize(
                        Decimal("0.01")
                    ),
                    remaining_balance_calculated=None,
                    currency=entry.get("currency", "SYP"),
                    record_status="confirmed",
                    reviewed_by=admin_id,
                    reviewed_at=now,
                )
            )
        db.commit()
    return {"batch_id": batch_id, "guardian_ids": guardian_ids}


def create_template(
    client: TestClient,
    csrf: str,
    *,
    name: str = "قالب تذكير",
    body: str = DEFAULT_BODY,
    channel: str = "sms",
    language: str = "ar",
    expect: int = 201,
) -> dict:
    response = client.post(
        "/api/v1/templates",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": name,
            "language": language,
            "channel": channel,
            "template_body": body,
        },
    )
    assert response.status_code == expect, response.text
    return response.json()


def create_campaign(
    client: TestClient,
    csrf: str,
    *,
    source_import_id: str,
    name: str = "حملة تذكير",
    template_id: str | None = None,
    expect: int = 201,
) -> dict:
    payload: dict = {"name": name, "source_import_id": source_import_id}
    if template_id:
        payload["template_id"] = template_id
    response = client.post(
        "/api/v1/campaigns",
        headers={"X-CSRF-Token": csrf},
        json=payload,
    )
    assert response.status_code == expect, response.text
    return response.json()
