# FeeDesk OPS-08 — UAT Execution Record

**Document ID:** M5-UAT-RECORD-01  
**Version:** 0.1 (blank template)  
**Date:** 4 November 2026  
**Owner:** QA  
**Status:** **NOT EXECUTED — TEMPLATE ONLY**

> **STATUS: NOT EXECUTED.**
>
> This file is a blank execution-record template. **No UAT session has taken place.** No result, defect, retest, acceptance decision, or signature below is real. Do not cite this file as UAT evidence until it is completed, reviewed, and signed in accordance with `uat-plan.md`.
>
> G0 and G4 remain open; G1–G3 are not passed; H4/H6 remain open. Completing this template would not, by itself, close any gate or authorise launch.

### ملخص عربي — Arabic summary

هذا القالب فارغ. **لم تُنفَّذ أي جلسة UAT.** جميع الحقول والنتائج والتواقيع أدناه فارغة. لا يُستخدم هذا الملف كدليل قبول حتى يُكمل ويُوقَّع وفق خطة UAT، ولا يعني التوقيع اجتياز G5 أو السماح بالإطلاق.

---

## 1. How to use this record

- Use one record per UAT session or test day. Give it a unique session ID.
- Complete the metadata and roster before executing any script.
- Record actual results, including failures and blocked steps. Do not overwrite a tester's observation.
- Reference evidence by file name or index ID; never paste PII, credentials, or full phone numbers into this record.
- Copy the result blocks from `uat-scripts.md`; do not change expected results after execution without a documented reason.
- Keep the record and evidence in the approved secure location. Do not store unredacted school data in the repository.
- If the session is not executed, leave the results and decision blank and keep the **NOT EXECUTED** status.

---

## 2. Session metadata

| Field | Value |
|---|---|
| UAT session ID |  |
| Session date |  |
| Start / end time |  |
| Timezone |  |
| Location / mode |  |
| Environment name |  |
| Environment URL |  |
| Build / commit |  |
| API / migration head |  |
| Database (UAT only) |  |
| Provider mode | `fake` / other:  |
| Messaging flags | `MESSAGING_ENABLED=` / `MESSAGING_KILL_SWITCH=` |
| Worker mode | Not running / isolated fake run / other:  |
| Data mode | Approved anonymized real / synthetic fallback |
| Data approval reference |  |
| Data set ID / version |  |
| Copy approval reference |  |
| UAT plan version |  |
| Script version |  |
| Fixture register version |  |
| Evidence folder / index |  |
| Defect tracker reference |  |
| Recorder |  |
| Notes |  |

---

## 3. Participant roster

| Name | Role | Organisation | Access level | Briefing completed | Signature / initials | Conflict / notes |
|---|---|---|---|---|---|---|
|  | School UAT Lead |  |  | ☐ |  |  |
|  | Staff Tester |  |  | ☐ |  |  |
|  | Admin Tester |  |  | ☐ |  |  |
|  | Technical Owner |  |  | ☐ |  |  |
|  | QA |  |  | ☐ |  |  |
|  | Observer |  |  | ☐ |  |  |

**Segregation check:** Staff Tester and Admin Tester are different people: ☐ Yes ☐ No (explain):  
**Observer access is read-only:** ☐ Yes ☐ No ☐ N/A

---

## 4. Entry criteria verification

All mandatory criteria must be **Yes** or have a signed disposition. A "No" on E-01, E-02, E-04, or E-05 stops formal UAT. A "No" on E-06 stops copy acceptance only; affected scripts are recorded as "observed only" and the copy remains a G3/launch blocker.

| ID | Criterion | Status (Yes / No / N/A) | Evidence reference | Verified by | Date |
|---|---|---|---|---|---|
| E-01 | G0 passed |  |  |  |  |
| E-02 | G4 passed |  |  |  |  |
| E-03 | G1–G3 disposition recorded |  |  |  |  |
| E-04 | Approved UAT environment |  |  |  |  |
| E-05 | Approved data set / synthetic approval |  |  |  |  |
| E-06 | Approved copy (or copy acceptance excluded) |  |  |  |  |
| E-07 | Approved accounts |  |  |  |  |
| E-08 | Fixtures and expected baselines |  |  |  |  |
| E-09 | Evidence and defect tooling |  |  |  |  |
| E-10 | Participant readiness and authorisation |  |  |  |  |

**Entry decision:** ☐ Proceed ☐ Stop  
**Reason / conditions:**  
**Authorised by (School UAT Lead):** ______________________  **Date:** __________  
**Authorised by (Technical Owner):** ______________________  **Date:** __________

---

## 5. Session log

| Time | Activity / script | Participants | Notes / interruptions |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |
|  |  |  |  |

---

## 6. Script results

Record one row per script. `Result` is **Pass / Fail / Blocked / N/A**. A blocked script requires an owner and a reason in the notes.

| ID | Title | Priority | Result | Executed by | Date/time | Defect IDs | Evidence ref | Notes |
|---|---|---|---|---|---|---|---|---|
| UAT-01 | Login, forced password change, session expiry, lockout | P1 |  |  |  |  |  |  |
| UAT-02 | Staff/admin RBAC and direct-URL denial | P1 |  |  |  |  |  |  |
| UAT-03 | Admin user management and guards | P1 |  |  |  |  |  |  |
| UAT-04 | School settings validation and audit | P1 |  |  |  |  |  |  |
| UAT-05 | Audit log visibility, labels, redaction | P1 |  |  |  |  |  |  |
| UAT-06 | XLSX upload, sheet selection, mapping, validation | P1 |  |  |  |  |  |  |
| UAT-07 | PDF text extraction and scanned-PDF detection | P1 |  |  |  |  |  |  |
| UAT-08 | Review ledger, row edit, revalidation | P1 |  |  |  |  |  |  |
| UAT-09 | Bulk exclusion and restore | P1 |  |  |  |  |  |  |
| UAT-10 | Guardian resolution and ambiguity blocking | P1 |  |  |  |  |  |  |
| UAT-11 | Confirmation, warnings, idempotency, cancellation | P1 |  |  |  |  |  |  |
| UAT-12 | Campaign draft, recipients, preview | P1 |  |  |  |  |  |  |
| UAT-13 | Submit for approval, stale revision, staff denial | P1 |  |  |  |  |  |  |
| UAT-14 | Admin approval, snapshot, idempotency | P1 |  |  |  |  |  |  |
| UAT-15 | Cancel approved campaign and read results | P1 |  |  |  |  |  |  |
| UAT-16 | Message history/detail, delivery vs acceptance, unknown | P1 |  |  |  |  |  |  |
| UAT-17 | Provider settings (fake), test-send/allowlist, balance | P1 |  |  |  |  |  |  |
| UAT-18 | Operations panel read-only and masked | P1 |  |  |  |  |  |  |
| UAT-19 | Dashboard/trends and per-currency honesty | P2 |  |  |  |  |  |  |
| UAT-20 | Privacy masking and permissioned reveal | P1 |  |  |  |  |  |  |
| UAT-21 | Blocked and error paths | P1 |  |  |  |  |  |  |
| UAT-22 | RTL, responsive, keyboard, screen-reader smoke | P2 |  |  |  |  |  |  |

**Coverage summary:** P1 with result: ___ / 20 (Pass ___, Fail ___, Blocked ___). P2 executed or deferred: ___ / 2.  
**Blocked/deferred P1 reason and approval:**  

---

## 7. Defect log

Do not include PII in a defect title or description. Use masked values, row IDs, and error codes.

| Defect ID | Script / step | Severity (proposed → agreed) | Title | Description / expected vs actual | Reproducible | Build / environment | Evidence ref | Owner | Status | Target fix | Retest |
|---|---|---|---|---|---|---|---|---|---|---|---|
| UAT-D-001 |  |  |  |  | ☐ Yes ☐ No |  |  |  | New / Triaged / In progress / Fixed / Retest / Closed / Deferred |  |  |
| UAT-D-002 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |
| UAT-D-003 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |
| UAT-D-004 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |
| UAT-D-005 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |
| UAT-D-006 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |
| UAT-D-007 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |
| UAT-D-008 |  |  |  |  | ☐ Yes ☐ No |  |  |  |  |  |  |

**Severity summary:** S1 open: ___; S2 open: ___; S3 open: ___; S4 open: ___.  
**Stop condition triggered?** ☐ No ☐ Yes — incident/ref:  

---

## 8. Retest record

| Defect ID | Fix build / commit | Retest date | Retested by | Original script repeated | Result (Pass / Fail) | Regression scope | Evidence ref | Closure approved by |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |  |  |

**Retest notes:**  
**Any fix that changed behaviour outside the defect scope:** ☐ No ☐ Yes (attach analysis)

---

## 9. Data and account disposition

| Item | Required action | Completed (Yes / No / N/A) | Evidence | Verified by |
|---|---|---|---|---|
| UAT data deleted or anonymized per approval | Delete/anonymize; confirm no residual school data |  |  |  |
| Pseudonym mapping key destroyed | Destroy/secure per data approval |  |  |  |
| Staff/admin UAT accounts deactivated | Deactivate; revoke sessions |  |  |  |
| Observer/read-only accounts deactivated | Deactivate |  |  |  |
| Fake provider credential revoked | Revoke; confirm no plaintext remains |  |  |  |
| Worker stopped | Stop isolated worker; confirm no claims |  |  |  |
| Environment reset or retained per approval | Record decision and owner |  |  |  |
| Evidence redacted and stored | Check no PII/secrets; store in approved folder |  |  |  |
| Evidence access list closed | Remove temporary access |  |  |  |
| Fixture register updated | Record actual fixtures/versions used |  |  |  |

**Disposition notes:**  

---

## 10. Acceptance decision

**Decision:**  
☐ Accepted  
☐ Accepted with conditions  
☐ Not accepted  
☐ **NOT EXECUTED** (leave the rest blank)

| Item | Value |
|---|---|
| Tested scope |  |
| Tested build / commit |  |
| Data mode |  |
| P1 coverage |  |
| Open S1 / S2 |  |
| Open S3 / S4 |  |
| Conditions (owner, action, date) |  |
| Rationale |  |
| Known gaps excluded from acceptance |  |
| Follow-up / launch blockers |  |

**Required statements:**

- No open S1 or S2: ☐ Confirmed ☐ Not confirmed
- Evidence complete and redacted: ☐ Confirmed ☐ Not confirmed
- Data/account disposition complete: ☐ Confirmed ☐ Not confirmed
- Copy acceptance included: ☐ Yes ☐ No — if No, copy remains a G3/launch blocker
- Real-data validation included: ☐ Yes ☐ No — if No, G2 real-sample gap remains open
- The decision is UAT only and is **not** G5, launch approval, training delivery, production readiness, or provider verification: ☐ Acknowledged

**If the decision is "Accepted" while any S1/S2 is open, the decision is invalid.**

---

## 11. Signatures

| Role | Name | Decision | Signature | Date |
|---|---|---|---|---|
| School UAT Lead |  |  |  |  |
| Staff Tester |  |  |  |  |
| Admin Tester |  |  |  |  |
| Technical Owner |  |  |  |  |
| QA |  |  |  |  |
| Observer (optional) |  |  |  |  |

**Sign-off statement:**

> We confirm that this record reflects the UAT session identified above, on the recorded build and data set, with the evidence and defects listed. We understand that this sign-off covers UAT only. It is not G5, does not authorise a live SMS or production launch, does not replace G0/G4 evidence, does not close H4/H6, and does not prove production deployment, backup/restore, monitoring, training, or handover readiness.

---

## 12. Attachments and evidence index

| Ref | File / record | Script / step | Redaction checked | Storage location | Notes |
|---|---|---|---|---|---|
|  |  |  | ☐ |  |  |
|  |  |  | ☐ |  |  |
|  |  |  | ☐ |  |  |
|  |  |  | ☐ |  |  |

**Linked records:**

- UAT plan: `docs/m5/uat-plan.md`
- UAT scripts: `docs/m5/uat-scripts.md`
- Fixture register:  
- Data approval:  
- Copy approval:  
- G0 record:  
- G4 record:  
- Build/deployment record:  
- Defect tracker export:  
- Account register:  

---

## 13. Change log

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 4 November 2026 | QA | Initial blank template; **NOT EXECUTED**. |
|  |  |  |  |

---

**End of record. STATUS: NOT EXECUTED. No UAT acceptance exists.**
