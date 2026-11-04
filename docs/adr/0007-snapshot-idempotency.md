# ADR 007 — Campaign snapshot and idempotency

**Status:** Accepted  
**Date:** 3 November 2026

## Context

A campaign must not change after approval, and a delivery retry must not create a second logical message. The school must be able to prove what was approved.

## Decision

- At approval, freeze campaign identity, recipients, destination phones, guardian names, amounts, currencies, rendered messages, channel, template version, approver, and timestamp.
- Generate a canonical JSON snapshot and SHA-256 hash.
- Verify the snapshot before job creation.
- Create messages and send jobs in the same transaction as approval.
- Give every logical message a UUIDv7-style stable ID and an idempotency key.
- Preserve the key across retries.
- A manual resend creates a new message, a new key, and an audit event.

## Consequences

- Later guardian or balance edits cannot change an approved campaign.
- Approval failure leaves no partial campaign, message, or job state.
- A duplicate job replay cannot create a second logical send.
