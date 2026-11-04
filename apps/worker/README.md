# Worker (M4)

The background worker will process durable `send_jobs` from PostgreSQL using `SELECT ... FOR UPDATE SKIP LOCKED`, call the messaging provider adapter, and update message/campaign states.

It is intentionally not implemented in M1. See ADR 006 and the M4 tasks in `FeeDesk-Task-Register.csv`.
