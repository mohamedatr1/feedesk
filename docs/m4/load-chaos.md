# M4 — Fake-Provider Load and Chaos Evidence (MSG-14)

**Date:** 4 November 2026  
**Scope:** Fake provider only. Synthetic data only. No live SMS, no Rasel host call, no production load, no multi-process rate-limit claim.  
**Status:** Load/chaos coverage implemented. **G4 is not marked passed.** G0 remains blocked.

## Scenario

A synthetic approved campaign is created with 100 frozen recipients, 100 `messages`, and 100 `send_jobs` using the same helper used by the M4 worker tests. The real `MessagingWorker` claim/process path is exercised end to end (`claim_next` → `process_job` → status application → campaign derivation) with the in-process `FakeProvider` and the test database. Pacing sleeps are stubbed in the load test to keep runtime bounded; pacing itself is covered by separate tests below.

Chaos scenarios use separate one-recipient campaigns with lease expiry, nested reclaim, 429/temporary errors, retry exhaustion, and timeout.

## Counts observed

| Measurement | Result |
|---|---|
| Recipients / messages / jobs | 100 / 100 / 100 |
| Claimed by `run_loop(max_jobs=100)` | 100 |
| Delivered messages | 100 |
| Completed jobs (attempt count exactly 1) | 100 |
| Campaign status | `completed` |
| Fake provider `send_count` | 100 |
| Duplicate message IDs / idempotency keys / provider message IDs | 0 (100 distinct each) |
| Provider events written | 0 (count unchanged across the run) |
| HTTP/network calls | 0 (`httpx.Client.send` and `httpx.AsyncClient.send` patched to raise) |
| Extra claims after the load run | 0 (`run_once` returns `claimed=False`) |

Chaos coverage additional outcomes:

| Scenario | Observed |
|---|---|
| Expired lease reclaim | Reclaimed exactly once; attempt 1 → 2; one send; second pass claims nothing |
| Reclaimed `submitting` | Message/job `unknown`; `last_error_code=RECONCILIATION_REQUIRED`; zero sends |
| Stale result after reclaim | `result_fenced`; old `delivered` result discarded, state stays `unknown`; exactly one audit event `message.result_discarded`; total sends across both workers = 1 |
| Concurrent claim race (2 threads/2 workers) | Exactly 1 claimed report, exactly 1 send, job attempt 1, message delivered |
| Idempotency-key replay | Fake `send_count` stays 1; identical result and provider message ID returned |
| 429 and temporary error | `retry` with backoff (2s base ±20% jitter; 429 also honors `Retry-After: 2`); attempt 1; `next_attempt_at` in the future |
| Retry exhaustion (3 attempts) | Message/job `failed`; campaign `failed`; fake `send_count` still 1 |
| Timeout | Message/job `unknown`, `TIMEOUT`; not re-claimed after a forced `next_attempt_at`; `send_count` stays 1 |
| Pacing | `run_once`: exactly one sleep (0.5s at 2/s) before provider I/O while state is `pending`/`claimed`. `run_loop`: exactly one sleep per send for 3 jobs, no extra poll sleep. Two workers pace independently |

## Observed wall-clock range

Load-test body (`create_campaign_messages` excluded; measured around `run_loop(max_jobs=100)`), three separate runs on the local Windows/PostgreSQL test database:

| Run | Elapsed |
|---|---|
| 1 | 3.33 s |
| 2 | 15.21 s |
| 3 | 17.93 s |

The spread reflects local database/machine variance, not a product assertion. The test **records** elapsed time and only asserts a generous `< 120 s` hang guard; it does not fail on a tight performance threshold. Full suite wall-clock in the evidence run: 139.70 s.

## Invariants

- One claim token per claim; only the owning token/attempt may apply a provider result.
- An expired lease may be reclaimed once; the reclaimed job moves to a terminal state and is never reclaimed again.
- A `submitting` message whose lease expired is never resent; it becomes `unknown` with `RECONCILIATION_REQUIRED`.
- A stale result from a replaced claim is audited (`message.result_discarded`) but never mutates message, job, or campaign state.
- Duplicate execution (concurrent claims, replayed idempotency key) produces one logical send.
- Retryable outcomes retry with bounded backoff up to the configured max attempts; exhaustion is `failed`.
- Ambiguous/timeout outcomes are `unknown` and are never re-claimed or auto-resent.
- Campaign status is derived from message/job outcomes; 100 delivered messages yield `completed`.
- Provider acceptance is not treated as delivery; the fake only reports `delivered` because its configured scenario is `delivered`.
- Pacing happens before provider I/O and before `submitting` is committed, in both `run_once` and `run_loop`, with no double sleep.
- Fake mode performs no network I/O and writes no provider events.

## Pacing limitation

Pacing is **per worker process**. `_pace()` sleeps `1 / MESSAGING_RATE_LIMIT_PER_SECOND` independently in each process, and there is no shared/global limiter. Running N worker processes can therefore exceed the intended provider rate by up to N×. Operationally, run one worker per provider account unless the provider enforces a global rate, or add a distributed limiter before scaling out.

## Commands

```powershell
Set-Location F:\FeeDesk\apps\api
& F:\FeeDesk\.venv\Scripts\ruff.exe check app tests
& F:\FeeDesk\.venv\Scripts\python.exe -m pytest tests/test_messaging_load.py -q
& F:\FeeDesk\.venv\Scripts\python.exe -m pytest -q
& F:\FeeDesk\.venv\Scripts\alembic.exe check
```

Results for this evidence run:

| Check | Result |
|---|---|
| `ruff check app tests` | pass |
| `pytest tests/test_messaging_load.py -q` | 14 passed |
| `pytest -q` | **425 passed** (1 pre-existing Starlette/httpx deprecation warning) |
| `alembic check` | No new upgrade operations detected |

## Real defects found

None. No worker/test changes were required beyond the new test file. The wide wall-clock spread (3.3 s–17.9 s) is recorded as an environment observation, not a defect, and the test intentionally avoids timing assertions.

## Explicit non-claims

- No live provider, no Rasel request, no SMS, no webhook, no network of any kind.
- No production or representative-scale load; 100 synthetic messages on a local test database is not a capacity or latency benchmark.
- No multi-process coordinated rate limit; pacing is per process as documented.
- No provider reconciliation writes or resolution of `unknown` outcomes.
- No claim that G0 or G4 is satisfied; this is fake-provider evidence only.
- No claim that `completed` means provider delivery in production; the fake scenario reports `delivered` explicitly.
