# M2 — Import API Contract and Domain Rules

**Status:** Baseline for M2 implementation. Backend and frontend must keep this contract unless both sides agree to a change.

**Base:** `/api/v1`  
**Auth:** session cookie; mutating requests require `X-CSRF-Token`.  
**Permissions:** `imports.view`, `imports.upload`, `imports.review`, `imports.confirm`.

---

## 1. Data shapes

### ImportBatchSummary

```json
{
  "id": "uuid",
  "source_filename": "sample.xlsx",
  "file_type": "xlsx",
  "status": "review_required",
  "worksheet_name": "الفصل الأول",
  "available_sheets": ["الفصل الأول", "الفصل الثاني"],
  "total_rows": 7,
  "valid_rows": 5,
  "invalid_rows": 1,
  "duplicate_rows": 1,
  "excluded_rows": 0,
  "totals_by_currency": { "SYP": "2600000.00", "USD": "400.00" },
  "max_upload_mb": 20.0,
  "warnings": [
    { "code": "SCANNED_PDF", "message_ar": "الملف يبدو ممسوحًا ضوئيًا.", "severity": "warning" }
  ],
  "uploaded_by": "user-id",
  "uploaded_by_name": "admin",
  "created_at": "2026-11-03T20:00:00Z",
  "updated_at": "2026-11-03T20:00:00Z",
  "confirmed_at": null,
  "cancelled_at": null
}
```

### ImportDetail

`ImportBatchSummary` plus:

```json
{
  "source_file_id": "uuid",
  "column_mapping": {
    "guardian_name": "اسم ولي الأمر",
    "guardian_phone": "رقم الهاتف",
    "remaining_balance": "المتبقي",
    "currency": "العملة"
  },
  "error_summary": null,
  "confirmed_by": null,
  "duplicate_reason": null
}
```

Aggregate fields:

- `uploaded_by_name` resolves the uploader's username.
- `excluded_rows` is a persisted count.
- `totals_by_currency` sums `remaining_balance` for non-excluded, non-invalid rows, grouped by ISO currency, serialized as decimal strings. Currencies are never combined.
- `max_upload_mb` comes from the upload-limit setting.
- `cancelled_at` and `updated_at` are state-transition timestamps.

### StagedRow

```json
{
  "id": "uuid",
  "source_row_number": 5,
  "source_page_number": null,
  "raw_data": { "اسم ولي الأمر": "ولي أمر 001", "رقم الهاتف": "+963900000001" },
  "normalized_data": {
    "guardian_name": "ولي أمر 001",
    "guardian_phone_original": "+963900000001",
    "guardian_phone_normalized": "+963900000001",
    "student_name": "طالب 001",
    "total_fee": "1000000.00",
    "amount_paid": "400000.00",
    "remaining_balance": "600000.00",
    "remaining_balance_calculated": "600000.00",
    "currency": "SYP",
    "fee_period": "الفصل الأول",
    "is_excluded": false
  },
  "validation_status": "valid",
  "validation_errors": [],
  "is_excluded": false
}
```

Statuses: `valid`, `warning`, `invalid`, `excluded`.

Validation issue shape:

```json
{
  "code": "MISSING_PHONE",
  "field": "guardian_phone",
  "message_ar": "رقم الهاتف مفقود.",
  "severity": "warning"
}
```

`severity` is `warning` or `error`. Only `error` blocks confirmation.

---

## 2. Endpoints

### POST `/imports`

Multipart upload:

| Field | Type | Required | Notes |
|---|---|---:|---|
| `file` | file | Yes | `.xlsx` or `.pdf` |
| `worksheet_name` | text | No | Required if the workbook has multiple sheets and the client wants immediate processing |
| `mapping` | JSON string | No | Canonical field → source header |
| `force_duplicate` | boolean | No | Explicit duplicate override |
| `duplicate_reason` | text | No | Required when forcing a duplicate |

Response `201 ImportDetail`:

- Single-sheet XLSX and text PDFs may return `status: "review_required"` with staged rows.
- Multi-sheet XLSX without `worksheet_name` returns `status: "uploaded"` with `available_sheets`.
- Scanned PDF returns `status: "review_required"` with zero rows and `SCANNED_PDF` warning.

Duplicate file hash without override: `409 DUPLICATE_FILE` with `details.existing_import_id`.

### POST `/imports/{id}/process`

Body:

```json
{
  "worksheet_name": "الفصل الأول",
  "mapping": { "guardian_name": "اسم ولي الأمر" }
}
```

Re-parses the stored file, stages rows, returns `ImportDetail`. Used for multi-sheet selection and manual mapping.

### GET `/imports`

Query: `page`, `page_size`, `status`.

Response:

```json
{ "items": [ImportBatchSummary], "total": 3, "page": 1, "page_size": 20 }
```

### GET `/imports/{id}`

Returns `ImportDetail`.

### GET `/imports/{id}/rows`

Query: `page`, `page_size`, `status` (`valid|warning|invalid|excluded`), `q`.

Response:

```json
{ "items": [StagedRow], "total": 7, "page": 1, "page_size": 50 }
```

### PATCH `/imports/{id}/rows/{row_id}`

Body:

```json
{
  "normalized_data": { "guardian_phone_original": "+963900000001", "remaining_balance": "600000.00" },
  "is_excluded": false
}
```

Re-normalizes/re-validates, updates batch counts, returns `StagedRow`. Block if the batch is confirmed/cancelled.

### POST `/imports/{id}/confirm`

Body:

```json
{ "acknowledge_warnings": true }
```

Rules:

- Batch must be `review_required` or `ready_to_confirm`.
- No row with `is_excluded=false` may have a blocking `error`.
- Warnings may be confirmed with `acknowledge_warnings=true`.
- Transaction creates/updates guardians, contacts, optional students, relationships, and fee balances.
- It is idempotent: confirming an already confirmed batch returns the confirmed detail.
- Returns `ImportDetail` with `status: "confirmed"`.

### POST `/imports/{id}/cancel`

Allowed from `uploaded`, `processing`, `review_required`, `ready_to_confirm`, `failed`. Returns `ImportDetail` with `status: "cancelled"`.

### GET `/imports/{id}/source`

Use the existing authenticated file route: `GET /files/{source_file_id}`.

---

## 3. Parsing rules

### XLSX

- Use openpyxl in `read_only=True, data_only=True`.
- List all worksheets; do not silently pick the first when multiple exist.
- Detect the header row within the first 20 rows (prefer a row with the most known synonyms).
- Preserve merged-cell values from the top-left cell.
- Preserve cached formula values; flag formulas without cached values.
- Exclude empty rows.
- Preserve source row number (1-based worksheet row).
- Maximum rows: configurable, default 5000.

### PDF

- Use pdfplumber for text and tables.
- Preserve page number per row.
- If a page has no extractable text (threshold), mark `SCANNED_PDF`; do not invent rows.
- If tables exist, use them; otherwise attempt line-based extraction and flag low confidence.
- OCR is out of scope for this pass; detection only.
- Maximum pages: configurable, default 200.

### Mapping

Canonical fields:

`guardian_name`, `guardian_phone`, `student_name`, `total_fee`, `amount_paid`, `remaining_balance`, `currency`, `fee_period`.

Auto-suggest from Arabic/English synonyms (e.g. `اسم ولي الأمر`, `الهاتف`, `الموبايل`, `المدفوع`, `المتبقي`, `الرصيد`, `العملة`, `الفصل`). The mapping is editable.

---

## 4. Normalization and validation

### Money

- Parse to `Decimal`, never float.
- Accept Arabic-Indic digits, `,`/`.` separators, and currency suffixes.
- Ambiguous separators → warning/error, not guessing.
- Negative remaining → error.
- Missing remaining → error.
- Zero remaining → valid, `is_eligible=false`, excluded from reminders later.
- If total and paid exist, calculate comparison; discrepancy → warning, preserve source remaining.

### Phone

- Use `python-phonenumbers`, region `SY`.
- Normalize to E.164 where possible.
- Preserve original.
- Invalid/missing/ambiguous → warning; record can be confirmed but `is_eligible=false`.
- Shared phone is a duplicate/ambiguity warning; never auto-merge guardians on phone alone.

### Row status

- `invalid` if any `error`.
- `excluded` if manually excluded; excluded rows never enter campaigns.
- `warning` if only warnings.
- `valid` if no issues.

### Blocking errors

`MISSING_GUARDIAN`, `MISSING_BALANCE`, `NEGATIVE_BALANCE`, `MISSING_CURRENCY`, `AMBIGUOUS_MONEY`, `DUPLICATE_ROW`.

Warnings include `MISSING_PHONE`, `INVALID_PHONE`, `SHARED_PHONE`, `TOTAL_DISCREPANCY`, `ZERO_BALANCE`, `SCANNED_PDF`.

### Duplicate rows

Compute a fingerprint from normalized guardian name, phone, student, period, remaining, and currency. Duplicate fingerprints inside the batch → `DUPLICATE_ROW` error, requiring manual exclusion. A shared phone with a different guardian name is a warning, not a merge.

---

## 5. Confirmation behavior

For each non-excluded, non-invalid staged row:

1. Find a guardian by exact normalized name **and** normalized phone. If none, create a guardian.
2. Add a primary contact only when the phone is present and not already on that guardian.
3. Create/reuse a student only when a student name is present; do not require student data.
4. Create a `fee_balances` row with source remaining, calculated comparison, explicit currency, source row reference, reviewer, and `record_status='confirmed'`.
5. Never merge two different guardian names solely because they share a phone.
6. Update batch counts and status transactionally; audit the confirmation.
7. No campaign or message is created in M2.

### Bulk exclusion and guardian resolution

- `POST /api/v1/imports/{id}/rows/exclusion` (`imports.review`, CSRF):
  `{is_excluded, scope:"invalid"|"selected", row_ids[]}`. One transaction, one revalidation, one audit event. Returns `ImportDetailOut`; `NO_ROWS_TO_EXCLUDE`, `ROW_NOT_FOUND`, or `IMPORT_STATE_INVALID` on invalid selectors/state.
- `GET /api/v1/imports/{id}/guardian-candidates` (`imports.view`): masked candidate rows with `exact`/`same_name`/`shared_phone`/`ambiguous`/`manual` status and counts. Never returns full phones.
- Row PATCH accepts `guardian_resolution:{mode:"auto"|"link_existing"|"create_new", guardian_id?}`.
- Confirmation preflight blocks ambiguous `auto` rows with `409 AMBIGUOUS_GUARDIAN` and `details.row_ids` before any writes. `link_existing` reuses the selected active guardian; `create_new` always creates a new one.

---

## 6. Extraction behavior (XLSX/PDF)

- Header detection scans the first rows for recognized Arabic/English headers. If none is sufficient, rows are staged with synthetic headers and value-based mapping, and `HEADER_NOT_FOUND` is a non-blocking warning.
- Multi-sheet XLSX with no explicit sheet auto-selects the best statement sheet by header mapping and data-row count; `available_sheets` remains available for switching.
- Currency detection scans title/header text for `SYP`, `USD`, `EUR`, `SAR`, `AED`, `ل.س`, `ليرة`, etc. If no currency column exists, an inferred currency column is added; if none is detected, the school settings currency is used with a warning.
- PDFs use table extraction first, then text/word-position fallback. Scanned image-only PDFs use assisted local Tesseract OCR (`ara+eng`) when enabled, producing candidate rows with `OCR_USED` and a mandatory human review; OCR is never auto-confirmed.
- Rows are never dropped solely because headers are unknown; the reviewer can correct mappings before extraction/confirmation.

## 7. Frontend screens

| Route | Screen |
|---|---|
| `/statements` | Import history + upload CTA |
| `/statements/upload` | File drop → upload → sheet selection → mapping → process |
| `/statements/[id]/review` | Editable staged rows, row errors, exclusions, confirm |
| `/statements/[id]` | Import detail, counts, source file, warnings |

The UI must show:

- clear file validation errors;
- sheet selection when multiple sheets exist;
- mapping before extraction;
- row-level errors next to the row;
- source row/page reference;
- confirm only when no blocking errors;
- an explicit warning acknowledgment;
- confirmed/cancelled states.
