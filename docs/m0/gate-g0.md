# G0 — Discovery and Provider Validation Gate

**Date:** 3 November 2026  
**Gate owner:** Product Owner / Tech Lead  
**Result:** **NOT PASSED**

M1 scaffolding has started at risk, as allowed by the delivery plan. No live sending, import confirmation, or production deployment is authorized until G0 passes.

---

## Gate checklist

| # | Criterion | Status | Evidence / blocker |
|---|---|---|---|
| 1 | Scope, team model, and baseline approved | **Blocked** | Plan drafted; school sign-off pending |
| 2 | 5+ XLSX and 3+ PDF anonymized samples received | **Blocked** | No school samples received yet |
| 3 | Statement taxonomy documented | **Partial** | Draft field dictionary created from PRD; requires real samples |
| 4 | Rasel account active and API access enabled | **Pass** | `GET /api/v2/account` 200 |
| 5 | Written provider confirmations: version, endpoint, channel, sender, coverage, use case, pricing, segments, limits, idempotency, DLR | **Partial** | Endpoint, policies, idempotency header, and error envelope verified; trial free-text restriction, sender, pricing, segments, and DLR not confirmed |
| 6 | Controlled test SMS delivered to 3 school numbers | **Blocked** | Two send attempts made: `local_sms` rejected the non-Syrian account phone; `int_sms` rejected the trial free-text send. No message delivered. |
| 7 | Currency/symbol, approval, retention, opt-out, hosting, Arabic wording decisions recorded | **Partial** | Recommended defaults recorded; school approval pending |
| 8 | Design token baseline and screen gap list approved | **Partial** | Token baseline implemented; designer sign-off pending |
| 9 | ADRs 001–008 accepted | **Pass** | ADRs created in `docs/adr/` |

## Conditions to pass G0

1. Receive real anonymized statement samples and validate the taxonomy. Synthetic fixtures exist for parser development only.
2. Get an approved SMS sender and record its ID.
3. Receive 3 school-controlled Syrian `+963` test numbers.
4. Move the Rasel account to a plan that permits free-text SMS, or obtain explicit provider enablement for the test.
5. Deliver a real Arabic test through the approved route and reconcile the provider record.
6. Confirm segment/pricing, delivery reporting, rate limits, and account balance.
7. Get school sign-off on currency, approval policy, retention, opt-out, hosting, and Arabic template.
8. Close the design gap list with the designer.

## What may continue at risk

- Repository, CI, schema, auth, RBAC, audit, storage, design system, shell, and settings.
- Provider adapter scaffolding against documented contracts, using a fake adapter for tests.
- Import parser prototypes using synthetic fixtures only.

## What must wait

- Any live SMS send.
- Import confirmation of real financial records.
- Campaign approval and job creation with real recipients.
- Production deployment and school onboarding.
