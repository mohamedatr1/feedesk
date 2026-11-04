# Unknown Message Outcomes Runbook

**Status:** Template. No live provider reconciliation has been tested. Manual
reconciliation tooling is not implemented; G4 is blocked.

## Meaning

`internal_status = 'unknown'` means FeeDesk could not determine whether the
provider accepted the message. Typical causes:

- provider request timed out after the request may have been sent,
- transport failed mid-request,
- provider returned an unmappable response,
- worker crashed while the message was `submitting`.

Provider **acceptance is not delivery**. An accepted message is still not proof
that the guardian received it.

## Non-negotiable rule

**Do not resend an unknown message.** A blind resend can deliver a duplicate
fee reminder to a guardian. There is no resend control in the UI by design.

## Identify and freeze

1. Stop the worker if unknowns are still being created:
   ```sh
   docker compose ... stop worker
   ```
2. Inspect the affected messages (read-only):
   ```sh
   docker compose ... exec -T db psql -U feedesk -d feedesk -c "
   select m.id, m.campaign_id, m.internal_status, m.provider_status,
          m.provider_message_id, m.idempotency_key, m.last_error_code,
          m.last_error_summary, m.submitted_at, m.updated_at
   from messages m
   where m.internal_status = 'unknown'
   order by m.updated_at desc
   limit 50;"
   ```
3. Inspect the related jobs and campaign:
   ```sh
   docker compose ... exec -T db psql -U feedesk -d feedesk -c "
   select j.id, j.status, j.attempt_count, j.next_attempt_at, j.last_error
   from send_jobs j
   join messages m on m.id = j.message_id
   where m.internal_status = 'unknown';"
   ```
4. Record the campaign ID, message IDs, time window, and provider request IDs in
   the incident log. Do not put phone numbers or names in the log.

## Reconcile with the provider (G4)

1. Use the provider console or a read-only status call, if available, with the
   `provider_message_id`, `idempotency_key`, or request ID.
2. Determine one of:
   - **Accepted/queued/delivered** — record the provider status and evidence.
   - **Rejected** — record the error; a future controlled retry may be allowed.
   - **Not found / no record** — do not assume "not sent"; provider search may be
     incomplete.
3. Get a second person to review before changing any message state.
4. Do not update `messages.internal_status` directly with SQL. There is no
   supported reconciliation command yet. If a correction is unavoidable, it must
   be a reviewed, audited engineering change with a backup first.

## What is missing

- No provider reconciliation API or admin screen.
- No audited manual status-correction workflow.
- No delivery-report webhook.
- No resend workflow.

These are G4/M4-remainder items. Until they exist, unknown outcomes require
engineering escalation and must stay visible.

## Closeout

- [ ] Provider evidence attached to the incident record.
- [ ] Affected guardians identified internally, not in shared channels.
- [ ] Decision recorded: accepted, rejected, or unresolved.
- [ ] Campaign left in `completed_with_errors` if any unknown remains.
- [ ] Worker restarted only after the cause is understood.
- [ ] Follow-up owner and date assigned.
