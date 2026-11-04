# FeeDesk M6 — Support Model

**Document ID:** M6-SUP-01  
**Version:** 0.1 (draft for school sign-off)  
**Date:** 4 November 2026  
**Status:** **Proposed. Not agreed, staffed, or signed.**  
**Audience:** School administration, technical owner, provider/operations, security.  
**Related:** `handover-pack.md`, `credential-handover.md`, `first-campaign-runbook.md`, `post-implementation-review.md`, `docs/runbooks/`.

> **Status statement**
>
> This is a proposed support model, not an operating SLA. No support rota, on-call number, escalation mailbox, or response-time commitment is recorded in this package. No live SMS, production deployment, UAT, or hypercare has occurred. All production-dependent items remain **blocked** until the school and technical owner sign the tables in §11 and §12 and the relevant gate evidence exists.
>
> Incident procedures may be used for tabletop or fake-provider exercises now. Live use of the unknown-outcome, provider-outage, key-rotation, restore, and privacy procedures is **blocked** until G0/G4, production access, and the relevant custody/policy approvals exist.
>
> Never include guardian names, phone numbers, message bodies, passwords, API keys, or database URLs in a support ticket, chat, email, or alert.

---

## 1. Purpose / الغرض

Define who owns what after handover, how incidents are classified and escalated, what evidence is collected, and what the school is asked to approve. The model is deliberately small: one school, one application, one provider account, and a named technical owner.

**Arabic summary / ملخص عربي**

يحدد هذا المستند مسؤوليات المدرسة والمالك التقني ومشغّل المزود والأمن، وساعات الدعم المقترحة، ومستويات التصعيد، وفئات الحوادث، والأدلة المطلوبة، وقوالب التواصل. جميع الأوقات واتفاقيات مستوى الخدمة **مقترحة** وتحتاج إلى توقيع المدرسة. لا تُرسل أسماء أو أرقام أولياء الأمور أو كلمات المرور أو المفاتيح في أي قناة دعم.

---

## 2. Scope and boundaries

### 2.1 In scope

- Application availability, login, imports, campaigns, approvals, messages, and reports.
- Worker/queue health, provider configuration, and safe messaging state.
- Backup, restore, deployment, and monitoring owned by the technical owner.
- Incident coordination, evidence handling, and school communication.
- Privacy/retention requests routed under the school's signed policy.
- Provider account, sender, balance, and delivery-report coordination.

### 2.2 Out of scope

- The school's finance policy, fee amounts, or guardians' personal circumstances.
- The provider's internal delivery network beyond a support ticket.
- Devices, browsers, or internet access at the school.
- Legal advice; the school's adviser owns legal interpretation.
- 24/7 coverage unless separately funded and signed.
- Any live send before G0/G4 and written go/no-go.

### 2.3 Support boundaries

| Domain | Owns | Does not own |
|---|---|---|
| School admin | Users, data decisions, campaign approval, school communication | Host, database, provider API, code |
| Technical owner | Host, deploy, DB, backup, monitoring, app configuration | School policy, provider commercial account, legal decisions |
| Provider/ops | Rasel account, sender approval, balance, delivery records, provider tickets | FeeDesk application logic, school data |
| Security | Incident command for suspected breach, key custody, access review | Routine functional support, fee policy |
| Engineering (T2) | Code defects, migrations, reconciliation writes, DB-role changes | School sign-off, provider commercial decisions |

---

## 3. Support principles

1. **One incident ID per issue.** Every report gets an ID; verbal reports are written up.
2. **No PII in tickets.** Use internal IDs, counts, and redacted screenshots. If a guardian must be identified, use the application's internal record ID, not name/phone.
3. **No secrets in any channel.** Never paste a password, API key, session cookie, database URL, or backup key.
4. **Unknown is not failure.** A message with `unknown` status is unresolved, not failed; never resend without provider reconciliation.
5. **Stop before you fix.** For sending, restore, migration, or key issues, stop the worker first and preserve evidence.
6. **One change at a time.** Do not rotate a key and retry a send simultaneously; isolate causes.
7. **School owns the data relationship.** FeeDesk does not contact guardians directly unless the school explicitly authorises a channel and wording.
8. **Write it down.** Record time, operator, commands, outcome, and decision for every production action.
9. **Do not improvise a destructive action.** Restore, purge, role change, and key rotation require the named approval path.
10. **Arabic and English are both valid.** School-facing communication should use the school's preferred language; technical records may be English.

---

## 4. Roles and ownership

Names are intentionally blank until the school and technical owner complete §12. A role without a named person and deputy is not staffed.

### 4.1 School administrator (مدير النظام المدرسي)

**Typical holder:** school director's delegate, bursar, or office manager with an `admin` application account.

**Owns:**

- Named user accounts, role assignment, deactivation, and quarterly access review.
- School settings: name, currency, locale, timezone, contacts, limits.
- Import approval and confirmation of financial data.
- Campaign preparation quality and school copy approval.
- Campaign approval (or named backup approver).
- First-line support for school staff: login, navigation, import questions.
- School-facing communication and escalation to the technical owner.
- Data-owner decisions with the school director: retention, deletion, privacy requests.

**Must not:**

- Share the admin account or password.
- Paste guardian data into tickets.
- Approve a campaign without previewing recipients, totals, and copy.
- Enable messaging or change provider settings without the technical owner and G4 authority.

### 4.2 Technical owner (المالك التقني)

**Typical holder:** FeeDesk operations engineer or contracted school IT lead with host access.

**Owns:**

- Host, OS patching, Docker/Compose, systemd, Caddy/TLS, DNS, firewall.
- Deployments, image tags, rollback, migrations, and release records.
- PostgreSQL availability, backup, restore drills, and retention of backup artifacts.
- Monitoring, alert routing, queue/worker health, and on-call response.
- Application configuration and environment-file custody (not values in tickets).
- Provider credential rotation/revocation execution with the provider/ops owner.
- Runbook maintenance and incident evidence.
- Handover of operational knowledge to the school.

**Must not:**

- Use the break-glass DB role for routine work.
- Run `docker compose down -v`.
- Restore over live data without written school approval.
- Change roles, keys, or provider settings during an active incident without isolating cause.

### 4.3 Provider / operations (مشغّل المزود)

**Typical holder:** the person who controls the Rasel account and commercial relationship.

**Owns:**

- Provider account status, plan, free-text enablement, and commercial terms.
- Approved sender ID and sender approval evidence.
- Syrian destination coverage confirmation and test-number coordination.
- Account balance, top-up, low-water mark, and pricing/segment confirmation.
- Provider tickets, status page, delivery reports, and reconciliation evidence.
- Provider-side incident communication and rate-limit guidance.

**Must not:**

- Claim delivery from provider acceptance alone.
- Ask FeeDesk to resend an unknown message without reconciliation.
- Share the provider API key in chat/email or with the school office.

### 4.4 Security (الأمن)

**Typical holder:** named security lead, school IT security, or contracted reviewer. May be the same person as the technical owner only with a recorded conflict and compensating review.

**Owns:**

- Security incident command for suspected breach, key compromise, or unauthorised access.
- Credential custody ledger, rotation schedule, and break-glass approval.
- Access reviews, MFA gap acceptance, and least-privilege exceptions.
- Privacy incident intake with the school data owner.
- Evidence preservation and post-incident review.
- Security review of provider/OCR/cloud changes.

**Must not:**

- Approve a deletion or retention change without the school data owner.
- Hold both the only admin account and the only break-glass credential without a deputy.

### 4.5 Engineering escalation (T2)

Not a standing school role. The technical owner escalates code, migration, reconciliation-write, or DB-role work to the FeeDesk engineering owner. Engineering does not approve school policy or provider commercial terms.

---

## 5. RACI matrix

**R** = responsible, **A** = accountable (one per row), **C** = consulted, **I** = informed.

| Activity | School admin | Technical owner | Provider/ops | Security |
|---|---|---|---|---|
| Named user accounts and access review | **A/R** | C | I | C |
| School settings and currency | **A/R** | C | I | I |
| Import review and financial confirmation | **A/R** | C | I | I |
| Campaign preparation and preview | **A/R** | C | I | I |
| Campaign approval | **A/R** | C | I | I |
| Host, deploy, and release | I | **A/R** | I | C |
| Database, backup, restore | I | **A/R** | I | C |
| Monitoring and on-call | I | **A/R** | C | I |
| Provider account, sender, balance | I | C | **A/R** | I |
| Provider outage ticket | I | C | **A/R** | I |
| Unknown-outcome reconciliation | C | R | **A** | I |
| Security incident command | C | R | C | **A** |
| Key custody and rotation | I | R | C | **A** |
| Privacy request / deletion | **A** | R | I | C |
| UAT and training | **A/R** | C | I | I |
| Runbook ownership and review | C | **A/R** | C | C |
| Hypercare review and go/no-go | **A** | R | C | C |
| Break-glass use | C | R | I | **A** |

**Interpretation:** the school admin is accountable for school data and school-facing decisions; the technical owner is accountable for operating the system; provider/ops is accountable for the provider relationship and reconciliation evidence; security is accountable for security incidents and custody, with the school data owner accountable for privacy decisions. If the school data owner is a different person from the admin, the “School admin” column for privacy requests means “school-side data owner or delegate”; record the actual name in §12.

---

## 6. Support hours and escalation tiers

### 6.1 Proposed support hours

These are proposals for school sign-off, not current commitments.

| Coverage | Proposed hours | Notes |
|---|---|---|
| School admin first-line | Sunday–Thursday, 08:00–15:00 Asia/Damascus | School office hours; Friday/Saturday closed |
| Technical owner | Sunday–Thursday, 09:00–17:00 Asia/Damascus | Business-hours support |
| Campaign-window coverage | Agreed per campaign, typically 08:00–18:00 | Named operator on call during the window |
| S1 on-call | Best effort outside hours | 24/7 requires a separate funded rota |
| Provider/ops | Provider's published support hours | Record the actual contract terms |
| Security | S1 only, as agreed | No standing 24/7 security desk |

**Public holidays:** coverage follows the school calendar; the technical owner publishes exceptions a week ahead where possible.

### 6.2 Tiers

| Tier | Owner | Handles | Does not handle |
|---|---|---|---|
| **T0 — Self-service / school admin** | School admin | Login guidance, navigation, import preparation, campaign preview, user questions, known-error lookup | Host, DB, provider API, code changes |
| **T1 — Technical owner** | Technical owner | Availability, TLS, deploy, queue/worker, backup, monitoring, non-emergency rotation, configuration | Code defects, provider commercial terms, school policy |
| **T2 — Engineering** | FeeDesk engineering | Code defects, migrations, reconciliation writes, DB-role changes, security fixes | School decisions, provider account ownership |
| **T3 — Provider/security** | Provider/ops or security | Provider outage/account/sender, suspected breach, key compromise, legal/privacy escalation | Routine functional support |

### 6.3 Escalation path

```text
School staff
   -> School admin (T0)
      -> Technical owner (T1)
         -> Engineering (T2)  |  Provider/ops or Security (T3)
            -> School director / data owner (decision)
```

**Escalate immediately, without waiting for the next tier's normal queue, when:**

- a message may have been sent to the wrong recipient or duplicated;
- `unknown` outcomes are increasing;
- the worker cannot be stopped or the kill switch is not effective;
- there is suspected key/credential compromise or unauthorised admin access;
- data loss/corruption or a failed restore is suspected;
- a privacy request or legal hold arrives;
- the provider reports account suspension or sender revocation.

---

## 7. Severity and response targets

Severity is assigned by the technical owner or security, not by the reporter. When in doubt, start higher.

| Severity | Definition | Examples | First response (proposed) | Update cadence |
|---|---|---|---|---|
| **S1 — Critical** | Safety, data, or live-send integrity at risk; service unusable during a campaign | Wrong/duplicate send, possible breach, data loss, DB down, worker sending uncontrollably, provider account compromise | 30 minutes | Every 30–60 minutes until contained |
| **S2 — High** | Core workflow blocked; no safe workaround | Campaign cannot approve, queue stalled, backup failed twice, provider auth failure, TLS expired | 4 business hours | Daily |
| **S3 — Medium** | Degraded but workaround exists | One user cannot log in, one import format fails, report mismatch, non-critical UI defect | 1 business day | Every 2 business days |
| **S4 — Low** | Cosmetic, documentation, or enhancement | Label, spacing, typo, training request | 3 business days | Weekly |

**Response is not resolution.** The first response acknowledges ownership and starts triage. Resolution targets are proposed in §11 and require sign-off.

---

## 8. Incident categories

Each category has a mandatory first action and a “do not” rule. Use the linked runbook for commands.

### 8.1 Unknown message outcome

**Trigger:** `messages.internal_status='unknown'`, timeout, ambiguous provider response, worker crash during `submitting`.

**First action:** stop the worker if unknowns are still being created; preserve message/job/provider IDs; do not resend.

**Owner:** provider/ops (reconciliation evidence) + technical owner (system state).

**Evidence:** campaign ID, message IDs, idempotency keys, provider message/request IDs, timestamps, error codes, counts, provider console result, second reviewer.

**Do not:** resend, bulk-retry, or edit `messages.internal_status` with SQL. No reconciliation write tool exists.

**Runbook:** `docs/runbooks/unknown-outcomes.md`.

### 8.2 Provider outage or account failure

**Trigger:** Rasel 5xx/timeouts, auth failure, sender rejected, insufficient balance, plan restriction.

**First action:** stop the worker; set `MESSAGING_KILL_SWITCH=true` and `MESSAGING_ENABLED=false`; classify auth/balance/sender/rate/outage/destination; open a provider ticket.

**Owner:** provider/ops; technical owner supports.

**Evidence:** error class counts, time window, provider status/ticket, affected campaigns, sender/balance state, recovery confirmation.

**Do not:** retry blindly, run multiple workers, change credentials and retry at the same time, or claim delivery from acceptance.

**Runbook:** `docs/runbooks/provider-outage.md`.

### 8.3 Key rotation or suspected compromise

**Trigger:** scheduled rotation, suspected leak, staff departure, provider key exposure, backup-key concern, TLS/domain compromise.

**First action:** contain (revoke/disable), preserve logs, notify security, identify blast radius. Do not rotate everything at once without a backup and a rollback path.

**Owner:** security (accountable); technical owner executes; provider/ops for provider-side revocation.

**Evidence:** reason, scope, who approved, time, key version (not value), systems restarted, sessions invalidated, provider revocation confirmation, audit review, follow-up rotation.

**Do not:** paste the old/new secret anywhere; rotate the provider vault key without a re-encryption procedure; rotate during an active incident unless the secret is the cause.

**Runbook:** `docs/runbooks/key-rotation.md`; custody rules in `credential-handover.md`.

### 8.4 Restore or data loss

**Trigger:** corrupted database, failed migration, accidental deletion, ransomware, failed release requiring restore.

**First action:** stop the worker, then web/api; preserve the current (even broken) database and uploads; declare a maintenance window; obtain written school approval for the data-loss window.

**Owner:** technical owner (execution); school data owner (approval); security (if caused by intrusion).

**Evidence:** backup ID, manifest SHA-256, restore target, start/end time, RPO/RTO actual, row counts, uploads sample download, smoke results, approvals, data-loss window.

**Do not:** overwrite the live database in place, extract over the live uploads volume, or use `down -v`.

**Runbook:** `docs/runbooks/backup-restore.md`.

### 8.5 Privacy request or privacy incident

**Trigger:** guardian/staff erasure or access request, suspected PII leak, misdirected message, log/ticket exposure, legal hold.

**First action:** log the request with an ID; verify the requester's identity through the school; do not delete or export until the signed policy and approval path are confirmed; preserve evidence; notify the school data owner and security.

**Owner:** school data owner (accountable); technical owner executes; security advises.

**Evidence:** request ID, verification method, scope, policy reference, approvals, records found/exported/anonymised counts, backup caveat, response date, legal-hold check.

**Do not:** send PII in the ticket, delete audit rows, or promise deletion from backups before expiry.

**Runbook/policy:** `docs/m5/privacy-retention-plan.md` (H4 open; no purge enabled).

### 8.6 Wrong or duplicate send

**Trigger:** recipient reports a wrong amount/name, duplicate SMS, message to an unintended number, or campaign sent after cancel.

**First action:** stop the worker and set the kill switch; preserve message bodies/IDs and provider evidence; quantify affected recipients; notify the school admin and security; do not send a correction campaign without school approval.

**Owner:** technical owner (containment); school admin (school communication); provider/ops (delivery evidence).

**Evidence:** campaign/message IDs, approved snapshot hash, recipient count, content hash, provider records, timeline, school decision, remediation.

**Do not:** delete messages, edit snapshots, or blame the provider before evidence.

### 8.7 Access or authentication incident

**Trigger:** suspected account takeover, lost admin device, shared password, unexpected role change, repeated lockouts.

**First action:** deactivate the account or revoke sessions; reset the password through the admin flow; review audit events; involve security if takeover is suspected.

**Owner:** school admin (account); technical owner (sessions/host); security (investigation).

**Evidence:** username/internal ID, time window, audit events, session revocation, role changes, IP/request IDs where available, resolution.

**Do not:** delete the user (audit references remain), reuse the old password, or grant a new admin without a second approval.

### 8.8 Import or financial-integrity incident

**Trigger:** wrong totals, duplicated rows, wrong guardian mapping, wrong currency, confirmed import with bad data.

**First action:** stop further confirmation; preserve the source file, import batch, staged rows, and audit; identify affected fee balances; do not delete the batch or source file.

**Owner:** school admin (data decision); technical owner (investigation); engineering (correction workflow).

**Evidence:** import batch ID, file SHA-256, row counts, per-currency totals, discrepancy, affected record IDs, correction approval, audit before/after.

**Do not:** hand-edit fee balances without an audited correction; re-import over the top without reconciliation.

### 8.9 Backup failure

**Trigger:** missed timer, non-zero backup unit, missing manifest/checksum, encryption failure, disk full, restore check failure.

**First action:** inspect the timer/unit/logs; confirm disk and key availability; run a manual dry run; do not delete the last good backup.

**Owner:** technical owner.

**Evidence:** unit status, log excerpt (no secrets), artifact list, manifest checksum, next successful run, restore check.

**Runbook:** `docs/runbooks/backup-restore.md`.

---

## 9. Evidence collection standard

### 9.1 Required fields for every incident

| Field | Requirement |
|---|---|
| Incident ID | Assigned at intake; used in all communication |
| Severity | S1–S4, with reason |
| Detected at | UTC and school-local time |
| Reporter | Name/role, not a guardian identity |
| Environment | Local / staging / production; release/commit |
| Component | Web/API/worker/DB/provider/backup/access |
| Summary | One or two sentences, no PII |
| Affected IDs | Campaign/message/job/import IDs; counts |
| Error codes | Exact code/message, redacted |
| Evidence links | Approved store; not chat |
| Actions taken | Time-stamped; who did what |
| Decision | Open/contained/resolved; owner and next update |
| PII check | Confirmed no names/phones/bodies in the record |

### 9.2 Evidence rules

- Use internal IDs, not guardian names or phone numbers.
- Redact query strings, cookies, authorization headers, and provider keys from screenshots/logs.
- Preserve original logs before restarting a container if practical; copy to the approved evidence store.
- Record provider ticket IDs and timestamps.
- Do not alter audit rows; they are append-only by design.
- Keep incident records under the school's retention policy; do not delete during an open investigation.
- If PII is exposed in a ticket, stop, remove/redact it, notify security, and record the exposure.

### 9.3 Evidence store

The school and technical owner must name an approved location (for example, a restricted folder or ticketing system) with access limited to the incident team. Chat threads are not an evidence store. Until named, treat evidence handling as **blocked**.

---

## 10. Communication templates

Use the school's preferred language. Send both Arabic and English when the audience is mixed. Replace `{{placeholders}}`; never add guardian names, phone numbers, balances, or message bodies.

### 10.1 Incident acknowledged / تأكيد استلام البلاغ

**Arabic**

```text
الموضوع: تأكيد استلام البلاغ {{incident_id}}

تم استلام بلاغكم بخصوص {{summary_without_pii}}.
التصنيف الحالي: {{severity}}.
بدأنا التحقق، والمالك المسؤول: {{owner_role}}.
سنوافيكم بتحديث خلال {{next_update_time}}.
يرجى عدم مشاركة أسماء أو أرقام أولياء الأمور أو أي بيانات شخصية في هذه القناة.
```

**English**

```text
Subject: Acknowledgement — {{incident_id}}

We have received your report about {{summary_without_pii}}.
Current severity: {{severity}}.
Triage has started; the accountable owner is {{owner_role}}.
We will provide an update by {{next_update_time}}.
Please do not share guardian names, phone numbers, or other personal data in this channel.
```

### 10.2 Status update / تحديث الحالة

**Arabic**

```text
الموضوع: تحديث {{incident_id}}

الحالة: {{status}}.
ما نعرفه: {{known_facts_without_pii}}.
ما نفعله الآن: {{current_action}}.
الأثر الحالي: {{impact_counts}} (بدون أسماء أو أرقام).
التحديث القادم: {{next_update_time}}.
```

**English**

```text
Subject: Update — {{incident_id}}

Status: {{status}}.
What we know: {{known_facts_without_pii}}.
What we are doing: {{current_action}}.
Current impact: {{impact_counts}} (no names or phone numbers).
Next update: {{next_update_time}}.
```

### 10.3 Resolution / إغلاق الحالة

**Arabic**

```text
الموضوع: إغلاق {{incident_id}}

تمت معالجة الحالة: {{resolution_summary_without_pii}}.
المدة: {{duration}}.
الإجراء الوقائي: {{preventive_action}}.
إذا تكرر الأثر، أبلغونا مع رقم الحادث.
```

**English**

```text
Subject: Resolution — {{incident_id}}

The incident is resolved: {{resolution_summary_without_pii}}.
Duration: {{duration}}.
Preventive action: {{preventive_action}}.
If the impact recurs, contact us with the incident ID.
```

### 10.4 Privacy request acknowledgement / تأكيد طلب الخصوصية

**Arabic**

```text
الموضوع: استلام طلب خصوصية {{request_id}}

استلمنا طلبكم بخصوص {{request_type}}.
سنتحقق من الهوية ونطاق الطلب وفق سياسة المدرسة المعتمدة.
الموعد المقترح للرد: {{response_date}}.
لن نقوم بحذف أو تصدير أي بيانات قبل اكتمال التحقق والموافقات.
```

**English**

```text
Subject: Privacy request received — {{request_id}}

We received your request regarding {{request_type}}.
We will verify identity and scope under the school's approved policy.
Proposed response date: {{response_date}}.
No data will be deleted or exported before verification and approvals are complete.
```

### 10.5 Provider outage notice / إشعار انقطاع المزود

**Arabic**

```text
الموضوع: تعليق الإرسال مؤقتًا — {{incident_id}}

تم إيقاف الإرسال مؤقتًا بسبب {{provider_issue}}.
الحملات المتأثرة: {{campaign_count}}.
لن نعيد إرسال أي رسالة إلا بعد التحقق من سجل المزود.
سنوافيكم عند استعادة الخدمة: {{next_update_time}}.
```

**English**

```text
Subject: Sending paused — {{incident_id}}

Sending has been paused because of {{provider_issue}}.
Affected campaigns: {{campaign_count}}.
We will not resend any message until the provider record is reconciled.
We will update you when service is restored: {{next_update_time}}.
```

### 10.6 Unknown outcome notice / حالة نتيجة غير معروفة

**Arabic**

```text
الموضوع: رسائل بحاجة إلى تحقق — {{incident_id}}

لدينا {{unknown_count}} رسالة حالتها غير معروفة لدى المزود.
لا نعتبرها فاشلة ولا نعيد إرسالها تلقائيًا.
نراجع سجل المزود الآن، وسنبلغكم بالنتيجة قبل أي إجراء تصحيحي.
```

**English**

```text
Subject: Messages requiring reconciliation — {{incident_id}}

We have {{unknown_count}} messages whose provider outcome is unknown.
We are not treating them as failed and will not resend automatically.
We are checking the provider record and will report the result before any corrective action.
```

### 10.7 Communication rules

- Use counts and internal IDs, not guardian identities.
- Do not promise delivery dates before provider evidence.
- Do not send a correction campaign without written school approval.
- Keep one incident thread; link updates to the incident ID.
- If a message must go to guardians, the school sends it through an approved channel and wording.

---

## 11. SLA placeholders requiring school sign-off

All values below are **proposals**, not commitments. The school must choose, fund, and sign them. Blank cells mean “not agreed”.

| ID | Commitment | Proposed value | School-approved value | Owner | Notes |
|---|---|---|---|---|---|
| SLA-01 | S1 first response | 30 minutes |  | Technical owner | During support hours; outside hours best effort |
| SLA-02 | S1 containment/workaround | 4 hours |  | Technical owner | Depends on provider/host access |
| SLA-03 | S2 first response | 4 business hours |  | Technical owner | |
| SLA-04 | S2 workaround | 1 business day |  | Technical owner | |
| SLA-05 | S3 first response | 1 business day |  | Technical owner | |
| SLA-06 | S4 first response | 3 business days |  | Technical owner | |
| SLA-07 | Application availability | Business-hours best effort |  | Technical owner | No 24/7 unless funded |
| SLA-08 | RPO | ≤24 hours |  | School + technical | Nightly backup |
| SLA-09 | RTO | ≤4 hours |  | School + technical | Single server; no HA |
| SLA-10 | Backup verification | Monthly restore drill |  | Technical owner | DB + uploads required |
| SLA-11 | Security incident notification | Within 24 hours of confirmation |  | Security | Legal timing may differ |
| SLA-12 | Privacy request response | Per signed policy (proposed 30 days) |  | School data owner | Legal review required |
| SLA-13 | Provider outage update | Every 2 business hours |  | Provider/ops | Provider-dependent |
| SLA-14 | Maintenance window notice | 2 business days |  | Technical owner | Emergency excluded |
| SLA-15 | Post-incident review | Within 5 business days (S1/S2) |  | Security/technical | Report to school |

**Sign-off rule:** a verbal “yes” is not an SLA. Record the school-approved value, approver, date, and any exclusions. If the school does not sign, support remains **best effort** and must be described that way.

---

## 12. Contacts and sign-off

### 12.1 Contact register (complete before handover)

| Role | Primary name | Backup name | Phone | Email | Hours | Notes |
|---|---|---|---|---|---|---|
| School director / authorised representative |  |  |  |  |  |  |
| School data owner |  |  |  |  |  |  |
| School administrator |  |  |  |  |  |  |
| Technical owner |  |  |  |  |  |  |
| Engineering escalation |  |  |  |  |  |  |
| Provider/operations |  |  |  |  |  |  |
| Security lead |  |  |  |  |  |  |
| Backup mailbox / alert destination |  |  |  |  |  |  |

**Do not put credentials, API keys, or guardian data in this table.**

### 12.2 Sign-off

| Item | School signatory | Role | Date | Signature |
|---|---|---|---|---|
| Support roles and RACI accepted |  |  |  |  |
| Support hours accepted |  |  |  |  |
| Severity and response targets accepted |  |  |  |  |
| SLA values SLA-01..SLA-15 accepted or amended |  |  |  |  |
| Communication templates and language accepted |  |  |  |  |
| Contacts and escalation path accepted |  |  |  |  |
| Evidence store and access accepted |  |  |  |  |
| Residual risks recorded (no MFA, no 24/7, single server) |  |  |  |  |

**Residual risks / exceptions:**

```text
1.
2.
3.
```

---

## 13. Review cadence

| Trigger | Action | Owner |
|---|---|---|
| Before first controlled campaign | Confirm contacts, hours, stop authority, and escalation | Technical owner + school |
| After every S1/S2 incident | Update severity, contacts, runbook, and evidence gaps | Security/technical |
| After each deploy or role/key change | Re-check on-call and rollback contacts | Technical owner |
| Monthly during hypercare | Review ticket volume, response times, and recurring defects | Technical owner + school |
| Quarterly | Access review, custody ledger review, SLA review | School admin + security |
| Annually | Full support-model review and retraining | School + technical owner |
| After H4/H6 or provider change | Re-review privacy/escalation and DB/provider contacts | Security + technical |

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 4 Nov 2026 | Initial M6 support model draft; proposed hours/SLA; no production claims | Documentation pass |
