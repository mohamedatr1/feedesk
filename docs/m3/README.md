# M3 — Campaign Management and Approval

**Status:** Core implementation complete; backend/API/frontend checks, full browser walkthrough, dialog focus-trap re-check, and dashboard/reporting (`RPT-01..03`) pass. Sending remains disabled; G3 is pending school copy approval and real data.

| Document | Purpose |
|---|---|
| `api-contract.md` | Binding campaign, template, eligibility, rendering, and approval contract |
| `subagent-brief.md` | Lane scopes, environment, rules, acceptance |
| `qa-plan.md` | Independent campaign/approval verification plan |
| `verification.md` | Executed backend/API/frontend checks and snapshot evidence |
| `../design/m3-campaign-screens.md` | Campaign/template screen spec |
| `../m2/verification.md` | Confirmed import data and M2 evidence |
| `../m4/verification.md` | Worker/message/control-plane evidence used by the dashboard counts |

## Scope

Confirmed balances → guardian/currency grouping → eligibility and exclusion reasons → template rendering → draft → submit → approval snapshot → pending messages/jobs. No worker and no provider call.

## Out of scope

Live SMS, Rasel adapter, worker execution, delivery statuses, retries, message history, and campaign results. Dashboard/reporting metrics (`RPT-01..03`) are now implemented in M3 with synthetic data: metrics API, dashboard UI, and an idempotent daily snapshot job. G3 still requires school copy approval and real data.

## Done when

- A campaign can be created from a confirmed import.
- Eligible recipients are grouped by guardian and currency; exclusions show reasons.
- Every message can be previewed; unresolved variables block approval.
- Approval records the approver, freezes an immutable hash, and creates pending messages/jobs transactionally.
- Source edits after approval do not change the snapshot.
- An unapproved campaign cannot be sent; no send action exists in M3.
- Formal G3 remains pending real samples and school copy approval.
