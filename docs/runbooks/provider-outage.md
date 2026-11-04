# Provider Outage Runbook

**Status:** Template. No live Rasel call, balance check, or outage drill has been
performed. G0/G4 remain open.

## Detection

- Worker logs show provider timeouts, connection errors, or 5xx responses.
- `messages.last_error_summary` reports provider request failure or timeout.
- Failed or unknown message counts rise.
- Provider console or status page reports an outage.
- Read-only balance check reports insufficient balance (when implemented).
- Sender ID is rejected or no longer approved.

## Immediate response

1. **Stop sending.** Stop the worker first, then set the kill switch:
   ```sh
   docker compose ... stop worker
   # Edit /etc/feedesk/feedesk.env:
   #   MESSAGING_KILL_SWITCH=true
   #   MESSAGING_ENABLED=false
   docker compose ... up -d --no-deps api
   ```
   Stop the worker even if the kill switch is set. Settings are read at process
   start; do not assume a running worker picked up an env change. Leave the
   worker stopped until reconciliation is complete.

2. **Do not delete jobs or clear leases.** Leave pending/retry jobs for the
   worker's backoff. Leave unknown messages untouched.

3. **Classify the failure.**
   ```sh
   docker compose ... exec -T db psql -U feedesk -d feedesk -c "
   select coalesce(last_error_code, 'none') as code,
          count(*),
          max(updated_at) as last_seen
   from messages
   where updated_at > now() - interval '2 hours'
   group by 1 order by 2 desc;"
   ```
   | Class | Examples | Action |
   |---|---|---|
   | Auth | invalid key, forbidden | Rotate/verify key in provider portal; do not retry |
   | Balance | insufficient credit | Top up; do not retry until confirmed |
   | Sender | sender not approved | Fix sender approval; no send |
   | Rate limit | 429 | Let backoff work; reduce rate |
   | Provider outage | 5xx, timeouts | Wait, monitor; no manual retry |
   | Destination | invalid/unreachable number | Needs data correction, not a retry |

4. **Protect the school relationship.** If a campaign was interrupted, record
   which recipients may have received a message and which did not. Do not send a
   "correction" campaign without school approval.

## Recovery

1. Confirm provider health, account status, sender approval, and balance through
   the provider's console or a read-only check.
2. Confirm no unknown outcomes are pending. Reconcile them first
   ([unknown-outcomes.md](unknown-outcomes.md)).
3. Re-enable in a controlled window, with the allowlist and lowest rate:
   ```sh
   # MESSAGING_KILL_SWITCH=false
   # MESSAGING_ENABLED=true
   # MESSAGING_ALLOWLIST=<approved test number>
   docker compose ... up -d --no-deps api worker
   ```
   Live enabling requires G0/G4 sign-off. Until then, this step is **not
   authorized**.
4. Watch failures and unknowns for at least one full campaign before widening.
5. Record the outage window, cause, affected campaigns, and provider ticket.

## Do not

- Do not resend unknown or failed messages in bulk.
- Do not run multiple workers to "speed up" recovery.
- Do not change provider credentials and retry at the same time; isolate causes.
- Do not claim messages were delivered based on provider acceptance.

## Provider balance (not implemented)

The Rasel adapter can read balance, but there is no scheduled exporter or admin
display. Until G4 wires a read-only balance check:

- Check the provider console before each campaign.
- Record the balance and time in the campaign checklist.
- Set a manual low-water mark with the school (for example, two campaigns'
  expected cost).
