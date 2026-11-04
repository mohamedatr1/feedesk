"""H3/M1 campaign detail privacy regressions.

``campaigns.view`` (detail) must never return full phone numbers, rendered SMS
bodies or student names.  ``campaigns.preview`` remains the explicit reveal
route for the same campaign, including stored approved/cancelled snapshots.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from .campaign_helpers import (
    clean_campaign_tables,
    create_campaign,
    create_confirmed_import,
    create_template,
    install_recipient_trigger,
)

FULL_PHONES = ("+963993000111", "+963993000222", "+963993000333")
MASKED_PHONES = ("+963 9•• ••• 111", "+963 9•• ••• 222", "+963 9•• ••• 333")


def _fixture(client: TestClient, csrf: str) -> dict:
    clean_campaign_tables()
    install_recipient_trigger()
    import_data = create_confirmed_import(
        [
            {
                "name": "ولي أمر الخصوصية أ",
                "phone": FULL_PHONES[0],
                "amount": "100",
                "currency": "SYP",
                "student": "طالب الخصوصية أ",
                "period": "الفصل الأول",
            },
            {
                "name": "ولي أمر الخصوصية ب",
                "phone": FULL_PHONES[1],
                "amount": "200",
                "currency": "SYP",
                "student": "طالب الخصوصية ب",
                "period": "الفصل الأول",
            },
            {
                "name": "ولي أمر الخصوصية ج",
                "phone": FULL_PHONES[2],
                "amount": "0",
                "currency": "SYP",
                "student": "طالب الخصوصية ج",
                "period": "الفصل الأول",
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
    return {"campaign": campaign, "template": template, "import": import_data}


def _assert_detail_masked(body: dict) -> None:
    recipients = body["recipients"]
    excluded = body["excluded"]
    assert recipients
    assert excluded
    for recipient in recipients:
        assert recipient["phone"] == recipient["phone_masked"]
        assert recipient["message"] == ""
        assert recipient["student_names"] == []
        assert recipient["student_count"] == 1
    for record in excluded:
        assert record["phone"] == record["phone_masked"]
    assert {recipient["phone_masked"] for recipient in recipients} == set(
        MASKED_PHONES[:2]
    )
    assert excluded[0]["phone_masked"] == MASKED_PHONES[2]


def _assert_preview_full(body: dict) -> None:
    recipients = body["recipients"]
    excluded = body["excluded"]
    assert {recipient["phone"] for recipient in recipients} == set(FULL_PHONES[:2])
    assert {recipient["phone_masked"] for recipient in recipients} == set(
        MASKED_PHONES[:2]
    )
    assert all(recipient["message"] for recipient in recipients)
    assert all(
        recipient["student_count"] == len(recipient["student_names"])
        for recipient in recipients
    )
    assert {
        name
        for recipient in recipients
        for name in recipient["student_names"]
    } == {"طالب الخصوصية أ", "طالب الخصوصية ب"}
    assert excluded[0]["phone"] == FULL_PHONES[2]
    assert excluded[0]["phone_masked"] == MASKED_PHONES[2]


def _assert_no_full_phone(text: str) -> None:
    for phone in FULL_PHONES:
        assert phone not in text


def test_detail_masks_while_preview_reveals(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    data = _fixture(client, csrf)
    campaign_id = data["campaign"]["id"]

    detail = client.get(f"/api/v1/campaigns/{campaign_id}")
    preview = client.get(f"/api/v1/campaigns/{campaign_id}/preview")
    assert detail.status_code == 200, detail.text
    assert preview.status_code == 200, preview.text

    _assert_detail_masked(detail.json())
    _assert_preview_full(preview.json())
    _assert_no_full_phone(detail.text)

    # The detail route still needs the review flags, but not the bulk PII.
    assert detail.json()["can_submit"] is True
    assert detail.json()["recipient_count"] == 2
    assert detail.json()["excluded_count"] == 1


def test_stored_approved_and_cancelled_detail_stays_masked(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client
    data = _fixture(client, csrf)
    campaign_id = data["campaign"]["id"]

    submitted = client.post(
        f"/api/v1/campaigns/{campaign_id}/submit",
        headers={"X-CSRF-Token": csrf},
        json={"expected_revision": data["campaign"]["revision"]},
    )
    assert submitted.status_code == 200, submitted.text
    approved = client.post(
        f"/api/v1/campaigns/{campaign_id}/approve",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_revision": submitted.json()["revision"],
            "acknowledge_warnings": True,
        },
    )
    assert approved.status_code == 200, approved.text

    approved_detail = client.get(f"/api/v1/campaigns/{campaign_id}")
    approved_preview = client.get(f"/api/v1/campaigns/{campaign_id}/preview")
    assert approved_detail.status_code == 200, approved_detail.text
    _assert_detail_masked(approved_detail.json())
    _assert_preview_full(approved_preview.json())
    _assert_no_full_phone(approved_detail.text)

    cancelled = client.post(
        f"/api/v1/campaigns/{campaign_id}/cancel",
        headers={"X-CSRF-Token": csrf},
        json={
            "expected_revision": approved.json()["revision"],
            "reason": "اختبار الخصوصية",
        },
    )
    assert cancelled.status_code == 200, cancelled.text

    cancelled_detail = client.get(f"/api/v1/campaigns/{campaign_id}")
    cancelled_preview = client.get(f"/api/v1/campaigns/{campaign_id}/preview")
    assert cancelled_detail.status_code == 200, cancelled_detail.text
    _assert_detail_masked(cancelled_detail.json())
    _assert_preview_full(cancelled_preview.json())
    _assert_no_full_phone(cancelled_detail.text)
