# M2 — Synthetic Import Acceptance (26-Fixture End-to-End Run)

**Date:** 4 November 2026  
**Scope:** Synthetic data only. This proves the import → review → confirm → campaign → fake-worker pipeline works for the fixture pack in this environment. It is **not** real-school acceptance and does not pass G0/G1/G4/G5, UAT, training, handover, or production deployment.

## Fixture pack

- **15 XLSX + 11 PDF = 26 fixtures**, all synthetic, all SHA-256 unique.
- Manifest: `.local/samples/qa/manifest.json`.
- Generators: `scripts/qa_fixtures/generate_xlsx.py`, `scripts/qa_fixtures/generate_pdf.mjs`, `scripts/qa_fixtures/generate_all.py`.
- Runner: `scripts/qa_fixtures/e2e_acceptance.py`.
- Result: `.local/samples/qa/e2e-report.json`.

Coverage includes:

- Arabic RTL and English LTR statements.
- Multi-sheet workbooks with a cover/notes sheet; statement-sheet auto-selection.
- Headers at row 7, merged headers, merged guardian cells, extra/shuffled columns, empty columns, wide sheets.
- Headerless 3-column and 5-column workbooks/PDFs with value-based mapping.
- Arabic-Indic digits, `ل.س`, multi-currency rows (SYP + USD), title/header-only currency.
- Cached formulas and one formula without a cached value.
- Invalid/zero/negative balances, duplicate rows, shared phones, missing/invalid phones, totals/footer rows.
- PDF bordered tables, borderless text columns, 48-row multi-page repeated headers, wrapped multi-line cells, landscape/rotated headers, mixed Arabic/English, totals/footer rows.
- Image-only scanned Arabic and English PDFs (OCR path).

## Execution

Environment: local API `http://127.0.0.1:8000`, local web `http://localhost:3000`, local PostgreSQL, local Tesseract `ara+eng` at 300 DPI. Messaging used the **fake provider only**; no live SMS or Rasel call was made.

```powershell
$env:PYTHONPATH='F:\FeeDesk\apps\api'
Set-Location F:\FeeDesk
F:\FeeDesk\.venv\Scripts\python.exe scripts\qa_fixtures\e2e_acceptance.py
```

The runner uploads each fixture, processes multi-sheet files, stages rows, validates mappings and row issues, confirms every `supports_full_confirm` fixture, creates and approves a campaign, runs the fake worker, and verifies delivered counts from campaign results.

## Result

| Metric | Result |
|---|---|
| Fixtures | **26 / 26 passed** |
| Imported/staged rows | **211** |
| Campaign-capable fixtures | **16** |
| Campaigns completed | **16 / 16** |
| Fake-worker jobs processed | **139** |
| Messages delivered | **139 / 139** |
| Staged-only fixtures (intentional review cases) | **10** |
| Full backend suite | **425 passed** |
| Ruff / `alembic check` | Clean / no drift |
| Migration head | `d3e4f5a6b7c8` |

Campaign verification:

| Fixture | Messages | Delivered | Status |
|---|---:|---:|---|
| xlsx-01-standard-ar-multisheet | 6 | 6 | completed |
| xlsx-02-standard-en-headers | 7 | 7 | completed |
| xlsx-04-header-at-row-7 | 6 | 6 | completed |
| xlsx-07-merged-headers-guardians | 3 | 3 | completed (shared guardian) |
| xlsx-08-arabic-indic-digits-lira | 6 | 6 | completed |
| xlsx-09-multi-currency-syp-usd | 6 | 6 | completed |
| xlsx-10-no-currency-col-usd-title | 6 | 6 | completed |
| xlsx-11-shuffled-column-order | 6 | 6 | completed |
| xlsx-12-cover-before-statement | 6 | 6 | completed |
| pdf-01-arabic-rtl-bordered | 7 | 7 | completed |
| pdf-02-english-ltr-table | 7 | 7 | completed |
| pdf-03-multipage-repeated-headers | 48 | 48 | completed |
| pdf-04-borderless-text-columns | 6 | 6 | completed |
| pdf-06-multiline-wrapped-cells | 5 | 5 | completed |
| pdf-07-landscape-rotated-headers | 8 | 8 | completed |
| pdf-10-mixed-ar-en-title-footer-currency | 6 | 6 | completed |

Intentionally staged-only (no confirmation/campaign): `xlsx-03`, `xlsx-05`, `xlsx-06`, `xlsx-13`, `xlsx-14`, `xlsx-15`, `pdf-05`, `pdf-08`, `pdf-09`, `pdf-11`. These carry expected review cases (headerless mapping, formulas, duplicates, zero/negative balances, invalid phones, OCR review, totals rows).

## Defects found and fixed by this run

1. **RTL visual-order phones** in PDF cells (`140 301 944 963+`) normalized to invalid numbers. Fixed in `normalize_pdf_cell` by restoring group order and the leading `+`; logical numbers are left untouched.
2. **Money-with-currency cells** (`س.ل 620,000`) were classified as currency, so headerless layouts lost the balance column. Fixed so parseable money wins classification; reversed currency tokens are also accepted by money/currency parsing.
3. **Headerless data rows** were mistaken for headers when the phone was still invalid. Header detection now rejects rows containing money values or 9+ digit values.
4. **Totals/footer rows** were staged as data. PDF rows now drop summary rows (Arabic mirrored/OCR variants and reversed English `latoT`) and single-cell titles/notes.
5. **Scanned PDFs with a bogus table** skipped OCR because `extract_tables()` returned a structure. OCR now runs whenever the page has no usable text layer; image-only pages never fall through to invented table rows.
6. **Tesseract PSM 6** collapsed gridded scanned tables into one line. OCR now uses PSM 4 with PSM 6/3 fallback.
7. **Harness expectation bug**: row-level validation codes (zero/negative balance, invalid/shared/missing phone, duplicates, uncached formula) were checked only against document warnings. The harness now aggregates row `validation_errors` with document warnings.

## Browser acceptance

Playwright against the production build, 1440×900 and 1024×900:

- Arabic multi-sheet XLSX: auto-selected sheet note, mapping, **6 review rows**.
- English XLSX: mapping, **7 review rows**.
- English PDF: mapping, **7 review rows**.
- Headerless PDF: header warning, mapping, **6 review rows**.
- Scanned Arabic PDF: OCR warning, manual-review copy, mapping, **8 review rows**.
- Review pages show guardian/phone/student/balance/currency; 1024 layout has no page overflow.
- Completed campaign `pdf-03` shows 48 recipients/messages; results page shows delivered counts; 1024 layout has no page overflow.
- Zero unexpected console errors. The only 409s were the deliberate duplicate-upload dialog path used to re-upload the same synthetic file.

## Known limitations (must stay visible)

- This is **synthetic evidence only**. Real anonymized school statements and school sign-off are still required for formal M2 acceptance.
- OCR accuracy on real scans, stamps, handwriting, and poor image quality is unmeasured. OCR rows always require review; headerless OCR can swap student/guardian name columns, which the reviewer must correct in mapping/review.
- The fixture pack intentionally uses `supports_full_confirm=false` for OCR/headerless/invalid-row cases; those are review-path evidence, not confirmation evidence.
- Exact golden snapshots for real school layouts and the idempotency convention remain open.
- No live provider, SMS, Rasel, UAT, training delivery, handover acceptance, production deployment, H4/H6, or G0/G4/G5 evidence is created by this run.

## Reproduction and cleanup

- Regenerate fixtures: `python scripts/qa_fixtures/generate_all.py`.
- Rerun acceptance: see command above; the API must be restarted after backend code changes.
- The QA admin `qa_synthetic_admin` was deactivated and its sessions revoked after the run. Synthetic imports/campaigns remain in the local development database for inspection; production must start from a clean migrated database.
