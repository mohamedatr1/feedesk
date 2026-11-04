# M3 — Campaign and Approval Verification Plan

**Purpose:** Independent checks after the campaign backend/frontend lanes finish. M3 verifies preparation and approval only; nothing is sent.

## 1. API smoke

Use an admin session for approval and a staff session for submit/permission checks.

1. Create a template version; verify the previous version is deactivated and the new version is active.
2. Create a second version with an unknown variable; verify the campaign preview blocks approval with `UNRESOLVED_VARIABLES` until corrected.
3. Create a campaign from a confirmed import:
   - eligible recipients grouped by guardian + currency;
   - zero balances excluded;
   - missing/invalid phones excluded with reasons;
   - shared phone produces a warning, not a merge;
   - totals match confirmed fee balances per currency.
4. `PATCH` draft name/template; verify revision increments and preview refreshes.
5. Submit as staff; verify `awaiting_approval`.
6. Attempt approve as staff → `403`.
7. Approve as admin without warning acknowledgment when warnings exist → `422 WARNINGS_UNACKNOWLEDGED`.
8. Approve with acknowledgment:
   - status `approved`;
   - `snapshot_hash` is 64 hex chars;
   - one `campaign_recipients` row per eligible recipient;
   - one `messages` row and one `send_jobs` row per recipient, all pending;
   - no `provider_events`, no network call, no worker.
9. Re-approve → same detail; no duplicate messages/jobs.
10. Change a guardian phone/fee balance after approval; verify the snapshot and hash do not change.
11. Revision conflict on submit/approve/cancel → `409 CAMPAIGN_CHANGED`.
12. Cancel an approved campaign; verify status `cancelled`, messages/jobs cancelled, recipient snapshots retained.
13. Try to update/delete an approved recipient directly in PostgreSQL; verify the trigger blocks it.
14. Verify audit events: `campaign.create`, `campaign.update`, `campaign.submit`, `campaign.approve`, `campaign.cancel`, `template.create`, `template.activate`.

## 2. Financial and eligibility assertions

- Only `confirmed` fee balances enter a campaign.
- Amounts are Decimal/NUMERIC and serialized as strings.
- Per-currency totals never combine currencies.
- Zero/negative balances are excluded with reasons.
- Missing/invalid phones are excluded with reasons.
- Inactive guardians are excluded.
- Shared phone across different guardians remains two recipients with a warning.
- Approval warning acknowledgment is required only when warnings exist.
- Source changes after approval do not affect the snapshot.

## 3. Snapshot integrity

- Recompute canonical JSON from persisted campaign/recipients and compare SHA-256 to `snapshot_hash`.
- Snapshot includes guardian id/name, destination phone, amount, currency, message, template id/version/body, approver, approval timestamp, fee balance ids, students, periods.
- Approval is all-or-nothing; force an error mid-transaction in a test and verify no partial rows.

## 4. UI checks

- Campaign list: status filters, counts, per-currency totals, creator/approver, empty/loading/error.
- Builder: only confirmed imports; active template; explicit draft creation; no auto-approval.
- Review: summary, excluded reasons, recipient table, per-message dialog, warning acknowledgment, submit/approve disabled reasons, cancel reason.
- Approved: read-only frozen view, hash, no send button, clear "sending not enabled" notice.
- Templates: admin version list/editor/activation, unknown-variable warning, staff read-only.
- RTL tables, 44px controls, labels, 1440/1024/768.
- No fake totals or fake delivery state.

## 5. Security checks

- Mutating routes require CSRF.
- Staff cannot approve or manage templates.
- Admin can approve.
- Approved snapshots cannot be edited through any endpoint.
- No provider secrets or phone data in logs.
- No Rasel call, worker, or send job execution occurs.

## 6. Out of scope

- Actual sending, provider adapter, worker, retries, delivery status, campaign results, message history.
- School copy approval and real recipient data.

## 7. Execution record

Executed checks and results are in `verification.md`. Synthetic fixtures validate the campaign pipeline; they do not replace real school data or school-approved copy for G3.
