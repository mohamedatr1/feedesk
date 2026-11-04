from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.campaigns.rendering import find_unknown_variables, format_amount, render_template
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


def test_rendering_allowed_variables_fallbacks_and_unknowns() -> None:
    body = (
        "  عزيزنا {{ guardian_name }}، رسوم {{student_list}} عن {{fee_period}}.  "
        "المبلغ {{amount}} {{currency}}. تواصل {{school_contact}}. "
        "قيمة غير معروفة {{mystery_value}}  "
    )
    result = render_template(
        body,
        guardian_name="ولي أمر 001",
        student_names=["طالب 001", "طالب 002"],
        amount=Decimal("2100000.00"),
        currency="SYP",
        fee_periods=[],
        school_name=None,
        school_contact=None,
    )
    assert result.body == (
        "عزيزنا ولي أمر 001، رسوم طالب 001، طالب 002 عن الفصل الحالي. "
        "المبلغ 2,100,000.00 SYP. تواصل إدارة المدرسة. قيمة غير معروفة {{mystery_value}}"
    )
    assert result.unknown_variables == ["mystery_value"]
    assert result.unresolved_variables == ["mystery_value"]
    assert find_unknown_variables(body) == ["mystery_value"]

    fallback = render_template(
        "{{school_name}}|{{student_name}}|{{student_list}}|{{fee_period}}|{{school_contact}}",
        guardian_name="ولي أمر",
        student_names=[],
        amount="1.00",
        currency="USD",
        fee_periods=[],
        school_name="",
        school_contact="",
    )
    assert fallback.body == "المدرسة|الطالب|أبنائكم|الفصل الحالي|إدارة المدرسة"
    assert fallback.unresolved_variables == []


def test_rendering_requires_guardian_name_and_formats_amounts() -> None:
    result = render_template(
        "{{guardian_name}} {{amount}} {{currency}}",
        guardian_name="   ",
        student_names=[],
        amount=Decimal("1234.5"),
        currency="SYP",
        fee_periods=[],
        school_name="مدرسة",
        school_contact="+963900000000",
    )
    assert result.body == "{{guardian_name}} 1,234.50 SYP"
    assert result.unresolved_variables == ["guardian_name"]
    assert format_amount(None) == "0.00"
    assert format_amount("-100000.00") == "-100,000.00"


def test_eligibility_groups_currencies_and_exclusions(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر مجمّع",
                "key": "grouped",
                "phone": "+963993000001",
                "amount": "600000",
                "currency": "SYP",
                "student": "طالب أ",
                "period": "الفصل الأول",
            },
            {
                "name": "ولي أمر مجمّع",
                "key": "grouped",
                "amount": "400000",
                "currency": "SYP",
                "student": "طالب ب",
                "period": "الفصل الثاني",
            },
            {
                "name": "ولي أمر مجمّع",
                "key": "grouped",
                "amount": "400",
                "currency": "USD",
                "student": "طالب أ",
                "period": "الفصل الأول",
            },
            {
                "name": "ولي أمر سليم",
                "key": "healthy",
                "phone": "+963993000008",
                "amount": "500000",
                "currency": "SYP",
                "student": "طالب ث",
                "period": "الفصل الأول",
            },
            {
                "name": "ولي أمر صفر",
                "phone": "+963993000002",
                "amount": "0",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر سالب",
                "phone": "+963993000003",
                "amount": "-100000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر بلا عملة",
                "phone": "+963993000004",
                "amount": "500000",
                "currency": "",
            },
            {
                "name": "ولي أمر بلا هاتف",
                "phone": None,
                "amount": "500000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر هاتف خاطئ",
                "phone": "INVALID",
                "amount": "500000",
                "currency": "SYP",
            },
            {
                "name": "ولي أمر غير نشط",
                "phone": "+963993000007",
                "amount": "500000",
                "currency": "SYP",
                "status": "inactive",
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

    assert campaign["status"] == "draft"
    assert campaign["source_filename"] == "campaign-confirmed.xlsx"
    assert campaign["recipient_count"] == 3
    assert campaign["excluded_count"] == 6
    assert campaign["invalid_contact_count"] == 2
    assert campaign["totals_by_currency"] == {
        "SYP": "1500000.00",
        "USD": "400.00",
    }
    assert campaign["template_version"] == 1
    assert campaign["revision"] == 0
    assert campaign["can_submit"] is True

    grouped_syp = next(
        recipient
        for recipient in campaign["recipients"]
        if recipient["currency"] == "SYP" and recipient["amount"] == "1000000.00"
    )
    assert grouped_syp["guardian_name"] == "ولي أمر مجمّع"
    assert grouped_syp["student_names"] == ["طالب أ", "طالب ب"]
    assert grouped_syp["fee_periods"] == ["الفصل الأول", "الفصل الثاني"]
    assert len(grouped_syp["fee_balance_ids"]) == 2
    assert grouped_syp["validation_status"] == "valid"
    assert "1,000,000.00" in grouped_syp["message"]
    assert "SYP" in grouped_syp["message"]

    grouped_usd = next(
        recipient
        for recipient in campaign["recipients"]
        if recipient["currency"] == "USD"
    )
    assert grouped_usd["amount"] == "400.00"
    assert grouped_usd["guardian_id"] == grouped_syp["guardian_id"]

    excluded_by_name = {
        record["guardian_name"]: record for record in campaign["excluded"]
    }
    assert {item["code"] for item in excluded_by_name["ولي أمر صفر"]["reasons"]} == {
        "ZERO_BALANCE"
    }
    assert {item["code"] for item in excluded_by_name["ولي أمر سالب"]["reasons"]} == {
        "NEGATIVE_BALANCE"
    }
    assert {
        item["code"] for item in excluded_by_name["ولي أمر بلا عملة"]["reasons"]
    } == {"MISSING_CURRENCY"}
    assert {
        item["code"] for item in excluded_by_name["ولي أمر بلا هاتف"]["reasons"]
    } == {"MISSING_PHONE"}
    assert {
        item["code"] for item in excluded_by_name["ولي أمر هاتف خاطئ"]["reasons"]
    } == {"INVALID_PHONE"}
    assert {
        item["code"] for item in excluded_by_name["ولي أمر غير نشط"]["reasons"]
    } == {"GUARDIAN_INACTIVE"}

    listing = client.get("/api/v1/campaigns").json()
    item = next(entry for entry in listing["items"] if entry["id"] == campaign["id"])
    assert item["recipient_count"] == 3
    assert item["excluded_count"] == 6
    assert item["totals_by_currency"] == {"SYP": "1500000.00", "USD": "400.00"}


def test_shared_phone_warns_without_merging_guardians(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر مشترك أ",
                "phone": "+963993000009",
                "amount": "600000",
                "currency": "SYP",
                "student": "طالب أ",
            },
            {
                "name": "ولي أمر مشترك ب",
                "phone": "+963993000009",
                "amount": "700000",
                "currency": "SYP",
                "student": "طالب ب",
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

    assert campaign["recipient_count"] == 2
    assert len({item["guardian_id"] for item in campaign["recipients"]}) == 2
    warning = next(
        item for item in campaign["warnings"] if item["code"] == "SHARED_PHONE"
    )
    assert warning["count"] == 2
    assert all(
        recipient["validation_status"] == "warning"
        and recipient["warnings"][0]["code"] == "SHARED_PHONE"
        for recipient in campaign["recipients"]
    )

    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": campaign["revision"]},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "awaiting_approval"

    unacknowledged = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": submitted.json()["revision"], "acknowledge_warnings": False},
    )
    assert unacknowledged.status_code == 422
    assert unacknowledged.json()["error"]["code"] == "WARNINGS_UNACKNOWLEDGED"

    approved = client.post(
        f"/api/v1/campaigns/{campaign['id']}/approve",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": submitted.json()["revision"], "acknowledge_warnings": True},
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "approved"
    assert all(
        recipient["validation_status"] == "warning"
        for recipient in body["recipients"]
    )
    with SessionLocal() as db:
        snapshots = list(
            db.scalars(
                select(CampaignRecipient).where(
                    CampaignRecipient.campaign_id == campaign["id"]
                )
            ).all()
        )
    assert len(snapshots) == 2
    assert all(row.eligibility_status == "warning" for row in snapshots)


def test_unknown_template_variables_block_submission(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر 001",
                "phone": "+963993000011",
                "amount": "600000",
                "currency": "SYP",
                "student": "طالب 001",
            }
        ]
    )
    bad_template = create_template(
        client,
        csrf,
        name="قالب بمتغير مجهول",
        body="عزيزنا {{guardian_name}} {{unknown_code}}",
    )
    assert bad_template["unknown_variables"] == ["unknown_code"]

    campaign = create_campaign(
        client,
        csrf,
        source_import_id=import_data["batch_id"],
        template_id=bad_template["id"],
    )
    assert campaign["can_submit"] is False
    assert any(
        item["code"] == "UNRESOLVED_VARIABLES"
        for item in campaign["blocking_reasons"]
    )
    blocked = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": campaign["revision"]},
    )
    assert blocked.status_code == 422
    assert blocked.json()["error"]["code"] == "CAMPAIGN_BLOCKED"

    good_template = create_template(
        client,
        csrf,
        name="قالب سليم",
        body="عزيزنا {{guardian_name}}، المبلغ {{amount}} {{currency}}.",
    )
    patched = client.patch(
        f"/api/v1/campaigns/{campaign['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"template_id": good_template["id"]},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["revision"] == campaign["revision"] + 1
    assert patched.json()["can_submit"] is True

    submitted = client.post(
        f"/api/v1/campaigns/{campaign['id']}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": patched.json()["revision"]},
    )
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["status"] == "awaiting_approval"
