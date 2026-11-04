from __future__ import annotations

import hashlib
import io
import os
import re
import zipfile
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from ..config import settings
from ..errors import ApiError

XLSX_EXT = ".xlsx"
PDF_EXT = ".pdf"
SUPPORTED_EXTENSIONS = (XLSX_EXT, PDF_EXT)

XLSX_CONTENT_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/octet-stream",
    "application/zip",
    "",
}
PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream", ""}

_FILENAME_UNSAFE = re.compile(r"[\x00-\x1f<>:\"/\\|?*]")

# Below this total uncompressed size a high ratio is harmless (tiny XML parts),
# so the compression-ratio guard only applies to larger archives.
_RATIO_FLOOR_BYTES = 1024 * 1024


def _archive_limit_details(
    *,
    members: int,
    total_uncompressed: int,
    largest_member: int,
    ratio: float,
) -> dict[str, int | float]:
    return {
        "members": members,
        "max_members": settings.xlsx_max_members,
        "total_uncompressed_bytes": total_uncompressed,
        "max_uncompressed_bytes": settings.xlsx_max_uncompressed_bytes,
        "largest_member_bytes": largest_member,
        "max_member_bytes": settings.xlsx_max_member_bytes,
        "compression_ratio": ratio,
        "max_compression_ratio": settings.xlsx_max_compression_ratio,
    }


def _check_archive_limits(archive: zipfile.ZipFile) -> None:
    """Reject oversized or highly compressed archives using only metadata.

    Nothing is extracted here, so the check cannot itself consume the memory it
    is meant to protect. Details contain counts and limits only, never member
    names or contents.
    """
    infos = archive.infolist()
    members = len(infos)
    total_uncompressed = sum(max(info.file_size, 0) for info in infos)
    total_compressed = sum(max(info.compress_size, 0) for info in infos)
    largest_member = max((max(info.file_size, 0) for info in infos), default=0)
    ratio = (
        float(total_uncompressed) / float(total_compressed)
        if total_compressed > 0
        else float(total_uncompressed)
    )

    def reject() -> None:
        _reject(
            "XLSX_ARCHIVE_LIMIT",
            "The XLSX archive exceeds the safe decompression limits.",
            _archive_limit_details(
                members=members,
                total_uncompressed=total_uncompressed,
                largest_member=largest_member,
                ratio=ratio,
            ),
        )

    if members > settings.xlsx_max_members:
        reject()
    if largest_member > settings.xlsx_max_member_bytes:
        reject()
    if total_uncompressed > settings.xlsx_max_uncompressed_bytes:
        reject()
    if (
        total_uncompressed >= _RATIO_FLOOR_BYTES
        and ratio > settings.xlsx_max_compression_ratio
    ):
        reject()


def safe_filename(filename: str | None) -> str:
    name = Path(filename or "statement.xlsx").name
    name = _FILENAME_UNSAFE.sub("_", name).strip()
    return name[:500] or "statement.xlsx"


def _reject(code: str, message_en: str, details=None) -> None:
    from ..imports.constants import MESSAGES_AR

    raise ApiError(422, code, MESSAGES_AR.get(code, message_en), message_en, details)


def validate_file(filename: str, content_type: str | None, data: bytes) -> str:
    """Validate extension, MIME type, magic bytes, and size. Returns the extension."""
    if not data:
        _reject("INVALID_FILE_TYPE", "The uploaded file is empty.")
    if len(data) > settings.upload_max_bytes:
        raise ApiError(
            413,
            "FILE_TOO_LARGE",
            f"حجم الملف أكبر من الحد المسموح ({settings.upload_max_bytes} بايت).",
            "The uploaded file exceeds the size limit.",
            {"max_bytes": settings.upload_max_bytes},
        )

    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        _reject("INVALID_FILE_TYPE", "Only .xlsx and .pdf statements are supported.")

    declared = (content_type or "").split(";", 1)[0].strip().lower()
    allowed_types = XLSX_CONTENT_TYPES if extension == XLSX_EXT else PDF_CONTENT_TYPES
    if declared not in allowed_types:
        _reject(
            "INVALID_FILE_TYPE",
            "The declared content type does not match a supported statement format.",
            {"content_type": declared},
        )

    if extension == PDF_EXT:
        if not data.startswith(b"%PDF-"):
            _reject("FILE_TYPE_MISMATCH", "The file does not contain a PDF header.")
        return PDF_EXT

    if data[:4] not in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"):
        _reject("FILE_TYPE_MISMATCH", "The file does not contain an XLSX (zip) header.")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            _check_archive_limits(archive)
            names = archive.namelist()
    except zipfile.BadZipFile:
        _reject("FILE_TYPE_MISMATCH", "The XLSX archive is corrupt.")
    if not any(name.startswith("xl/") for name in names):
        _reject("FILE_TYPE_MISMATCH", "The archive does not contain an Excel workbook.")
    return XLSX_EXT


def ensure_xlsx_file_safe(path: Path) -> None:
    """Apply the archive limits to an already-stored XLSX file before parsing."""
    try:
        with zipfile.ZipFile(path) as archive:
            _check_archive_limits(archive)
    except zipfile.BadZipFile:
        _reject("FILE_TYPE_MISMATCH", "The XLSX archive is corrupt.")



def file_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_private(data: bytes, extension: str) -> str:
    root = Path(settings.upload_dir).resolve()
    folder = root / "imports" / uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(folder, 0o700)
    except OSError:  # pragma: no cover - platform dependent
        pass

    target = folder / f"{uuid4().hex}{extension}"
    with open(target, "xb") as handle:
        handle.write(data)
    try:
        os.chmod(target, 0o600)
    except OSError:  # pragma: no cover - platform dependent
        pass

    if root not in target.resolve().parents:
        raise ApiError(400, "INVALID_PATH", "مسار الملف غير صالح.", "Invalid file path.")
    return target.resolve().relative_to(root).as_posix()


def resolve_storage_path(storage_key: str) -> Path:
    root = Path(settings.upload_dir).resolve()
    candidate = (root / storage_key).resolve()
    if candidate != root and root not in candidate.parents:
        raise ApiError(400, "INVALID_PATH", "مسار الملف غير صالح.", "Invalid file path.")
    return candidate


async def read_upload(file: UploadFile) -> bytes:
    data = await file.read(settings.upload_max_bytes + 1)
    if len(data) > settings.upload_max_bytes:
        raise ApiError(
            413,
            "FILE_TOO_LARGE",
            f"حجم الملف أكبر من الحد المسموح ({settings.upload_max_bytes} بايت).",
            "The uploaded file exceeds the size limit.",
            {"max_bytes": settings.upload_max_bytes},
        )
    return data
