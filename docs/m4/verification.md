# M4 — Messaging Foundation Verification Record

**Date:** 4 November 2026  
**Scope:** Fake-provider worker, message/results surfaces, and safe provider control plane. No live SMS, no Rasel host call, no worker pilot.

## Backend and worker

| Check | Command/result |
|---|---|
| Lint | `ruff check app tests` — pass |
| Tests | `pytest -q` — 425 passed |
| Migration drift | `alembic check` — clean |
| Migration head | `b2c3d4e5f6a7` |
| Worker smoke | fake provider, `MESSAGING_ENABLED=true`, kill switch false, scenario `delivered`; 2 jobs claimed, 2 delivered, 0 failed/unknown |
| Campaign derivation | `81aece4e-d84f-4ca6-824e-3bd6380e3b62` moved to `completed` with counts `{delivered: 2}` |
| API | `/messages` returned 2 newest-first items; detail returned provider request id and redacted fake payload; `/campaigns/{id}/results` returned 2 delivered |
| Safety | no Rasel host request; no provider events; provider payload contains only fake metadata; no send/resend endpoint |

## Frontend

| Check | Result |
|---|---|
| Typecheck | `npm run typecheck` pass |
| Production build | `next build` pass; routes include `/messages`, `/messages/[id]`, `/campaigns/[id]/results` |
| Shareable copy | no `الإرسال غير مفعّل` / `لا تُسلَّم أي رسالة` copy remains; read-only no-manual-send line used |
| Responsive | 1024 and 1440 report `scrollWidth === clientWidth` for messages, results, campaign list/detail, builder |
| Console/network | 0 console errors, 0 page errors, 0 failed non-prefetch requests |

## Browser walkthrough

- `/messages`: 4 historical messages (2 delivered from the fake worker, 2 cancelled from the M3 cancellation test), read-only notice, filters, no resend. Delivered filter returns 2; search works.
- `/messages/{id}`: exact frozen body, destination/amount/currency, `تم التسليم`, provider request/message IDs, redacted payload disclosure, attempts/next retry, no resend.
- `/campaigns/{id}/results`: exact `اكتملت المعالجة`, total 2, delivered 2, all other counts 0, delivery note, 2-row table, no progress bar/percentage, no send/resend.
- `/campaigns`: completed row and `النتائج` action; no false sending-disabled notice.
- `/campaigns/{id}`: processing notice, results link, frozen snapshot, no edit/approve/cancel/send.
- `/campaigns/new`: read-only no-manual-send line, no false sending-disabled copy.
- 1024/1440: no document horizontal overflow on all checked screens.
- No provider/Rasel request, no worker invocation, no `/send`, no resend.

## Environment used for the safe smoke

```powershell
$env:MESSAGING_PROVIDER = "fake"
$env:MESSAGING_ENABLED = "true"
$env:MESSAGING_KILL_SWITCH = "false"
$env:FAKE_PROVIDER_SCENARIO = "delivered"
```

The worker is run only against the development database after a synthetic campaign approval. The API process never sends.

## Safe provider control plane (4 November 2026)

| Check | Result |
|---|---|
| Credential vault | Fernet ciphertext at rest; plaintext never returned; rotation increments `key_version`; revoke clears ciphertext |
| Worker credentials | DB row supersedes environment; rotation refreshes the provider; revocation releases a claimed job to `pending` without sending |
| Provider config guards | Rate/attempts/lease, HTTPS Rasel base, E.164 allowlist, production fake guard |
| Test-send | Fake-only, allowlist required, dry-run result, masked audit, per-actor throttle |
| Balance | Fake `unlimited`; non-fake returns `live_provider_blocked` without network |
| Operations | Read-only summary/jobs/issues/detail; masked phones; no claim tokens, bodies, secrets, or resend action |
| Safety | `run_once` and `run_loop` pace before the `submitting` commit; unknown outcomes never re-armed |
| Browser/API | Provider settings rotate/revoke/test-send and operations page verified at 1024/1440; 0 console errors |
| Tests | 425 passed; Ruff clean; `alembic check` clean; head `b2c3d4e5f6a7` |

Fake-provider load/chaos evidence is in `load-chaos.md`: 100 recipients delivered, expired-lease reclaim once, stale-result fencing, one-send concurrency/idempotency replay, 429/temporary retry, exhaustion, timeout→unknown, and pacing before `submitting`. No live provider, production load, or multi-process rate limit was tested.

The temporary M4 admin/staff QA accounts were deactivated and their sessions revoked after verification. Synthetic messages/campaigns remain for inspection; no real guardian data or live provider call was used.
