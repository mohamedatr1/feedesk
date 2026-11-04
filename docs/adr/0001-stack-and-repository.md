# ADR 001 — Application stack and repository layout

**Status:** Accepted  
**Date:** 3 November 2026

## Context

FeeDesk is a single-school operational application with Arabic RTL UI, Excel/PDF import, human review, campaign approval, and a background messaging worker. The team is small and the operational budget is limited.

## Decision

Use a modular monolith:

- Next.js 16 + TypeScript for the web application.
- FastAPI + Python 3.10+ for the API.
- PostgreSQL 16 for persistence.
- SQLAlchemy 2 + Alembic for schema and migrations.
- A separate Python worker process sharing the backend codebase.
- A single repository with `apps/api`, `apps/web`, `apps/worker`, `packages/shared`, `infra`, and `docs`.

## Consequences

- One deployment unit and one database simplify transactions and operations.
- Frontend and backend can be developed in parallel with a generated OpenAPI client.
- The worker can be scaled independently without introducing a second codebase.
- Microservices, Redis, and Kubernetes are intentionally deferred.
