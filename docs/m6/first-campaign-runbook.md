# FeeDesk M6 — First Controlled Campaign Runbook

**Document ID:** M6-CAM-01  
**Version:** 0.1 (template; not authorised for live use)  
**Date:** 4 November 2026  
**Status:** **Blocked until G0 passes and a written G4 pilot authorisation is signed. This campaign is itself G4 pilot evidence; G4 is not passed until the pilot and reconciliation are accepted.**  
**Audience:** School admin, technical owner, provider/ops, security.  
**Related:** `handover-pack.md`, `support-model.md`, `post-implementation-review.md`, `docs/runbooks/`.

> **Do not run this against live guardians yet.**
>
> G0 is not passed (no approved sender, no Syrian test delivery, no free-text plan, no real samples). G4 is not passed (no live test-send, no verified reconciliation, no controlled pilot). No production host, TLS, delivered alert, production backup/restore drill, UAT, or training exists. Every live step below is **blocked** until G0 evidence exists and a written G4 pilot authorisation is signed.
>
> This runbook is not a launch authorisation. It is the procedure for the pilot that may close G4 — not for a general send.

---

## 1. Purpose / الغرض

Run the smallest safe live campaign that can prove the end-to-end path — import → approval → provider acceptance → results → reconciliation — without exposing the wider guardian population. The first campaign is a controlled pilot, not a general send.

**Arabic summary / ملخص عربي**

هذا الدليل مخصص لأول حملة تجريبية خاضعة للرقابة بعد اجتياز G0/G4 وتوقيع قرار المضي. لا يجوز استخدامه لإرسال عام أو قبل استلام موافقة المدرسة. أي خطوة حقيقية تبقى **محجوبة** حتى تتوفر أدلة البوابة والنسخ الاحتياطي والمراقبة والدعم.

---

## 2. Authority and roles

| Role | Responsibility in this campaign |
|---|---|
| School director / authorised representative | Approves the cohort, copy, and go/no-go; owns school communication |
| School data owner | Confirms data scope, retention, and privacy constraints |
| School admin | Prepares/approves the campaign; operates the UI; first-line school contact |
| Technical owner | Host, deploy, worker, backup, monitoring, kill switch, evidence |
| Provider/ops | Sender, balance, provider console, delivery/reconciliation evidence |
| Security | Incident command, custody, privacy escalation |
| Stop authority | Named in §3.2; may stop without waiting for consensus |

**One incident commander** must be named for the campaign window. The commander is not necessarily the approver.

---

## 3. Preconditions and gate evidence

### 3.1 Gate evidence

| Gate | Required evidence | Status | Evidence reference |
|---|---|---|---|
| G0 | Approved sender ID; free-text plan/enablement; 3 school-controlled Syrian `+963` numbers; delivered test SMS; provider record; real anonymised samples/taxonomy; school decisions | **Blocked** (open) |  |
| G4 pilot authorisation | Written authorisation to run this controlled pilot; live test-send; delivery/reconciliation contract agreed; pilot plan and reconciliation owner named | **Blocked** (authorisation required) |  |
| G4 closure | This pilot’s results + provider reconciliation + signed pilot report | **Blocked** (not started) |  |
| G5 / wider launch | OPS-01..OPS-10 closed; UAT; training; go/no-go | **Blocked** (open; not required for the pilot) |  |
| School approval | Cohort, copy, opt-out, currency, retention, support window | **Blocked** (pending) |  |
| Technical readiness | Host, TLS, backup, monitoring, runbooks, access | **Blocked** (not verified) |  |

**Rule:** G0 must be **Pass**, and a written **G4 pilot authorisation** must exist. G5 is not required for the pilot. If G0 is not Pass or the pilot authorisation is missing, stop. Do not substitute a fake-provider result for a gate.

### 3.2 Pre-flight checklist — approvals and policy

- [ ] Written go/no-go signed by the school director and technical owner.
- [ ] Cohort agreed in writing: count, selection rule, exclusions, currency, language.
- [ ] Arabic copy approved by the school, including opt-out/contact wording.
- [ ] Sender ID approved and recorded (exact provider sender, not a guess).
- [ ] Opt-out/communication-restriction policy applied; restricted guardians excluded.
- [ ] Retention/privacy policy for the campaign data signed, or the campaign is explicitly outside retention scope with data-owner approval.
- [ ] Support window, contacts, and stop authority named.
- [ ] School knows this is a pilot and may receive questions from guardians.
- [ ] No promise of delivery date or delivery guarantee has been made.

### 3.3 Pre-flight checklist — provider

- [ ] Provider account active; plan permits free-text SMS to Syria.
- [ ] Sender approved and visible in the provider console.
- [ ] Three school-controlled Syrian `+963` test numbers recorded; consent confirmed.
- [ ] A real test SMS was delivered through the approved route and reconciled.
- [ ] Provider balance checked; cost estimate for the cohort recorded; low-water mark agreed.
- [ ] Rate limit/segments/pricing confirmed for the cohort.
- [ ] Delivery-report/reconciliation method confirmed (console, report, or read-only call).
- [ ] Provider ticket/contact available for the campaign window.
- [ ] `RASEL_SENDER_ID`, `RASEL_CHANNEL`, `RASEL_BASE_URL` verified without printing the API key.
- [ ] Provider credential source is confirmed (encrypted DB vault preferred; approved env fallback allowed) and is `configured=true`; rotation/revocation path known.

### 3.4 Pre-flight checklist — allowlist and test numbers

- [ ] `MESSAGING_ALLOWLIST` contains only approved E.164 numbers for the pilot/test.
- [ ] The allowlist is not widened to the whole school “to save time.”
- [ ] Test numbers are school-controlled, not guardian numbers.
- [ ] Test messages contain no real guardian/student data.
- [ ] The effect of the allowlist on the pilot cohort is understood and tested: a **non-empty** allowlist blocks every recipient not listed (`RECIPIENT_NOT_ALLOWLISTED`, failed without send). Either list every approved pilot number or confirm in writing that an empty allowlist is permitted for the approved cohort.
- [ ] The exact allowlist is recorded; removing a number is part of the stop procedure.

### 3.5 Pre-flight checklist — templates and copy

- [ ] Active template version is the school-approved version.
- [ ] Variables resolve deterministically for every recipient; no `UNKNOWN_VARIABLE` blockers.
- [ ] Currency, amount, school name, and contact details are correct.
- [ ] Student names are omitted by default unless the school explicitly approved them.
- [ ] Opt-out/contact wording is present and approved.
- [ ] Arabic review completed by a named school reviewer.
- [ ] Preview checked for at least 3 recipients across currencies/amount formats.
- [ ] No message body contains internal notes, IDs, or staff-only text.
- [ ] Character/segment count checked; no accidental multi-segment cost surprise.

### 3.6 Pre-flight checklist — data and campaign

- [ ] Import is confirmed; source file hash and batch ID recorded.
- [ ] Review is complete; no unreviewed blocking errors.
- [ ] Per-currency totals reconcile to the source; any discrepancy explained.
- [ ] Duplicates and shared phones reviewed; no phone-only guardian merge.
- [ ] Invalid/missing phones excluded with reason.
- [ ] Zero/negative balances and inactive guardians excluded per policy.
- [ ] Guardian resolution cases closed.
- [ ] Cohort count matches the approved list; any change re-approved.
- [ ] Campaign preview shows the correct recipients, exclusions, warnings, totals, and template version.
- [ ] Approval snapshot hash recorded.
- [ ] Pending messages = pending jobs = approved recipients.

### 3.7 Pre-flight checklist — technical and backup

- [ ] Release/commit pinned; image tags recorded; rollback target known.
- [ ] Host healthy: disk >15%, DB reachable, time sync, TLS valid.
- [ ] `api`, `web`, `proxy`, `db` healthy; exactly one worker.
- [ ] Worker startup shows the intended provider, `enabled=true` only if authorised, `kill_switch=false` only if authorised.
- [ ] Queue is empty or explained; no stale `submitting`/`unknown` backlog.
- [ ] Monitoring/alerts active; on-call recipient confirmed.
- [ ] Encrypted backup completed **before** the campaign; manifest and SHA-256 recorded.
- [ ] Uploads included in the backup; restore path known (or explicitly accepted as a gap).
- [ ] A current restore point exists; RPO/RTO accepted for the campaign.
- [ ] No deploy, migration, role change, or key rotation during the campaign window.
- [ ] `MESSAGING_MAX_ATTEMPTS`, `MESSAGING_LEASE_SECONDS`, and rate are set to the approved low values.
- [ ] Kill-switch procedure and worker-stop command are open in the operator console.

### 3.8 Pre-flight checklist — communication

- [ ] School staff know the pilot time and which guardians are included.
- [ ] A school contact can answer guardian questions.
- [ ] The school approved the wording for “if you received this in error.”
- [ ] No correction campaign will be sent without a new approval.
- [ ] Incident bridge/chat is staffed; no PII in it.

**Pre-flight result:** ☐ Pass — complete §4 and proceed to §5  ☐ Fail — stop and record reasons

---

## 4. Pilot design

These are **proposals**, not school decisions.

| Design choice | Proposed | School decision |
|---|---|---|
| Cohort size | 10–20 guardians (or 5–10 for the first hour) |  |
| Selection | One confirmed import, one currency, one template, no special cases |  |
| Exclusions | Complaints, opt-outs, invalid phones, inactive guardians, zero/negative balances, unresolved identity |  |
| Timing | School-approved window with support staff present |  |
| Rate | 1 message/second, low max attempts |  |
| Success | 100% of approved recipients have a known outcome; 0 duplicates; 0 wrong content; totals reconcile |  |
| Failure | Any unknown/duplicate/wrong send triggers stop and review |  |

**Do not** include the whole school, multiple currencies, or multiple templates in the first controlled campaign unless the school explicitly accepts the added risk.

---

## 5. Execution sequence

> All steps require §3 to pass. Commands are in `docs/runbooks/`; this section describes the order and controls.

### Step 0 — Go/no-go meeting (10 minutes)

- Confirm gate evidence, cohort, copy, balance, backup, monitoring, and stop authority.
- Record attendees and decision.
- If anyone cannot confirm a critical item, stop.

### Step 1 — Freeze and snapshot

- Stop imports, settings changes, user changes, and template edits for the window.
- Take/confirm the pre-campaign backup; record manifest hash and time.
- Record current queue/message counts (pending, failed, unknown, submitting).
- Confirm no campaign is already sending.

### Step 2 — Verify provider and configuration

- Read-only provider check: account, sender, balance, channel.
- Confirm credential vault status without displaying the key.
- Confirm `MESSAGING_PROVIDER=rasel`, `MESSAGING_ENABLED=true`, `MESSAGING_KILL_SWITCH=false` **only if G4 authorises live sending**; otherwise keep fake/disabled.
- Confirm allowlist and rate.
- Confirm worker is single and healthy.

### Step 2b — Approved test-send (G4 evidence)

- Use only the three school-controlled `+963` numbers and approved test wording.
- Confirm the allowlist, send one test, and reconcile the provider record.
- Verify no duplicate, correct sender, and an acceptable message body.
- Record the provider message ID and result.
- Do not include guardian/student data in the test.

### Step 3 — Create and preview the campaign

- Create from the confirmed import.
- Apply the approved cohort/exclusions.
- Verify recipient count, per-currency totals, warnings, template version, and preview.
- If anything differs from the approved list, stop and re-approve.

### Step 4 — Approve

- School admin approves with warning acknowledgement.
- Record snapshot hash, approver, time, recipient count, message/job count.
- Approval creates pending jobs; no provider call yet.

### Step 5 — Start sending

- Start exactly one worker.
- Watch the first message through claim → submitting → provider response → terminal.
- Confirm no duplicate claim, no second send, and the expected provider record.
- Continue at the approved rate.

### Step 6 — Monitor

| Time | Checks |
|---|---|
| First 5 minutes | Continuous: queue, worker logs, provider errors, unknown/failed counts, duplicate indicators |
| Every 15 minutes until terminal | Counts, provider balance, worker liveness, 5xx, school questions |
| 1 hour after terminal | Final counts, any late provider update, reconciliation start |
| Next business day | Delivery evidence, unresolved unknowns, school feedback |

**Do not** leave the window unattended. If staffing is insufficient, reduce the cohort or postpone.

### Step 7 — Stop and reconcile

- Stop the worker when the queue is empty or a stop condition occurs.
- Reconcile before any wider send.
- Do not start a second campaign until this one has a known outcome.

---

## 6. Stop conditions

Stop the worker and set the kill switch immediately if any of the following occurs. Do not wait for the next scheduled check.

| # | Condition | Immediate action |
|---|---|---|
| 1 | Any `unknown` message | Stop worker; preserve IDs; follow `unknown-outcomes.md`; no resend |
| 2 | Any duplicate send or duplicate provider acceptance | Stop; preserve provider/message evidence; quantify; notify school/security |
| 3 | Wrong recipient, amount, currency, school name, or message body | Stop; preserve snapshot; notify school; no correction send without approval |
| 4 | Provider auth, sender, balance, or plan error | Stop; classify; provider ticket; no retry until fixed |
| 5 | Provider 5xx/timeout spike or status-page outage | Stop; kill switch; provider ticket; no blind retry |
| 6 | Queue stalled >5 minutes or worker crash loop | Stop; worker recovery runbook; do not start a second worker |
| 7 | 5xx rate >2% for 10 minutes and rising | Stop; check deploy/DB; rollback if new |
| 8 | Suspected unauthorised access or key compromise | Stop; security incident; revoke/rotate; preserve evidence |
| 9 | School requests a stop | Stop immediately; confirm in writing |
| 10 | Data/totals no longer reconcile | Stop; do not approve further; investigate import/campaign |
| 11 | Backup/monitoring failure during the window | Pause unless the campaign is already terminal; fix before continuing |
| 12 | Any S1 incident | Stop; incident command; school notification |

### Stop procedure

```text
1. Stop the worker.
2. Set MESSAGING_KILL_SWITCH=true and MESSAGING_ENABLED=false.
3. Recreate API (and worker only when safe) so the setting is loaded.
4. Preserve logs, message/job IDs, provider IDs, and the approved snapshot.
5. Do not delete jobs, clear leases, edit message status, or resend.
6. Notify the incident commander, school admin, and provider/ops.
7. Record time, reason, operator, and current counts.
8. Reconcile before any restart.
```

**Note:** settings are read at process start. Do not assume a running worker picked up an env change; stop it.

---

## 7. Reconciliation

### 7.1 Required counts

| Check | Expected | Actual | Difference | Explanation |
|---|---:|---:|---:|---|
| Approved recipients |  |  |  |  |
| Messages created |  |  |  |  |
| Jobs created |  |  |  |  |
| Provider accepted |  |  |  |  |
| Provider delivered (evidence) |  |  |  |  |
| Failed |  |  |  |  |
| Unknown |  |  |  |  |
| Cancelled |  |  |  |  |

**Invariant:** approved recipients = messages = jobs. Provider accepted may be lower; delivered may be lower than accepted. Never force the numbers.

### 7.2 Evidence

- Provider console/report with message IDs and timestamps.
- FeeDesk message IDs, idempotency keys, attempts, error codes.
- Campaign snapshot hash and approver.
- Worker logs (no PII) and queue counts.
- School confirmation of any guardian-reported duplicate/non-receipt.

### 7.3 Unknowns

- Do not resend.
- Record provider result: accepted / rejected / not found.
- “Not found” does not mean “not sent.”
- Get a second reviewer before any status correction.
- If unresolved, leave the campaign in `completed_with_errors` and assign an owner.

### 7.4 Closeout

- [ ] All approved recipients have a known outcome or an explicit unresolved owner.
- [ ] No duplicate/wrong send remains unexplained.
- [ ] Provider balance/usage reconciled.
- [ ] School informed of counts and any follow-up.
- [ ] Evidence stored; no PII in shared records.
- [ ] Post-implementation review scheduled (`post-implementation-review.md`).

---

## 8. Rollback and disable

### 8.1 Disable sending (preferred)

Use when the campaign must stop but data is intact.

```text
1. Stop the worker.
2. Set MESSAGING_KILL_SWITCH=true.
3. Set MESSAGING_ENABLED=false.
4. Recreate API; recreate worker only when it will stay disabled.
5. Confirm readiness and that no new jobs are claimed.
6. Preserve pending jobs and terminal outcomes; do not delete.
```

### 8.2 Revert to fake provider

Use for a safe local/staging state, never to “test” live delivery.

```text
MESSAGING_PROVIDER=fake
MESSAGING_ENABLED=false
MESSAGING_KILL_SWITCH=true
MESSAGING_ALLOW_FAKE_IN_PRODUCTION=false
```

Recreate API/worker; confirm worker logs show fake/disabled/kill-switch on.

### 8.3 Cancel a campaign

- Cancel only if the campaign is not terminal and the UI permits it.
- Cancellation must not overwrite terminal message outcomes (fixed behaviour).
- Do not delete messages, jobs, audit events, or the approved snapshot.
- Record who cancelled, when, and why.

### 8.4 Restore (only for data corruption/loss)

- Stop worker, then web/api.
- Preserve the current database/uploads even if broken.
- Get written school approval for the data-loss window.
- Follow `docs/runbooks/backup-restore.md`; restore to a new database/volume, verify, then switch.
- Never use `docker compose down -v`.
- Record RPO/RTO actuals and data-loss window.

### 8.5 School communication

- Tell the school what happened, how many recipients are affected, and what is unresolved.
- Do not send a guardian-facing correction without school approval and approved wording.
- Do not blame the provider before evidence.
- Use counts and internal IDs, not guardian identities.

---

## 9. Campaign record template

```text
Campaign ID:
Campaign name:
Import batch ID / source hash:
Template version / snapshot hash:
Approved by / time:
Cohort rule / count:
Currency(ies) / totals:
Exclusions by reason:
Provider / sender / channel:
Balance before / after:
Backup ID / manifest hash:
Worker start / stop:
Messages: created / accepted / delivered / failed / unknown / cancelled
Duplicates / wrong sends:
Incidents:
Reconciliation owner / date:
School sign-off:
Post-implementation review ID:
```

---

## 10. Post-campaign checklist

- [ ] Campaign is terminal; no pending jobs left unexplained.
- [ ] Unknowns reconciled or assigned; no resend.
- [ ] Provider evidence attached.
- [ ] School received the result summary.
- [ ] Support tickets linked to the campaign.
- [ ] Defects/incidents logged.
- [ ] Backup still healthy after the campaign.
- [ ] Monitoring showed no unresolved alert.
- [ ] Access/key changes (if any) recorded.
- [ ] Post-implementation review scheduled.
- [ ] Wider rollout remains **blocked** until the review’s go/no-go.

---

## 11. Sign-off

| Role | Name | Confirms | Signature | Date |
|---|---|---|---|---|
| School director / authorised representative |  | Cohort, copy, go/no-go |  |  |
| School data owner |  | Data scope/retention |  |  |
| School admin |  | Campaign prepared/approved |  |  |
| Technical owner |  | Host/backup/monitoring ready |  |  |
| Provider/ops |  | Sender/balance/reconciliation ready |  |  |
| Security |  | Incident/custody readiness |  |  |

**Pre-flight result:** ☐ Pass  ☐ Fail  
**Campaign decision:** ☐ Go  ☐ Hold  ☐ Cancel

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 4 Nov 2026 | Initial first-campaign runbook template; live steps blocked | Documentation pass |
