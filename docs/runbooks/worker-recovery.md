# Worker Crash and Recovery Runbook

**Status:** Template; recovery behavior is implemented and unit-tested, but no
production crash/recovery drill has been run.

The worker is the only process that claims `send_jobs`. The API never sends.
Jobs are claimed with `FOR UPDATE SKIP LOCKED` and a lease; a crashed worker's
lease expires and another worker can reclaim the job.

## Symptoms

- `FeeDeskWorkerStalled`: oldest pending job > 5 minutes.
- `FeeDeskStaleLeases`: claimed job with `lease_expires_at < now()`.
- `FeeDeskQueueBacklog`: pending/retry jobs above threshold.
- No `worker.start` line after a deploy.
- `worker` container restarting repeatedly.

## Triage (read-only)

```sh
docker compose ... ps worker
docker compose ... logs --tail=200 worker

docker compose ... exec -T db psql -U feedesk -d feedesk -c "
select status, count(*),
       min(created_at) as oldest,
       min(next_attempt_at) as next_attempt
from send_jobs
group by status
order by status;"

docker compose ... exec -T db psql -U feedesk -d feedesk -c "
select id, status, attempt_count, lease_expires_at, heartbeat_at, last_error
from send_jobs
where status = 'claimed'
order by lease_expires_at
limit 20;"

docker compose ... exec -T db psql -U feedesk -d feedesk -c "
select internal_status, count(*)
from messages
group by internal_status
order by internal_status;"
```

## Recovery

1. **Confirm one worker only.**
   ```sh
   docker compose ... ps --services --filter status=running | grep worker
   ```
   If two workers are running, stop the extra one before doing anything else.
   Leases reduce duplication but are not a licence to run two workers during an
   incident.

2. **Restart the worker.**
   ```sh
   docker compose ... restart worker
   docker compose ... logs --tail=100 worker
   ```
   A graceful stop requests `worker.stop_requested`; it finishes the current job
   or clears the lease before exiting.

3. **Wait for lease expiry.** Do not hand-edit `send_jobs` or clear leases in the
   database. The default lease is 60 seconds
   (`MESSAGING_LEASE_SECONDS`). A new worker reclaims expired claims.

4. **Verify.**
   - New `worker.loop` / `worker.once` log lines appear.
   - `oldest pending` age decreases.
   - `stale_claimed_jobs` returns to zero.
   - No message moves to `unknown` unexpectedly.

5. **If restart loops**, check disk, database reachability, and configuration:
   ```sh
   docker compose ... logs --tail=300 worker
   df -h
   curl -fsS https://${APP_DOMAIN}/health/ready
   ```
   The worker exits non-zero on an unrecoverable startup error. Do not loop
   restarts blindly; capture the error first.

## Crash during provider submission

If the worker died while a message was `submitting`, the outcome is unknown.
Follow [unknown-outcomes.md](unknown-outcomes.md). Do not resend.

## Safe diagnostic mode

`python -m app.worker --once` claims and processes **at most one** job. It is
only safe while messaging is disabled or the provider is fake:

```sh
docker compose ... run --rm worker python -m app.worker --once
```

Never use it against a live provider to "see if it works".

## Escalation

If the queue cannot drain and the provider is reachable, stop the worker and
escalate. A backed-up queue is safer than uncontrolled retries.
