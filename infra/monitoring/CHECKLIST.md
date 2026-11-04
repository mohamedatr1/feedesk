# Monitoring and Alerting Checklist (Pre-G4 Design)

**Status:** Checklist and templates only. Nothing here is deployed, and no alert
has been fired or delivered. Provider balance monitoring is blocked by G4.

## Signals

| # | Signal | Source | Proposed threshold | First action |
|---|---|---|---|---|
| 1 | Public web uptime | blackbox probe of `/` | 3 failures / 3 min | Deploy runbook; check `proxy`, `web` |
| 2 | API readiness | blackbox probe of `/health/ready` | 3 failures / 3 min | Check `db` health, then API logs |
| 3 | API 5xx rate | Caddy JSON log -> Loki | >10 in 5 min; >2% for 10 min | Check deploy time, roll back if new |
| 4 | Queue depth | postgres_exporter custom query | pending/retry >25 for 10 min; >100 for 5 min | Worker recovery runbook |
| 5 | Worker liveness | oldest pending job age | >300 s for 5 min | Worker recovery runbook |
| 6 | Expired leases | `send_jobs.lease_expires_at < now()` | any for 5 min | Confirm worker dead before restart |
| 7 | Failed jobs | `send_jobs.status='failed'` (24 h) | any increase in 10 min | Inspect `last_error`; provider outage runbook |
| 8 | Unknown outcomes | `messages.internal_status='unknown'` | any in 24 h | Unknown outcomes runbook; no auto-resend |
| 9 | Stuck submitting | `messages.internal_status='submitting'` >10 min | any | Treat as unknown until reconciled |
| 10 | Provider balance | Rasel read-only balance call | school-defined low-water mark | Top up; **not wired** (G4) |
| 11 | Disk | node_exporter filesystem | <15% warning, <10% critical | Free space; never delete DB files |
| 12 | Database reachable | `pg_up`, `pg_isready` | 2 min down | Database recovery; restore only if needed |
| 13 | DB connections | postgres_exporter | >80% of max for 10 min | Check stuck sessions |
| 14 | Uploads volume growth | custom uploads query | trend review weekly | Plan capacity; confirm uploads are private |
| 15 | Backup freshness | textfile metric from backup script | >36 h | Backup/restore runbook |
| 16 | Backup failure | systemd unit failure / timer | any | Fix before the next night |
| 17 | TLS expiry | blackbox `probe_ssl_earliest_cert_expiry` | <14 days | Check Caddy renewal |

## Alert delivery checks (must be run before launch)

- [ ] Send a synthetic test alert through Alertmanager to the on-call mailbox.
- [ ] Confirm alert resolves and sends a resolved notification.
- [ ] Confirm alerts do not include guardian names, phone numbers, or message text.
- [ ] Confirm the person on call can reach the host and the provider console.
- [ ] Record an escalation contact and response-time expectation.
- [ ] Verify the external probe runs outside the school network.
- [ ] Verify the backup freshness metric appears after one successful backup.
- [ ] Verify a failed backup produces a visible failure (unit status or metric).

## Minimum admin-visible information (PRD 19.3)

The API already exposes messaging status through `/api/v1`; the checklist
assumes an operator can see:

- provider connection status and configured channel,
- last provider error and last successful test,
- pending send jobs, failed jobs, and unknown outcomes,
- provider balance when available.

The last item is not implemented. Do not claim it works until G4 provides a
read-only balance check and the metric is emitted.

## Explicit gaps

- No hosted Prometheus/Grafana/Loki/Alertmanager exists in this repository.
- `postgres_exporter_queries.yml` targets the deprecated `--extend.query-path`
  format and is unvalidated against a running exporter.
- The `feedesk_provider_balance_credit` rule is inert without an exporter.
- Thresholds are guesses for a 10-50 recipient pilot and must be tuned.
- Log retention, PII scrubbing, and alert routing need a written school decision.
