# Delivery Progress

**Last updated:** 4 November 2026  
**Status:** M0 blocked; M1 foundation complete for the implemented surface, formal G1 not passed; M2 import implemented and verified with synthetic fixtures (multi-sheet auto-selection, currency inference, headerless/custom layouts, assisted OCR with human review, bulk exclusion, guardian resolution, property tests) including a 26-fixture import → confirm → campaign → fake-worker run (16/16 campaigns, 139/139 messages), formal acceptance blocked on real school samples; M3 campaign preparation/approval and dashboard/reporting implemented and browser-verified, formal M3/G3 blocked on school copy approval and real data; M4 safe messaging foundation and control plane implemented (fake provider, encrypted credentials, safe test-send, ops panel); live SMS and real Rasel verification remain blocked by G0; M5 formal launch/UAT is blocked, with only pre-G4 security/ops hardening in progress. Pre-G4 H4/H6 decision packages, the OCR memo, and the runbook review record are prepared; all remain open or planned.

Legend: `[x]` complete, `[ ]` not complete. `FeeDesk-Task-Register.csv` has the same status per task.

---

## M0 — Discovery and Provider Validation

- [x] Store the Rasel API key in a gitignored local env file
- [x] Verify the key against the account endpoint
- [x] Read the account snapshot (wallet, plan, verification flags)
- [x] List SMS senders
- [x] List Syria SMS policies
- [x] Attempt a `local_sms` test (blocked: account phone is not Syrian)
- [x] Attempt an `int_sms` test (blocked: trial free-text restriction)
- [x] Create synthetic XLSX samples for parser development
- [x] Create text and scanned PDF samples for parser development
- [x] Create real-sample intake folders under `.local/samples/real/`
- [x] Write Rasel verification evidence
- [x] Write ADRs 001–008
- [x] Write the draft statement taxonomy
- [x] Write the decision log and sample register
- [x] Write the design token baseline and screen gap list
- [ ] Receive 5+ real anonymized XLSX statements
- [ ] Receive 3+ real anonymized PDF statements
- [ ] Get an approved Rasel SMS sender
- [ ] Provide 3 school-controlled Syrian test numbers
- [ ] Move the account to a free-text-enabled plan or get provider enablement
- [ ] Deliver a successful Arabic test SMS
- [ ] Confirm pricing, segments, delivery reports, rate limits, and balance
- [ ] Get school sign-off on currency, approval, retention, opt-out, hosting, and Arabic wording
- [ ] **G0 gate passed**

## M1 — Foundation and Design System

### Backend

- [x] Repository scaffold and monorepo layout
- [x] Local PostgreSQL development cluster
- [x] Config and secret loading
- [x] Initial schema and Alembic migrations
- [x] Append-only audit trigger (update/delete + truncate)
- [x] Argon2id password hashing
- [x] Server-side sessions and expiry
- [x] CSRF on all mutating routes
- [x] RBAC permission guards and matrix tests
- [x] Persistent login lockout + failed-login audit
- [x] Case-insensitive username uniqueness
- [x] Last-active-admin and self-demotion guards
- [x] Request-ID validation and proxy-aware client IP handling
- [x] Settings validation (ISO currency + IANA timezone)
- [x] Health readiness returns 503 when the database is unavailable
- [x] API security headers; production docs disabled
- [x] Production guard for default session secret/seed password
- [x] User management API: create, update, deactivate, reset password
- [x] School settings API
- [x] Audit event API and append-only enforcement
- [x] Private storage abstraction and authenticated download
- [x] Backup and restore drill
- [x] 425 backend tests passing (M1–M4 foundation + M5 hardening + PDF layout edge cases)
- [x] Ruff lint clean
- [x] Configurable approval permission per user (FND-08): admin-managed `can_approve_campaigns` flag, scoped to campaign approval only
- [x] Generated OpenAPI TypeScript client (`lib/openapi.d.ts`, `npm run generate:api`); idempotency convention remains a follow-up
- [ ] Error tracking with PII scrubbing
- [ ] CI executed on a real repository

### Frontend

- [x] Design tokens and Arabic RTL primitives
- [x] App shell: right sidebar, topbar, active nav, skip link, logout
- [x] Login and forced password change
- [x] Settings and users UI
- [x] User edit dialog (role/email/job title)
- [x] Accessible confirmation dialogs
- [x] 44px touch targets and table semantics
- [x] Per-route document titles
- [x] Cached session/settings (no shell remount on navigation)
- [x] Honest loading states and currency fallback removal
- [x] Settings visible to staff read-only; audit link admin-only
- [x] Audit actor names and Arabic action/entity labels
- [x] Contrast-safe metadata, input borders, and focus outline
- [x] TypeScript check
- [x] Production build
- [x] `npm audit` — 0 vulnerabilities
- [x] Design and accessibility review (`docs/design/design-review.md`)
- [x] P1 design fixes
- [ ] Full P2 visual-scale polish (topbar/sidebar/type scale)
- [x] Session-expired explanation on the login screen
- [ ] Frontend automated tests / Playwright suite
- [ ] **G1 gate passed** (blocked by G0 and remaining acceptance evidence)

## M2 — Import and Financial Review

- [ ] Real statement samples validated
- [x] Upload endpoint with extension/MIME/magic-byte checks, limits, SHA-256, duplicate override, and private storage
- [x] Import batch lifecycle, status transitions, and audit events
- [x] XLSX parser: sheets, header detection, merged cells, cached formulas, source rows
- [x] PDF parser: text/tables and page references
- [x] Scanned-PDF detection and assisted local OCR (Tesseract `ara+eng`); OCR rows require human review
- [x] Column mapping: Arabic/English auto-suggestions plus manual mapping
- [x] Staging persistence with raw + normalized JSON and source references
- [x] Validation engine: money, Arabic digits, currency, phone E.164, negative/zero, totals, duplicates
- [x] Import list/detail UI, upload wizard, mapping, and review ledger
- [x] Row editing, revalidation, exclusion, filters, source references, and warning acknowledgment
- [x] Import confirmation transaction with provenance and idempotency
- [x] Duplicate file detection and override with reason
- [x] Fixture-based parser and validation tests
- [x] API smoke flow against synthetic XLSX/PDF fixtures
- [x] Database assertions for guardians, contacts, students, and fee balances
- [x] Frontend typecheck, production build, and `npm audit`
- [x] Browser walkthrough of review and upload flows
- [x] Synthetic 26-fixture end-to-end acceptance: 26/26 imports, 211 rows, 16/16 campaigns completed, 139/139 fake-worker messages delivered, 10 intentional review-only fixtures (`docs/m2/synthetic-acceptance.md`)
- [x] Targeted re-check of layout, counts, exclusion announcement, and currency totals
- [x] Bulk exclusion/restore UI and API with one revalidation and one audit event
- [x] Multi-sheet auto-selection, PDF/XLSX currency inference, headerless/custom-layout fallback, and upload-flow UX
- [x] Manual guardian resolution: candidate matching, row overrides, ambiguous-confirm blocking, UI
- [x] Hypothesis property tests for money and phone normalization
- [ ] Formal golden-file coverage for real school samples
- [ ] **G2 gate passed** (blocked by real samples and G0/G1)

## M3 — Campaign Management and Approval

- [x] Eligibility service with confirmed balances, guardian/currency grouping, and exclusion reasons
- [x] Destination phone selection (primary valid E.164 contact) and shared-phone warnings
- [x] Campaign backend: create/list/detail/preview/draft edit/state machine/permissions
- [x] Template management: version retention, activation, allowed variables, fallbacks, unknown-variable blockers
- [x] Deterministic Arabic renderer with required-variable resolution and plain-text output
- [x] Campaign builder UI with confirmed-import selection, template selection, and readiness checks
- [x] Campaign review UI: counts, per-currency totals, warnings, exclusions, recipient table, message preview
- [x] Submit-for-approval and admin approval with warning acknowledgment and revision checks
- [x] Immutable approval snapshot, canonical SHA-256, frozen recipients/exclusions/warnings, DB immutability trigger
- [x] Transactional approval to pending messages + send jobs + audit, idempotent repeat
- [x] Cancel/revoke flow with reason, snapshot retention, and message/job cancellation
- [x] Campaign list UI with status filters, counts, totals, creator/approver
- [x] Approved/cancelled read-only views with hash and no-send notice
- [x] Browser walkthrough of builder → review → submit → approve
- [x] Shared-dialog focus trap fixed and re-checked (Tab/Shift+Tab, no BODY focus)
- [x] Dashboard/reporting metrics (`RPT-01..03`): metrics API, dashboard UI, idempotent daily snapshot job
- [ ] School-approved Arabic template copy
- [ ] **G3 gate passed**

## M4 — Messaging Foundation

- [x] Provider port and fake adapter scenario matrix
- [x] Rasel adapter implemented behind the port; mocked-HTTP tests only (no live contract verification)
- [x] PostgreSQL worker: SKIP LOCKED claim, lease/heartbeat/reclaim, pacing, graceful stop
- [x] Retry classification/backoff/jitter/max attempts; timeout → unknown, no blind resend
- [x] Idempotency-key replay safety and duplicate-execution protection
- [x] Conservative message status mapping and campaign status derivation
- [x] Message history/detail and campaign results APIs
- [x] Message history/detail and campaign results UI; no send/resend control
- [x] Safety defaults: fake provider, messaging disabled, kill switch on, SMS-only channel lock
- [x] Fake-provider worker smoke: 2 delivered, campaign completed, no provider/network call
- [x] Browser walkthrough of messages/results, 1024/1440 layouts, and no-send controls
- [x] Encrypted provider credential vault + rotation/revoke admin UI
- [x] Worker resolves DB credentials with rotation refresh; revoke releases pending jobs without sending
- [x] Fake/dry-run allowlisted test-send, balance preflight, and per-actor test-send throttle
- [x] Read-only reconciliation/ops panel (queue depth, due/stale jobs, failed/unknown, provider health)
- [x] Browser/API verification of provider settings, operations, and dashboard surfaces
- [x] Fake-provider load/chaos coverage: 100 recipients, reclaim/stale-result fencing, one-send concurrency, retry/timeout, pacing
- [ ] Live test-send and provider reconciliation writes (blocked by G0)
- [ ] Webhooks and pilot
- [ ] **G4 gate passed**

## M5 — Production Hardening (Pre-G4)

- [x] Deployment/backup/monitoring/runbook scaffolding prepared
- [x] Vercel Services production deployment live at `https://feedesk-one.vercel.app`: public Next.js web, private FastAPI via `API_URL` binding, Neon production database, build-time migrations/seed, restored synthetic demo data (51 confirmed imports, 54 campaigns, 346 messages), and live smoke tests (`docs/deployment/vercel-deployment.md`); custom domain, backups, monitoring, and UAT remain open
- [x] Local PostgreSQL backup/restore drill including M1–M4 tables (database only)
- [x] Pre-G4 security/privacy/permission audit completed (0 critical, 6 high, 10 medium, 6 low)
- [x] Full API permission matrix (`OPS-02`): 52 routes, permission/CSRF drift, identity matrix, object isolation
- [x] H3/M1 campaign privacy closure: masked detail, `campaigns.preview`-gated full preview, dedicated `files.download`, browser-verified
- [x] OPS-08 UAT plan, scripts, and execution-record template prepared — **NOT EXECUTED**
- [x] External decision pack: 24 G0/G4/H4/H6/hosting/UAT/support decisions with owners and evidence
- [x] M4/M8 closure: XLSX archive limits (upload + stored-file parse) and recursive audit phone redaction; M7 config guards and encrypted provider credentials applied
- [ ] Security fixes/privacy closure (`OPS-01`/`OPS-03`) — H4 school decision package and H6 provisioning package prepared but open; M7 credential vault fixed
- [ ] Production deployment verification (`OPS-05`)
- [ ] Monitoring stack and delivered alert test (`OPS-06`)
- [ ] Runbook review/rehearsal (`OPS-07`) — desk review record at `docs/runbooks/review.md`; only the local DB restore was exercised
- [ ] UAT with school employee (`OPS-08`) — blocked by G0/G4
- [ ] Training (`OPS-09`)
- [ ] Launch go/no-go (`OPS-10`) — blocked
- [ ] **G5 gate passed**

## M6

- [x] Arabic training guide draft with synthetic-data exercises (`docs/m6/training-guide-ar.md`)
- [x] Handover/support/credential/first-campaign/post-implementation drafts (`docs/m6/`)
- [x] Fake-provider pilot rehearsal (`docs/m6/pilot-rehearsal.md`) — not the live first campaign
- [x] Internal handover readiness review (`docs/m6/handover-readiness-review.md`) — **NOT ACCEPTED**
- [x] Internal training rehearsal (`docs/m6/training-rehearsal.md`) — **not school training delivery**
- [ ] Training delivery (`OPS-09`) — blocked until G0/G4 and a school-approved environment
- [ ] First controlled campaign and hypercare (`OPS-11`) — blocked
- [ ] Handover acceptance (`OPS-12`) — drafts prepared; no sign-off
- [ ] Handover pack acceptance (M6)

---

## Evidence links

- `docs/m0/rasel-verification.md`
- `docs/m0/gate-g0.md`
- `docs/m0/statement-taxonomy.md`
- `docs/m0/decision-log.md`
- `docs/m0/synthetic-fixtures.md`
- `docs/m1/status.md`
- `docs/m2/README.md`
- `docs/m2/api-contract.md`
- `docs/m2/qa-plan.md`
- `docs/m2/verification.md`
- `docs/m2/ocr-decision.md`
- `docs/m3/README.md`
- `docs/m3/api-contract.md`
- `docs/m3/qa-plan.md`
- `docs/m3/verification.md`
- `docs/m4/README.md`
- `docs/m4/api-contract.md`
- `docs/m4/qa-plan.md`
- `docs/m4/verification.md`
- `docs/m4/load-chaos.md`
- `docs/m5/README.md`
- `docs/m5/security-review.md`
- `docs/m5/privacy-retention-plan.md`
- `docs/m5/db-role-separation.md`
- `docs/m5/deployment-readiness.md`
- `docs/m5/external-decision-pack.md`
- `docs/m5/uat-plan.md`
- `docs/m5/uat-scripts.md`
- `docs/m5/uat-execution-record.md`
- `docs/m6/README.md`
- `docs/m6/training-guide-ar.md`
- `docs/m6/first-campaign-runbook.md`
- `docs/m6/support-model.md`
- `docs/m6/credential-handover.md`
- `docs/m6/post-implementation-review.md`
- `docs/m6/handover-pack.md`
- `docs/m6/handover-readiness-review.md`
- `docs/m6/pilot-rehearsal.md`
- `docs/m6/training-rehearsal.md`
- `docs/runbooks/README.md`
- `docs/runbooks/backup-restore.md`
- `docs/runbooks/review.md`
- `docs/design/m4-message-screens.md`
- `docs/design/m3-campaign-screens.md`
- `docs/design/design-review.md`

