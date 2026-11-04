# M5 — Database Role Separation Plan (H6)

**Status:** Open. This is a provisioning and verification package, not an applied change. The current production-like Compose starts the app as the `feedesk` database owner. That is convenient for Alembic but lets a compromised app credential disable audit triggers and perform DDL. No production role change has been applied or verified. This plan targets the production-like stack; the development Compose remains on its existing bootstrap role.

**Date:** 4 November 2026  
**Version:** 1.0 (provisioning plan; not applied)  
**Prepared by:** FeeDesk documentation pass (pre-G4)  
**Related:** `security-review.md` (H6), `deployment-readiness.md`, `../runbooks/backup-restore.md`, `../runbooks/deploy-rollback.md`.

## Current gap

| Item | Current state | Risk |
|---|---|---|
| Runtime database role | API and worker connect as `feedesk`, the database owner/superuser | A compromised app can run DDL, drop or disable audit triggers, and truncate audit |
| Migration role | The `api` service command runs `alembic upgrade head` and the seed before starting Uvicorn | Migrations and runtime share one credential |
| Backup role | `scripts/feedesk_backup.py` defaults to `--db-user feedesk` inside the `db` service | The backup path uses an owner credential instead of a read-only role |
| Restore role | `scripts/feedesk_restore.py` defaults to `--db-user feedesk` and `--no-owner --no-privileges` | Restored objects are owned by the restoring role and grants are not restored |
| Audit ownership | `audit_events` and its trigger function are owned by the runtime role | The runtime role can `ALTER TABLE ... DISABLE TRIGGER` and `DROP TRIGGER` |

The current Compose topology must not be treated as tamper-proof against a compromised app credential.

## Target roles

| Role | Purpose | Rights | Explicitly not allowed |
|---|---|---|---|
| `feedesk_owner` | Migrations, seed, schema changes, restore ownership | Owns the database, `public` schema, tables, sequences, and trigger functions; DDL; login only for the migration/seed job | No API/worker runtime use; no shared credential with app |
| `feedesk_app` | API and worker runtime | `CONNECT`, `USAGE` on `public`, `SELECT/INSERT/UPDATE/DELETE` on required tables, `USAGE/SELECT` on sequences; audit `SELECT/INSERT` only | No DDL, no table/function ownership, no `TRUNCATE`, no audit `UPDATE/DELETE`, no trigger changes, no `session_replication_role` |
| `feedesk_backup` | Backup dumps and read-only checks | `CONNECT`, `USAGE` on `public`, `SELECT` on all tables and sequences | No `INSERT/UPDATE/DELETE/TRUNCATE`, no DDL, no ownership |
| `feedesk` | Bootstrap superuser / break-glass | Existing superuser retained for emergency recovery | Never used by API, worker, or backup; credential offline |

`feedesk_owner` is not a superuser. Superuser-only operations (creating the database, installing extensions, managed-provider role changes) remain a break-glass or provider-admin action. Separation reduces the runtime blast radius; it does not make the owner credential safe to expose. The owner credential must be restricted to the one-shot migration/seed job, stored separately, and rotated on the same schedule as the other production secrets.

## Preconditions

- [ ] Written maintenance window and school approval to change production database roles.
- [ ] Verified database **and uploads** backup, with a restore point and checksum.
- [ ] Worker stopped; `MESSAGING_PROVIDER=fake`, `MESSAGING_ENABLED=false`, `MESSAGING_KILL_SWITCH=true`.
- [ ] Baseline captured: roles, database/schema/table owners, grants, trigger definitions, `alembic current`.
- [ ] Three new passwords generated and stored in the approved secret store; never in shell history, Compose files, tickets, or logs.
- [ ] A staging or scratch PostgreSQL database exists for denial and restore tests.
- [ ] The migration/runtime split is designed and reviewed (see step 4); do not change roles first and split the command later.
- [ ] A rollback operator and a second reviewer are named.

## Ordered provisioning

Run as the bootstrap superuser (`feedesk`) from the `db` service unless stated otherwise. Define the Compose helper once:

```sh
dc() {
  docker compose \
    --project-name feedesk-prod \
    --env-file /etc/feedesk/feedesk.env \
    -f /opt/feedesk/infra/compose/docker-compose.prod.yml \
    "$@"
}
```

### Step 0 — Capture baseline

```sh
dc exec -T db psql -U feedesk -d feedesk -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_database(), current_user;
SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname='feedesk';
SELECT nspname, pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname='public';
SELECT c.relkind, c.relname, pg_get_userbyid(c.relowner) AS owner
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname='public' AND c.relkind IN ('r','p','S','v','m','f')
ORDER BY c.relkind, c.relname;
SELECT p.proname, pg_get_userbyid(p.proowner) AS owner
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname='public' AND p.proname IN ('prevent_audit_mutation','prevent_approved_campaign_recipient_mutation');
SELECT tgname, tgenabled, pg_get_triggerdef(oid) AS definition
FROM pg_trigger
WHERE tgrelid='audit_events'::regclass AND NOT tgisinternal
ORDER BY tgname;
SELECT t.typname, t.typtype, pg_get_userbyid(t.typowner) AS owner
FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname='public' AND t.typtype IN ('c','d','e','r')
ORDER BY t.typname;
SQL
```

Store the output, redacting passwords. Optionally capture role definitions with `pg_dumpall --roles-only`, but that file contains password hashes; keep it encrypted and offline, never in the repository.

### Step 1 — Create roles

Use a secret manager or an interactive `psql` session. The placeholders below are not values to commit.

```sql
CREATE ROLE feedesk_owner LOGIN PASSWORD '<from-secret-store>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE feedesk_app LOGIN PASSWORD '<from-secret-store>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE feedesk_backup LOGIN PASSWORD '<from-secret-store>'
  NOSUPERUSER NOCREATEDB NOCREATEROLE;
```

Use URL-safe passwords (or percent-encode them for `DATABASE_URL`) and keep them in the secret store. Do not paste real values into shell history or a committed file.

Set a fixed search path for the app role:

```sql
ALTER ROLE feedesk_app IN DATABASE feedesk SET search_path = public, pg_catalog;
```

### Step 2 — Transfer ownership of application objects

```sql
ALTER DATABASE feedesk OWNER TO feedesk_owner;
\c feedesk
ALTER SCHEMA public OWNER TO feedesk_owner;

DO $$
DECLARE
  obj record;
BEGIN
  FOR obj IN
    SELECT c.relkind, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public'
      AND c.relkind IN ('r','p','S','v','m','f')
    ORDER BY CASE c.relkind
      WHEN 'r' THEN 1 WHEN 'p' THEN 1
      WHEN 'S' THEN 2
      WHEN 'v' THEN 3 WHEN 'm' THEN 3
      WHEN 'f' THEN 4
      ELSE 5 END, c.relname
  LOOP
    IF obj.relkind = 'S' THEN
      EXECUTE format('ALTER SEQUENCE public.%I OWNER TO feedesk_owner', obj.relname);
    ELSIF obj.relkind = 'v' THEN
      EXECUTE format('ALTER VIEW public.%I OWNER TO feedesk_owner', obj.relname);
    ELSIF obj.relkind = 'm' THEN
      EXECUTE format('ALTER MATERIALIZED VIEW public.%I OWNER TO feedesk_owner', obj.relname);
    ELSIF obj.relkind = 'f' THEN
      EXECUTE format('ALTER FOREIGN TABLE public.%I OWNER TO feedesk_owner', obj.relname);
    ELSE
      EXECUTE format('ALTER TABLE public.%I OWNER TO feedesk_owner', obj.relname);
    END IF;
  END LOOP;

  FOR obj IN
    SELECT p.proname, p.prokind, pg_get_function_identity_arguments(p.oid) AS args
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
  LOOP
    IF obj.prokind = 'p' THEN
      EXECUTE format('ALTER PROCEDURE public.%I(%s) OWNER TO feedesk_owner', obj.proname, obj.args);
    ELSIF obj.prokind = 'a' THEN
      EXECUTE format('ALTER AGGREGATE public.%I(%s) OWNER TO feedesk_owner', obj.proname, obj.args);
    ELSE
      EXECUTE format('ALTER FUNCTION public.%I(%s) OWNER TO feedesk_owner', obj.proname, obj.args);
    END IF;
  END LOOP;
END $$;
```

This block transfers only objects in `public`; it deliberately avoids `REASSIGN OWNED BY feedesk`. On a cluster where `feedesk` was the `initdb`/bootstrap superuser, `REASSIGN OWNED` can try to reassign system catalog objects and fail or damage the cluster. If the cluster was initialised with a different bootstrap role and `feedesk` owns no system objects, `REASSIGN OWNED` is a shortcut, but the block above is the reviewed path.

Sequences owned by a table column may follow the table owner; if PostgreSQL rejects a direct sequence ownership change, verify the table owner and record the exception rather than forcing it.

Verify in verification section A that the ownership query shows `feedesk_owner` for every application table, sequence, view, and trigger function. If the schema contains a standalone type, domain, or collation, transfer it explicitly (`ALTER TYPE`, `ALTER DOMAIN`, `ALTER COLLATION`); the current models do not define one, but the query is authoritative.

### Step 3 — Apply grants and default privileges

Run as `feedesk_owner` or the bootstrap superuser. Keep this block in a versioned, idempotent `grants.sql`; the commands below are the reviewed baseline.

```sql
REVOKE ALL ON DATABASE feedesk FROM PUBLIC;
GRANT CONNECT ON DATABASE feedesk TO feedesk_app, feedesk_backup;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO feedesk_app, feedesk_backup;
REVOKE CREATE ON SCHEMA public FROM feedesk_app, feedesk_backup;

-- Runtime DML. Audit is narrowed immediately below.
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO feedesk_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO feedesk_app;

-- Backup reads only.
GRANT SELECT ON ALL TABLES IN SCHEMA public TO feedesk_backup;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO feedesk_backup;

-- Audit: insert and select only. No update, delete, truncate, trigger, or ownership.
REVOKE ALL ON audit_events FROM feedesk_app;
GRANT SELECT, INSERT ON audit_events TO feedesk_app;
REVOKE ALL ON audit_events FROM feedesk_backup;
GRANT SELECT ON audit_events TO feedesk_backup;

-- Alembic version is read-only to the runtime; only the owner migrates.
REVOKE INSERT, UPDATE, DELETE ON alembic_version FROM feedesk_app;
GRANT SELECT ON alembic_version TO feedesk_app;

REVOKE TRUNCATE ON ALL TABLES IN SCHEMA public FROM feedesk_app;
REVOKE TRUNCATE ON ALL TABLES IN SCHEMA public FROM feedesk_backup;

-- Future objects created by the owner.
ALTER DEFAULT PRIVILEGES FOR ROLE feedesk_owner IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO feedesk_app;
ALTER DEFAULT PRIVILEGES FOR ROLE feedesk_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO feedesk_app;
ALTER DEFAULT PRIVILEGES FOR ROLE feedesk_owner IN SCHEMA public
  GRANT SELECT ON TABLES TO feedesk_backup;
ALTER DEFAULT PRIVILEGES FOR ROLE feedesk_owner IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO feedesk_backup;
```

Notes:

- Default privileges are not a substitute for the audit hardening block. Re-run the `audit_events` and `alembic_version` revokes after every migration that adds an audit-like/immutable table.
- Do not grant `TEMPORARY` on the database unless a tested application path requires it. The current app does not document a temp-table requirement.
- Leave `EXECUTE` on trigger functions at the default unless a test shows it must be narrowed; the audit insert path depends on those functions firing.

### Step 4 — Split migration and runtime credentials

This is a configuration/code-change prerequisite, not something the SQL above can fix. The current `api` command runs Alembic, the seed, and Uvicorn with one URL.

Target topology:

| Process | Role | Command | Environment |
|---|---|---|---|
| One-shot `migrate` (new) | `feedesk_owner` | `alembic upgrade head && python -m app.seed` | `DATABASE_URL` = owner URL, job-local only |
| `api` | `feedesk_app` | `uvicorn ... --no-access-log` | `DATABASE_URL` = app URL |
| `worker` | `feedesk_app` | `python -m app.worker` | `DATABASE_URL` = app URL |
| Backup job | `feedesk_backup` | `feedesk_backup.py --execute` | Backup credential, not app/owner |
| Restore/repair | `feedesk_owner` or provider admin | `pg_restore` into a new database | Owner credential |

The current settings read `DATABASE_URL`; there is no `MIGRATION_DATABASE_URL` in the application. Do not invent one unless the code is changed to read it. Override `DATABASE_URL` only in the one-shot migration/seed job, and keep the app/worker value separate.

Requirements:

- The owner URL must never appear in `api` or `worker` environments.
- The backup script must stop defaulting to `feedesk`; pass the backup role explicitly or read a dedicated secret.
- The restore helper must create/restore into a database owned by `feedesk_owner`, or transfer ownership and re-grant afterwards.
- Verify the rendered Compose environment with `dc config` and inspect it manually; passwords must be redacted in any captured output.

### Step 5 — Start in order and verify

1. Run the migration/seed job as `feedesk_owner`.
2. Confirm `alembic current` matches the release.
3. Start `api`, then `worker`, then `web` with the app credential.
4. Run the smoke checks in the verification section.
5. Do not enable messaging. The worker must report `provider=fake enabled=False kill_switch=True`.

## Verification commands

Run these on a staging copy first. On production, run only read-only checks and the denial checks that fail before writing. Destructive tamper tests belong on a restored scratch database.

### A. Ownership, triggers, and privilege matrix

```sh
dc exec -T db psql -U feedesk -d feedesk -v ON_ERROR_STOP=1 <<'SQL'
SELECT current_database(), current_user;
SELECT datname, pg_get_userbyid(datdba) AS owner FROM pg_database WHERE datname='feedesk';
SELECT nspname, pg_get_userbyid(nspowner) AS owner FROM pg_namespace WHERE nspname='public';
SELECT c.relkind, c.relname, pg_get_userbyid(c.relowner) AS owner
FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname='public' AND c.relkind IN ('r','p','S','v','m','f')
ORDER BY c.relkind, c.relname;
SELECT p.proname, pg_get_userbyid(p.proowner) AS owner
FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE n.nspname='public' AND p.proname IN ('prevent_audit_mutation','prevent_approved_campaign_recipient_mutation');
SELECT tgname, tgenabled, pg_get_triggerdef(oid) AS definition
FROM pg_trigger
WHERE tgrelid='audit_events'::regclass AND NOT tgisinternal
ORDER BY tgname;
SELECT t.typname, t.typtype, pg_get_userbyid(t.typowner) AS owner
FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
WHERE n.nspname='public' AND t.typtype IN ('c','d','e','r')
ORDER BY t.typname;

SELECT
  has_database_privilege('feedesk_app','feedesk','CONNECT') AS app_connect,
  has_database_privilege('feedesk_app','feedesk','TEMP') AS app_temp,
  has_schema_privilege('feedesk_app','public','USAGE') AS app_schema_usage,
  has_schema_privilege('feedesk_app','public','CREATE') AS app_schema_create,
  has_table_privilege('feedesk_app','users','SELECT') AS app_users_select,
  has_table_privilege('feedesk_app','users','UPDATE') AS app_users_update,
  has_table_privilege('feedesk_app','audit_events','SELECT') AS app_audit_select,
  has_table_privilege('feedesk_app','audit_events','INSERT') AS app_audit_insert,
  has_table_privilege('feedesk_app','audit_events','UPDATE') AS app_audit_update,
  has_table_privilege('feedesk_app','audit_events','DELETE') AS app_audit_delete,
  has_table_privilege('feedesk_app','audit_events','TRUNCATE') AS app_audit_truncate,
  has_table_privilege('feedesk_app','alembic_version','INSERT') AS app_alembic_insert,
  has_table_privilege('feedesk_backup','users','SELECT') AS backup_users_select,
  has_table_privilege('feedesk_backup','users','UPDATE') AS backup_users_update;
SQL
```

Expected:

- Database, `public` schema, application tables, sequences, views, row types, and both trigger functions are owned by `feedesk_owner`.
- Both audit triggers exist and `tgenabled` is `O` (origin).
- App: connect true, temp false, schema usage true, schema create false, users select/update true, audit select/insert true, audit update/delete/truncate false, `alembic_version` insert false.
- Backup: users select true, users update false.

Set an owner helper for read-only checks and the scratch-database test. The password is read from the secret store, not typed into the command line:

```sh
read -r -s FEEDESK_OWNER_PASSWORD
export FEEDESK_OWNER_PASSWORD
psql_owner() {
  dc exec -T -e PGPASSWORD="$FEEDESK_OWNER_PASSWORD" db \
    psql -U feedesk_owner -d feedesk -v ON_ERROR_STOP=1 "$@"
}
```

### B. App-role DDL and tamper denial

Set the app password from the secret store without leaving it in shell history:

```sh
read -r -s FEEDESK_APP_PASSWORD
export FEEDESK_APP_PASSWORD
psql_app() {
  dc exec -T -e PGPASSWORD="$FEEDESK_APP_PASSWORD" db \
    psql -U feedesk_app -d feedesk -v ON_ERROR_STOP=1 "$@"
}
psql_app -c "SELECT current_user;"
```

Expected `feedesk_app`, then each command below must fail. Capture the exact error and timestamp. A command that succeeds is a failed verification.

| Test | Command | Expected error |
|---|---|---|
| Create table | `psql_app -c "CREATE TABLE h6_should_fail(id integer);"` | `permission denied for schema public` |
| Create schema | `psql_app -c "CREATE SCHEMA h6_should_fail;"` | `permission denied for database feedesk` |
| Alter table | `psql_app -c "ALTER TABLE users ADD COLUMN h6_should_fail integer;"` | `must be owner of table users` |
| Drop table | `psql_app -c "DROP TABLE users;"` | `must be owner of table users` |
| Create index | `psql_app -c "CREATE INDEX h6_should_fail_idx ON audit_events(created_at);"` | `must be owner of table audit_events` |
| Disable trigger | `psql_app -c "ALTER TABLE audit_events DISABLE TRIGGER audit_events_no_update_delete;"` | `must be owner of table audit_events` |
| Drop trigger | `psql_app -c "DROP TRIGGER audit_events_no_update_delete ON audit_events;"` | `must be owner of table audit_events` |
| Update audit | `psql_app -c "UPDATE audit_events SET action='tampered' WHERE false;"` | `permission denied for table audit_events` |
| Delete audit | `psql_app -c "DELETE FROM audit_events WHERE false;"` | `permission denied for table audit_events` |
| Truncate audit | `psql_app -c "TRUNCATE audit_events;"` | `permission denied for table audit_events` |
| Replication role | `psql_app -c "SET session_replication_role = replica;"` | `permission denied to set parameter "session_replication_role"` |
| Set role | `psql_app -c "SET ROLE feedesk_owner;"` | `permission denied to set role "feedesk_owner"` |
| Alter function owner | `psql_app -c "ALTER FUNCTION prevent_audit_mutation() OWNER TO feedesk_app;"` | `must be owner of function prevent_audit_mutation` |
| Drop function | `psql_app -c "DROP FUNCTION prevent_audit_mutation();"` | `must be owner of function prevent_audit_mutation` |
| Update catalogs | `psql_app -c "UPDATE pg_trigger SET tgenabled='D' WHERE tgname='audit_events_no_update_delete';"` | `permission denied for table pg_trigger` |

After the denial tests, re-run the trigger query from A and confirm `tgenabled` is still `O`. The app must also be able to write a normal audit event; verify in a transaction and roll it back (prefer a staging database):

```sh
psql_app <<'SQL'
BEGIN;
INSERT INTO audit_events (id, action, entity_type, created_at)
VALUES ('h6-verify-0001', 'h6.verify', 'verification', now());
SELECT id, action FROM audit_events WHERE id='h6-verify-0001';
ROLLBACK;
SQL
```

Expected: `INSERT 0 1`, one selected row, `ROLLBACK`. No row remains.

### C. Audit trigger still fires for the owner

Run only on a restored scratch database, never against production audit rows.

```sh
dc exec -T -e PGPASSWORD="$FEEDESK_OWNER_PASSWORD" db \
  psql -U feedesk_owner -d feedesk_restore_h6 -v ON_ERROR_STOP=1 \
  -c "UPDATE audit_events SET action='tampered' WHERE id=(SELECT id FROM audit_events LIMIT 1);"
```

Expected: `ERROR: audit_events is append-only`. Repeat with `DELETE`, then `TRUNCATE`; both must raise the same exception. This proves ownership transfer preserved the trigger and function.

### D. Backup role read-only

```sh
read -r -s FEEDESK_BACKUP_PASSWORD
export FEEDESK_BACKUP_PASSWORD
psql_backup() {
  dc exec -T -e PGPASSWORD="$FEEDESK_BACKUP_PASSWORD" db \
    psql -U feedesk_backup -d feedesk -v ON_ERROR_STOP=1 "$@"
}

psql_backup -c "SELECT count(*) FROM audit_events;"
psql_backup -c "UPDATE users SET username = username WHERE false;"
psql_backup -c "DELETE FROM users WHERE false;"
psql_backup -c "TRUNCATE users;"
psql_backup -c "CREATE TABLE h6_backup_should_fail(id integer);"

dc exec -T -e PGPASSWORD="$FEEDESK_BACKUP_PASSWORD" db \
  pg_dump -U feedesk_backup -d feedesk -Fc --no-owner --no-privileges \
  -f /tmp/h6-backup-test.dump
dc exec -T db pg_restore --list /tmp/h6-backup-test.dump | head -n 20
dc exec -T db rm -f /tmp/h6-backup-test.dump
```

Expected: the `SELECT` and `pg_dump` succeed; update, delete, truncate, and create fail with `permission denied`; `pg_restore --list` lists `audit_events`, its triggers, and the tables. The dump contains no ownership or grant commands because `--no-owner --no-privileges` is used.

### E. Application smoke with the app role

Run the normal authenticated smoke, not the schema-creating pytest suite:

- [ ] Login and forced password change.
- [ ] Dashboard, settings, users, imports list, campaign read-only views, message history, audit list load.
- [ ] One authenticated file download works.
- [ ] Worker starts with `provider=fake enabled=False kill_switch=True`.
- [ ] Queue counts unchanged; no message was sent.
- [ ] `psql_app -c "SELECT current_user;"` returns `feedesk_app`.
- [ ] `psql_owner -c "SELECT version_num FROM alembic_version;"` matches the release.

The test suite creates and drops schema objects in `conftest.py`; it must continue to run as `feedesk_owner` against a scratch database. Do not weaken grants to make the test suite pass as `feedesk_app`.

## Migration and restore ownership reapplication

`pg_dump --no-owner --no-privileges` deliberately omits ownership and grants. A restore is not complete until they are reapplied.

Preferred restore:

1. Create the target database with `feedesk_owner` as owner, or create it as break-glass and run `ALTER DATABASE <target> OWNER TO feedesk_owner;`.
2. Restore as `feedesk_owner` (or as break-glass if the provider requires it).
3. If objects were restored by another role, run the step 2 ownership block against the target database with `feedesk_owner` as the target. Do not use `REASSIGN OWNED` when the restore role is the cluster bootstrap superuser.
4. Re-run the idempotent `grants.sql` block from step 3. Do not assume default privileges survived the dump.
5. Verify `audit_events`, `alembic_version`, sequences, and both trigger functions are owned by `feedesk_owner`.
6. Run `alembic current` as owner and confirm the revision matches the release. Do not run `alembic upgrade head` during a restore unless the release explicitly requires it.
7. Start the API with the app role and repeat smoke checks.

Managed PostgreSQL caveat: if the provider does not allow superuser or ownership changes, use the provider's role/ownership tooling and record the equivalent evidence. Do not fake ownership in the dump.

## Rollback

Use when the app cannot start, audit inserts fail, migrations cannot run as owner, or the backup role cannot dump. Run the ownership steps as the bootstrap superuser (`feedesk`); the app role cannot perform them. Roll back in this order; do not combine it with a migration downgrade.

1. Stop the sender and application:
   ```sh
   dc stop worker api web
   ```
2. Restore the previous runtime configuration (bootstrap `feedesk` URL and the previous `api` command) in a reviewed change. Keep messaging disabled.
3. Transfer ownership back:
   ```sql
   ALTER DATABASE feedesk OWNER TO feedesk;
   \c feedesk
   ALTER SCHEMA public OWNER TO feedesk;
   -- Re-run the step 2 DO block with every feedesk_owner replaced by feedesk.
   ```
   Do not use `REASSIGN OWNED BY feedesk_owner` here; the same bootstrap-role risk applies in reverse.
4. Disable, but do not immediately drop, the new roles:
   ```sql
   ALTER ROLE feedesk_app NOLOGIN;
   ALTER ROLE feedesk_backup NOLOGIN;
   ALTER ROLE feedesk_owner NOLOGIN;
   ```
   Do not `DROP ROLE` while a role still owns objects; PostgreSQL will refuse, and a partial cleanup is worse than a disabled role. After the incident is understood and a backup exists, `DROP OWNED BY feedesk_app, feedesk_backup; DROP ROLE feedesk_app, feedesk_backup;` in a separate approved change. Drop `feedesk_owner` only after ownership has been reassigned back and the role owns nothing.
5. Re-run the application smoke. Confirm `current_user` is the bootstrap role and `alembic current` is unchanged.
6. Record the rollback time, reason, commands, and any data written during the failed window.

Rollback triggers:

- App readiness fails for more than 5 minutes after the role change.
- Audit insert or select fails.
- Migration/seed cannot connect as owner.
- Backup cannot dump.
- Any unexpected 5xx, connection-pool exhaustion, or permission error in normal reads/writes.

## Evidence to attach

All items remain open. H6 is not closed by applying SQL; it is closed by reproducible evidence and a rollback that was at least rehearsed on staging.

- [ ] Baseline and post-change role list (`\du`), database/schema/table/sequence/function owners, and trigger definitions.
- [ ] Privilege matrix output from section A, with the expected true/false values.
- [ ] App-role denial transcript from section B: command, exact error, exit code, timestamp, database name.
- [ ] Owner-run audit tamper test from section C, run on a restored scratch database.
- [ ] Backup-role read-only transcript and `pg_dump`/`pg_restore --list` evidence.
- [ ] App-role smoke: login, core read paths, audit insert/rollback, worker safe startup, queue unchanged.
- [ ] `alembic current` before and after; migration/seed run as owner.
- [ ] Rendered configuration diff showing owner only in the migration job, app in API/worker, backup in the backup job; passwords redacted.
- [ ] Restore drill with ownership/grant reapplication and post-restore smoke.
- [ ] Rollback rehearsal on staging, or a documented tabletop with the exact commands above.
- [ ] Named approver, operator, second reviewer, date, and maintenance window.

## Remaining implementation gaps before H6 can close

| Gap | Why it blocks closure | Owner/action |
|---|---|---|
| Compose still runs Alembic/seed in `api` | Owner credential would leak into runtime | Add a one-shot `migrate` service; API/worker use app URL |
| Backup script defaults to `feedesk` | Backup still uses an owner credential | Pass `feedesk_backup` explicitly or read a dedicated secret |
| Restore script defaults to `feedesk` and `--no-owner` | Restored objects/grants are wrong | Create DB with `feedesk_owner` or transfer ownership and re-grant after restore |
| Runbooks use `-U feedesk` | Commands will use the break-glass role or fail if that credential is unavailable | Update `worker-recovery`, `unknown-outcomes`, `provider-outage`, `key-rotation`, `backup-restore`, `first-run-checks` |
| No versioned `grants.sql` | Grants drift after migrations | Commit an idempotent grant/hardening script and a post-migration check |
| Test suite requires DDL | It cannot run as `feedesk_app` | Keep schema tests on a scratch DB as owner; add an app-role smoke lane |
| No grant-drift check | A migration can widen app rights | Add a verification query/test to CI or the deploy checklist |
| Secret rotation for three roles | New credentials are long-lived | Add to `key-rotation.md` after H6 is applied |
| Managed PostgreSQL path untested | Provider may not allow superuser or direct ownership changes | Record provider-specific role procedure or keep self-managed PostgreSQL |
| Break-glass credential custody | `feedesk` superuser remains powerful | Store offline, name custodian, test recovery without app roles |

Until then, H6 remains open. The current Compose topology must not be treated as tamper-proof against a compromised app credential, and OPS-01/OPS-03 or G5 must not be marked complete.
