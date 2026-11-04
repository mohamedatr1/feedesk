# FeeDesk M6 — Operational Handover Pack

**Document ID:** M6-HO-01  
**Version:** 0.1 (draft for acceptance)  
**Date:** 4 November 2026  
**Status:** **Draft. Handover is not complete and has not been accepted.**  
**Audience:** School administration, incoming technical owner, operations/provider support, security reviewer.  
**Owner:** FeeDesk technical lead (proposed; not yet accepted).  
**Source of truth:** the repository and the evidence documents listed in §13. If this pack conflicts with code, migrations, or a signed gate record, the code/gate record wins.

> **Status statement — read this first**
>
> This pack describes a system whose application surface is implemented and verified **locally**, but whose production operation is **not verified**. G0 is **not passed**. G4 is **not passed**. G5 is **not passed**. No production host, HTTPS certificate, delivered alert, live SMS, UAT, or production deployment exists. OPS-11 (first controlled campaign/hypercare) and OPS-12 (handover) remain open.
>
> Nothing in this document authorises a live send, a production deployment, a restore over live data, a credential rotation, or a retention purge.

---

## 1. Purpose and scope

### 1.1 Purpose / الغرض

This pack gives an incoming operator the minimum accurate picture needed to accept — or refuse — operational ownership of FeeDesk. It separates:

- what is implemented and verified locally;
- what is scaffolded but unexercised;
- what is blocked by an external gate, school decision, or missing evidence.

### 1.2 In scope

- System purpose, architecture, topology, and repository layout.
- Application roles and permissions.
- Environment variable names and non-secret safe states (never credential values).
- Migration, backup, monitoring, and runbook index.
- Known limitations, open gates, and blockers.
- A handover acceptance checklist.

### 1.3 Out of scope

- Live provider verification, campaign execution, and reconciliation (see `first-campaign-runbook.md`).
- Secret values and credential transfer (see `credential-handover.md`).
- Support ownership and SLAs (see `support-model.md`).
- Post-campaign review (see `post-implementation-review.md`).
- Replacing G0/G4/G5 gate records or school sign-off.

### 1.4 Arabic summary / ملخص عربي

حزمة التسليم هذه تصف نظام FeeDesk كما هو موجود فعليًا: واجهة وتطبيق ومهام خلفية مبنية ومختبرة محليًا، لكن التشغيل الإنتاجي غير مثبت. لم يتم تفعيل الرسائل النصية الحقيقية، ولم يتم نشر النظام على خادم إنتاجي، ولم تُعتمد بوابات G0/G4/G5. أي بند يعتمد على الإنتاج أو المزود أو توقيع المدرسة يُعد **محجوبًا** حتى توجد الأدلة والتوقيعات.

---

## 2. System overview

FeeDesk is a private, single-school application for:

1. importing fee statements from Excel/PDF;
2. normalising and reviewing guardian, student, and fee-balance data;
3. preparing a campaign from a confirmed import;
4. approving an immutable recipient/message snapshot;
5. creating pending messages and send jobs;
6. sending through a provider adapter (currently fake by default);
7. showing campaign results, message history, and an operations view.

**Current operating mode:** safe/local. The default configuration is:

```text
MESSAGING_PROVIDER=fake
MESSAGING_ENABLED=false
MESSAGING_KILL_SWITCH=true
```

The Rasel adapter exists and is tested only with mocked HTTP. No live Rasel request, SMS, delivery report, or reconciliation has been verified.

### 2.1 Product boundaries

| Boundary | Current position |
|---|---|
| Tenancy | One school per deployment; no multi-tenant isolation |
| Channel | SMS only; WhatsApp hard-disabled |
| OCR | Scanned PDFs are detected and refused; no OCR execution |
| Approval | Admin-only approval by default; staff can prepare/submit |
| Sending | Worker only; API never sends; no manual resend control |
| Unknown outcomes | Treated as unknown, never auto-resent |
| Data retention | Policy not adopted; no purge job (H4 open) |
| Runtime DB role | Current Compose uses the database owner; H6 role split not applied |

### 2.2 Runtime versions (local evidence)

| Component | Version / requirement | Notes |
|---|---|---|
| Python | 3.10+ | Local venv at `.venv` |
| FastAPI / SQLAlchemy / Alembic | Repository-pinned | See `apps/api/requirements.txt` |
| PostgreSQL | 16 | Local cluster port `55432` |
| Node.js | 24+ | Next.js build |
| Next.js | 16 | App Router, TypeScript, Tailwind |
| Docker / Compose | Compose v2 on target host | Docker absent on the local workstation |
| Caddy | 2 | TLS/headers template |

Version pins must be verified against the release being handed over; this table describes the local development baseline, not a production lockfile.

---

## 3. Verified locally vs blocked

This is the most important distinction in the pack. “Verified locally” means it ran on the development workstation or local PostgreSQL cluster. It does **not** mean production-ready.

### 3.1 Verified locally (with evidence)

| Area | What was verified | Evidence | Limits |
|---|---|---|---|
| Backend suite | 425 tests pass | `docs/m4/verification.md`, `docs/m4/load-chaos.md` | Local test database; not production |
| Lint/type/build | Ruff, TypeScript check, Next.js production build | `README.md`, `docs/m4/verification.md` | Local workstation |
| Permission matrix | 52 protected routes, permission/CSRF drift, identities, object isolation | `docs/m5/security-review.md`; `tests/test_permission_matrix.py` | Does not prove host hardening |
| Auth/RBAC/audit | Argon2id, sessions, CSRF, append-only audit, last-admin guard | `docs/m1/status.md` | MFA not implemented |
| Import | XLSX/PDF parsing, mapping, staging, review, confirm, provenance | `docs/m2/verification.md` | Synthetic fixtures; no real school samples |
| Campaign/approval | Eligibility, Arabic templates, immutable snapshot, pending jobs | `docs/m3/verification.md` | School copy not approved |
| Messaging foundation | Fake provider, worker claim/lease/retry/idempotency, status mapping | `docs/m4/verification.md` | Fake only; Rasel mocked |
| Credential vault | Fernet ciphertext at rest, rotation/revoke, no plaintext return | `docs/m4/verification.md` | No documented/tested vault-key re-encryption procedure |
| Load/chaos | 100 synthetic recipients, reclaim, fencing, 429/timeout, pacing | `docs/m4/load-chaos.md` | Not a capacity benchmark |
| Local DB restore | `pg_dump -Fc` + restore into scratch DB, row counts checked | `docs/runbooks/backup-restore.md` (3 and 4 Nov 2026) | Database only; no uploads/encryption/offsite |
| Security fixes | H1–H3, H5, M1–M10 fixed; H4/H6 open | `docs/m5/security-review.md` | Production role change not applied |
| Compose syntax | YAML parsed | `docs/m5/deployment-readiness.md` | No `docker compose config`; Docker absent |

### 3.2 Blocked or unverified (production-dependent)

Every row below is **blocked** until the stated evidence exists. Do not mark these complete from documentation alone.

| Item | State | Blocking evidence needed |
|---|---|---|
| G0 provider/sender/test number/real samples | **Blocked** (gate open) | Approved sender, free-text plan, 3 Syrian `+963` test numbers, delivered test, reconciled provider record, real anonymised samples |
| G4 messaging verification/pilot | **Blocked** (gate open) | Written pilot authorisation, live test-send, delivery/reconciliation contract, controlled pilot, signed gate |
| G5 launch | **Blocked** (gate open) | OPS-01..OPS-10 and gates closed |
| Production deployment (OPS-05) | **Blocked** (scaffolded only) | Real host, DNS, TLS, firewall, image build, deploy record, smoke checks |
| TLS/DNS | **Blocked** (unverified) | Certificate issuance/renewal, HTTP→HTTPS redirect, HSTS, firewall |
| Backup/restore (OPS-04) | **Blocked** (partial) | Encrypted backup, offsite copy, uploads restore, script `--execute`, production restore drill |
| Monitoring/alerting (OPS-06) | **Blocked** (template only) | Running stack, alert rules loaded, delivered test alert, balance metric |
| Runbooks (OPS-07) | **Blocked** (drafted/desk-reviewed) | Exercise on staging/production; named owners |
| H4 retention/deletion | **Blocked** (open) | School policy S1–S10, purge job, retention fields, legal hold, deletion evidence |
| H6 DB role separation | **Blocked** (open) | `feedesk_owner/app/backup` applied, denial tests, rollback rehearsal |
| UAT (OPS-08) | **Blocked** (not performed) | School employee UAT on approved data; defect triage; sign-off |
| Training (OPS-09) | **Blocked** (not performed) | Arabic training record and attendance |
| Live SMS / pilot | **Blocked** (not performed) | G0/G4 and written go/no-go |
| M6 handover (OPS-12) | **Blocked** (draft) | Signed acceptance checklist §12 |
| M6 hypercare (OPS-11) | **Blocked** (not started) | First controlled campaign and 2-week review |

### 3.3 What “verified locally” does not prove

- That the Compose stack starts on a Linux host.
- That Caddy can obtain or renew a certificate.
- That systemd units run at boot.
- That alerts are delivered or routed without PII.
- That encrypted backups can be decrypted by the custodian.
- That uploads survive a restore.
- That the Rasel account can send a free-text Syrian SMS.
- That provider acceptance equals delivery — it does not.
- That the school has approved copy, retention, opt-out, hosting, or support hours.

---

## 4. Architecture and topology

### 4.1 Logical architecture

```text
                         School users (Arabic RTL browser)
                                      |
                                      | HTTPS
                                      v
                         +-------------------------+
                         |  Caddy 2 (proxy)        |
                         |  TLS, headers, /health  |
                         +------------+------------+
                                      |
                     +----------------+----------------+
                     |                                 |
                     v                                 |
          +---------------------+                      |
          | Next.js 16 (web)    |                      |
          | UI + /api rewrite   |                      |
          +----------+----------+                      |
                     |                                 |
                     v                                 |
          +---------------------+                      |
          | FastAPI (api)       |<---------------------+
          | auth, RBAC, imports |   /health/* direct
          | campaigns, messages |
          +----+-----------+----+
               |           |
               |           +----------------------+
               v                                  v
      +------------------+               +------------------+
      | PostgreSQL 16    |               | Private uploads  |
      | private network  |               | named volume     |
      +--------+---------+               +------------------+
               ^
               | claim / lease / idempotency
      +--------+---------+
      | Worker           |
      | python -m app.worker
      +--------+---------+
               |
               | provider port (fake by default)
               v
      +------------------+
      | Rasel adapter    |  <-- no live call verified
      | (mocked tests)   |
      +------------------+
```

### 4.2 Production-like services

| Service | Image/build | Exposure | Responsibility | Current state |
|---|---|---|---|---|
| `proxy` | `caddy:2-alpine` | Host `80`, `443`, `443/udp` | TLS, security headers, `/health/*` routing, HTTP→HTTPS | Template; never run |
| `web` | `apps/web/Dockerfile` | Private `app` network | Next.js UI; rewrites `/api/*` to `api:8000` | Image never built |
| `api` | `apps/api/Dockerfile` | Private `app` + `backend` | HTTP API, migrations, seed, file downloads | Image never built |
| `worker` | same build as `api` | Private `app` + `backend` | Only sender process; claims `send_jobs` | Fake only; no production run |
| `db` | `postgres:16` | Private `backend` only; no host port | PostgreSQL data | Container never run |

**Named volumes:** `feedesk_prod_db`, `feedesk_prod_uploads`, `feedesk_prod_caddy_data`, `feedesk_prod_caddy_config`.

**Networks:** `app` (egress-capable; proxy/web/api/worker) and `backend` (`internal: true`; api/worker/db). The database is not published to the host.

**Trust boundaries:**

1. Browser → Caddy: untrusted input; TLS; security headers; no access log by default (query strings could contain PII).
2. Caddy → Next.js/API: trusted proxy network; `X-Forwarded-For` overwritten.
3. API/worker → PostgreSQL: private network; current credential is the database owner (H6 open).
4. Worker → provider: outbound HTTPS; credentials resolved server-side; provider payload redacted.
5. Uploads: API-only access through authenticated download; no public static serving.

### 4.3 Primary data flow

```text
Upload (XLSX/PDF)
  -> validate extension/MIME/magic/size/archive limits
  -> store private source file + SHA-256
  -> parse sheets/pages -> map columns
  -> stage raw + normalised rows
  -> validate money/phones/currencies/duplicates
  -> human review / exclusions / guardian resolution
  -> confirm inside one transaction
       -> guardians, contacts, optional students, relationships, fee_balances
       -> provenance + audit
  -> create campaign from confirmed import
  -> eligibility/exclusions + per-currency totals
  -> render approved Arabic template version
  -> submit for approval
  -> admin approval -> immutable snapshot (SHA-256)
       -> pending messages + pending send jobs + audit
  -> worker claims job (SKIP LOCKED + lease)
  -> provider call with idempotency key
  -> status mapping (acceptance != delivery)
  -> campaign status derived from message outcomes
```

**No send affordance exists in the UI.** Approval creates pending jobs; only the worker processes them, and only when messaging is deliberately enabled.

### 4.4 Failure boundaries

| Failure | Behaviour |
|---|---|
| API crash | Web shows error; worker continues only if API was already healthy; no send from API |
| Worker crash | Lease expires; another worker may reclaim; a reclaimed `submitting` becomes `unknown`, never resent |
| Provider timeout/ambiguity | `unknown` + reconciliation required; no blind resend |
| Duplicate worker | Leases reduce duplication; operationally run one worker (pacing is per process) |
| Database unavailable | Readiness fails; worker cannot claim; no silent fallback |
| Provider auth/balance/sender failure | Jobs retry/fail per classification; operator must stop and classify |
| Upload failure | Import remains staged/reviewable; no partial confirmation |

---

## 5. Repository layout

```text
F:\FeeDesk
├── apps/
│   ├── api/                 FastAPI, SQLAlchemy, Alembic, worker, pytest
│   │   ├── app/
│   │   │   ├── routers/     HTTP route modules
│   │   │   ├── imports/     parsing, normalisation, validation, storage
│   │   │   ├── campaigns/   eligibility, rendering, snapshot, service
│   │   │   ├── messaging/   port, fake, Rasel, credentials, worker, ops
│   │   │   ├── dashboard/   metrics and daily snapshot
│   │   │   ├── models.py    ORM entities
│   │   │   ├── security.py  sessions, RBAC, password hashing
│   │   │   ├── audit.py     append-only audit helper
│   │   │   ├── privacy.py   masking/redaction helpers
│   │   │   ├── worker.py    worker entry point
│   │   │   └── seed.py      idempotent school/admin seed
│   │   ├── alembic/         migration chain
│   │   └── tests/           backend and permission-matrix tests
│   ├── web/                 Next.js 16 App Router, TypeScript, Tailwind, RTL
│   │   ├── app/             login, dashboard, statements, campaigns, messages,
│   │   │                    operations, settings, audit, change-password
│   │   ├── components/      shell, tables, dialogs, domain components
│   │   └── lib/             API client, session, formatting
│   └── worker/              reserved for worker-specific deployment assets;
│                            runtime lives in apps/api/app/worker.py
├── packages/
│   └── shared/              reserved for generated API types
├── infra/
│   ├── compose/             dev + production-like Compose, Caddyfile, env templates
│   ├── systemd/             feedesk.service, backup service/timer
│   └── monitoring/          Prometheus/Alertmanager/Loki templates, checklist
├── docs/
│   ├── adr/                 ADR 001–008
│   ├── m0/                  discovery, G0, samples, decisions
│   ├── m1/ … m5/            milestone evidence
│   ├── m6/                  this handover package
│   ├── runbooks/            operational procedures and review record
│   └── design/              tokens, screen specs, design review
├── scripts/                 db helper, Rasel read-only check, backup/restore
├── FeeDesk-Task-Register.csv
├── PRD.md
└── FeeDesk-Delivery-Plan.md
```

### 5.1 Key entry points

| Entry point | Path | Purpose |
|---|---|---|
| API app | `apps/api/app/main.py` | FastAPI app, routers, middleware, health |
| Worker | `apps/api/app/worker.py` | Claim/process loop, graceful stop |
| Seed | `apps/api/app/seed.py` | Idempotent school/admin seed |
| Migrations | `apps/api/alembic/` | Schema chain |
| Web root | `apps/web/app/layout.tsx` | RTL shell and route layout |
| Prod Compose | `infra/compose/docker-compose.prod.yml` | Topology template |
| Caddy | `infra/compose/Caddyfile` | TLS/headers/routing |
| Backup | `scripts/feedesk_backup.py` | DB + uploads + manifest |
| Restore | `scripts/feedesk_restore.py` | Scratch-only restore helper |

### 5.2 API surface (prefix `/api/v1`)

| Router | Main concern |
|---|---|
| `auth` | login, logout, session, password change |
| `users` | admin user management, roles, reset, deactivate |
| `settings` | school settings, messaging/provider settings |
| `audit` | append-only audit query |
| `dashboard` | KPIs, action queue, trends |
| `files` | authenticated private download |
| `imports` | upload, process, map, review, confirm, cancel |
| `templates` | Arabic template versions and activation |
| `campaigns` | create, preview, submit, approve, cancel, results |
| `messages` | message history/detail |
| `messaging_control` | credential rotate/revoke, test-send, balance preflight |
| `messaging_ops` | read-only queue/failed/unknown operations view |

Health endpoints are public by design: `/health/live`, `/health/ready`. Login is public by design.

---

## 6. Data model overview

Core tables (not exhaustive):

| Group | Tables | Notes |
|---|---|---|
| Identity | `users`, `sessions` | Argon2id; server-side sessions; deactivate, not hard-delete |
| School | `school_settings` | Name, currency, locale, timezone, contacts, limits |
| Import | `import_batches`, `source_files`, `staged_rows` | Source provenance; raw + normalised staged data |
| People | `guardians`, `guardian_contacts`, `students`, `guardian_student_relationships` | No phone-only merges |
| Finance | `fee_balances` | Decimal money; source row provenance |
| Templates | `message_templates` | Retained versions; activation |
| Campaign | `campaigns`, `campaign_recipients` | Immutable approved snapshot; DB trigger against mutation |
| Messaging | `provider_credentials`, `messages`, `send_jobs`, `provider_events` | Encrypted provider key; claim/lease/idempotency |
| Audit | `audit_events` | Append-only; update/delete/truncate triggers |
| Reporting | `dashboard_metrics_daily` | Idempotent daily snapshot |

**Known data caveats:**

- `SourceFile.retention_until` exists but is not populated.
- No purge/anonymisation job exists (H4).
- Duplicate override writes a second physical copy of the source file.
- Audit is append-only; owner-run archival is not implemented.
- Deleting live data does not delete encrypted backups.

---

## 7. Roles and permissions

### 7.1 Application roles

| Role | Intended user | Effective permissions | Restrictions |
|---|---|---|---|
| `admin` | School administrator / technical administrator | Wildcard `*` — all permissions | Can approve campaigns, manage users/settings/templates, view audit |
| `staff` | School office user | Dashboard, files, imports (view/upload/review/confirm), finance view, guardians view, campaigns (view/create/edit/preview/submit), messages view, settings view, templates view | **Cannot approve campaigns**, manage users/settings/templates, or view audit |

There is no separate `auditor` role in the application. The permission matrix tests include an auditor-style identity for route isolation, but production roles are `admin` and `staff`.

### 7.2 Permission groups (observed in routes)

| Group | Permissions |
|---|---|
| Dashboard | `dashboard.view` |
| Files | `files.download` |
| Imports | `imports.view`, `imports.upload`, `imports.review`, `imports.confirm` |
| Finance/guardians | `finance.view`, `guardians.view` |
| Campaigns | `campaigns.view`, `campaigns.create`, `campaigns.edit`, `campaigns.preview`, `campaigns.submit`, `campaigns.approve` |
| Messages | `messages.view` |
| Templates | `templates.view`, `templates.manage` |
| Settings | `settings.view`, `settings.manage` |
| Users | `users.manage` |
| Audit | `audit.view` |

### 7.3 Account rules

- Every user must have a named account; no shared logins.
- First login forces a password change for the seeded administrator.
- Password reset is admin-initiated temporary password + forced change.
- Deactivation, not deletion, preserves audit references.
- Last-admin safeguards prevent removing the final administrator.
- MFA is **not implemented**. Compensate with a strong unique password, restricted host access, and short session policy; record the residual risk.
- Admin approval is the default policy; the approval permission is not yet configurable per user (FND-08 remainder).
- Do not give `admin` to routine staff merely to bypass an approval bottleneck. Use a named backup approver.

### 7.4 Technical roles vs application roles

| Role | Belongs to | Should not be the same person by default |
|---|---|---|
| School admin | School | Holds `admin` in the app; approves campaigns and users |
| Technical owner | FeeDesk/operations | Holds host/SSH, deploy, backup, DB, monitoring; may hold a separate named app admin only if needed |
| Provider/ops | Provider account owner | Holds Rasel console, sender, balance, provider tickets |
| Security | School/technical security | Holds incident authority, key custody, access review |

Separation reduces both mistake and abuse risk. Where one person must hold two roles, record the conflict and a compensating review.

---

## 8. Environment variables (names and non-secret safe states)

> **Never put values in this document, tickets, chat, screenshots, or source control.** The templates are `.env.example` (local) and `infra/compose/.env.production.example` (production-like). Production uses `/etc/feedesk/feedesk.env`, mode `0600`. The tables below list names and, where useful, non-secret safe defaults (such as `fake`/`false`); they never contain a credential value.

### 8.1 Core

| Name | Purpose | Required | Notes |
|---|---|---|---|
| `APP_ENV` | Environment mode | Yes | Production must be `production`; guards fail closed |
| `APP_NAME` | Display name | No | Defaults to FeeDesk |
| `DATABASE_URL` | SQLAlchemy database URL | Yes | Built in prod Compose from `POSTGRES_PASSWORD`; never paste it |
| `SESSION_SECRET` | Session signing/secret material | Yes | ≥32 chars in production |
| `APP_BASE_URL` | Public base URL | Yes | Must be `https://` in production |
| `API_BASE_URL` | API base URL | Yes | Public HTTPS in production |
| `UPLOAD_DIR` | Private upload directory | Yes | `/data/uploads` in Compose |
| `LOG_LEVEL` | Log verbosity | No | `INFO` default |
| `COOKIE_NAME` | Session cookie name | Yes | Production `__Host-fd_session` |
| `COOKIE_SECURE` | Secure cookie flag | Yes | Must be true in production |
| `TRUST_FORWARDED_FOR` | Trust proxy header | No | Only behind trusted proxy |
| `SESSION_HOURS` | Session lifetime | No | 8 hours default |
| `LOGIN_RATE_LIMIT` | Login attempts per window | No | 5 default |
| `LOGIN_RATE_WINDOW_SECONDS` | Login rate window | No | 60 default |
| `LOGIN_LOCKOUT_THRESHOLD` | Failed attempts before lockout | No | 5 default |
| `LOGIN_LOCKOUT_MINUTES` | Lockout duration | No | 15 default |
| `UPLOAD_MAX_BYTES` | Max upload size | No | 20 MiB default |
| `IMPORT_MAX_ROWS` | Max import rows | No | 5000 default |
| `IMPORT_MAX_PAGES` | Max PDF pages | No | 200 default |
| `XLSX_MAX_UNCOMPRESSED_BYTES` | XLSX archive bound | No | 200 MiB default |
| `XLSX_MAX_MEMBER_BYTES` | XLSX member bound | No | 100 MiB default |
| `XLSX_MAX_COMPRESSION_RATIO` | XLSX ratio bound | No | 100 default |
| `XLSX_MAX_MEMBERS` | XLSX member count | No | 10000 default |

### 8.2 Provider and credential vault

| Name | Purpose | Required | Notes |
|---|---|---|---|
| `RASEL_API_KEY` | Provider API key (env fallback) | Pre-G4: empty | Prefer encrypted DB vault; never log/return |
| `RASEL_BASE_URL` | Provider base URL | Yes | Must be HTTPS; default `https://raselsms.com` |
| `RASEL_CHANNEL` | Provider channel | Yes | `local_sms` or `sms` |
| `RASEL_SENDER_ID` | Approved sender ID | G0 | Empty pre-G0 |
| `PROVIDER_CREDENTIAL_KEY` | Fernet key for provider vault | Yes in production | Losing it makes stored provider credentials unreadable |
| `MESSAGING_TEST_SEND_LIMIT` | Per-actor test-send throttle | No | 5 default |
| `MESSAGING_TEST_SEND_WINDOW_SECONDS` | Test-send throttle window | No | 60 default |

### 8.3 Messaging safety

| Name | Purpose | Safe default | Notes |
|---|---|---|---|
| `MESSAGING_PROVIDER` | `fake` or `rasel` | `fake` | Live requires G0/G4 |
| `MESSAGING_ENABLED` | Master send switch | `false` | Must stay false pre-G4 |
| `MESSAGING_KILL_SWITCH` | Stop sending | `true` | Must stay true pre-G4 |
| `MESSAGING_RATE_LIMIT_PER_SECOND` | Per-process pacing | `1` | Per worker process, not global |
| `MESSAGING_MAX_ATTEMPTS` | Retry cap | `3` | Exhaustion → `failed` |
| `MESSAGING_LEASE_SECONDS` | Claim lease | `60` | Expiry allows reclaim |
| `MESSAGING_ALLOWLIST` | E.164 test recipients | empty | Comma-separated; no names |
| `MESSAGING_ALLOW_FAKE_IN_PRODUCTION` | Allow fake in prod | `false` | Never for live delivery |
| `FAKE_PROVIDER_SCENARIO` | Fake outcome | `delivered` | Test only |

### 8.4 Seed and school defaults

| Name | Purpose | Notes |
|---|---|---|
| `SEED_ADMIN_USERNAME` | Initial admin username | `admin` default |
| `SEED_ADMIN_PASSWORD` | Initial temporary password | One-time; force change; never reuse |
| `SEED_ALLOW_DEFAULT_PASSWORD` | Allow default in non-prod | Never in production |
| `SEED_SCHOOL_NAME` | Initial school name | School must confirm |
| `SEED_CURRENCY` | ISO currency | School decision pending |
| `SEED_CURRENCY_SYMBOL` | Display symbol | School decision pending |

### 8.5 Backup and host

| Name | Purpose | Notes |
|---|---|---|
| `POSTGRES_PASSWORD` | Database password | Required by Compose; current role is owner |
| `BACKUP_DIR` | Backup output directory | `/var/backups/feedesk` |
| `BACKUP_RETENTION_DAYS` | Daily artifact retention | Proposed 30 |
| `BACKUP_UPLOADS_VOLUME` | Uploads volume name | `feedesk_prod_uploads` |
| `BACKUP_METRICS_TEXTFILE` | Backup metric textfile | For node_exporter |
| `BACKUP_AGE_RECIPIENT` | age public recipient | Required for encrypted `--execute` |
| `COMPOSE_ENV_FILE` | Compose env file path | Used by scripts |
| `APP_DOMAIN` | Public hostname | Required by Caddy |
| `API_INTERNAL_URL` | Web→API URL for the Next bridge | `http://api:8000` in Compose; Vercel injects the `API_URL` service binding instead |

### 8.6 Environment rules

1. Production must not reuse `.env.local`.
2. `APP_ENV=production` enforces secret length, secure cookie, HTTPS base URL, non-default seed password, valid Fernet key, and fake-provider guard.
3. Provider credentials in the DB take precedence over environment values; a revoked DB row must not fall back to a stale env key.
4. `docker compose config` output can contain secrets. Redact before sharing; never commit it.
5. Environment files are `0600`, owned by the service account, and excluded from backups unless escrowed separately.

---

## 9. Migration, backup, monitoring, and runbook index

### 9.1 Migration

| Item | Detail |
|---|---|
| Tool | Alembic |
| Location | `apps/api/alembic/` |
| Apply | `alembic upgrade head` |
| Drift check | `alembic check` |
| Current Compose | `api` runs `alembic upgrade head` and seed before Uvicorn |
| Target H6 | One-shot `migrate` job as `feedesk_owner`; API/worker as `feedesk_app` — **not applied** |
| Rollback | Do not run `alembic downgrade` blindly; restore a verified backup with school approval |
| Evidence | Migration head and `alembic check` result recorded per release |

### 9.2 Backup and restore

| Item | Proposed target | Verified? |
|---|---|---|
| RPO | ≤24 hours (nightly) | No; school must sign |
| RTO | ≤4 hours (single server) | No; school must sign |
| Retention | 30 daily + 12 monthly | No; monthly manual |
| Encryption | age recipient; private key offline | Scripts require it; not drilled |
| Offsite | Required in production | Not implemented by script |
| Contents | PostgreSQL custom dump, uploads tar, JSON manifest with SHA-256 | DB drill only; uploads not restored |
| Restore helper | Scratch targets only (`feedesk_restore_*`) | Dry-run checked; no `--execute` via Docker |
| Drill evidence | 3 Nov 2026 and 4 Nov 2026 local DB restores | Database only |

**Do not** use `docker compose down -v`; it deletes the database and uploads volumes.

### 9.3 Monitoring

| Signal | Source | Proposed threshold | Status |
|---|---|---|---|
| Web uptime | Blackbox probe `/` | 3 failures / 3 min | Template |
| API readiness | Blackbox probe `/health/ready` | 3 failures / 3 min | Template |
| API 5xx | Caddy logs → Loki | >10 in 5 min; >2% / 10 min | Template; access log disabled |
| Queue depth | postgres_exporter | >25 / 10 min; >100 / 5 min | Template; exporter unvalidated |
| Worker liveness | oldest pending job age | >300 s / 5 min | Template |
| Expired leases | `send_jobs.lease_expires_at < now()` | any / 5 min | Template |
| Failed jobs | `send_jobs.status='failed'` (24h) | any increase | Template |
| Unknown outcomes | `messages.internal_status='unknown'` | any / 24h | Template |
| Stuck submitting | `submitting` >10 min | any | Template |
| Provider balance | Rasel read-only call | school low-water mark | **Not wired (G4)** |
| Disk | node_exporter | <15% warn, <10% critical | Template |
| DB reachable | `pg_up` | 2 min down | Template |
| DB connections | postgres_exporter | >80% for 10 min | Template |
| Backup freshness | textfile metric | >36 h | Template |
| TLS expiry | blackbox | <14 days | Template |

No alert has fired or been delivered. The balance rule is inert without an exporter.

### 9.4 Runbook index

| Runbook | Use when | Status |
|---|---|---|
| `docs/runbooks/deploy-rollback.md` | First deploy, release, failed release | Template; not exercised |
| `docs/runbooks/worker-recovery.md` | Queue stalled, worker crashed, duplicate workers | Template; no crash drill |
| `docs/runbooks/unknown-outcomes.md` | Message status `unknown`; provider reconciliation | Template; no reconciliation tooling |
| `docs/runbooks/provider-outage.md` | Rasel errors, timeouts, balance/sender problems | Template; no live call |
| `docs/runbooks/key-rotation.md` | Session, DB, provider, backup key rotation | Template; not exercised |
| `docs/runbooks/backup-restore.md` | Backup checks, restore drill, production restore | Partial; DB drill only |
| `docs/runbooks/first-run-checks.md` | Before handing app to school user | Template; not performed |
| `docs/runbooks/review.md` | Owner/gap/review record | Desk review only |

**Universal runbook rules:** no PII/secrets in tickets/logs; stop worker before restore/migration/key change; unknown is not failure; no blind resend; messaging stays fake/disabled/kill-switch on until G0/G4 and written go/no-go; record time, operator, commands, outcome.

---

## 10. Known limitations

### 10.1 Product and data

- No OCR execution; scanned PDFs are refused with `SCANNED_PDF`.
- No in-app manual row entry for a zero-row PDF.
- No real school statement acceptance; synthetic fixtures only.
- Arabic template copy is not school-approved.
- No resend workflow; unknown outcomes need engineering escalation.
- No provider reconciliation API/admin correction UI; the operations panel is read-only.
- No delivery-report webhook; polling/reconciliation contract unverified.
- Provider balance preflight exists for fake mode only; no live balance display pre-G0.
- Bulk row exclusion and manual guardian resolution are implemented and browser-verified with synthetic data; real-sample acceptance remains pending.
- No configurable approval permission per user; default admin-only.
- No OpenAPI-generated client; no frontend automated tests in CI.

### 10.2 Operations and security

- No production host, TLS, DNS, firewall, or image registry.
- No CI/CD beyond repository workflow; no production deployment automation.
- No external secret manager; most secrets are environment variables on the host, while provider credentials may be encrypted in the DB vault (see §10.4).
- The local development cluster uses trust authentication on localhost; never expose port `55432`.
- Provider credentials are encrypted in the DB, but no vault-key re-encryption procedure is documented or tested.
- H4 retention/purge open; data retained indefinitely.
- H6 DB-role separation open; runtime uses owner credential.
- No MFA; no emergency access procedure beyond break-glass placeholder.
- No PITR/HA; single server + nightly dumps.
- No resource limits/log shipping; JSON log rotation only.
- No alert delivery, on-call rota, or named owners.
- Runbooks are English-only; Arabic quick reference is pending.
- Frontend accessibility/visual polish remains partial beyond P1 fixes.
- Provider pacing is per worker process; multiple workers can exceed the intended rate.

### 10.3 Claims not made

- No production deployment.
- No container image build/deploy.
- No TLS certificate issuance/renewal.
- No alert fired/delivered.
- No uploads backup/restore.
- No encrypted/offsite backup drill.
- No live Rasel/SMS call.
- No provider reconciliation or delivery confirmation.
- No worker crash/lease reclaim drill on a production host; the fake-provider load/chaos matrix passed locally.
- No provider credential rotation exercised against a live provider; the vault rotation/revoke flow passed locally.
- No UAT, training delivery, launch, or school sign-off.
- No G0/G4/G5 pass.

### 10.4 Documentation inconsistencies to resolve at acceptance

These are source-document conflicts, not new claims. Do not resolve them by assuming the more optimistic version.

| Topic | Conflict | Safe position |
|---|---|---|
| Provider credential encryption/rotation UI | Historical M5/README text called it unimplemented; the later M4/M7 evidence records the vault, rotation/revoke UI, and worker integration as implemented and tested locally | Treat the later evidence as the intended build; verify the deployed release and vault key before claiming production readiness |
| Bulk row exclusion / manual guardian resolution | Historical README/M2 text called them unimplemented; the M2 API/tests and browser checks record them as implemented with synthetic data | Verify the deployed UI/API and real-sample acceptance before training on real data |
| Table count | M1 status records a historical count; current models include newer M4/M2 tables | Use the live migration/schema, not a historical count |
| Runbook DB role | Runbooks use `-U feedesk`; H6 targets `feedesk_app`/`feedesk_owner`/`feedesk_backup` | H6 is not applied; update commands only after the role change is verified |

Record the resolution and the checked release in the handover acceptance record.

---

## 11. Open gates and blockers

Every row below is **blocked for production use** until its evidence is attached and accepted. The “State” column describes the gate’s current state, not readiness.

| Gate/decision | State | Owner | What unlocks it |
|---|---|---|---|
| G0 — discovery/provider | **Open** | PO/Tech lead + school + provider | Real samples, taxonomy, approved sender, 3 Syrian test numbers, free-text plan, delivered test, provider evidence, school decisions |
| G1 — foundation/design | **Open/pending** | Tech lead + design | Formal G1 checklist and remaining design/CI acceptance evidence |
| G2 — import review | **Open/pending** | QA/PO/School | Real anonymized samples, golden files, formal M2 acceptance |
| G3 — campaign/approval | **Open/pending** | PO/School | School-approved Arabic copy and real-data campaign verification |
| G4 — messaging/pilot | **Open** | Tech lead + provider ops | Live test-send, delivery/reconciliation contract, controlled pilot, signed gate |
| G5 — launch | **Open** | All | OPS-01..OPS-10, UAT, training, go/no-go |
| OPS-01/03 security/privacy | **Open** | Security/TL | H4 retention, H6 DB roles |
| OPS-04 backup/restore | **Partial** | DevOps/DBA | Encrypted+offsite+uploads restore, script `--execute`, RPO/RTO sign-off |
| OPS-05 deployment | **Scaffolded** | DevOps | Host, DNS/TLS, firewall, images, deploy record |
| OPS-06 monitoring | **Template** | DevOps | Running stack, delivered alert, balance metric |
| OPS-07 runbooks | **Drafted + desk-reviewed** | TL/Ops | Exercise + named owners |
| OPS-08 UAT | **Not started** | QA/PO/School | UAT on approved data + sign-off |
| OPS-09 training | **Draft + internal rehearsal; delivery blocked** | PO/Design | Approved environment, delivered Arabic training, attendance/assessment record |
| OPS-10 launch | **Not started** | All | Checklist + go/no-go |
| OPS-11 hypercare | **Rehearsal only** | Team | Live first campaign + 2-week review |
| OPS-12 handover | **Draft; readiness review not accepted** | TL/PO | Signed acceptance §12 and required evidence |
| H4 retention S1–S10 | **Open** | School data owner | Signed policy + purge implementation + evidence |
| H6 DB roles | **Open** | DBA/backend | Role provisioning + denial tests + rollback rehearsal |
| Hosting/data residency | **Open** | School | Written decision |
| Support hours/SLA | **Open** | School + provider | Signed support model |
| Credential custody | **Open** | School + security | Signed custody ledger and handover ceremony |

---

## 12. Handover acceptance checklist

Handover is accepted only when every applicable box is checked and signed. Items marked **BLOCKED** cannot be checked from this pack; they require the named evidence.

### 12.1 Documentation and scope

- [ ] This pack read and understood by school admin and technical owner.
- [ ] `support-model.md` roles, hours, and escalation accepted or amended.
- [ ] `credential-handover.md` custody ledger completed with named custodians.
- [ ] `first-campaign-runbook.md` reviewed; no live step authorised yet.
- [ ] `post-implementation-review.md` accepted as the hypercare template.
- [ ] Known limitations (§10) acknowledged in writing.
- [ ] Open gates (§11) acknowledged; no gate marked passed.

### 12.2 Access and credentials

- [ ] Named school admin account exists; seed password changed; no shared login.
- [ ] Named technical owner account and host access exist; MFA gap recorded.
- [ ] Provider console access belongs to the school or a named custodian.
- [ ] Secret store/custody location agreed; no secret in this pack.
- [ ] Break-glass custodian and deputy named; rules read.
- [ ] Session/DB/provider/vault/backup/TLS/monitoring custody entries completed **without values**.
- [ ] Provider credential source verified on the deployed release (DB vault or approved env fallback); vault status/rotation path confirmed.
- [ ] **BLOCKED:** credential transfer ceremony completed over an approved channel.

### 12.3 Operations

- [ ] Approved host exists; OS patched; timezone/NTP/firewall set.
- [ ] DNS/TLS issued and renewal monitored.
- [ ] Compose config validated on the host; images built and tagged.
- [ ] `api`, `worker`, `web`, `proxy`, `db` healthy; worker reports fake/disabled/kill-switch on.
- [ ] Backup runs encrypted, offsite, and a scratch restore (DB + uploads) passes.
- [ ] Alert stack runs; a test alert is delivered and resolved to the on-call mailbox.
- [ ] Runbooks exercised on staging/host; named owners and deputies recorded.
- [ ] H6 role separation applied and denial tests passed, or residual risk accepted in writing.
- [ ] **BLOCKED:** production deployment record and smoke checks.

### 12.4 School readiness

- [ ] School data owner and deputy named.
- [ ] Retention/deletion policy S1–S10 signed (H4).
- [ ] Currency, opt-out, approval, hosting, and Arabic copy approved.
- [ ] UAT completed on approved/anonymised data, with evidence and defect triage attached.
- [ ] Arabic training delivered; attendance recorded.
- [ ] Support hours, contacts, and SLA placeholders signed.
- [ ] First controlled campaign plan approved; stop authority named.
- [ ] **BLOCKED:** UAT/training/launch sign-off.

### 12.5 Acceptance decision

Because the production-dependent items in §3.2 are blocked, the only honest current decision is **Not accepted** or **Accepted with conditions limited to documentation/planning**. Do not select “Accepted” as proof of operational readiness; it would require the host, TLS, backup/restore, alerts, UAT, training, and gate evidence to exist.

| Decision | Meaning | Signature | Date |
|---|---|---|---|
| Accepted | Ownership transferred with listed exceptions |  |  |
| Accepted with conditions | Ownership transferred; conditions tracked below |  |  |
| Not accepted | Handover incomplete; reasons recorded |  |  |

**Conditions / exceptions:**

```text
1.
2.
3.
```

**Signatories:**

| Role | Name | Signature | Date |
|---|---|---|---|
| School director / authorised representative |  |  |  |
| School data owner |  |  |  |
| Technical owner |  |  |  |
| Provider/operations lead |  |  |  |
| Security reviewer |  |  |  |

---

## 13. Evidence register

| Evidence | Location | Date | Scope | Status |
|---|---|---|---|---|
| M1 status | `docs/m1/status.md` | 3 Nov 2026 | Foundation/local | Local only |
| M2 verification | `docs/m2/verification.md` | Nov 2026 | Import/synthetic | Local only |
| M3 verification | `docs/m3/verification.md` | Nov 2026 | Campaign/approval | Local only |
| M4 verification | `docs/m4/verification.md` | 4 Nov 2026 | Messaging fake | Local only |
| Load/chaos | `docs/m4/load-chaos.md` | 4 Nov 2026 | Fake provider | Local only |
| Security review | `docs/m5/security-review.md` | 4 Nov 2026 | OPS-01/02/03 | H4/H6 open |
| Retention plan | `docs/m5/privacy-retention-plan.md` | 4 Nov 2026 | H4 decision package | Not signed |
| DB roles | `docs/m5/db-role-separation.md` | 4 Nov 2026 | H6 provisioning | Not applied |
| Deployment readiness | `docs/m5/deployment-readiness.md` | 4 Nov 2026 | OPS-04..07 | Partial/template |
| Runbook review | `docs/runbooks/review.md` | 4 Nov 2026 | Desk review | Open |
| Local DB restore | `docs/runbooks/backup-restore.md` | 3–4 Nov 2026 | DB only | Partial |
| G0 gate | `docs/m0/gate-g0.md` | 3 Nov 2026 | Provider/discovery | Not passed |
| Decision log | `docs/m0/decision-log.md` | Nov 2026 | School decisions | Pending |
| Task register | `FeeDesk-Task-Register.csv` | Living | M0–M6 | OPS-11/12 open |

---

## 14. Unresolved decisions

These require a named owner and a date. They are not documentation gaps alone; they block production.

| # | Decision | Owner | Needed for | Status |
|---|---|---|---|---|
| 1 | Hosting model, location, data residency | School | OPS-05 | Open |
| 2 | Backup encryption, offsite destination, key custodian | School + security | OPS-04 | Open |
| 3 | RPO/RTO (proposed ≤24 h / ≤4 h) | School | OPS-04 | Open |
| 4 | Monitoring stack, on-call owner, alert mailbox | Technical owner | OPS-06 | Open |
| 5 | Provider plan, sender, Syrian coverage, balance low-water mark | Provider/ops | G0/G4 | Open |
| 6 | Messaging enablement authority and kill-switch owner | School + technical | G4 | Open |
| 7 | Retention/deletion policy S1–S10 | School data owner | H4/OPS-03 | Open |
| 8 | DB role separation window and rollback operator | Technical/DBA | H6/OPS-01 | Open |
| 9 | Admin accounts, password reset, MFA gap acceptance | School + security | Handover | Open |
| 10 | Rollback/data-loss authority | School | OPS-04/05 | Open |
| 11 | TLS/DNS domain and renewal monitoring | Technical owner | OPS-05 | Open |
| 12 | Support hours, SLA, escalation contacts | School + provider | Support model | Open |
| 13 | Arabic template and opt-out wording | School | G0/M3 | Open |
| 14 | UAT participants, data set, acceptance criteria | School + QA | OPS-08 | Open |
| 15 | First pilot cohort and stop authority | School | OPS-11 | Open |
| 16 | Provider vault-key rotation/re-encryption procedure | Security + engineering | Provider credential continuity | Open |
| 17 | 5xx monitoring source while Caddy access logging is disabled | Technical owner | OPS-06 | Open |
| 18 | Runbook owners/deputies and Arabic quick reference | Technical + school | OPS-07 / RBR-01 / RBR-10 | Open |

---

## 15. Related documents

- `docs/m5/deployment-readiness.md`
- `docs/m5/security-review.md`
- `docs/m5/privacy-retention-plan.md`
- `docs/m5/db-role-separation.md`
- `docs/runbooks/README.md` and all runbooks
- `docs/m4/load-chaos.md`
- `docs/m2/ocr-decision.md`
- `docs/runbooks/review.md`
- `docs/m6/support-model.md`
- `docs/m6/credential-handover.md`
- `docs/m6/post-implementation-review.md`
- `docs/m6/first-campaign-runbook.md`

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 4 Nov 2026 | Initial M6 handover draft; local-vs-blocked separation; no production claims | Documentation pass |
