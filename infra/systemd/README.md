# systemd Units (Template)

**Status:** Template only. Not installed or verified on a server.

Assumptions:

- Repository deployed at `/opt/feedesk`, owned by `feedesk:feedesk`.
- Production env file at `/etc/feedesk/feedesk.env` (mode `0600`, root-owned
  or `feedesk`-owned, never committed).
- Backup env file at `/etc/feedesk/backup.env` (mode `0600`).
- The `feedesk` service user is in the `docker` group. Membership in `docker`
  is effectively root; restrict login access to this account.
- Docker Engine with the Compose v2 plugin is installed.

## Files

| File | Purpose |
|---|---|
| `feedesk.service` | Validate env, then `docker compose up -d`; stop on shutdown |
| `feedesk-backup.service` | One-shot nightly backup with safety checks |
| `feedesk-backup.timer` | Daily 02:30 local time, persistent catch-up |

`docker-compose.prod.yml` already sets `restart: unless-stopped`, so containers
also restart after a Docker daemon restart. The unit makes the desired state
explicit and validates configuration at boot.

## Install (when a host is approved)

```sh
# Create the service account first if it does not exist.
sudo useradd --system --home-dir /opt/feedesk --shell /usr/sbin/nologin feedesk
sudo usermod -aG docker feedesk

sudo install -d -m 0750 -o feedesk -g feedesk /opt/feedesk /etc/feedesk
sudo install -d -m 0700 -o feedesk -g feedesk /var/backups/feedesk
sudo install -d -m 0755 -o feedesk -g feedesk /var/lib/node_exporter/textfile
sudo install -m 0644 infra/systemd/feedesk.service /etc/systemd/system/
sudo install -m 0644 infra/systemd/feedesk-backup.service /etc/systemd/system/
sudo install -m 0644 infra/systemd/feedesk-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemd-analyze verify /etc/systemd/system/feedesk.service \
  /etc/systemd/system/feedesk-backup.service \
  /etc/systemd/system/feedesk-backup.timer
sudo systemctl enable --now feedesk.service
sudo systemctl enable --now feedesk-backup.timer
systemctl list-timers feedesk-backup.timer
```

## Backup env example

```sh
BACKUP_DIR=/var/backups/feedesk
BACKUP_RETENTION_DAYS=30
BACKUP_UPLOADS_VOLUME=feedesk_prod_uploads
BACKUP_METRICS_TEXTFILE=/var/lib/node_exporter/textfile/feedesk_backup.prom
# Backups must be encrypted in production. Keep the age private key OFF this host.
# BACKUP_AGE_RECIPIENT=age1...
COMPOSE_ENV_FILE=/etc/feedesk/feedesk.env
```

The backup unit invokes the script with `--execute`; the script itself defaults
to dry-run for manual use. See `docs/runbooks/backup-restore.md`.

## Not verified

- `systemd-analyze verify` was not run on a Linux host in this phase.
- The hardening directives (`ProtectSystem=strict`, group access to the Docker
  socket) were not exercised with this stack.
- Timer timezone follows the host. Confirm it matches the school's office hours
  before enabling.
