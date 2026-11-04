# M3 — Campaign and Approval Brief

**Repo root:** `F:\FeeDesk`  
**Milestone:** M3 — Campaign Management and Approval  
**Date:** 3 November 2026  
**Exit criterion:** Staff can prepare and approve a valid campaign without sending it.

## Read first

1. `docs/m3/api-contract.md` — binding API/domain contract.
2. PRD sections 5.2, 5.3, 7.3, 7.4, 8.6, 8.7, 8.8, 10 (campaign tables), 11.1–11.4, 13 D/E, 17.3, 20 Phase 3.
3. `docs/m2/verification.md` — confirmed import data and known M2 behavior.
4. `docs/design/design-review.md`, `docs/design/tokens.css`, `docs/design/m2-import-screens.md`.
5. `apps/web/AGENTS.md` before writing frontend code.

## Current state

- M2 import and confirmation are complete against synthetic fixtures; 87 backend tests pass.
- Core tables already exist: `message_templates`, `campaigns`, `campaign_recipients`, `messages`, `send_jobs`, `provider_events`.
- No campaign/template API or UI exists yet. `/campaigns` and `/messages` are placeholders.
- G0 is blocked. Live SMS, provider calls, and worker execution are out of scope for M3.
- Temporary QA admin is inactive. Do not reactivate it; tests create their own users.

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
- `.env.local` is secret; never read, print, or copy it.
- Do not start long-running servers for implementation validation; I will run the browser E2E.
- Do not send SMS, call Rasel, start a worker, or create provider events.

## Global rules

- Arabic RTL first; calm green/cream design language.
- No AI in eligibility, amounts, templates, or approval.
- Money: `Decimal`/`NUMERIC(18,2)`; never float; serialize as strings; never combine currencies.
- Confirmed fee balances only; zero balances excluded; missing/invalid phones excluded with reasons.
- Never merge guardians on phone alone. Shared phone is a warning, not a merge.
- Approval is explicit, permission-checked, transactional, idempotent, and recorded.
- Approved snapshots are immutable and hashed.
- No provider/network calls in M3. Approval creates pending messages/jobs only.
- Every mutating endpoint uses `require_csrf` and the correct permission.
- Audit every create/update/submit/approve/cancel.
- Do not expose provider secrets or phone data in logs.
- Report files changed, tests run, migration head, and unresolved risks.

## Lane ownership

### Backend campaign lane

Scope:
- `apps/api/app/campaigns/**` (new package: eligibility, grouping, rendering, service)
- `apps/api/app/routers/campaigns.py`, `apps/api/app/routers/templates.py`
- `apps/api/app/schemas.py` (campaign/template schemas only)
- `apps/api/app/models.py` (campaign/template fields only)
- `apps/api/app/security.py` (add `templates.view` to staff; no other role changes)
- `apps/api/app/main.py` (include the two new routers)
- `apps/api/app/seed.py` (optional default draft template only)
- `apps/api/alembic/versions/**` (one new reversible migration; do not edit existing migrations)
- `apps/api/tests/**` (campaign/template tests only)

Deliver:
1. Eligibility service: confirmed balances by source import, guardian/currency grouping, delegation to contacts, Decimal sums, exclusion reasons, shared-phone warnings.
2. Rendering service: allowed variables, fallbacks, unknown-variable blockers, deterministic output, Arabic text, amount formatting.
3. Template CRUD/versioning/activation API and default draft-template seed.
4. Campaign create/list/detail/preview/update/submit/approve/cancel API with state and revision checks.
5. Approval transaction: immutable recipient snapshots, one message and one pending send job per recipient, canonical SHA-256 snapshot hash, approver record, audit, rollback.
6. Database migration for campaign summary/revision/cancel fields and template version uniqueness, plus an immutability trigger for approved campaign recipients.
7. Tests: eligibility/grouping/exclusions, rendering, template versions, campaign permissions/CSRF, state transitions, revision conflicts, approval snapshot/jobs, idempotent approval, cancel, immutability trigger, no provider/network calls.

Do not touch import/auth/settings/audit routers except the `security.py` permission addition. Do not write frontend files or docs.

### Design lane

Scope: `docs/design/m3-campaign-screens.md` only; no code.

Deliver:
- Screen specs for campaign list, builder, review/preview, approved read-only, cancelled, template management.
- Approval semantics: warning acknowledgment, immutable snapshot, hash display, no-send banner.
- Excluded panel and reason copy; per-message preview dialog.
- RTL table/number/currency rules; 1440/1024/768; 44px controls; loading/empty/error states.
- Arabic copy deck for statuses, warnings, exclusions, approval/cancel confirmations, template editor, validation errors.
- Accessibility checklist and focus order.
- Reuse the existing tokens/primitives; do not redesign the shell.

### Frontend campaign lane

Dispatch after the design spec exists; scope:
- `apps/web/app/campaigns/**`
- `apps/web/app/settings/templates/**`
- `apps/web/components/campaigns/**`
- `apps/web/lib/api.ts` (campaign/template client only)
- `apps/web/app/settings/page.tsx` (add template-management link only)
- `apps/web/app/globals.css` only if a shared style is unavoidable

Deliver:
- `/campaigns` list with status filters/tabs, counts, per-currency totals, creator/approver, empty/loading/error.
- `/campaigns/new` builder: confirmed import select, name, active template, create draft.
- `/campaigns/[id]` summary, excluded list/reasons, recipient table, message preview dialog, submit/approve/cancel, approved immutable view with hash and no-send notice.
- `/settings/templates` admin list/version editor/activate; staff read-only if visible.
- Typed API methods and error handling; no fabricated data; no send action.
- RTL, 44px controls, accessible labels/tables/dialogs, 1024 behavior.

## Acceptance evidence

- Backend: Ruff clean, pytest green, `alembic check` clean; tests cover eligibility, grouping, rendering, permissions, revision conflicts, approval snapshot/jobs, idempotency, cancel, and immutability.
- Frontend: typecheck and production build green; screens render real API data.
- Design: spec complete, consistent with the existing dashboard/import language.
- Browser E2E later: create draft from confirmed import, preview recipients, submit, approve, verify frozen snapshot and pending jobs, verify no sending.
