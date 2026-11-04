from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response
from openpyxl import Workbook
from sqlalchemy import delete, select

from app.config import settings
from app.imports.ocr import is_available as ocr_is_available
from app.models import (
    AuditEvent,
    FeeBalance,
    Guardian,
    GuardianContact,
    GuardianStudentRelationship,
    ImportBatch,
    SourceFile,
    StagedRow,
    Student,
)

from .conftest import SessionLocal, login

SAMPLES = Path(__file__).resolve().parent / "fixtures"
XLSX_SAMPLES = SAMPLES / "xlsx"
PDF_SAMPLES = SAMPLES / "pdf"
REAL_SAMPLES = Path(__file__).resolve().parents[3] / ".local" / "samples" / "real"
REAL_XLSX = REAL_SAMPLES / "xlsx" / "FeeDesk_Sample_Fee_Statement.xlsx"
REAL_PDF = REAL_SAMPLES / "pdf" / "FeeDesk_Sample_Fee_Statement.pdf"

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
PDF_MIME = "application/pdf"


@pytest.fixture(autouse=True)
def import_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    _clean_import_tables()
    yield
    _clean_import_tables()


def _clean_import_tables() -> None:
    with SessionLocal() as db:
        for model in (
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


def _upload(
    client: TestClient,
    csrf: str,
    path: Path,
    *,
    mime: str = XLSX_MIME,
    data: dict[str, str] | None = None,
) -> Response:
    with path.open("rb") as handle:
        return client.post(
            "/api/v1/imports",
            headers={"X-CSRF-Token": csrf},
            files={"file": (path.name, handle, mime)},
            data=data or {},
        )


def _upload_sample(client: TestClient, csrf: str, name: str, **form: str):
    path = XLSX_SAMPLES / name
    return _upload(client, csrf, path, data=form)


def _make_workbook(
    path: Path,
    headers: list[str],
    rows: list[list[object]],
    *,
    title: str = "البيانات",
) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return path


STANDARD_HEADERS = [
    "اسم ولي الأمر",
    "رقم الهاتف",
    "اسم الطالب",
    "إجمالي القسط",
    "المدفوع",
    "المتبقي",
    "العملة",
]


def _audit_actions(entity_id: str) -> list[str]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AuditEvent.action).where(AuditEvent.entity_id == entity_id)
            ).all()
        )


def test_upload_multi_sheet_auto_selects_statement_sheet(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client

    response = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "review_required"
    assert body["available_sheets"] == ["الفصل الأول", "الفصل الثاني"]
    assert body["worksheet_name"] == "الفصل الأول"
    assert body["total_rows"] == 7
    assert body["source_file_id"]
    assert body["available_headers"]
    assert body["column_mapping"]["guardian_name"] == "اسم ولي الأمر"
    auto_warning = next(
        warning
        for warning in body["warnings"]
        if warning["code"] == "SHEET_AUTO_SELECTED"
    )
    assert "الفصل الأول" in auto_warning["message_ar"]

    source = client.get(f"/api/v1/files/{body['source_file_id']}")
    assert source.status_code == 200
    assert source.content[:2] == b"PK"


@pytest.mark.skipif(
    not (REAL_XLSX.is_file() and REAL_PDF.is_file()),
    reason="real sample statements are not available",
)
def test_upload_real_samples_stages_rows_with_inferred_currency(
    admin_client: tuple[TestClient, str],
) -> None:
    client, csrf = admin_client

    xlsx = _upload(client, csrf, REAL_XLSX)
    assert xlsx.status_code == 201, xlsx.text
    xlsx_body = xlsx.json()
    assert xlsx_body["worksheet_name"] == "كشف الأقساط"
    assert xlsx_body["total_rows"] == 18
    assert any(
        warning["code"] == "SHEET_AUTO_SELECTED"
        for warning in xlsx_body["warnings"]
    )
    xlsx_rows = client.get(f"/api/v1/imports/{xlsx_body['id']}/rows").json()[
        "items"
    ]
    assert len(xlsx_rows) == 18
    assert all(
        row["normalized_data"]["currency"] == "SYP" for row in xlsx_rows
    )
    assert not any(
        issue["code"] == "MISSING_CURRENCY"
        for row in xlsx_rows
        for issue in row["validation_errors"]
    )

    pdf = _upload(client, csrf, REAL_PDF, mime=PDF_MIME)
    assert pdf.status_code == 201, pdf.text
    pdf_body = pdf.json()
    assert pdf_body["total_rows"] == 18
    pdf_rows = client.get(f"/api/v1/imports/{pdf_body['id']}/rows").json()[
        "items"
    ]
    assert len(pdf_rows) == 18
    assert all(
        row["normalized_data"]["currency"] == "SYP" for row in pdf_rows
    )
    assert not any(
        issue["code"] == "MISSING_CURRENCY"
        for row in pdf_rows
        for issue in row["validation_errors"]
    )


def test_summary_aggregates_uploader_and_excluded_rows(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    upload = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx")
    assert upload.status_code == 201, upload.text
    uploaded = upload.json()
    assert uploaded["uploaded_by_name"] == "admin_test"
    assert uploaded["max_upload_mb"] == 20.0
    assert uploaded["excluded_rows"] == 0
    # The statement sheet is selected and staged during upload.
    assert uploaded["worksheet_name"] == "الفصل الأول"
    assert uploaded["totals_by_currency"] == {
        "SYP": "2600000.00",
        "USD": "400.00",
    }
    assert uploaded["updated_at"]
    assert uploaded["cancelled_at"] is None

    batch_id = uploaded["id"]
    processed = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "الفصل الأول"},
    )
    assert processed.status_code == 200, processed.text
    detail = processed.json()
    assert detail["excluded_rows"] == 0
    # Invalid (negative) rows are not aggregated; zero balances are.
    assert detail["totals_by_currency"] == {
        "SYP": "2600000.00",
        "USD": "400.00",
    }

    rows = client.get(f"/api/v1/imports/{batch_id}/rows").json()["items"]
    negative = next(row for row in rows if row["validation_status"] == "invalid")
    valid_syp = next(
        row
        for row in rows
        if row["source_row_number"] == 5 and row["validation_status"] != "invalid"
    )

    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{negative['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": True},
    )
    after_invalid_exclusion = client.get(f"/api/v1/imports/{batch_id}").json()
    assert after_invalid_exclusion["excluded_rows"] == 1
    assert after_invalid_exclusion["totals_by_currency"] == {
        "SYP": "2600000.00",
        "USD": "400.00",
    }

    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{valid_syp['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": True},
    )
    after_valid_exclusion = client.get(f"/api/v1/imports/{batch_id}").json()
    assert after_valid_exclusion["excluded_rows"] == 2
    assert after_valid_exclusion["totals_by_currency"] == {
        "SYP": "2000000.00",
        "USD": "400.00",
    }

    listing = client.get("/api/v1/imports").json()
    item = next(entry for entry in listing["items"] if entry["id"] == batch_id)
    assert item["uploaded_by_name"] == "admin_test"
    assert item["excluded_rows"] == 2
    assert item["totals_by_currency"] == {
        "SYP": "2000000.00",
        "USD": "400.00",
    }


def test_process_sheet_stages_rows_and_counts(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    batch_id = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx").json()["id"]

    response = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "الفصل الأول"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "review_required"
    assert body["worksheet_name"] == "الفصل الأول"
    assert body["total_rows"] == 7
    assert body["invalid_rows"] == 1
    assert body["duplicate_rows"] == 0
    assert body["valid_rows"] == 6
    assert body["column_mapping"]["guardian_name"] == "اسم ولي الأمر"
    assert body["error_summary"]["by_code"]["NEGATIVE_BALANCE"] == 1
    assert "اسم ولي الأمر" in body["available_headers"]
    assert "المتبقي" in body["available_headers"]
    assert "+963" not in json.dumps(body["available_headers"])

    rows = client.get(f"/api/v1/imports/{batch_id}/rows").json()
    assert rows["total"] == 7
    by_source_row = {row["source_row_number"]: row for row in rows["items"]}
    first = by_source_row[5]
    assert first["normalized_data"]["guardian_name"] == "ولي أمر تجريبي 001"
    assert first["normalized_data"]["remaining_balance"] == "600000.00"
    assert first["normalized_data"]["currency"] == "SYP"
    assert first["validation_status"] == "warning"
    assert any(
        issue["code"] == "INVALID_PHONE" for issue in first["validation_errors"]
    )

    zero = by_source_row[6]
    assert any(issue["code"] == "ZERO_BALANCE" for issue in zero["validation_errors"])
    assert zero["normalized_data"]["remaining_balance"] == "0.00"

    negative = by_source_row[9]
    assert negative["validation_status"] == "invalid"
    assert any(
        issue["code"] == "NEGATIVE_BALANCE" and issue["severity"] == "error"
        for issue in negative["validation_errors"]
    )

    missing_phone = by_source_row[8]
    assert any(
        issue["code"] == "MISSING_PHONE" for issue in missing_phone["validation_errors"]
    )

    sibling = by_source_row[10]
    assert sibling["normalized_data"]["guardian_name"] == "ولي أمر تجريبي 001"
    assert not any(
        issue["code"] == "DUPLICATE_ROW" for issue in sibling["validation_errors"]
    )

    filtered = client.get(
        f"/api/v1/imports/{batch_id}/rows", params={"status": "invalid"}
    ).json()
    assert filtered["total"] == 1
    searched = client.get(
        f"/api/v1/imports/{batch_id}/rows", params={"q": "طالب تجريبي 006"}
    ).json()
    assert searched["total"] == 1

    actions = _audit_actions(batch_id)
    assert "import.upload" in actions
    assert "import.process" in actions


def test_upload_single_sheet_arabic_digits_normalized(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client

    response = _upload_sample(client, csrf, "sample-02-arabic-digits.xlsx")

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "review_required"
    assert body["total_rows"] == 4
    assert body["worksheet_name"] == "بيانات"
    assert "الموبايل" in body["available_headers"]
    assert "٠٩٩٠٠٠٠٠١١" not in json.dumps(body)

    detail = client.get(f"/api/v1/imports/{body['id']}").json()
    assert detail["available_headers"] == body["available_headers"]
    assert "٠٩٩٠٠٠٠٠١١" not in json.dumps(detail)

    rows = client.get(f"/api/v1/imports/{body['id']}/rows").json()["items"]
    first = rows[0]
    assert "raw_data" not in first
    assert first["normalized_data"]["guardian_phone_original"] == "٠٩٩٠٠٠٠٠١١"
    assert first["normalized_data"]["guardian_phone_normalized"] == "+963990000011"
    assert first["normalized_data"]["total_fee"] == "123456.00"
    assert first["normalized_data"]["remaining_balance"] == "73456.00"
    assert first["normalized_data"]["currency"] == "SYP"

    zero = rows[3]
    assert zero["validation_status"] == "warning"
    assert any(
        issue["code"] == "ZERO_BALANCE" for issue in zero["validation_errors"]
    )


def test_staged_rows_hide_raw_data_but_keep_it_server_side(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    body = _upload_sample(client, csrf, "sample-02-arabic-digits.xlsx").json()

    response = client.get(f"/api/v1/imports/{body['id']}/rows")
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert items
    assert all("raw_data" not in item for item in items)

    with SessionLocal() as db:
        stored = db.scalar(
            select(StagedRow)
            .where(StagedRow.import_batch_id == body["id"])
            .order_by(StagedRow.position)
            .limit(1)
        )
    assert stored is not None
    assert stored.raw_data["الموبايل"] == "٠٩٩٠٠٠٠٠١١"


def test_messy_headers_separators_and_mapping(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    body = _upload_sample(client, csrf, "sample-03-messy-headers.xlsx").json()
    response = client.post(
        f"/api/v1/imports/{body['id']}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "كشف ملخبط"},
    )
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["total_rows"] == 4
    assert detail["column_mapping"]["guardian_name"] == "اسم الولي"
    assert "fee_period" not in detail["column_mapping"]

    rows = client.get(f"/api/v1/imports/{body['id']}/rows").json()["items"]
    assert rows[0]["source_row_number"] == 7
    assert rows[0]["normalized_data"]["amount_paid"] == "1250000.50"
    assert rows[1]["normalized_data"]["amount_paid"] == "1250000.50"
    assert rows[1]["normalized_data"]["remaining_balance"] == "1250000.50"
    assert rows[2]["normalized_data"]["currency"] == "USD"
    assert rows[3]["normalized_data"]["student_name"] is None


def test_pdf_text_and_scanned_pdf(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client

    text_response = _upload(
        client, csrf, PDF_SAMPLES / "sample-01-text-table.pdf", mime=PDF_MIME
    )
    assert text_response.status_code == 201, text_response.text
    text_body = text_response.json()
    assert text_body["status"] == "review_required"
    assert text_body["file_type"] == "pdf"
    assert text_body["total_rows"] == 6
    assert text_body["invalid_rows"] == 1

    rows = client.get(f"/api/v1/imports/{text_body['id']}/rows").json()["items"]
    assert {row["source_page_number"] for row in rows} == {1}
    assert "ولي أمر" in rows[0]["normalized_data"]["guardian_name"]
    assert rows[0]["normalized_data"]["guardian_phone_normalized"] == "+963900000101"
    assert any(
        issue["code"] == "INVALID_PHONE" for issue in rows[0]["validation_errors"]
    )
    assert rows[4]["normalized_data"]["remaining_balance"] == "-100000.00"

    scanned_response = _upload(
        client, csrf, PDF_SAMPLES / "sample-02-scanned-image.pdf", mime=PDF_MIME
    )
    assert scanned_response.status_code == 201, scanned_response.text
    scanned = scanned_response.json()
    assert scanned["status"] == "review_required"
    if ocr_is_available():
        # Assisted OCR stages rows, but they still go through review/validation.
        assert scanned["total_rows"] > 0
        assert any(
            warning["code"] == "OCR_USED" for warning in scanned["warnings"]
        )
    else:
        assert scanned["total_rows"] == 0
        assert any(
            warning["code"] == "SCANNED_PDF" for warning in scanned["warnings"]
        )


def test_duplicate_file_requires_override_with_reason(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    first = _upload(
        client, csrf, PDF_SAMPLES / "sample-02-scanned-image.pdf", mime=PDF_MIME
    )
    assert first.status_code == 201

    duplicate = _upload(
        client, csrf, PDF_SAMPLES / "sample-02-scanned-image.pdf", mime=PDF_MIME
    )
    assert duplicate.status_code == 409
    error = duplicate.json()["error"]
    assert error["code"] == "DUPLICATE_FILE"
    assert error["details"]["existing_import_id"] == first.json()["id"]

    missing_reason = _upload(
        client,
        csrf,
        PDF_SAMPLES / "sample-02-scanned-image.pdf",
        mime=PDF_MIME,
        data={"force_duplicate": "true"},
    )
    assert missing_reason.status_code == 422
    assert missing_reason.json()["error"]["code"] == "DUPLICATE_REASON_REQUIRED"

    forced = _upload(
        client,
        csrf,
        PDF_SAMPLES / "sample-02-scanned-image.pdf",
        mime=PDF_MIME,
        data={"force_duplicate": "true", "duplicate_reason": "إعادة رفع للتدقيق"},
    )
    assert forced.status_code == 201, forced.text
    assert forced.json()["duplicate_reason"] == "إعادة رفع للتدقيق"
    assert "import.duplicate_override" in _audit_actions(forced.json()["id"])


def test_invalid_file_type_and_magic_bytes(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client

    text_file = tmp_path / "statement.txt"
    text_file.write_text("not a statement", encoding="utf-8")
    response = _upload(client, csrf, text_file, mime="text/plain")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INVALID_FILE_TYPE"

    disguised = tmp_path / "statement.xlsx"
    disguised.write_bytes(b"%PDF-1.4 not really a workbook")
    mismatch = _upload(client, csrf, disguised, mime=XLSX_MIME)
    assert mismatch.status_code == 422
    assert mismatch.json()["error"]["code"] == "FILE_TYPE_MISMATCH"


def test_duplicate_rows_and_exclusion(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "duplicates.xlsx",
        STANDARD_HEADERS,
        [
            ["ولي أمر تكرار", "0993000001", "طالب أ", 1000, 400, 600, "SYP"],
            ["ولي أمر تكرار", "0993000001", "طالب أ", 1000, 400, 600, "SYP"],
        ],
    )
    response = _upload(client, csrf, path)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total_rows"] == 2
    assert body["duplicate_rows"] == 1
    assert body["invalid_rows"] == 1
    assert body["status"] == "review_required"

    rows = client.get(f"/api/v1/imports/{body['id']}/rows").json()["items"]
    duplicate = next(row for row in rows if row["validation_status"] == "invalid")
    assert any(
        issue["code"] == "DUPLICATE_ROW" and issue["severity"] == "error"
        for issue in duplicate["validation_errors"]
    )

    exclude = client.patch(
        f"/api/v1/imports/{body['id']}/rows/{duplicate['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": True},
    )
    assert exclude.status_code == 200, exclude.text
    assert exclude.json()["validation_status"] == "excluded"
    assert exclude.json()["is_excluded"] is True

    detail = client.get(f"/api/v1/imports/{body['id']}").json()
    assert detail["duplicate_rows"] == 0
    assert detail["invalid_rows"] == 0
    assert detail["status"] == "ready_to_confirm"

    excluded_only = client.get(
        f"/api/v1/imports/{body['id']}/rows", params={"status": "excluded"}
    ).json()
    assert excluded_only["total"] == 1

    confirmed = client.post(
        f"/api/v1/imports/{body['id']}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": False},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "confirmed"


def test_shared_phone_warns_and_never_merges_guardians(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "shared-phone.xlsx",
        STANDARD_HEADERS,
        [
            ["ولي أمر أول", "0993000009", "طالب أول", 1000, 400, 600, "SYP"],
            ["ولي أمر ثان", "0993000009", "طالب ثان", 1000, 400, 600, "SYP"],
        ],
    )
    body = _upload(client, csrf, path).json()
    assert body["status"] == "ready_to_confirm" or body["status"] == "review_required"

    rows = client.get(f"/api/v1/imports/{body['id']}/rows").json()["items"]
    assert all(
        any(issue["code"] == "SHARED_PHONE" for issue in row["validation_errors"])
        for row in rows
    )

    confirmed = client.post(
        f"/api/v1/imports/{body['id']}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert confirmed.status_code == 200, confirmed.text

    with SessionLocal() as db:
        guardians = list(db.scalars(select(Guardian)).all())
        contacts = list(db.scalars(select(GuardianContact)).all())
    assert {guardian.full_name for guardian in guardians} == {
        "ولي أمر أول",
        "ولي أمر ثان",
    }
    assert len(contacts) == 2
    assert {contact.normalized_phone for contact in contacts} == {"+963993000009"}


def test_confirm_reuses_guardian_across_rows_without_student(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "same-guardian.xlsx",
        STANDARD_HEADERS,
        [
            ["ولي أمر واحد", "0993000021", None, 1000, 400, 600, "SYP"],
            ["ولي أمر واحد", "0993000021", None, 1000, 500, 500, "SYP"],
        ],
    )
    body = _upload(client, csrf, path).json()
    assert body["status"] == "ready_to_confirm"
    assert body["total_rows"] == 2

    confirmed = client.post(
        f"/api/v1/imports/{body['id']}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": False},
    )
    assert confirmed.status_code == 200, confirmed.text

    with SessionLocal() as db:
        guardians = list(db.scalars(select(Guardian)).all())
        contacts = list(db.scalars(select(GuardianContact)).all())
        balances = list(db.scalars(select(FeeBalance)).all())
        students = list(db.scalars(select(Student)).all())

    assert len(guardians) == 1
    assert len(contacts) == 1
    assert len(balances) == 2
    assert students == []
    assert {balance.guardian_id for balance in balances} == {guardians[0].id}


def test_row_patch_revalidates_and_blocks_after_confirm(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    batch_id = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx").json()["id"]
    client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "الفصل الأول"},
    )
    rows = client.get(f"/api/v1/imports/{batch_id}/rows").json()["items"]
    negative = next(row for row in rows if row["validation_status"] == "invalid")

    patched = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{negative['id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "normalized_data": {
                "remaining_balance": "100000.00",
                "guardian_phone_original": "0990000005",
            }
        },
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["normalized_data"]["remaining_balance"] == "100000.00"
    assert body["normalized_data"]["guardian_phone_normalized"] == "+963990000005"
    assert body["validation_status"] == "warning"
    assert any(
        issue["code"] == "TOTAL_DISCREPANCY" for issue in body["validation_errors"]
    )

    detail = client.get(f"/api/v1/imports/{batch_id}").json()
    assert detail["invalid_rows"] == 0
    assert "import.row.update" in _audit_actions(batch_id)

    with SessionLocal() as db:
        row_event = db.scalar(
            select(AuditEvent)
            .where(
                AuditEvent.entity_id == batch_id,
                AuditEvent.action == "import.row.update",
            )
            .order_by(AuditEvent.created_at.desc())
        )
    assert row_event is not None
    assert row_event.before_data["normalized_data"]["remaining_balance"] == "-100000.00"
    assert row_event.after_data["normalized_data"]["remaining_balance"] == "100000.00"
    assert (
        row_event.before_data["normalized_data"]["guardian_phone_original"]
        == "+963 9•• ••• 005"
    )
    assert (
        row_event.after_data["normalized_data"]["guardian_phone_original"]
        == "+963 9•• ••• 005"
    )
    serialized_audit = json.dumps(
        {"before": row_event.before_data, "after": row_event.after_data}
    )
    assert "+963900000005" not in serialized_audit
    assert "0990000005" not in serialized_audit
    assert row_event.before_data["is_excluded"] is False
    assert row_event.after_data["is_excluded"] is False

    unknown = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{negative['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"normalized_data": {"unknown_field": "x"}},
    )
    assert unknown.status_code == 422

    excluded = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{negative['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": True},
    )
    assert excluded.status_code == 200

    confirmed = client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert confirmed.status_code == 200

    blocked = client.patch(
        f"/api/v1/imports/{batch_id}/rows/{negative['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": False},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "IMPORT_STATE_INVALID"


def test_confirm_transaction_is_idempotent_and_preserves_provenance(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    batch_id = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx").json()["id"]
    client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "الفصل الأول"},
    )
    rows = client.get(f"/api/v1/imports/{batch_id}/rows").json()["items"]
    negative = next(row for row in rows if row["validation_status"] == "invalid")
    client.patch(
        f"/api/v1/imports/{batch_id}/rows/{negative['id']}",
        headers={"X-CSRF-Token": csrf},
        json={"is_excluded": True},
    )

    unacknowledged = client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": False},
    )
    assert unacknowledged.status_code == 422
    assert unacknowledged.json()["error"]["code"] == "WARNINGS_UNACKNOWLEDGED"

    confirmed = client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "confirmed"
    assert body["confirmed_by"]
    assert body["confirmed_at"]

    with SessionLocal() as db:
        guardians = list(db.scalars(select(Guardian)).all())
        contacts = list(db.scalars(select(GuardianContact)).all())
        students = list(db.scalars(select(Student)).all())
        relationships = list(db.scalars(select(GuardianStudentRelationship)).all())
        balances = list(db.scalars(select(FeeBalance)).all())
        excluded_row = db.get(StagedRow, negative["id"])

    assert len(guardians) == 5
    assert len(contacts) == 4
    assert len(students) == 6
    assert len(relationships) == 6
    assert len(balances) == 6
    assert excluded_row is not None and excluded_row.is_excluded is True

    balance_by_guardian = {balance.guardian_id: balance for balance in balances}
    assert {balance.currency for balance in balances} == {"SYP", "USD"}
    zero = next(balance for balance in balances if balance.remaining_balance_source == 0)
    assert zero.currency == "SYP"
    assert all(balance.import_batch_id == batch_id for balance in balances)
    assert all(balance.source_row_id for balance in balances)
    assert all(balance.record_status == "confirmed" for balance in balances)
    assert all(balance.reviewed_by for balance in balances)
    assert len(balance_by_guardian) == 5
    assert "import.confirm" in _audit_actions(batch_id)

    second = client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert second.status_code == 200
    assert second.json()["status"] == "confirmed"

    with SessionLocal() as db:
        assert len(list(db.scalars(select(FeeBalance)).all())) == 6
        assert len(list(db.scalars(select(Guardian)).all())) == 5


def test_confirm_blocks_blocking_errors_and_empty_batches(
    admin_client: tuple[TestClient, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, csrf = admin_client
    batch_id = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx").json()["id"]
    client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "الفصل الأول"},
    )
    blocked = client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "BLOCKING_ROWS"

    # This case exercises the empty-batch path, so keep OCR out of the way.
    monkeypatch.setattr(settings, "ocr_enabled", False)
    scanned = _upload(
        client, csrf, PDF_SAMPLES / "sample-02-scanned-image.pdf", mime=PDF_MIME
    ).json()
    no_rows = client.post(
        f"/api/v1/imports/{scanned['id']}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert no_rows.status_code == 409
    assert no_rows.json()["error"]["code"] == "NO_CONFIRMABLE_ROWS"


def test_list_cancel_and_state_transitions(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    batch_id = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx").json()["id"]

    listing = client.get(
        "/api/v1/imports", params={"status": "review_required"}
    ).json()
    assert listing["total"] >= 1
    assert any(item["id"] == batch_id for item in listing["items"])
    assert listing["page"] == 1

    cancelled = client.post(
        f"/api/v1/imports/{batch_id}/cancel",
        headers={"X-CSRF-Token": csrf},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"]
    assert cancelled.json()["updated_at"]
    assert "import.cancel" in _audit_actions(batch_id)

    again = client.post(
        f"/api/v1/imports/{batch_id}/cancel",
        headers={"X-CSRF-Token": csrf},
    )
    assert again.status_code == 200

    confirm = client.post(
        f"/api/v1/imports/{batch_id}/confirm",
        headers={"X-CSRF-Token": csrf},
        json={"acknowledge_warnings": True},
    )
    assert confirm.status_code == 409

    process = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "الفصل الأول"},
    )
    assert process.status_code == 409


def test_process_requires_worksheet_and_valid_mapping(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    batch_id = _upload_sample(client, csrf, "sample-01-multi-sheet.xlsx").json()["id"]

    auto_sheet = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={},
    )
    assert auto_sheet.status_code == 200, auto_sheet.text
    assert auto_sheet.json()["worksheet_name"] == "الفصل الأول"
    assert auto_sheet.json()["total_rows"] == 7

    invalid_sheet = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={"worksheet_name": "غير موجودة"},
    )
    assert invalid_sheet.status_code == 422
    assert invalid_sheet.json()["error"]["code"] == "INVALID_WORKSHEET"

    invalid_mapping = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={
            "worksheet_name": "الفصل الأول",
            "mapping": {"guardian_name": "عمود غير موجود"},
        },
    )
    assert invalid_mapping.status_code == 422
    assert invalid_mapping.json()["error"]["code"] == "INVALID_MAPPING"

    unknown_field = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={
            "worksheet_name": "الفصل الأول",
            "mapping": {"not_a_field": "اسم ولي الأمر"},
        },
    )
    assert unknown_field.status_code == 422
    assert unknown_field.json()["error"]["code"] == "INVALID_MAPPING"

    mapped = client.post(
        f"/api/v1/imports/{batch_id}/process",
        headers={"X-CSRF-Token": csrf},
        json={
            "worksheet_name": "الفصل الأول",
            "mapping": {"guardian_name": "اسم ولي الأمر"},
        },
    )
    assert mapped.status_code == 200, mapped.text
    mapping = mapped.json()["column_mapping"]
    assert mapping["guardian_name"] == "اسم ولي الأمر"
    assert mapping["remaining_balance"] == "المتبقي"


def test_upload_form_mapping_and_validation(
    admin_client: tuple[TestClient, str]
) -> None:
    client, csrf = admin_client
    response = _upload_sample(
        client,
        csrf,
        "sample-01-multi-sheet.xlsx",
        worksheet_name="الفصل الثاني",
        mapping=json.dumps({"guardian_name": "اسم ولي الأمر"}),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "review_required"
    assert body["total_rows"] == 3
    assert body["worksheet_name"] == "الفصل الثاني"

    bad_mapping = _upload_sample(
        client,
        csrf,
        "sample-02-arabic-digits.xlsx",
        mapping="{not json}",
    )
    assert bad_mapping.status_code == 422
    assert bad_mapping.json()["error"]["code"] == "INVALID_MAPPING"


def test_csrf_and_rbac(
    client: TestClient,
    staff_client: tuple[TestClient, str],
    admin_client: tuple[TestClient, str],
) -> None:
    unauthenticated = client.get("/api/v1/imports")
    assert unauthenticated.status_code == 401

    staff, staff_csrf = staff_client
    staff_upload = _upload_sample(staff, staff_csrf, "sample-01-multi-sheet.xlsx")
    assert staff_upload.status_code == 201

    without_csrf = staff.post(
        "/api/v1/imports",
        files={
            "file": (
                "sample-01-multi-sheet.xlsx",
                (XLSX_SAMPLES / "sample-01-multi-sheet.xlsx").read_bytes(),
                XLSX_MIME,
            )
        },
    )
    assert without_csrf.status_code == 403
    assert without_csrf.json()["error"]["code"] == "CSRF_INVALID"

    admin, admin_csrf = admin_client
    username = f"m2_must_change_{uuid4().hex[:8]}"
    created = admin.post(
        "/api/v1/users",
        headers={"X-CSRF-Token": admin_csrf},
        json={
            "username": username,
            "password": "MustChange!2026",
            "role": "staff",
        },
    )
    assert created.status_code == 201, created.text

    must_change = TestClient(client.app)
    login(must_change, username, "MustChange!2026")
    blocked = must_change.get("/api/v1/imports")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"
