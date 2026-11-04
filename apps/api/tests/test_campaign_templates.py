from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.campaigns.constants import DEFAULT_TEMPLATE_BODY
from app.campaigns.rendering import find_unknown_variables, render_template

from .campaign_helpers import clean_campaign_tables, create_template, install_recipient_trigger


@pytest.fixture(autouse=True)
def campaign_environment() -> None:
    clean_campaign_tables()
    install_recipient_trigger()
    yield
    clean_campaign_tables()


def test_default_template_omits_student_names() -> None:
    assert "{{student_list}}" not in DEFAULT_TEMPLATE_BODY
    assert "{{guardian_name}}" in DEFAULT_TEMPLATE_BODY
    assert find_unknown_variables(DEFAULT_TEMPLATE_BODY) == []

    rendered = render_template(
        DEFAULT_TEMPLATE_BODY,
        guardian_name="ولي أمر",
        student_names=["طالب يجب ألا يظهر"],
        amount="100.00",
        currency="SYP",
        fee_periods=["الفصل الأول"],
        school_name="مدرسة الاختبار",
        school_contact="هاتف المدرسة",
    )
    assert rendered.unresolved_variables == []
    assert "طالب يجب ألا يظهر" not in rendered.body


def test_template_versions_activation_and_read_permissions(
    admin_client: tuple[TestClient, str],
    staff_client: tuple[TestClient, str],
) -> None:
    admin, csrf = admin_client
    version_one = create_template(
        admin,
        csrf,
        name="قالب الرسوم",
        body="عزيزنا {{guardian_name}}، المبلغ {{amount}} {{currency}}.",
    )
    assert version_one["version"] == 1
    assert version_one["is_active"] is True
    assert version_one["unknown_variables"] == []

    version_two = create_template(
        admin,
        csrf,
        name="قالب الرسوم",
        body="نسخة ثانية {{guardian_name}} {{mystery}}",
    )
    assert version_two["version"] == 2
    assert version_two["is_active"] is True
    assert version_two["unknown_variables"] == ["mystery"]

    first_detail = admin.get(f"/api/v1/templates/{version_one['id']}").json()
    assert first_detail["is_active"] is False
    assert first_detail["template_body"].startswith("عزيزنا")

    listing = admin.get("/api/v1/templates").json()
    matching = [
        item for item in listing["items"] if item["name"] == "قالب الرسوم"
    ]
    assert [item["version"] for item in matching] == [2, 1]
    assert all("template_body" not in item for item in matching)

    active = admin.get(
        "/api/v1/templates/active", params={"channel": "sms", "language": "ar"}
    )
    assert active.status_code == 200
    assert active.json()["id"] == version_two["id"]
    assert active.json()["template_body"]

    variables = admin.get("/api/v1/templates/variables").json()["variables"]
    assert {item["name"] for item in variables} == {
        "guardian_name",
        "school_name",
        "student_name",
        "student_list",
        "amount",
        "currency",
        "fee_period",
        "school_contact",
    }
    student_list = next(item for item in variables if item["name"] == "student_list")
    assert student_list["fallback"] == "أبنائكم"

    staff, staff_csrf = staff_client
    assert staff.get("/api/v1/templates").status_code == 200
    assert staff.get(f"/api/v1/templates/{version_two['id']}").status_code == 200
    forbidden = staff.post(
        "/api/v1/templates",
        headers={"X-CSRF-Token": staff_csrf},
        json={
            "name": "قالب موظف",
            "language": "ar",
            "channel": "sms",
            "template_body": "نص {{guardian_name}}",
        },
    )
    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "FORBIDDEN"

    activated = admin.post(
        f"/api/v1/templates/{version_one['id']}/activate",
        headers={"X-CSRF-Token": csrf},
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["is_active"] is True
    assert admin.get(f"/api/v1/templates/{version_two['id']}").json()["is_active"] is False


def test_template_validation_csrf_and_404(
    admin_client: tuple[TestClient, str], client: TestClient
) -> None:
    admin, csrf = admin_client
    assert client.get("/api/v1/templates").status_code == 401

    missing_csrf = admin.post(
        "/api/v1/templates",
        json={
            "name": "قالب بلا حماية",
            "language": "ar",
            "channel": "sms",
            "template_body": "{{guardian_name}}",
        },
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["error"]["code"] == "CSRF_INVALID"

    blank = admin.post(
        "/api/v1/templates",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "   ",
            "language": "ar",
            "channel": "sms",
            "template_body": "{{guardian_name}}",
        },
    )
    assert blank.status_code == 422
    assert blank.json()["error"]["code"] == "VALIDATION_ERROR"

    empty_body = admin.post(
        "/api/v1/templates",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "قالب فارغ",
            "language": "ar",
            "channel": "sms",
            "template_body": "   ",
        },
    )
    assert empty_body.status_code == 422

    missing = admin.get("/api/v1/templates/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "TEMPLATE_NOT_FOUND"

    no_active = admin.get(
        "/api/v1/templates/active", params={"channel": "sms", "language": "ar"}
    )
    assert no_active.status_code == 404
    assert no_active.json()["error"]["code"] == "TEMPLATE_NOT_FOUND"
