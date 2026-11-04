# M0 — Rasel Verification Evidence

**Date:** 3 November 2026  
**Owner:** Tech Lead  
**Status:** Partial — G0 not passed  
**Secret handling:** The API key is stored only in `F:\FeeDesk\.env.local` (gitignored). It is not recorded here or in source control.

---

## 1. Authentication and account access

| Check | Result | Evidence |
|---|---|---|
| API key accepted | Pass | `GET /api/v2/account` → HTTP 200 |
| Account accessible | Pass | Wallet, plan, and profile returned |
| Phone verified | Pass | `profile.phoneVerified = true` |
| Business name verified | **Blocked** | `profile.businessNameVerified = false` |
| App name verified | **Blocked** | `profile.appNameVerified = false` |
| Account can send | Pass | `subscription.access.canSend = true` |
| Plan active | Pass | Trial plan active, ends `2026-11-10T17:52:27Z` |
| Wallet balance | Note | USD 0.10 available; likely insufficient for a real campaign |
| Usage this period | Note | 1 message/segment already counted |

The account is reachable and the key has useful scopes, but the commercial and sender-identity setup is not ready for production.

## 2. SMS sender names

`GET /api/v2/sms-senders` and `GET /api/v2/sms-senders?approvedOnly=true` both returned HTTP 200 with **0 sender names**.

**Impact:** FeeDesk cannot send a production fee reminder until an approved SMS sender exists and is selected for the account. This is a hard G0 blocker.

Required actions:

1. Create an SMS sender name in the Rasel dashboard.
2. Submit it for approval.
3. Confirm the approved sender ID/name.
4. Add the approved sender ID to `RASEL_SENDER_ID`.
5. Repeat the controlled test with that sender.

## 3. Syrian SMS policies

`GET /api/v2/messages/policies` returned 16 policies. The relevant local-Syria routes are:

| Provider | Channel | Enabled | Allowed message types | Free-text fee reminder? |
|---|---|---:|---|---|
| `sms_mtn` | `sms_syria` | Yes | OTP, utility, marketing, free_text | **Yes** — priority 1 |
| `sms_syriatel` | `sms_syria` | Yes | OTP only | **No** — free text not allowed |
| `sms_taqnyat` | `sms_syria` | Yes | OTP, utility, marketing, free_text | **Yes** — priority 3 |

**Conclusion:** A free-text reminder can use the MTN route (preferred) or Taqnyat fallback. Syriatel currently permits OTP only, so it cannot be assumed for fee reminders. The final routing decision must be confirmed with a real send.

## 4. Send contract baseline

Published contract used for the adapter design:

```http
POST https://raselsms.com/api/v2/messages/send
X-API-Key: <server-side key>
Idempotency-Key: <stable per-message key>
Content-Type: application/json

{
  "to": "+9639XXXXXXXX",
  "channel": "local_sms",
  "messageType": "free_text",
  "content": { "text": "..." }
}
```

Response fields observed in documentation:

- `success`
- `requestId`
- `status` (`sent`, `queued`, `scheduled`, ...)
- `resolved.channel`
- `resolved.provider`
- `billing.estimatedCost`, `billing.currency`
- `tracking.messageId`, `tracking.usageId`

**Important:** `status: sent` is not proof of delivery. Delivery must be confirmed through a status query or callback whose semantics are verified with the school account.

## 5. What is verified

- The API key works against the account and policy endpoints.
- The account can send according to the plan snapshot.
- Local Syria SMS routes exist for MTN and Taqnyat with free-text support.
- WhatsApp is present on the platform, but remains disabled for FeeDesk v1 by project policy.
- The send endpoint and idempotency header match the current PRD baseline.

## 6. What is not verified

- An approved sender name for the school.
- A real Arabic fee-reminder message delivered to a school-controlled `+963` number.
- Delivery-report/callback behavior for this account.
- Segment counting and billing for Arabic Unicode on the selected route.
- Rate limits and insufficient-balance behavior for this account.
- Whether the trial plan and USD 0.10 balance are sufficient for the pilot.
- Business/app name verification, which may be required before production.

## 7. Controlled send attempts — 3 November 2026

Two attempts were made using the account's verified phone. No message was delivered.

| Attempt | Channel | Result | Interpretation |
|---|---|---|---|
| 1 | `local_sms` | HTTP 400 `LOCAL_SMS_REQUIRES_SYRIAN_NUMBER` | The account phone is not a Syrian `+963` number; a school-controlled Syrian number is required. |
| 2 | `int_sms` | HTTP 403 `TRIAL_FIXED_MESSAGE_RESTRICTED` (request `msgreq_1793732136892_ckzub8`) | The trial plan does not allow this free-text send. The provider response points to the verification endpoint or a paid/fixed-message plan. |

**Conclusion:** FeeDesk cannot complete the controlled Arabic fee-reminder test until:

1. A school-controlled Syrian number is provided.
2. The Rasel account is moved to a plan that permits free-text SMS (or Rasel explicitly enables the test).
3. An approved sender is available for the selected route.

The send endpoint, authentication, idempotency header, and error envelope were exercised successfully; the block is commercial/route-level, not a FeeDesk authentication failure.

## 8. Required before G0 can pass

| # | Action | Owner | Evidence |
|---|---|---|---|
| 1 | Create and approve an SMS sender | School | Sender ID/name in Rasel |
| 2 | Add 3 school-controlled test numbers | School | Number register (private) |
| 3 | Run a direct Arabic test through the approved sender | TL | Message received + provider record |
| 4 | Confirm delivery-report/status-query behavior | TL | Written/provider evidence |
| 5 | Confirm segment/pricing rules | Rasel / TL | Written rule + examples |
| 6 | Confirm trial/balance is sufficient | School | Top-up or plan confirmation |
| 7 | Record the sender ID in `.env.local` | TL | `RASEL_SENDER_ID` set |
| 8 | Repeat the test through the FeeDesk adapter | TL | MSG-04 evidence |

## 9. Security note

The key was shared in the working conversation. It is stored locally in a gitignored file and is never sent to any host other than `raselsms.com`. If the conversation or logs are retained outside the school's control, rotate the key after configuration.

**G0 status: BLOCKED — provider route is reachable, but sender approval, test delivery, and commercial confirmation are incomplete.**
