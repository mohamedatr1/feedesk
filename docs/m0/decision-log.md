# Decision Log

**Status:** Recommended defaults recorded; school approval required before G0.

| ID | Decision | Recommended default | Status | Owner | Needed by |
|---|---|---|---|---|---|
| OD-01 | Currency and symbol | Store ISO code; display symbol configurable; default dev value `SYP` / `د.س` | Pending school | School | W1 |
| OD-02 | Multi-currency messages | One message per guardian per currency; no combined total | Pending | PO/TL | W1 |
| OD-03 | Student names in SMS | Omit by default; use only if school requires | Pending school | School | W1 |
| OD-04 | Retention | Source files 12 months; audit 24 months; fee records per school policy | Pending school | School | W1 |
| OD-05 | Hosting | Secured VPS with encrypted offsite backups; confirm data residency | Pending school | School | W2 |
| OD-06 | Approval policy | Configurable permission; default admin-only approval | Pending school | School | W1 |
| OD-07 | Password reset | Admin temporary password + forced change; email reset P1 | Accepted for M1 | PO | W2 |
| OD-08 | OCR scope | Detect scanned PDFs; optional assisted OCR behind a flag; human verification mandatory | Accepted for M1 | TL | W2 |
| OD-09 | WhatsApp in v1 | Hard-disabled until written Syrian route verification | Accepted | School | W0 |
| OD-10 | Delivery reporting | Decide after provider evidence; adapter supports webhook and polling | Open | TL | G0 |
| OD-11 | Batch personalization | One job/submission per personalized recipient unless Rasel confirms a personalized batch | Accepted | TL | G0 |
| OD-12 | Send pacing | Default 1 message/second, 100/day; configurable | Accepted provisional | PO/TL | W2 |
| OD-13 | Error tracking | Self-hosted or SaaS with PII scrubbing; never log message bodies | Open | TL | W2 |
| OD-14 | Contact permission/opt-out | Written policy; record communication restriction per guardian; show as exclusion reason | Pending school | School | W1 |

## Notes

- The dev seed uses `SYP` and `د.س` only to make the UI testable. It is not a production decision.
- The school must approve the final Arabic template wording before production.
- The approval policy must record both preparer and approver even when one person performs both actions.
