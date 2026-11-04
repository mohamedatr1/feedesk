# FeeDesk M6 — Fake-Provider Pilot Rehearsal

**Document ID:** M6-REH-01  
**Version:** 0.1  
**Date:** 4 November 2026  
**Status:** Rehearsal evidence only. **Not** the first live campaign, hypercare, G4 closure, handover acceptance, or launch.  
**Audience:** School admin, technical owner, provider/ops, security.  
**Related:** `first-campaign-runbook.md`, `docs/runbooks/worker-recovery.md`, `docs/runbooks/unknown-outcomes.md`.

---

## 1. Scope and non-claims

This document records a local, end-to-end rehearsal of the campaign path using the **fake provider** and **synthetic data only**:

```text
confirmed import -> draft campaign -> preview/exclusions -> submit -> warning acknowledgement
-> approval snapshot -> real MessagingWorker + FakeProvider -> messages/results/ops reconciliation
```

**What this rehearsal is:**

- A check that the existing API, worker, and read-only operations surfaces work together on one synthetic campaign.
- Evidence that approval creates messages/jobs, the worker claims and completes them, and the result views agree.
- Evidence that no send/resend control is exposed and that list/ops surfaces use masked phones.

**What this rehearsal is not:**

- Not a live SMS campaign. No message left the machine.
- No Rasel host call, no Rasel API request, and no external network request.
- No claim that a real provider accepted or delivered anything.
- No G0, G4, G5, OPS-09, OPS-11, OPS-12, hypercare, training, or launch claim. G0/G4/G5 remain open.
- No application code, `.env.local`, account, or unrelated document was changed.
- The synthetic campaign and its messages/jobs are retained as evidence. No account was deactivated.

**Scope result:** the fake-provider path completed with 2/2 synthetic messages terminal, 0 duplicates, 0 provider events, and 0 failed/unknown messages. This is a **rehearsal pass only**.

---

## 2. Environment

| Item | Value |
|---|---|
| API | `http://127.0.0.1:8000` |
| Web UI | `http://localhost:3000` |
| Database | Local PostgreSQL used by the development environment |
| App environment | `development` |
| Admin account | `qa_rehearsal_pilot_admin` (role `admin`, synthetic) |
| Provider | `fake` (`FakeProvider`) |
| Provider scenario | `delivered` |
| Messaging flags used by the worker process | `MESSAGING_ENABLED=true`, `MESSAGING_KILL_SWITCH=false` |
| Network | None. The fake adapter has no network I/O. |
| Data | Synthetic only |
| Source import | `9ea965b7-2a5a-4750-a76b-01590a24ece5` (`m3-campaign-sample.xlsx`, status `confirmed`) |
| Template | `0f40aace-ae7f-4f8b-a7b5-090f1425ce8c` — `تذكير الرسوم الدراسية`, version `1`, active |

The worker was executed as an isolated local process with the flags above. The API process configuration was not modified, and `.env.local` was not edited. Message, phone, and provider values in this document are recorded as counts, IDs, and masked values only.

---

## 3. Campaign record

| Field | Value |
|---|---|
| Campaign ID | `05b751fe-2ec6-4bf9-9758-158e88fdea2a` |
| Campaign name | `M6 Pilot Rehearsal 2026-11-04 (fake provider)` |
| Channel | `sms` |
| Status at close | `completed` |
| Revision | `2` |
| Source import | `9ea965b7-2a5a-4750-a76b-01590a24ece5` |
| Template | `0f40aace-ae7f-4f8b-a7b5-090f1425ce8c`, version `1` |
| Eligible recipients | `2` |
| Excluded records | `2` |
| Invalid contacts | `1` |
| Currency total | `SYP 1,100,000.00` |
| Created by | `qa_rehearsal_pilot_admin` |
| Created at | `2026-11-04T13:37:07.442017+01:00` |
| Submitted at | `2026-11-04T13:37:25.474878+01:00` |
| Approved at | `2026-11-04T13:37:25.667436+01:00` |
| Snapshot hash | `de9c61f9d61badcd1d615f8651d38d484bf626d0848bf79d72920ce0ca78a9f2` |

### 3.1 Preview and exclusions

- Blocking reasons: none (`can_submit=true`).
- Warning: `SHARED_PHONE` — count `2`. The two eligible recipients share the same masked destination (`+963 9•• ••• 701`).
- Excluded records:
  - `ZERO_BALANCE` — 1 synthetic record, `SYP 0.00`.
  - `MISSING_PHONE` — 1 synthetic record, `SYP 400,000.00`.
- The preview returned 2 recipients and 2 excluded records; `invalid_contact_count=1` matches the missing-phone exclusion.
- Recipient rows were checked in preview mode only; no full phone or guardian/student name is reproduced here.

**Observation:** the shared-phone warning is a synthetic data condition, not a system failure. In a real pilot the school must decide whether shared-phone guardians are in scope and record that decision before approval.

---

## 4. Approval evidence

The campaign was created from the confirmed import at revision `0`, then submitted and approved through the CSRF-aware API.

| Step | Request | Result |
|---|---|---|
| Create draft | `POST /api/v1/campaigns` | `201`, status `draft`, revision `0`, 2 recipients, 2 exclusions |
| Preview | `GET /api/v1/campaigns/{id}/preview` | `200`, 2 recipients, 2 exclusions, no blocking reasons |
| Submit | `POST /api/v1/campaigns/{id}/submit` (`expected_revision=0`) | `200`, status `awaiting_approval`, revision `1` |
| Approval with stale revision | `POST /api/v1/campaigns/{id}/approve` (`expected_revision=0`) | `409 CAMPAIGN_CHANGED`, current revision `1` |
| Approval without warning acknowledgement | `POST /api/v1/campaigns/{id}/approve` (`expected_revision=1`, `acknowledge_warnings=false`) | `422 WARNINGS_UNACKNOWLEDGED`, `warning_count=1` |
| Approval with warning acknowledgement | `POST /api/v1/campaigns/{id}/approve` (`expected_revision=1`, `acknowledge_warnings=true`) | `200`, status `approved`, revision `2` |

**Approval result:**

- Approved by `qa_rehearsal_pilot_admin` at `2026-11-04T13:37:25.667436+01:00`.
- Approval created `2` messages and `2` pending jobs.
- Approval made **no** provider call. Messages were still `pending` before the worker ran.
- Snapshot hash: `de9c61f9d61badcd1d615f8651d38d484bf626d0848bf79d72920ce0ca78a9f2`.

**Audit trail (read-only query):**

| Action | Recorded at |
|---|---|
| `campaign.create` | `2026-11-04T13:37:07.442017+01:00` |
| `campaign.submit` | `2026-11-04T13:37:25.459913+01:00` |
| `campaign.approve` | `2026-11-04T13:37:25.663880+01:00` |

The `campaign.approve` audit payload contains the same snapshot hash and `recipient_count=2`. The stale-revision and unacknowledged-warning attempts did not create messages or jobs.

---

## 5. Worker result

### 5.1 Worker configuration

| Setting | Value |
|---|---|
| Worker | `app.messaging.worker.MessagingWorker` (real worker, local process) |
| Provider instance | `FakeProvider` |
| `MESSAGING_PROVIDER` | `fake` |
| `MESSAGING_ENABLED` | `true` |
| `MESSAGING_KILL_SWITCH` | `false` |
| `FAKE_PROVIDER_SCENARIO` | `delivered` |
| `MESSAGING_ALLOWLIST` | empty (no allowlist filtering during this fake run) |
| `MESSAGING_RATE_LIMIT_PER_SECOND` | `10` (rehearsal process only) |
| `MESSAGING_MAX_ATTEMPTS` | `3` |
| Network | none |

The worker was run until no claimable job remained, then run once more to verify it could not claim or send again. It never called the Rasel adapter.

### 5.2 Processed jobs

| Job ID | Message ID | Outcome | Attempts | Campaign status after result |
|---|---|---|---|---:|---|
| `2a7001f5-a520-4ae9-9f9f-6cd450f1130e` | `de0756e0-5e88-410c-a2e7-35f17262944e` | `delivered` (fake) | 1 | `sending` |
| `69441fbd-ffb6-4325-a430-25ba18b09ea6` | `66122236-07f3-4906-a6cc-efdef134f86d` | `delivered` (fake) | 1 | `completed` |

- **Fake send count:** `2` (`FakeProvider.send_count`).
- **Second pass:** `claimed=false`, no new claim, fake send count stayed `2`.
- **Duplicates:** none. 2 messages, 2 jobs, 2 distinct idempotency keys, 2 distinct provider message IDs, 0 `resend_of_message_id` links.
- **Provider events:** 0 rows in total; 0 rows for `fake`; no unprocessed events; `last_received_at=null`.

The two fake provider IDs were `fake-msg-b121c2279773` and `fake-msg-1e697a4cd6ba`. They are local deterministic IDs, not evidence of external delivery.

---

## 6. Reconciliation view

### 6.1 Required counts

| Check | Expected | Actual | Difference | Explanation |
|---|---:|---:|---:|---|
| Approved recipients | 2 | 2 | 0 | Frozen approval snapshot |
| Messages created | 2 | 2 | 0 | One message per approved recipient |
| Jobs created | 2 | 2 | 0 | One pending job per message |
| Provider outcomes delivered (fake) | 2 | 2 | 0 | Local fake scenario `delivered` |
| Provider accepted (intermediate status) | 0 | 0 | 0 | Fake `delivered` writes terminal delivered directly |
| Provider events received | 0 | 0 | 0 | No webhook/event path used |
| Failed | 0 | 0 | 0 | No failed messages |
| Unknown | 0 | 0 | 0 | No unknown messages |
| Cancelled | 0 | 0 | 0 | Campaign not cancelled |
| Duplicate sends | 0 | 0 | 0 | Distinct keys/provider IDs; second pass claimed nothing |
| Resend links | 0 | 0 | 0 | No resend workflow |

**Invariant:** approved recipients = messages = jobs = `2`.

### 6.2 Results and history

- `GET /api/v1/campaigns/{id}/results`: status `completed`, `message_count=2`, counts `delivered=2`, all other message statuses `0`, total `SYP 1,100,000.00`.
- `GET /api/v1/messages?campaign_id={id}`: total `2`; both `internal_status=delivered`, `provider_status=delivered`; both show the masked phone `+963 9•• ••• 701`.
- `GET /api/v1/messaging/ops/jobs?campaign_id={id}`: total `2`; both `job_status=completed`, `attempt_count=1`, no lease/lock, no error.
- `GET /api/v1/messaging/ops/issues?kind=unknown`: `0`; `kind=failed`: `0`.
- Ops summary after the run: `pending=0`, `claimed=0`, `retry=0`, `due_now=0`, `stale_claims=0`; `failed=0`, `unknown=0`, `reconciliation_required=0`; `provider_events.unprocessed=0`.

### 6.3 Privacy checks

- Message history, campaign results, and operations job/detail surfaces returned masked phones only. The ops message detail returned `destination_phone_masked` and did **not** include `destination_phone` or `message_body_snapshot`.
- The explicit `GET /api/v1/messages/{id}` detail remains the documented reveal surface for `messages.view` and returns the full destination and frozen body. It was used only to confirm field shape; no full phone or body is recorded here.
- No provider payload contains a real key, sender, or external request. The fake payload is metadata only (`provider=fake`, `scenario`, `channel`).

### 6.4 No send/resend control

- `POST /api/v1/messages/{id}/resend` → `404`.
- `POST /api/v1/campaigns/{id}/send` → `404`.
- The only send-like OpenAPI path is `/api/v1/messaging/test-send`, which is the existing fake-only, allowlist-gated dry-run test-send surface. There is no campaign send/resend endpoint and no send/resend button in the UI.
- Unknown outcomes remain reconciliation-only; no retry or resend action was available or used.

---

## 7. Layout and console checks

Browser checks used Chromium through Playwright with an authenticated admin session. Viewports were `1024×800` and `1440×900`. Pages checked: dashboard `/`, operations `/operations`, campaign results `/campaigns/{id}/results`, and message history `/messages?campaign_id={id}`.

| Viewport | Page | HTTP | Horizontal overflow | Console errors | Page errors |
|---|---|---:|---|---:|---:|
| 1024×800 | Dashboard | 200 | none | 0 | 0 |
| 1024×800 | Operations | 200 | none | 0 | 0 |
| 1024×800 | Campaign results | 200 | none | 0 | 0 |
| 1024×800 | Message history | 200 | none | 0 | 0 |
| 1440×900 | Dashboard | 200 | none | 0 | 0 |
| 1440×900 | Operations | 200 | none | 0 | 0 |
| 1440×900 | Campaign results | 200 | none | 0 | 0 |
| 1440×900 | Message history | 200 | none | 0 | 0 |

Observed content:

- Dashboard loaded its KPI/activity data; it is an aggregate view and does not list the individual rehearsal campaign. The campaign is visible in Campaigns, Campaign results, and Message history.
- Operations showed the fake provider strip, the masked-only notice, an empty due/stale queue, `0` failed, `0` unknown, `0` reconciliation-required, and `0` unprocessed provider events.
- Campaign results showed the campaign name, `completed` status, total `2`, delivered `2`, the delivery caveat, and the two masked-phone rows.
- Message history showed the campaign name and both delivered rows with masked phones.
- No visual overflow was detected at either width (`scrollWidth == clientWidth`).

**Request-failure note:** Playwright recorded Next.js RSC prefetch requests as `net::ERR_ABORTED` during rapid navigation (25 at 1024, 31 at 1440). These are cancelled prefetches, not console errors, page errors, or failed API data loads; all four pages rendered their expected data. No user-facing failure was observed.

---

## 8. Defects and observations

**Blocking defects:** none found in this fake-provider rehearsal.

| Item | Classification | Note |
|---|---|---|
| `SHARED_PHONE` warning on both eligible recipients | Data/policy observation | Synthetic data shares one masked number. The warning was acknowledged as designed. A real pilot needs a written school decision on shared-phone recipients. |
| Dashboard does not show the individual campaign | Observation, not a defect | Dashboard is an aggregate view; campaign-level evidence is in Campaigns/results/history. |
| Message detail exposes the full destination/body to `messages.view` | Documented design boundary | H3/M1 masking applies to lists, results, and ops. The explicit detail view remains a controlled reveal surface and was not used for bulk export. |
| Next.js RSC prefetch `ERR_ABORTED` entries | Test-harness noise | No console errors, page errors, or failed page data; recorded for transparency. |
| No real delivery/reconciliation evidence | Expected limitation | The fake adapter cannot prove Rasel delivery or provider-side reconciliation. That remains a live pilot/G4 activity. |

No message was marked delivered by a real provider. No duplicate, wrong-recipient, unknown, or failed message was observed in this scope.

---

## 9. Stop/rollback rehearsal note

A stop/disable rehearsal was run in an **isolated worker process** after the campaign reached `completed`. It did not change `.env.local`, the running API, the campaign, messages, jobs, audit rows, or account state.

| Configuration | Worker result | Fake send count |
|---|---|---:|
| `MESSAGING_ENABLED=true`, `MESSAGING_KILL_SWITCH=true` | `claimed=false`, `skipped_reason=kill_switch` | 0 |
| `MESSAGING_ENABLED=false`, `MESSAGING_KILL_SWITCH=true` | `claimed=false`, `skipped_reason=messaging_disabled` | 0 |

**What this proves:** a worker started with the kill switch on, or with messaging disabled, claims no job and sends nothing. The setting is read at process start; a running worker must be stopped and restarted for an environment change to take effect.

**Not exercised:** a real campaign cancellation, job/lease manipulation, database restore, or live-provider rollback. Those remain runbook steps and would modify or destroy this rehearsal evidence. In a real stop, follow `first-campaign-runbook.md` §6 and §8: stop the worker, set the kill switch/disabled flags, restart the relevant processes, preserve IDs/logs/snapshots, do not delete or edit message state, and do not resend.

The rehearsal state is already the safe fake/disabled-capable baseline; no live provider credential or destination was used.

---

## 10. Evidence retained

- Synthetic campaign `05b751fe-2ec6-4bf9-9758-158e88fdea2a` is retained with 2 delivered fake messages, 2 completed jobs, the approval snapshot hash, and campaign audit events.
- No data was deleted. No user account was deactivated.
- This document contains no full phone numbers, guardian/student names, message bodies, credentials, or secrets.

**Rehearsal result:** PASS within the fake-provider scope described above.  
**Gate status:** G0/G4/G5 remain open; this rehearsal does not close them or authorise a live send.
