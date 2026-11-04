# M2 — Verification and Smoke Plan

**Purpose:** Independent acceptance checks after the backend/frontend import lanes finish. The synthetic fixtures validate the pipeline; real school samples are still required for formal M2 acceptance.

## 1. API smoke flow

Use an authenticated admin session and CSRF header.

1. Upload `sample-01-multi-sheet.xlsx` without a sheet:
   - expect `201`, `status=uploaded`, two `available_sheets`;
2. `POST /imports/{id}/process` with `الفصل الأول`:
   - expect staged rows, status `review_required`;
3. `GET /imports/{id}/rows`:
   - every row has `source_row_number`;
   - zero-balance row is valid but not campaign-eligible;
   - negative row is `invalid`;
   - same guardian/phone sibling rows remain separate fee rows;
4. Edit a phone and remaining balance via `PATCH`:
   - row is revalidated; detail counts update after refetch;
5. Exclude an invalid row:
   - excluded rows never block confirmation;
6. Confirm without warning acknowledgment when warnings exist:
   - expect a clear validation error;
7. Confirm with acknowledgment:
   - status `confirmed`;
   - response idempotent on a second confirm;
8. Confirm database effects:
   - guardians/contacts/students/fee balances created;
   - source remaining equals the reviewed source value;
   - no campaign/message rows created;
9. Upload the same file again:
   - expect `409 DUPLICATE_FILE` with `existing_import_id`.
10. Upload `sample-02-scanned-image.pdf`:
    - expect `review_required`, zero rows, `SCANNED_PDF` warning, no invented values.

## 2. Parser checks

| Fixture | Expected |
|---|---|
| `sample-01-multi-sheet.xlsx` | 2 sheets; Arabic headers; SYP/USD; zero, negative, missing phone; sibling rows |
| `sample-02-arabic-digits.xlsx` | Arabic-Indic digits parsed to Decimal; currency suffixes; zero row |
| `sample-03-messy-headers.xlsx` | header found after blank rows; empty/notes sheets not selected silently |
| `sample-01-text-table.pdf` | text + table extracted; page references present; presentation-form Arabic normalized |
| `sample-02-scanned-image.pdf` | zero text; detected as scanned; no auto rows |

## 3. Financial assertions

- Money stored as Decimal/NUMERIC; never float.
- Source remaining preserved after correction.
- Calculated remaining is comparison-only.
- Missing total fee is not invented.
- Zero balance stored and excluded from reminders later.
- Negative balance blocks confirmation.
- Different currencies are never summed.
- Missing/invalid phone does not destroy the financial row; it blocks messaging eligibility later.
- Shared phone does not auto-merge guardians.
- Confirmation is transactional and idempotent.

## 4. UI checks

- Statements list: upload CTA, status, counts, review/detail action, empty/loading/error.
- Upload: file validation, sheet selection, mapping, explicit process, no auto-redirect.
- Review: row errors visible, one-row edit with original value, exclusion, filters, source ref, confirm disabled with reason.
- Detail: counts, warnings, source file, status/timestamps.
- RTL tables, 44px controls, labels, 1024/768 layout.
- No fake totals, no fabricated progress percentage.

## 5. Security checks

- Upload/review/confirm require the correct permissions.
- CSRF missing → 403.
- File type spoofing/MIME mismatch rejected.
- Path traversal blocked.
- Duplicate upload cannot bypass override without a reason.
- Confirmed/cancelled batches reject edits.
- Audit events exist for upload, process, row correction, confirm, cancel, duplicate override.

## 6. Out of scope

- OCR execution.
- Campaigns, eligibility grouping, message rendering, Rasel sending.
- Real school data in CI.

## 7. Execution record

Executed checks and results are in `verification.md`. Synthetic fixtures validate the pipeline; they do not replace real school samples for formal M2 acceptance.
