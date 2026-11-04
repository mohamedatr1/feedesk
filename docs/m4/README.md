# M4 — Messaging Foundation

**Status:** Safe foundation and control plane implemented and verified: provider port/fake/Rasel adapters, worker, message history/results APIs/UI, encrypted credential vault with rotation/revoke, fake/dry-run allowlisted test-send, balance preflight, read-only reconciliation/ops panel, and browser/API checks. Live SMS, live test-send, provider reconciliation writes, webhooks, load/chaos, and Rasel contract verification remain disabled until G0/G4.

| Document | Purpose |
|---|---|
| `api-contract.md` | Binding provider/worker/message/results contract for this slice |
| `subagent-brief.md` | Lane scopes, safety rules, environment |
| `../design/m4-message-screens.md` | Message history/detail and campaign results screen spec |
| `qa-plan.md` | Worker/message/results verification plan |
| `verification.md` | Executed worker/API/UI evidence |
| `load-chaos.md` | Fake-provider load, reclaim, concurrency, retry/timeout, pacing evidence |

## Scope

Fake provider → worker claim/lease/retry/idempotency → message states → campaign results → message history → encrypted provider credentials → fake/dry-run test-send → read-only ops/reconciliation. Rasel adapter implemented behind the provider port and tested only with mocked HTTP.

## Out of scope in this slice

Live test-send/SMS, live Rasel contract verification, provider webhooks, reconciliation writes/resolution actions, load/chaos, pilot, message resend. The ops surface is deliberately read-only.

## Hard constraints

- No live SMS; no request to `raselsms.com` in tests or validation.
- `MESSAGING_PROVIDER=fake` and `MESSAGING_ENABLED=false` by default.
- Provider acceptance is not delivery.
- Timeout/ambiguous outcome becomes `unknown`; never blind-resend.
- WhatsApp remains hard-disabled.

## Done when

- Worker processes synthetic pending jobs with the fake provider.
- Message states, retries, leases, duplicate execution, and campaign status derivation are tested.
- Message history/detail and campaign results render real API data.
- No send/resend control exists; no provider secret or full payload is exposed.
