# M2 — Import Workstream Brief

**Repo root:** `F:\FeeDesk`  
**Milestone:** M2 — Import and Financial Review  
**Date:** 3 November 2026

## Read first

1. `docs/m2/api-contract.md` — the binding API/domain contract.
2. `docs/m0/statement-taxonomy.md` — field rules.
3. `docs/m0/synthetic-fixtures.md` — local fixtures and parser findings.
4. `docs/m1/status.md` — current foundation.
5. PRD sections 7.1, 7.2, 8.3, 8.4, 8.5, 16.1, 16.2, 17.1, 17.2.

## Current state

- M1 backend is working: auth/session/CSRF/RBAC, users, settings, audit, private file route.
- Core tables already exist: `import_batches`, `source_files`, `staged_rows`, `guardians`, `guardian_contacts`, `students`, `guardian_student_relationships`, `fee_balances`.
- `openpyxl` and `pdfplumber` are installed and in `requirements.txt`.
- Backend tests: 51 passing. Frontend build: passing.
- G0 is blocked. Do not send SMS, create campaigns, or use real guardian data.

## Environment

```powershell
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\ruff.exe check app tests
& F:\FeeDesk\.venv\Scripts\python.exe -m pytest -q
& F:\FeeDesk\.venv\Scripts\alembic.exe check

Set-Location F:\FeeDesk\apps\web
npm run typecheck
$env:NODE_OPTIONS="--max-old-space-size=1024"
$env:NEXT_TELEMETRY_DISABLED="1"
npm run build
```

- Dev DB: `127.0.0.1:55432/feedesk`; tests use `feedesk_test`.
- `.env.local` is secret; do not read/print/copy it.
- Do not start long-running servers for validation; build/tests only.
- Synthetic fixtures: `.local/samples/xlsx/*.xlsx` and `.local/samples/pdf/*.pdf`.

## Global rules

- Arabic RTL first.
- No AI/LLM extraction or financial decisions.
- Money uses `Decimal`/`NUMERIC(18,2)`; never binary float.
- Preserve source values and provenance.
- Missing phone/invalid phone can retain a financial record but must block messaging eligibility.
- Zero balance is stored, excluded from reminders.
- Negative balance is a blocking error.
- Different currencies are never combined.
- Never auto-merge guardians on phone alone.
- Import confirmation is transactional and idempotent.
- Every mutating endpoint uses `require_csrf` and the correct permission.
- No live SMS, campaigns, or messages in M2.
- Report files changed, tests run, and unresolved risks.

## Lane ownership

### Backend import lane

Scope:
- `apps/api/app/imports/**` (new package: parsers, normalization, validation, mapping, storage, service)
- `apps/api/app/routers/imports.py`
- `apps/api/app/schemas.py` (import schemas only)
- `apps/api/app/models.py` (import metadata fields only)
- `apps/api/app/config.py` (upload limits only)
- `apps/api/app/main.py` (include import router only)
- `apps/api/alembic/versions/**` (one new migration, do not edit existing migrations)
- `apps/api/tests/**` (import tests only)
- `apps/api/requirements.txt` only if a dependency is strictly required

Deliver:
- upload + storage + SHA-256 + duplicate detection;
- XLSX/PDF parsing with sheet list, header detection, page/row refs;
- scanned-PDF detection (no OCR);
- mapping suggestions and manual mapping;
- staging persistence;
- validation/normalization engine;
- import list/detail/rows/edit/exclude/process/confirm/cancel endpoints;
- transactional confirmation into guardians/contacts/students/fee balances;
- audit events for upload, process, row correction, confirm, cancel, duplicate override;
- tests using synthetic fixtures plus edge cases.

Do not touch auth/users/settings/audit routers or frontend files.

### Frontend import lane

Scope:
- `apps/web/app/statements/**`
- `apps/web/lib/api.ts` (import client + FormData handling only)
- `apps/web/components/imports/**` (new)
- `apps/web/app/globals.css` only if a small shared style is unavoidable

Deliver:
- `/statements` import history with upload CTA, status, counts, date, uploader, review/detail action, error summary.
- `/statements/upload` file drop, validation, upload progress, sheet selection, mapping table, process action.
- `/statements/[id]/review` editable staged rows, inline error display, exclusion, filters, source reference, warning acknowledgment, confirm.
- `/statements/[id]` detail/counts/source/warnings/audit summary.
- API client methods typed against `docs/m2/api-contract.md`.
- RTL, 44px controls, accessible labels, loading/empty/error states, no fake data.
- `File`/`FormData` upload must not force JSON content type.

Do not touch other pages, backend files, docs, or `.env.local`.

### Design lane

Scope: `docs/design/m2-import-screens.md` only; no code.

Deliver:
- screen-by-screen spec for statements list, upload wizard, mapping, review table, detail, empty/error/loading states;
- RTL layout and table guidance;
- row error/exclusion/confirmation semantics;
- copy recommendations;
- responsive notes at 1440/1024/768;
- accessibility checklist.

## Acceptance evidence

- Backend: `ruff` clean, `pytest` green, `alembic check` clean; tests cover XLSX, PDF, scanned PDF, money/phone/duplicate validation, confirm transaction, CSRF/RBAC.
- Frontend: `tsc` clean, production build green; screens render with real API data when backend is available.
- Design: spec readable and consistent with the approved dashboard language.
