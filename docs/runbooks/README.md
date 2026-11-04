# FeeDesk Runbooks

Operational procedures for the pre-G4 production-like stack.

**Important:** No procedure here has been executed against a production host.
No live SMS has been sent or tested. G0 and G4 remain open. Treat these as
reviewed templates until the deployment-readiness checklist records evidence.
The only exercised procedure is the local PostgreSQL database restore; see
[review.md](review.md).

## Index

| Runbook | Use when |
|---|---|
| [deploy-rollback.md](deploy-rollback.md) | First deploy, routine release, failed release |
| [worker-recovery.md](worker-recovery.md) | Queue stalled, worker crashed, duplicate workers |
| [unknown-outcomes.md](unknown-outcomes.md) | Message status is `unknown`; provider reconciliation |
| [provider-outage.md](provider-outage.md) | Rasel errors, timeouts, balance/sender problems |
| [key-rotation.md](key-rotation.md) | Session, database, provider, or backup key rotation |
| [backup-restore.md](backup-restore.md) | Backup checks, restore drill, actual restore |
| [first-run-checks.md](first-run-checks.md) | Before handing the app to a school user |
| [review.md](review.md) | Owner, prerequisites, gaps, and unexercised procedures (4 Nov 2026) |

## Command shorthand

`docker compose ...` in these runbooks means:

```sh
docker compose \
  --project-name feedesk-prod \
  --env-file /etc/feedesk/feedesk.env \
  -f /opt/feedesk/infra/compose/docker-compose.prod.yml
```

Adjust paths only if the deployment layout differs.

## Universal rules

1. Never put secrets, guardian names, phone numbers, or message text in tickets,
   chat, alert labels, or logs.
2. Never run `docker compose down -v`. It deletes the database and uploads
   volumes.
3. Stop the worker before any database restore, migration rollback, or key
   change that affects sending.
4. `unknown` is not failure. Do not resend an unknown message without provider
   reconciliation.
5. Messaging must stay `MESSAGING_PROVIDER=fake`, `MESSAGING_ENABLED=false`,
   `MESSAGING_KILL_SWITCH=true` until G0/G4 and a written go/no-go.
6. Record the time, operator, commands, and outcome for every production action.
