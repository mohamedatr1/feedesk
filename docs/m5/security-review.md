# M5 — Pre-G4 Security and Privacy Review

**Date:** 4 November 2026  
**Mode:** read-only audit; no provider calls, no `.env.local` values, no production deployment.  
**Audit result:** 0 Critical, 6 High, 10 Medium, 6 Low. **Current:** OPS-02 closed; OPS-01/03 open.

## High findings

| ID | Finding | Required closure |
|---|---|---|
| H1 | Crash/lease reclaim can resend a message already submitted (`submitting` is reclaimed, result application is not fenced) | Treat reclaimed `submitting` as `unknown`; never auto-resend; fence result updates by worker/attempt; crash/lease/concurrency tests |
| H2 | Phones/guardian names leak into Caddy/Uvicorn access logs via `q` query strings | Disable Uvicorn access log; redact `q`/`Referer` in Caddy; test a phone search produces no phone in logs |
| H3 | Full phone numbers exposed in message/campaign/excluded list views | Server-side masked list field; reveal full only on explicit detail/preview; tests |
| H4 | No retention purge, deletion, or anonymization; source files/PII retained indefinitely; duplicate override writes a second copy | School retention policy; `retention_until`; purge job; cancel/delete cleanup; reuse source file on duplicate override; deletion runbook |
| H5 | Production guard is fail-open if `APP_ENV` is omitted; default seed password/cookies can be used | Fail-closed container/config defaults; block default seed outside development; validate secure cookie/HTTPS |
| H6 | Runtime DB role can disable audit triggers because it owns the tables | Separate migration/runtime roles; no DDL/audit ownership for runtime; trigger-tamper test |

## Medium findings

M1 campaign detail exposes all full phones/message bodies without `campaigns.preview`; M2 raw staged data returned wholesale; M3 SQL parameter logs can contain PII; M4 XLSX decompression bomb limits; M5 route-guard inconsistencies (cancel/preview/file) and missing matrix tests; M6 default SMS includes student names; M7 provider config can use fake-delivered in production/HTTP base/rate 0; M8 audit stores phone PII; M9 backup encryption optional; M10 cancelling approved campaign overwrites terminal message outcomes.

## Low findings

Logout cookie flags; login CSRF/lockout enumeration; dependency pinning/CVE gate/non-root containers; CSP and `Cache-Control: no-store`; unused `SESSION_SECRET`/unenforced send limits; rate limits beyond login and public health detail.

## What is already good

Argon2id, server-side sessions, CSRF on mutating routes, RBAC on every protected route, append-only audit triggers, private upload storage with magic-byte checks, generic 500 responses, request IDs, app-level log redaction, provider payload redaction, fake/disabled/kill-switch defaults, idempotency keys, unknown outcomes not auto-resent, no dangerous frontend HTML/eval, HSTS at Caddy, 0 npm audit vulnerabilities, no broken Python requirements.

## Route matrix closure

All protected routes have a backend permission dependency. The audit gaps were closed:
- `POST /campaigns/{id}/cancel` now requires `campaigns.edit` and still re-checks approval state.
- `GET /campaigns/{id}` returns masked phones, empty rendered messages, and no student names; full data is only on `GET /campaigns/{id}/preview` (`campaigns.preview`).
- `GET /files/{id}` requires the dedicated `files.download` permission.
- Login remains public by design (no CSRF/Origin check); health endpoints remain public.
- `tests/test_permission_matrix.py` covers all 52 routes, permission/CSRF drift, identities, and object isolation.

## Closure priority

**P0:** H1, H2, H3, H4, H5, H6.  
**P1:** M1–M10.  
**P2:** L1–L6.

No code was changed by this audit. This document records findings; fixes are tracked separately and must not be marked closed until evidence exists.

## Fix status (4 November 2026)

| Finding | Status | Evidence |
|---|---|---|
| H1 duplicate send after crash/reclaim | **Fixed** | Claim token + worker/attempt fencing; stale results discarded/audited; reclaimed `submitting` → `unknown`/`RECONCILIATION_REQUIRED`; 425 tests |
| H2 query strings in access logs | **Fixed in scaffolding** | Caddy access log disabled; Uvicorn production command uses `--no-access-log`; app logger records path only |
| H5 fail-open production defaults | **Fixed** | Production Dockerfile default `APP_ENV=production`; secure `__Host-`/HTTPS/cookie/secret/seed validation; default seed refused outside development |
| M3 SQL parameter logs | **Fixed** | SQLAlchemy engine `hide_parameters=True`; regression test |
| M10 cancellation overwrites terminal outcomes | **Fixed** | Only non-terminal messages/jobs cancelled; retained terminal outcomes audited; mixed-status test |
| L1 logout cookie flags | **Fixed** | Matching `HttpOnly`/`Secure`/`SameSite`/path deletion; test |
| L4 cache/no-store | **Fixed** | `/api/v1` and authenticated file responses get `no-store`/`no-cache`; tests |
| M5 route-guard inconsistencies | **Fixed** | Cancel requires `campaigns.edit`; preview requires `campaigns.preview`; file download requires `files.download`; matrix drift tests cover all routes |
| M9 backup encryption optional | **Fixed** | `feedesk_backup.py --execute` requires `--age-recipient` unless explicit local `--allow-unencrypted`; local dump removed |
| H3 phone masking in lists | **Fixed** | Message summaries return `destination_phone_masked` only; campaign detail masks phones, blanks rendered SMS bodies and student names; preview requires `campaigns.preview`; frontend tables use masked values and reveal only in the explicit preview dialog; 425 tests + browser check |
| M1 campaign detail bulk PII | **Fixed** | Detail returns masked phones, empty messages, and no student names; `/preview` requires `campaigns.preview`; approved/cancelled snapshots follow the same split |
| M4 XLSX decompression limits | **Fixed** | Upload and stored-file parsing inspect zip metadata (members, per-member size, total uncompressed, ratio with a 1 MB floor); 422 `XLSX_ARCHIVE_LIMIT`; no content extraction; tests |
| M7 provider config guard | **Fixed** | Rate/attempts/lease, HTTPS Rasel base, E.164 allowlist, production fake guard, encrypted credential vault + rotation/revoke UI, DB-over-env worker resolution with revocation releasing pending jobs, test-send allowlist/throttle; secrets never returned or logged |
| M2 raw staged data | **Fixed** | `raw_data` removed from `StagedRowOut`; server retains it; `available_headers` returns names only |
| M6 default template student names | **Fixed for new defaults** | `student_list` removed from default body; existing active templates require an admin-created version |
| M8 audit PII | **Fixed** | `record_audit` now recursively masks phone-like keys in nested `before`/`after` payloads; masking is idempotent; existing append-only rows are unchanged |
| H4 retention/deletion/anonymization | **Open** | Plan: `docs/m5/privacy-retention-plan.md`; school policy required |
| H6 runtime DB role separation | **Open** | Plan: `docs/m5/db-role-separation.md`; no production role change |
| OPS-02 full matrix tests | **Fixed** | `tests/test_permission_matrix.py`: 52 routes, permission/CSRF introspection drift, anonymous/staff/admin/auditor identities, CSRF mutations, object isolation; 425 tests pass |

**Verdict:** OPS-02 is closed by the passing permission matrix. H3, M1, M4, M7, and M8 are closed (masked detail, permission-gated preview, dedicated file download, encrypted credential vault with DB-over-env worker resolution, provider config guards, XLSX archive limits, recursive audit redaction; 425 tests + browser checks). OPS-01 and OPS-03 remain **open** only for H4 retention and H6 DB-role separation, which require school/production decisions; G5 is not passed.
