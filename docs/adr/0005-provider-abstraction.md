# ADR 005 — Messaging provider abstraction

**Status:** Accepted  
**Date:** 3 November 2026

## Context

Rasel is the initial provider. The published contract may differ from the school account, and future providers may be added. The application must not leak provider details into campaign or finance logic.

## Decision

- Define a narrow provider port: `send`, `get_status`, `get_balance`, `health`.
- Implement a fake adapter for development and tests.
- Implement a Rasel adapter behind the port.
- Keep API keys server-side, encrypted at rest, masked in UI, and absent from logs and frontend bundles.
- Map provider responses to internal states only after their meaning is verified.
- Treat a timeout or ambiguous response as `unknown`; never resend automatically.
- Use one durable job/submission per personalized recipient.
- Hard-disable WhatsApp until the Syrian route and sender are verified.

## Consequences

- Provider-specific payloads are stored only as redacted diagnostics.
- A second provider can be added without changing campaign snapshots.
- The adapter contract must be re-tested against the school account at G0.
