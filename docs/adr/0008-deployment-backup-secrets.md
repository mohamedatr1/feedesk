# ADR 008 — Deployment, backups, and secrets

**Status:** Accepted  
**Date:** 3 November 2026

## Context

The school needs a reliable private deployment without a dedicated operations team. Production must not depend on a developer's personal computer.

## Decision

- Deploy the web app, API, worker, and PostgreSQL on a secured server or a managed PostgreSQL service.
- Use HTTPS through a reverse proxy (Caddy or equivalent).
- Keep the database and uploaded files on private storage.
- Inject secrets at runtime; never commit them to source control.
- Encrypt provider credentials at rest; keep the master key outside the database.
- Take encrypted nightly database and file backups, stored off the application server.
- Propose RPO ≤ 24 hours and RTO ≤ 4 hours; use PITR if the school requires tighter recovery.
- Test restore in M1 and again before launch.
- Use expand/contract migrations, a verified backup before migration, and a tested rollback.

## Consequences

- A short maintenance window is acceptable for v1.
- Backup access and restore operations are audited.
- The school must confirm hosting location, retention, and access requirements before production.
