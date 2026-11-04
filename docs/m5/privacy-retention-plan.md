# M5 — Retention and Deletion Decision Package (H4)

**Status:** Open. This is a decision package and design plan, not an implemented purge and not an adopted policy. No deletion will be enabled until the school signs the decisions below. Recommendations are clearly labelled proposals for discussion; they are **not** school decisions.

**Date:** 4 November 2026  
**Version:** 1.0 (draft for school decision; not approved)  
**Prepared by:** FeeDesk documentation pass (pre-G4)  
**Decision owner:** School data owner (to be named) with the FeeDesk technical lead  
**Related:** `security-review.md` (H4), `deployment-readiness.md`, `../runbooks/backup-restore.md`, ADR 008, decision-log `OD-04`.

## Why H4 is still open

- `SourceFile.retention_until` exists in the schema but is never populated.
- No purge, deletion, or anonymization job exists.
- Source files, staged raw rows, and guardian/student PII are retained indefinitely.
- The duplicate-override path writes a second physical copy of the source file.
- Backups are separate artifacts: deleting live data does not delete encrypted backups.
- The audit table is append-only, so audit retention needs an owner-run archive procedure, not an application purge.

Until the school signs the decisions below and the engineering evidence is attached, H4 remains open and no deletion may be scheduled.

## Decision table

The school chooses one option per row. "Recommended option" is a starting point for discussion, not a default that is already in force. Periods may be combined or varied by data type. These are operational proposals, not legal advice; the school should confirm its legal obligations with its adviser (S7).

| ID | Decision | Options for the school | Recommended option (not adopted) | Tradeoffs / consequences | Implementation hook |
|---|---|---|---|---|---|
| R1 | Retention of original statement files (`source_files`) | 90 days; 12 months; academic year + 1; indefinite | 12 months from upload for confirmed or review-required batches, then delete the private object; allow a shorter period if the school archives outside FeeDesk | Longer keeps re-review, audit, and duplicate-override evidence; shorter reduces PII and storage but loses the original document. Fee records and audit events remain either way | `SourceFile.retention_until`; purge CLI deletes the storage object first, then the row only after object deletion succeeds |
| R2 | Retention of staged rows (`staged_rows`, raw and normalized JSON) | Same period as R1; delete `raw_data` at confirmation and keep normalized values; 90 days after confirmation | Keep staged rows for the R1 period, then delete them. If row-level provenance must outlive R1, export a non-PII provenance record first | Raw rows contain the fullest PII copy. Deleting staged rows sets `fee_balances.source_row_id` to NULL, reducing provenance. Keeping them duplicates PII | `staged_rows`; FK `fee_balances.source_row_id` is `ON DELETE SET NULL` |
| R3 | Retention of confirmed fee records (`fee_balances`) | Current academic year + 1; 5 years; 10 years; school finance/legal policy | Follow the school's finance/legal retention period. If none exists, use 5 years after the fee period closes as a discussion starting point, subject to school/legal confirmation | Collection and audit need history; data minimization favours deletion. Hard deletion is restricted by guardian/import foreign keys, and campaign snapshots may retain related PII separately. Prefer archive/delete only when no dependency remains | `fee_balances`; school finance policy; archive/export procedure |
| R4 | Campaign and message snapshots | Keep with campaign indefinitely; 24 months; redact bodies/phones at 12 months | Keep campaign metadata, counts, and terminal message status for audit; redact message bodies and recipient name/phone snapshots after 12 months unless a legal hold applies | Snapshots prove what was approved and sent, but they duplicate guardian PII and message content. Redaction must not break campaign results or audit evidence | `campaign_recipients` snapshots; `messages.provider_payload_redacted`; redaction job, not row deletion |
| R5 | Audit events (`audit_events`) | Indefinite; 24 months; 5 years | 24 months, then an immutable archive; owner-run archival or partitioning because the append-only trigger blocks `DELETE` | Audit supports accountability and incident review, but may still contain masked PII, names, actor IDs, and IP addresses. Legal hold must override expiry. The app role must never purge audit | `audit_events`; owner-only archive/partition procedure; no app-role delete |
| R6 | Backups (database and uploads) | 30 daily + 12 monthly; 30 days only; 12 months only; add PITR | Confirm 30 daily + 12 monthly with encryption and offsite copies; expire artifacts by policy; preserve named artifacts under legal hold | Recovery vs retention/privacy. Deleted live data persists in backups until expiry. Monthly archives are manual. PITR adds cost and operational complexity | `scripts/feedesk_backup.py`; `BACKUP_RETENTION_DAYS`; manual monthly archive; backup index for holds |
| R7 | Cancelled or failed imports | Delete immediately; 7-day grace; 30-day grace; retain for audit | 30-day grace, then delete the source file and staged rows; keep import-batch metadata and audit without raw PII. Delete immediately on a written request. Never delete confirmed fee records | Immediate deletion is strongest for privacy but removes duplicate-detection and investigation evidence. A grace period costs storage and keeps PII longer | Import cancel/failure path; purge CLI; `import_batches` status and audit |
| R8 | Guardian/student data when a relationship ends | Hard delete; anonymize identifiers; retain | Anonymize guardian/student names, phones, and relationship identifiers; keep fee balances and audit IDs. Hard delete only when no financial, campaign, message, or audit dependency exists | Erasure requests favour deletion, but fee and audit history may require retention. Foreign keys use `RESTRICT`/`SET NULL`; snapshots must be redacted too. Re-import can recreate identities unless a tombstone is kept | `guardians`, `guardian_contacts`, `students`, `guardian_student_relationships`; snapshots; anonymization procedure |
| R9 | Who approves a deletion and what evidence is retained | Single administrator; two-person approval; school director + technical operator | Written request, identity check, and two-person approval (school data owner + FeeDesk operator); execute by a named engineer; audit counts/IDs only; issue a deletion receipt without PII | Two-person approval reduces mistake and abuse risk but is slower. A small school may not have two available people; name a deputy and an emergency path | Audit event; deletion/anonymization runbook; approval record |
| R10 | Legal hold | No hold; hold register; hold per named matter | Written hold register that suspends purge for named students, imports, campaigns, or date ranges; release only in writing; flag backup artifacts separately; review quarterly | Holds protect legal/disciplinary needs but increase PII retention and storage. Subject mapping must be reliable, and encrypted backups cannot be selectively edited | Hold list/flag checked by the purge job; backup manifest index; not implemented |
| R11 | Import-batch metadata (`import_batches`) | Keep with source file; 24 months; indefinite | Keep non-PII batch metadata (IDs, counts, totals, status, timestamps, uploader ID) for 24 months for audit/reporting; remove or scrub `source_filename` if it contains PII at R1 expiry | Metadata supports duplicate detection, reporting, and audit but can include a filename with names. Long retention is low cost but keeps a small PII copy | `import_batches`; `source_filename`, `file_hash`; audit references |

### Retention clock

The school must also confirm when each period starts. Proposed starting points for discussion:

| Data | Proposed clock start |
|---|---|
| Source files and staged rows | Upload time |
| Cancelled imports | Cancellation time |
| Confirmed fee records | Fee period close, or confirmation if the school prefers |
| Campaign/message snapshots | Campaign approval or completion |
| Audit events | Event creation |
| Backups | Backup completion |
| Guardian/student data | End of relationship or written request |

These are proposals. A period without an agreed start event is not implementable.

## Explicit school sign-off list

Each item must be signed by the school's authorised representative. A signature approves the referenced decision; it does not authorise the engineering team to skip the acceptance evidence below.

| ID | Sign-off statement | Decision refs | School signatory | Role | Date | Signed |
|---|---|---|---|---|---|---|
| S1 | Approve the retention periods and clock starts for source files, staged rows, confirmed fee records, campaign/message snapshots, audit, backups, and import-batch metadata | R1–R6, R11, clock table |  |  |  | [ ] |
| S2 | Approve when cancelled or failed imports are deleted, and confirm that confirmed fee records are never deleted by the cancel path | R7 |  |  |  | [ ] |
| S3 | Approve whether guardian/student data is anonymized or deleted at end of relationship, including campaign/message snapshots | R8 |  |  |  | [ ] |
| S4 | Approve who may request, approve, and execute a deletion, and what evidence is retained | R9 |  |  |  | [ ] |
| S5 | Approve the legal-hold register, release authority, and quarterly review | R10 |  |  |  | [ ] |
| S6 | Confirm backup retention, encryption, offsite storage, and RPO/RTO; accept that deleted live data remains in backups until expiry | R6 |  |  |  | [ ] |
| S7 | Confirm the school's legal/regulatory retention obligations, or record that none were identified for this data | R1–R11 |  |  |  | [ ] |
| S8 | Approve the deletion/anonymization runbook and any guardian/student communication wording | R7–R11 |  |  |  | [ ] |
| S9 | Authorise populating `retention_until` and running the purge CLI in `--dry-run`; `--execute` stays disabled until S1–S8 are signed | R1–R7, R11 |  |  |  | [ ] |
| S10 | Name the school data owner and a deputy for deletion approvals | R9 |  |  |  | [ ] |

**Record the signed version:** school name, document version, representative, date, and any exceptions. A verbal approval is not sufficient for `--execute`.

## Proposed mechanism (design only)

- Set `SourceFile.retention_until` at upload from a configurable period (no default deletion until approved).
- Add a scheduled purge CLI (`python -m app.retention --dry-run`, then `--execute`) that:
  - finds expired source files and imports;
  - deletes the private file object;
  - deletes or anonymizes staged raw/normalized data under the signed policy;
  - preserves confirmed fee balances and campaign/message snapshots unless the school requires deletion or redaction;
  - records counts and IDs (not raw PII) in audit;
  - refuses to purge anything referenced by an approved campaign unless a separate signed policy allows it.
- Reuse the existing `SourceFile` for duplicate overrides instead of writing a second physical copy.
- On import cancel, schedule deletion; do not delete confirmed financial records.
- Define a separate anonymization procedure for guardians/students; do not silently rewrite fee balances.
- Backups: retention/expiry is applied to backup artifacts separately; deleting live data does not delete encrypted backups automatically.

## Engineering acceptance evidence required

All items remain open. School sign-off alone does not close H4.

- [ ] S1–S10 signed and recorded with a document version and date.
- [ ] `retention_until` populated on upload; null/unknown behaviour documented.
- [ ] Dry-run report matches expected records and excludes legal holds.
- [ ] Transactional purge with failure rollback.
- [ ] Audit event with counts and IDs only, no raw PII.
- [ ] Cancel path tested: file and staging removed, confirmed fee records untouched.
- [ ] Import-batch metadata and `source_filename` handled per R11.
- [ ] Duplicate override no longer creates a second physical copy.
- [ ] Backup expiry documented and tested; a live-data deletion does not imply backup deletion.
- [ ] Anonymization procedure tested; fee balances and audit references preserved.
- [ ] Legal-hold exclusion tested, including a released hold.
- [ ] Mistaken-purge rollback/restore path tested.
- [ ] Deletion/anonymization runbook approved.

## Open questions for the school

1. Is hard deletion of confirmed fee records ever required, or is a read-only archive sufficient?
2. Can audit events be archived after the retention period given the append-only trigger, and who owns that archive?
3. Should backups age out personal data faster than the proposed 12 months?
4. Who is the school's legal/data-protection adviser for retention and erasure questions?
5. Are Arabic and English deletion/erasure notices required, and who sends them?
6. Does the fee-record clock start at confirmation or at the close of the fee period?

Until these are answered and signed, H4 remains open: no policy is adopted, no purge job exists, and no deletion is enabled.
