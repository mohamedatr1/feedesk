# M2 — Verification Record

**Date:** 3 November 2026  
**Scope:** Synthetic fixtures only. Formal M2 acceptance still requires real school statements.

## Backend and schema

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check app tests` | Pass |
| Tests | `pytest -q` | 87 passed |
| Migration drift | `alembic check` | No new upgrade operations |
| Migration head | `alembic current` | `e5f6a7b8c9d0` |

## End-to-end API smoke

Script: `C:\Users\IT DOCTOR\AppData\Local\Temp\opencode\m2_api_smoke2.py` (temporary, not in repo).  
Fixtures: `.local/samples/xlsx/sample-01-multi-sheet.xlsx`, `sample-03-messy-headers.xlsx`; `.local/samples/pdf/sample-01-text-table.pdf`, `sample-02-scanned-image.pdf`.

Passed:

- Duplicate file without override → `409 DUPLICATE_FILE` with `existing_import_id`.
- Forced duplicate without a reason → `422 DUPLICATE_REASON_REQUIRED`.
- Forced duplicate with reason → `201 uploaded`; two worksheets listed; `uploaded_by_name` and `max_upload_mb` present.
- Sheet processing → `review_required`, 7 rows, 6 valid, 1 invalid, per-currency totals `{"SYP":"2600000.00","USD":"400.00"}`.
- Source row numbers present; negative balance is `invalid`; missing phone warns; zero balance stored; sibling rows remain separate.
- Row patch: valid phone clears `INVALID_PHONE`; corrected remaining balance raises `TOTAL_DISCREPANCY` (expected because total/paid are unchanged).
- Confirm with an active invalid row → `409 BLOCKING_ROWS` and row ids.
- Excluding the invalid row then confirming without acknowledgment → `422 WARNINGS_UNACKNOWLEDGED`.
- Confirming with acknowledgment → `200 confirmed`; totals update to `{"SYP":"2650000.00","USD":"400.00"}`; second confirm is idempotent.
- Scanned PDF → `review_required`, zero rows, `SCANNED_PDF` warning, no invented rows.
- Text PDF → 6 rows with page references.
- Messy workbook → three sheets listed; selected sheet detects headers after leading blank rows and stages 4 rows.
- Upload without CSRF → `403`.

## Database assertions

Confirmed batch `05fa1c96-63b4-40fe-9dc8-4271ac36fb4e`:

- 6 fee balances, all `confirmed`, all with `source_row_id` and `reviewed_by`.
- Currencies explicit (`SYP`, `USD`); USD not combined with SYP.
- Corrected source remaining `650000.00` preserved; calculated comparison `600000.00` retained separately.
- Zero-balance row stored (`0.00`).
- Excluded invalid row produced no fee balance.
- 6 guardians, 5 contacts, 6 student relationships; no contact invented for the missing-phone row.
- Two same-name guardians with different phones remained separate — no name-only merge.
- No campaign and no message rows created.

The shared-phone/name reuse path is covered by `test_confirm_reuses_guardian_across_rows_without_student`; the different-name/shared-phone split is covered by `test_shared_phone_warns_and_never_merges_guardians`.

## Browser walkthrough

Playwright run on 3 November 2026 against the running web/API stack, using a temporary admin account.

Passed:

- Login → dashboard.
- Statements list: upload CTA, status labels, counts, uploader, and review action.
- Flow A (text PDF `8d250665-05c4-4708-9734-2d1beea08450`): review table, source page references, inline negative-balance error, blocked confirm bar; exclude invalid row; warning acknowledgment; confirmation dialog; redirect to detail with confirmed banner and read-only state. API ended `confirmed`, 6 total, 5 included, 1 excluded, `SYP 1600000.00` + `USD 400.00`.
- Flow B (fresh `ui-upload-sample.xlsx` → batch `cb871349-becd-4715-ae14-17ef9b710de8`): upload handoff, single-sheet mapping, 8/8 auto-suggestions, explicit extraction, result panel, two valid rows, `SYP 1100000.00`, confirmation, confirmed detail.
- 1440px layouts; 1024px statements/upload/detail layouts; RTL; keyboard path to confirm; focus handoff; icon-button labels; zero console/page errors and zero failed API calls.

Defects found and status:

| # | Severity | Defect | Status |
|---|---|---|---|
| 1 | Medium | Review page expanded the document to 1165px at a 1024px viewport | Fixed: contain/paint on the table scroller and `min-w-0` on the card |
| 2 | Medium | Confirmed banner counted total rows instead of included rows | Fixed: total − excluded − invalid |
| 3 | Low | `جاهزة 0` / `صالحة 0` while warning rows would import | Fixed: the bar/dialog now show `للاستيراد` as total − excluded − invalid |
| 4 | Low | Excluded row still announced a blocking error | Fixed: excluded issue styling/suffix is non-blocking |
| 5 | Low | Screen readers heard the currency code twice in totals | Fixed: visual code hidden from AT, term announced once |

Evidence: `C:\Users\IT DOCTOR\AppData\Local\Temp\opencode\m2-ui\REPORT.md` and screenshots in the same folder. Temporary evidence, not part of the repository.

### Targeted fix re-check

All five fixes passed in a second Playwright run:

- 1024×900 review page: `documentElement.scrollWidth=1024`, `clientWidth=1024`; the table wrapper still scrolls (`1180 > 914`, range 266). 1440 remains 1440.
- Confirm bar: `للاستيراد 6 · مستثناة 0 · تحذيرات 6` for a 7-row batch with 1 invalid row; after exclusion `للاستيراد 6 · مستثناة 1 · تحذيرات 6`. No `جاهزة` or `صالحة`.
- Excluded row: suffix changes from `(خطأ مانع للتأكيد)` to `(سجل مستبعد — لا يمنع التأكيد)` and the issue text becomes muted; restoring the row reverses both.
- Confirmed banner for Flow A: `تم تأكيد الاستيراد. الأسطر المؤكدة: 5. السجلات للعرض فقط.`
- Currency totals accessibility tree: `term: SYP` / `definition: 1,600,000.00`; visible code is `aria-hidden`, so it is not announced twice.
- Final build spot-check after the last count adjustment: bar `للاستيراد 6`, 1024 width 1024, banner 5, zero console errors.

Evidence: `C:\Users\IT DOCTOR\AppData\Local\Temp\opencode\m2-ui-fixes\REPORT.md` and screenshots in that folder.

## Bulk exclusion and guardian resolution (4 November 2026)

- `POST /imports/{id}/rows/exclusion` supports `scope=invalid` and `scope=selected`, revalidates once, and writes one audit event.
- `GET /imports/{id}/guardian-candidates` returns masked candidates with exact/name/phone matches and ambiguity status.
- Row PATCH supports `auto` / `link_existing` / `create_new`; confirmation blocks ambiguous auto matches with `409 AMBIGUOUS_GUARDIAN` and no partial writes.
- Browser verification on `39db6d7b-f9f2-44bb-857f-67e907616c86`: bulk exclude/restore succeeded, guardian link saved, masked phones only, 1024 layout 1024, 0 console errors.
- Hypothesis property tests cover money/phone normalization; full backend suite is 425 tests.

## Real/custom statement extraction (4 November 2026)

The reported sample failures were reproduced and fixed:

- Multi-sheet XLSX now auto-selects the statement sheet (`كشف الأقساط`) instead of returning zero rows and forcing a manual choice. The sample stages **18 rows / 18 valid**.
- PDF title-level currency is detected (`SYP` from `العملة: ليرة سورية (ل.س)`) and injected as an inferred currency column; the sample stages **18 rows / 18 valid** with no `MISSING_CURRENCY` errors.
- Headerless/custom sheets fall back to synthetic headers plus value-based mapping (phone, money, currency, names) with non-blocking warnings. A 3-column headerless test stages **3 rows / 3 valid** and maps guardian, phone, and remaining balance.
- Explicit sheet selection, existing header detection, validation, and archive limits remain green.
- Browser verification: XLSX and PDF each show 18 extracted rows, auto-sheet note, “continue to mapping”, inferred currency mapping, 1024 layout, 0 console errors.
- Full backend suite: **425 tests**; Ruff and `alembic check` clean.

Scanned image-only PDFs now use assisted local OCR; OCR remains review-gated.

## Assisted OCR (4 November 2026)

- Tesseract `ara+eng`, local only, 300 DPI; TSV word reconstruction with RTL column ordering.
- `sample-02-scanned-image.pdf` stages **6 candidate rows** (5 valid, 1 requiring correction) with `OCR_USED` + `HEADER_NOT_FOUND` warnings instead of zero rows.
- OCR-derived rows are never auto-confirmed; invalid phones/amounts remain row errors for human correction.
- `OCR_ENABLED=false` or missing Tesseract/Arabic data degrades to the previous `SCANNED_PDF` warning.
- Browser check on the earlier PSM 6 build: 7 rows, OCR review warning, mapping opened, 1024 layout, 0 console errors. The final PSM 4 path stages 6 rows on this fixture (5 valid, 1 requiring correction), confirmed by a parser probe.
- Full backend suite: **425 tests**; Ruff and `alembic check` clean.

## Synthetic 26-fixture end-to-end acceptance (4 November 2026)

- 15 custom XLSX + 11 custom PDF fixtures, including headerless, merged, multi-sheet, Arabic-Indic, multi-currency, formula, invalid-value, borderless, multi-page, landscape, wrapped-cell, and image-only scanned layouts.
- **26/26 fixtures passed**; **211 rows** staged; **16/16 campaign-capable fixtures** completed through the fake worker with **139/139 messages delivered**; 10 files intentionally staged-only for review.
- This run found and fixed RTL phone group reversal, money-with-currency classification, headerless first-row misdetection, totals/footer staging, OCR being skipped when a bogus table existed, and OCR page-segmentation failure on gridded scans.
- Browser acceptance covered Arabic/English XLSX and PDF, headerless PDF, scanned Arabic OCR, review rows, mappings, campaign 48/48 results, 1024 layouts, and zero unexpected console errors.
- Full detail and campaign table: `synthetic-acceptance.md`.
- This remains synthetic evidence; real-school samples and formal M2 acceptance are still required.

## Notes

- The synthetic fixture numbers `+963900000001…` are possible but not valid Syrian numbers under libphonenumber; they correctly produce `INVALID_PHONE` warnings. Valid test numbers use `+96393…`/`+96399…`.
- The earlier API smoke returned `404` because an older uvicorn process was still serving the previous code. Restart the API after backend changes. The current process serves `/api/v1/imports` and returns `401` unauthenticated, as expected.
- Browser walkthrough evidence is recorded in the UI verification section above. Temporary screenshots and the raw report live under `C:\Users\IT DOCTOR\AppData\Local\Temp\opencode\m2-ui\` and `...\m2-ui-fixes\`.
- The temporary admin used for QA was deactivated and its sessions revoked after verification. Synthetic import batches remain in the development database for inspection; no real guardian data was used.
