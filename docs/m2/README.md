# M2 — Import and Financial Review

**Status:** Core implementation complete; formal acceptance pending real school samples and G0/G1.  
**Verified:** 4 November 2026 — backend suite, 26-fixture synthetic end-to-end acceptance, browser walkthrough, and targeted fix re-checks.

| Document | Purpose |
|---|---|
| `api-contract.md` | Binding API and domain contract for backend/frontend |
| `subagent-brief.md` | Lane scopes, fixtures, environment, rules |
| `../design/m2-import-screens.md` | Screen spec for the import UI |
| `qa-plan.md` | Independent smoke/acceptance checks |
| `verification.md` | Executed checks, results, and known fixture caveats |
| `synthetic-acceptance.md` | 26-fixture import → confirm → campaign → fake-worker acceptance evidence |
| `ocr-decision.md` | Assisted OCR decision, limitations, risks, and revisit evidence |
| `../m0/statement-taxonomy.md` | Canonical fields and validation rules |
| `../m0/synthetic-fixtures.md` | Synthetic XLSX/PDF fixtures |

## Scope

Upload → parse → map → stage → review → correct → confirm → fee records, with provenance and no silent financial changes.

## Out of scope

Campaign creation/approval/worker execution is covered by the M3/M4 surfaces and the synthetic acceptance run; live Rasel sending remains out of scope until G0/G4. OCR is implemented as assisted, review-gated extraction.

## Lanes

- Backend: import package, parsers, validation, API, confirmation, tests, migration.
- Frontend: statements list, upload wizard, review table, detail.
- Design: M2 screen spec.

## Done when

- XLSX/PDF samples parse or fail with actionable errors.
- Every staged row has source provenance.
- Blocking errors prevent confirmation; warnings require acknowledgment.
- Confirmation is transactional and idempotent.
- Guardians/contacts/students/fee balances are created without phone-only merges.
- Real school samples still required for formal M2 acceptance; synthetic fixtures are development evidence only.

## Known gaps

- OCR execution is implemented as **assisted, local-only OCR** (Tesseract `ara+eng`); every OCR row requires human review. Real scanned-sample accuracy and school approval remain pending. Decision and limitations: `ocr-decision.md`.
- Exact golden snapshots for real school statements are not yet in the suite; fixture-based tests, real synthetic sample parses, and Hypothesis money/phone property tests cover the current parser and validation rules.
- Multi-sheet XLSX auto-selects the best statement sheet; headerless/custom layouts use heuristic mapping and may still require manual column correction before confirmation.
- Formal M2 acceptance is blocked on real school statements and the G0/G1 decisions.
- Bulk exclusion/restore and manual guardian resolution are implemented and browser-verified with synthetic fixtures; real-sample confirmation remains pending.
