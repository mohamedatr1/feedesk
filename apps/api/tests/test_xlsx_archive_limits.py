from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.config import settings
from app.errors import ApiError
from app.imports import storage
from app.models import (
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

SAMPLES = Path(__file__).resolve().parent / "fixtures" / "xlsx"
SAMPLE = SAMPLES / "sample-02-arabic-digits.xlsx"
XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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


@pytest.fixture()
def import_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path / "uploads"))
    _clean_import_tables()
    yield
    _clean_import_tables()


def _synthetic_xlsx(*, member_size: int = 4096) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/workbook.xml", b"0" * member_size)
    return buffer.getvalue()


def _assert_archive_limit(error: ApiError) -> None:
    assert error.status_code == 422
    assert error.code == "XLSX_ARCHIVE_LIMIT"
    assert error.message_ar == "أرشيف XLSX يتجاوز حدود الحجم الآمن."
    assert isinstance(error.details, dict)
    serialized = str(error.details)
    assert "xl/" not in serialized


def test_validate_file_rejects_excessive_member_count(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "xlsx_max_members", 1)
    data = SAMPLE.read_bytes()

    with pytest.raises(ApiError) as excinfo:
        storage.validate_file(SAMPLE.name, XLSX_MIME, data)

    _assert_archive_limit(excinfo.value)


def test_validate_file_rejects_oversized_member(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "xlsx_max_member_bytes", 1024)
    data = _synthetic_xlsx(member_size=4096)

    with pytest.raises(ApiError) as excinfo:
        storage.validate_file("book.xlsx", XLSX_MIME, data)

    _assert_archive_limit(excinfo.value)


def test_validate_file_rejects_excessive_total_size(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "xlsx_max_uncompressed_bytes", 1024)
    data = _synthetic_xlsx(member_size=4096)

    with pytest.raises(ApiError) as excinfo:
        storage.validate_file("book.xlsx", XLSX_MIME, data)

    _assert_archive_limit(excinfo.value)


def test_validate_file_rejects_high_compression_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "xlsx_max_compression_ratio", 2.0)
    data = _synthetic_xlsx(member_size=2 * 1024 * 1024)

    with pytest.raises(ApiError) as excinfo:
        storage.validate_file("book.xlsx", XLSX_MIME, data)

    _assert_archive_limit(excinfo.value)


def test_small_legitimate_archive_is_not_rejected_by_ratio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A tiny, highly compressible workbook is below the ratio floor.
    monkeypatch.setattr(settings, "xlsx_max_compression_ratio", 1.0)
    data = _synthetic_xlsx(member_size=1024)

    assert storage.validate_file("book.xlsx", XLSX_MIME, data) == ".xlsx"


def test_validate_file_accepts_normal_fixture() -> None:
    assert storage.validate_file(SAMPLE.name, XLSX_MIME, SAMPLE.read_bytes()) == ".xlsx"


def test_ensure_xlsx_file_safe_rejects_stored_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "xlsx_max_members", 1)

    with pytest.raises(ApiError) as excinfo:
        storage.ensure_xlsx_file_safe(SAMPLE)

    _assert_archive_limit(excinfo.value)


def test_ensure_xlsx_file_safe_accepts_normal_fixture() -> None:
    storage.ensure_xlsx_file_safe(SAMPLE)


def test_upload_rejects_archive_limit_and_creates_no_import(
    admin_client: tuple[TestClient, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, csrf = admin_client
    monkeypatch.setattr(settings, "xlsx_max_members", 1)

    with SAMPLE.open("rb") as handle:
        response = client.post(
            "/api/v1/imports",
            headers={"X-CSRF-Token": csrf},
            files={"file": (SAMPLE.name, handle, XLSX_MIME)},
        )

    assert response.status_code == 422, response.text
    error = response.json()["error"]
    assert error["code"] == "XLSX_ARCHIVE_LIMIT"
    assert error["message_ar"] == "أرشيف XLSX يتجاوز حدود الحجم الآمن."

    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ImportBatch)) == 0
        assert db.scalar(select(func.count()).select_from(SourceFile)) == 0
