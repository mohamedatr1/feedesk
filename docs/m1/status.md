# M1 Foundation — Status

**Date:** 3 November 2026  
**Status:** Implemented surface is working locally. Formal M1/G1 close is blocked by G0 and the remaining acceptance evidence below.

## Completed

| Area | Evidence |
|---|---|
| Repository scaffold | `apps/api`, `apps/web`, `apps/worker`, `packages`, `infra`, `docs` |
| Local dev database | PostgreSQL 16 at `.local/pgdata`, port 55432 |
| CI workflow | `.github/workflows/ci.yml`: secret scan, lint, migrations, down/up, tests, frontend build |
| Config and secrets | `.env.example`, gitignored `.env.local`, production guard for default secrets |
| Schema + migrations | 19 tables, three migrations, reversible chain, `alembic check` clean |
| Audit | Append-only update/delete/truncate trigger; actor, before/after, request ID, IP policy |
| Auth | Argon2id, server sessions, expiry, logout, forced password change, persistent lockout |
| CSRF | Applied to all mutating users/settings/auth routes, with negative tests |
| RBAC | Admin/Staff guards; matrix tests cover settings, users, audit, files, auth |
| Users | Create, update role/email/job title, deactivate, reset password, last-admin guard, case-insensitive uniqueness |
| Settings | School name, ISO currency, symbol, locale, IANA timezone, contacts, limits; validated and audited |
| Private storage | Path-safe authenticated download; audit event; tests |
| API conventions | Error envelope, request IDs, validation, pagination, security headers; generated OpenAPI TypeScript client (`npm run generate:api`) |
| Health | `/health/live` and `/health/ready`; readiness returns 503 on DB failure |
| Design system | Tokens, RTL shell, buttons/inputs/cards/tables/pills, dialogs, confirmations, empty states |
| Frontend shell | Sidebar, topbar, active nav, skip link, cached session, per-route titles |
| Login/password | Responsive login, forced change, reveal toggle, 12-character rule, sign-out |
| Dashboard | Honest loading/empty states, no fake sparkline, no fabricated currency |
| Settings/users | Admin edit, staff read-only, user edit/confirm/deactivate/reset, per-user campaign approval flag |
| Audit UI | Actor names, Arabic action/entity labels, loading state, full-ID disclosure |
| Accessibility | Contrast-safe metadata/borders, real focus outline, table captions/scopes, 44px targets |
| Tests | 51 M1 backend tests (425 total with M2–M5 hardening); Ruff clean; TypeScript clean; production build passing |
| Backup/restore | Local dump/restore verified: users/audit/settings row counts |
| Design review | `docs/design/design-review.md`; P1 fixes implemented |

## Remaining before M1/G1 close

- Error tracking with PII scrubbing (OD-13).
- Frontend automated tests / Playwright suite.
- Full P2 visual-scale polish (type scale, topbar/sidebar, display serif).
- CI execution on a real repository.
- Production deployment and monitoring (M5).
- G0 blockers: real samples, approved sender, Syrian test number, free-text-enabled plan, school decisions.

## M2 preparation

- Synthetic XLSX fixtures: `.local/samples/xlsx/` (3 files).
- Synthetic PDF fixtures: `.local/samples/pdf/` (text table + scanned image).
- Real sample intake: `.local/samples/real/xlsx/` and `.local/samples/real/pdf/`.
- Parser finding: Chromium Arabic PDFs expose presentation-form codepoints; normalize before comparison.
- Scanned PDF fixture is handled by assisted local OCR (Tesseract `ara+eng`) and remains review-gated; OCR accuracy on real samples is not yet measured.

## Commands

```powershell
.\scripts\db.ps1 start
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\alembic.exe upgrade head
& F:\FeeDesk\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

Set-Location F:\FeeDesk\apps\web
npm run dev
```

