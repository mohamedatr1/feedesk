# FeeDesk OPS-08 — UAT Scripts

**Document ID:** M5-UAT-SCRIPTS-01  
**Version:** 0.1  
**Date:** 4 November 2026  
**Owner:** QA  
**Status:** **TEMPLATE — NOT EXECUTED**

> **Status statement — read this first**
>
> These scripts are prepared for a future UAT. **No script has been executed.** Expected results are documented expectations derived from `docs/m1/status.md`, `docs/m2/verification.md`, `docs/m3/verification.md`, `docs/m4/verification.md`, and `docs/m6/training-guide-ar.md`. They are not observed results and do not prove that any gate passed.
>
> Use synthetic fixtures when approved anonymized real data is unavailable. Never use a real guardian number, a real provider key, or a live SMS in these scripts.

### ملخص عربي — Arabic summary

هذه سكربتات اختبار جاهزة للتنفيذ لاحقًا، **ولم تُنفَّذ**. النتائج المتوقعة أدناه هي نتائج موثّقة من مراجع M1–M4 وليست نتائج مرصودة. لا تُستخدم بيانات ولي أمر حقيقية دون موافقة مكتوبة وتجهيل موثّق، ولا يُرسل أي SMS حقيقي؛ استخدم المزوّد الوهمي والبيانات الاصطناعية عند غياب البيانات المعتمدة.

---

## 1. How to use these scripts

1. Read `uat-plan.md` §6 (entry criteria) and §8 (environment/data policy) first. Do not start if a mandatory entry criterion is unmet.
2. Confirm the fixture baseline in §3 against the approved UAT build. If a fixture or expected count differs, record the difference and stop that script until QA updates the baseline.
3. Execute one script at a time. Record the actual result even when it differs from the expected result.
4. For each step, capture redacted evidence and note the exact Arabic message or error code.
5. Complete the result block at the end of each script. "Blocked" requires a reason, owner, and expected unblock date; it is not a pass.
6. Copy the results into `uat-execution-record.md`. Do not treat this script file as the execution record.

### 1.1 Result codes

| Code | Meaning |
|---|---|
| **Pass** | All steps met the expected result, or a difference is explicitly accepted as non-defect with a note. |
| **Fail** | One or more steps did not meet the expected result and a defect is logged. |
| **Blocked** | The script could not be executed because a documented precondition, fixture, environment, or gate is missing. |
| **N/A** | The step or script does not apply to the approved scope; the reason is recorded. |

### 1.2 Evidence rules

- Mask full phone numbers, guardian/student names, emails, addresses, IDs, message bodies with real data, credentials, tokens, and cookies.
- Use solid redaction, not reversible blur. Prefer synthetic data.
- Record the build/commit, environment, tester, date/time, and script/step in the evidence index.
- Do not capture API bodies containing PII; record field names and status codes instead.
- Do not store evidence in the repository, chat, or personal cloud. Use the approved secure folder.

---

## 2. Common preconditions

Unless a script says otherwise:

- The UAT environment is approved, access-restricted, and separate from production.
- The build/commit and migration head are recorded.
- `MESSAGING_PROVIDER=fake`; live sending is blocked; kill switch is on by default.
- Staff and admin UAT accounts are active, separate, and have completed forced password change.
- The approved fixture register and expected baselines are available.
- The evidence folder, redaction method, and defect tracker are ready.
- No real guardian/student data is present unless the written data approval covers it and anonymization is verified.

---

## 3. Fixture baseline

These baselines are from the synthetic verification records and training guide. Re-verify them on the UAT build before scoring.

| ID | Fixture | Source / sheet | Expected baseline | Used by |
|---|---|---|---|---|
| F1 | `sample-01-multi-sheet.xlsx` | `.local/samples/xlsx/`; sheet **الفصل الأول** | 7 rows; 1 negative-balance blocking row; 1 missing-phone row; totals **SYP 2,600,000.00 + USD 400.00** | UAT-06, UAT-08, UAT-09, UAT-10 |
| F2 | `sample-02-arabic-digits.xlsx` | `.local/samples/xlsx/`; sheet **بيانات** | 4 rows; 3 eligible recipients; 1 `ZERO_BALANCE` exclusion; totals **SYP 573,456.00 + USD 200.00** | UAT-06 (optional), UAT-12 (alternative) |
| F3 | `sample-03-messy-headers.xlsx` | `.local/samples/xlsx/`; sheet **كشف ملخبط** | 3 sheets; headers detected after leading blank rows; 4 rows staged | UAT-06 (optional) |
| F4 | `sample-01-text-table.pdf` | `.local/samples/pdf/` | 6 rows; 1 negative-balance row; page references; totals **SYP 1,600,000.00 + USD 400.00** | UAT-07 |
| F5 | `sample-02-scanned-image.pdf` | `.local/samples/pdf/` | 0 rows; `SCANNED_PDF` warning; no invented rows; cannot confirm | UAT-07, UAT-21 |
| F6 | `m3-campaign-sample.xlsx` or approved equivalent | Confirmed synthetic import used by M3 verification | 2 eligible recipients; 2 exclusions (`ZERO_BALANCE`, `MISSING_PHONE`); **SYP 1,100,000.00**; `SHARED_PHONE=2` | UAT-12–UAT-16 |
| F7 | Ambiguous-guardian fixture | QA-prepared; **not currently in `.local/samples`** | More than one candidate for a row; auto-link disabled; confirmation blocked with `AMBIGUOUS_GUARDIAN` | UAT-10, UAT-21 |
| F8 | Invalid/duplicate files | QA-prepared | Unsupported type, empty file, MIME mismatch, oversized file, XLSX archive-limit file, duplicate of F1 | UAT-21 |
| F9 | Fake-provider allowlist numbers | UAT test-number register; synthetic/reserved only | Two approved test numbers T1/T2; one non-allowlisted number T3 | UAT-17 |
| F10 | Fake timeout/unknown scenario | Technical Owner-prepared synthetic campaign | At least one message reaches `unknown`; one send attempt; no re-claim or resend | UAT-16 |

> If `.local/samples` is not present on the UAT workstation, QA prepares equivalent synthetic fixtures and attaches the expected baseline before execution. Do not substitute real school data.
>
> If an approved anonymized real fixture replaces a synthetic one, attach its approved expected baseline and update the fixture register before execution. Do not reuse a synthetic expected count for a different file.

---

## 4. Script index

| ID | Title | Milestone | Priority | Data |
|---|---|---|---|---|
| UAT-01 | Login, forced password change, session expiry, lockout | M1 | P1 | UAT accounts |
| UAT-02 | Staff/admin RBAC and direct-URL denial | M1 | P1 | UAT accounts; F6 |
| UAT-03 | Admin user management and guards | M1 | P1 | Disposable account |
| UAT-04 | School settings validation and audit | M1 | P1 | Reversible test values |
| UAT-05 | Audit log visibility, labels, redaction | M1 | P1 | Events from UAT-03/04 |
| UAT-06 | XLSX upload, sheet selection, mapping, validation | M2 | P1 | F1, F3 optional |
| UAT-07 | PDF text extraction and scanned-PDF detection | M2 | P1 | F4, F5 |
| UAT-08 | Review ledger, row edit, revalidation | M2 | P1 | F1 batch |
| UAT-09 | Bulk exclusion and restore | M2 | P1 | F1 batch |
| UAT-10 | Guardian resolution and ambiguity blocking | M2 | P1 | F1/F6; F7 |
| UAT-11 | Confirmation, warnings, idempotency, cancellation | M2 | P1 | F1/F4 batch |
| UAT-12 | Campaign draft, recipients, preview | M3 | P1 | F6 or F2 |
| UAT-13 | Submit for approval, stale revision, staff denial | M3 | P1 | UAT-12 draft |
| UAT-14 | Admin approval, snapshot, idempotency | M3 | P1 | UAT-13 campaign |
| UAT-15 | Cancel approved campaign and read results | M3/M4 | P1 | UAT-14 campaign |
| UAT-16 | Message history/detail, delivery vs acceptance, unknown | M4 | P1 | Fake-delivered + F10 |
| UAT-17 | Provider settings (fake), test-send/allowlist, balance | M4 | P1 | F9 |
| UAT-18 | Operations panel read-only and masked | M4 | P1 | Fake worker data |
| UAT-19 | Dashboard/trends and per-currency honesty | M3 | P2 | Confirmed imports |
| UAT-20 | Privacy masking and permissioned reveal | M5 | P1 | F6; staff/admin; QA API |
| UAT-21 | Blocked and error paths | M2–M5 | P1 | F5, F8, F9; disposable account |
| UAT-22 | RTL, responsive, keyboard, screen-reader smoke | M1–M5 | P2 | Any approved pages |

---

## 5. Scripts

### UAT-01 — Login, forced password change, session expiry, lockout

**Covers:** M1; OPS-08.  
**Priority:** P1.  
**Preconditions:** E-01–E-04 and E-07 met; staff test account with a temporary password; one disposable lockout account; admin account; lockout threshold recorded by the Technical Owner.  
**Test data:** UAT accounts only. Never record a password.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open the UAT login URL in a fresh browser profile. | Arabic RTL login appears with username/password fields; no password is prefilled; no production claim. | Screenshot of login; URL/build. |
| 2 | Enter the staff username and a wrong password; submit. | Generic Arabic error; no indication whether the username exists; failed-login audit event. | Screenshot; audit event ID. |
| 3 | Enter the correct temporary password; submit. | Forced password-change screen appears before any dashboard or data screen. | Screenshot. |
| 4 | Enter an 11-character new password. | Rejected with the 12-character rule; no save. | Screenshot of validation. |
| 5 | Enter two different valid passwords. | Mismatch error; no save. | Screenshot. |
| 6 | Enter a valid 12+ character new password and save. | Password saved; forced-change flag cleared; authenticated screen available. | Screenshot of success; no password visible. |
| 7 | Log out, then use the browser Back button. | Login screen remains; no authenticated data is restored from cache. | Screenshot. |
| 8 | Log in with the new password. | Dashboard or landing page loads. | Screenshot. |
| 9 | Expire the session (QA/Technical Owner method) and click a protected action. | Session-expired message and redirect to login; no partial mutation. | Screenshot; request ID. |
| 10 | On the disposable account, submit wrong passwords to the recorded threshold. Then try the correct password. | Lockout message; correct password still blocked during lockout; lockout audit event; admin reset/unlock path works. Do not lock the main test accounts. | Screenshot; audit event ID; no password. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-02 — Staff/admin RBAC and direct-URL denial

**Covers:** M1; M5 privacy boundary.  
**Priority:** P1.  
**Preconditions:** Staff and admin accounts; a campaign awaiting approval (F6 or UAT-13); QA available for the API check.  
**Test data:** F6; UAT accounts.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, inspect the sidebar. | No Users, Operations, Audit, or Provider settings entries; Settings is visible but read-only. | Screenshot of sidebar. |
| 2 | As staff, open `/settings/users` directly. | Access denied (403 or safe redirect); no user list or PII. | Screenshot; status/request ID. |
| 3 | As staff, open `/operations` directly. | Access denied; no queue or provider data. | Screenshot; status. |
| 4 | As staff, open `/audit` directly. | Access denied; no audit rows. | Screenshot; status. |
| 5 | As staff, open a campaign awaiting approval. | No approve button; notice that approval is available to the system administrator only (`الاعتماد متاح لمدير النظام`). | Screenshot. |
| 6 | QA calls the approve endpoint with the staff session and a valid CSRF token. | `403`; campaign state unchanged; no messages/jobs created. | Status code; request ID; before/after state. |
| 7 | Staff attempts a settings save via UI and, if available, API. | Read-only/`403`; no change; no audit mutation claiming success. | Screenshot/status. |
| 8 | Log in as admin. | Users, Settings, Audit, Operations, and Provider settings are available. | Screenshot. |
| 9 | If an observer/read-only account exists, log in and repeat steps 1–4. | Read-only or denied consistently with the approved role. | Screenshot. |

**Known gap:** FND-08 per-user approval permission is not implemented. Approval is admin-role only. Record this as a known gap, not as a new defect, unless the school's approved requirement makes it a UAT blocker.

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-03 — Admin user management and guards

**Covers:** M1.  
**Priority:** P1.  
**Preconditions:** Admin account; at least two active admins or a documented last-admin condition; one disposable staff account.  
**Test data:** Synthetic usernames only; temporary passwords delivered securely.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Admin opens Settings → Users. | User list shows username, role, status, job title/email where applicable; no passwords. | Screenshot with synthetic data. |
| 2 | Create a staff user with a 12+ character temporary password, role, and optional job title. | User created; temporary password shown once; create audit event. | Screenshot without password; audit ID. |
| 3 | Log in as the new user. | Forced password change before access. | Screenshot. |
| 4 | As admin, edit role, email, and job title; save. | Changes persist; update audit event. | Screenshot; audit ID. |
| 5 | Reset the user's password. | Temporary password shown once; existing sessions revoked; reset audit event. | Screenshot without password; old-session check. |
| 6 | Deactivate the user. | Login blocked; sessions revoked; deactivate audit event. | Screenshot; audit ID. |
| 7 | Reactivate the user. | Login possible after the required password change. | Screenshot. |
| 8 | Try to deactivate the currently signed-in admin. | Blocked with an Arabic guard message; no state change. | Screenshot. |
| 9 | Try to demote or deactivate the last active admin. | Blocked; no state change. | Screenshot. |
| 10 | Try to create a username that differs only by case from an existing one. | Rejected as a duplicate; no second account. | Screenshot. |
| 11 | Clean up: deactivate the disposable user; confirm no password appears in evidence. | Account deactivated; evidence clean. | Screenshot; evidence check. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-04 — School settings validation and audit

**Covers:** M1.  
**Priority:** P1.  
**Preconditions:** Admin and staff accounts; original settings recorded; approval to change and restore test values.  
**Test data:** Reversible test values only; restore the original values before leaving the script.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, open Settings. | Read-only; no save control; values visible. | Screenshot. |
| 2 | As admin, open Settings. | Editable school name, ISO currency, display symbol, IANA timezone, locale, contact phone/email, send/batch limits. | Screenshot. |
| 3 | Enter an invalid currency (for example `SY`) and save. | Validation error; no save. | Screenshot. |
| 4 | Enter an invalid timezone (for example `Damascus`) and save. | Validation error; no save. | Screenshot. |
| 5 | Enter a limit outside 1–10000 and save. | Validation error; no save. | Screenshot. |
| 6 | Save valid test values (school name suffix, valid ISO currency, valid IANA timezone, valid limits). | Save succeeds; settings persist; audit event records before/after without secrets. | Screenshot; audit ID. |
| 7 | Verify the currency and school name appear consistently in the UI. | No fabricated currency fallback; no combined currency. | Screenshot. |
| 8 | Restore the original settings; save. | Restore succeeds; audit event. | Screenshot; audit ID. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-05 — Audit log visibility, labels, redaction

**Covers:** M1; M5.  
**Priority:** P1.  
**Preconditions:** Admin and staff accounts; audit events from UAT-03 and UAT-04; at least one event with a phone-like field (for example a row edit or import event).  
**Test data:** Existing UAT events only.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, open `/audit` directly. | Access denied; no rows. | Screenshot; status. |
| 2 | As admin, open Audit. | Latest 25 events with total and Refresh; no edit/delete controls. | Screenshot. |
| 3 | Verify the user create/update/reset/deactivate and settings events from UAT-03/04. | Correct actor, action, entity, timestamp, and ID disclosure. | Screenshot; event IDs. |
| 4 | Inspect an event payload or detail. | No secrets, passwords, tokens, or full request bodies; phone-like fields masked. | Screenshot/field notes; no PII. |
| 5 | Try to find an edit/delete action. | No such control or endpoint; the log is read-only. | Screenshot; optional API check. |
| 6 | QA confirms the append-only trigger separately if in scope for the security evidence. | UAT does not attempt a direct DB tamper test; record the separate evidence reference. | Security evidence reference. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-06 — XLSX upload, sheet selection, mapping, validation

**Covers:** M2.  
**Priority:** P1.  
**Preconditions:** Staff account; F1; optional F3; no duplicate of F1 or a known duplicate for the duplicate sub-check.  
**Test data:** F1, F3.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open Statements → New upload. | Allowed types are `.xlsx` and PDF; size limit shown; empty/unsupported type is rejected. | Screenshot. |
| 2 | Upload F1. | Uploaded screen appears with status/counts and the sheet list; the app does **not** auto-open review. | Screenshot. |
| 3 | Open sheet selection. | No sheet is selected automatically; the list shows the workbook's sheets. | Screenshot. |
| 4 | Select **الفصل الأول** and continue. | Mapping screen appears for the selected sheet. | Screenshot. |
| 5 | Review the mapping fields: guardian name, phone, student name, total, paid, remaining, currency, period. | Required fields are guardian name, remaining, currency; auto-suggestions are present and editable. | Screenshot. |
| 6 | Try to use the same column for two fields. | Rejected: the same column cannot be used twice. | Screenshot. |
| 7 | Extract records. | Rows are staged; summary shows counts and per-currency totals. | Screenshot. |
| 8 | Open review. | 7 rows; 1 negative-balance blocking row; 1 missing-phone row; totals **SYP 2,600,000.00 + USD 400.00**; source row references present. | Screenshot; row IDs. |
| 9 | Re-upload F1 to test duplicates. | Duplicate dialog appears with "open previous import"; override without reason is rejected (`DUPLICATE_REASON_REQUIRED`); with a reason it succeeds and writes audit. | Screenshots; audit ID. |
| 10 | Optional: upload F3 and select **كشف ملخبط**. | Three sheets are listed; headers are detected after leading blank rows; 4 rows staged. | Screenshot. |
| 11 | Optional: upload F2 and select **بيانات**. | Arabic-Indic digits and `ل.س` are normalized; 4 rows; 3 eligible; 1 zero-balance row; totals **SYP 573,456.00 + USD 200.00**. | Screenshot. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-07 — PDF text extraction and scanned-PDF detection

**Covers:** M2.  
**Priority:** P1.  
**Preconditions:** Staff account; F4; F5.  
**Test data:** F4, F5.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Upload F4. | Status `review_required`; 6 rows; 1 negative-balance row; totals **SYP 1,600,000.00 + USD 400.00**. | Screenshot. |
| 2 | Open review and inspect source references. | Each row shows a page reference (and row where available); no invented source. | Screenshot. |
| 3 | Upload F5 (scanned image PDF). | 0 rows; `SCANNED_PDF` warning; no invented rows; confirmation is not possible. | Screenshot. |
| 4 | Confirm the OCR boundary. | The UI explains that scanned PDFs are detected, not read automatically; no OCR claim. | Screenshot/notes. |
| 5 | If F4 extraction fails, log a defect. | Do not manually add rows or edit the PDF to force a pass. | Defect entry. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-08 — Review ledger, row edit, revalidation

**Covers:** M2.  
**Priority:** P1.  
**Preconditions:** An unconfirmed F1 batch from UAT-06; staff account; approved synthetic valid phone for the correction step.  
**Test data:** F1 batch; synthetic valid phone from the UAT test-number register.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open the review ledger. | Counts for total, valid, warnings, errors, duplicates, excluded; status filter and search are present. | Screenshot. |
| 2 | Verify the bottom bar. | `للاستيراد N · مستثناة N · تحذيرات N`; per-currency totals; no combined-currency total. | Screenshot. |
| 3 | Open the negative-balance row and try to save it as negative. | Blocking balance error; cannot save as valid. | Screenshot. |
| 4 | Change the remaining balance to `0` and save. | Revalidation runs; a `TOTAL_DISCREPANCY` warning/error appears as documented; success message "تم تحديث السجل وأُعيد التحقق منه." | Screenshot. |
| 5 | With an unsaved edit, change the filter or page. | Blocked with "احفظ التعديل أو ألغِه أولًا." | Screenshot. |
| 6 | Open a row with an invalid phone; correct it to the approved synthetic valid number; save. | `INVALID_PHONE` clears; row remains editable; original value line shows the prior value. | Screenshot; row ID. |
| 7 | Verify source reference, currency, and totals. | Source page/row remains; currencies remain separate; totals update consistently. | Screenshot. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-09 — Bulk exclusion and restore

**Covers:** M2.  
**Priority:** P1.  
**Preconditions:** A review batch with at least one invalid row; staff account.  
**Test data:** F1 batch from UAT-06/08.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Select one invalid row; choose **استثناء المحدد**; confirm. | Row excluded; counts update; one audit event for the bulk action. | Screenshot; audit ID. |
| 2 | Filter to excluded; select the row; choose **استعادة المحدد**; confirm. | Row restored; counts update; one audit event. | Screenshot; audit ID. |
| 3 | Choose **استثناء الصفوف غير الصالحة (N)**. | Dialog explains that the action covers the whole statement, not only the current page. | Screenshot. |
| 4 | Confirm the bulk exclusion. | All invalid rows in the statement are excluded; counts update; one audit event. | Screenshot; audit ID. |
| 5 | Change page, filter, or search. | The selection is cleared; no hidden selection carries over. | Screenshot. |
| 6 | Verify the excluded row text. | "سجل مستبعد — لا يمنع التأكيد"; it does not block confirmation. | Screenshot. |
| 7 | Restore the excluded rows. | Counts return to the pre-exclusion values; one audit event. | Screenshot; audit ID. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-10 — Guardian resolution and ambiguity blocking

**Covers:** M2.  
**Priority:** P1.  
**Preconditions:** A batch with candidate rows; F7 ambiguous fixture prepared and verified by QA; staff account.  
**Test data:** F1/F6; F7.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open **تحديد ولي الأمر** for a row with candidates. | Dialog shows guardian name, masked phone, match type (exact/name/shared/ambiguous/manual), and selection method. | Screenshot with masked phone. |
| 2 | Choose **ربط تلقائي** where exactly one clear candidate exists; save. | Row links to the candidate; success message; audit event. | Screenshot; row ID. |
| 3 | Choose **ربط ولي أمر موجود**, select a candidate, and save. | Row links to the chosen existing guardian; masked phone and match type remain visible; audit. | Screenshot. |
| 4 | Choose **إنشاء ولي أمر جديد** and save. | A new guardian is created from the row data; row updates; audit. | Screenshot; row ID. |
| 5 | Open an ambiguous row (more than one candidate). | Auto-link is disabled; the row is marked ambiguous. | Screenshot. |
| 6 | Attempt confirmation without resolving the ambiguous row. | `409 AMBIGUOUS_GUARDIAN`; dialog "لم يتم تأكيد الاستيراد." with affected-row count and "عرض الأسطر المتأثرة"; no partial writes. | Screenshot; status/error code; before/after counts. |
| 7 | Resolve every affected row via link-existing or create-new; re-confirm. | Confirmation proceeds only after all ambiguous rows are resolved. | Screenshot. |
| 8 | Verify same-name/different-phone rows and shared-phone rows. | No name-only merge; shared phone warns but does not auto-merge. | Screenshot/notes. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-11 — Confirmation, warnings, idempotency, cancellation

**Covers:** M2.  
**Priority:** P1.  
**Preconditions:** A batch with warnings but no blocking errors; a separate unconfirmed batch to cancel; staff account; QA for the idempotency check.  
**Test data:** F1/F4 batch; separate F1 batch.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Review the bottom bar and currency totals. | Counts and totals match the review ledger; currencies are separate. | Screenshot. |
| 2 | Try to confirm without acknowledging warnings. | Blocked/disabled; `WARNINGS_UNACKNOWLEDGED` if attempted. | Screenshot/status. |
| 3 | Select the acknowledgment "راجعت التحذيرات وأفهم أن السجلات ستُستورد كما هي." and confirm. | Final dialog summarizes counts/warnings; confirmation is described as final. | Screenshot. |
| 4 | Confirm with "تأكيد وإنشاء السجلات". | Banner "تم تأكيد الاستيراد. الأسطر المؤكدة: N. السجلات للعرض فقط."; status confirmed. | Screenshot. |
| 5 | Verify the confirmed detail. | Totals and included counts match; no edit/exclude/cancel; no campaign/message created automatically. | Screenshot; counts. |
| 6 | QA repeats confirmation/idempotency on the same batch. | No duplicate records; idempotent response; no second set of guardians/balances. | Status; DB/API counts; request ID. |
| 7 | On the separate batch, cancel before confirmation (enter a reason if the build requires one). | Status cancelled; no financial records; statement retained; audit. | Screenshot; audit ID. |
| 8 | Try to confirm a batch with blocking errors. | `409 BLOCKING_ROWS`; row IDs returned; no partial write. | Status; row IDs; before/after counts. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-12 — Campaign draft, recipients, preview

**Covers:** M3.  
**Priority:** P1.  
**Preconditions:** A confirmed import (F6 recommended; F2 alternative); active approved template; staff account.  
**Test data:** F6 baseline: 2 recipients, 2 exclusions, **SYP 1,100,000.00**, `SHARED_PHONE=2`. F2 baseline: 3 recipients, 1 `ZERO_BALANCE`, **SYP 573,456.00 + USD 200.00**. Use the approved baseline for the chosen fixture.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open Campaigns → New. | Only confirmed imports are offered. | Screenshot. |
| 2 | Select the confirmed import, enter a campaign name, select the active template. | Readiness checklist shows import selected, name valid, template selected. | Screenshot. |
| 3 | Create the draft. | Draft is created; "أُنشئت المسودة. راجع المستلمين والمبالغ قبل الإرسال للاعتماد."; no send. | Screenshot. |
| 4 | Review recipients, exclusions, warnings, and totals. | Masked phones; recipient count and exclusion reasons; `SHARED_PHONE` warning if present; per-currency totals. | Screenshot. |
| 5 | Open **معاينة الرسالة** for one recipient. | Full synthetic phone, rendered body, amount/currency, classes/students, count of balances, character count; Previous/Next work; close. | Screenshot with synthetic value. |
| 6 | Verify the recipient table. | No full phones; no send/resend control; no unresolved variables. | Screenshot/notes. |
| 7 | Edit the draft name or template; save. | Revision increments; preview recalculates; the source import cannot be changed. | Screenshot; revision. |
| 8 | Optional: use a template with an unknown variable. | Draft may be created, but submit/approval is blocked with `UNRESOLVED_VARIABLES`. | Screenshot; error code. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-13 — Submit for approval, stale revision, staff denial

**Covers:** M3.  
**Priority:** P1.  
**Preconditions:** A draft from UAT-12; staff and admin accounts; QA/second session for the stale-revision check.  
**Test data:** UAT-12 draft.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, open the draft and choose **إرسال للاعتماد**. | Dialog explains that recipients will be recalculated from the confirmed import before submission. | Screenshot. |
| 2 | Review the summary/warnings and submit. | Status `awaiting_approval`; "أُرسلت الحملة للاعتماد." | Screenshot. |
| 3 | As staff, inspect the approval area. | Notice "الاعتماد متاح لمدير النظام."; no approve control. | Screenshot. |
| 4 | In a second session, edit the draft revision; then submit from the stale first session. | `409 CAMPAIGN_CHANGED`; message "تغيّرت الحملة منذ فتحها..."; page refreshes; no submission with the stale revision. | Status/error code; screenshot. |
| 5 | Verify no messages or jobs exist before approval. | `message_count=0`/no messages; no provider call; no send. | Screenshot/API counts. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-14 — Admin approval, snapshot, idempotency

**Covers:** M3.  
**Priority:** P1.  
**Preconditions:** A campaign awaiting approval with at least one warning; admin and staff accounts; QA for the staff-approval API check.  
**Test data:** UAT-13 campaign.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As admin, open the campaign. | Approve control is available; warning list is visible. | Screenshot. |
| 2 | Open the approval dialog. | Explains immutable snapshot, no send, and one message/job per recipient; warning acknowledgment is required. | Screenshot. |
| 3 | Try to approve without acknowledging warnings. | Button disabled or `422 WARNINGS_UNACKNOWLEDGED`; no approval. | Screenshot/status. |
| 4 | Acknowledge and approve. | Status `approved`; 64-character SHA-256 snapshot hash; frozen recipients/exclusions/warnings; `message_count` and `pending_job_count`; "لم تُرسل أي رسالة." | Screenshot; hash; counts. |
| 5 | QA calls approve as staff. | `403`; no state change. | Status; before/after state. |
| 6 | Re-approve the same campaign. | Idempotent: no duplicate messages/jobs; same snapshot. Record any additional audit event, but do not treat it as a defect unless it implies a second approval or creates data. | Screenshot; counts; audit. |
| 7 | Verify counts. | Approved recipients = messages = jobs; 0 provider events; 0 sends. | API/DB counts; request ID. |
| 8 | Try to edit an approved recipient. | No edit control; backend/database immutability is covered by security evidence. | Screenshot; reference. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-15 — Cancel approved campaign and read results

**Covers:** M3/M4.  
**Priority:** P1.  
**Preconditions:** An approved campaign with pending messages (worker not run); admin account.  
**Test data:** UAT-14 campaign, or a separate approved synthetic campaign.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open the approved campaign; choose **إلغاء الحملة**. | Reason is required; dialog explains the effect. | Screenshot. |
| 2 | Enter a reason and confirm. | Status `cancelled`; reason retained; approved snapshot/hash retained; pending messages/jobs cancelled. | Screenshot; counts. |
| 3 | Verify terminal outcomes are not overwritten. | Any delivered/failed/unknown message remains as-is; only non-terminal messages are cancelled. | Screenshot/API counts. |
| 4 | Open **نتائج الرسائل**. | Campaign status cancelled; counts include cancelled; delivery caveat; no progress bar or percentage. | Screenshot. |
| 5 | Verify no send/resend control. | None in any state. | Screenshot. |
| 6 | If a processing/completed campaign is available, repeat cancellation. | Behaviour matches the documented state rules; record any difference. | Screenshot; defect if unsafe. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-16 — Message history/detail, delivery vs acceptance, unknown

**Covers:** M4.  
**Priority:** P1.  
**Preconditions:** A fake-provider campaign processed with the `delivered` scenario; if available, a message in `provider_accepted`/`queued_by_provider`; F10 timeout/unknown campaign prepared by the Technical Owner; staff and admin accounts.  
**Test data:** Fake-delivered campaign; F10; existing synthetic accepted/queued messages if retained.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, open **سجل الرسائل**. | Read-only notice "عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي."; filters by campaign/status; search; masked phones; provider reference; last update. | Screenshot. |
| 2 | Filter to delivered and search for a synthetic guardian/phone. | Results filter correctly; the full phone is not exposed in the list or URL. | Screenshot; URL/field notes. |
| 3 | Open a delivered message detail. | Frozen body; full synthetic destination; campaign; amount/currency; SMS channel; status; provider request/message IDs; attempts; redacted payload; no resend. | Screenshot with synthetic value. |
| 4 | Open a `provider_accepted` or `queued_by_provider` message, if available. | Explanation that provider acceptance/queueing is not delivery; not counted as delivered. | Screenshot. |
| 5 | Open an `unknown` message (F10). | Explanation "انتهت المحاولة دون رد واضح..."; no resend; no auto-retry; status remains unknown. | Screenshot. |
| 6 | Open campaign results. | Counts separated: total, pending, awaiting delivery confirmation (`submitting`+`provider_accepted`+`queued_by_provider`), delivered, needs review (`failed`+`unknown`), cancelled; no progress bar. | Screenshot. |
| 7 | Verify `completed` semantics. | "اكتملت المعالجة" does not mean all messages delivered; a campaign with failed/unknown shows the documented aggregate status. | Screenshot/notes. |
| 8 | Technical Owner runs the fake timeout scenario for F10 once. | Message/job reach `unknown`; one send attempt; not re-claimed; no resend; no duplicate. | Worker output; counts; audit. |
| 9 | QA attempts the resend endpoint / looks for a resend control. | No control; endpoint `404`; nothing is sent. | Status; screenshot. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-17 — Provider settings (fake), test-send/allowlist, balance

**Covers:** M4.  
**Priority:** P1.  
**Preconditions:** Admin account; fake provider; allowlist configured with T1/T2; T3 non-allowlisted; no live provider credential.  
**Test data:** F9; fake credential value; synthetic message text.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open Settings → Provider. | Status shows provider/channel/sender/key version/test mode; live sending is blocked; no plaintext key. | Screenshot. |
| 2 | Rotate the credential with a fake API key and sender ID. | Save succeeds; `key_version` increments; key is never shown again; audit event masks the secret. | Screenshot; audit ID. |
| 3 | Revoke the credential; confirm. | Credential revoked; test-send/balance disabled until a new key; audit event. | Screenshot; audit ID. |
| 4 | Save a fake credential again for the test-send. | Status configured; live sending still blocked. | Screenshot. |
| 5 | Test-send to T1 with a short synthetic message. | Fake/dry-run result; "محاكاة — لم تُرسل رسالة فعلية"; masked recipient; provider message ID; time; no real SMS. | Screenshot; audit ID. |
| 6 | Test-send to T3 (not allowlisted). | `RECIPIENT_NOT_ALLOWLISTED`; no send. | Screenshot/status. |
| 7 | If the allowlist is empty in an isolated approved config, test-send. | `ALLOWLIST_REQUIRED`; no send. Do not remove the shared allowlist without Technical Owner approval. | Screenshot/status. |
| 8 | Open balance. | Fake: `unlimited`, currency `SMS`, preflight success; note that this is simulated. | Screenshot. |
| 9 | Do **not** switch to a non-fake provider. If the environment is already non-fake, stop and escalate. | Expected blocked behaviour: `LIVE_TEST_SEND_BLOCKED` / `live_provider_blocked`; no network call. | Screenshot/status; incident note. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-18 — Operations panel read-only and masked

**Covers:** M4.  
**Priority:** P1.  
**Preconditions:** Admin and staff accounts; fake worker run or queued jobs; a campaign with delivered/unknown data if available.  
**Test data:** Fake-provider queue; F10 optional.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, open `/operations` directly. | Access denied; no queue/provider data. | Screenshot; status. |
| 2 | As admin, open Operations. | Provider status strip; queue now; due/stale; failed/unknown/reconciliation; provider events; Refresh. | Screenshot. |
| 3 | Inspect phone values. | Masked only; no full phones. | Screenshot. |
| 4 | Inspect job/message details. | No message bodies, credentials, claim tokens, or secrets. | Screenshot/field notes. |
| 5 | Look for actions. | No resend, reschedule, retry, or status-correction controls; only Refresh. | Screenshot. |
| 6 | Cross-check counts with messages/results for the same campaign. | Counts agree within the documented status definitions; no fabricated progress. | Screenshot/notes. |
| 7 | Verify the unknown notice. | "النتيجة غير المعروفة ليست فشلًا." | Screenshot. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-19 — Dashboard/trends and per-currency honesty

**Covers:** M3.  
**Priority:** P2.  
**Preconditions:** Confirmed imports/campaigns; dashboard data; no seeded fake snapshots unless approved; staff and admin accounts.  
**Test data:** Approved confirmed imports; dashboard reconciliation sheet prepared by QA.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | Open the dashboard as staff. | Per-currency totals; counts; action queue; recent activity; no combined-currency total. | Screenshot. |
| 2 | Cross-check totals with the confirmed imports. | Totals match the approved reconciliation sheet; no browser-side calculation. | Screenshot + reconciliation. |
| 3 | Open the trends area. | If insufficient snapshots: "تظهر الاتجاهات بعد توفر لقطات كافية." If snapshots exist: per-currency deltas only; no fabricated 0%/arrow. | Screenshot. |
| 4 | Verify the activity link. | Admin-only audit link; staff does not see an admin link. | Screenshot. |
| 5 | Inspect the provider channel card. | Informational "development/fake" state, not a live provider status; no claim of real sending. | Screenshot. |
| 6 | Refresh and re-check. | Numbers remain stable unless data changed; no flicker to a fabricated value. | Screenshot. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-20 — Privacy masking and permissioned reveal

**Covers:** M5; M1/M3/M4 privacy.  
**Priority:** P1.  
**Preconditions:** Staff and admin accounts; F6 campaign/messages; a synthetic full phone; QA for API checks; a file/import object owned by another test user if object isolation is in scope.  
**Test data:** F6; synthetic phone; UAT file IDs.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | As staff, open the statements list. | No full phone/name exposure in list columns or search results. | Screenshot masked. |
| 2 | Open campaign detail. | Recipient table uses masked phones; no full phones, student names, or rendered bodies; preview is permission-gated. | Screenshot. |
| 3 | Open message history and operations (if admin). | Masked phones; no bodies in list/ops. | Screenshot. |
| 4 | As admin, open **معاينة الرسالة**. | Full synthetic phone/body only in the explicit preview dialog; close returns to masked view; no bulk copy/export. | Screenshot with synthetic value. |
| 5 | QA calls list/detail APIs. | List returns `destination_phone_masked`, not `destination_phone`; campaign detail returns masked phones and no full bodies; preview requires `campaigns.preview`; file download requires `files.download`. | Field names; status codes; request IDs. |
| 6 | Inspect audit for phone-like fields. | Masked; no full payload. | Screenshot/field notes. |
| 7 | QA requests a file/import ID not owned by the test user. | `403`/`404`; no data; no existence leak beyond the approved behaviour. | Status; request ID. |
| 8 | Review captured evidence. | No full phone, name, body, credential, or token. | Evidence checklist. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-21 — Blocked and error paths

**Covers:** M2–M5.  
**Priority:** P1.  
**Preconditions:** QA-prepared F8; F5; F9; a disposable account; Technical Owner for the isolated kill-switch/worker check; staff and admin accounts.  
**Test data:** F5, F8, F9; synthetic campaign.

Execute each subcase separately and record its own result. A blocked subcase is not a pass.

| Subcase | Action | Expected result | Evidence |
|---|---|---|---|
| 21A | Upload an unsupported type, empty file, MIME-mismatched file, oversized file, and XLSX archive-limit file. | Each is rejected with the documented Arabic error/code; no batch or partial financial data. | Screenshot; status/error code. |
| 21B | Upload a duplicate of F1; try override without a reason, then with a reason. | `409 DUPLICATE_FILE` with previous import; `422 DUPLICATE_REASON_REQUIRED`; with reason succeeds and audits. | Screenshot; status; audit. |
| 21C | In mapping, omit a required field; then map one column twice. | Extraction blocked with a clear message; duplicate column rejected; no rows staged. | Screenshot. |
| 21D | Confirm a batch with an unexcluded blocking row. | `409 BLOCKING_ROWS`; row IDs returned; no partial write. | Status; row IDs; counts. |
| 21E | Confirm a warning batch without acknowledgment. | `422 WARNINGS_UNACKNOWLEDGED`; no confirmation. | Status. |
| 21F | Confirm with an unresolved ambiguous guardian. | `409 AMBIGUOUS_GUARDIAN`; no partial write; affected rows listed. | Status; screenshot. |
| 21G | Create a campaign from an import with no eligible recipients. | Blocked with `NO_ELIGIBLE_RECIPIENTS`; no messages/jobs. | Screenshot/status. |
| 21H | Submit with a stale campaign revision. | `409 CAMPAIGN_CHANGED`; page refresh required; no stale approval. | Status; screenshot. |
| 21I | Approve as staff (UI and QA API). | No control; `403`; no state change. | Screenshot/status. |
| 21J | Test-send to a non-allowlisted number; empty allowlist in an isolated config; repeat until rate-limited if safe. | `RECIPIENT_NOT_ALLOWLISTED`; `ALLOWLIST_REQUIRED`; `RATE_LIMITED`; no real send. | Screenshot/status. |
| 21K | Technical Owner starts a new isolated fake worker process with the kill switch on, then a new process with messaging disabled. | `claimed=false`; no send; no state change. Record the exact flags and result. | Worker output; counts. |
| 21L | Use an expired session; attempt a mutating API call without CSRF. | `401`/session-expired redirect; missing CSRF `403`; no mutation. | Status; screenshot. |
| 21M | Upload F5 (scanned PDF). | 0 rows; `SCANNED_PDF`; no confirmation; no invented data. | Screenshot. |
| 21N | Request a file download without `files.download`; request an unowned object. | `403`/`404`; no file bytes; no data leak. | Status; request ID. |

**Subcase results:**

| Subcase | Result (Pass / Fail / Blocked / N/A) | Defect ID | Evidence ref |
|---|---|---|---|
| 21A |  |  |  |
| 21B |  |  |  |
| 21C |  |  |  |
| 21D |  |  |  |
| 21E |  |  |  |
| 21F |  |  |  |
| 21G |  |  |  |
| 21H |  |  |  |
| 21I |  |  |  |
| 21J |  |  |  |
| 21K |  |  |  |
| 21L |  |  |  |
| 21M |  |  |  |
| 21N |  |  |  |

**Overall result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes (list subcases):**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

### UAT-22 — RTL, responsive, keyboard, screen-reader smoke

**Covers:** M1–M5 cross-cutting.  
**Priority:** P2.  
**Preconditions:** Browser with 1024×800 and 1440×900 viewports; keyboard; optional screen reader; approved pages with non-PII data.  
**Test data:** Any approved pages; no PII.

| # | Step | Expected result | Evidence |
|---|---|---|---|
| 1 | At 1024 and 1440, open login, statements, review, campaign, messages, results, dashboard, settings, and operations. | No document-level horizontal overflow; tables scroll inside their wrapper; dialogs fit. | Screenshots; width notes. |
| 2 | Check RTL layout. | Sidebar on the right; Arabic alignment; table headers and dialogs read correctly. | Screenshot. |
| 3 | Keyboard through login, upload, review, campaign, and dialogs. | Visible focus ring; logical tab order; skip link works; dialogs trap focus; Esc closes without action. | Notes; screenshots. |
| 4 | Check touch/click targets. | Key controls are at least 44px; no overlapping hit areas. | Notes/screenshot. |
| 5 | Screen reader smoke (if available). | Table captions/scopes announced; status/count changes announced once; currency code not announced twice. | Notes. |
| 6 | Zoom to 200%. | Content remains usable; no critical clipping; no horizontal document scroll where avoidable. | Screenshot/notes. |

**Result:** ☐ Pass ☐ Fail ☐ Blocked ☐ N/A  
**Actual result / notes:**  
**Defect ID(s):**  
**Evidence ref(s):**  
**Tester / date:**  

---

## 6. Appendix — Error-code quick reference

Use these codes as evidence anchors; record the exact Arabic message shown by the build.

| Code | Context |
|---|---|
| `DUPLICATE_FILE` / `DUPLICATE_REASON_REQUIRED` | Duplicate upload / missing override reason |
| `FILE_TOO_LARGE` / `INVALID_FILE_TYPE` / `FILE_TYPE_MISMATCH` / `XLSX_ARCHIVE_LIMIT` | Upload validation |
| `BLOCKING_ROWS` | Confirmation with unexcluded errors |
| `WARNINGS_UNACKNOWLEDGED` | Confirmation/approval without acknowledgment |
| `AMBIGUOUS_GUARDIAN` | Unresolved guardian candidates |
| `IMPORT_STATE_INVALID` | Import state no longer allows the action |
| `CAMPAIGN_CHANGED` | Stale campaign revision |
| `NO_ELIGIBLE_RECIPIENTS` | Campaign has no eligible recipients |
| `TEMPLATE_INACTIVE` / `UNRESOLVED_VARIABLES` | Template state/variable blockers |
| `RECIPIENT_NOT_ALLOWLISTED` / `ALLOWLIST_REQUIRED` | Test-send allowlist |
| `LIVE_TEST_SEND_BLOCKED` / `live_provider_blocked` | Live provider/test-send blocked |
| `RATE_LIMITED` | Test-send throttle |
| `SCANNED_PDF` | Scanned PDF detected; no rows |
| `401` / `403` | Session/permission denial |

---

**End of scripts. No script has been executed.**
