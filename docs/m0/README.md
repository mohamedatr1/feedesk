# M0 — Discovery and Provider Validation

**Status:** Partial. G0 is not passed. M1 scaffolding has started at risk.

| Document | Purpose |
|---|---|
| `gate-g0.md` | Gate checklist and blockers |
| `rasel-verification.md` | Account, sender, policy, and contract evidence |
| `sample-register.md` | Requested statement samples and tracking table |
| `statement-taxonomy.md` | Draft field dictionary and normalization rules |
| `synthetic-fixtures.md` | Synthetic XLSX/PDF fixtures and parser findings |
| `decision-log.md` | Currency, approval, retention, hosting, and communication decisions |
| `../adr/` | Architecture decisions 001–008 |
| `../design/tokens.css` | Observed design tokens |
| `../design/screen-gap.md` | Screen and design-system coverage |
| `../m1/status.md` | Foundation implementation status |

## Current G0 blockers

1. No approved Rasel SMS sender on the account.
2. No delivered Arabic test SMS to school-controlled numbers. `local_sms` rejected the non-Syrian account phone; `int_sms` rejected the trial free-text send.
3. The account is on a trial that does not permit the free-text send; a paid/free-text-enabled plan or provider enablement is required.
4. No real anonymized XLSX/PDF samples (synthetic fixtures exist only for parser development).
5. Pending school decisions on currency, approval, retention, opt-out, hosting, and Arabic wording.
6. Provider business/app verification, pricing, segment rules, and delivery reporting remain unconfirmed.

Live SMS remains disabled. WhatsApp remains hard-disabled.
