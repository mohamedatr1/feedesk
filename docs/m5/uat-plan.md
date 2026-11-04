# FeeDesk OPS-08 — User Acceptance Test (UAT) Plan

**Document ID:** M5-UAT-PLAN-01  
**Version:** 0.1  
**Date:** 4 November 2026  
**Owner:** QA / Product Owner (proposed)  
**Approver:** School UAT Lead (proposed; not assigned)  
**Status:** **PLAN ONLY — NOT EXECUTED — NOT AN ACCEPTANCE RECORD**

> **Status statement — read this first**
>
> This document is a plan for OPS-08. **No UAT session has been executed.** No participant, data set, environment, or sign-off has been approved. G0 and G4 are **open**, G1–G3 are **not passed**, and H4/H6 remain open. Nothing in this document closes a gate, authorises a live SMS, approves production use, or proves that FeeDesk is ready to launch.
>
> The scripts in `uat-scripts.md` describe expected behaviour derived from the M1–M4 verification records. Expected results are **not observed results**. The execution record in `uat-execution-record.md` is a blank template marked **NOT EXECUTED**.

### ملخص عربي — Arabic summary

هذه الوثيقة **خطة** لاختبار القبول (OPS-08) وليست سجل تنفيذ. لم تُنفَّذ أي جلسة UAT، ولم تُعتمد بيانات أو حسابات أو بيئة، وبوابات G0/G4 ما زالت مفتوحة، وG1–G3 غير مجتازة. لا يجوز استخدام هذه الوثيقة لإثبات قبول أو إذن إطلاق. يغطي النطاق M1–M5، ويتطلب بيانات حقيقية مجهولة الهوية بموافقة مكتوبة أو بيانات اصطناعية بديلة، ومزوّدًا وهميًا فقط، وعدم إرسال أي SMS حقيقي.

---

## 1. Purpose

Define a controlled, evidence-based UAT for FeeDesk so that a school employee can evaluate the implemented M1–M5 surfaces against approved scenarios, using approved data and a fake provider, before any launch decision.

The UAT answers one question:

> Can a school staff member and a school administrator complete the agreed fee-reminder workflow safely and correctly, with understandable Arabic UI, correct financial behaviour, correct permissions, and no unintended send, on the tested build and data set?

It does **not** answer whether the provider is commercially or operationally ready, whether production infrastructure is ready, whether training is complete, or whether the school should launch.

---

## 2. Objectives

| ID | Objective | Evidence |
|---|---|---|
| O-01 | Confirm the school can sign in, change a temporary password, and use only the functions allowed by its role. | UAT-01, UAT-02 |
| O-02 | Confirm imports preserve financial meaning and provenance for XLSX and PDF statements. | UAT-06–UAT-11 |
| O-03 | Confirm blocking errors, warnings, exclusions, guardian ambiguity, and confirmation are understandable and fail closed. | UAT-08–UAT-11, UAT-21 |
| O-04 | Confirm a campaign can be prepared, previewed, submitted, approved, and cancelled without any send. | UAT-12–UAT-15 |
| O-05 | Confirm message and result screens distinguish provider acceptance from delivery and never offer a blind resend. | UAT-16, UAT-18 |
| O-06 | Confirm provider settings, fake test-send, allowlist, and balance behave safely with the fake provider. | UAT-17 |
| O-07 | Confirm dashboard, trends, and per-currency totals are honest and do not fabricate deltas. | UAT-19 |
| O-08 | Confirm PII masking, permission boundaries, audit visibility, and evidence handling protect school data. | UAT-02, UAT-05, UAT-20 |
| O-09 | Record defects with reproducible evidence and agree an acceptance decision with named owners. | Execution record |

---

## 3. Scope

### 3.1 In scope

| Area | Implemented surface to test | Primary scripts |
|---|---|---|
| M1 — Identity, RBAC, settings, users, audit | Login, forced password change, session expiry, lockout, staff/admin boundaries, user lifecycle, school settings validation, audit read-only view | UAT-01–UAT-05 |
| M2 — Import and financial review | XLSX/PDF upload, sheet selection, column mapping, validation, row edit/revalidation, bulk exclusion/restore, guardian resolution, confirmation, cancellation | UAT-06–UAT-11 |
| M3 — Campaigns, approval, dashboard | Draft from a confirmed import, recipient/exclusion/warning review, message preview, submit, admin approval, immutable snapshot, cancel, results, dashboard/trends | UAT-12–UAT-15, UAT-19 |
| M4 — Messaging foundation and control plane | Fake-provider message history/detail, campaign results, delivery-vs-acceptance semantics, unknown outcome, provider settings, fake test-send/allowlist, balance, read-only operations | UAT-16–UAT-18 |
| M5 — Hardening surfaces visible in UAT | Privacy masking, role boundaries, audit redaction, blocked/error paths, Arabic RTL/responsive/accessibility smoke | UAT-20–UAT-22 |

### 3.2 Out of scope

- Live SMS, live Rasel calls, provider webhooks, provider reconciliation writes, and any campaign to real guardians.
- OCR execution for scanned PDFs; the product detects a scanned PDF and creates no rows.
- Manual message resend, status correction, or reconciliation actions; the UI is read-only.
- WhatsApp or any channel other than SMS (hard-disabled).
- Billing, online payment, or fee collection.
- Production deployment, TLS, DNS, firewall, monitoring, backup/restore, and runbook execution. Those are OPS-04–OPS-07 and require separate evidence.
- Training delivery, hypercare, go/no-go, launch, or handover acceptance.
- Performance, capacity, or load acceptance. M4 load/chaos evidence is fake-provider engineering evidence only.
- Formal penetration testing, threat modelling, or a full WCAG audit. UAT includes role/privacy and accessibility smoke checks but is not a substitute for those activities.
- A claim that G0, G1, G2, G3, G4, G5, OPS-08, OPS-09, OPS-10, or launch has passed.

### 3.3 Non-claims

- UAT acceptance is **not** production acceptance.
- UAT acceptance is **not** G5 and does **not** authorise launch.
- UAT on synthetic data does **not** close the real-sample gap in G2.
- UAT on a school-approved Arabic template does **not** approve final copy for every future campaign; copy approval is version-specific.
- UAT does **not** prove provider delivery. The fake provider cannot prove Rasel delivery, latency, or reconciliation.

---

## 4. UAT approach

### 4.1 Two possible data modes

| Mode | Description | May count as OPS-08? |
|---|---|---|
| **A — Approved anonymized real data** | School-approved, anonymized statements and derived records; live provider remains fake/disabled. | Yes, if all entry criteria and this plan are met. |
| **B — Synthetic fallback** | `.local/samples` or QA-prepared synthetic fixtures; no real school data. Used after E-01/E-02 are met when approved real data is unavailable or not appropriate for a scenario. | Only with the School UAT Lead's written approval of a synthetic-only scope. The record must state that real-data validation remains open. |

A pre-gate synthetic exercise is a **rehearsal**, not OPS-08, and must be labelled as such. It cannot be used for UAT acceptance or to close G2. A synthetic-only formal UAT still requires G0/G4 entry and must record that real-sample acceptance remains open.

### 4.2 Test cycle

1. **Entry review** — verify E-01–E-10 in §6. A failed mandatory entry criterion stops the session.
2. **Environment and data freeze** — record build, commit, migrations, fixtures, accounts, and data approval reference. No unrecorded changes during a script.
3. **Dry run** — QA executes the scripts once in a non-scoring run to confirm preconditions and fixture baselines. Dry-run results are not acceptance evidence.
4. **Formal execution** — Staff Tester and Admin Tester execute the scripts. QA records evidence and defects. The Technical Owner supports environment and fake-worker steps.
5. **Daily triage** — QA, Technical Owner, and School UAT Lead review new defects and agree severity.
6. **Retest** — QA retests fixes on a recorded build; the original script and a small regression scope are repeated.
7. **Exit review** — verify §7 and decide Accepted / Accepted with conditions / Not accepted.
8. **Sign-off and data disposition** — sign §13, then delete or anonymize UAT data and deactivate accounts.

### 4.3 Test rules

- One script at a time; record the actual result even when it differs from the expected result.
- Do not "make the test pass" by editing data, skipping a guard, changing the provider, or using SQL.
- Stop and log a defect when the system does something unsafe or misleading, even if the screen eventually allows progress.
- Use only the approved environment, accounts, fixtures, and test numbers.
- No live SMS, no real guardian number, no real provider key.
- The API never sends; if a worker is needed for message/results scripts, the Technical Owner runs it in an isolated fake-provider process with the approved flags.
- Arabic UI labels are quoted as observed in the current build; if the build's wording differs, record the difference rather than translating it silently.

---

## 5. Roles

| Role | Responsibilities | Decision rights | Must not |
|---|---|---|---|
| **School UAT Lead** | Owns the school-side plan, participants, data approval, schedule, and acceptance recommendation; resolves policy questions; signs the decision. | Approve data mode, scope, deferrals, and final acceptance recommendation. | Execute admin approval on behalf of the Admin Tester without recording it; approve a live send. |
| **Staff Tester** | School staff member. Executes staff scripts: imports, review, campaign draft/submit, message/result reading. | Report defects and propose severity. | Approve campaigns, change users/settings, access admin-only screens, use real guardian data. |
| **Admin Tester** | School administrator. Executes admin scripts: approval, users, settings, templates, provider (fake), audit, operations. | Report defects and confirm admin-side behaviour. | Use a real provider key; approve a campaign outside the UAT environment; share temporary passwords. |
| **Technical Owner** | Prepares the approved environment, build, database, fake provider, allowlist, worker runs, accounts, and logs; supports technical evidence; fixes or routes defects. | Stop the session for safety; declare environment/build state. | Change `.env.local` or production; enable live messaging; access school data beyond the approved set. |
| **QA** | Owns the plan, scripts, fixture register, evidence index, defect log, retest, and coverage; independently judges pass/fail; recommends stop/continue. | Reject incomplete evidence; propose severity; block exit if S1/S2 remain open. | Rewrite a tester's actual result; close a defect without retest evidence. |
| **Observer** | School management, security/privacy, product owner, or other approved observer. Watches, asks questions, and may raise defects. | Raise concerns; no execution authority unless also assigned a tester role. | Intervene in a script, handle credentials, or remove evidence. |

**Segregation:** where staffing allows, the Staff Tester and Admin Tester are different people. The person who implements a fix should not be the only person who retests it.

---

## 6. Entry criteria

All mandatory criteria must be **Yes** or have a signed, recorded disposition. A "No" on E-01, E-02, E-04, or E-05 stops formal UAT. A "No" on E-06 stops copy acceptance only; affected scripts are recorded as "observed only" and the copy remains a G3/launch blocker.

| ID | Criterion | Evidence required | Mandatory |
|---|---|---|---|
| E-01 | **G0 passed** — approved Rasel sender, Syrian test numbers, free-text-enabled plan or provider enablement, 5+ real anonymized XLSX and 3+ real anonymized PDF samples, and written school decisions on currency, approval, retention, opt-out, hosting, and Arabic wording. | Signed G0 record and linked evidence. | Yes |
| E-02 | **G4 passed** — live test-send evidence, provider reconciliation method, and a controlled pilot record. | Signed G4 record. | Yes |
| E-03 | **G1–G3 disposition recorded** — if any is not passed, the open item is listed as a known gap and excluded from UAT acceptance; it remains a launch blocker. | Gate status table approved by School UAT Lead and QA. | Yes |
| E-04 | **Approved UAT environment** — separate from production, approved URL, TLS, build/commit, migrations at head, health checks, monitoring, restricted access, and a tested reset/restore path. | Environment record and health/build screenshots. | Yes |
| E-05 | **Approved data set** — written school approval for anonymized real data, or written approval for synthetic-only mode; data register and anonymization check complete. | Signed data approval and fixture register. | Yes |
| E-06 | **Approved copy** — school-approved Arabic campaign template and critical SMS/opt-out wording; if not approved, copy-dependent scripts are "observed only" and cannot be accepted. | Copy approval reference and template version. | Conditional — required for copy acceptance only |
| E-07 | **Approved accounts** — separate staff and admin UAT accounts, temporary passwords delivered securely, forced password change enabled, least privilege, no shared accounts, observer read-only if used. | Account register; no passwords in the record. | Yes |
| E-08 | **Fixtures and expected baselines** — approved XLSX/PDF fixtures, duplicate/unsupported/scanned files, campaign fixture, ambiguous-guardian fixture, and fake-provider allowlist test numbers. | Fixture register with expected baselines. | Yes |
| E-09 | **Evidence and defect tooling** — secure evidence folder, redaction method, defect tracker, build/version record, and access to relevant logs/request IDs. | Tooling checklist. | Yes |
| E-10 | **Participant readiness and authorisation** — roles assigned, safety/data/evidence briefing completed, confidentiality terms signed if required, and written UAT authorisation from the School UAT Lead and Technical Owner. | Roster, briefing record, signed authorisation. | Yes |

### 6.1 Environment safety requirements

- `MESSAGING_PROVIDER=fake`.
- `MESSAGING_ENABLED=false` and `MESSAGING_KILL_SWITCH=true` by default. A controlled fake-worker run may temporarily set the worker flags in an isolated process with Technical Owner approval; the API process remains non-sending.
- No production provider credential is present in the UAT environment.
- No production database, production object storage, or production school data is connected.
- The environment is access-restricted and monitored; test accounts are the only accounts used.
- A pre-UAT backup or reset point exists, and the restore path has been checked.

**Why G4 is an entry criterion when UAT uses the fake provider:** G4 proves that the live provider path, test-send, and reconciliation method exist before the school is asked to accept the product. UAT deliberately does not send to guardians, so the G4 evidence and the UAT evidence are separate and neither replaces the other.

---

## 7. Exit criteria

| ID | Criterion | Threshold |
|---|---|---|
| X-01 | **Coverage** | Every P1 script has a recorded result (Pass/Fail/Blocked). A P1 may be Blocked only for a documented external blocker approved by the School UAT Lead; otherwise it must be executed. P2 scripts are executed or deferred in writing. |
| X-02 | **Critical defects** | No open S1 or S2 defect. Any S1/S2 discovered must be fixed and retested, or the decision is **Not accepted**. |
| X-03 | **Other defects** | S3 defects have an owner, workaround, and accepted target date; S4 defects are triaged and may be deferred. No defect may be silently closed. |
| X-04 | **Evidence** | Every executed script has a result, actual result, tester/date, and evidence reference. Evidence is redacted and contains no PII or secrets. |
| X-05 | **Data and access disposition** | UAT data is deleted or anonymized per approval; accounts are deactivated; sessions revoked; fake credentials revoked; worker stopped; evidence stored in the approved location. |
| X-06 | **Sign-off** | School UAT Lead, QA, Technical Owner, and the testers sign the decision. The record states the tested build, data mode, scope, open conditions, and explicit non-claims. |

**Pass-rate rule:** 100% of P1 scripts in the agreed scope must pass. A P1 that is Blocked for an external reason must be explicitly excluded from the acceptance scope in writing and remains an open launch blocker. A numeric overall pass rate is not sufficient; an S1/S2 defect blocks acceptance regardless of the percentage.

---

## 8. Environment and data policy

### 8.1 Environment

| Item | Requirement |
|---|---|
| Hosting | Approved UAT/staging environment, separate from production; no production credentials. |
| Build | One recorded build/commit and migration head for the session; rebuilds require a new session ID or a recorded change note. |
| Provider | Fake provider only. Live provider and live SMS are prohibited in UAT. |
| Messaging | Disabled/kill switch on by default; controlled fake-worker runs only. |
| Access | Named testers and support only; no shared logins; sessions revoked after the session. |
| Monitoring | Basic health/error visibility; no claim that production monitoring is verified. |
| Reset | A reset/restore point exists; the Technical Owner records how to return to it. |

### 8.2 Data modes

**Mode A — approved anonymized real data.** Only with a written school approval that names the data owner, purpose, permitted fields, storage location, access list, retention, and deletion method. "Anonymized" means direct identifiers are removed or replaced before the data enters the UAT environment, not merely hidden in the UI.

**Mode B — synthetic fallback.** Use `.local/samples` or QA-prepared fixtures. Synthetic data must preserve the relationships needed for the scenario (same guardian across rows, shared phone, missing phone, zero balance, multi-currency, ambiguous candidates). A synthetic-only sign-off must say so.

### 8.3 Anonymisation standard

Before approval, the data owner and QA verify:

- Guardian names, student names, staff names, emails, national IDs, addresses, and account numbers are removed or replaced with stable pseudonyms (for example `GUARDIAN-001`, `STUDENT-001`).
- Phone numbers are replaced with reserved synthetic numbers in valid E.164 format; shared-phone, missing-phone, and invalid-phone cases are preserved deliberately.
- The same pseudonym is used consistently across rows so duplicate/shared relationships remain testable.
- Rare combinations (unusual amount + class + date + sibling group) are assessed for re-identification risk.
- The pseudonym mapping key is stored separately, encrypted, access-limited, and destroyed after UAT.
- No real data is copied into the repository, chat, tickets, screenshots, or this documentation set.

### 8.4 Copy policy

- The active campaign template must be the school-approved version for copy acceptance. The seeded template is draft copy and is not school-approved.
- If copy is not approved, UAT-12–UAT-14 may verify rendering, variables, amounts, and layout, but the copy itself is recorded as **not accepted** and remains a G3/launch blocker.
- Error messages and UI labels may be reviewed for clarity, but final Arabic wording approval is a separate school decision.

### 8.5 Prohibited actions

- No live SMS or live provider call.
- No real guardian/student data without written approval and anonymization.
- No production secrets, `.env.local`, API keys, session cookies, or temporary passwords in evidence.
- No SQL edits to force a state, resolve an unknown outcome, or bypass a guard.
- No manual resend, campaign "replacement" send, or provider reconciliation write.
- No disabling audit, CSRF, RBAC, masking, or the kill switch to make a test pass.
- No screenshot of a full phone number, real name, message body, credential, or token.

---

## 9. Coverage matrix M1–M5

| Milestone / area | UAT scripts | What is covered | Entry dependency | Acceptance note |
|---|---|---|---|---|
| **M1 — Identity and access** | UAT-01, UAT-02 | Login, forced password change, session expiry, lockout, staff/admin RBAC, direct-URL denial | E-01–E-04, E-07 | FND-08 per-user approval permission is not implemented; approval is admin-role only. Record as a known gap. |
| **M1 — Administration** | UAT-03, UAT-04, UAT-05 | User lifecycle and guards, settings validation, audit visibility and redaction | E-04, E-07 | Audit append-only trigger is also covered by security tests; UAT checks the UI/API surface. |
| **M2 — Import** | UAT-06, UAT-07 | XLSX multi-sheet, sheet selection, mapping, PDF text, scanned-PDF detection | E-01, E-05, E-08 | Real-sample acceptance remains G2 until approved samples and golden files exist. |
| **M2 — Review and confirmation** | UAT-08–UAT-11 | Row edit/revalidation, bulk exclusion/restore, guardian resolution, ambiguity blocking, confirmation, idempotency, cancellation | E-05, E-08 | Ambiguous-guardian fixture must be prepared and verified before the session. |
| **M3 — Campaign and approval** | UAT-12–UAT-15 | Draft, preview, submit, stale revision, admin approval, snapshot/hash, cancel, results | E-01–E-03, E-06, E-08 | School-approved copy is required for copy acceptance. |
| **M3 — Dashboard** | UAT-19 | Per-currency totals, action queue, activity, trend honesty | E-05, E-08 | No fabricated deltas; snapshot history is not seeded for the test. |
| **M4 — Messages and results** | UAT-16 | History/detail, masking, delivery vs acceptance, unknown outcome, no resend | E-02, E-04, E-08 | Fake provider only; no live delivery claim. |
| **M4 — Provider control plane** | UAT-17 | Fake credential rotation/revoke, test-send allowlist, balance preflight | E-04, E-08 | No real key; live test-send remains blocked. |
| **M4 — Operations** | UAT-18 | Read-only queue/issues view, masked phones, no action controls | E-04, E-08 | Read-only by design; no reconciliation write. |
| **M5 — Privacy and hardening** | UAT-20, UAT-21, UAT-22 | Masking, permissioned preview/download, blocked/error paths, RTL/responsive/accessibility smoke | E-04, E-07, E-09 | H4 retention and H6 DB-role separation are **not** proven by UAT; they remain open. |
| **M5 — Deployment/recovery/monitoring** | Not covered by UI UAT | OPS-04–OPS-07 require separate deployment, backup/restore, alert, and runbook evidence | N/A | Do not infer production readiness from UAT. |

---

## 10. Defect severity and triage

### 10.1 Severity

| Severity | Definition | Examples | Exit effect |
|---|---|---|---|
| **S1 — Critical** | Unsafe, irreversible, or security-critical. Causes data loss/corruption, unauthorised access, PII exposure, wrong-recipient risk, a real send, audit tamper, or total workflow failure. | Full phone/name exposed in a list or evidence; staff approves a campaign; approved totals wrong; confirmation writes partial records; live SMS sent; audit can be edited; app unavailable to all testers. | Stop the session. No acceptance until fixed and retested. |
| **S2 — High** | Major workflow blocked with no acceptable workaround, or a misleading state that could cause a wrong operational decision. | Upload/mapping/confirmation/campaign creation blocked; approval/cancel state inconsistent; missing audit for a mutation; provider acceptance presented as delivery; RBAC allows a restricted screen without data exposure. | No acceptance until fixed and retested, or the scope is formally reduced and the defect remains an open launch blocker. |
| **S3 — Medium** | Workflow impaired but a safe workaround exists; incorrect non-critical count/label; validation message missing while the backend still blocks; accessibility barrier on a secondary task. | Layout overflow at 1024px on a secondary screen; unclear Arabic error; keyboard trap in a non-critical dialog. | Fix or accept with owner, workaround, and target date. |
| **S4 — Low** | Cosmetic or minor inconsistency with no safety or task impact. | Typo, spacing, inconsistent label, non-blocking visual defect. | Triage; may be deferred. |

### 10.2 Triage workflow

1. **Log** — the tester records script ID, step, expected, actual, severity proposal, build, and redacted evidence. Target: before moving to the next script.
2. **Reproduce** — QA confirms reproducibility and checks whether the defect is data-, environment-, or build-specific.
3. **Assess** — QA and Technical Owner agree severity and owner. The School UAT Lead is informed of every S1/S2.
4. **Contain** — for S1, stop the affected workflow, preserve evidence, and apply the approved safety action (stop worker, keep kill switch on, revoke test credential, restrict access). Do not delete evidence.
5. **Fix and retest** — the fix is recorded against a build; QA repeats the original script and a small regression scope; the retest result is attached.
6. **Close or defer** — close only with retest evidence. Defer S3/S4 only with an owner, workaround, target date, and School UAT Lead acceptance.
7. **No silent downgrade** — an S1/S2 may be downgraded only with QA, Technical Owner, and School UAT Lead agreement recorded in the defect log.

### 10.3 Stop conditions

Stop the session and escalate if any of the following occurs:

- Any real SMS, live provider call, or real provider credential use.
- Unauthorised access to admin data or another user's object.
- A full phone, real name, message body, or credential appears in a list view, log, URL, or evidence without approval.
- Wrong recipient, wrong amount, wrong currency, or duplicate send in an approved snapshot.
- Partial confirmation/approval, data loss, or audit tampering.
- The environment is no longer the recorded build or data set.
- A tester is unsure whether an action is safe.

---

## 11. Evidence rules

### 11.1 Required evidence per script

- Script ID, step number, tester, date/time, build/commit, and environment.
- Expected result and actual result, including exact Arabic message or error code where applicable.
- Screenshot or redacted capture for UI behaviour; HTTP status/request ID for API checks; masked row/object IDs for traceability.
- Pass/Fail/Blocked/N/A and defect IDs.

### 11.2 Redaction

- Mask full phone numbers, guardian/student names, emails, addresses, national IDs, account numbers, message bodies containing real data, credentials, tokens, cookies, and API keys.
- Use solid redaction, not reversible blur. Keep enough context to prove the field or behaviour exists.
- For a "full phone is visible in detail/preview" check, use a synthetic number; if approved real data is used, redact the value and record "field present; value redacted".
- Do not capture browser developer tools with cookies, authorization headers, or full API bodies.
- Do not save HAR files, raw database dumps, or unredacted screenshots in the evidence folder.

### 11.3 Storage and access

- Store evidence in the approved secure folder, not in the repository, chat, or personal cloud.
- Use a per-session index with file name, script/step, result, and redaction check.
- Limit access to the named UAT roles; record who accessed the folder.
- Retain redacted evidence per the school's approved retention; delete unredacted originals after redaction.
- If evidence contains PII by mistake, stop, delete it, notify the School UAT Lead and QA, and record the incident.

---

## 12. Execution sequence (proposed)

| Stage | Activity | Output |
|---|---|---|
| 0 | Entry review and authorisation | Signed entry checklist; go/stop decision |
| 1 | Environment/data freeze and dry run | Build record; fixture baseline; dry-run notes (not acceptance) |
| 2 | Session 1 — M1 and M2 | UAT-01–UAT-11 results; defects |
| 3 | Daily triage | Severity agreements; fix queue |
| 4 | Session 2 — M3 and M4 | UAT-12–UAT-18 results; defects |
| 5 | Session 3 — M5 and cross-cutting | UAT-19–UAT-22 results; defects |
| 6 | Retest | Retest record; updated results |
| 7 | Exit review | Coverage, defect status, decision recommendation |
| 8 | Sign-off and disposition | Signed record; data/account cleanup |

Sessions may be combined if the School UAT Lead approves, but each session must have its own metadata, roster, and evidence index.

---

## 13. Sign-off

### 13.1 Decision options

| Decision | Meaning |
|---|---|
| **Accepted** | The agreed UAT scope passed on the recorded build and data set; no open S1/S2; conditions, if any, are closed. |
| **Accepted with conditions** | The scope passed except for listed S3/S4 conditions with owners and dates. No open S1/S2. |
| **Not accepted** | Any open S1/S2, missing mandatory coverage, invalid evidence, or an unmet entry/exit criterion. |

### 13.2 Sign-off table

| Role | Name | Decision | Conditions / comments | Signature | Date |
|---|---|---|---|---|---|
| School UAT Lead |  |  |  |  |  |
| Staff Tester |  |  |  |  |  |
| Admin Tester |  |  |  |  |  |
| Technical Owner |  |  |  |  |  |
| QA |  |  |  |  |  |
| Observer (optional) |  |  |  |  |  |

### 13.3 Sign-off statement

> We confirm that the UAT scope recorded in this plan was executed on the recorded build and data set, with the results and defects in the execution record. We understand that this decision covers UAT only. It is not G5, does not authorise a live SMS or production launch, does not replace G0/G4 evidence, does not close H4/H6, and does not prove production deployment, backup/restore, monitoring, training, or handover readiness.

**If this section is blank or marked NOT EXECUTED, no UAT acceptance exists.**

---

## 14. Explicit blockers (as of 4 November 2026)

These are current blockers to starting formal OPS-08. They are not UAT findings; they are preconditions that do not yet exist.

| ID | Blocker | Current state | UAT impact | Owner | Exit condition |
|---|---|---|---|---|---|
| B-01 | **G0 open** | No approved Rasel sender, no school-controlled Syrian test numbers, no free-text-enabled plan, no 5+ XLSX / 3+ PDF real anonymized samples, and school decisions on currency, approval, retention, opt-out, hosting, and Arabic wording are not signed. | Formal UAT entry (E-01) fails; real/anonymized data, provider acceptance, and copy acceptance are blocked. | School + Provider + Product Owner | Signed G0 record with evidence. |
| B-02 | **G4 open** | No live test-send, no verified provider reconciliation, no controlled pilot. | OPS-08 entry criterion E-02 is unmet; messaging scripts remain fake-only. | Technical Lead + Provider Ops | Signed G4 record. |
| B-03 | **G1 not passed** | FND-08 per-user approval permission is not implemented; FND-15 OpenAPI client/idempotency convention is incomplete; error tracking with PII scrubbing and frontend automated tests are missing; CI has not run on a real repository. | RBAC/approval expectations and API-contract checks may hit known gaps. | Engineering | G1 record or written disposition of each item. |
| B-04 | **G2 not passed** | Real statement samples and golden-file coverage are missing. Import acceptance is synthetic-only. | UAT cannot validate real school XLSX/PDF shapes. | School + QA | Real samples + golden files + G2 record. |
| B-05 | **G3 not passed** | School-approved Arabic template copy is missing; the seeded template is draft copy. | Copy-dependent campaign scripts can test behaviour but not accept wording. | School + Product Owner | Approved template version + G3 record. |
| B-06 | **H4 retention/anonymization open** | No adopted retention policy, purge job, deletion runbook, or school-approved anonymization standard. | A UAT-specific data approval and deletion method must be written; the school must explicitly accept that H4 remains open. | School + Security | Signed retention/anonymization policy and implemented controls, or a written UAT-specific approval with the H4 gap acknowledged. |
| B-07 | **H6 DB-role separation open** | Runtime DB role still owns tables and can disable audit triggers in the current deployment model. | Audit/security acceptance is limited; UAT cannot prove tamper resistance. | DBA + Engineering | Separate migration/runtime roles applied and verified. |
| B-08 | **No approved UAT/staging environment** | No production-like host, TLS, monitoring, alert test, or verified deployment exists. | E-04 is unmet; UAT would run on an unapproved local/dev environment. | DevOps + School | Approved environment record and health/build evidence. |
| B-09 | **No approved data set, accounts, or participants** | No signed data approval, account register, roster, or UAT authorisation. | E-05, E-07, E-10 are unmet. | School UAT Lead + QA | Signed approvals and roster. |
| B-10 | **Ambiguous-guardian fixture missing** | `.local/samples` has no fixture guaranteed to produce `AMBIGUOUS_GUARDIAN`; the training guide records this gap. | UAT-10's ambiguity sub-check is blocked until QA prepares and verifies a synthetic fixture. | QA | Verified synthetic fixture and expected baseline. |
| B-11 | **OCR not implemented; scanned PDF detection only** | Scanned PDFs produce 0 rows and a warning; no OCR execution. | UAT-07 can accept detection only; no scanned-data extraction claim. | Product Owner | Explicit school acceptance of manual handling, or OCR scope decision. |
| B-12 | **No MFA; no provider balance metric** | MFA is not implemented; provider balance has no metric/alert and the fake balance is `unlimited`. | Security and monitoring acceptance are limited; UAT cannot prove MFA or live balance monitoring. | Security + DevOps | School risk acceptance or implementation. |
| B-13 | **Runbooks and recovery not exercised** | Only a local database restore was drilled; uploads/encryption/offsite/production restore and alerts are unverified. | UAT cannot close OPS-04–OPS-07; these require separate evidence. | DevOps + DBA | Executed runbook/recovery evidence. |
| B-14 | **No live provider reconciliation tool** | Unknown outcomes are read-only; no reconciliation or audited correction workflow exists. | UAT-16 can prove "unknown is not failure and is not resent"; it cannot prove resolution. | Engineering + Provider Ops | Reconciliation procedure/tool and G4 evidence. |

---

## 15. References

- `docs/progress.md` — current delivery and gate status.
- `docs/m1/status.md` — foundation implementation and remaining G1 items.
- `docs/m2/verification.md` — synthetic import/review/confirmation evidence.
- `docs/m3/verification.md` — campaign/approval/dashboard evidence.
- `docs/m4/verification.md` — fake-provider messaging/control-plane evidence.
- `docs/m4/load-chaos.md` — fake-provider load/chaos limits.
- `docs/m5/security-review.md` — security findings, masking, H4/H6 status.
- `docs/m5/deployment-readiness.md` — environment, backup, monitoring, runbook limits.
- `docs/m6/training-guide-ar.md` — Arabic UI labels and synthetic exercises.
- `docs/m6/pilot-rehearsal.md` — fake-provider rehearsal boundaries.
- `FeeDesk-Task-Register.csv` — OPS-08 definition and dependencies.
- `docs/m5/uat-scripts.md` — executable scripts.
- `docs/m5/uat-execution-record.md` — blank execution record (**NOT EXECUTED**).

---

**End of plan. No UAT has been executed. No gate is passed.**
