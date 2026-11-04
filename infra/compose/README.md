# Production-like Compose Stack

**Status:** Template only. Not deployed or verified on a production host.

`docker-compose.prod.yml` adds a worker, private uploads, health checks, and an
HTTPS reverse proxy while keeping the development file `docker-compose.yml`
unchanged.

| Service | Exposure | Purpose |
|---|---|---|
| `proxy` (Caddy) | host `80`, `443`, `443/udp` | TLS termination; only public entry point |
| `web` (Next.js) | private `app` network | UI and `/api/*` rewrite to `api:8000` |
| `api` (FastAPI) | private `app`/`backend` | HTTP API, migrations, seed |
| `worker` | private `app`/`backend` | `python -m app.worker`; only sender process |
| `db` (PostgreSQL 16) | private `backend` only | no host port published |

Uploads live in the named volume `feedesk_prod_uploads`; the database lives in
`feedesk_prod_db`. Caddy state is in `feedesk_prod_caddy_data`.

## Compose command

```sh
cp infra/compose/.env.production.example infra/compose/.env.production
# edit infra/compose/.env.production
docker compose \
  --env-file infra/compose/.env.production \
  -f infra/compose/docker-compose.prod.yml \
  config --quiet
docker compose \
  --env-file infra/compose/.env.production \
  -f infra/compose/docker-compose.prod.yml \
  up -d --build
```

`config --quiet` validates interpolation and fails when a required placeholder
is missing. Do not use `--env-file .env.local`; development values must not be
reused in production.

## Safety defaults

- `MESSAGING_PROVIDER=fake`, `MESSAGING_ENABLED=false`,
  `MESSAGING_KILL_SWITCH=true`.
- `RASEL_API_KEY` is empty in the template.
- The database has no published port.
- The API seed is idempotent and runs before `uvicorn`.
- The worker starts only after the API passes `/health/ready`, so migrations
  have completed.

## Known gaps

- No resource limits, log shipping, or external uptime check are wired here.
- Image tags are not pinned by digest, and there is no image registry.
- Caddy certificate issuance, firewall rules, and DNS were not exercised.
- Backups are outside Compose; see `docs/runbooks/backup-restore.md`.
- Monitoring templates are in `infra/monitoring/` and are not deployed.
