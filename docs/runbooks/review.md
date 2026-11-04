# Runbook Review Record

**Review date:** 4 November 2026  
**Review type:** Desk review against the current Compose files, scripts, and M5 documentation. **No production host was used, no container image was built, no TLS certificate was issued, no alert was delivered, no uploads were restored, and no live provider call was made.**  
**Status:** Open. OPS-07 remains open. This record does not approve any runbook for production.

The only operational procedure exercised in this phase is the local PostgreSQL dump/restore drill on 3 and 4 November 2026. Script syntax checks, `--help`, and dry runs are not runbook exercises.

## Scope and method

- Read every runbook in `docs/runbooks/`.
- Compared commands with the current production-like Compose file, backup/restore scripts, and M5 deployment-readiness notes.
- Did not run Docker, systemd, Caddy, a production PostgreSQL command, or any provider request.
- Owner roles below are **proposed and unassigned**. No named on-call, deputy, or school approver has accepted them.
- "Last review" means a documentation desk review, not an operational sign-off.

## Inventory

| Runbook | Purpose | Proposed owner / role | Prerequisites | Last review | Exercised? | Gaps / open actions |
|---|---|---|---|---|---|---|
| `README.md` | Index, command shorthand, universal safety rules | Operations lead | All runbooks present; deployment layout known | 4 Nov 2026 (desk) | n/a — index | `docker compose ...` is shorthand, not a real alias; no named owner; add link to this review record |
| `deploy-rollback.md` | First deploy, routine release, failed release | Deployment/operations engineer + school IT; second reviewer for rollback | Approved host, DNS, TLS, `/etc/feedesk/feedesk.env`, recent backup, monitoring owner, maintenance window, messaging disabled | 4 Nov 2026 (desk) | No | No host or image build; image/tag names (`feedesk-prod-api`, `feedesk-prod-web`) unverified; migration/seed split depends on H6; rollback and migration rollback not rehearsed; no maintenance-window/approval template |
| `worker-recovery.md` | Queue stalled, worker crashed, duplicate workers | Backend/worker engineer + on-call operations | Running Compose stack, database access, worker logs, queue metrics, one-worker rule | 4 Nov 2026 (desk) | No | No crash/lease-reclaim drill; no delivered `FeeDeskWorkerStalled`/`FeeDeskStaleLeases` alert; no queue dashboard; `psql -U feedesk` commands must change after H6 |
| `unknown-outcomes.md` | Message status is `unknown`; provider reconciliation | Provider operations lead + backend engineer + incident commander | G4 provider access, message/job IDs, provider console, second reviewer, no-resend rule | 4 Nov 2026 (desk) | No | No reconciliation API, admin screen, or audited status-correction workflow; no live provider evidence; G4 remains blocked; second-reviewer process is not formalized |
| `provider-outage.md` | Rasel errors, timeouts, balance/sender problems | Provider operations lead + operations | G0/G4 provider access, provider console, sender/balance status, kill switch, worker stop | 4 Nov 2026 (desk) | No | No live Rasel call or outage drill; no balance exporter/admin display; re-enable steps are not authorized pre-G4; no provider status-page integration; no outage ticket template |
| `key-rotation.md` | Session, database, provider, or backup key rotation | Security/operations lead + DBA | Secret store, verified backup, maintenance window, age private key custody, role-specific database credentials | 4 Nov 2026 (desk) | No | No rotation drill; no production secrets; database role commands must be updated for H6; backup-key custody and decrypt path untested; no rotation cadence or owner |
| `backup-restore.md` | Backup checks, restore drill, actual restore | DBA/backup custodian + school data owner for destructive restore | Host, backup artifacts, encryption key, scratch database/volume, approval for destructive restore | 4 Nov 2026 (desk); drills 3 & 4 Nov 2026 | **Partial — local PostgreSQL database restore only** | No uploads restore, encryption, offsite copy, decrypt drill, script `--execute` via Docker, or production restore; production-command section is still an outline; RPO/RTO unsigned; no backup-failure alert; monthly archive manual |
| `first-run-checks.md` | Before handing the app to a school user | Deployment/operations engineer + school admin | Approved host, DNS/TLS, env file, seed admin, monitoring, school user, written messaging-disabled confirmation | 4 Nov 2026 (desk) | No | No host or TLS; no delivered alert test; uploads check depends on retention policy; backup scratch restore not run from this checklist; training/handover and school sign-off not done |
| `review.md` | This review record | Documentation/operations reviewer | All runbooks present | 4 Nov 2026 | n/a — this record | Must be updated after each exercise, H6 change, or incident; not an operational sign-off |

## What was actually exercised

Only the following was executed:

- 3 November 2026: manual `pg_dump -Fc` of the local `feedesk` database, restore into `feedesk_restore_check`, row-count check (`users` 1, `audit_events` 9, `school_settings` 1), then scratch database dropped.
- 4 November 2026: manual `pg_dump -Fc` including M1–M4 tables, restore into `feedesk_restore_m5`, row-count check (`users` 6, `audit_events` 124, `source_files` 8, `import_batches` 8, `campaigns` 6, `campaign_recipients` 4, `messages` 4, `send_jobs` 4, `provider_events` 0), then scratch database dropped.
- `python -m py_compile` for the backup/restore scripts, `--help` for both, and dry runs. No `--execute` run, no Docker restore, no uploads archive.
- YAML syntax parsing of `docker-compose.prod.yml`; no `docker compose config`, no Caddy validation, no `systemd-analyze verify`.

The M2/M3/M4 API, browser, and worker verifications are product verification, not runbook exercises. They do not prove any production procedure.

## What remains unexercised

| Procedure | Why it matters | Evidence needed to close |
|---|---|---|
| Production deploy | Images, health ordering, seed, proxies, and volumes have never run on a host | Staging or production deploy record with image tags, `docker compose ps`, health checks, logs, and smoke results |
| Application rollback | A failed release must return to a known-good image without resending | Rehearsed tag/rollback on staging with smoke checks and no message movement |
| Migration rollback | Forward-only/data-destructive migrations make blind downgrade unsafe | Documented decision per release; backup restore rehearsal; school approval for the data-loss window |
| TLS/DNS | Certificate issuance, renewal, redirect, HSTS, and firewall behavior are unproven | `curl -I`, certificate chain, HTTP→HTTPS redirect, renewal test |
| Alert delivery | `FeeDeskWorkerStalled`, stale leases, backup failure, disk, and 5xx alerts have not fired | Delivered test alert, resolved notification, on-call acknowledgement, alert labels without PII |
| Uploads backup/restore | Database-only restore does not prove guardian documents survive | Uploads archive listing, scratch-volume restore, authenticated sample download |
| Backup encryption/decryption/offsite | An encrypted backup that cannot be decrypted is not a backup | `age` encrypt/decrypt with the offline key, checksum after offsite copy, custodian verification |
| Live provider send | G0/G4 are open; no Rasel contract, sender, or delivery evidence exists | Approved test send, provider evidence, delivery/acceptance distinction, no duplicate |
| Provider reconciliation | Unknown outcomes cannot be closed without provider evidence | Provider console/read-only check, second reviewer, audited correction path, G4 sign-off |
| Worker crash/lease reclaim | Crash recovery and duplicate suppression are unit-tested but not drilled | Kill a worker mid-job in staging; observe lease expiry, no blind resend, unknown handling |
| Key rotation | A leaked secret has no exercised response | Staging rotation of session, database, provider, and backup keys with rollback |
| First-run/handover | The school has not used the app on an approved host | Completed first-run checklist, training record, written messaging-disabled confirmation, school sign-off |
| Destructive production restore | The school must authorise the data-loss window and operator | Tabletop or approved drill with named operator, preserved broken copy, RPO/RTO actuals |
| Monitoring stack | Templates exist; Prometheus/Loki/Alertmanager were not run | Running stack, dashboards, alert rules loaded, balance metric decision |
| Systemd/Caddy on host | Units and Caddyfile were not validated on the target OS | `systemd-analyze verify`, `caddy validate`, timer/service status, reboot persistence |

## Cross-cutting findings

| ID | Finding | Risk | Action | Owner | Status |
|---|---|---|---|---|---|
| RBR-01 | No named runbook owner, deputy, or on-call | An incident has no accountable responder | Assign owners and a deputy for each runbook; publish escalation contacts | Operations lead | Open |
| RBR-02 | No production host, DNS, or TLS | Deploy/rollback/first-run commands are untested | Provision a staging host and run deploy + rollback before production | Deployment engineer | Open |
| RBR-03 | No delivered alert | Worker, backup, disk, and 5xx failures may go unnoticed | Build the monitoring stack and deliver a test alert to the on-call mailbox | Operations lead | Open |
| RBR-04 | Uploads restore, encryption, offsite, and decrypt untested | Database recovery may not restore guardian documents; encrypted backups may be unreadable | Run an uploads + encrypted backup/restore drill with the offline key | DBA/backup custodian | Open |
| RBR-05 | No live provider evidence; G0/G4 open | Unknown/outage/reconciliation procedures cannot be validated | Complete G0/G4 and run a controlled test-send/reconciliation exercise | Provider operations lead | Blocked |
| RBR-06 | H6 role separation changes the intended role for `-U feedesk` commands | Worker/backup/restore runbooks may use the break-glass role or fail if it is unavailable | Update all database commands and script defaults after H6 | DBA + backend engineer | Open |
| RBR-07 | `docker compose ...` is shorthand, not a runnable alias | An operator may run the wrong project or env file | Define and test the full helper command in each runbook; keep project name/paths explicit | Operations lead | Open |
| RBR-08 | No maintenance-window, approval, or post-incident template | Destructive actions lack a recorded authorisation | Add a window/approval template and an incident record template | Operations lead + school | Open |
| RBR-09 | No exercise schedule | Runbooks will drift from the deployed system | Review after each deploy, H6 change, backup drill, incident, and at least annually | Operations lead | Open |
| RBR-10 | Runbooks are English-only; school handover is pending | School staff may not be able to follow an incident procedure | Add an Arabic quick-reference/handover checklist with the school | School admin + operations | Open |
| RBR-11 | Backup/restore scripts are dry-run-checked only | `--execute` may fail on the host | Run `--execute` on staging with a scratch target and record the transcript | DBA/backup custodian | Open |
| RBR-12 | No rollback rehearsal | A failed deploy may become a data-loss event | Rehearse application rollback and a migration-restore decision on staging | Deployment engineer | Open |
| RBR-13 | Provider balance has no metric or admin display | A campaign can start with insufficient credit | Wire a read-only balance check or keep a documented manual check with a low-water mark | Provider operations lead | Open |

## Claims explicitly not made

- No production deployment was performed.
- No container image was built or deployed.
- No TLS certificate was issued, renewed, or validated.
- No alert fired or was delivered.
- No uploads archive was backed up or restored.
- No backup was encrypted, decrypted, or copied offsite by the scripts in this phase.
- No live Rasel/SMS call was made.
- No worker crash, lease reclaim, provider outage, or unknown reconciliation drill was run.
- No key rotation was performed.
- No first-run/handover was performed on an approved host.
- No runbook was exercised beyond the local PostgreSQL database restore described above.

## Review conclusion

The runbooks are useful reviewed templates, not approved operational procedures. OPS-07 remains open. Do not mark OPS-07, M5, or G5 complete from this record. Re-review after the H6 role change, after the first staging deployment, after the first uploads/encrypted backup drill, and before any live provider send.
