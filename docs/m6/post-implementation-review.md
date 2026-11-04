# FeeDesk M6 — Post-Implementation Review Template

**Document ID:** M6-PIR-01  
**Version:** 0.1 (template)  
**Date:** 4 November 2026  
**Status:** **Template only. No controlled campaign or hypercare has occurred.**  
**Use after:** the first controlled campaign and the two-week hypercare period (OPS-11).  
**Related:** `first-campaign-runbook.md`, `handover-pack.md`, `support-model.md`, `docs/m5/privacy-retention-plan.md`.

> **This review does not replace UAT, G4, G5, or school acceptance.**
>
> It records what actually happened in the first controlled campaign and hypercare. Until G0 is passed and the pilot was authorised under G4, every “actual” field below is empty and every production-dependent criterion is **blocked**. This review may supply evidence toward G4 closure, but it does not itself close G4. Do not fill this template with synthetic/fake-provider results and present it as a live campaign review.

---

## 1. Purpose / الغرض

Decide whether the school can widen rollout beyond the first controlled cohort, based on evidence rather than impression. The review covers:

- campaign and provider outcomes;
- defects and incidents;
- user feedback and training gaps;
- privacy/retention actions;
- operational readiness (backup, alerts, runbooks, access);
- a go/no-go decision for wider rollout.

**Arabic summary / ملخص عربي**

هذا القالب يراجع أول حملة خاضعة للرقابة وفترة الدعم المكثف. الهدف هو قرار مبني على الأدلة بشأن التوسع، وليس بديلًا عن UAT أو بوابات G4/G5. لا تُملأ الحقول الفعلية إلا بعد وجود حملة حقيقية وأدلة المزود. أي بند يعتمد على الإنتاج أو المزود يبقى **محجوبًا** حتى تتوفر الأدلة.

---

## 2. Review metadata

| Field | Entry |
|---|---|
| Review ID | PIR-{{YYYY}}-{{NN}} |
| Review type | First controlled campaign + 2-week hypercare |
| Campaign ID(s) |  |
| Review period (start/end) |  |
| Environment | Staging / production (circle one) |
| Release/commit |  |
| Provider / sender |  |
| School cohort size |  |
| Currency(ies) |  |
| Review chair |  |
| Participants |  |
| Evidence location |  |
| Status | Draft / Reviewed / Signed |

---

## 3. Executive summary

Write no more than 10 lines. State the outcome, the strongest evidence, the most serious unresolved issue, and the recommendation.

```text
Outcome:
Campaign scope:
What worked:
What did not:
Unresolved:
Recommendation:
```

**Recommendation options:** widen / widen with conditions / hold / roll back to fake-only.

---

## 4. Scope and method

### 4.1 In scope

- The first controlled campaign end to end: pre-flight, import, campaign, approval, send, results, reconciliation, closeout.
- The two-week hypercare support window.
- Defects, incidents, user feedback, training, privacy actions, and operational readiness.

### 4.2 Out of scope

- School finance policy and fee correctness outside the imported statement.
- Provider internal network performance.
- Legal advice on retention.
- Features not enabled in the campaign (OCR, WhatsApp, webhooks, resend).

### 4.3 Method

- Review the campaign record, approved snapshot, message/job counts, provider evidence, and audit trail.
- Review tickets and incident records by severity.
- Interview the school admin, at least one staff user, and the technical/provider contacts.
- Compare actuals with the pre-flight success criteria.
- Record disagreements; do not average them away.

---

## 5. Campaign metrics

Fill from the application, provider console, and campaign record. Use counts, not guardian identities.

### 5.1 Import and data quality

| Metric | Definition | Source | Pre-agreed target | Actual | Verdict |
|---|---|---|---|---|---|
| Import batches | Number processed for the campaign | Import list | 1 |  |  |
| Source rows | Rows in the confirmed statement | Import detail |  |  |  |
| Accepted rows | Rows confirmed into fee balances | Import detail |  |  |  |
| Excluded rows | Rows excluded with reason | Review ledger |  |  |  |
| Validation errors | Rows with blocking errors | Import detail |  |  |  |
| Duplicate rows | Detected duplicates | Import audit |  |  |  |
| Total discrepancy | Difference between source and computed totals | Import detail | 0 |  |  |
| Guardian resolution cases | Manual identity decisions | Review ledger |  |  |  |
| Time to review | Upload → confirmation | Audit timestamps |  |  |  |

### 5.2 Campaign and approval

| Metric | Definition | Source | Pre-agreed target | Actual | Verdict |
|---|---|---|---|---|---|
| Eligible recipients | Recipients after exclusions | Campaign detail |  |  |  |
| Excluded recipients | Count by reason | Campaign detail |  |  |  |
| Currencies | Distinct currencies in campaign | Campaign detail |  |  |  |
| Per-currency totals | Sum of outstanding balances | Campaign detail | Reconciles to import |  |  |
| Messages created | Pending messages at approval | Message list | = eligible recipients |  |  |
| Jobs created | Pending jobs at approval | Operations panel | = eligible recipients |  |  |
| Approval revisions | Draft revisions before approval | Audit |  |  |  |
| Approval time | Submit → approve | Audit timestamps |  |  |  |
| Snapshot hash recorded | Immutable snapshot evidence | Campaign detail | Present |  |  |

### 5.3 Sending and outcomes

| Metric | Definition | Source | Pre-agreed target | Actual | Verdict |
|---|---|---|---|---|---|
| Provider accepted | Messages accepted by provider | Provider console / messages | = messages attempted |  |  |
| Delivered | Messages with delivery evidence | Provider report / user confirmation | Not assumed from acceptance |  |  |
| Failed | Terminal failures | Message list | 0 |  |  |
| Unknown | Ambiguous outcomes | Message list | 0 unresolved |  |  |
| Cancelled | Cancelled before send | Message list | 0 |  |  |
| Duplicate sends | Same recipient/content sent twice | Provider + messages | 0 |  |  |
| Wrong recipient/content | Confirmed mis-send | Incident record | 0 |  |  |
| Send duration | First claim → last terminal | Job timestamps |  |  |  |
| Approval → first send | Queue latency | Timestamps |  |  |  |
| Campaign status | Derived final status | Campaign detail | `completed` or explained |  |  |

> **Critical distinction:** provider acceptance is not delivery. If no delivery report exists, write “not measured” — do not convert acceptance into delivered.

### 5.4 Reliability and support

| Metric | Definition | Source | Pre-agreed target | Actual | Verdict |
|---|---|---|---|---|---|
| API readiness | `/health/ready` failures during window | Monitoring | 0 unplanned |  |  |
| 5xx rate | API errors during window | Logs/monitoring | <2% |  |  |
| Worker stalls | Oldest pending >5 min | Monitoring | 0 |  |  |
| Expired leases | Stale claimed jobs | Monitoring | 0 |  |  |
| Queue depth | Peak pending/retry | Monitoring | <25 |  |  |
| Backup success | Nightly runs succeeded | Backup unit | 100% |  |  |
| Restore check | Scratch restore passed | Drill record | Pass |  |  |
| Alerts delivered | Test/real alerts received | Alert mailbox | All |  |  |
| Tickets opened | Count by severity | Support log |  |  |  |
| First response | Median by severity | Support log | Per SLA |  |  |
| Resolution time | Median by severity | Support log | Per SLA |  |  |
| Reopened tickets | Count | Support log | 0 |  |  |

### 5.5 Security and privacy

| Metric | Definition | Source | Pre-agreed target | Actual | Verdict |
|---|---|---|---|---|---|
| Access reviews completed | Named accounts reviewed | Access record | 100% |  |  |
| MFA gap accepted | Written acceptance | Risk record | Signed |  |  |
| PII exposures in tickets/logs | Confirmed incidents | Incident log | 0 |  |  |
| Privacy requests | Received / completed | Request log | Per policy |  |  |
| Retention actions | Purge/anonymise runs | H4 record | Per signed policy |  |  |
| Unauthorised access | Confirmed events | Audit/security | 0 |  |  |
| Key rotations | Completed / due | Custody ledger | Per schedule |  |  |

---

## 6. Defects

Record every defect found during the campaign or hypercare, including those fixed in-flight.

| ID | Severity | Description | Impact | Root cause | Fix / workaround | Owner | Status | Regression test |
|---|---|---|---|---|---|---|---|---|
| DEF-01 |  |  |  |  |  |  | Open / Fixed / Won't fix |  |
| DEF-02 |  |  |  |  |  |  |  |  |
| DEF-03 |  |  |  |  |  |  |  |  |

**Severity guide:** S1 = safety/data/live-send integrity; S2 = core workflow blocked; S3 = degraded with workaround; S4 = cosmetic/documentation.

**Questions to answer:**

- Did any defect affect the approved recipient list, amount, currency, or message body?
- Was any defect caused by the import, the template, the approval, the worker, or the provider?
- Was the defect reproducible? Is there a regression test?
- Did a workaround alter data? If so, was it audited and approved?

---

## 7. Incidents

| ID | Category | Severity | Start | Detected | Contained | Resolved | Affected count | Root cause | Actions | Owner |
|---|---|---|---|---|---|---|---|---|---|---|
| INC-01 | Unknown / outage / key / restore / privacy / wrong send / access / import / backup |  |  |  |  |  |  |  |  |  |
| INC-02 |  |  |  |  |  |  |  |  |  |  |

**For each S1/S2, attach:**

- timeline with UTC and school-local time;
- what the school was told and when;
- provider ticket/evidence;
- whether the worker was stopped and the kill switch used;
- data impact and whether a restore was considered;
- follow-up owner/date.

**Do not include** guardian names, phone numbers, message bodies, or secrets. Use message/campaign IDs and counts.

---

## 8. Provider reconciliation

Complete only with real provider evidence. Pre-G4, write **blocked**.

### 8.1 Count reconciliation

| Check | Expected | Actual | Difference | Explanation |
|---|---:|---:|---:|---|
| Approved recipients |  |  |  |  |
| Messages created |  |  |  |  |
| Jobs created |  |  |  |  |
| Provider accepted |  |  |  |  |
| Provider delivered (evidence) |  |  |  |  |
| Failed |  |  |  |  |
| Unknown |  |  |  |  |
| Cancelled |  |  |  |  |

**Rule:** approved recipients = messages created = jobs created. Any difference is a defect or an explained exclusion. Provider accepted may be lower than attempted; delivered may be lower than accepted. Do not force the numbers to match.

### 8.2 Evidence used

- [ ] Provider console export or screenshot (redacted).
- [ ] Provider message IDs / request IDs matched to FeeDesk message IDs.
- [ ] Idempotency keys checked for duplicate suppression.
- [ ] Delivery report or user confirmation, if available.
- [ ] Provider ticket for any outage/rejection.
- [ ] Second reviewer for any status correction.

### 8.3 Unresolved unknowns

| Message ID | Campaign ID | Provider ID | First seen | Last checked | Provider result | Decision | Owner |
|---|---|---|---|---|---|---|---|
|  |  |  |  |  | Accepted / Rejected / Not found |  |  |

**Do not** resend an unknown message. “Not found” does not prove “not sent.” Keep the campaign in `completed_with_errors` if any unknown remains.

---

## 9. User feedback and training gaps

### 9.1 Feedback by audience

| Audience | Method | What worked | What was hard | Quote (anonymised) | Action |
|---|---|---|---|---|---|
| School admin | Interview |  |  |  |  |
| School staff | Interview/survey |  |  |  |  |
| Technical owner | Review |  |  |  |  |
| Provider/ops | Review |  |  |  |  |

**Privacy rule:** do not record guardian names, phone numbers, balances, or message bodies in feedback. Use role labels and counts.

### 9.2 Training gaps

| Topic | Audience | Gap observed | Action | Owner | Due |
|---|---|---|---|---|---|
| Import and mapping | School staff |  |  |  |  |
| Review and exclusions | School staff |  |  |  |  |
| Guardian resolution | School staff |  |  |  |  |
| Campaign preview and approval | School admin |  |  |  |  |
| Understanding acceptance vs delivery | School admin |  |  |  |  |
| Unknown outcomes / no resend | School admin + technical |  |  |  |  |
| Kill switch and stop authority | School admin + technical |  |  |  |  |
| Backup/restore awareness | Technical |  |  |  |  |
| Privacy/retention request intake | School admin |  |  |  |  |
| Credential hygiene | All |  |  |  |  |

### 9.3 Documentation gaps

- Was the Arabic copy clear and correct?
- Did users understand why a row was excluded?
- Did the preview show enough to approve confidently?
- Did the results page distinguish accepted, delivered, failed, and unknown?
- Did support respond in the school's preferred language?
- Which runbook or FAQ needs updating?

---

## 10. Privacy and retention actions

H4 is **open**; no purge job exists. This section records actions and blockers, not a policy approval.

| Item | Status | Evidence / action | Owner | Date |
|---|---|---|---|---|
| Retention policy S1–S10 signed | Open / Signed |  | School data owner |  |
| `retention_until` populated | Not implemented |  | Engineering |  |
| Purge dry-run completed | Not run |  | Engineering |  |
| Purge `--execute` authorised | Blocked until S1–S8 |  | School data owner |  |
| Legal-hold register | Not implemented |  | School/security |  |
| Privacy requests received |  |  | School admin |  |
| Requests completed within policy |  |  | School admin |  |
| PII exposures in logs/tickets |  |  | Security |  |
| Backup retention/expiry confirmed |  |  | Technical owner |  |
| Deletion receipt issued (no PII) |  |  | School admin |  |

**Do not** delete live data, audit rows, or backups during this review without the signed H4 procedure and approvals.

---

## 11. Operational readiness review

| Area | Question | Evidence | Verdict |
|---|---|---|---|
| Deployment | Was the release deployed from a tagged image with a recorded rollback target? |  |  |
| TLS/DNS | Valid certificate, redirect, renewal monitored? |  |  |
| Backup | Encrypted, offsite, uploads included, restore tested? |  |  |
| Alerts | Delivered and resolved to the on-call mailbox? |  |  |
| Runbooks | Which were exercised? Which failed? |  |  |
| DB roles | H6 applied? Denial tests passed? |  |  |
| Access | Named accounts, least privilege, leavers removed? |  |  |
| Keys | Custody ledger complete? Rotations due? |  |  |
| Provider | Sender/balance/plan verified? Reconciliation method agreed? |  |  |
| Support | Contacts, hours, escalation, SLA signed? |  |  |
| Training | School staff trained and confident? |  |  |
| Privacy | Retention policy signed and operable? |  |  |

**Unexercised procedures are not “ready.”** Mark them “not verified,” not “pass.”

---

## 12. Go/no-go for wider rollout

### 12.1 Criteria

| # | Criterion | Evidence required | Status (Pass / Fail / Blocked) | Notes |
|---|---|---|---|---|
| 1 | No unresolved S1 incident | Incident log |  |  |
| 2 | No duplicate or wrong-recipient send | Provider + message evidence |  |  |
| 3 | All unknown outcomes reconciled or explicitly accepted | Reconciliation table |  |  |
| 4 | Provider acceptance/delivery distinction documented | Provider evidence |  |  |
| 5 | Import totals reconcile; no unexplained discrepancy | Import/campaign records |  |  |
| 6 | Backup + uploads restore drill passed | Drill record |  |  |
| 7 | Alerts delivered and acknowledged | Alert mailbox |  |  |
| 8 | Runbooks exercised; owners named | Review record |  |  |
| 9 | Support model/SLA signed | Support sign-off |  |  |
| 10 | Training completed; gaps closed or accepted | Training record |  |  |
| 11 | Retention/privacy policy signed; no unlawful retention | H4 sign-off |  |  |
| 12 | Access review complete; no shared accounts | Access record |  |  |
| 13 | Key custody ledger complete; rotations current | Custody ledger |  |  |
| 14 | Known limitations accepted in writing | Handover acceptance |  |  |
| 15 | G4 pilot report signed and gate closed | Signed G4 record |  |  |
| 16 | School approves wider cohort and wording | Written approval |  |  |

### 12.2 Decision

| Decision | Meaning | Conditions |
|---|---|---|
| **Go** | Widen to the next cohort |  |
| **Conditional go** | Widen only after listed conditions close |  |
| **Hold** | Keep the current cohort; fix and re-review |  |
| **Roll back** | Disable live messaging; return to fake-only |  |

**Decision:** ____________________  
**Rationale:** ____________________________________________________________

**Conditions before widening:**

```text
1.
2.
3.
```

### 12.3 Approvals

| Role | Name | Decision | Signature | Date |
|---|---|---|---|---|
| School director / authorised representative |  |  |  |  |
| School data owner |  |  |  |  |
| Technical owner |  |  |  |  |
| Provider/operations lead |  |  |  |  |
| Security reviewer |  |  |  |  |

---

## 13. Action plan

| # | Action | Owner | Due | Priority | Status | Evidence |
|---|---|---|---|---|---|---|
| 1 |  |  |  |  |  |  |
| 2 |  |  |  |  |  |  |
| 3 |  |  |  |  |  |  |

**Closure rule:** an action is closed only with evidence. “Discussed” is not closed.

---

## 14. Lessons learned

| Question | Answer |
|---|---|
| What surprised us? |  |
| What almost went wrong? |  |
| What would we do differently next campaign? |  |
| What should become a permanent check or runbook step? |  |
| What should we stop doing? |  |
| What training or documentation is missing? |  |

---

## 15. Evidence appendix

| Evidence | Location | Date | Redacted? |
|---|---|---|---|
| Campaign record / snapshot hash |  |  |  |
| Import batch and totals |  |  |  |
| Message/job export (IDs/counts) |  |  |  |
| Provider console/report |  |  |  |
| Incident records |  |  |  |
| Support tickets |  |  |  |
| Alert delivery receipt |  |  |  |
| Backup/restore record |  |  |  |
| Training attendance |  |  |  |
| School approvals |  |  |  |

**Do not attach** full phone numbers, guardian names, message bodies, credentials, or unredacted database rows.

---

## 16. Review sign-off

| Item | Chair | Date | Signature |
|---|---|---|---|
| Metrics verified against source |  |  |  |
| Defects/incidents complete |  |  |  |
| Provider reconciliation reviewed |  |  |  |
| Privacy actions reviewed |  |  |  |
| Go/no-go decision recorded |  |  |  |
| Action owners accepted |  |  |  |

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1 | 4 Nov 2026 | Initial post-implementation review template; no campaign data | Documentation pass |
