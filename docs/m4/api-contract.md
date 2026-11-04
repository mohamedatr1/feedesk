# M4 — Messaging Foundation Contract (First Slice)

**Status:** Binding for the first safe M4 slice. Live Rasel sending remains disabled until G0 passes. The default provider is a deterministic fake adapter; the Rasel adapter is implemented behind the port but is not live-tested in this slice.

## Scope

- Provider port: `send`, `get_status`, `get_balance`, `health`.
- Fake adapter with a scenario matrix.
- Rasel adapter using the published contract, testable with mocked HTTP only.
- PostgreSQL worker: durable claim, lease, heartbeat/reclaim, pacing, graceful stop.
- Retry/idempotency/status mapping and campaign status derivation.
- Message history and campaign results APIs/UI.
- Safety: provider mode, kill switch, SMS-only channel lock, allowlist and rate limit configuration.

Deferred: credential storage/rotation UI, live test-send, webhooks (unverified), balance preflight UI, ops panel, load/chaos, pilot. Those remain open M4 tasks.

## Provider configuration

Environment/config (never returned to the browser):

| Setting | Default | Meaning |
|---|---|---|
| `MESSAGING_PROVIDER` | `fake` | `fake` or `rasel` |
| `MESSAGING_ENABLED` | `false` | Master send switch; worker refuses to send when false |
| `MESSAGING_KILL_SWITCH` | `true` | When true, worker leaves jobs pending |
| `MESSAGING_RATE_LIMIT_PER_SECOND` | `1` | Worker pacing |
| `MESSAGING_MAX_ATTEMPTS` | `3` | Retry cap |
| `MESSAGING_LEASE_SECONDS` | `60` | Claim lease before reclaim |
| `MESSAGING_ALLOWLIST` | empty | E.164 numbers allowed for controlled tests |
| `FAKE_PROVIDER_SCENARIO` | `delivered` | Fake result scenario for dev/E2E |
| `RASEL_API_KEY` | empty | Server-side only |
| `RASEL_BASE_URL` | `https://raselsms.com` | Provider base |
| `RASEL_SENDER_ID` | empty | Approved sender (G0 blocker) |
| `RASEL_CHANNEL` | `local_sms` | SMS channel |

The worker must refuse `rasel` mode when the key or sender is missing, or when `MESSAGING_ENABLED=false`/`MESSAGING_KILL_SWITCH=true`. It must never call the provider in `fake` mode.

## Provider port

```python
@dataclass
class ProviderResult:
    outcome: str  # accepted | queued | delivered | failed | rate_limited | temporary_error | unknown
    provider_status: str | None
    request_id: str | None
    provider_message_id: str | None
    error_code: str | None
    error_summary: str | None
    retry_after_seconds: int | None
    payload_redacted: dict

class ProviderPort(Protocol):
    def send(self, *, to: str, text: str, idempotency_key: str, channel: str) -> ProviderResult: ...
    def get_status(self, *, provider_message_id: str) -> ProviderResult: ...
    def get_balance(self) -> dict: ...
    def health(self) -> bool: ...
```

### Fake adapter scenarios

`delivered`, `accepted`, `queued`, `failed`, `rate_limited`, `timeout`, `temporary_error`, `insufficient_balance`, `invalid_recipient`, `duplicate`. The fake adapter must deduplicate by idempotency key: replaying the same key returns the original result and does not increment its send counter.

### Rasel adapter

- `POST {base}/api/v2/messages/send` with `X-API-Key`, `Idempotency-Key`, `Content-Type: application/json`.
- Body: `{"to": "+963...", "channel": "local_sms", "messageType": "free_text", "content": {"text": "..."}}`.
- Map only conservative states: `queued` → queued; `sent`/accepted → accepted; explicit `delivered` → delivered; failure → failed; unknown/unrecognized → unknown.
- 401/403 auth → permanent failure; 429 → rate-limited with retry-after; 5xx → temporary; timeout/transport ambiguity → unknown, never blind-resend.
- Store only a redacted response payload (no API key, no full request body). The full phone/message stays in the message snapshot.
- Unit tests use `httpx.MockTransport`; no live host call.

## Data model additions

- `messages.provider_payload_redacted` JSON (nullable/default `{}`).
- `send_jobs.lease_expires_at` timestamp (nullable, indexed).
- `send_jobs.heartbeat_at` timestamp (nullable).
- Existing `provider_status`, `provider_request_id`, `provider_message_id`, `last_error_*`, `attempt_count`, `next_attempt_at`, `locked_*` are reused.

Job statuses: `pending`, `claimed`, `retry`, `completed`, `failed`, `unknown`, `cancelled`.

Message statuses: `pending`, `submitting`, `provider_accepted`, `queued_by_provider`, `delivered`, `failed`, `unknown`, `cancelled`.

## Worker behavior

1. Claim one job:
   - status in `pending`/`retry`, `next_attempt_at` null or <= now, or status `claimed` with expired lease;
   - join approved/queued/sending campaign and message;
   - `FOR UPDATE SKIP LOCKED`;
   - set `status=claimed`, `locked_by`, `locked_at`, `heartbeat_at`, `lease_expires_at`, increment `attempt_count`.
2. Refuse to send when `MESSAGING_ENABLED=false`, kill switch true, campaign cancelled, message cancelled/terminal, channel not SMS, or provider config invalid. Release/leave the job safely.
3. Set message `submitting`; call provider with the existing message idempotency key.
4. Apply result:
   - accepted/queued/delivered → message status accordingly, provider ids, submitted_at/delivered_at; job `completed`.
   - failed permanent → message/job `failed`, error code/summary; no retry.
   - rate_limited/temporary → job `retry` with backoff+jitter and retry-after when present, until max attempts; then failed.
   - unknown/timeout → message/job `unknown`; no automatic resend.
5. Derive campaign status after each terminal change:
   - any pending/retry/claimed/submitting → `sending`;
   - all terminal and any failed/unknown → `completed_with_errors`;
   - all failed → `failed`;
   - all accepted/queued/delivered/cancelled → `completed` or `cancelled`.
6. Graceful shutdown stops claiming, finishes the in-flight job, then exits. A crash leaves a lease; another worker reclaims after expiry.

Backoff: exponential base 2s, cap 5 minutes, ±20% jitter, deterministic under a test seed. Max attempts configurable.

## API

### Messages

`GET /api/v1/messages`

Query: `page`, `page_size`, `campaign_id`, `status`, `q` (guardian name or phone).

```json
{
  "items": [MessageSummary],
  "total": 2,
  "page": 1,
  "page_size": 20
}
```

`MessageSummary`:

```json
{
  "id": "uuid",
  "campaign_id": "uuid",
  "campaign_name": "حملة ...",
  "guardian_name": "ولي أمر ...",
  "destination_phone_masked": "+963 9•• ••• 701",
  "amount": "600000.00",
  "currency": "SYP",
  "channel": "sms",
  "internal_status": "delivered",
  "provider_status": "delivered",
  "provider_message_id": "...",
  "last_error_code": null,
  "last_error_summary": null,
  "next_attempt_at": null,
  "submitted_at": "2026-11-04T...",
  "delivered_at": "2026-11-04T...",
  "created_at": "2026-11-03T...",
  "updated_at": "2026-11-04T..."
}
```

`GET /api/v1/messages/{id}` adds `message_body_snapshot`, `provider_payload_redacted`, `provider_request_id`, `attempt_count`, and `next_attempt_at`.

Permissions: `messages.view` (staff/admin).

### Campaign results

`GET /api/v1/campaigns/{id}/results`

Returns `CampaignSummary` fields plus:

```json
{
  "message_count": 2,
  "counts": {
    "pending": 0,
    "submitting": 0,
    "provider_accepted": 0,
    "queued_by_provider": 0,
    "delivered": 2,
    "failed": 0,
    "unknown": 0,
    "cancelled": 0
  },
  "last_activity_at": "2026-11-04T...",
  "delivery_note_ar": "قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط."
}
```

Permissions: `campaigns.view`.

No campaign send/resend endpoint exists. The safe provider control plane adds:

### Provider credentials
- `GET /api/v1/messaging/provider` (`settings.manage`, admin) → provider/credential metadata only: `configured`, `credential_source`, `sender_id`, `channel`, `key_version`, rotation actor/time, `test_send_mode`, `live_send_available=false`.
- `PUT /api/v1/messaging/provider/credential` (CSRF) → `{api_key, sender_id, channel}`; encrypts with Fernet, increments `key_version`, never returns or audits the secret.
- `POST /api/v1/messaging/provider/revoke` (CSRF) → clears ciphertext and deactivates the credential. Database credentials take precedence over environment; a revoked row never falls back to stale env secrets.

### Safe test-send + balance
- `POST /api/v1/messaging/test-send` (CSRF) → `{recipient, message}`; requires the E.164 recipient to be in `MESSAGING_ALLOWLIST`, refuses non-fake providers with `409 LIVE_TEST_SEND_BLOCKED`, returns a fake-provider result with `dry_run=true`, and audits only the masked recipient/outcome. A per-actor audit-backed throttle returns `429 RATE_LIMITED`.
- `GET /api/v1/messaging/balance` → fake preflight (`unlimited`) or a blocked `live_provider_blocked` result; no network call.

### Read-only operations/reconciliation
- `GET /api/v1/messaging/ops/summary` → queue/message/campaign/provider-event counts, provider credential metadata.
- `GET /api/v1/messaging/ops/jobs` → due/stale job rows with masked phone, attempts, lease/heartbeat, last error; no claim tokens.
- `GET /api/v1/messaging/ops/issues?kind=unknown|failed` → reconciliation lists; no write/resend action.
- `GET /api/v1/messaging/ops/messages/{id}` → message detail plus job/provider events/recent audit actions.

All ops routes are `settings.manage` (admin), GET-only, and never return full phones, message bodies, claim tokens, or credentials. Unknown outcomes are never automatically or manually re-sent from this surface.

## Frontend routes

| Route | Screen |
|---|---|
| `/messages` | Message history list with campaign/status/search filters and pager |
| `/messages/[id]` | Message detail with frozen body, status, provider references, redacted payload |
| `/campaigns/[id]/results` | Progress counts, campaign status, per-message list, clear accepted-vs-delivered wording |

The UI must never imply delivery from provider acceptance. No send/resend button exists in this slice.
