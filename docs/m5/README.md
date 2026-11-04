# M5 — Production Hardening (Pre-G4 Readiness)

**Status:** Formal M5 launch/UAT cannot start. G0 and G4 remain open. Pre-G4 hardening is in progress: operations/deployment scaffolding, local M1–M4 backup/restore drill, security/privacy audit, a high-severity fix pass, the full API permission matrix, the H3/M1 campaign-privacy closure, and the M4/M7/M8 security-medium pass (including encrypted provider credentials) are complete. OPS-02 is closed; OPS-01/03 remain open only for H4 retention and H6 DB-role separation. The H4 school decision package and H6 provisioning package are drafted but **not approved or applied**. An OPS-08 UAT plan/scripts/template and a 24-decision external pack are prepared; UAT is **not executed**, and the decision pack remains open. No production deployment, live SMS, or provider call is involved.

| Document | Purpose |
|---|---|
| `security-review.md` | OPS-01/02/03 findings and closure evidence |
| `privacy-retention-plan.md` | H4 school decision package and implementation plan (open; no policy adopted) |
| `db-role-separation.md` | H6 role provisioning/verification package (open; not applied) |
| `deployment-readiness.md` | OPS-04/05/06/07 manifests, backup, monitoring, runbooks status |
| `external-decision-pack.md` | Consolidated G0/G4/H4/H6/hosting/UAT/support decisions and bilingual request template |
| `uat-plan.md` | OPS-08 UAT plan, roles, entry/exit criteria, coverage, triage |
| `uat-scripts.md` | OPS-08 executable scripts for M1–M5 |
| `uat-execution-record.md` | Blank OPS-08 execution/sign-off record (**NOT EXECUTED**) |
| `../runbooks/` | Operational procedures; review record in `../runbooks/review.md` |

## Allowed now

- Security review and fixes that are independent of the provider.
- Full API permission-matrix tests.
- Privacy controls: masking, retention/deletion procedure, log redaction.
- Backup/restore drill on the local cluster.
- Deployment/monitoring/runbook scaffolding without production credentials or live host changes.

## Blocked

- Live Rasel verification, controlled test send, pilot, provider reconciliation.
- UAT with a school employee on real/anonymized data.
- Training delivery and launch go/no-go.
- Production deployment verification, HTTPS certificate issuance, and live alerts.

## Hard constraints

- No production secrets in the repository.
- No live SMS or provider host call.
- No claim that M5/G5 is passed.
- No destructive production action.
