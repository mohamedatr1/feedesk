# M5 Deployment Readiness (Pre-G4)

**Status:** Operations/deployment scaffolding is ready to review and to run
locally where Docker exists. It is **not** production-ready. No production host
was provisioned, no HTTPS certificate was issued, no container image was built,
and no live SMS or provider call was made.

| Gate/dependency | State | Effect |
|---|---|---|
| G0 — provider/sender/test number/real samples | **Open** | Live messaging must stay disabled |
| G4 — messaging verification/pilot | **Open** | No production send, reconciliation, or balance automation |
| Production host decision | **Open** | No deployment verification, DNS, TLS, firewall, or hosting evidence |
| School decisions (hosting, retention, access, budget) | **Open** | Blocks production go/no-go |

## OPS status

| Item | Status | Evidence | Remaining blocker |
|---|---|---|---|
| OPS-04 Backup/restore + RPO/RTO | **Partial** | Scripts, runbook, local DB drill including M1–M4 tables | Docker unavailable on the local host, so uploads archive extraction/restore was not exercised; encryption, offsite, production restore not tested |
| OPS-05 Production deployment | **Scaffolded** | Compose, Caddy, systemd, first-run checks | No host, DNS, TLS, images, or deployment evidence |
| OPS-06 Monitoring/alerting | **Template only** | Prometheus/Alertmanager/Loki templates, checklist | No monitoring stack, no alert test, balance metric absent |
| OPS-07 Runbooks | **Drafted + desk-reviewed** | Deploy/rollback, worker, unknown, outage, keys, backup, first-run; review record in `docs/runbooks/review.md` | Not exercised; production TLS/alerts/uploads restore/live provider remain unverified |
| Security review OPS-01/02/03 | **Partial** | OPS-02 permission matrix passes (52 routes); H3/M1/M4/M7/M8 fixed and browser/API-verified. OPS-01/03 open only for H4/H6. See `docs/m5/security-review.md` | Not closable yet |

## What is ready to use locally

These are safe with fake messaging and no production secrets:

- `infra/compose/docker-compose.prod.yml` for a production-like topology review
  and local Docker test, including worker, uploads, health checks, no published
  database port, and Caddy TLS termination.
- `infra/compose/Caddyfile` with HTTPS, security headers, `/health/*` routing,
  and JSON access logs.
- `infra/compose/.env.production.example` with required placeholders and
  messaging safety defaults.
- `infra/systemd/` units and timer, as templates.
- `infra/monitoring/` Prometheus/Alertmanager/Loki templates, postgres_exporter
  custom queries, and the checklist.
- `docs/runbooks/` procedures.
- `scripts/feedesk_backup.py` and `scripts/feedesk_restore.py`, both dry-run by
  default and restricted to scratch targets for restore.

The development stack `infra/compose/docker-compose.yml` is unchanged.

## What is explicitly not ready

- **No production deployment was verified.** Compose was not run: Docker is not
  installed on this workstation.
- **No live SMS was sent or tested.** `MESSAGING_PROVIDER=fake`,
  `MESSAGING_ENABLED=false`, and `MESSAGING_KILL_SWITCH=true` are the defaults in
  the production-like file.
- **No TLS certificate was issued.** Caddy/DNS/firewall behavior is unproven.
- **No backup was encrypted or shipped offsite.** `feedesk_backup.py --execute` now requires an age recipient unless the explicit local-drill flag is used; the manual local drill was unencrypted and uploads were not included.
- **No script-driven/Docker restore was executed.** The restore helper was syntax- and dry-run-checked only. A manual PostgreSQL dump/restore into a scratch database was executed locally on 4 November; uploads were not restored.
- **No alert fired or was delivered.** The provider balance metric does not
  exist yet.
- **No database PITR or high availability.** The design is single-server with
  nightly dumps, subject to the school's RPO approval.
- **No external secret manager.** Most secrets are environment variables on the host. Provider credentials are encrypted in the database with `PROVIDER_CREDENTIAL_KEY`; the rotation/revoke UI and worker DB-over-env resolution are implemented. Vault-key re-encryption and external secret-manager custody remain unimplemented.
- **No CI/CD or image registry.** Images are built locally; rollback tags are
  manual.
- **No resource limits or log shipping.** Compose uses JSON log rotation only.

## Verification performed

| Check | Result |
|---|---|
| Read existing dev compose, README, `.env.example`, ADR 008, PRD 15.5/19 | Done |
| Parse `docker-compose.prod.yml` as YAML | Passed (PyYAML syntax only) |
| Validate Caddyfile with `caddy validate` | Skipped: Caddy not installed |
| `docker compose config --quiet` | Skipped: Docker not installed |
| `systemd-analyze verify` | Skipped: Windows host, no systemd |
| `python -m py_compile` backup/restore scripts | Passed |
| Backup/restore `--help` and dry runs | Passed; no files/DB/volumes changed |
| Backup/restore `--execute` | **Not run** via Docker (would require a host) |
| Local PostgreSQL drill (4 Nov 2026) | `pg_dump -Fc` of `feedesk`, restore into scratch `feedesk_restore_m5`, row counts verified, scratch DB dropped. Counts: 6 users, 124 audit events, 8 source files, 8 imports, 6 campaigns, 4 recipients, 4 messages, 4 jobs, 0 provider events. |
| Uploads backup/restore | **Not run** in this drill; script supports it but requires a Docker host |
| Live provider call | **Not made** |

YAML checks use Python + PyYAML; they do not prove Compose semantics. Run
`docker compose config --quiet` on the target host before deploying.

## Production decisions still open

1. **Hosting:** single VPS vs managed PostgreSQL; location and data-residency
   constraints; who administers the host.
2. **Backup:** encryption tool and key custodian; offsite destination and access
   logging; 30/12 retention confirmation; whether PITR is required.
3. **RPO/RTO:** confirm ≤24 h / ≤4 h, or fund PITR and a faster restore path.
4. **Monitoring:** hosted vs self-hosted Prometheus/Loki; on-call owner; alert
   mailbox; log retention and PII scrubbing.
5. **Provider:** free-text plan, approved sender, Syrian destination support,
   balance low-water mark, and reconciliation method (G0/G4).
6. **Messaging enablement:** allowlist test-send flow, kill-switch ownership,
   approval to send, and a rollback-to-fake procedure.
7. **School policy:** retention, deletion, opt-out wording, Arabic template copy,
   office hours, and support contacts.
8. **Access:** admin accounts, password reset path, MFA (not implemented), and
   emergency access.
9. **Rollback:** acceptable data-loss window and authority to approve a restore.
10. **TLS/DNS:** final `APP_DOMAIN`, certificate issuance, and renewal monitoring.

## Go/no-go rule

Do not mark OPS-04/05/06/07 complete, G4 passed, or M5/G5 passed from this
scaffolding. Completion requires a real host, an approved deployment record, a
tested restore including uploads, a delivered test alert, runbook review, and
the G0/G4 evidence.
