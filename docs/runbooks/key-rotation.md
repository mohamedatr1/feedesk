# Key and Secret Rotation Runbook

**Status:** Template. Rotation has not been exercised in production. There is no
credential-rotation UI or encrypted credential store; secrets are environment
variables injected at deploy time.

## Inventory

| Secret | Where | Effect of rotation |
|---|---|---|
| `SESSION_SECRET` | `/etc/feedesk/feedesk.env` | All sessions invalidated; users re-login |
| `POSTGRES_PASSWORD` | env file + PostgreSQL role | API/worker lose DB until all updated |
| `SEED_ADMIN_PASSWORD` | env file | Only affects first seed of a new database |
| `RASEL_API_KEY` | env file | Provider calls fail until updated; not used while fake |
| `BACKUP_AGE_RECIPIENT` / private key | env file / offline escrow | New backups only; old backups need old key |
| TLS certificate | Caddy volume | Automatic; do not edit manually |

Secrets must never be committed, pasted into chat, or logged. Generate with:

```sh
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## A. Session secret

Use when a session secret may have leaked, or on a scheduled cadence.

1. Generate a new value of at least 32 characters.
2. Update `SESSION_SECRET` in `/etc/feedesk/feedesk.env` (mode `0600`).
3. Recreate API and worker:
   ```sh
   docker compose ... up -d --no-deps api worker
   ```
4. Confirm `/health/ready` and a fresh login. All existing users are logged out.
5. Record time and reason. Do not rotate during an active incident unless the
   secret is the cause.

## B. Database password

1. Take a verified backup.
2. Choose a URL-safe password, or percent-encode it for `DATABASE_URL`.
3. Change the role inside PostgreSQL:
   ```sh
   docker compose ... exec -T db psql -U feedesk -d feedesk \
     -c "ALTER ROLE feedesk WITH PASSWORD 'NEW_VALUE';"
   ```
4. Update `POSTGRES_PASSWORD` in the env file.
5. Recreate API and worker:
   ```sh
   docker compose ... up -d --no-deps api worker
   ```
6. Verify readiness and worker startup. The `db` container's
   `POSTGRES_PASSWORD` env is only used at initialization; do not recreate the
   db container to apply it.
7. Keep the old value only in the approved secret store until the change is
   confirmed, then destroy it.

## C. Rasel API key

Requires G0/G4 ownership of the provider account. Do not perform this while
messaging is live without a maintenance window.

1. Generate a new key in the provider console; confirm the old key's revocation
   timing.
2. Update `RASEL_API_KEY` in the env file.
3. Recreate API and worker.
4. Confirm worker startup logs show the expected provider and **no** key value.
5. Run only the read-only account/sender check approved for the environment. Do
   not send a message.
6. Revoke the old key after the new one is confirmed.
7. If a key leaked, check provider logs for unauthorized sends and follow the
   provider outage/incident process.

## D. Seed administrator password

`SEED_ADMIN_PASSWORD` is used only when the seed creates a new administrator.
Changing it later does nothing. Use the admin password-reset flow for an existing
user, then confirm the first-login password change.

## E. Backup encryption key

- Keep the age **private** key offline, in escrow, with a named custodian and a
  tested recovery path.
- Rotating the recipient affects new backups only. Retain the old private key
  until every old backup is expired.
- Never store the private key on the application server.
- Restore drill must prove the custodian can decrypt a backup without the app
  host.

## Verification checklist

- [ ] New secret length and format checked (no whitespace).
- [ ] Env file mode `0600`; owner is the service account.
- [ ] No secret printed in shell history, logs, or ticket.
- [ ] API readiness passes; login works.
- [ ] Worker starts and reports the expected safe messaging state.
- [ ] Old secret revoked or scheduled for destruction.
- [ ] Rotation recorded in the operations log.
- [ ] Backup encryption custodian informed, if applicable.
