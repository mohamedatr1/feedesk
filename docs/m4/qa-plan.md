# M4 — Messaging Foundation Verification Plan

**Purpose:** Verify the safe messaging foundation. G0 and G4 remain blocked; no live SMS is part of this plan.

## 1. Provider and worker

- Fake adapter returns each scenario and deduplicates repeated idempotency keys.
- Rasel adapter request shape, headers, body, redacted payload, and response mapping are tested with `httpx.MockTransport`; no real host call.
- 401/403 invalid key, 429 rate limit, 5xx temporary, timeout unknown, insufficient balance, invalid recipient.
- Worker claims with `FOR UPDATE SKIP LOCKED`; two workers cannot process one job concurrently.
- Lease expiry reclaims a crashed worker's job.
- Heartbeat/lease refresh while in flight.
- Graceful shutdown stops claiming and finishes/releases in-flight work.
- Backoff+jitter, max attempts, no retry for permanent errors, no blind resend for unknown.
- Duplicate job execution preserves one logical message/idempotency key.
- Campaign status derives from message outcomes, not worker optimism.

## 2. Safety

- `MESSAGING_ENABLED=false` or kill switch true → no provider call.
- Missing Rasel key/sender or incomplete config → no provider call.
- WhatsApp/non-SMS channel rejected.
- Cancelled campaign/message not sent.
- No provider secrets, full request bodies, phones, or message text in logs.
- No `/send`, `/resend`, webhook, or live test endpoint exposed in this slice.

## 3. API and UI

- `GET /messages` filters by campaign/status/search, pager, permissions.
- `GET /messages/{id}` shows frozen body, destination, internal/provider states, provider IDs, redacted payload, attempts/next retry; no resend control.
- `GET /campaigns/{id}/results` shows counts by state, progress, failed/unknown, per-message links.
- Accepted-vs-delivered wording is explicit; unknown is not shown as success.
- RTL/44px/1024; empty/loading/error; no fabricated delivery.
- Staff/admin permissions; no credential or secret exposure.

## 4. Worker smoke (fake only)

1. Use the approved synthetic campaign `81aece4e-d84f-4ca6-824e-3bd6380e3b62` with 2 pending messages/jobs.
2. Run `python -m app.worker --once` with:
   - `MESSAGING_PROVIDER=fake`
   - `MESSAGING_ENABLED=true`
   - `MESSAGING_KILL_SWITCH=false`
   - `FAKE_PROVIDER_SCENARIO=delivered`
3. Verify both messages become `delivered`, jobs `completed`, campaign `completed`.
4. Verify no network request to Rasel and no provider events.
5. Re-run the worker; verify no duplicate messages or sends.

## 5. Out of scope

Credential storage/rotation UI, live test-send, webhooks, ops panel, load/chaos, pilot. Those remain open M4 tasks and require G0/G4.

## 6. Execution record

Executed backend, worker, API, frontend, and browser checks are in `verification.md`. The worker was run only with the fake provider; no Rasel host call occurred.
