# ADR 006 — PostgreSQL-backed worker and job semantics

**Status:** Accepted  
**Date:** 3 November 2026

## Context

The expected campaign size is 10–50 recipients, with a tested ceiling of 100. A simple, durable worker is sufficient; Redis and Kubernetes add operational cost without a proven need.

## Decision

- Store send jobs in PostgreSQL.
- Claim jobs with `SELECT ... FOR UPDATE SKIP LOCKED`.
- Use a lease and heartbeat; expired leases are reclaimable.
- Enforce one job per logical message and one logical message per personalized submission.
- Pace submissions; default 1 message/second with a configurable cap.
- On graceful shutdown, stop claiming, finish in-flight work, and release leases.
- Derive campaign status from message outcomes, not worker optimism.
- Hold `unknown` outcomes for reconciliation; never auto-resend.

## Consequences

- Worker restart does not lose queued jobs.
- Two workers cannot process the same job concurrently.
- Database performance and lock behavior must be monitored.
- A distributed queue can be introduced later behind the same job semantics.
