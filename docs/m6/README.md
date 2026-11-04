# M6 — Pilot, Hypercare, and Handover (Pre-Launch Drafts)

**Status:** Draft only. No first controlled campaign, hypercare, training delivery, handover acceptance, or launch has occurred. G0/G4/G5 remain open. These documents prepare the school and technical owner without claiming production readiness.

| Document | Purpose |
|---|---|
| `training-guide-ar.md` | Arabic admin/staff training modules, synthetic-data exercises, troubleshooting, and sign-off |
| `first-campaign-runbook.md` | Pre-flight gates, controlled pilot sequence, stop conditions, reconciliation, and rollback/disable |
| `support-model.md` | Ownership, support tiers, incident categories, evidence rules, and communication templates |
| `credential-handover.md` | Credential custody, rotation/revocation, break-glass rules, and handover ceremony (names only; no secrets) |
| `post-implementation-review.md` | First-campaign/hypercare review template and wider-rollout go/no-go |
| `handover-pack.md` | Architecture, roles, env names, runbook index, known limitations, open gates, acceptance checklist |
| `handover-readiness-review.md` | Internal readiness review; **NOT ACCEPTED** for operational handover |
| `pilot-rehearsal.md` | Fake-provider end-to-end pilot rehearsal (not the live first campaign) |
| `training-rehearsal.md` | Internal browser rehearsal of staff/admin modules (not school training delivery) |

## Hard constraints

- Training uses synthetic fixtures only; no real guardian data or live SMS.
- G0 plus a written G4 pilot authorisation is required before the first controlled campaign.
- H4 retention and H6 DB-role separation remain open; OPS-01/03 cannot close without them.
- No credentials, secrets, or production values belong in these documents.
- No claim that OPS-09 training, OPS-11 hypercare, OPS-12 handover, or G5 has passed.
