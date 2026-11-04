from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import Request
from sqlalchemy import Text, cast, delete, func, or_, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import settings
from ..errors import ApiError
from ..models import (
    FeeBalance,
    Guardian,
    GuardianContact,
    GuardianStudentRelationship,
    ImportBatch,
    SchoolSettings,
    SourceFile,
    StagedRow,
    Student,
    User,
)
from ..privacy import mask_phone
from . import storage
from .constants import (
    EDITABLE_NORMALIZED_FIELDS,
    MESSAGES_AR,
    REQUIRED_FIELDS,
)
from .errors import ImportParseError
from .normalization import InvalidMappingError, clean_text, normalize_name_key
from .parsing import ParsedDocument, list_xlsx_sheets, parse_pdf, parse_xlsx
from .validation import apply_normalized_patch, revalidate_batch

CANCELLABLE_STATUSES = {
    "uploaded",
    "processing",
    "review_required",
    "ready_to_confirm",
    "failed",
}

_MAX_AVAILABLE_HEADERS = 200


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_batch(db: Session, batch_id: str, *, lock: bool = False) -> ImportBatch:
    statement = select(ImportBatch).where(ImportBatch.id == batch_id)
    if lock:
        statement = statement.with_for_update()
    batch = db.scalar(statement)
    if batch is None:
        raise ApiError(
            404,
            "IMPORT_NOT_FOUND",
            "عملية الاستيراد غير موجودة.",
            "Import batch not found.",
        )
    return batch


def source_file_for(db: Session, batch_id: str) -> SourceFile | None:
    return db.scalar(select(SourceFile).where(SourceFile.import_batch_id == batch_id))


def _warnings(batch: ImportBatch) -> list[dict[str, Any]]:
    return list(batch.warnings or [])


def _uploader_name(db: Session, user_id: str | None) -> str | None:
    if not user_id:
        return None
    return db.scalar(select(User.username).where(User.id == user_id))


def batch_summary(db: Session, batch: ImportBatch) -> dict[str, Any]:
    return {
        "id": batch.id,
        "source_filename": batch.source_filename,
        "file_type": batch.file_type,
        "status": batch.status,
        "worksheet_name": batch.worksheet_name,
        "available_sheets": list(batch.available_sheets or []),
        "total_rows": batch.total_rows,
        "valid_rows": batch.valid_rows,
        "invalid_rows": batch.invalid_rows,
        "duplicate_rows": batch.duplicate_rows,
        "excluded_rows": batch.excluded_rows,
        "totals_by_currency": dict(batch.totals_by_currency or {}),
        "max_upload_mb": round(settings.upload_max_bytes / (1024 * 1024), 2),
        "warnings": _warnings(batch),
        "uploaded_by": batch.uploaded_by,
        "uploaded_by_name": _uploader_name(db, batch.uploaded_by),
        "created_at": batch.created_at,
        "updated_at": batch.updated_at,
        "confirmed_at": batch.confirmed_at,
        "cancelled_at": batch.cancelled_at,
    }


def available_headers(db: Session, batch: ImportBatch) -> list[str]:
    """Return source header names only, never cell values.

    The staged rows keep their original header keys server-side so the mapping
    UI can offer manual matching without re-exposing ``raw_data`` values.
    """
    names: set[str] = set()
    for (raw,) in db.execute(
        select(StagedRow.raw_data).where(StagedRow.import_batch_id == batch.id)
    ):
        if isinstance(raw, dict):
            for header in raw:
                text = clean_text(header)
                if text:
                    names.add(text)
    for header in (batch.column_mapping or {}).values():
        text = clean_text(header)
        if text:
            names.add(text)
    return sorted(names)[:_MAX_AVAILABLE_HEADERS]


def batch_detail(db: Session, batch: ImportBatch) -> dict[str, Any]:
    source = source_file_for(db, batch.id)
    payload = batch_summary(db, batch)
    payload.update(
        {
            "source_file_id": source.id if source else None,
            "available_headers": available_headers(db, batch),
            "column_mapping": dict(batch.column_mapping or {}),
            "error_summary": batch.error_summary,
            "confirmed_by": batch.confirmed_by,
            "duplicate_reason": batch.duplicate_reason,
        }
    )
    return payload


def row_payload(row: StagedRow) -> dict[str, Any]:
    return {
        "id": row.id,
        "source_row_number": row.source_row_number,
        "source_page_number": row.source_page_number,
        "normalized_data": row.normalized_data or {},
        "validation_status": row.validation_status,
        "validation_errors": list(row.validation_errors or []),
        "is_excluded": bool(row.is_excluded),
        "guardian_resolution_mode": row.guardian_resolution_mode or "auto",
        "resolved_guardian_id": row.resolved_guardian_id,
    }


def _stage(db: Session, batch: ImportBatch, document: ParsedDocument) -> None:
    batch.available_sheets = document.available_sheets
    batch.worksheet_name = document.worksheet_name
    batch.warnings = document.warnings
    batch.column_mapping = document.mapping
    batch.status = "processing"
    batch.updated_at = _now()

    for position, parsed in enumerate(document.rows):
        db.add(
            StagedRow(
                id=str(uuid4()),
                import_batch_id=batch.id,
                source_row_number=parsed.source_row_number,
                source_page_number=parsed.source_page_number,
                position=position,
                raw_data=parsed.raw_data,
                normalized_data={},
                parser_warnings=parsed.warnings,
                validation_status="pending",
                validation_errors=[],
                is_excluded=False,
            )
        )
    db.flush()
    revalidate_batch(db, batch)


def _default_currency(db: Session) -> str:
    school = db.get(SchoolSettings, 1)
    currency = (school.default_currency if school else None) or settings.seed_currency
    return str(currency).strip() or settings.seed_currency


def _parse_error_details(exc: ImportParseError) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": exc.code, "message_ar": exc.message_ar}
    if exc.details is not None:
        payload["details"] = exc.details
    return payload


def create_import(
    db: Session,
    *,
    request: Request,
    user: User,
    filename: str,
    content_type: str | None,
    data: bytes,
    worksheet_name: str | None,
    mapping: dict[str, str] | None,
    force_duplicate: bool,
    duplicate_reason: str | None,
) -> ImportBatch:
    safe_name = storage.safe_filename(filename)
    extension = storage.validate_file(safe_name, content_type, data)
    digest = storage.file_sha256(data)

    existing = db.scalar(
        select(ImportBatch)
        .where(
            ImportBatch.file_hash == digest,
            ImportBatch.status.notin_(("cancelled", "failed")),
        )
        .order_by(ImportBatch.created_at.desc())
        .limit(1)
    )
    if existing is not None:
        if not force_duplicate:
            raise ApiError(
                409,
                "DUPLICATE_FILE",
                MESSAGES_AR["DUPLICATE_FILE"],
                "A file with the same SHA-256 hash was already imported.",
                {"existing_import_id": existing.id},
            )
        if not (duplicate_reason or "").strip():
            raise ApiError(
                422,
                "DUPLICATE_REASON_REQUIRED",
                MESSAGES_AR["DUPLICATE_REASON_REQUIRED"],
                "duplicate_reason is required when forcing a duplicate import.",
            )

    storage_key = storage.save_private(data, extension)
    batch_id = str(uuid4())
    batch = ImportBatch(
        id=batch_id,
        source_filename=safe_name,
        file_hash=digest,
        file_type=extension.lstrip("."),
        uploaded_by=user.id,
        status="uploaded",
        worksheet_name=None,
        duplicate_reason=(duplicate_reason or "").strip() or None,
    )
    db.add(batch)
    db.add(
        SourceFile(
            id=str(uuid4()),
            import_batch_id=batch_id,
            storage_key=storage_key,
            original_filename=safe_name,
            content_type=(
                "application/pdf" if extension == storage.PDF_EXT else
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            file_size=len(data),
            sha256_hash=digest,
            uploaded_by=user.id,
        )
    )
    db.flush()

    if existing is not None:
        record_audit(
            db,
            request=request,
            actor_user_id=user.id,
            action="import.duplicate_override",
            entity_type="import_batch",
            entity_id=batch.id,
            after={
                "existing_import_id": existing.id,
                "duplicate_reason": batch.duplicate_reason,
                "file_hash": digest,
            },
        )

    source = source_file_for(db, batch.id)
    if source is None:  # pragma: no cover - defensive
        raise ApiError(
            500,
            "INTERNAL_ERROR",
            "تعذر الوصول إلى الملف المرفوع.",
            "The stored source file record is missing.",
        )
    file_path = storage.resolve_storage_path(source.storage_key)
    try:
        if batch.file_type == "xlsx":
            sheets = list_xlsx_sheets(file_path)
            if worksheet_name and worksheet_name not in sheets:
                raise ApiError(
                    422,
                    "INVALID_WORKSHEET",
                    MESSAGES_AR["INVALID_WORKSHEET"],
                    "The requested worksheet does not exist.",
                    {"available_sheets": sheets},
                )
            document = parse_xlsx(
                file_path,
                worksheet_name=worksheet_name,
                mapping=mapping,
                max_rows=settings.import_max_rows,
                default_currency=_default_currency(db),
            )
        else:
            document = parse_pdf(
                file_path,
                mapping=mapping,
                max_pages=settings.import_max_pages,
                default_currency=_default_currency(db),
            )
    except ImportParseError as exc:
        batch.status = "failed"
        batch.error_summary = _parse_error_details(exc)
        batch.warnings = []
        batch.updated_at = _now()
        record_audit(
            db,
            request=request,
            actor_user_id=user.id,
            action="import.upload",
            entity_type="import_batch",
            entity_id=batch.id,
            after={
                "source_filename": batch.source_filename,
                "file_type": batch.file_type,
                "status": "failed",
                "error_code": exc.code,
            },
        )
        db.commit()
        return batch
    except InvalidMappingError as exc:
        raise ApiError(
            422,
            "INVALID_MAPPING",
            MESSAGES_AR["INVALID_MAPPING"],
            "The column mapping references an unknown source header.",
            {"header": exc.header},
        ) from exc

    _stage(db, batch, document)

    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="import.upload",
        entity_type="import_batch",
        entity_id=batch.id,
        after={
            "source_filename": batch.source_filename,
            "file_type": batch.file_type,
            "file_hash": digest,
            "status": batch.status,
            "worksheet_name": batch.worksheet_name,
        },
    )
    db.commit()
    db.refresh(batch)
    return batch


def process_import(
    db: Session,
    batch: ImportBatch,
    *,
    request: Request,
    user: User,
    worksheet_name: str | None,
    mapping: dict[str, str] | None,
) -> ImportBatch:
    if batch.status in {"confirmed", "cancelled"}:
        raise ApiError(
            409,
            "IMPORT_STATE_INVALID",
            MESSAGES_AR["IMPORT_STATE_INVALID"],
            "The import cannot be processed in its current state.",
            {"status": batch.status},
        )

    source = source_file_for(db, batch.id)
    if source is None:
        raise ApiError(
            404,
            "IMPORT_NOT_FOUND",
            MESSAGES_AR["IMPORT_NOT_FOUND"],
            "The source file for this import is missing.",
        )
    file_path = storage.resolve_storage_path(source.storage_key)
    if not file_path.is_file():
        raise ApiError(
            404,
            "IMPORT_NOT_FOUND",
            MESSAGES_AR["IMPORT_NOT_FOUND"],
            "The source file for this import is missing.",
        )

    selected = worksheet_name or batch.worksheet_name
    try:
        if batch.file_type == "xlsx":
            sheets = list_xlsx_sheets(file_path)
            if selected and selected not in sheets:
                raise ApiError(
                    422,
                    "INVALID_WORKSHEET",
                    MESSAGES_AR["INVALID_WORKSHEET"],
                    "The requested worksheet does not exist.",
                    {"available_sheets": sheets},
                )
            document = parse_xlsx(
                file_path,
                worksheet_name=selected,
                mapping=mapping,
                max_rows=settings.import_max_rows,
                default_currency=_default_currency(db),
            )
        else:
            document = parse_pdf(
                file_path,
                mapping=mapping,
                max_pages=settings.import_max_pages,
                default_currency=_default_currency(db),
            )
    except ImportParseError as exc:
        batch.status = "failed"
        batch.error_summary = _parse_error_details(exc)
        batch.updated_at = _now()
        db.commit()
        return batch
    except InvalidMappingError as exc:
        raise ApiError(
            422,
            "INVALID_MAPPING",
            MESSAGES_AR["INVALID_MAPPING"],
            "The column mapping references an unknown source header.",
            {"header": exc.header},
        ) from exc

    db.execute(delete(StagedRow).where(StagedRow.import_batch_id == batch.id))
    db.flush()
    _stage(db, batch, document)

    missing_required = sorted(
        field for field in REQUIRED_FIELDS if not (batch.column_mapping or {}).get(field)
    )
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="import.process",
        entity_type="import_batch",
        entity_id=batch.id,
        after={
            "worksheet_name": batch.worksheet_name,
            "column_mapping": batch.column_mapping,
            "total_rows": batch.total_rows,
            "invalid_rows": batch.invalid_rows,
            "missing_required_fields": missing_required,
        },
    )
    db.commit()
    db.refresh(batch)
    return batch


def update_row(
    db: Session,
    batch: ImportBatch,
    row: StagedRow,
    *,
    request: Request,
    user: User,
    normalized_data: dict[str, Any] | None,
    is_excluded: bool | None,
    guardian_resolution: dict[str, Any] | None = None,
) -> StagedRow:
    if batch.status not in {"review_required", "ready_to_confirm"}:
        raise ApiError(
            409,
            "IMPORT_STATE_INVALID",
            MESSAGES_AR["IMPORT_STATE_INVALID"],
            "Rows can only be edited while the import is under review.",
            {"status": batch.status},
        )

    changed: list[str] = []
    before_data = dict(row.normalized_data or {})
    before_excluded = bool(row.is_excluded)
    before_mode = row.guardian_resolution_mode or "auto"
    before_guardian_id = row.resolved_guardian_id
    resolution_changed = False
    if normalized_data is not None:
        unknown = sorted(set(normalized_data) - EDITABLE_NORMALIZED_FIELDS)
        if unknown:
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                "حقول غير قابلة للتعديل في بيانات الصف.",
                "Unsupported normalized_data fields.",
                {"fields": unknown},
            )
        changed.extend(apply_normalized_patch(row, normalized_data))
    if guardian_resolution is not None:
        mode = str(guardian_resolution.get("mode") or "auto")
        if mode not in {"auto", "link_existing", "create_new"}:
            raise ApiError(
                422,
                "VALIDATION_ERROR",
                "وضع مطابقة ولي الأمر غير صالح.",
                "Invalid guardian resolution mode.",
                {"mode": mode},
            )
        target_id: str | None = None
        if mode == "link_existing":
            target_id = str(guardian_resolution.get("guardian_id") or "").strip() or None
            if target_id is None:
                raise ApiError(
                    422,
                    "VALIDATION_ERROR",
                    "يجب اختيار ولي الأمر المطلوب ربطه.",
                    "guardian_id is required for link_existing.",
                )
            guardian = db.get(Guardian, target_id)
            if guardian is None:
                raise ApiError(
                    404,
                    "GUARDIAN_NOT_FOUND",
                    "ولي الأمر غير موجود.",
                    "Guardian not found.",
                    {"guardian_id": target_id},
                )
            if guardian.status != "active":
                raise ApiError(
                    409,
                    "GUARDIAN_INACTIVE",
                    "ولي الأمر غير نشط.",
                    "The guardian is not active.",
                    {"guardian_id": target_id},
                )
        if mode != row.guardian_resolution_mode or target_id != row.resolved_guardian_id:
            row.guardian_resolution_mode = mode
            row.resolved_guardian_id = target_id
            changed.append("guardian_resolution")
            resolution_changed = True
    if is_excluded is not None and bool(row.is_excluded) != is_excluded:
        row.is_excluded = is_excluded
        changed.append("is_excluded")

    if not changed:
        return row

    row.reviewed_by = user.id
    row.reviewed_at = _now()
    db.flush()
    revalidate_batch(db, batch)
    batch.updated_at = _now()
    data_fields = [field for field in changed if field not in {"is_excluded", "guardian_resolution"}]
    if data_fields or "is_excluded" in changed:
        record_audit(
            db,
            request=request,
            actor_user_id=user.id,
            action="import.row.update",
            entity_type="import_batch",
            entity_id=batch.id,
            before={
                "row_id": row.id,
                "normalized_data": {
                    field: before_data.get(field) for field in data_fields
                },
                "is_excluded": before_excluded,
            },
            after={
                "row_id": row.id,
                "changed_fields": [
                    field for field in changed if field != "guardian_resolution"
                ],
                "normalized_data": {
                    field: (row.normalized_data or {}).get(field) for field in data_fields
                },
                "is_excluded": bool(row.is_excluded),
            },
        )
    if resolution_changed:
        record_audit(
            db,
            request=request,
            actor_user_id=user.id,
            action="import.guardian.resolve",
            entity_type="import_batch",
            entity_id=batch.id,
            before={
                "row_id": row.id,
                "mode": before_mode,
                "guardian_id": before_guardian_id,
            },
            after={
                "row_id": row.id,
                "mode": row.guardian_resolution_mode,
                "guardian_id": row.resolved_guardian_id,
            },
        )
    db.commit()
    db.refresh(batch)
    db.refresh(row)
    return row


def bulk_set_row_exclusion(
    db: Session,
    batch: ImportBatch,
    *,
    request: Request,
    user: User,
    is_excluded: bool,
    scope: str,
    row_ids: list[str],
) -> ImportBatch:
    """Exclude or restore many staged rows in one transaction.

    ``scope="invalid"`` selects every non-excluded invalid row in the batch.
    ``scope="selected"`` uses the supplied row ids, which must all belong to the
    batch.  A no-op repeat (all selected rows already in the requested state) is
    accepted without writing a second audit event, so the endpoint is idempotent.
    """
    if batch.status not in {"review_required", "ready_to_confirm"}:
        raise ApiError(
            409,
            "IMPORT_STATE_INVALID",
            MESSAGES_AR["IMPORT_STATE_INVALID"],
            "Rows can only be edited while the import is under review.",
            {"status": batch.status},
        )

    if scope == "invalid":
        selected = list(
            db.scalars(
                select(StagedRow)
                .where(
                    StagedRow.import_batch_id == batch.id,
                    StagedRow.is_excluded.is_(False),
                    StagedRow.validation_status == "invalid",
                )
                .order_by(StagedRow.position.asc(), StagedRow.id.asc())
            ).all()
        )
    else:
        unique_ids = list(dict.fromkeys(row_ids))
        if not unique_ids:
            selected = []
        else:
            found = list(
                db.scalars(
                    select(StagedRow).where(
                        StagedRow.import_batch_id == batch.id,
                        StagedRow.id.in_(unique_ids),
                    )
                ).all()
            )
            found_by_id = {row.id: row for row in found}
            missing = [row_id for row_id in unique_ids if row_id not in found_by_id]
            if missing:
                raise ApiError(
                    404,
                    "ROW_NOT_FOUND",
                    "الصف غير موجود.",
                    "Staged row not found in this import.",
                    {"row_ids": missing[:50]},
                )
            selected = [found_by_id[row_id] for row_id in unique_ids]

    if not selected:
        raise ApiError(
            409,
            "NO_ROWS_TO_EXCLUDE",
            "لا توجد صفوف مطابقة للاستثناء.",
            "No rows matched the bulk exclusion selector.",
            {"scope": scope},
        )

    targets = [row for row in selected if bool(row.is_excluded) != is_excluded]
    if not targets:
        return batch

    for row in targets:
        row.is_excluded = is_excluded
    db.flush()
    revalidate_batch(db, batch)
    batch.updated_at = _now()
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action=(
            "import.rows.bulk_exclude"
            if is_excluded
            else "import.rows.bulk_restore"
        ),
        entity_type="import_batch",
        entity_id=batch.id,
        after={
            "scope": scope,
            "excluded_count": len(targets),
            "row_ids_sample": [row.id for row in targets][:50],
        },
    )
    db.commit()
    db.refresh(batch)
    return batch


def cancel_import(
    db: Session,
    batch: ImportBatch,
    *,
    request: Request,
    user: User,
) -> ImportBatch:
    if batch.status == "cancelled":
        return batch
    if batch.status not in CANCELLABLE_STATUSES:
        raise ApiError(
            409,
            "IMPORT_STATE_INVALID",
            MESSAGES_AR["IMPORT_STATE_INVALID"],
            "The import cannot be cancelled in its current state.",
            {"status": batch.status},
        )
    batch.status = "cancelled"
    batch.cancelled_at = _now()
    batch.updated_at = batch.cancelled_at
    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="import.cancel",
        entity_type="import_batch",
        entity_id=batch.id,
        after={"status": "cancelled"},
    )
    db.commit()
    db.refresh(batch)
    return batch


def _row_name_key(row: StagedRow) -> str:
    data = row.normalized_data or {}
    name = str(data.get("guardian_name") or "").strip()
    return normalize_name_key(name)[:255]


def _row_phone(row: StagedRow) -> str | None:
    data = row.normalized_data or {}
    phone = data.get("guardian_phone_normalized")
    return str(phone) if phone else None


def _candidate_index(
    db: Session, rows: list[StagedRow]
) -> dict[str, list[dict[str, Any]]]:
    """Build deduplicated guardian candidates for each staged row.

    The lookup reads only guardians and their contacts; no candidate state is
    persisted. Candidate dictionaries carry the ORM object internally and are
    trimmed to the public five-item cap by the caller.
    """
    name_keys: set[str] = set()
    phones: set[str] = set()
    for row in rows:
        name_key = _row_name_key(row)
        if name_key:
            name_keys.add(name_key)
        phone = _row_phone(row)
        if phone:
            phones.add(phone)

    guardian_by_id: dict[str, Guardian] = {}
    name_guardians: dict[str, list[Guardian]] = {}
    if name_keys:
        for guardian in db.scalars(
            select(Guardian).where(Guardian.normalized_name.in_(name_keys))
        ):
            guardian_by_id[guardian.id] = guardian
            name_guardians.setdefault(guardian.normalized_name, []).append(guardian)

    phone_guardians: dict[str, list[Guardian]] = {}
    if phones:
        pairs = db.execute(
            select(GuardianContact.guardian_id, GuardianContact.normalized_phone)
            .where(GuardianContact.normalized_phone.in_(phones))
            .distinct()
        ).all()
        missing_ids = {
            guardian_id for guardian_id, _ in pairs if guardian_id not in guardian_by_id
        }
        if missing_ids:
            for guardian in db.scalars(
                select(Guardian).where(Guardian.id.in_(missing_ids))
            ):
                guardian_by_id[guardian.id] = guardian
        for guardian_id, normalized_phone in pairs:
            guardian = guardian_by_id.get(guardian_id)
            if guardian is not None and normalized_phone:
                phone_guardians.setdefault(normalized_phone, []).append(guardian)

    phone_by_guardian: dict[str, GuardianContact] = {}
    if guardian_by_id:
        contacts = db.scalars(
            select(GuardianContact)
            .where(GuardianContact.guardian_id.in_(guardian_by_id))
            .order_by(GuardianContact.is_primary.desc(), GuardianContact.created_at.asc())
        ).all()
        for contact in contacts:
            phone_by_guardian.setdefault(contact.guardian_id, contact)

    index: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        name_key = _row_name_key(row)
        phone = _row_phone(row)
        marked: dict[str, dict[str, Any]] = {}
        for guardian in name_guardians.get(name_key, []):
            marked[guardian.id] = {
                "guardian": guardian,
                "name_match": True,
                "phone_match": False,
            }
        if phone:
            for guardian in phone_guardians.get(phone, []):
                entry = marked.setdefault(
                    guardian.id,
                    {
                        "guardian": guardian,
                        "name_match": False,
                        "phone_match": False,
                    },
                )
                entry["phone_match"] = True

        candidates: list[dict[str, Any]] = []
        for entry in marked.values():
            guardian = entry["guardian"]
            if entry["name_match"] and entry["phone_match"]:
                match = "exact"
            elif entry["name_match"]:
                match = "name"
            else:
                match = "phone"
            contact = phone_by_guardian.get(guardian.id)
            phone_value = (
                (contact.normalized_phone or contact.original_phone) if contact else None
            )
            candidates.append(
                {
                    "guardian": guardian,
                    "guardian_id": guardian.id,
                    "full_name": guardian.full_name,
                    "phone_masked": mask_phone(phone_value),
                    "status": guardian.status,
                    "match": match,
                }
            )
        candidates.sort(
            key=lambda item: (
                0
                if item["match"] == "exact"
                else 1
                if item["match"] == "name"
                else 2,
                item["full_name"],
                item["guardian_id"],
            )
        )
        index[row.id] = candidates[:5]
    return index


def _candidate_status(candidates: list[dict[str, Any]], *, has_phone: bool) -> str | None:
    exact = [item for item in candidates if item["match"] == "exact"]
    name_matches = [
        item for item in candidates if item["match"] in {"exact", "name"}
    ]
    if len(exact) > 1 or (not has_phone and len(name_matches) > 1):
        return "ambiguous"
    if len(exact) == 1:
        return "exact"
    if name_matches:
        return "same_name"
    if candidates:
        return "shared_phone"
    return None


def _auto_guardian(db: Session, row: StagedRow) -> Guardian | None:
    candidates = _candidate_index(db, [row]).get(row.id, [])
    if _row_phone(row):
        exact = [item for item in candidates if item["match"] == "exact"]
        if len(exact) == 1:
            return exact[0]["guardian"]
        return None
    name_matches = [item for item in candidates if item["match"] == "name"]
    if len(name_matches) == 1:
        return name_matches[0]["guardian"]
    return None


def guardian_candidates(db: Session, batch: ImportBatch) -> dict[str, Any]:
    rows = list(
        db.scalars(
            select(StagedRow)
            .where(StagedRow.import_batch_id == batch.id)
            .order_by(StagedRow.position.asc(), StagedRow.id.asc())
        ).all()
    )
    index = _candidate_index(db, rows)
    resolved_ids = {
        row.resolved_guardian_id for row in rows if row.resolved_guardian_id
    }
    resolved_names: dict[str, str] = {}
    if resolved_ids:
        resolved_names = dict(
            db.execute(
                select(Guardian.id, Guardian.full_name).where(
                    Guardian.id.in_(resolved_ids)
                )
            ).all()
        )

    counts = {"ambiguous": 0, "same_name": 0, "shared_phone": 0, "manual": 0}
    items: list[dict[str, Any]] = []
    for row in rows:
        candidates = index.get(row.id, [])
        mode = row.guardian_resolution_mode or "auto"
        status = "manual" if mode != "auto" else _candidate_status(
            candidates, has_phone=bool(_row_phone(row))
        )
        if status is None:
            continue
        if status in counts:
            counts[status] += 1
        data = row.normalized_data or {}
        items.append(
            {
                "row_id": row.id,
                "guardian_name": data.get("guardian_name"),
                "guardian_phone_masked": mask_phone(
                    data.get("guardian_phone_original")
                    or data.get("guardian_phone_normalized")
                ),
                "status": status,
                "mode": mode,
                "resolved_guardian_id": row.resolved_guardian_id,
                "resolved_guardian_name": resolved_names.get(row.resolved_guardian_id)
                if row.resolved_guardian_id
                else None,
                "candidates": [
                    {
                        "guardian_id": item["guardian_id"],
                        "full_name": item["full_name"],
                        "phone_masked": item["phone_masked"],
                        "status": item["status"],
                        "match": item["match"],
                    }
                    for item in candidates
                ],
            }
        )
    return {"items": items, "counts": counts}


def _ensure_contact(
    db: Session,
    guardian: Guardian,
    *,
    original_phone: str,
    normalized_phone: str | None,
) -> bool:
    conditions = [GuardianContact.original_phone == original_phone]
    if normalized_phone:
        conditions.append(GuardianContact.normalized_phone == normalized_phone)
    existing = db.scalar(
        select(GuardianContact)
        .where(GuardianContact.guardian_id == guardian.id, or_(*conditions))
        .limit(1)
    )
    if existing is not None:
        return False
    has_primary = db.scalar(
        select(func.count())
        .select_from(GuardianContact)
        .where(
            GuardianContact.guardian_id == guardian.id,
            GuardianContact.is_primary.is_(True),
        )
    )
    db.add(
        GuardianContact(
            id=str(uuid4()),
            guardian_id=guardian.id,
            original_phone=original_phone[:64],
            normalized_phone=normalized_phone,
            contact_type="mobile",
            is_primary=not bool(has_primary),
            is_verified=False,
        )
    )
    return True


def _ensure_student(
    db: Session,
    guardian: Guardian,
    student_name: str,
    batch_id: str,
) -> tuple[Student, bool, bool]:
    student_name = student_name[:255]
    # Only reuse a student already linked to this guardian. Do not merge
    # students across guardians solely because they share a display name.
    student = db.scalar(
        select(Student)
        .join(
            GuardianStudentRelationship,
            GuardianStudentRelationship.student_id == Student.id,
        )
        .where(
            GuardianStudentRelationship.guardian_id == guardian.id,
            Student.full_name == student_name,
        )
        .limit(1)
    )
    student_created = False
    if student is None:
        student = Student(id=str(uuid4()), full_name=student_name)
        db.add(student)
        db.flush()
        student_created = True
    relationship = db.scalar(
        select(GuardianStudentRelationship)
        .where(
            GuardianStudentRelationship.guardian_id == guardian.id,
            GuardianStudentRelationship.student_id == student.id,
        )
        .limit(1)
    )
    relationship_created = False
    if relationship is None:
        db.add(
            GuardianStudentRelationship(
                id=str(uuid4()),
                guardian_id=guardian.id,
                student_id=student.id,
                relationship_type="guardian",
                source_import_id=batch_id,
            )
        )
        relationship_created = True
    return student, student_created, relationship_created


def confirm_import(
    db: Session,
    batch_id: str,
    *,
    request: Request,
    user: User,
    acknowledge_warnings: bool,
) -> ImportBatch:
    batch = get_batch(db, batch_id, lock=True)
    if batch.status == "confirmed":
        return batch
    if batch.status not in {"review_required", "ready_to_confirm"}:
        raise ApiError(
            409,
            "IMPORT_STATE_INVALID",
            MESSAGES_AR["IMPORT_STATE_INVALID"],
            "The import cannot be confirmed in its current state.",
            {"status": batch.status},
        )

    revalidate_batch(db, batch)
    rows = list(
        db.scalars(select(StagedRow).where(StagedRow.import_batch_id == batch.id)).all()
    )
    rows.sort(key=lambda row: (row.position, row.id))

    blocking = [
        row
        for row in rows
        if not row.is_excluded
        and any(item.get("severity") == "error" for item in (row.validation_errors or []))
    ]
    if blocking:
        raise ApiError(
            409,
            "BLOCKING_ROWS",
            MESSAGES_AR["BLOCKING_ROWS"],
            "Some staged rows still contain blocking validation errors.",
            {
                "row_ids": [row.id for row in blocking],
                "error_summary": batch.error_summary,
            },
        )

    active = [row for row in rows if not row.is_excluded]
    if not active:
        raise ApiError(
            409,
            "NO_CONFIRMABLE_ROWS",
            MESSAGES_AR["NO_CONFIRMABLE_ROWS"],
            "There are no non-excluded rows to confirm.",
        )

    blocking_warnings = [
        warning
        for warning in (batch.warnings or [])
        if warning.get("severity") == "error"
    ]
    if blocking_warnings:
        raise ApiError(
            409,
            "BLOCKING_ROWS",
            MESSAGES_AR["BLOCKING_ROWS"],
            "The file-level warnings are blocking and must be resolved.",
            {"warning_codes": [warning.get("code") for warning in blocking_warnings]},
        )

    warnings = list(batch.warnings or [])
    warning_rows = [
        row
        for row in active
        if any(item.get("severity") == "warning" for item in (row.validation_errors or []))
    ]
    warnings = warnings + [{"row_id": row.id} for row in warning_rows]
    if warnings and not acknowledge_warnings:
        raise ApiError(
            422,
            "WARNINGS_UNACKNOWLEDGED",
            MESSAGES_AR["WARNINGS_UNACKNOWLEDGED"],
            "Warnings must be acknowledged before confirming the import.",
            {"warning_count": len(warnings)},
        )

    # Resolve every manual choice and ambiguous automatic match before the
    # first guardian/contact/student write, so a blocked confirm never leaves
    # partial records behind.
    candidate_index = _candidate_index(db, active)
    ambiguous_rows: list[str] = []
    missing_guardian_rows: list[str] = []
    inactive_guardian_rows: list[str] = []
    for row in active:
        mode = row.guardian_resolution_mode or "auto"
        if mode == "auto":
            status = _candidate_status(
                candidate_index.get(row.id, []),
                has_phone=bool(_row_phone(row)),
            )
            if status == "ambiguous":
                ambiguous_rows.append(row.id)
        elif mode == "link_existing":
            guardian = (
                db.get(Guardian, row.resolved_guardian_id)
                if row.resolved_guardian_id
                else None
            )
            if guardian is None:
                missing_guardian_rows.append(row.id)
            elif guardian.status != "active":
                inactive_guardian_rows.append(row.id)
    if ambiguous_rows:
        raise ApiError(
            409,
            "AMBIGUOUS_GUARDIAN",
            "توجد صفوف لها أكثر من ولي أمر مطابق وتحتاج إلى اختيار يدوي.",
            "Some rows match more than one guardian and need a manual choice.",
            {"row_ids": ambiguous_rows[:50]},
        )
    if missing_guardian_rows:
        raise ApiError(
            404,
            "GUARDIAN_NOT_FOUND",
            "ولي الأمر المحدد غير موجود.",
            "A selected guardian no longer exists.",
            {"row_ids": missing_guardian_rows[:50]},
        )
    if inactive_guardian_rows:
        raise ApiError(
            409,
            "GUARDIAN_INACTIVE",
            "ولي الأمر المحدد غير نشط.",
            "A selected guardian is not active.",
            {"row_ids": inactive_guardian_rows[:50]},
        )

    now = _now()
    created = {"guardians": 0, "contacts": 0, "students": 0, "fee_balances": 0}
    resolution_counts = {"auto": 0, "link_existing": 0, "create_new": 0}
    for row in active:
        data = row.normalized_data or {}
        existing_balance = db.scalar(
            select(FeeBalance.id).where(FeeBalance.source_row_id == row.id).limit(1)
        )
        if existing_balance is not None:
            continue

        name = str(data.get("guardian_name") or "").strip()[:255]
        name_key = normalize_name_key(name)[:255]
        phone = data.get("guardian_phone_normalized")
        original_phone = str(data.get("guardian_phone_original") or "").strip()

        mode = row.guardian_resolution_mode or "auto"
        if mode not in resolution_counts:
            mode = "auto"
        resolution_counts[mode] += 1

        guardian: Guardian | None = None
        if mode == "link_existing":
            guardian = (
                db.get(Guardian, row.resolved_guardian_id)
                if row.resolved_guardian_id
                else None
            )
        elif mode == "auto":
            guardian = _auto_guardian(db, row)

        if guardian is None:
            guardian = Guardian(
                id=str(uuid4()),
                full_name=name,
                normalized_name=name_key,
                status="active",
            )
            db.add(guardian)
            db.flush()
            created["guardians"] += 1

        if original_phone and _ensure_contact(
            db,
            guardian,
            original_phone=original_phone,
            normalized_phone=phone,
        ):
            created["contacts"] += 1

        student = None
        student_name = str(data.get("student_name") or "").strip()
        if student_name:
            student, student_created, _ = _ensure_student(
                db, guardian, student_name, batch.id
            )
            if student_created:
                created["students"] += 1

        fee_period = str(data.get("fee_period") or "").strip() or None
        db.add(
            FeeBalance(
                id=str(uuid4()),
                guardian_id=guardian.id,
                student_id=student.id if student is not None else None,
                import_batch_id=batch.id,
                source_row_id=row.id,
                fee_period=fee_period[:80] if fee_period else None,
                total_fee=_decimal(data.get("total_fee")),
                amount_paid=_decimal(data.get("amount_paid")),
                remaining_balance_source=_decimal(data.get("remaining_balance")) or Decimal("0"),
                remaining_balance_calculated=_decimal(
                    data.get("remaining_balance_calculated")
                ),
                currency=str(data.get("currency") or ""),
                record_status="confirmed",
                reviewed_by=user.id,
                reviewed_at=now,
            )
        )
        created["fee_balances"] += 1
        row.reviewed_by = user.id
        row.reviewed_at = now
        # Make the new guardian/contact/student visible to the next row's
        # exact name+phone lookup inside this transaction.
        db.flush()

    batch.status = "confirmed"
    batch.confirmed_at = now
    batch.confirmed_by = user.id
    batch.updated_at = now
    revalidate_batch(db, batch)
    batch.status = "confirmed"

    record_audit(
        db,
        request=request,
        actor_user_id=user.id,
        action="import.confirm",
        entity_type="import_batch",
        entity_id=batch.id,
        after={
            "status": "confirmed",
            "created": created,
            "guardian_resolution_counts": resolution_counts,
            "total_rows": batch.total_rows,
            "valid_rows": batch.valid_rows,
            "invalid_rows": batch.invalid_rows,
        },
    )
    db.commit()
    db.refresh(batch)
    return batch


def _decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(str(value))


def list_rows(
    db: Session,
    batch: ImportBatch,
    *,
    page: int,
    page_size: int,
    status: str | None,
    query: str | None,
) -> tuple[list[StagedRow], int]:
    conditions = [StagedRow.import_batch_id == batch.id]
    if status == "excluded":
        conditions.append(StagedRow.is_excluded.is_(True))
    elif status:
        conditions.append(StagedRow.is_excluded.is_(False))
        conditions.append(StagedRow.validation_status == status)

    if query:
        pattern = f"%{query.strip()}%"
        conditions.append(
            or_(
                cast(StagedRow.raw_data, Text).ilike(pattern),
                cast(StagedRow.normalized_data, Text).ilike(pattern),
            )
        )

    total = db.scalar(
        select(func.count()).select_from(StagedRow).where(*conditions)
    ) or 0
    rows = list(
        db.scalars(
            select(StagedRow)
            .where(*conditions)
            .order_by(
                StagedRow.position.asc(),
                StagedRow.id.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return rows, int(total)
