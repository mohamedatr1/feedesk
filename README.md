# FeeDesk

Private, single-school fee-statement and reminder application. Arabic RTL UI, deterministic Excel/PDF import, human review, campaign approval, and Rasel messaging.

**Current state:** M0 is partially complete (provider route verified, G0 blocked). The M1 foundation is implemented and working locally: auth, RBAC, per-user campaign approval permission, schema, audit, settings, users, RTL shell, login, dashboard, and audit UI. M2 import is implemented with synthetic-fixture verification: XLSX/PDF parsing, multi-sheet auto-selection, currency inference, headerless/custom-layout fallback, assisted local OCR for scanned PDFs (human review required), sheet selection, column mapping, staging, validation, review, bulk exclusion, manual guardian resolution, and transactional confirmation. M3 campaign preparation and approval are implemented: eligibility/exclusions, per-currency totals, Arabic template versioning/rendering, draft submission, immutable approval snapshots, pending messages/jobs, and dashboard/reporting metrics with an idempotent daily snapshot job. M4 safe messaging foundation and control plane are implemented with a fake provider, Rasel adapter (mocked tests only), PostgreSQL worker, retries/idempotency/status mapping, message history, campaign results, encrypted provider credentials, fake/dry-run test-send, balance preflight, and a read-only operations panel; live SMS remains disabled until G0. M5 formal launch/UAT is blocked by G0/G4; pre-G4 hardening is in progress: production-like Compose, backup/restore helpers, monitoring templates, runbooks, local DB restore drill, a security/privacy review with H3/M1/M4/M7/M8 fixes, and the full permission matrix. Formal M1/G1, M2, M3, M4, and M5 acceptance remain pending the M0 blockers, real school samples, provider verification, and school copy approval. A Vercel Services deployment is live at https://feedesk-one.vercel.app for smoke testing; persistent upload storage, the messaging worker, backups, monitoring, custom domain, and real-school UAT remain open.

## Repository layout

```
apps/
  api/        FastAPI + SQLAlchemy + Alembic + tests
  web/        Next.js 16 + TypeScript + Tailwind + RTL UI
  worker/     reserved for worker-specific deployment assets; runtime lives in apps/api/app/worker.py
packages/
  shared/     reserved for generated API types
infra/
  compose/    Docker Compose for a production-like stack
docs/
  adr/        architecture decisions
  deployment/ Vercel Services and deployment notes
  m0/         discovery evidence, G0 gate, samples, decisions
  design/     tokens and screen gap
scripts/      local development helpers
vercel.json   Vercel Services: public web + private API binding
```

## Prerequisites

- Python 3.10+ (local venv is at `.venv`)
- Node.js 24+
- PostgreSQL 16 binaries (`F:\PostgreSQL\16\bin` on this machine)

Docker is not installed on this workstation. A Compose stack is provided for environments that have Docker.

## Local database

The local development cluster lives at `.local/pgdata` on port **55432**. It is separate from any PostgreSQL service on port 5432.

```powershell
# Start
& 'F:\PostgreSQL\16\bin\pg_ctl.exe' -D 'F:\FeeDesk\.local\pgdata' `
  -o '-p 55432 -c listen_addresses=127.0.0.1' `
  -l 'F:\FeeDesk\.local\pg.log' start

# Stop
& 'F:\PostgreSQL\16\bin\pg_ctl.exe' -D 'F:\FeeDesk\.local\pgdata' stop

# Check
& 'F:\PostgreSQL\16\bin\pg_isready.exe' -h 127.0.0.1 -p 55432
```

The cluster uses trust authentication on localhost only. Do not expose port 55432.

## Environment

Copy `.env.example` to `.env.local` and set:

- `SESSION_SECRET` — long random value.
- `RASEL_API_KEY` — server-side key; never put it in frontend code.
- `SEED_ADMIN_PASSWORD` — temporary first-login password.
- `DATABASE_URL` — already points at the local cluster.

`.env.local` is gitignored.

## Backend

```powershell
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\python.exe -m alembic upgrade head
& F:\FeeDesk\.venv\Scripts\python.exe -m app.seed
& F:\FeeDesk\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/health/live and `/health/ready`
- Read-only provider check: `python scripts/rasel_check.py` (account, senders, policies; sends nothing)

The seed creates the school settings and an administrator only when they do not exist. The initial temporary password comes from `SEED_ADMIN_PASSWORD`; if the administrator password has already been changed, use the new password. A fresh database still forces a password change on first login.

## Frontend

```powershell
Set-Location F:\FeeDesk\apps\web
npm install
npm run dev
```

- App: http://localhost:3000
- Login: http://localhost:3000/login

Browser calls to `/api/*` go through the Next.js route handler `apps/web/app/api/[...path]/route.ts`, which forwards to `API_INTERNAL_URL` locally/Compose or to the Vercel `API_URL` service binding. See `docs/deployment/vercel.md` for the multi-service Vercel setup.

## Tests and checks

```powershell
# Backend
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\python.exe -m pytest -q
& F:\FeeDesk\.venv\Scripts\ruff.exe check app tests

# Frontend
Set-Location F:\FeeDesk\apps\web
npm run typecheck
npm run build
```

The backend test suite creates and uses `feedesk_test` on the local cluster. It does not touch the development database.

## What is implemented

### M1 foundation

- PostgreSQL schema and Alembic migrations for all core entities.
- Append-only audit table enforced by update/delete/truncate triggers.
- Argon2id password hashing, server-side sessions, expiry, and persistent login lockout.
- CSRF protection on all mutating routes, with negative tests.
- Backend RBAC with Administrator/Staff roles and last-admin safeguards.
- Case-insensitive username uniqueness.
- Admin user management: create, update role/email/job title, deactivate, reset password.
- School settings: name, ISO currency, display symbol, locale, IANA timezone, contacts, limits, validation.
- Private file storage abstraction and authenticated download route.
- Health endpoints, validated request IDs, JSON logs with redaction, and error envelope.
- Arabic RTL shell, design tokens, login, forced password change, dashboard, settings, users, audit, dialogs, and confirmations.
- P1 accessibility fixes: contrast, input boundaries, focus outline, skip link, per-route titles.
- 425 backend tests; Ruff, TypeScript check, production build, `npm audit` clean.

### M2 import

- Upload `.xlsx`/`.pdf` with extension, MIME/magic-byte checks, size and row/page limits, SHA-256 duplicate detection, and override-with-reason.
- XLSX parsing with worksheet listing, header detection, merged-cell values, cached formulas, source row numbers, and empty-row skipping.
- PDF text/table parsing with page references; scanned PDFs use assisted local OCR (`ara+eng`) with mandatory human review, and degrade to `SCANNED_PDF` without invented rows when OCR is unavailable.
- Arabic/English column mapping with auto-suggestions, manual overrides, and required-field checks.
- Staging with raw + normalized JSON, validation status, exclusions, and per-currency totals.
- Decimal money, Arabic-Indic digits, currency suffixes, negative/missing/zero balances, total discrepancies, E.164 phone normalization, shared-phone warnings, and duplicate-row fingerprints.
- Import history, upload wizard, mapping, review ledger with one-row editing and exclusions, confirm/cancel, detail, and authenticated source download.
- Transactional, idempotent confirmation into guardians, contacts, optional students, relationships, and fee balances with source provenance; no phone-only merges.
- Audit events for upload, process, row correction (before/after), duplicate override, confirm, and cancel.
- Synthetic 26-fixture end-to-end acceptance (15 XLSX + 11 PDF): 26/26 imports passed, 211 rows staged, 16/16 campaigns completed through the fake worker with 139/139 messages delivered; evidence and limitations in `docs/m2/synthetic-acceptance.md`.

### M3 campaign and approval

- Campaign creation from a confirmed import; guardian/currency grouping; per-currency outstanding totals.
- Eligibility exclusions for zero/negative balances, missing currency, inactive guardians, missing/invalid phones; shared-phone warnings without guardian merges.
- Arabic template management with retained versions, activation, allowed variables, deterministic fallbacks, and unknown-variable blockers.
- Draft editing, explicit submit-for-approval, admin approval with warning acknowledgment and revision checks.
- Immutable approval snapshots with canonical SHA-256, frozen recipients/exclusions/warnings/template version, and a DB trigger against recipient mutation.
- Transactional approval creates one pending message and one pending send job per recipient, plus audit; approval itself makes no provider call.
- Read-only approved/cancelled views, campaign list, and admin template editor. No send affordance in any state.

### M4 messaging foundation

- Provider port with fake and Rasel adapters; the Rasel adapter uses the published contract and mocked-HTTP tests only.
- PostgreSQL worker with `FOR UPDATE SKIP LOCKED`, lease/heartbeat/reclaim, pacing, graceful stop, retry backoff/jitter, and idempotency-key replay safety.
- Conservative status mapping: provider acceptance is not delivery; timeout/ambiguity becomes `unknown` with no blind resend.
- Campaign status derivation from message outcomes; message history/detail and campaign results APIs/UI with per-state counts.
- Safety defaults: fake provider, messaging disabled, kill switch on; SMS-only channel lock; no send/resend control.
- 425 backend tests; frontend typecheck/build; no live provider request.

### Not yet implemented (next milestones)

- Live Rasel test-send and verified delivery-report contract (G0).
- Provider webhooks, reconciliation writes/admin resolution actions, and the controlled pilot (M4 remainder).
- Production hardening, UAT, training delivery, launch (M5/M6). Training and handover drafts are prepared under `docs/m6/`.
- OCR execution for scanned PDFs; scanned files are detected only.
- Real school statement acceptance evidence and school-approved Arabic template copy.
- Error tracking with PII scrubbing, configurable approval permission, generated OpenAPI client, full P2 visual polish, frontend automated tests in CI, CI execution on a real repository, production deployment and monitoring.

## M0 status and blockers

See `docs/m0/gate-g0.md` and `docs/m0/rasel-verification.md`.

G0 is **not passed** because:

- No approved SMS sender exists on the Rasel account.
- No school-controlled Syrian test number or delivered test SMS. `local_sms` rejected the non-Syrian account phone; `int_sms` is blocked by the trial free-text restriction.
- The account needs a free-text-enabled plan or provider enablement for the test.
- Real school statement samples are not yet received; synthetic XLSX/PDF fixtures exist under `.local/samples/` for parser development only.
- Currency, approval, retention, opt-out, hosting, and Arabic template decisions await school sign-off.
- Business/app name verification and commercial confirmation are incomplete.

Live sending remains disabled. WhatsApp remains hard-disabled.

## Sample fixtures

- Synthetic parser fixtures: `.local/samples/xlsx/` and `.local/samples/pdf/`.
- Real anonymized school statements: place them in `.local/samples/real/xlsx/` and `.local/samples/real/pdf/`.
- The synthetic fixtures do not satisfy G0; real samples are still required.

## Security notes

- The Rasel API key is stored only in `.env.local` (gitignored).
- Rotate the key if the working conversation or logs are retained outside the school's control.
- Users are deactivated, not hard-deleted, because audit events reference the actor and the audit log is append-only.
- Do not put real guardian data into test fixtures or source control.

