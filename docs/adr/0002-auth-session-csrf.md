# ADR 002 — Authentication, sessions, and CSRF

**Status:** Accepted  
**Date:** 3 November 2026

## Context

Users are school administrative employees on shared office machines. The application holds financial and guardian data. The frontend and API are served through one origin in production.

## Decision

- Authenticate with username and password.
- Hash passwords with Argon2id.
- Use server-side sessions stored in PostgreSQL.
- Set an HttpOnly, Secure (in production), SameSite=Lax session cookie.
- Require a CSRF token header on state-changing requests.
- Enforce role permissions in the backend for every protected route.
- Force a password change after an administrator-issued temporary password.
- Revoke other sessions when a password changes.

## Consequences

- Sessions can be revoked immediately.
- No JWT is stored in browser storage.
- The API must remain same-origin or use a trusted reverse proxy.
- In production the cookie name should move to `__Host-fd_session`.
- Users are deactivated, not hard-deleted, because audit events reference the actor and the audit table is append-only.
