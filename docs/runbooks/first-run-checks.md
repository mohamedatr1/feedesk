# First-Run and Pre-Handover Checks

**Status:** Template. Run only on an approved host. No live SMS.

## Host

- [ ] OS patched; timezone set to the school's timezone; NTP active.
- [ ] Non-root `feedesk` user; SSH key-only; root login disabled.
- [ ] Firewall: 22 from admin IPs only; 80/443 public; no 5432, 3000, or 8000.
- [ ] Docker Engine and Compose v2 installed; `docker compose version` works.
- [ ] Disk has room for database + uploads + 30 daily backups; monitor >15% free.
- [ ] `/opt/feedesk` owned by `feedesk`; repo release pinned to a commit/tag.
- [ ] `/etc/feedesk/feedesk.env` mode `0600`; no `.env.local`, dev secrets, or
      live provider key.

## Configuration validation

```sh
docker compose \
  --project-name feedesk-prod \
  --env-file /etc/feedesk/feedesk.env \
  -f infra/compose/docker-compose.prod.yml \
  config --quiet
```

- [ ] `POSTGRES_PASSWORD`, `SESSION_SECRET`, `SEED_ADMIN_PASSWORD`, and
      `APP_DOMAIN` are set and not placeholders.
- [ ] `SESSION_SECRET` is at least 32 random characters.
- [ ] `SEED_ADMIN_PASSWORD` is not the application default.
- [ ] `COOKIE_SECURE=true`; cookie name is `__Host-fd_session`.
- [ ] `MESSAGING_PROVIDER=fake`, `MESSAGING_ENABLED=false`,
      `MESSAGING_KILL_SWITCH=true`.
- [ ] `RASEL_API_KEY` is empty or an approved staging key; production key is not
      present pre-G4.

## Start

```sh
sudo systemctl start feedesk.service
docker compose ... ps
docker compose ... logs --tail=100 api
docker compose ... logs --tail=100 worker
```

Expected order: `db` healthy -> `api` migrates/seeds and becomes healthy ->
`worker` starts -> `web` healthy -> `proxy` healthy.

## Verify

- [ ] `https://$APP_DOMAIN/health/live` returns 200.
- [ ] `https://$APP_DOMAIN/health/ready` returns 200 with `database: ok`.
- [ ] HTTP redirects to HTTPS; certificate chain is valid.
- [ ] `curl -I` shows HSTS, `X-Content-Type-Options`, `X-Frame-Options`, and no
      `Server` banner.
- [ ] Login page loads; login with the seed admin forces a password change.
- [ ] After changing the password, the seed password no longer works.
- [ ] Settings show the correct school name, currency, and timezone.
- [ ] Users, audit, imports, campaigns, message history pages load.
- [ ] Worker log shows `provider=fake enabled=False kill_switch=True`.
- [ ] Queue is empty or unchanged; no message was sent.
- [ ] Uploads work: create a synthetic import, then verify an authenticated
      download; delete/retain per policy.
- [ ] Audit log captures the login, settings change, and import actions.
- [ ] No guardian data appears in container logs.
- [ ] Backups: `systemctl start feedesk-backup.service` succeeds; manifest and
      checksums exist; run a scratch restore verification.

## Monitoring

- [ ] External probes configured for `/` and `/health/ready`.
- [ ] Test alert delivered to the on-call mailbox; resolved notification works.
- [ ] Disk, database, queue, failed/unknown, and backup alerts visible.
- [ ] Provider balance remains a manual check (not wired).

## Handover

- [ ] School user trained on import, review, approval, and results.
- [ ] Written confirmation that messaging is disabled.
- [ ] Support contact and escalation path shared.
- [ ] First-week review scheduled.
- [ ] Deployment-readiness status updated with actual evidence.
