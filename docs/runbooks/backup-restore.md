# Backup and Restore Runbook

**Status:** Local database drills completed 3 November 2026 and 4 November 2026 (M1–M4 tables). Production encryption, offsite storage, and uploads restore are **not** verified. The new scripts have syntax and dry-run checks only; no script-driven or Docker restore was executed in this phase.

## Targets and assumptions

| Item | Proposed target | Assumption |
|---|---|---|
| RPO | ≤ 24 hours | Nightly backup; reporting/imports are office-hours work |
| RTO | ≤ 4 hours | Single server; PostgreSQL dump restore plus uploads |
| Retention | 30 daily, 12 monthly | Script prunes only daily artifacts; monthly archive is manual |
| Encryption | Required in production | `age` recipient on the host, private key offline |
| Offsite | Required in production | Copy after encryption; access logged |
| Verification | Monthly restore drill | Scratch database + uploads archive listing |

These are proposals from ADR 008. The school must confirm them before launch.
Because the database dump and uploads archive are taken sequentially, a file
written during the backup window may be slightly newer than the database dump.
Uploads referenced by the restored database should exist; orphaned newer files
are harmless. Record the backup start/end time.

## What the backup contains

- PostgreSQL custom-format dump (`pg_dump -Fc`), no owners/privileges.
- Private uploads volume tar (`feedesk_prod_uploads`).
- A JSON manifest with byte sizes and SHA-256 checksums, written last.

The backup does **not** include Caddy certificate data (renewable), Docker
images, or the env file. Escrow secrets separately.

## Script

`scripts/feedesk_backup.py` is dry-run by default and never restores.

```sh
# Dry run: prints commands, writes nothing.
python3 scripts/feedesk_backup.py --env-file /etc/feedesk/feedesk.env

# Production run (systemd does this with --execute; BACKUP_AGE_RECIPIENT must be set).
python3 scripts/feedesk_backup.py --execute \
  --env-file /etc/feedesk/feedesk.env \
  --backup-dir /var/backups/feedesk \
  --age-recipient age1... \
  --metrics-textfile /var/lib/node_exporter/textfile/feedesk_backup.prom

# Local drill only: explicitly allow an unencrypted artifact.
python3 scripts/feedesk_backup.py --execute --allow-unencrypted \
  --env-file /etc/feedesk/feedesk.env \
  --backup-dir /tmp/feedesk-drill
```

It reads credentials from the Compose `db` service, not from the command line.
The uploads tar runs in a throwaway `alpine:3.20` container against a read-only
volume mount. Pre-pull `alpine:3.20` on an air-gapped host.

Environment equivalents: `BACKUP_DIR`, `BACKUP_RETENTION_DAYS`,
`BACKUP_UPLOADS_VOLUME`, `BACKUP_METRICS_TEXTFILE`, `BACKUP_AGE_RECIPIENT`,
`COMPOSE_ENV_FILE`.

### Encryption

```sh
# Public recipient on the host; private key offline in escrow.
python3 scripts/feedesk_backup.py --execute \
  --env-file /etc/feedesk/feedesk.env \
  --backup-dir /var/backups/feedesk \
  --age-recipient age1...
```

The script now refuses `--execute` without an age recipient unless the explicit
local-drill flag `--allow-unencrypted` is passed. Do not use that flag in
production.

### Offsite copy

The script does not copy offsite. After a successful run:

```sh
# Example only; adapt to the approved storage. Verify checksums after copy.
rclone copy /var/backups/feedesk remote:feedesk-backups/$(date -u +%Y/%m)
```

Alert on backup failure and on backup age > 36 hours. Keep at least one copy
outside the application host.

### Retention

The script deletes only `feedesk-*` files matching `.dump`, `.dump.age`,
`.tar.gz`, `.tar.gz.age`, and `-manifest.json`, older than
`BACKUP_RETENTION_DAYS`. It never deletes the database or uploads volume.
Monthly archives must be copied aside before daily retention expires.

## Scheduled backup

`infra/systemd/feedesk-backup.service` + `.timer` run daily at 02:30 local time.
The unit invokes the script with `--execute`. The timer uses `Persistent=true`,
so a missed run starts after boot.

```sh
systemctl list-timers feedesk-backup.timer
systemctl status feedesk-backup.service
journalctl -u feedesk-backup.service -n 100 --no-pager
```

## Restore verification (safe)

`scripts/feedesk_restore.py` is also dry-run by default. It refuses any target
that does not match `feedesk_restore_[a-z0-9_]+`, so it cannot target the
production `feedesk` database or `feedesk_prod_uploads` volume.

```sh
# 1. Dry run.
python3 scripts/feedesk_restore.py \
  --env-file /etc/feedesk/feedesk.env \
  --dump /var/backups/feedesk/feedesk-20261104T023000Z-db.dump \
  --uploads-archive /var/backups/feedesk/feedesk-20261104T023000Z-uploads.tar.gz

# 2. Scratch restore + checks (creates a scratch DB; does not touch production).
python3 scripts/feedesk_restore.py --execute \
  --env-file /etc/feedesk/feedesk.env \
  --dump /var/backups/feedesk/feedesk-20261104T023000Z-db.dump \
  --uploads-archive /var/backups/feedesk/feedesk-20261104T023000Z-uploads.tar.gz \
  --uploads-target-volume feedesk_restore_uploads_20261104
```

If the backup is encrypted, decrypt it first on a trusted workstation with the
offline private key:

```sh
age --decrypt -i /secure/feedesk-backup.key -o /tmp/feedesk.dump feedesk-...-db.dump.age
```

Do not copy the private key onto the application host. The restore script does
not decrypt.

The script reports row counts for `users`, `audit_events`, and
`school_settings`, checks the tar for absolute paths, `..`, links, and devices,
and optionally extracts uploads into a scratch volume. Cleanup is manual:

```sh
docker compose ... exec -T db dropdb -U feedesk feedesk_restore_verify_...
docker volume rm feedesk_restore_uploads_20261104
```

A restore is not complete until:

- [ ] The database accepts connections.
- [ ] `users`, `audit_events`, and `school_settings` counts are non-zero and
      plausible.
- [ ] Alembic version matches the release.
- [ ] An application health check passes against the scratch data (if wired).
- [ ] Uploads archive opens, has no unsafe paths, and file count is recorded.
- [ ] A sample authenticated download works after restore.

## Production restore (destructive, requires approval)

Do not run this as a drill. Requires the school's written approval and a named
operator.

1. Declare a maintenance window. Stop the worker first, then web and api:
   ```sh
   docker compose ... stop worker web api
   ```
2. Take a backup of the **current** database and uploads, even if it is broken.
   Preserve it separately.
3. Verify the target backup manifest and SHA-256 before use.
4. Restore the database. The production restore path is intentionally manual:
   - create a replacement database and restore into it, or
   - use the managed PostgreSQL restore procedure, if one was chosen.
   Do not overwrite the live database in place without a preserved copy.
   Before launch, replace this outline with the exact commands for the chosen
   host and rehearse them. Do not improvise during an incident.
5. Restore uploads into a **new** volume, then swap the volume reference in a
   reviewed Compose change. Do not extract over the live uploads volume.
6. Start `api` and run readiness; start `web`; leave `worker` stopped.
7. Run smoke checks: login, settings, import list, campaign read-only views,
   message history, audit log, one authenticated download.
8. Confirm no message is `submitting`. Reconcile unknown outcomes before
   starting the worker.
9. Start the worker only with messaging disabled/kill switch on, then confirm
   queue state.
10. Record RPO/RTO actuals, data-loss window, and approvals.

## Local drill evidence (3 November 2026)

```powershell
$dump = "F:\FeeDesk\.local\backups\feedesk-20261103-193308.dump"
& 'F:\PostgreSQL\16\bin\pg_dump.exe' -h 127.0.0.1 -p 55432 -U postgres -d feedesk -Fc -f $dump
& 'F:\PostgreSQL\16\bin\createdb.exe' -h 127.0.0.1 -p 55432 -U postgres feedesk_restore_check
& 'F:\PostgreSQL\16\bin\pg_restore.exe' -h 127.0.0.1 -p 55432 -U postgres -d feedesk_restore_check $dump
& 'F:\PostgreSQL\16\bin\psql.exe' -h 127.0.0.1 -p 55432 -U postgres -d feedesk_restore_check `
  -c "select (select count(*) from users) as users, (select count(*) from audit_events) as audit_events, (select count(*) from school_settings) as settings;"
```

| Table | Rows |
|---|---:|
| users | 1 |
| audit_events | 9 |
| school_settings | 1 |

The scratch database was dropped after verification. This drill did not cover
uploads, encryption, offsite storage, or a production-like Compose stack.

### Local drill evidence (4 November 2026, M1–M4 tables)

```powershell
$dump = "F:\FeeDesk\.local\backups\feedesk-m5-20261104-011339.dump"
& 'F:\PostgreSQL\16\bin\pg_dump.exe' -h 127.0.0.1 -p 55432 -U postgres -d feedesk -Fc -f $dump
& 'F:\PostgreSQL\16\bin\createdb.exe' -h 127.0.0.1 -p 55432 -U postgres feedesk_restore_m5
& 'F:\PostgreSQL\16\bin\pg_restore.exe' -h 127.0.0.1 -p 55432 -U postgres -d feedesk_restore_m5 $dump
# row-count check, then:
& 'F:\PostgreSQL\16\bin\dropdb.exe' -h 127.0.0.1 -p 55432 -U postgres feedesk_restore_m5
```

| Table | Rows |
|---|---:|
| users | 6 |
| audit_events | 124 |
| source_files | 8 |
| import_batches | 8 |
| campaigns | 6 |
| campaign_recipients | 4 |
| messages | 4 |
| send_jobs | 4 |
| provider_events | 0 |

The scratch database was dropped. The restore included M4 messaging rows and
confirmed no provider events. Uploads, encryption, offsite storage, and a
production-like stack were not covered.

## Script checks performed in this phase

- `python -m py_compile scripts/feedesk_backup.py scripts/feedesk_restore.py`
- `--help` for both scripts
- dry runs of both scripts (no files, databases, or volumes changed)

No script-driven or Docker restore was executed. The 4 November local PostgreSQL restore above was executed manually against a scratch database.
