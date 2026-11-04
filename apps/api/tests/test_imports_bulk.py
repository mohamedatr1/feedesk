from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import delete, select

from app.config import settings
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

from .conftest import SessionLocal

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

STANDARD_HEADERS = [
    "اسم ولي الأمر",
    "رقم الهاتف",
    "اسم الطالب",
    "إجمالي القسط",
    "المدفوع",
    "المتبقي",
    "العملة",
]


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


def _make_workbook(path: Path, rows: list[list[object]]) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "البيانات"
    sheet.append(STANDARD_HEADERS)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return path


def _upload(client: TestClient, csrf: str, path: Path):
    with path.open("rb") as handle:
        return client.post(
            "/api/v1/imports",
            headers={"X-CSRF-Token": csrf},
            files={"file": (path.name, handle, XLSX_MIME)},
        )


def _bulk(
    client: TestClient,
    csrf: str,
    batch_id: str,
    *,
    is_excluded: bool,
    scope: str,
    row_ids: list[str] | None = None,
):
    return client.post(
        f"/api/v1/imports/{batch_id}/rows/exclusion",
        headers={"X-CSRF-Token": csrf},
        json={
            "is_excluded": is_excluded,
            "scope": scope,
            "row_ids": row_ids or [],
        },
    )


def _rows(client: TestClient, batch_id: str, status: str | None = None) -> list[dict]:
    params = {"status": status} if status else None
    response = client.get(f"/api/v1/imports/{batch_id}/rows", params=params)
    assert response.status_code == 200, response.text
    return response.json()["items"]


def _audit_events(batch_id: str, action: str) -> list[AuditEvent]:
    with SessionLocal() as db:
        return list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.entity_id == batch_id,
                    AuditEvent.action == action,
                )
            ).all()
        )


def test_selected_bulk_exclude_and_restore(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "selected.xlsx",
        [
            ["ولي أمر ألف", "0993100001", "طالب ألف", 1000, 400, 600, "SYP"],
            ["ولي أمر باء", "0993100002", "طالب باء", 1000, 500, 500, "SYP"],
            ["ولي أمر جيم", "0993100003", "طالب جيم", 1000, 250, 750, "SYP"],
        ],
    )
    body = _upload(client, csrf, path).json()
    assert body["status"] == "ready_to_confirm"
    rows = _rows(client, body["id"])
    picked = [rows[0]["id"], rows[2]["id"]]

    excluded = _bulk(
        client,
        csrf,
        body["id"],
        is_excluded=True,
        scope="selected",
        row_ids=picked,
    )
    assert excluded.status_code == 200, excluded.text
    detail = excluded.json()
    assert detail["excluded_rows"] == 2
    assert detail["valid_rows"] == 1
    assert detail["total_rows"] == 3
    assert detail["status"] == "ready_to_confirm"

    excluded_rows = _rows(client, body["id"], status="excluded")
    assert {row["id"] for row in excluded_rows} == set(picked)
    assert all(row["validation_status"] == "excluded" for row in excluded_rows)

    restored = _bulk(
        client,
        csrf,
        body["id"],
        is_excluded=False,
        scope="selected",
        row_ids=picked,
    )
    assert restored.status_code == 200, restored.text
    detail = restored.json()
    assert detail["excluded_rows"] == 0
    assert detail["valid_rows"] == 3
    assert detail["total_rows"] == 3

    rows_after = _rows(client, body["id"])
    assert all(row["is_excluded"] is False for row in rows_after)
    assert all(row["validation_status"] != "excluded" for row in rows_after)


def test_invalid_scope_excludes_all_invalid_rows(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "invalid-scope.xlsx",
        [
            ["ولي أمر صالح", "0993200001", "طالب صالح", 1000, 400, 600, "SYP"],
            ["ولي أمر سالب أ", "0993200002", "طالب سالب أ", 1000, 1200, -200, "SYP"],
            ["ولي أمر سالب ب", "0993200003", "طالب سالب ب", 1000, 1300, -300, "SYP"],
        ],
    )
    body = _upload(client, csrf, path).json()
    assert body["status"] == "review_required"
    assert body["invalid_rows"] == 2
    assert body["excluded_rows"] == 0

    response = _bulk(client, csrf, body["id"], is_excluded=True, scope="invalid")
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["invalid_rows"] == 0
    assert detail["excluded_rows"] == 2
    assert detail["valid_rows"] == 1
    assert detail["status"] == "ready_to_confirm"

    assert _rows(client, body["id"], status="invalid") == []
    excluded = _rows(client, body["id"], status="excluded")
    assert len(excluded) == 2
    assert all(row["validation_status"] == "excluded" for row in excluded)

    # The invalid selector is a one-shot cleanup: nothing invalid remains.
    again = _bulk(client, csrf, body["id"], is_excluded=True, scope="invalid")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "NO_ROWS_TO_EXCLUDE"


def test_bulk_exclusion_rejects_rows_from_another_batch(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    first = _upload(
        client,
        csrf,
        _make_workbook(
            tmp_path / "first.xlsx",
            [["ولي أمر أول", "0993300001", "طالب أول", 1000, 400, 600, "SYP"]],
        ),
    ).json()
    second = _upload(
        client,
        csrf,
        _make_workbook(
            tmp_path / "second.xlsx",
            [["ولي أمر ثان", "0993300002", "طالب ثان", 1000, 400, 600, "SYP"]],
        ),
    ).json()
    first_rows = _rows(client, first["id"])
    foreign_row = _rows(client, second["id"])[0]["id"]

    rejected = _bulk(
        client,
        csrf,
        first["id"],
        is_excluded=True,
        scope="selected",
        row_ids=[first_rows[0]["id"], foreign_row],
    )
    assert rejected.status_code == 404
    assert rejected.json()["error"]["code"] == "ROW_NOT_FOUND"
    assert rejected.json()["error"]["details"]["row_ids"] == [foreign_row]

    # The whole request is rejected before any row changes.
    detail = client.get(f"/api/v1/imports/{first['id']}").json()
    assert detail["excluded_rows"] == 0
    assert all(row["is_excluded"] is False for row in _rows(client, first["id"]))


def test_bulk_exclusion_is_idempotent_and_writes_one_event(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "idempotent.xlsx",
        [
            ["ولي أمر واحد", "0993400001", "طالب واحد", 1000, 400, 600, "SYP"],
            ["ولي أمر اثنان", "0993400002", "طالب اثنان", 1000, 300, 700, "SYP"],
            ["ولي أمر ثلاثة", "0993400003", "طالب ثلاثة", 1000, 200, 800, "SYP"],
        ],
    )
    body = _upload(client, csrf, path).json()
    picked = [row["id"] for row in _rows(client, body["id"])]

    first = _bulk(
        client,
        csrf,
        body["id"],
        is_excluded=True,
        scope="selected",
        row_ids=picked,
    )
    assert first.status_code == 200, first.text
    assert first.json()["excluded_rows"] == 3

    repeat = _bulk(
        client,
        csrf,
        body["id"],
        is_excluded=True,
        scope="selected",
        row_ids=picked,
    )
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["excluded_rows"] == 3

    exclude_events = _audit_events(body["id"], "import.rows.bulk_exclude")
    assert len(exclude_events) == 1
    after = exclude_events[0].after_data or {}
    assert after["scope"] == "selected"
    assert after["excluded_count"] == 3
    assert sorted(after["row_ids_sample"]) == sorted(picked)
    assert _audit_events(body["id"], "import.row.update") == []

    restored = _bulk(
        client,
        csrf,
        body["id"],
        is_excluded=False,
        scope="selected",
        row_ids=picked,
    )
    assert restored.status_code == 200
    assert restored.json()["excluded_rows"] == 0
    repeat_restore = _bulk(
        client,
        csrf,
        body["id"],
        is_excluded=False,
        scope="selected",
        row_ids=picked,
    )
    assert repeat_restore.status_code == 200

    restore_events = _audit_events(body["id"], "import.rows.bulk_restore")
    assert len(restore_events) == 1
    assert (restore_events[0].after_data or {})["excluded_count"] == 3
    assert len(_audit_events(body["id"], "import.rows.bulk_exclude")) == 1


def test_bulk_exclusion_refreshes_counts_and_status(
    admin_client: tuple[TestClient, str], tmp_path: Path
) -> None:
    client, csrf = admin_client
    path = _make_workbook(
        tmp_path / "duplicates.xlsx",
        [
            ["ولي أمر مكرر", "0993500001", "طالب مكرر", 1000, 400, 600, "SYP"],
            ["ولي أمر مكرر", "0993500001", "طالب مكرر", 1000, 400, 600, "SYP"],
        ],
    )
    body = _upload(client, csrf, path).json()
    assert body["status"] == "review_required"
    assert body["invalid_rows"] == 1
    assert body["duplicate_rows"] == 1
    assert body["totals_by_currency"] == {"SYP": "600.00"}

    response = _bulk(client, csrf, body["id"], is_excluded=True, scope="invalid")
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["duplicate_rows"] == 0
    assert detail["invalid_rows"] == 0
    assert detail["excluded_rows"] == 1
    assert detail["valid_rows"] == 1
    assert detail["total_rows"] == 2
    assert detail["status"] == "ready_to_confirm"
    assert detail["totals_by_currency"] == {"SYP": "600.00"}

    refreshed = client.get(f"/api/v1/imports/{body['id']}").json()
    assert refreshed["excluded_rows"] == 1
    assert refreshed["status"] == "ready_to_confirm"


def test_bulk_exclusion_permissions_and_csrf(
    client: TestClient,
    staff_client: tuple[TestClient, str],
    tmp_path: Path,
) -> None:
    staff, staff_csrf = staff_client
    path = _make_workbook(
        tmp_path / "staff.xlsx",
        [["ولي أمر موظف", "0993600001", "طالب موظف", 1000, 400, 600, "SYP"]],
    )
    body = _upload(staff, staff_csrf, path).json()
    staff_rows = _rows(staff, body["id"])

    anonymous = client.post(
        f"/api/v1/imports/{body['id']}/rows/exclusion",
        json={
            "is_excluded": True,
            "scope": "selected",
            "row_ids": [staff_rows[0]["id"]],
        },
    )
    assert anonymous.status_code == 401

    without_csrf = staff.post(
        f"/api/v1/imports/{body['id']}/rows/exclusion",
        json={
            "is_excluded": True,
            "scope": "selected",
            "row_ids": [staff_rows[0]["id"]],
        },
    )
    assert without_csrf.status_code == 403
    assert without_csrf.json()["error"]["code"] == "CSRF_INVALID"

    allowed = _bulk(
        staff,
        staff_csrf,
        body["id"],
        is_excluded=True,
        scope="selected",
        row_ids=[staff_rows[0]["id"]],
    )
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["excluded_rows"] == 1
    assert len(_audit_events(body["id"], "import.rows.bulk_exclude")) == 1
