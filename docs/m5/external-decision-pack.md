# FeeDesk — Consolidated External Decision Pack

**Document ID:** M5-EXT-DEC-01  
**Version:** 1.0 (draft for decision; not approved)  
**Date:** 4 November 2026  
**Prepared by:** Documentation and codemap specialist  
**Audience:** School director/PO, technical owner, provider/ops, security  
**Status:** **Open. No decision in this pack has been taken. No gate is passed.**

**Abbreviations:** PO = product owner; TL = technical lead (engineering); technical owner = operations owner; DBA = database administrator; UAT = user acceptance testing; DLR = delivery report; OPS = operations task; H4/H6 = security findings in `security-review.md`.

> **This is a decision pack, not a status report and not a gate record.**
>
> - G0, G4, and G5 remain open. H4 and H6 remain open. OPS-09, OPS-11, and OPS-12 are incomplete.
> - Every “recommendation” below is a proposal for discussion. It is **not** an adopted default and does not indicate school, provider, or security agreement.
> - Nothing here authorises a live SMS, production deployment, real-data import, retention purge, credential transfer, or gate closure.
> - A decision is valid only when recorded in writing with the named authority, date, chosen option, conditions, and evidence link.

**Three decisions block the most work:** the G0 input bundle (**DEC-01–DEC-06**), hosting and data residency (**DEC-15**), and H4 retention/deletion (**DEC-12–DEC-13**). See §8.

---

## 1. One-page asks summary

**In one line:** the school releases the data and approves the live path; the technical owner proposes and proves the production platform, and the school approves it; provider/ops enables and evidences delivery; security approves the controls, custody, and stop authority.

| Audience | Decide now | Provide or confirm | If not decided |
|---|---|---|---|
| **School director / PO** | Sender display and free-text acceptance (**DEC-03–DEC-04**); G0 test authorisation (**DEC-06**); G4 pilot scope, cohort, allowlist, stop authority (**DEC-07**); Arabic copy, currency, opt-out (**DEC-10**); approver policy (**DEC-11**); H4 retention and deletion authority (**DEC-12–DEC-13**); hosting and residency (**DEC-15**); UAT and training participation (**DEC-20–DEC-21**); support hours/SLA (**DEC-22**); handover signatories and go/no-go authority (**DEC-23–DEC-24**) | Named authorised representative and data owner/deputy (**PRE-01**); signed G0 scope and design-gap closure (**PRE-02**); access to anonymised samples (**DEC-01**); three test numbers and consent (**DEC-05**); named pilot cohort and stop authority; legal adviser and position for H4 | G0 stays open; no live SMS, pilot, production use, UAT on real data, training delivery, or handover |
| **Technical owner** | H6 maintenance window and rollback (**DEC-14**); host and region proposal (**DEC-15**); domain/TLS/firewall plan (**DEC-16**); backup/offsite/RPO/RTO design (**DEC-17**); monitoring/on-call/alert mailbox (**DEC-18**); custody execution and vault-key path (**DEC-19**) | Host/region/cost options; release manifest; backup and restore evidence; alert test; runbook owners; 5xx metric source; retention/purge feasibility and dry-run plan (**DEC-12–DEC-13**) | OPS-04/05/06 cannot start; no production evidence; H6 cannot be applied |
| **Provider / ops** | Provider matrix and contract of record (**DEC-02**); approved sender (**DEC-03**); free-text plan/enablement (**DEC-04**); three test numbers accepted (**DEC-05**); G0 test delivery (**DEC-06**); G4 live test and reconciliation contract (**DEC-08–DEC-09**) | Written confirmations, pricing/segments, balance and low-water mark, DLR method, console access, campaign-window contact | G0 cannot pass; G4 cannot be authorised; no reconciliation evidence |
| **Security** | Deletion/anonymisation authority and legal hold (**DEC-13**); H6 role separation (**DEC-14**); monitoring PII and alert routing (**DEC-18**); custody model and vault-key re-encryption or residual risk (**DEC-19**); incident command and stop input (**DEC-24**) | H6 denial/tamper review; custody ledger and break-glass escrow; MFA residual-risk position; evidence store | OPS-01/03/12 cannot close; no credential transfer; no handover |

**Meeting output required:** one chosen option per decision, or an explicit “hold” with a named owner and date; one evidence owner per decision; a recorded gate impact; and the next meeting date. Silence, absence, or a verbal “yes” is not a decision.

**Suggested sequence:** G0 inputs → G0 controlled test → G4 pilot authorisation → G4 live test/reconciliation → H4/H6/hosting in parallel → UAT/training → go/no-go → handover. Do not compress G0 to reach G4.

---

## 2. How decisions are recorded

### 2.1 Decision rules

1. **One ID per decision.** A decision may have parameters (cohort, window, custodian, retention period); record the chosen values under the same ID. Do not bundle unrelated approvals into one signature.
2. **Written authority.** A school decision requires the person named in **PRE-01**. A provider decision requires the account owner or a written delegate. A technical decision requires the technical owner. A security decision requires the security lead.
3. **Conditional approval is allowed.** “Approved subject to evidence X by date Y” is valid and should be recorded as conditional.
4. **A decision does not pass a gate.** Gate evidence is verified separately against the gate record. No decision here changes G0/G4/G5 to Pass.
5. **No verbal approval** for H4 `--execute`, G4 live sending, H6 role changes, or credential transfer. These require a signed record.
6. **Every decision links to evidence.** If the evidence does not exist, the decision is a condition, not a closure.
7. **Status vocabulary:** Open, Conditional, Decided, Withdrawn, Superseded. Every item in this pack is currently **Open — not decided**.

### 2.2 Enabling preconditions

These are not part of the 24-decision register, but no school decision is valid without them.

| ID | Precondition | Owner | Evidence | Needed before |
|---|---|---|---|---|
| **PRE-01** | Name the school’s authorised representative, data owner and deputy, school administrator, backup approver, and who may sign for the school | School director | Written appointment with named acceptance and scope of authority | Any school decision; OPS-12 |
| **PRE-02** | Approve the G0 scope/team baseline and close the design token/screen gap list (G0 criteria 1 and 8) | School director + designer/PO | Signed baseline; design gap list closed or explicitly waived | G0 |

> **G0 note:** the decisions in §3.2 cover samples, provider confirmation, sender, free-text, test numbers, and the controlled test. G0 also requires the scope/design items in **PRE-02**. The provider account/API criterion and ADRs 001–008 are already recorded as Pass in `gate-g0.md`; that does not make G0 pass.

---

## 3. Decision register

### 3.1 Register index

| ID | Decision | Owner role | Blocking gate | Status |
|---|---|---|---|---|
| DEC-01 | Anonymised statement samples and taxonomy acceptance | School director/PO; TL | G0 | Open |
| DEC-02 | Written provider confirmation and contract of record | Provider/ops; TL | G0 | Open |
| DEC-03 | Approved sender ID | Provider/ops; school director | G0 | Open |
| DEC-04 | Free-text plan or explicit enablement | Provider/ops | G0 | Open |
| DEC-05 | Three school-controlled test numbers and consent | School admin; provider/ops | G0 | Open |
| DEC-06 | Authorise the controlled G0 test send | School director; TL | G0 | Open |
| DEC-07 | G4 pilot authorisation, cohort, allowlist, stop authority | School director; TL | G4 | Open |
| DEC-08 | G4 live test-send authorisation | School director; provider/ops | G4 | Open |
| DEC-09 | Provider reconciliation contract | Provider/ops; TL | G4 | Open |
| DEC-10 | Arabic copy, currency, and opt-out wording | School director/PO | G0/G3 | Open |
| DEC-11 | Approver policy, including FND-08 configurability | School director/PO; TL | G0; G1; G5 | Open |
| DEC-12 | H4 retention periods and clock starts | School data owner | H4 | Open |
| DEC-13 | H4 deletion, anonymisation, and legal hold | School data owner; security | H4 | Open |
| DEC-14 | H6 DB-role separation and maintenance window | Technical owner/DBA; security | H6 | Open |
| DEC-15 | Hosting model and data residency | School director; TL | OPS-05/G5 | Open |
| DEC-16 | Domain, TLS, DNS, and firewall | School admin; TL | OPS-05/G5 | Open |
| DEC-17 | Backup encryption, offsite copy, RPO/RTO | School data owner; TL/DBA | OPS-04/G5 | Open |
| DEC-18 | Monitoring, on-call, and alert mailbox | TL; school admin; security | OPS-06/G5 | Open |
| DEC-19 | Credential custody and vault-key re-encryption | Security; school director; TL | OPS-12/G4 | Open |
| DEC-20 | UAT participants, data, scenarios, acceptance | School director; PO/QA | OPS-08/G5 | Open |
| DEC-21 | Training cohort, attendance, environment | PO/Design; school admin | OPS-09/G5 | Open |
| DEC-22 | Support hours, SLA, contacts, evidence store | School director; TL/security | OPS-07/11/12 | Open |
| DEC-23 | Handover signatories and acceptance criteria | School director/PO | OPS-12 | Open |
| DEC-24 | Go/no-go authority, quorum, and launch rule | School director/PO | G4/G5/OPS-10/11 | Open |

**Minimum sequence:** DEC-01 and DEC-02–DEC-04 can start in parallel; DEC-05 precedes DEC-06; the G0 gate record must be signed Pass before DEC-07; DEC-08 precedes the pilot; DEC-09 must be agreed before pilot start. H4, H6, and hosting can run in parallel but must close before production launch.

---

### 3.2 G0 — provider validation and school inputs (DEC-01–DEC-06)

G0 is a sequence, not a single signature. Samples and taxonomy come first; provider confirmation and sender/free-text come next; the test numbers and controlled test come last. A failure at any point leaves G0 open.

#### DEC-01 · G0 — Anonymised statement samples and taxonomy acceptance

**Question.** Will the school provide at least five anonymised XLSX and three anonymised PDF fee statements — including multi-sheet, scanned, and multi-currency examples where available — and who signs the field taxonomy against those samples?

**Options.**
- **A (recommended, not decided):** Provide the full 5+3 set with provenance and redaction confirmation, and name a school reviewer for the taxonomy. The technical lead validates the taxonomy and parser golden files against the samples.
- **B:** Provide 2 XLSX and 1 PDF first, then the remainder. G0 stays open until the minimum 5+3 is met; this is a fallback, not a pass.
- **C:** Continue with synthetic fixtures only. This does not satisfy G0 criterion 2 and cannot support real-data import confirmation.

**Owner:** School director/PO (samples); technical lead (taxonomy).  
**Evidence required:** Sample register (file type, sheet count, scanned/OCR, currency, period, redaction method, provenance); signed taxonomy; updated golden-file suite; parser test results.  
**Blocking gate:** G0 criteria 2–3; G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-02 · G0 — Written provider confirmation and contract of record

**Question.** Will provider/ops obtain a written provider confirmation covering version, endpoint, channel, sender, Syrian coverage, use case, pricing, segments, limits, idempotency, delivery reporting, and current balance — and accept it as the contract of record?

**Options.**
- **A (recommended, not decided):** Full written matrix or provider ticket covering every field, with any exceptions named explicitly. Technical lead reviews accuracy before acceptance.
- **B:** Written confirmation for the pilot scope only (sender, free-text, Syria, price, delivery reporting), with the remaining fields due before wider launch.
- **C:** Console screenshots or oral confirmation only. This is not sufficient for G0 criterion 5 and will not be treated as evidence.

**Owner:** Provider/ops; technical lead reviews technical fields.  
**Evidence required:** Provider letter/ticket with all fields; rate card; segment rules; delivery-report method; idempotency behaviour; current balance; low-water mark; named support contact. No API key in any document.  
**Blocking gate:** G0 criterion 5; G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-03 · G0 — Approved sender ID

**Question.** Which exact sender ID will appear to guardians, and has the provider approved that sender for the school’s use case?

**Options.**
- **A (recommended, not decided):** Approve one alphanumeric sender ID, record it in the provider console, and confirm it in writing. The school director approves the displayed name before any test.
- **B:** Use a provider-default or shared short code for the pilot. This reduces branding control and must be disclosed to guardians; it may be acceptable only if the provider confirms it.
- **C:** No sender approval. G0 cannot pass and no live message may be sent.

**Owner:** Provider/ops; school director approves the displayed sender.  
**Evidence required:** Sender ID in the provider console; written approval; sender registration evidence if the provider requires it; confirmation that the sender is visible to Syrian recipients.  
**Blocking gate:** G0 criteria 5–6; G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-04 · G0 — Free-text plan or explicit enablement

**Question.** Will the Rasel account be moved to a plan — or receive explicit written enablement — that permits free-text SMS to Syrian `+963` numbers for the pilot, or must the pilot use a provider-hosted template?

**Options.**
- **A (recommended, not decided):** Move to a plan or obtain written enablement for free-text SMS to Syria. This preserves the approved Arabic copy and the product’s variable rendering.
- **B:** Use a provider-hosted template for the pilot. The copy must be constrained to the template fields, the school must approve the change, and the product path must be tested against that route.
- **C:** Keep the trial account with no free-text. Live sending is deferred and G0 cannot pass; this is the current state.

**Owner:** Provider/ops.  
**Evidence required:** Plan/enablement confirmation in writing; free-text test result; segment/pricing confirmation; confirmation that the route accepts the approved sender and Syrian destinations.  
**Blocking gate:** G0 criteria 5–6; G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-05 · G0 — Three school-controlled test numbers and consent

**Question.** Which three school-controlled Syrian `+963` numbers, on which networks, may receive the G0 test, who has consented, and what test wording is approved?

**Options.**
- **A (recommended, not decided):** Three staff-controlled numbers across at least two networks, with written holder consent and test text containing no guardian or student data.
- **B:** Start with one number, then add two after the first delivery. G0 remains open until three deliveries are evidenced; this is a fallback.
- **C:** Use guardian numbers or a non-Syrian personal number. This is not acceptable for G0 and must not be done.

**Owner:** School administrator/director; provider/ops coordinates.  
**Evidence required:** Number register (E.164 format, holder, network, consent, date); approved test wording; allowlist configuration in staging; confirmation that no real guardian/student data is used.  
**Blocking gate:** G0 criterion 6; G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-06 · G0 — Authorise the controlled G0 test send

**Question.** Does the school authorise one controlled G0 test SMS per approved number through the approved sender/free-text route, with a named operator, window, and stop authority, once DEC-02–DEC-05 are signed?

**Options.**
- **A (recommended, not decided):** Authorise a single test per number in a recorded window, with a named operator and stop authority, using only the three approved numbers and approved wording.
- **B:** Authorise a provider-console test only. This may prove the provider route but does not produce FeeDesk send/reconciliation evidence; G0 stays open.
- **C:** No test yet. G0 cannot pass; no live send may occur.

**Owner:** School director and technical owner; provider/ops executes.  
**Evidence required:** Signed test authorisation; send log; provider message IDs; delivery receipts; screenshot/report; reconciliation note; zero duplicate; time window; named stop authority.  
**Blocking gate:** G0 criterion 6; G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

---

### 3.3 G4 and school policy (DEC-07–DEC-11)

G4 is the controlled pilot, not a general send. It requires G0 to pass first, a written pilot authorisation, a live test-send, and a reconciliation contract. Arabic copy and approver policy must be settled before campaign approval can be exercised.

#### DEC-07 · G4 — Pilot authorisation, cohort, allowlist, and stop authority

**Question.** Does the school authorise a controlled G4 pilot to a named cohort — proposed 10–20 guardians from one confirmed import, one currency, one approved template — with a written selection/exclusion rule, allowlist mode, shared-phone rule, timing, and named stop authority?

**Options.**
- **A (recommended, not decided):** 10–20 guardians, exact allowlist, exclude complaints, opt-outs, invalid phones, inactive guardians, zero/negative balances, unresolved identity, and shared phones unless explicitly approved. Name one incident commander and one stop authority.
- **B:** Start with 5–10 guardians for the first hour, then expand to 20 only after a clean checkpoint. Slower but lower exposure.
- **C:** Whole-school or multi-currency send. This is not a pilot and is not recommended.

**Owner:** School director; technical lead; provider/ops.  
**Evidence required:** Signed pilot authorisation; cohort list/count; allowlist configuration and test; exclusion reasons; shared-phone decision; window; named stop authority; school communication note. Record whether the allowlist is exact or an empty-list exception is approved (HR-G17).  
**Blocking gate:** G4; OPS-11.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-08 · G4 — Live test-send authorisation

**Question.** Who performs the G4 live test-send, to which approved number(s), with what wording, and what evidence must be captured before the pilot campaign may start?

**Options.**
- **A (recommended, not decided):** One live test to one approved test number, using the approved sender and wording, with a named operator and second reviewer; capture provider message ID, delivery status, sender, body, and timestamp before the pilot.
- **B:** One test per approved number before the pilot. Stronger evidence, more provider cost and time.
- **C:** Start the pilot without a separate live test. Not recommended; G4 evidence would be ambiguous.

**Owner:** School director authorises; provider/ops and technical lead execute.  
**Evidence required:** Signed live-test authorisation; test message ID; provider receipt; delivered body/sender check; no duplicate; no guardian data; reconciliation note.  
**Blocking gate:** G4.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-09 · G4 — Provider reconciliation contract

**Question.** What provider evidence will be accepted for each message, within what window will it be reconciled, who owns reconciliation, and what unresolved/unknown rate is acceptable before the pilot may proceed or close?

**Options.**
- **A (recommended, not decided):** Provider console/report fields with message IDs and timestamps; reconciliation within one business hour; zero unexplained unknowns or duplicates; a named second reviewer for any status correction; the pilot holds if the invariant does not reconcile.
- **B:** Reconcile by next business day and hold the pilot until clean. Slower but accommodates provider latency.
- **C:** Accept provider “accepted” status as delivery. Not sufficient for G4 closure.

**Owner:** Provider/ops (evidence); technical lead (system); school director accepts the result.  
**Evidence required:** Reconciliation contract (fields, cadence, owner, escalation); console/report access; message IDs and idempotency keys; required counts table; unknown handling; second reviewer; signed test result.  
**Blocking gate:** G4; OPS-11.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-10 · School policy — Arabic copy, currency, and opt-out wording

**Question.** Which exact Arabic template version, currency display (ISO code and symbol), school/contact block, and opt-out/communication-restriction wording does the school approve for pilot and production?

**Options.**
- **A (recommended, not decided):** Approve the current draft with a named Arabic reviewer and recorded changes; version and hash the copy. The technical lead implements exactly that version.
- **B:** Return a marked-up version by a set date; the technical lead implements and re-previews before approval.
- **C:** Defer copy. This blocks G0 criterion 7, G3, campaign approval, UAT, and training content; it is the current state.

**Owner:** School director/PO with Arabic reviewer; technical lead implements.  
**Evidence required:** Signed copy with version/hash; reviewer name; preview for at least three recipients across currencies; opt-out wording; character/segment count; currency decision (OD-01); confirmation that student names are omitted unless explicitly approved (OD-03).  
**Blocking gate:** G0 criterion 7; G3; OPS-08; OPS-09.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-11 · School policy — Approver policy and FND-08

**Question.** Should campaign approval remain admin-only for the pilot, or become a configurable per-user permission (FND-08), and who may prepare, approve, or both?

**Options.**
- **A (recommended, not decided):** Keep approval admin-only for the pilot; implement FND-08 configurable approval before wider launch. This avoids delaying the pilot while still recording the gap.
- **B:** Implement FND-08 before the pilot. This delays the pilot but proves separation earlier and closes the FND-08 acceptance item.
- **C:** Allow staff approval now without configurable permission. Not recommended; it weakens the audit and role boundary.

**Owner:** School director/PO; technical lead.  
**Evidence required:** Written approval matrix (roles, users, deputy, self-approval rule); FND-08 acceptance evidence if required; tests for preparer/approver recording, permission drift, and self-approval; audit fields.  
**Blocking gate:** G0 criterion 7; G1/FND-08; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

---

### 3.4 H4 — retention, deletion, and anonymisation (DEC-12–DEC-13)

H4 is a school policy decision plus engineering evidence. A signature alone does not close it. No purge or anonymisation may be enabled before both the policy and the acceptance evidence exist.

#### DEC-12 · H4 — Retention periods and clock starts

**Question.** Does the school approve retention periods and clock starts for source files, staged rows, confirmed fee records, campaign/message snapshots, audit events, backups, and import metadata (R1–R6, R11)?

**Options.**
- **A (recommended for discussion, not decided):** Source and staged rows 12 months from upload; confirmed fee records per school finance/legal policy (5 years after period close if none); campaign/message snapshots 24 months with body/phone redaction at 12 months; audit events 24 months then immutable archive; backups 30 daily + 12 monthly; import metadata 24 months.
- **B:** Privacy-first: source/staged 90 days; snapshots 12 months; backups 30 days; fee records per finance policy. This reduces PII but loses re-review and duplicate-override evidence.
- **C:** Longer or indefinite retention with a legal-hold register. Higher PII exposure and storage; requires a documented legal basis.

**Owner:** School data owner/director with the school’s legal adviser.  
**Evidence required:** Signed S1/S6/S7 with document version and date; clock-start table; confirmation of legal/regulatory obligations; exceptions; acknowledgment that deleted live data remains in backups until expiry.  
**Blocking gate:** H4/OPS-03; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-13 · H4 — Deletion, anonymisation, and legal hold

**Question.** Who may request, approve, and execute deletion or anonymisation; what evidence is retained; and how are legal holds recorded, applied, and released (R7–R10)?

**Options.**
- **A (recommended, not decided):** Written request, identity check, two-person approval (school data owner + FeeDesk operator), named engineer executes, audit counts/IDs only, written legal-hold register, quarterly review.
- **B:** Single school-admin approval with technical execution. Faster but weaker dual control; acceptable only with a named deputy and audit review.
- **C:** No deletion or anonymisation until after the first year. H4 stays open and privacy requests are deferred; not recommended.

**Owner:** School data owner; security; technical lead.  
**Evidence required:** Signed S2–S5/S8–S10; deletion/anonymisation runbook; hold register template; approval form; dry-run report; execute/rollback evidence; deletion receipt without PII; backup caveat.  
**Blocking gate:** H4/OPS-03; G5; OPS-12.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

---

### 3.5 H6, hosting, and operations (DEC-14–DEC-19)

These decisions turn the production path from scaffolding into an operable system. They can run partly in parallel with G0, but production launch cannot occur without them.

#### DEC-14 · H6 — DB-role separation and maintenance window

**Question.** Does the school/technical owner approve applying the H6 separation (`feedesk_owner` / `feedesk_app` / `feedesk_backup`, with break-glass retained) in a named maintenance window with the documented denial tests and rollback?

**Options.**
- **A (recommended, not decided):** Approve a window before G4, keep messaging disabled, apply the roles, run the denial/tamper tests, and rehearse rollback. This removes the runtime owner credential before any live campaign.
- **B:** Defer until after the pilot. The pilot runs on the owner credential and security records the residual risk in writing; not recommended.
- **C:** Use managed PostgreSQL provider roles instead. Requires a provider-specific procedure and equivalent evidence; do not improvise ownership changes.

**Owner:** Technical owner/DBA; security approves.  
**Evidence required:** Signed window and named operator/reviewer; verified database **and uploads** backup; baseline role/owner/trigger capture; denial transcript; owner tamper test on a scratch database; backup-role dump; app smoke; rollback rehearsal; updated runbooks; versioned `grants.sql`; release pin.  
**Blocking gate:** H6/OPS-01; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-15 · Hosting and data residency

**Question.** Where will production run — single VPS, VPS plus managed PostgreSQL, or school-hosted — in which country/region, who administers it, and what residency rule applies to the database, uploads, backups, and logs?

**Options.**
- **A (recommended, not decided):** A single school-approved VPS in a named region with self-managed PostgreSQL; the technical owner administers it; encrypted offsite backups go to an approved location. Accept single-server risk in writing.
- **B:** Application VPS plus managed PostgreSQL in an approved region. Easier backup/PITR and provider maintenance; higher recurring cost and a data-processor review.
- **C:** School-hosted/on-premises. Maximum control; requires school IT capacity, power/connectivity, and an offsite backup path.

**Owner:** School director + technical owner.  
**Evidence required:** Written hosting/residency decision; provider and region; data-flow map; named administrator; cost approval; contract/DPA if applicable; backup and log locations; single-server risk acceptance.  
**Blocking gate:** OPS-05; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-16 · Domain, TLS, DNS, and firewall

**Question.** Which domain will staff and guardians use, who controls the registrar/DNS, who approves firewall rules, and who owns certificate issuance and renewal monitoring?

**Options.**
- **A (recommended, not decided):** A school-owned subdomain, school-controlled registrar with MFA, technical owner managing DNS/Caddy and renewal alerts. Clear school ownership and operational control.
- **B:** A FeeDesk-managed domain delegated by the school. Faster to set up but creates custody and continuity risk.
- **C:** IP-only or HTTP access. Not acceptable for production.

**Owner:** School administrator (registrar) + technical owner.  
**Evidence required:** Domain name; registrar ownership/MFA; DNS records; TLS chain; HTTP→HTTPS redirect; firewall allowlist; external port scan; renewal alert test; certificate expiry monitoring.  
**Blocking gate:** OPS-05; OPS-06; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-17 · Backup encryption, offsite copy, RPO/RTO

**Question.** Does the school approve encrypted backups with an offsite copy, a named key custodian and deputy, 30 daily + 12 monthly retention, and RPO ≤24 h / RTO ≤4 h — or fund PITR and a faster restore path?

**Options.**
- **A (recommended, not decided):** Approve the proposed RPO/RTO and retention; age encryption; offsite copy; offline private key; quarterly restore drill including uploads. This matches the current single-server design.
- **B:** Tighter RPO ≤1 h / RTO ≤2 h with PITR. Higher cost and operational complexity; requires provider support and testing.
- **C:** Looser RPO ≤72 h with daily backups and a written data-loss acceptance. Not recommended for fee data and campaign evidence.

**Owner:** School data owner + technical owner/DBA; security for key custody.  
**Evidence required:** Signed SLA-08/09 and S6; encrypted backup artifact; offsite copy; uploads restore; decrypt drill with the offline key; `--execute` transcript; restore point; named data-loss authority; documented backup expiry.  
**Blocking gate:** OPS-04; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-18 · Monitoring, on-call, and alert mailbox

**Question.** Which monitoring model, on-call arrangement, alert mailbox/on-call channel, 5xx source, and provider balance low-water alert will be used?

**Options.**
- **A (recommended, not decided):** Self-hosted Prometheus/Alertmanager/Loki on the host; school-controlled alert mailbox; business-hours on-call with a named deputy; a delivered and resolved test alert. Lower recurring cost and clearer data control.
- **B:** Hosted monitoring with MFA and paid on-call. Faster to operate but adds recurring cost and a data-processor review.
- **C:** Manual best-effort checks. Not acceptable for the pilot.

**Owner:** Technical owner + school administrator; security reviews PII handling.  
**Evidence required:** Running stack; alert rules loaded; delivered and resolved test alert; named on-call and deputy; alert mailbox; alternative 5xx metric (access logs are disabled for PII); provider balance metric; PII-safe labels; log retention and scrubbing.  
**Blocking gate:** OPS-06; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-19 · Credential custody and vault-key re-encryption

**Question.** Does the school approve the credential custody model — named custodians/deputies, offline break-glass escrow, dual control, approved transfer channel — and authorise either implementing vault-key re-encryption or accepting the residual risk that `PROVIDER_CREDENTIAL_KEY` cannot be rotated safely without a re-encryption tool?

**Options.**
- **A (recommended, not decided):** Implement and rehearse re-encryption before G4, then execute the custody ceremony and ledger. Name custodians/deputies for CR-01–CR-17.
- **B:** Accept documented residual risk with compensating controls and rotate by re-entering the provider key after an approved procedure. Weaker; requires security sign-off and a tested recovery path.
- **C:** Defer custody until after the pilot. OPS-12 stays blocked and no credential transfer occurs; not recommended.

**Owner:** Security + school director + technical owner.  
**Evidence required:** Signed custody model; CR-01–CR-17 custodians/deputies; ledger; sealed break-glass record; transfer evidence; re-encryption procedure/test/rollback; MFA residual-risk decision (HR-G24); rotation schedule.  
**Blocking gate:** OPS-12; G4; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

---

### 3.6 Readiness, people, and authority (DEC-20–DEC-24)

These decisions do not produce technical evidence themselves, but they determine who accepts the evidence, who is trained, who supports the system, and who may launch or stop it.

#### DEC-20 · UAT participants, data, scenarios, and acceptance

**Question.** Does the school approve the UAT plan in `uat-plan.md` — named School UAT Lead, Staff and Admin testers, observer, data mode (A: approved anonymised real data, or B: synthetic), schedule, and acceptance authority — and confirm that no session starts before the G0/G4 entry criteria are met?

**Options.**
- **A (recommended, not decided):** Approve `uat-plan.md` as written: School UAT Lead, separate Staff/Admin testers where staffing allows, QA, Technical Owner, and an observer; Mode A anonymised real data if the data owner approves, otherwise Mode B synthetic; execute all P1 scripts; no open S1/S2; sign `uat-execution-record.md`.
- **B:** Synthetic-only Mode B for the first session, then a second Mode A session after data approval. Slower but reduces data-handling risk.
- **C:** Defer UAT until after the pilot. OPS-08 and G5 remain blocked; this is the current state.

**Owner:** School director/UAT Lead + QA.  
**Evidence required:** Signed UAT plan; participant roster; data approval and anonymisation method for Mode A, or written synthetic approval for Mode B; approved environment; fixture register; execution record; defect log/triage; signed acceptance.  
**Blocking gate:** OPS-08; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-21 · Training cohort, attendance, and environment

**Question.** Which school staff attend training, in which approved environment, over how many Arabic sessions, and what attendance/competency record is required?

**Options.**
- **A (recommended, not decided):** All campaign preparers and approvers (2–6 people); two Arabic sessions on staging with synthetic data; attendance and a short assessment.
- **B:** Train-the-trainer for one or two super-users. Lower cost but coverage and deputy risk.
- **C:** Self-read guide only. Not acceptable for OPS-09.

**Owner:** PO/Design + school administrator.  
**Evidence required:** Approved training environment; cohort roster; delivered sessions; attendance; assessment results; school acknowledgment; updated Arabic guide with ambiguity fixture and support/privacy module.  
**Blocking gate:** OPS-09; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-22 · Support hours, SLA, contacts, and evidence store

**Question.** Does the school approve support hours (proposed Sunday–Thursday business hours), SLA-01–SLA-15 (including S1 30-minute response and RPO/RTO), named contacts/deputies, escalation path, and an approved evidence store?

**Options.**
- **A (recommended, not decided):** Approve the proposed business-hours model, SLA-01–SLA-15, a school mailbox/restricted evidence folder, and record residual risks (no MFA, no 24/7, single server).
- **B:** Fund extended or 24/7 S1 coverage. Higher cost; requires a rota and funding approval.
- **C:** Best-effort support with a written acknowledgment. Not recommended for launch.

**Owner:** School director + technical owner + security.  
**Evidence required:** Signed SLA table; contact register; evidence store named with access list; escalation acceptance; residual risks; tabletop record for unknown outcome, outage, restore, key compromise, and privacy incident.  
**Blocking gate:** OPS-07; OPS-11; OPS-12; G5.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-23 · Handover signatories and acceptance criteria

**Question.** Who signs operational handover, what evidence must be attached, and what conditions or exceptions are acceptable?

**Options.**
- **A (recommended, not decided):** Four-party sign-off (school director, technical owner, security, provider/ops) with an evidence pack and a conditions log.
- **B:** School director and technical owner only. Faster but weaker provider and security accountability.
- **C:** Defer handover until after hypercare. OPS-12 remains open; not recommended.

**Owner:** School director/PO.  
**Evidence required:** Named signatories; signed acceptance/conditions; release manifest (commit, image digests, migration head); gate records; custody ledger; support model; UAT/training evidence; hypercare report.  
**Blocking gate:** OPS-12.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

#### DEC-24 · Go/no-go authority, quorum, and launch rule

**Question.** Who chairs go/no-go, who can call stop, what quorum and evidence are required, and what is the rule for pilot → wider launch?

**Options.**
- **A (recommended, not decided):** School director chairs; technical owner, security, and provider/ops attend; unanimous go required; the school director or named incident commander may stop; wider launch requires a clean pilot report and a new go/no-go.
- **B:** Technical owner chairs with school approval. Faster but school accountability is weaker.
- **C:** No formal go/no-go; proceed when gates pass. Not recommended.

**Owner:** School director + PO.  
**Evidence required:** Written authority matrix; go/no-go checklist; quorum; stop procedure; signed pilot report; escalation contacts; decision record template.  
**Blocking gate:** G4; G5; OPS-10; OPS-11.  
**Due:** [YYYY-MM-DD — set at meeting] · **Status:** Open — not decided.

---

## 4. Meeting agenda, pre-reads, and record

### 4.1 Agenda — 150 minutes

**Meeting date:** [YYYY-MM-DD] · **Chair:** [name/role] · **Recorder:** [name/role] · **Decision deadline:** [YYYY-MM-DD]

**Rule:** G0 is discussed first and is not compressed to make time for later items. If time runs short, stop after H4 and schedule a second session for H6/hosting. The meeting records decisions; it does not pass a gate.

| Time | Item | Decisions | Required attendee | Output |
|---:|---|---|---|---|
| 0–10 | Purpose, authority, and decision rules | PRE-01, PRE-02 | All | Confirmed chair, recorder, and authorised representatives |
| 10–45 | **G0** — samples, provider, sender, free-text, test numbers, test authorisation | DEC-01–DEC-06 | School director, provider/ops, technical lead | Chosen option or hold per decision; evidence owner; test window |
| 45–65 | **G4** — pilot scope, cohort/allowlist, live test, reconciliation | DEC-07–DEC-09 | School director, technical lead, provider/ops | Pilot authorisation or explicit hold; cohort/stop authority; reconciliation owner |
| 65–85 | **H4** — retention, deletion, anonymisation, legal hold | DEC-12–DEC-13 | School data owner, security, technical lead | Signed policy direction or conditions; legal-review owner |
| 85–100 | **H6** — role separation and maintenance window | DEC-14 | Technical owner/DBA, security | Window, operator, reviewer, rollback condition |
| 100–125 | **Hosting and operations** — residency, TLS/DNS/firewall, backup/RPO/RTO, monitoring, custody | DEC-15–DEC-19 | School director, technical owner, security | Host/region; domain/registrar; RPO/RTO; alert mailbox; custody model |
| 125–145 | **School policy and readiness** — copy, approver, UAT, training, support, handover, go/no-go | DEC-10–DEC-11, DEC-20–DEC-24 | School director, PO, QA, security | Named reviewers, cohorts, signatories, authority matrix |
| 145–150 | Record review and next steps | All | All | Decisions recorded; open holds with owners/dates; next meeting date |

**If only 90 minutes are available:** hold G0 (35 min), G4 (20 min), H4 (20 min), and close (15 min). Move H6 and hosting to a second session. Do not merge G0 decisions or treat a provider call as a substitute for the written record.

### 4.2 Pre-read list

| Document | Read by | Focus | Bring to the meeting |
|---|---|---|---|
| [`../m0/gate-g0.md`](../m0/gate-g0.md) | All | G0 checklist, failed test attempts, conditions to pass | Current evidence gaps and any new provider messages |
| [`../m0/decision-log.md`](../m0/decision-log.md) | School/PO, technical lead | OD-01–OD-14, especially currency, approval, retention, opt-out, hosting | School position on each open OD item |
| [`privacy-retention-plan.md`](privacy-retention-plan.md) | School data owner, security, technical lead | R1–R11, clock table, S1–S10, open questions | Legal adviser’s position and any retention constraints |
| [`db-role-separation.md`](db-role-separation.md) | Technical owner, DBA, security | Current gap, target roles, preconditions, evidence list | Proposed window, operator, reviewer, rollback plan |
| [`deployment-readiness.md`](deployment-readiness.md) | Technical owner, school director | Open production decisions 1–10, go/no-go rule | Host/region options and cost; backup/monitoring constraints |
| [`security-review.md`](security-review.md) | Security, technical lead | H4/H6 status, OPS-01/03, residual risks | Security position on H6, deletion, custody, MFA |
| [`../m6/first-campaign-runbook.md`](../m6/first-campaign-runbook.md) | School director, provider/ops, technical lead | §3–§4 preconditions and pilot design; §7 reconciliation; §11 sign-off | Cohort, allowlist, stop authority, test numbers |
| [`../m6/support-model.md`](../m6/support-model.md) | School director, technical owner, security | §6 hours/tiers, §7 severity, §11 SLA-01–15, §12 contacts | Approved hours, contacts, evidence store |
| [`uat-plan.md`](uat-plan.md), [`uat-scripts.md`](uat-scripts.md), [`uat-execution-record.md`](uat-execution-record.md) | School UAT Lead, QA, technical owner | Roles, entry/exit criteria, data modes, scripts, execution record | Data mode, roster, schedule, acceptance authority |
| [`../m6/handover-readiness-review.md`](../m6/handover-readiness-review.md) | All | §10.2 required evidence, §11 gap register, §13 minimum decisions | Position on each Critical/High gap |
| [`../../FeeDesk-Task-Register.csv`](../../FeeDesk-Task-Register.csv) | PO, technical lead | Dependencies, unchecked acceptance items, gate status | Any corrections to task status |

### 4.3 Decision record template

Use one row per decision; do not combine decisions in one record.

```text
Decision ID:
Decision (option chosen):
Conditions / exceptions:
Decided by (name, role, authority):
Date and time:
Evidence link (document, ticket, provider record):
Next action / owner / due:
Gate impact: does not pass a gate by itself; evidence still required:
Review date:
```

---

## 5. Bilingual request / email template

### 5.1 Arabic

```text
الموضوع: طلب قرارات خارجية لمشروع FeeDesk — اجتماع [التاريخ]

حضرة [الاسم / الجهة]،
تحية طيبة وبعد،

يسرّنا دعوتكم إلى اجتماع اتخاذ القرارات الخارجية لمشروع FeeDesk، وذلك في [التاريخ] الساعة [الوقت] في [المكان / رابط الاجتماع].

الغرض من الاجتماع هو تسجيل القرارات التي لا يستطيع فريق المشروع اتخاذها نيابة عن المدرسة أو المزود أو الجهة الأمنية، وربط كل قرار بالدليل المطلوب والبوابة التي يفتحها. الحزمة المرفقة هي:
docs/m5/external-decision-pack.md

المحاور المطلوبة:
1. G0: العينات المجهولة، تأكيدات المزود، المرسل، تمكين الرسائل النصية الحرة، أرقام الاختبار الثلاثة، وتفويض الاختبار.
2. G4: تفويض التجربة، مجموعة المستلمين، الاختبار الحي، وعقد المطابقة مع المزود.
3. H4: مدد الاحتفاظ، الحذف، إخفاء الهوية، وصلاحيات الحجز القانوني.
4. H6 والاستضافة: فصل أدوار قاعدة البيانات، الاستضافة والموقع، TLS/DNS/الجدار الناري، النسخ الاحتياطي، والمراقبة.
5. القرارات المتبقية: النسخ العربي، سياسة المعتمد، UAT، التدريب، الدعم، التسليم، وصلاحية المضي/التوقف.

نرجو قبل الاجتماع:
- تأكيد أسماء الحاضرين وصلاحيتهم في اتخاذ القرار.
- قراءة الوثائق المحددة في قائمة القراءة المسبقة.
- إحضار التأكيدات أو الوثائق المطلوبة لكل قرار.
- تحديد القرارات التي تحتاج إلى جهة أخرى، واسم صاحب القرار البديل.

ملاحظة مهمة: لا يعني حضور الاجتماع أو الموافقة على قرار أن أي بوابة قد اجتازت، ولا يجيز الإرسال الحي أو النشر الإنتاجي أو معالجة بيانات حقيقية أو حذف بيانات أو نقل بيانات الدخول. تبقى G0/G4/G5 وH4/H6 مفتوحة حتى تُستكمل الأدلة وتُسجّل القرارات كتابةً.

نرجو الرد بتأكيد الحضور واسم الممثل المخوّل قبل [التاريخ].

مع التقدير،
[الاسم]
[الدور]
[الهاتف]
[البريد الإلكتروني]
```

### 5.2 English

```text
Subject: FeeDesk external decision meeting — [date]

Dear [name],

We are requesting your attendance at the FeeDesk external decision meeting on [date] at [time] at [location / meeting link].

The purpose is to record the decisions that the project team cannot take on behalf of the school, the provider, or security, and to link each decision to the evidence it requires and the gate it affects. The attached pack is:
docs/m5/external-decision-pack.md

Decisions to be addressed:
1. G0: anonymised samples, provider confirmations, sender, free-text enablement, three test numbers, and test authorisation.
2. G4: pilot authorisation, cohort, live test, and the provider reconciliation contract.
3. H4: retention periods, deletion, anonymisation, and legal hold.
4. H6 and hosting: database-role separation, hosting/residency, TLS/DNS/firewall, backup, and monitoring.
5. Remaining decisions: Arabic copy, approver policy, UAT, training, support, handover, and go/no-go authority.

Before the meeting, please:
- confirm the attendees and their authority to decide;
- read the documents listed in the pre-read list;
- bring the confirmations or documents required for each decision;
- identify decisions that need another authority and name the alternate decision-maker.

Important: attendance or approval does not mean any gate has passed, and does not authorise live SMS, production deployment, real-data processing, deletion, or credential transfer. G0/G4/G5 and H4/H6 remain open until the evidence is complete and decisions are recorded in writing.

Please confirm attendance and the authorised representative by [date].

Regards,
[Name]
[Role]
[Phone]
[Email]
```

### 5.3 Reply template

```text
Attendance: [ ] Yes  [ ] No  [ ] Delegate: ____________________
Authority: [ ] Can decide  [ ] Can recommend only  [ ] Observer
Decisions we can decide at the meeting: ____________________
Decisions requiring another owner: ____________________ / owner: ____________________
Evidence we will bring: ____________________
Preferred language: [ ] Arabic  [ ] English  [ ] Both
```

---

## 6. What can start immediately after each decision

These actions may start once the decision is recorded, **subject to the no-live-send and no-production-change constraints in §7**. The only live sends permitted are the specifically authorised G0/G4 tests in DEC-06 and DEC-08. A decision starts work; it does not close a gate.

| Decision | Immediate next action | Owner | Evidence it creates |
|---|---|---|---|
| DEC-01 | Validate taxonomy against real samples; update golden files and parser fixtures; complete the sample register | Technical lead | G0 criteria 2–3 evidence |
| DEC-02 | Lock provider contract tests; configure pricing/segments/DLR expectations; file the written matrix | Technical lead / provider | G0 criterion 5 evidence |
| DEC-03 | Configure the approved sender in staging; update the test plan; do not send live | Technical lead / provider | Sender approval evidence |
| DEC-04 | Configure the free-text or template route in staging; update copy constraints | Technical lead / provider | Route/plan evidence |
| DEC-05 | Register the three numbers; verify E.164; update the staging allowlist; no live send | Technical lead / school admin | Test-number register |
| DEC-06 | Execute the controlled test with a named operator; capture provider IDs and receipts; reconcile | Provider / technical lead | G0 criterion 6 evidence |
| DEC-07 | Finalise cohort and allowlist; book the window; name the incident commander; rehearse with the fake provider | Technical lead / school | G4 authorisation package |
| DEC-08 | Prepare and execute the live test; record message ID, sender, body, and delivery status | Provider / technical lead | G4 live-test evidence |
| DEC-09 | Build the reconciliation worksheet; obtain console access; name the second reviewer; dry-run the counts invariant | Provider / technical lead | Reconciliation contract and dry run |
| DEC-10 | Create the approved template version; preview three recipients; count segments; update UAT/training scripts | Technical lead / school | Copy sign-off and template hash |
| DEC-11 | Configure approval roles and tests; add FND-08 to the pre-launch backlog if deferred | Technical lead | Approval matrix and FND-08 evidence (if chosen) |
| DEC-12 | Populate `retention_until` in dry-run; document null behaviour; design the purge CLI; no deletion | Backend engineer | H4 dry-run design |
| DEC-13 | Write the deletion/anonymisation/hold runbooks and approval form; dry-run only | Security / technical lead | H4 procedure and dry-run evidence |
| DEC-14 | Schedule the window; take a verified backup; capture the baseline; apply on staging; run denial tests | DBA / technical owner | H6 evidence pack |
| DEC-15 | Provision the host/region; record cost and administrator; draft the data-flow/residency map | Technical owner | OPS-05 start |
| DEC-16 | Obtain registrar access; create DNS records; configure Caddy; test certificate issuance and renewal | Technical owner | OPS-05 TLS evidence |
| DEC-17 | Configure age recipient and offsite target; run an encrypted backup; restore uploads; decrypt with the offline key | Technical owner / DBA | OPS-04 evidence |
| DEC-18 | Deploy the monitoring stack; load rules; deliver and resolve a test alert; wire the balance metric | Technical owner | OPS-06 evidence |
| DEC-19 | Build the custody ledger; name custodians/deputies; implement and rehearse re-encryption; plan the ceremony | Security / technical owner | OPS-12 evidence |
| DEC-20 | Finalise the UAT plan, data mode, and roster from `uat-plan.md`; schedule; execute; triage defects | QA / school | OPS-08 evidence |
| DEC-21 | Book the environment and sessions; prepare the roster; deliver; assess; record attendance | PO / school admin | OPS-09 evidence |
| DEC-22 | Publish contacts, SLA, and evidence store; run a tabletop; record residual risks | Technical owner / school | OPS-07 evidence |
| DEC-23 | Assemble the handover evidence pack; schedule sign-off; open the conditions log | PO | OPS-12 evidence |
| DEC-24 | Publish the authority/quorum matrix; schedule the pilot go/no-go; record the decision | School director / PO | G4/G5 governance evidence |

---

## 7. Cannot proceed until

### 7.1 Live messaging and G0

- **No live SMS, including the G0 test,** until DEC-02–DEC-06 are recorded, the three test numbers are confirmed, and the approved sender/free-text route is verified. The current state has no delivered test; the earlier `local_sms` and `int_sms` attempts failed.
- **G0 cannot pass** until the 5+3 samples and taxonomy (DEC-01), provider confirmation (DEC-02), sender (DEC-03), free-text or approved template route (DEC-04), test numbers (DEC-05), delivered test (DEC-06), and PRE-02 scope/design sign-off are complete. A provider console screenshot is not a substitute for the delivered test.
- **No real-data import confirmation** until the sample taxonomy is accepted and the real statement formats have been validated.

### 7.2 G4 pilot and live campaign

- **No G4 pilot authorisation** until the G0 gate record is verified and signed Pass, DEC-07–DEC-09 are signed, and the technical pre-flight (host, TLS, backup, monitoring, exactly one worker, stop procedure) is complete.
- **No live campaign** until the pilot authorisation names the cohort, allowlist mode, shared-phone rule, stop authority, and go/no-go attendees. A non-empty allowlist blocks every non-listed recipient; an empty allowlist requires a written exception.
- **No wider rollout** until the pilot report is signed, reconciliation is clean or every unknown has an owner, and a new go/no-go is recorded under DEC-24.

### 7.3 Production deployment and operations

- **No production deployment evidence** until DEC-15 (host/residency) and DEC-16 (domain/TLS/firewall) are decided and the host is provisioned. The current package has no host, DNS, certificate, image build, or deploy record.
- **No production launch** until H4 and H6 are closed, OPS-04/05/06/07 are verified, UAT and training are complete, and DEC-24 records a go.
- **No H6 role change** until DEC-14 is signed, a verified database **and uploads** backup exists, the worker is stopped with messaging disabled, the window and rollback operator are named, and the denial/tamper tests are ready.
- **No `feedesk_app` runtime** until the Compose migration/runtime split is implemented; applying roles first would leak the owner credential into the API/worker.
- **No offsite/encrypted backup `--execute`** until DEC-17 names the key custodian/deputy, the offsite destination, and the decrypt path. The local drill was database-only and unencrypted.
- **No monitoring/alerting claim** until DEC-18 produces a running stack, a delivered and resolved test alert, an alternative 5xx source, and the provider balance metric. Caddy access logging is disabled for PII, so the old 5xx source is inert.
- **No vault-key rotation** until DEC-19 and the re-encryption procedure/test exist. Rotating `PROVIDER_CREDENTIAL_KEY` without re-encryption makes stored provider credentials unreadable.

### 7.4 Data, privacy, and handover

- **No retention purge `--execute`** until DEC-12 and DEC-13 are signed, the S1–S10 acceptance evidence exists, `retention_until` is populated, a dry-run matches expectations, legal holds are excluded, and the deletion runbook is approved. No deletion may be scheduled now.
- **No formal UAT session** until DEC-20 is signed, the `uat-plan.md` entry criteria (including G0/G4) are met, the data handling is approved under H4, and the environment is approved. Synthetic Mode B may be planned, but it does not satisfy OPS-08 or replace G0/G4.
- **No training delivery** until DEC-21 is signed, the approved environment exists, and the Arabic copy is approved under DEC-10. The current training evidence is an internal rehearsal only.
- **No support/SLA commitment** until DEC-22 is signed. Until then, support is best effort and must be described that way; the contact register and evidence store are blank.
- **No handover or credential transfer** until DEC-23 is signed, OPS-11 hypercare is complete, the custody ledger is populated, and the gate records exist. No credential has been transferred.
- **No go/no-go** until DEC-24 is signed and the required evidence is attached. No gate passes by implication, and no document in this pack may be cited as a launch authorisation.

---

## 8. The three decisions that block the most work

### 1. G0 input bundle — DEC-01 to DEC-06

**Why it blocks the most:** it gates G0, and G0 gates every live message, the G4 pilot, provider reconciliation, real-sample taxonomy, realistic UAT, and credible training. It also has the longest external lead time: school samples, a named school reviewer, provider commercial action, sender approval, free-text enablement, three consented numbers, and a delivered test.

**What unblocks it:** the school releases the 5+3 samples and names the taxonomy reviewer; provider/ops delivers the written matrix, sender, and free-text confirmation; the school names three test numbers and authorises one controlled test; the technical lead captures the provider record and reconciles it.

**Do not** treat the two failed test attempts as progress toward G0. The account/API criterion is Pass; the gate is not.

### 2. Hosting and data residency — DEC-15

**Why it blocks the most:** without a host and region, there is no production deployment, no TLS/DNS/firewall verification, no offsite backup destination, no monitoring stack, no H6 maintenance window, and no G5 evidence. It is the root dependency for OPS-04/05/06 and for the production half of the handover.

**What unblocks it:** the school chooses single VPS, VPS + managed PostgreSQL, or school-hosted; names the country/region and administrator; accepts or rejects the single-server risk; and approves the cost and any data-processor terms. The technical owner then provisions the host and starts DEC-16 and DEC-17.

### 3. H4 retention/deletion — DEC-12 and DEC-13

**Why it blocks the most:** it gates OPS-03, privacy closure, real/anonymised UAT, production data use, the purge/anonymisation implementation, backup retention design, and handover. It is also the longest policy lead time because it needs the school’s legal adviser, a data owner, a deputy, and a legal-hold process.

**What unblocks it:** the school signs the retention periods and clock starts, the deletion/anonymisation authority, and the legal-hold process; engineering then builds the dry-run, purge, and anonymisation evidence. A signature alone does not close H4; the acceptance evidence in `privacy-retention-plan.md` is still required.

**Next after these three:** G4 pilot authorisation and reconciliation (DEC-07–DEC-09), then Arabic copy and approver policy (DEC-10–DEC-11), then UAT/training/support (DEC-20–DEC-22).

---

## 9. Document control

| Version | Date | Change | Author |
|---|---|---|---|
| 1.0 | 4 November 2026 | Consolidated external decision pack: asks by audience, 24-decision register, agenda, pre-reads, bilingual request, start-after-decision table, cannot-proceed list, top-three blockers. No decision taken; no gate passed. | Documentation and codemap specialist |

**Related documents:** [`gate-g0.md`](../m0/gate-g0.md) · [`decision-log.md`](../m0/decision-log.md) · [`deployment-readiness.md`](deployment-readiness.md) · [`security-review.md`](security-review.md) · [`privacy-retention-plan.md`](privacy-retention-plan.md) · [`db-role-separation.md`](db-role-separation.md) · [`handover-readiness-review.md`](../m6/handover-readiness-review.md) · [`first-campaign-runbook.md`](../m6/first-campaign-runbook.md) · [`support-model.md`](../m6/support-model.md) · [`FeeDesk-Task-Register.csv`](../../FeeDesk-Task-Register.csv)

**Explicit non-claims:** this pack is not legal advice, not a gate record, not a launch authorisation, not a UAT or training record, and not evidence that any production, provider, backup, monitoring, retention, or custody action has occurred.
