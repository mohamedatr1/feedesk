# M3 — Verification Record

**Date:** 3 November 2026  
**Scope:** Synthetic fixtures only. No live SMS, provider call, worker, or delivery status exists in M3.

## Backend and schema

| Check | Command | Result |
|---|---|---|
| Lint | `ruff check app tests` | Pass |
| Tests | `pytest -q` | 104 passed at the M3 slice (current suite: 425) |
| Migration drift | `alembic check` | No new upgrade operations |
| Migration head | `alembic current` | `a9b8c7d6e5f4` |

## API smoke

Fixture: confirmed import `9ea965b7-2a5a-4750-a76b-01590a24ece5` from `m3-campaign-sample.xlsx` (two eligible shared-phone recipients, one zero-balance exclusion, one missing-phone exclusion).

Passed:

- Template v1 created; v2 created and auto-activated; unknown variable `unknown_x` detected; staff template management rejected with `403`; v1 reactivated.
- A draft using the unknown-variable template was created but blocked with `UNRESOLVED_VARIABLES`; `can_submit=false`; cancelled.
- Campaign creation without CSRF rejected with `403`.
- Main campaign: 2 recipients, 2 exclusions, `SYP 1,100,000.00`, `SHARED_PHONE` warning count 2, valid E.164 phones, no unresolved variables in messages.
- Staff sees `can_submit=true`, `can_approve=false`; no messages before approval.
- Draft edit increments revision; stale submit gets `409 CAMPAIGN_CHANGED`.
- Staff submits; admin sees `can_approve=true`; staff approve gets `403`.
- Approve without warning acknowledgment gets `422 WARNINGS_UNACKNOWLEDGED`; with acknowledgment succeeds.
- Approved detail: status `approved`, 64-char hash `22a55be6…b9ef9b`, 2 frozen recipients, 2 frozen exclusions, `message_count=2`, `pending_job_count=2`.
- Re-approve is idempotent; no duplicate messages/jobs.
- Database: 2 `campaign_recipients`, 2 `messages` pending, 2 `send_jobs` pending, no `provider_events`.
- Direct update of an approved recipient is blocked by the database trigger.
- Cancel approved persists the reason, keeps the snapshot/hash and recipients, and marks messages/jobs `cancelled`.
- A second draft cancels cleanly.

## Snapshot and safety

- Approval freezes recipients, excluded records, warnings, template version/body, approver, timestamp, and hash in one transaction.
- Source edits after approval do not change the snapshot; backend tests cover this.
- The canonical snapshot hash is SHA-256 over sorted campaign/template/approver/recipient data.
- Approval creates one pending message and one pending send job per recipient; no provider adapter, worker, network call, or delivery state exists.

## Frontend

| Check | Command | Result |
|---|---|---|
| Typecheck | `npm run typecheck` | Pass |
| Production build | `npm run build` | Pass; 15 routes at the M3 slice (current: 16) |
| Dependency audit | `npm audit --omit=dev` | 0 vulnerabilities |

## Dashboard/reporting (`RPT-01..03`, 4 November 2026)

- `GET /api/v1/dashboard` returns per-currency confirmed/positive totals as decimal strings, operational counts, action queue, recent activity (no audit payloads), and trend snapshots.
- Dashboard UI renders per-currency totals, counts, action queue, activity, and per-currency deltas only when snapshot history exists; no fabricated deltas.
- Daily snapshot CLI (`python -m app.dashboard.snapshot --date YYYY-MM-DD`) is idempotent; a repeat run for the same date left one row.
- Browser verification: dashboard totals `SYP 6,850,000.00` + `USD 800.00`, action queue, activity, trends hint with insufficient history, 1024/1440 no overflow, 0 console errors.
- G3 remains open because school-approved Arabic copy and real data are still required.

## Browser walkthrough

Playwright run on 3 November 2026 against the running web/API stack.

Passed:

- Staff login and campaign list: 3 rows initially, status tabs/counts, filters, per-currency totals, create CTA.
- Builder: 4 confirmed-import cards, seed template selection, raw template body/variables, readiness checklist, no-send notices; draft created.
- Draft detail: 2 recipients, 2 exclusions, 1 warning, `SYP 1,100,000.00`, shared-phone warning, zero/missing-phone reasons, 2 recipient rows with the shared E.164 phone, rendered message preview with amount/currency and no unresolved variables.
- Submit dialog; campaign moved to `بانتظار الاعتماد`; staff saw `الاعتماد متاح لمدير النظام` and no approve control.
- Admin approve dialog: warning list, no-send boundary, primary action disabled until acknowledgment; approval returned `200`.
- Approved detail: exact status `معتمدة`, green snapshot card, approver/time, 64-char hash `75fd329b…e44385a`, 2 frozen recipients/exclusions, `message_count=2`, `pending_job_count=2`, permanent `لم تُرسل أي رسالة`, and no send/edit/submit affordance.
- Template admin: grouped versions, active/inactive badges, editor from the seed template, save-as-version created seed v2 and activated it; staff template screens were read-only.
- Responsive: 1024/1440 pages all reported `documentElement.scrollWidth === clientWidth`; tables fit their wrappers and dialogs fit.
- Keyboard: create/submit/approve reachable with a visible focus ring; Esc closed dialogs without action.
- Zero console errors, page errors, failed non-prefetch requests, or HTTP ≥400 during the final flow. No `/send`, provider host, DELETE, or batch cancel.

Defect and fix:

- **Medium accessibility:** native `<dialog>` focus cycling leaked one Tab stop to `BODY` in submit, approve, and message-preview dialogs. Fixed in the shared `Dialog` with an explicit Tab/Shift+Tab cycle over visible, enabled focusables. Targeted re-check passed: 12 forward and 12 backward Tabs per dialog across four dialog states, zero `BODY` hits, zero outside-dialog stops, Esc closed without action.
- Observation: shared-phone recipients correctly render as `تحذير` rather than `صالح`; they are eligible and included, and the warning requires approval acknowledgment.

Evidence: `C:\Users\IT DOCTOR\AppData\Local\Temp\opencode\m3-ui\` and `...\m3-ui-focus\` (temporary, not in the repository).

## Notes

- The seeded Arabic template is draft copy. School copy approval remains a G3/launch blocker. The browser walkthrough created seed template version 2 for verification; it remains stored but inactive, and version 1 was restored as the active draft after cleanup.
- The M3 UI deliberately has no send affordance in any state; approved campaigns show a read-only snapshot and a permanent “nothing sent” notice.
- M3 does not include the dashboard/reporting tasks (`RPT-01..03`) or message history/results.
- The temporary M3 admin/staff QA accounts were deactivated and their sessions revoked after verification. Synthetic campaigns and template versions remain in the development database for inspection; no real guardian data was used.
