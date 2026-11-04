# Deploy and Rollback Runbook

**Status:** Template. No production deployment has been verified.

## Preconditions (all required)

- [ ] G0 provider verification and G4 messaging approval are closed, or the
      release explicitly keeps messaging disabled.
- [ ] Hosting location, data residency, access, and retention are approved by
      the school.
- [ ] DNS points the chosen `APP_DOMAIN` at the host; ports 80/443 are reachable.
- [ ] SSH is key-only and restricted; firewall allows only 22 (admin IPs),
      80, and 443.
- [ ] Docker Engine + Compose v2 are installed; the `feedesk` user is in the
      `docker` group.
- [ ] `/etc/feedesk/feedesk.env` exists, mode `0600`, with production values and
      no development secrets.
- [ ] A recent backup exists and its manifest checksum is readable.
- [ ] Monitoring, even if manual, has an owner.

## Build and deploy

```sh
cd /opt/feedesk

# 1. Validate interpolation before touching running containers.
docker compose \
  --project-name feedesk-prod \
  --env-file /etc/feedesk/feedesk.env \
  -f infra/compose/docker-compose.prod.yml \
  config --quiet

# 2. Build images. Tag before deploy so rollback has a target.
docker compose ... build --pull
docker tag feedesk-prod-api:latest feedesk-prod-api:$(date -u +%Y%m%dT%H%M%SZ)
docker tag feedesk-prod-web:latest feedesk-prod-web:$(date -u +%Y%m%dT%H%M%SZ)

# 3. Take a backup before migrations.
sudo systemctl start feedesk-backup.service
# Confirm the manifest and SHA-256 values exist before continuing.

# 4. Apply.
docker compose ... up -d --remove-orphans

# 5. Watch health.
docker compose ... ps
curl -fsS "https://${APP_DOMAIN}/health/ready"
```

The `api` command runs `alembic upgrade head` and the idempotent seed before
starting `uvicorn`. The worker starts only after API readiness passes.

## Post-deploy smoke checks

- [ ] `proxy`, `web`, `api`, `worker`, `db` are `running`; `db` and `api` are
      `healthy`.
- [ ] `/health/live` and `/health/ready` return 200 through the public host.
- [ ] TLS certificate is valid and HTTP redirects to HTTPS.
- [ ] Login works; the session cookie is `__Host-fd_session` with `Secure`,
      `HttpOnly`, and `SameSite=Lax`.
- [ ] Dashboard, settings, users, imports, campaigns, and message history load.
- [ ] Worker logs show `worker.start` with `provider=fake enabled=False
      kill_switch=True`.
- [ ] Queue counts are zero or unchanged; no new sends occurred.
- [ ] No 5xx spike in Caddy logs.
- [ ] Backup timer is active.

## Rollback

### A. Application-only rollback (preferred)

Use when the database schema is backward compatible.

```sh
# Stop the sender first so a rollback cannot race a send.
docker compose ... stop worker

# Re-tag the previous known-good image as :latest, then recreate only app services.
docker tag feedesk-prod-api:<previous> feedesk-prod-api:latest
docker tag feedesk-prod-web:<previous> feedesk-prod-web:latest
docker compose ... up -d --no-deps api web

# Re-run smoke checks, then restart the worker.
docker compose ... up -d worker
```

### B. Migration rollback

Do **not** run `alembic downgrade` blindly. FeeDesk migrations may be
forward-only or data-destructive. The approved path is:

1. Stop `worker`, then `web` and `api`.
2. Preserve the failed database for investigation if disk allows.
3. Restore the pre-deploy backup into a scratch database and verify it with
   `scripts/feedesk_restore.py`.
4. Only with the school's approval, restore the production database using
   [backup-restore.md](backup-restore.md). This discards writes after the backup.
5. Deploy the previous application version and re-run smoke checks.

## Rollback triggers

- Readiness fails for more than 5 minutes after deploy.
- 5xx rate above 2% for 10 minutes and rising.
- Login or core read paths broken.
- Any sign of duplicate or unintended sends.
- Migration error or data-integrity alarm.

## Do not

- Do not use `down -v`.
- Do not delete Docker volumes to "reset" the app.
- Do not enable messaging to test a deploy.
- Do not rotate keys during a rollback; do one change at a time.
