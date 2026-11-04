# FeeDesk M6 — Internal Handover Readiness Review

**Document ID:** M6-HRR-01  
**Version:** 0.2 (internal review)  
**Date:** 4 November 2026  
**Reviewer:** Documentation and codemap specialist (internal, read-only)  
**Status:** **Internal readiness review. Not an acceptance record, gate record, UAT result, training record, or launch authorisation.**  
**Decision:** **NOT ACCEPTED for operational handover.**  
**Scope:** `docs/m6/*`, `docs/m5/deployment-readiness.md`, `docs/m5/security-review.md`, `docs/runbooks/review.md`, `docs/m4/verification.md`, `docs/m4/load-chaos.md`, and `FeeDesk-Task-Register.csv`.

> **Status statement — read this first**
>
> The M6 package is coherent, candid, and unusually well cross-referenced. It is also **not handover-ready**. Every production-dependent claim remains unverified, and several ownership and custody artifacts are still blank. G0, G4, and G5 are not passed. H4 and H6 remain open. OPS-09, OPS-11, and OPS-12 are not complete. No UAT, training delivery, production deployment, verified live SMS, first controlled campaign, hypercare period, or handover acceptance has occurred.
>
> **Recommended disposition: NOT ACCEPTED for operational handover.** A documentation-only conditional acceptance is possible in principle, but it would record conditions, not readiness; no such acceptance has been signed. This review signs nothing and closes nothing.
>
> **Source-status update (4 November 2026):** M2 README records bulk exclusion and guardian resolution as implemented, M4 README records the encrypted credential vault, and M5 deployment-readiness now records encrypted provider credentials plus the rotation/revoke UI. The runbook `-U feedesk` command remains stale until H6 is applied. HR-G23 is therefore closed for documentation conflicts and remains open only for the H6 runbook update.
>
> **Rehearsal update (4 November 2026):** A fake-provider pilot rehearsal ([`pilot-rehearsal.md`](pilot-rehearsal.md)) and an internal browser training rehearsal ([`training-rehearsal.md`](training-rehearsal.md)) add local evidence. They reduce HR-G21’s validation gap but do not close OPS-09/11/12 or any gate; school delivery, attendance, live pilot authorization, and signed acceptance remain required.

---

## 1. Bottom line

### 1.1 What is genuinely strong

- The six core M6 documents form a complete set: handover pack, support model, credential custody, first-campaign runbook, post-implementation review, and Arabic training guide. The M6 index states the same constraints consistently: [`docs/m6/README.md`](README.md).
- The package separates local evidence from production claims instead of blurring them: [`handover-pack.md`](handover-pack.md) §3, §10.3, §11.
- Safe messaging defaults are stated consistently in the handover pack, training guide, and deployment evidence: `MESSAGING_PROVIDER=fake`, `MESSAGING_ENABLED=false`, `MESSAGING_KILL_SWITCH=true` ([`handover-pack.md`](handover-pack.md) §2; [`training-guide-ar.md`](training-guide-ar.md) §1.2).
- Local evidence is substantive: 425 backend tests, a 52-route permission matrix, a local PostgreSQL restore drill, fake-provider load/chaos, and a local credential-vault rotation/revoke flow ([`verification.md`](../m4/verification.md); [`load-chaos.md`](../m4/load-chaos.md); [`security-review.md`](../m5/security-review.md)).
- Post-draft rehearsals add local evidence without changing gate status: a fake-provider pilot rehearsal with 2/2 synthetic messages and a zero-send kill-switch check, plus an internal browser training rehearsal ([`pilot-rehearsal.md`](pilot-rehearsal.md); [`training-rehearsal.md`](training-rehearsal.md)).
- No secret values were observed in the M6 documents during manual review. This is not a substitute for a secret scan; it is a positive documentation-hygiene observation.

### 1.2 What blocks acceptance

| # | Blocking reality | Severity | Gate / record |
|---|---|---|---|
| 1 | No production deployment or launch record: host, DNS, TLS, image build, deploy record, smoke test, or go/no-go | **Critical** | OPS-05 / OPS-10 / G5 |
| 2 | No encrypted/offsite backup, uploads restore, decrypt drill, or signed RPO/RTO | **Critical** | OPS-04 / G5 |
| 3 | No named operational owners, contacts, custodians, deputies, incident commander, or stop authority | **Critical** | OPS-07 / OPS-11 / OPS-12 |
| 4 | H4 retention/deletion policy unsigned; no purge or anonymisation implementation | **Critical** | H4 / OPS-03 / G5 |
| 5 | G0 and G4 not passed; no verified live SMS delivery, provider test, pilot authorisation, or reconciliation evidence | **Critical** | G0 / G4 |
| 6 | No UAT and no training delivery; no approved training environment is recorded | **High** | OPS-08 / OPS-09 / G5 |
| 7 | Credential custody ledger, break-glass escrow, and transfer ceremony not executed | **High** | OPS-12 |
| 8 | Vault-key re-encryption, reconciliation tooling, release pin, 5xx alert source, and provider balance metric are unresolved | **High** | G4 / OPS-06 / OPS-11 / OPS-12 |
| 9 | H6 DB role separation not applied; runtime uses the owner credential; audit tamper path remains | **High** | H6 / OPS-01 / G5 |

### 1.3 The central distinction

**The M6 package is ready to support planning, tabletop rehearsal, and condition-setting. It is not ready to transfer operational ownership.** The documents describe what should happen; they do not prove that it has happened. Passing local tests does not prove a Linux host starts, Caddy obtains a certificate, alerts arrive without PII, backups decrypt, or a Syrian SMS is delivered.

---

## 2. Scope, method, and status definitions

### 2.1 Documents reviewed

| Document | Date / version | Stated status | Review treatment |
|---|---|---|---|
| [`docs/m6/README.md`](README.md) | 4 Nov 2026 | Pre-launch drafts | Package index and constraints |
| [`handover-pack.md`](handover-pack.md) | 4 Nov 2026, v0.1 | Draft; not accepted | Primary handover artifact |
| [`support-model.md`](support-model.md) | 4 Nov 2026, v0.1 | Proposed; not signed | Support ownership and SLA |
| [`credential-handover.md`](credential-handover.md) | 4 Nov 2026, v0.1 | Draft; no credential transferred | Custody and rotation |
| [`first-campaign-runbook.md`](first-campaign-runbook.md) | 4 Nov 2026, v0.1 | Template; live steps blocked | Pilot procedure |
| [`post-implementation-review.md`](post-implementation-review.md) | 4 Nov 2026, v0.1 | Template only | Hypercare review |
| [`training-guide-ar.md`](training-guide-ar.md) | 4 Nov 2026, draft | Not delivered | Arabic training material |
| [`pilot-rehearsal.md`](pilot-rehearsal.md) | 4 Nov 2026, v0.1 | Fake-provider rehearsal only | Local campaign-path evidence |
| [`training-rehearsal.md`](training-rehearsal.md) | 4 Nov 2026 | Internal rehearsal only | Local training-browser evidence |
| [`deployment-readiness.md`](../m5/deployment-readiness.md) | 4 Nov 2026 | Not production-ready | OPS status and deployment evidence |
| [`security-review.md`](../m5/security-review.md) | 4 Nov 2026 | Records OPS-02 as closed; OPS-01/03 open | Security findings and fixes |
| [`review.md`](../runbooks/review.md) | 4 Nov 2026 | Open; OPS-07 open | Runbook desk review |
| [`verification.md`](../m4/verification.md) | 4 Nov 2026 | Local fake-provider verification | Local messaging evidence |
| [`load-chaos.md`](../m4/load-chaos.md) | 4 Nov 2026 | Fake-provider only | Local reliability evidence |
| [`FeeDesk-Task-Register.csv`](../../FeeDesk-Task-Register.csv) | Living | OPS-09/11/12 unchecked | Task and gate status |

### 2.2 Status definitions used in this review

| Status | Meaning |
|---|---|
| **Ready (local evidence)** | The artifact exists and is supported by a local test, drill, desk review, or verified repository path. It is **not** production evidence. |
| **Rehearsal only** | The procedure or template is drafted and suitable for desk/tabletop/fake-provider rehearsal; it has not been exercised in a production-like environment. |
| **Blocked (external)** | The item requires a school, provider, host, legal, or production action or evidence that cannot be produced from the repository. |
| **Gap** | A required artifact, owner, decision, fixture, or consistency fix is missing or contradictory. Work is needed even before external evidence can close it. |

No item marked **Ready (local evidence)** should be read as production-ready. No item marked **Rehearsal only** should be read as exercised.

### 2.3 Method and limitations

This was a read-only documentation review. The reviewer:

- read every document listed in §2.1;
- verified that the principal repository paths cited by the handover pack exist;
- did not re-run tests, Docker, systemd, Caddy, PostgreSQL commands, provider calls, or browser checks;
- did not read `.env.local`, provider credentials, or any secret value;
- did not perform a secret scan, vulnerability scan, or code review;
- treated recorded local results as evidence, not as independently reproduced results;
- reviewed the pilot and training rehearsal records as documents; this reviewer did not observe or re-run those sessions.

Verified paths include `apps/api/app/main.py`, `apps/api/app/worker.py`, `apps/api/app/seed.py`, `apps/api/app/routers/`, `apps/web/app/layout.tsx`, `infra/compose/docker-compose.prod.yml`, `infra/compose/Caddyfile`, `infra/compose/.env.production.example`, `scripts/feedesk_backup.py`, `scripts/feedesk_restore.py`, `apps/api/tests/test_permission_matrix.py`, and `apps/api/tests/test_messaging_load.py`.

The review is dated 4 November 2026, the same date as the M6 drafts. Freshness is good; release identity is not (see HR-G15).

### 2.4 Explicit non-claims

The following are explicit non-claims. **None of these has occurred**, and this review must not be cited as evidence of any of them:

- launch, go-live, or production readiness;
- UAT completion or acceptance;
- training delivery or attendance;
- handover acceptance or ownership transfer;
- production deployment, container image build, DNS, TLS, or firewall verification;
- live SMS (no delivered or verified live SMS), successful provider test-send, delivery, or reconciliation;
- G0, G4, G5, or G1–G3 pass;
- OPS-09, OPS-11, or OPS-12 completion;
- MFA, PITR, high availability, or 24/7 support;
- production credential transfer, production rotation, or break-glass use.

---

## 3. Readiness scorecard

| Area | Document state | Strongest evidence available now | Evidence still missing | Verdict |
|---|---|---|---|---|
| Handover pack | Complete draft | Local test/security records; explicit blocked register | Release pin, production evidence, signed acceptance | **Not acceptable yet** |
| Support model | Proposed | RACI, tiers, templates, evidence standard | Named people, SLA values, contacts, evidence store | **Not acceptable yet** |
| Credential custody | Inventory and procedures | Local vault rotation/revoke; no-secret discipline | Custodians, ledger, break-glass escrow, transfer | **Not acceptable yet** |
| First-campaign runbook | Template | M2/M3 workflows; M4 fake load/chaos; fake-provider pilot rehearsal | G0, G4 authorisation, live provider evidence | **Blocked** |
| Post-implementation review | Template | Metric definitions and guardrails | Actual campaign and hypercare data | **Blocked** |
| Training guide | Arabic draft | Synthetic exercises; internal browser rehearsal | School delivery, attendance, ambiguity fixture | **Blocked** |

**Overall:** the package is documentation-complete enough to guide a conditioned plan; it is not evidence-complete enough to accept operational ownership.

---

## 4. Handover pack checklist

Source: [`handover-pack.md`](handover-pack.md).

| # | Check | Status | Evidence | Condition / limitation |
|---|---|---|---|---|
| HP-01 | Identity, version, owner, source-of-truth precedence | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) header; §1.1 | Owner is “proposed; not yet accepted”; version 0.1 |
| HP-02 | Scope, out-of-scope, and related documents | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §1.2–1.3, §15 | Clear boundaries; no school sign-off |
| HP-03 | Arabic executive summary | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §1.4 | Summary only; full pack is English |
| HP-04 | System overview and safe defaults | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §2; [`ADR 008`](../adr/0008-deployment-backup-secrets.md) | Defaults are documented, not enforced on a host |
| HP-05 | Verified-local vs blocked separation | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §3.1–3.3 | Strong section; depends on cited local evidence being current |
| HP-06 | Architecture and topology description | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §4.1–4.4 | No service in the diagram has run in production |
| HP-07 | Repository layout, entry points, API surface | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §5.1–5.2; verified paths in §2.3 | No docs-vs-code drift check is recorded |
| HP-08 | Data model overview | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §6 | Historical table-count conflict disclosed in §10.4; use live schema |
| HP-09 | Roles, permissions, account rules | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §7; [`security-review.md`](../m5/security-review.md) | MFA absent; approval permission not configurable (FND-08 remainder) |
| HP-10 | Environment variable names and no-secret rule | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §8; `.env.example`; `infra/compose/.env.production.example` | Names and safe states only; production validation unproven |
| HP-11 | Migration and runbook index | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §9.1, §9.4; [`review.md`](../runbooks/review.md) | Runbook index is current; runbooks themselves are unexercised |
| HP-12 | Backup/restore index | **Rehearsal only** | [`handover-pack.md`](handover-pack.md) §9.2; [`backup-restore.md`](../runbooks/backup-restore.md) | Local database-only drill; no uploads, encryption, offsite, or `--execute` |
| HP-13 | Monitoring index | **Blocked (external)** | [`handover-pack.md`](handover-pack.md) §9.3; [`deployment-readiness.md`](../m5/deployment-readiness.md) | Templates only; no stack, no delivered alert, no balance metric |
| HP-14 | Known limitations | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §10.1–10.2 | Honest and specific; not a substitute for production testing |
| HP-15 | Documentation-conflict register | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §10.4 | Conflicts are disclosed but not closed; see HR-G23 |
| HP-16 | Open gates and blockers register | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §11 | Register is accurate for G0/G4/G5 and the OPS-09/11/12 draft states, but omits G1–G3; see HR-G22 |
| HP-17 | Acceptance checklist | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §12 | Template only; every box unchecked; signatories blank |
| HP-18 | Evidence register | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §13 | No release manifest, commit SHA, image digest, or deployed-release identifier |
| HP-19 | Unresolved decisions | **Ready (local evidence)** | [`handover-pack.md`](handover-pack.md) §14 | All 18 items open; several have no named owner or date |
| HP-20 | Release pin / version verification | **Gap** | [`handover-pack.md`](handover-pack.md) §2.2 | The pack says pins must be verified against the release, but no release is pinned. See HR-G15 |
| HP-21 | Gate-register completeness (G1–G3) | **Gap** | [`FeeDesk-Task-Register.csv`](../../FeeDesk-Task-Register.csv); [`m2 README`](../m2/README.md); [`m3 README`](../m3/README.md) | G1/G2/G3 are unchecked or pending, but the handover pack names only G0/G4/G5. See HR-G22 |
| HP-22 | Technical-owner onboarding and competency record | **Gap** | [`handover-pack.md`](handover-pack.md) §12.1–12.3 | No walkthrough, shadowing, or competency sign-off is recorded. See HR-G26 |

---

## 5. Support model checklist

Source: [`support-model.md`](support-model.md).

| # | Check | Status | Evidence | Condition / limitation |
|---|---|---|---|---|
| SM-01 | Purpose, scope, and support boundaries | **Ready (local evidence)** | [`support-model.md`](support-model.md) §1–2 | Clear in/out-of-scope; no school acceptance |
| SM-02 | Role definitions and “must not” rules | **Ready (local evidence)** | [`support-model.md`](support-model.md) §4 | Roles are defined, not staffed |
| SM-03 | RACI matrix | **Ready (local evidence)** | [`support-model.md`](support-model.md) §5 | Proposed; no accountable person has accepted a row |
| SM-04 | Named role holders, deputies, and contact register | **Gap** | [`support-model.md`](support-model.md) §4, §12.1 | Every name, phone, email, and hours cell is blank. See HR-G01 |
| SM-05 | Support hours and campaign-window coverage | **Rehearsal only** | [`support-model.md`](support-model.md) §6.1 | Proposed hours; no funded rota or signed schedule |
| SM-06 | Tiers and escalation path | **Rehearsal only** | [`support-model.md`](support-model.md) §6.2–6.3 | Not exercised; no published escalation contacts |
| SM-07 | Severity and response targets | **Rehearsal only** | [`support-model.md`](support-model.md) §7 | Proposed S1–S4 targets; no measured response |
| SM-08 | Incident categories and first actions | **Rehearsal only** | [`support-model.md`](support-model.md) §8 | Good procedures; no tabletop record. See HR-G20 |
| SM-09 | Evidence-collection standard | **Ready (local evidence)** | [`support-model.md`](support-model.md) §9.1–9.2 | Strong “no PII / no secrets” standard |
| SM-10 | Approved evidence store | **Gap** | [`support-model.md`](support-model.md) §9.3 | Store unnamed; document itself says evidence handling is blocked until named. See HR-G10 |
| SM-11 | Communication templates | **Ready (local evidence)** | [`support-model.md`](support-model.md) §10 | Bilingual and PII-safe; school language/wording acceptance pending |
| SM-12 | SLA placeholders | **Blocked (external)** | [`support-model.md`](support-model.md) §11 | SLA-01..15 school-approved values are blank |
| SM-13 | Support sign-off | **Blocked (external)** | [`support-model.md`](support-model.md) §12.2 | **NOT SIGNED**; no residual-risk acceptance |
| SM-14 | Review cadence | **Rehearsal only** | [`support-model.md`](support-model.md) §13 | Proposed cadence; not operating |
| SM-15 | 24/7 / on-call commitment | **Blocked (external)** | [`support-model.md`](support-model.md) §6.1 | Best effort only; 24/7 requires separate funding and signature |
| SM-16 | MFA residual-risk acceptance | **Gap** | [`support-model.md`](support-model.md) §12.2; [`handover-pack.md`](handover-pack.md) §7.3 | MFA is not implemented and no written acceptance exists. See HR-G24 |
| SM-17 | Tabletop exercise record | **Gap** | [`support-model.md`](support-model.md) §8 | No recorded tabletop for unknown outcome, outage, restore, key compromise, or privacy. See HR-G20 |

---

## 6. Credential custody checklist

Source: [`credential-handover.md`](credential-handover.md).

| # | Check | Status | Evidence | Condition / limitation |
|---|---|---|---|---|
| CC-01 | No-secret rule and document content | **Ready (local evidence)** | [`credential-handover.md`](credential-handover.md) §2, §9 | Manual read found no values; not a secret scan |
| CC-02 | Credential inventory CR-01..CR-17 | **Ready (local evidence)** | [`credential-handover.md`](credential-handover.md) §3 | Inventory is detailed but incomplete for hosting/offsite; see HR-G16 |
| CC-03 | Storage classes and approved locations | **Rehearsal only** | [`credential-handover.md`](credential-handover.md) §3 | No secret manager deployed; locations are targets, not verified |
| CC-04 | Custodians, deputies, custody ledger, minimum set | **Gap** | [`credential-handover.md`](credential-handover.md) §3.1, §4 | Inventory holds role titles, not named people; the ledger and minimum-set checklists are blank. See HR-G11 |
| CC-05 | Handover preconditions and transfer steps | **Gap** | [`credential-handover.md`](credential-handover.md) §5.1–5.2 | No approved transfer channel or identity-verification method selected. See HR-G11 |
| CC-06 | Dual control | **Rehearsal only** | [`credential-handover.md`](credential-handover.md) §5.3 | Rule stated; no dual-control rehearsal recorded |
| CC-07 | Session-secret rotation | **Rehearsal only** | [`credential-handover.md`](credential-handover.md) §6.1 | No production rotation; no session-invalidation drill |
| CC-08 | Database credential rotation and H6 | **Blocked (external)** | [`credential-handover.md`](credential-handover.md) §6.2; [`db-role-separation.md`](../m5/db-role-separation.md) | Runtime uses owner credential; H6 not applied |
| CC-09 | Provider API key and vault rotation | **Rehearsal only** | [`credential-handover.md`](credential-handover.md) §6.3; [`verification.md`](../m4/verification.md) | Vault rotate/revoke verified locally; no live provider call |
| CC-10 | Vault-key re-encryption | **Gap** | [`credential-handover.md`](credential-handover.md) §6.4 | No re-encryption tool or tested procedure; document marks rotation blocked. See HR-G12 |
| CC-11 | Backup encryption keys and decrypt path | **Blocked (external)** | [`credential-handover.md`](credential-handover.md) §6.5; [`backup-restore.md`](../runbooks/backup-restore.md) | No encrypted/offsite backup, no offline-key decrypt drill |
| CC-12 | TLS/domain and registrar custody | **Blocked (external)** | [`credential-handover.md`](credential-handover.md) §6.6 | No certificate, domain, registrar MFA, or renewal test |
| CC-13 | Monitoring accounts and alert mailbox | **Blocked (external)** | [`credential-handover.md`](credential-handover.md) §6.7 | No monitoring account, alert mailbox, or delivery test |
| CC-14 | Seed administrator one-time use | **Ready (local evidence)** | [`credential-handover.md`](credential-handover.md) §6.8; [`m1 status`](../m1/status.md) | App behavior locally verified; production first-login execution unverified |
| CC-15 | SSH/host access | **Blocked (external)** | [`credential-handover.md`](credential-handover.md) §6.9 | No host, no `authorized_keys`, no root-disable verification |
| CC-16 | Break-glass rules and sealed escrow | **Gap** | [`credential-handover.md`](credential-handover.md) §7 | No sealed custody record, offline location, or named person/deputy. See HR-G11 |
| CC-17 | Compromise playbook | **Rehearsal only** | [`credential-handover.md`](credential-handover.md) §8 | Not exercised; no incident drill |
| CC-18 | Rotation schedule and sign-off | **Blocked (external)** | [`credential-handover.md`](credential-handover.md) §11–12 | Dates blank; **NOT SIGNED** |

---

## 7. First-campaign runbook checklist

Source: [`first-campaign-runbook.md`](first-campaign-runbook.md).

| # | Check | Status | Evidence | Condition / limitation |
|---|---|---|---|---|
| FC-01 | Purpose, scope, and authority roles | **Ready (local evidence)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §1–2 | One incident commander must be named; no name recorded |
| FC-02 | Gate evidence (G0, G4, G5) | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.1; [`gate-g0.md`](../m0/gate-g0.md) | G0 and G4 open; G5 not required for pilot but not passed |
| FC-03 | School approvals and policy pre-flight | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.2 | Cohort, copy, retention, support window, stop authority not signed |
| FC-04 | Provider pre-flight | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.3 | No approved sender, free-text plan, test numbers, delivered test, or balance |
| FC-05 | Allowlist and test numbers | **Ready (local evidence)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.4; [`verification.md`](../m4/verification.md) | Fake test-send/allowlist behavior verified locally; production list and empty-list decision unresolved. See HR-G17 |
| FC-06 | Template and Arabic copy | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.5; [`training-guide-ar.md`](training-guide-ar.md) §13.4 | Seeded copy is not school-approved |
| FC-07 | Data and campaign pre-flight | **Ready (local evidence)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.6; [`m2 verification`](../m2/verification.md); [`m3 verification`](../m3/verification.md) | Synthetic data only; real-sample acceptance is G0 |
| FC-08 | Technical and backup pre-flight | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.7 | No host, TLS, monitoring, encrypted backup, or restore point |
| FC-09 | Communication pre-flight | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.8 | No school contact staffing or approved “received in error” wording |
| FC-10 | Pilot design and cohort decisions | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §4 | Cohort size, selection, shared-phone policy, timing, currency, and success criteria undecided |
| FC-11 | Execution sequence | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §5 | All live steps require G0 + written G4 pilot authorisation |
| FC-11a | Fake-provider campaign-path rehearsal | **Ready (local evidence)** | [`pilot-rehearsal.md`](pilot-rehearsal.md) §3–6 | 2/2 synthetic messages; 0 duplicate/unknown/failed; no live provider or delivery |
| FC-12 | Stop conditions and stop procedure | **Rehearsal only** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §6; [`pilot-rehearsal.md`](pilot-rehearsal.md) §9 | Kill-switch/disabled checks passed; no live campaign cancellation |
| FC-13 | Reconciliation counts and invariant | **Ready (local evidence)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §7.1; [`load-chaos.md`](../m4/load-chaos.md); [`pilot-rehearsal.md`](pilot-rehearsal.md) §6 | 2/2 synthetic counts reconciled; provider evidence absent |
| FC-14 | Unknown-outcome handling | **Rehearsal only** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §7.3; [`support-model.md`](support-model.md) §8.1 | No reconciliation/correction tool; engineering escalation only. See HR-G13 |
| FC-15 | Rollback and disable | **Rehearsal only** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §8; [`pilot-rehearsal.md`](pilot-rehearsal.md) §9 | Kill-switch/disabled checks passed; not exercised on a host or live campaign |
| FC-16 | Campaign record and post-campaign checklist | **Ready (local evidence)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §9–10; [`pilot-rehearsal.md`](pilot-rehearsal.md) §3–4 | Templates complete; the pilot record is synthetic, not a live campaign |
| FC-17 | Single-worker control | **Gap** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.7, §5 | “Exactly one worker” is procedural; no technical singleton guard is documented. See HR-G25 |
| FC-18 | G4 pilot authorisation and campaign sign-off | **Blocked (external)** | [`first-campaign-runbook.md`](first-campaign-runbook.md) §3.1, §11 | No written authorisation; no named stop authority; **NOT SIGNED** |

---

## 8. Post-implementation review checklist

Source: [`post-implementation-review.md`](post-implementation-review.md).

| # | Check | Status | Evidence | Condition / limitation |
|---|---|---|---|---|
| PR-01 | Purpose and non-replacement disclaimer | **Ready (local evidence)** | [`post-implementation-review.md`](post-implementation-review.md) §1 | Explicitly says it does not replace UAT, G4, G5, or acceptance |
| PR-02 | Metadata and executive-summary structure | **Ready (local evidence)** | [`post-implementation-review.md`](post-implementation-review.md) §2–3 | Fields blank; no review ID or chair |
| PR-03 | Metric definitions | **Ready (local evidence)** | [`post-implementation-review.md`](post-implementation-review.md) §5 | Good definitions; no actuals |
| PR-04 | Defect and incident templates | **Ready (local evidence)** | [`post-implementation-review.md`](post-implementation-review.md) §6–7 | Templates complete; no campaign defects/incidents |
| PR-05 | Provider reconciliation | **Blocked (external)** | [`post-implementation-review.md`](post-implementation-review.md) §8 | No provider evidence; pre-G4 instructions say “blocked” |
| PR-06 | User feedback and training gaps | **Blocked (external)** | [`post-implementation-review.md`](post-implementation-review.md) §9 | No UAT or training delivery |
| PR-07 | Privacy and retention actions | **Blocked (external)** | [`post-implementation-review.md`](post-implementation-review.md) §10; [`privacy-retention-plan.md`](../m5/privacy-retention-plan.md) | H4 open; no purge, legal hold, or deletion evidence |
| PR-08 | Operational readiness review | **Blocked (external)** | [`post-implementation-review.md`](post-implementation-review.md) §11 | OPS-04/05/06/07 unverified; H6 not applied |
| PR-09 | Go/no-go criteria | **Ready (local evidence)** | [`post-implementation-review.md`](post-implementation-review.md) §12.1 | Criteria complete; none can pass today |
| PR-10 | Action plan, lessons learned, evidence appendix | **Ready (local evidence)** | [`post-implementation-review.md`](post-implementation-review.md) §13–15 | Templates complete; empty |
| PR-11 | Review sign-off | **Blocked (external)** | [`post-implementation-review.md`](post-implementation-review.md) §16 | **NOT SIGNED**; no chair or date |
| PR-12 | Hypercare operating plan and review schedule | **Gap** | [`post-implementation-review.md`](post-implementation-review.md) §2, §4; [`support-model.md`](support-model.md) §13 | PIR template exists, but no OPS-11 plan with daily checks, staffing, entry/exit criteria, or schedule. See HR-G18 |

---

## 9. Training guide checklist

Source: [`training-guide-ar.md`](training-guide-ar.md).

| # | Check | Status | Evidence | Condition / limitation |
|---|---|---|---|---|
| TR-01 | Audience, prerequisites, constraints | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §1.1–1.3 | Clear synthetic-data and fake-provider rules |
| TR-02 | Role matrix | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §1.4; [`security-review.md`](../m5/security-review.md) | Matches admin/staff permissions; approval is admin-only |
| TR-03 | Login, password, statements, and import modules | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §2–3; [`m1 status`](../m1/status.md); [`m2 verification`](../m2/verification.md) | Content matches synthetic workflow; no real-sample acceptance |
| TR-04 | Guardian resolution and bulk exclude | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §3.7–3.8 | Locally verified with synthetic data; real-sample acceptance pending |
| TR-05 | Campaign, approval, and results modules | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §4; [`m3 verification`](../m3/verification.md) | Copy not school-approved; no live send |
| TR-06 | Messaging, operations, and provider modules | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §5–6; [`verification.md`](../m4/verification.md) | Fake provider only; live provider blocked |
| TR-07 | Hands-on exercises | **Rehearsal only** | [`training-guide-ar.md`](training-guide-ar.md) §8; [`training-rehearsal.md`](training-rehearsal.md) §3–5 | Internal browser rehearsal passed with noted gaps; exercise 7 not re-run; no school trainee |
| TR-08 | Ambiguity exercise fixture | **Gap** | [`training-guide-ar.md`](training-guide-ar.md) §8.7, §13.1; [`training-rehearsal.md`](training-rehearsal.md) §5 | No fixture guaranteed to produce `AMBIGUOUS_GUARDIAN`. See HR-G21 |
| TR-09 | Assessment and troubleshooting | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §9–10; [`training-rehearsal.md`](training-rehearsal.md) §5 | Internal rehearsal found no console errors; audit-page content assertion was inconclusive; error strings may drift |
| TR-10 | Training attendance and evaluation record | **Gap** | [`training-guide-ar.md`](training-guide-ar.md) §12; [`training-rehearsal.md`](training-rehearsal.md) §6 | Internal rehearsal sign-off only; no school attendance or cohort roster. See HR-G21 |
| TR-11 | Approved training environment | **Blocked (external)** | [`training-guide-ar.md`](training-guide-ar.md) §1.2, §1.6 | No approved staging/training environment is recorded |
| TR-12 | Training delivery | **Blocked (external)** | [`training-guide-ar.md`](training-guide-ar.md) §12–13; [`FeeDesk-Task-Register.csv`](../../FeeDesk-Task-Register.csv) OPS-09 | Not delivered; OPS-09 unchecked |
| TR-13 | School linguistic and copy approval | **Blocked (external)** | [`training-guide-ar.md`](training-guide-ar.md) §13.4 | Arabic template copy still requires school approval (G0/G3) |
| TR-14 | Support, escalation, and privacy-request module | **Gap** | [`training-guide-ar.md`](training-guide-ar.md) §1.5, §9 | Training covers app use, not incident reporting, support escalation, or privacy-request intake. See HR-G21 |
| TR-15 | Technical-owner onboarding | **Gap** | [`handover-pack.md`](handover-pack.md) §12.3; [`training-guide-ar.md`](training-guide-ar.md) §1.1 | Arabic guide targets school staff; no technical onboarding curriculum or competency check. See HR-G26 |
| TR-16 | Trainer notes and known gaps | **Ready (local evidence)** | [`training-guide-ar.md`](training-guide-ar.md) §13 | Honest disclosure of fixture, copy, and expected-result gaps |

---

## 10. Evidence separation

### 10.1 Verified local evidence (can be relied on now, within its limits)

| Evidence | Location | What it proves | What it does **not** prove |
|---|---|---|---|
| 425 backend tests; Ruff clean; `alembic check` clean; migration head `b2c3d4e5f6a7` | [`verification.md`](../m4/verification.md); [`load-chaos.md`](../m4/load-chaos.md) | Local backend behavior and schema consistency | Production host, capacity, or provider behavior |
| 52-route permission matrix; permission/CSRF drift; object isolation | [`security-review.md`](../m5/security-review.md); `apps/api/tests/test_permission_matrix.py` | Route-level authorization coverage | Host hardening, MFA, or production role separation |
| Argon2id, sessions, CSRF, append-only audit, last-admin guard | [`m1 status`](../m1/status.md); [`security-review.md`](../m5/security-review.md) | Application auth/audit behavior | MFA, SSO, or emergency access |
| Synthetic import parsing, review, confirm, provenance | [`m2 verification`](../m2/verification.md) | Import workflow with synthetic XLSX/PDF | Real school statement acceptance (G0) |
| Campaign eligibility, Arabic rendering, immutable snapshot, pending jobs | [`m3 verification`](../m3/verification.md) | Campaign/approval workflow | Approved school copy or live send |
| Fake provider, worker claim/lease/retry/idempotency, status mapping | [`verification.md`](../m4/verification.md) | Messaging foundation behavior | Rasel live request, delivery, or reconciliation |
| Fernet credential vault; rotation/revoke; DB-over-env; no plaintext return | [`verification.md`](../m4/verification.md) | App-level provider credential handling | Vault-key re-encryption or live provider rotation |
| 100-recipient fake load/chaos; reclaim; fencing; 429/timeout; pacing | [`load-chaos.md`](../m4/load-chaos.md) | Local queue behavior and invariants | Capacity benchmark or multi-process rate limit |
| Fake-provider pilot rehearsal: 2 synthetic recipients, 2 delivered fake messages, 0 duplicates/unknown/failed, stop/disable check | [`pilot-rehearsal.md`](pilot-rehearsal.md) §3–9 | End-to-end campaign path with fake provider; approval creates messages/jobs; kill switch/disabled worker claims nothing | Live provider, delivery, reconciliation, or production host |
| Internal browser training rehearsal: staff/admin screens, layout, console | [`training-rehearsal.md`](training-rehearsal.md) §3–5 | UI navigation/labels/controls render with synthetic data; no console errors on checked screens | Arabic comprehension, school attendance, formal OPS-09 delivery |
| Local PostgreSQL `pg_dump -Fc` restore into scratch DB; row counts | [`backup-restore.md`](../runbooks/backup-restore.md); [`review.md`](../runbooks/review.md) | Database dump/restore mechanics | Uploads, encryption, offsite, or production restore |
| Compose YAML parse; script compile/dry-run; no `docker compose config` | [`deployment-readiness.md`](../m5/deployment-readiness.md) | Syntax-level readiness | That the stack starts on Linux or Caddy works |
| Security fixes H1–H3, H5, M1–M10; H4/H6 open | [`security-review.md`](../m5/security-review.md) | Local remediation evidence | OPS-01/03 closure or production hardening |

**Privacy boundary observed in rehearsal:** list, results, and operations surfaces return masked phones, but the explicit message detail and campaign preview remain controlled full-reveal surfaces by design (H3/M1). The training rehearsal flags that the review-table phone is editable and full; trainers must not read numbers aloud. See [`security-review.md`](../m5/security-review.md) and [`training-rehearsal.md`](training-rehearsal.md) §5.

### 10.2 Required production/school/provider evidence (cannot be manufactured locally)

| Required evidence | Owner | Gate / record | Current state |
|---|---|---|---|
| Approved sender, free-text plan, 3 Syrian `+963` test numbers, delivered test, provider record, real samples, school decisions | Provider/ops + school + tech lead | G0 | **Open**; [`gate-g0.md`](../m0/gate-g0.md) |
| Written G4 pilot authorisation, live test-send, delivery/reconciliation contract, controlled pilot, signed report | School director + technical owner + provider | G4 | **Open** |
| Production host, DNS, TLS, firewall, image build, deploy record, smoke checks | Technical owner | OPS-05 / G5 | **Not started** |
| Encrypted backup, offsite copy, uploads restore, decrypt drill, script `--execute`, signed RPO/RTO | DBA/backup custodian + school | OPS-04 / G5 | **Partial (DB-only local drill)** |
| Running monitoring stack, loaded alert rules, delivered/resolved test alert, balance metric, 5xx source | Technical owner | OPS-06 / G5 | **Template only** |
| Runbooks exercised on staging/production; named owners/deputies; Arabic quick reference | Technical owner + school | OPS-07 / OPS-12 | **Desk review only** |
| UAT on approved/anonymised data; defect triage; school sign-off | School + QA/PO | OPS-08 / G5 | **Not started** |
| Approved training environment; delivered Arabic training; attendance; assessment; school acknowledgment | PO/Design + school | OPS-09 / G5 | **Draft + internal rehearsal; delivery blocked** |
| Launch checklist, go/no-go record, production smoke | All | OPS-10 / G5 | **Not started** |
| First controlled campaign, 2-week hypercare, PIR with actual data | Team + school | OPS-11 | **Rehearsal only (fake provider); live campaign not started** |
| Signed handover acceptance and credential transfer evidence | School + technical + security + provider | OPS-12 | **Draft; NOT SIGNED** |
| Signed retention/deletion policy; purge/anonymisation implementation; deletion evidence; legal hold | School data owner + engineering | H4 / OPS-03 | **Open** |
| DB role separation applied; denial tests; trigger-tamper test; rollback rehearsal | DBA/backend + security | H6 / OPS-01 | **Open** |

**G0 nuance:** G0 is not a monolithic failure. The provider account/API access criterion is recorded as Pass, but the gate remains open because sender approval, free-text enablement, three Syrian test numbers, a delivered test, provider record, real samples, and school decisions are missing. The gate record notes two failed attempts: `local_sms` rejected the non-Syrian account phone, and `int_sms` rejected the trial free-text send. “No live SMS” in this review therefore means no **delivered or verified** live SMS, not no attempt at all. See [`gate-g0.md`](../m0/gate-g0.md).

---

## 11. Gap register

Severity is assigned for handover readiness, not for production incident severity. “Critical” means handover cannot be accepted or a gate cannot close without it. “High” means a material operational or security control is missing. “Medium” means the package can be corrected without changing the gate outcome. Checklist references point to the rows in §4–§9, where each item carries its evidence link.

| ID | Severity | Gap | Checklist ref | Owner role | Required evidence | Blocking gate |
|---|---|---|---|---|---|---|
| HR-G01 | **Critical** | No named operational ownership: contacts, deputies, runbook owners, incident commander, stop authority, data owner | SM-04, SM-13, CC-04, FC-01, FC-18 | School admin + technical owner | Named roster with written acceptance, deputies, published escalation, contact register | OPS-07 / OPS-11 / OPS-12 |
| HR-G02 | **Critical** | No production deployment or launch evidence: host, DNS, TLS, firewall, images, deploy record, smoke checks, launch checklist/go-no-go; hosting/residency decision absent | HP-06, HP-13, FC-08 | Technical owner + school | Written hosting/residency decision, host provisioning record, DNS/TLS validation, image digests/tags, `docker compose config`, deploy/smoke transcript, launch checklist/go-no-go, rollback target | OPS-05 / OPS-10 / G5 |
| HR-G03 | **Critical** | No encrypted/offsite backup, uploads restore, decrypt drill, or signed RPO/RTO; script `--execute` not run | HP-12, CC-11, PR-08 | DBA/backup custodian + school | Encrypted backup artifact, offsite copy, uploads restore, offline-key decrypt, `--execute` transcript, RPO/RTO sign-off | OPS-04 / G5 |
| HR-G04 | **Critical** | H4 retention/deletion unsigned and unimplemented; PII retained indefinitely; no purge or legal hold | HP-14, PR-07 | School data owner + engineering | Signed R1–R11 policy, `retention_until` population, purge/anonymisation job, dry-run/execute evidence, legal hold, deletion receipt | H4 / OPS-03 / G5 |
| HR-G05 | **High** | H6 DB role separation not applied; runtime uses owner credential; audit tamper path remains | CC-08, PR-08 | DBA/backend + security | `feedesk_owner/app/backup` applied, denial tests, trigger-tamper test, rollback rehearsal, runbook updates | H6 / OPS-01 / G5 |
| HR-G06 | **Critical** | G0 not passed: no approved sender, free-text plan, Syrian test delivery, real samples, or school decisions | FC-02, FC-04, FC-06 | Provider/ops + school + tech lead | Signed G0 record, sender ID, plan, 3 `+963` numbers, delivered test, provider record, samples/taxonomy, school decisions | G0 / G4 |
| HR-G07 | **Critical** | G4 not passed: no written pilot authorisation, live test-send, DLR/reconciliation contract, or live controlled pilot | FC-02, FC-11, FC-18 | School director + technical owner + provider | Signed G4 pilot authorisation, live test-send evidence, DLR contract, pilot report, signed G4 record | G4 / OPS-11 |
| HR-G08 | **High** | No UAT on approved/anonymised data; no defect triage or school sign-off | PR-06, PR-09 | School + QA/PO | UAT plan, participants, approved data set, executed scenarios, defect triage, sign-off | OPS-08 / G5 |
| HR-G09 | **High** | No approved training environment is recorded, and no training delivery/attendance/evaluation exists | TR-11, TR-12 | PO/Design + school | Approved environment, delivered sessions, attendance roster, assessment results, school acknowledgment | OPS-09 / G5 |
| HR-G10 | **High** | Support model, SLA, contacts, and evidence store are unsigned or unnamed | SM-04, SM-10, SM-12, SM-13 | School admin + technical owner + security | Signed SLA-01..15, contact register, evidence-store access list, escalation acceptance, residual risks | OPS-07 / OPS-11 / OPS-12 |
| HR-G11 | **High** | Credential custody incomplete: no named custodians/deputies, ledger, break-glass escrow, approved transfer channel, or transfer evidence | CC-04, CC-05, CC-16 | Security + school + technical owner | Custody ledger, named custodians/deputies, sealed break-glass record, approved channel and identity verification, transfer evidence | OPS-12 |
| HR-G12 | **High** | Vault-key re-encryption not implemented or tested; `PROVIDER_CREDENTIAL_KEY` rotation is blocked | CC-10 | Security + engineering | Documented re-encryption procedure, scratch-DB rehearsal, decrypt test, rollback path, second reviewer | G4 / OPS-12 |
| HR-G13 | **High** | No provider reconciliation or audited correction capability; unknown outcomes require case-by-case engineering escalation | FC-14, PR-05 | Engineering + provider/ops | Audited reconciliation write workflow or signed manual procedure with second reviewer; tests; G4 evidence | G4 / OPS-11 |
| HR-G14 | **High** | Monitoring sources unresolved: 5xx source is inert with Caddy access logging disabled, and the provider balance metric is not wired | HP-13, PR-08 | Technical owner | Alternative 5xx metric source, provider balance metric, alert rules, delivered/resolved test, PII-safe labels | OPS-06 |
| HR-G15 | **High** | No release manifest or deployed-release pin: no commit SHA, image digest, dependency lock hash, or migration head in the handover record | HP-18, HP-20 | Technical owner | Signed release manifest with commit, image digests, migration head, lock/SBOM hashes, date, verification commands | OPS-12 |
| HR-G16 | **High** | Credential inventory omits hosting/VPS console and offsite backup storage credentials | CC-02 | Security + technical owner | Added CR entries, custodians/deputies, storage class, rotation/revocation, ledger rows | OPS-04 / OPS-05 / OPS-12 |
| HR-G17 | **High** | Allowlist operating decision unresolved: a non-empty allowlist blocks every non-listed pilot recipient; an empty list may conflict with test-only intent | FC-05 | Technical owner + school | Written decision, tested configuration, exact approved list or approved empty-list exception | G4 / OPS-11 |
| HR-G18 | **Medium** | No hypercare operating plan: daily checks, staffing, entry/exit criteria, data collection, and schedule are absent | PR-12 | Technical owner + school | Signed OPS-11 plan with cadence, roles, metrics, exit criteria, and review schedule | OPS-11 |
| HR-G19 | **Medium** | Runbooks unexercised; no named owners/deputies; no Arabic quick reference; no maintenance/incident templates | HP-11, SM-06, PR-08 | Technical owner + school | Staging exercises, named owners/deputies, Arabic quick reference, maintenance/incident templates, updated review record | OPS-07 / OPS-12 |
| HR-G20 | **Medium** | No tabletop exercise for unknown outcome, provider outage, restore, key compromise, or privacy incident | SM-08, SM-17 | Technical owner + provider/ops + security | Tabletop record with scenario, participants, findings, actions, and due dates | OPS-07 / OPS-11 |
| HR-G21 | **Medium** | Training guide only partially rehearsal-validated: exercise 7 numbers not re-run, ambiguity fixture missing, no school cohort roster, no support/privacy module | TR-07, TR-08, TR-10, TR-14 | PO/Design + QA | Executed dry-run of every exercise, committed ambiguity fixture, reconciled expected results, school attendance roster, added modules | OPS-09 |
| HR-G22 | **Medium** | Gate/task register inconsistency: G1–G3 unchecked or pending but not named in the handover pack; MSG-04 remains unchecked despite fake test-send evidence; OPS-02 is checked while its G4 dependency is open | HP-16, HP-21 | Technical lead + PO | Reconciled gate register with pass/waiver records for G1–G3; task-status and dependency corrections; explicit gate narrative | OPS-12 |
| HR-G23 | **Medium** | Source-document conflicts reconciled: M2/M4/M5 now record bulk exclusion, guardian resolution, and the encrypted vault/rotation UI. The runbook still uses `-U feedesk` until H6 is applied; the table count is historical. | HP-08, HP-15 | Documentation lead + technical owner | Runbook commands updated after H6; conflict register closed against the checked release | OPS-12 |
| HR-G24 | **Medium** | MFA is not implemented and no written residual-risk acceptance exists | SM-16 | School + security | Signed MFA risk acceptance with compensating controls, or MFA implementation | OPS-01 / OPS-12 |
| HR-G25 | **Medium** | “Exactly one worker” is procedural only; no technical singleton guard is documented, while pacing and rate are per process | FC-17 | Technical owner + engineering | Singleton lock or preflight process check, tested; runbook step; alert for duplicate workers | OPS-11 |
| HR-G26 | **Medium** | No technical-owner onboarding or competency record: no walkthrough, shadowing, first-run observation, or Q&A sign-off | HP-22, TR-15 | Technical lead | Onboarding plan, walkthrough record, shadowing evidence, observed first-run checklist, competency sign-off | OPS-12 |

---

## 12. Cannot accept yet

The following cannot be accepted, marked complete, or represented as ready from the current package:

- **Handover acceptance (OPS-12).** The acceptance checklist is unsigned and the custody ledger is blank. See [`handover-pack.md`](handover-pack.md) §12 and [`credential-handover.md`](credential-handover.md) §10.
- **Production deployment (OPS-05).** No host, DNS, TLS, firewall, image build, deploy record, or smoke test. See [`deployment-readiness.md`](../m5/deployment-readiness.md).
- **Backup/restore (OPS-04).** Only a local database restore exists; uploads, encryption, offsite, decrypt, and `--execute` are absent. See [`review.md`](../runbooks/review.md).
- **Monitoring/alerting (OPS-06).** No running stack, delivered alert, balance metric, or 5xx source. See [`handover-pack.md`](handover-pack.md) §9.3.
- **Runbooks (OPS-07).** Desk-reviewed templates only; no exercise and no named owners. See [`review.md`](../runbooks/review.md).
- **UAT (OPS-08).** Not performed; no participants, data set, defect triage, or sign-off.
- **Training (OPS-09).** Not delivered; no approved environment, attendance, or evaluation.
- **Launch (OPS-10/G5).** No launch checklist, go/no-go record, or production smoke.
- **First controlled campaign and hypercare (OPS-11).** Only a fake-provider rehearsal exists; no live first campaign, pilot authorisation, cohort, stop authority, or hypercare plan. See [`pilot-rehearsal.md`](pilot-rehearsal.md).
- **Live SMS or provider verification (G0/G4).** No approved sender, free-text plan, verified Syrian test delivery, live test-send, or reconciliation.
- **H4 retention/deletion.** Policy unsigned; no purge, anonymisation, legal hold, or deletion evidence.
- **H6 DB role separation.** Not applied; runtime still uses the owner credential.
- **Credential custody.** No named custodians, ledger, break-glass escrow, or transfer ceremony. See [`credential-handover.md`](credential-handover.md) §3–5.
- **Support model/SLA.** No signed hours, response targets, contacts, or evidence store.
- **Any gate pass.** G0, G4, and G5 are open. G1 and G2 are unchecked in the task register; M2 and M3 record formal acceptance as pending G0/G1 and school copy/real data respectively. None may be treated as passed by implication.
- **Any statement that the system is production-ready, launched, UAT-accepted, trained, or handed over.** None of those events has occurred.

---

## 13. Minimum decisions needed

These are the smallest decisions that unblock the next meaningful step. They are not a complete project plan. Each decision needs a named owner, a date, and a recorded output.

### 13.1 School / authorised representative

| # | Decision | Needed before | Required output |
|---|---|---|---|
| S-01 | Name the school director/authorised representative, data owner and deputy, school admin and backup approver | OPS-07 / OPS-11 / OPS-12 | Written appointments with acceptance |
| S-02 | Approve hosting model, location, and data residency | OPS-05 | Written hosting decision |
| S-03 | Approve retention/deletion policy R1–R11 (H4) and legal-hold process | H4 / OPS-03 | Signed policy with data-owner signature |
| S-04 | Approve RPO ≤24 h / RTO ≤4 h, or fund PITR/faster restore | OPS-04 | Signed RPO/RTO and data-loss authority |
| S-05 | Approve support hours, SLA-01..15, contacts, escalation, and evidence store | OPS-07 / OPS-12 | Signed support model and contact register |
| S-06 | Approve Arabic template copy, opt-out wording, currency, and approval policy | G0 / G3 | Signed copy and policy decision |
| S-07 | Approve UAT participants, data set, scenarios, and acceptance criteria | OPS-08 | Signed UAT plan |
| S-08 | Approve first pilot cohort, selection rule, stop authority, and go/no-go attendees | G4 / OPS-11 | Written pilot approval |
| S-09 | Accept MFA residual risk or fund MFA | OPS-01 / OPS-12 | Signed risk acceptance |
| S-10 | Approve credential storage classes, custody model, break-glass custodians, and transfer channel | OPS-12 | Signed custody plan |
| S-11 | Decide allowlist mode for the pilot: exact approved list or written empty-list exception | G4 / OPS-11 | Written decision and tested configuration |
| S-12 | Decide whether shared-phone guardians are in scope for the pilot and record the rule | G4 / OPS-11 | Written shared-phone policy and preview evidence |

### 13.2 Technical owner

| # | Decision / action | Needed before | Required output |
|---|---|---|---|
| T-01 | Provision the approved host; set OS, NTP, firewall, DNS, TLS, and renewal monitoring | OPS-05 | Host and TLS evidence |
| T-02 | Build and tag images; run `docker compose config`; record digests and rollback target | OPS-05 | Image/deploy manifest |
| T-03 | Implement encrypted, offsite backup with uploads and a decrypt/restore drill | OPS-04 | Drill transcript and artifact list |
| T-04 | Stand up monitoring, load alert rules, deliver and resolve a test alert, wire the balance metric | OPS-06 | Alert receipt and dashboard evidence |
| T-05 | Resolve the 5xx monitoring source without re-enabling PII-bearing access logs | OPS-06 | Alternative metric and tested rule |
| T-06 | Apply H6 roles with a maintenance window, denial tests, and rollback rehearsal; update runbooks | H6 / OPS-01 | H6 evidence pack |
| T-07 | Name runbook owners/deputies; exercise deploy, rollback, worker recovery, restore, and key rotation on staging | OPS-07 | Exercise records |
| T-08 | Produce the release manifest: commit, image digests, migration head, lock/SBOM hashes, date | OPS-12 | Signed release manifest |
| T-09 | Complete the custody inventory (VPS console, offsite backup, registry/CI if used) and ledger | OPS-12 | Updated inventory and ledger |
| T-10 | Confirm the deployed provider credential source and vault status; document rotation/revocation path | G4 / OPS-12 | Deployed-release verification |
| T-11 | Enforce or technically guard the single-worker rule | OPS-11 | Tested control and runbook step |
| T-12 | Produce the hypercare plan with daily checks, staffing, and exit criteria | OPS-11 | Signed OPS-11 plan |

### 13.3 Provider / operations

| # | Decision / action | Needed before | Required output |
|---|---|---|---|
| P-01 | Confirm approved sender ID, free-text plan, and Syrian coverage | G0 | Provider written confirmation |
| P-02 | Accept 3 school-controlled `+963` test numbers and support a delivered test | G0 | Test record and provider message ID |
| P-03 | Confirm pricing, segments, rate limits, balance, and low-water mark | G0 / G4 | Written commercial/technical confirmation |
| P-04 | Confirm the delivery-report/reconciliation method and console access | G0 / G4 | Reconciliation contract |
| P-05 | Support the G4 pilot test-send and reconcile the provider record | G4 | Pilot reconciliation evidence |
| P-06 | Name a provider/ops contact for the campaign window and incident escalation | OPS-11 | Contact and escalation path |

### 13.4 Security

| # | Decision / action | Needed before | Required output |
|---|---|---|---|
| SEC-01 | Approve custody model, storage classes, break-glass rules, and dual control | OPS-12 | Signed security acceptance |
| SEC-02 | Review and approve the vault-key re-encryption procedure or record the residual risk | G4 / OPS-12 | Procedure review or signed exception |
| SEC-03 | Define the evidence store, access list, and incident-command handoff | OPS-07 / OPS-11 | Evidence-store approval |
| SEC-04 | Review H6 denial tests and the audit-trigger tamper test | H6 / OPS-01 | Security sign-off |
| SEC-05 | Accept or reject the MFA residual risk with compensating controls | OPS-01 / OPS-12 | Signed risk decision |

---

## 14. Sign-off block

> **SIGN-OFF STATUS: NOT SIGNED.**
>
> No signature, acceptance, conditional acceptance, or gate closure has been given. The table below is a placeholder for the eventual handover decision. A signature on this review would acknowledge the findings; it would not close any gate, prove any production claim, or replace the separate gate records.

| Role | Name | Decision | Signature | Date |
|---|---|---|---|---|
| School admin / authorised representative | ____________________ | ☐ Accepted  ☐ Accepted with conditions  ☐ Not accepted | ____________________ | __________ |
| Technical owner | ____________________ | ☐ Accepted  ☐ Accepted with conditions  ☐ Not accepted | ____________________ | __________ |
| Security reviewer | ____________________ | ☐ Accepted  ☐ Accepted with conditions  ☐ Not accepted | ____________________ | __________ |
| Provider/operations lead | ____________________ | ☐ Accepted  ☐ Accepted with conditions  ☐ Not accepted | ____________________ | __________ |

**Conditions / exceptions:** none recorded, because no acceptance has been given.

**Recommended current disposition:** **Not accepted.** The only honest alternatives are “not accepted” or “accepted with conditions limited to documentation and planning.” Neither is a statement of operational readiness. A full “accepted” decision would require the production, school, provider, UAT, training, and gate evidence listed in §10.2 and the closure of the Critical/High gaps in §11.

---

## 15. Review conclusion

The M6 package succeeds as a candid description of a locally verified system with a blocked production path. The fake-provider pilot and internal training rehearsals strengthen the local evidence but do not change that blocked path. The package does not yet succeed as a handover instrument, because the artifacts that prove ownership — names, signatures, custody records, production evidence, and gate records — are missing or blank.

The correct next step is not another documentation pass. It is to:

1. name the owners and custodians;
2. obtain the school’s retention, hosting, SLA, copy, UAT, and pilot decisions;
3. produce the production deployment, backup/restore, and alert evidence;
4. complete the first controlled campaign only after G0 and a written G4 pilot authorisation;
5. deliver training and UAT;
6. return to this review and the handover acceptance checklist with evidence.

Until then, the package should be used for planning, tabletop rehearsal, and condition-setting — not for launch, live SMS, or ownership transfer.

---

## 16. Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 4 Nov 2026 | Initial internal handover readiness review; section checklists, evidence separation, gap register, decisions, and unsigned sign-off block; no production or gate claims | Documentation and codemap specialist |
| 0.2 | 4 Nov 2026 | Integrated fake-provider pilot and internal training rehearsal evidence; corrected source-status reconciliation; HR-G23 remains partially open; no gate claims | Documentation and codemap specialist |
