# ADR 003 — Money representation and validation

**Status:** Accepted  
**Date:** 3 November 2026

## Context

Fee values come from Excel/PDF statements and must remain traceable. Binary floating point can silently change amounts, and currencies may differ between records.

## Decision

- Store money as PostgreSQL `NUMERIC(18,2)`.
- Parse into Python `Decimal`, never through binary float.
- Store the reviewed source remaining balance in `remaining_balance_source`.
- If total fee and paid amount are available, compute a comparison balance for validation only.
- Never overwrite the source balance with a calculated value.
- Never invent missing total fees.
- Require an explicit ISO currency per record.
- Group totals by currency and never combine currencies in messages.
- Preserve before/after values for financial corrections.

## Consequences

- Import and campaign code must use decimal-aware helpers.
- Database migrations must not introduce floating-point money columns.
- UI formatting may round for display, but stored and snapshotted values remain exact.
