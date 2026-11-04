# M4 — Messaging Foundation Brief (First Safe Slice)

**Repo root:** `F:\FeeDesk`  
**Milestone:** M4 — Messaging Foundation  
**Date:** 4 November 2026  
**Hard constraint:** No live SMS, no real Rasel send, no worker call to `raselsms.com`. G0 is blocked. The default provider is `fake`; the Rasel adapter is implemented and unit-tested only with mocked HTTP.

## Read first

1. `docs/m4/api-contract.md` — binding contract for this slice.
2. PRD 8.9, 8.10, 11.3, 11.4, 16.3, 17.4, 18.4, 20 Phase 4.
3. ADR 005 (provider abstraction), ADR 006 (worker/jobs), ADR 007 (idempotency).
4. `docs/m3/verification.md` for approved campaign/job state.
5. `apps/web/AGENTS.md` before frontend work.

## Current state

- M3 approval creates one pending `messages` row and one pending `send_jobs` row per recipient, with a stable `idempotency_key`.
- No worker, provider adapter, message API, or results UI exists yet.
- `/messages` is a placeholder.
- Rasel account has no approved sender, no Syrian test number, trial free-text restriction, and no delivered test. G0 is blocked.

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
- Do not start long-running servers for validation; I will run the worker/E2E.
- Worker tests inject the fake provider; no network.

## Global rules

- Never call Rasel in tests, development, or validation.
- Never send SMS. `MESSAGING_ENABLED` defaults false; kill switch defaults true.
- Provider credentials are server-side only; never return them to the browser or logs.
- SMS only. WhatsApp is hard-disabled.
- One logical message per personalized recipient; preserve message identity and idempotency key across retries.
- Ambiguous timeout → `unknown`; never blind-resend.
- Provider acceptance is not delivery. Only explicit `delivered` becomes `delivered`.
- Campaign status must be derived from message outcomes, not worker optimism.
- Use `Decimal`/strings for money; never floats.
- Every mutating endpoint uses CSRF and the correct permission; read-only history/results use `messages.view`/`campaigns.view`.
- Audit worker/manual operations without logging phone numbers/message bodies/secrets.

## Lane ownership

### Backend messaging/worker lane

Scope:
- `apps/api/app/messaging/**` (port, fake adapter, Rasel adapter, error mapping, worker service)
- `apps/api/app/worker.py` (CLI/runtime entry point)
- `apps/api/app/routers/messages.py`
- `apps/api/app/routers/campaigns.py` (add `/campaigns/{id}/results` only)
- `apps/api/app/schemas.py` (message/results schemas only)
- `apps/api/app/models.py` (message/job fields only)
- `apps/api/app/config.py` (messaging settings only)
- `apps/api/app/main.py` (include messages router only)
- `apps/api/alembic/versions/**` (one new reversible migration)
- `apps/api/tests/**` (messaging/worker tests only)
- `apps/api/requirements.txt` only if strictly required

Deliver:
1. Provider port + fake adapter scenario matrix + Rasel adapter with mocked-HTTP tests.
2. Worker claim/lease/heartbeat/reclaim with `FOR UPDATE SKIP LOCKED`, pacing, graceful stop.
3. Retry classification/backoff/jitter/max attempts; timeout → unknown, no blind resend.
4. Idempotency replay safety using existing message key; fake dedupe; provider header.
5. Status mapping and campaign status derivation.
6. Message list/detail API and campaign results API with counts.
7. Migration for redacted payload/lease/heartbeat fields.
8. Tests: fake scenarios, Rasel request/mocked responses, timeout/429/5xx/auth/balance, duplicate execution, lease reclaim, graceful stop, retry backoff, idempotent replay, campaign status derivation, permissions, no live network.

Do not implement credential UI/encryption, live test-send, webhooks, or ops panel in this slice. Do not touch campaign approval logic except results serialization.

### Design lane

Scope: `docs/design/m4-message-screens.md` only; no code.

Deliver:
- Message history list: filters (campaign, state, search), columns, pager, empty/loading/error.
- Message detail: frozen body, destination, status, provider references, redacted payload, no resend.
- Campaign results: progress counts, accepted-vs-delivered wording, failures/unknown, per-message table, no send affordance.
- Status vocabulary and Arabic copy for all message/campaign states.
- RTL, 44px, 1440/1024/768, accessibility/focus, no fake delivery claims.

### Frontend lane

Dispatch after the design spec; scope:
- `apps/web/app/messages/**`
- `apps/web/app/campaigns/[id]/results/**`
- `apps/web/components/messages/**`
- `apps/web/components/campaigns/**` (results components only)
- `apps/web/lib/api.ts` (message/results client only)
- `apps/web/app/globals.css` only if unavoidable

Deliver:
- `/messages` list/search/filter/pager and `/messages/[id]` detail.
- `/campaigns/[id]/results` progress/counts/per-message table.
- Typed API methods, error/empty/loading, RTL/accessibility.
- No send/resend affordance; no claim that accepted means delivered.

## Acceptance evidence

- Backend: Ruff, pytest, `alembic check`; no live network; all scenarios tested.
- Frontend: typecheck/build; design spec followed.
- Worker: one-shot run against synthetic approved campaign with fake provider creates realistic terminal states and derives campaign status; no Rasel host contact.
- Browser E2E: message history, detail, campaign results; no send control.
