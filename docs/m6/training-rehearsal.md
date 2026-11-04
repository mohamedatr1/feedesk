# FeeDesk M6 — Internal Training Rehearsal

**Document ID:** M6-REH-02  
**Date:** 4 November 2026  
**Status:** **Internal rehearsal only.** Not school training delivery, UAT, G0/G4/G5, handover acceptance, or launch. No live SMS or provider call occurred.  
**Related:** `training-guide-ar.md`, `pilot-rehearsal.md`, `../m2/verification.md`, `../m4/verification.md`.

## 1. Scope and non-claims

This rehearsal walks the trainer through the principal staff/admin screens using synthetic data and the fake provider. It validates navigation, labels, controls, layout, and console health. It does **not**:

- replace a school training session or attendance record;
- validate Arabic comprehension by school staff;
- exercise live messaging or production infrastructure;
- claim OPS-09, OPS-11, OPS-12, UAT, G0/G4/G5, or launch.

## 2. Environment

| Item | Value |
|---|---|
| Web / API | `http://localhost:3000` / `http://127.0.0.1:8000` |
| Staff account | `qa_rehearsal_trainer` (role `staff`, synthetic) |
| Admin account | `qa_rehearsal_trainer_admin` (role `admin`, synthetic) |
| Data | Synthetic only; review import `39db6d7b-f9f2-44bb-857f-67e907616c86` |
| Provider | Fake / dry-run only; no network |
| Browser | Playwright Chromium, headless |

No bulk exclusion, guardian link, campaign approval, or credential rotation was performed in this rehearsal; those flows are already browser-verified in `docs/m2/verification.md`, `docs/m4/verification.md`, and `pilot-rehearsal.md`.

## 3. Modules exercised

| # | Module | Result | Evidence/notes |
|---|---|---|---|
| 1 | Staff login and dashboard | Pass | Dashboard heading, totals, action queue, activity rendered |
| 2 | Statements list | Pass | Import history rendered |
| 3 | Review page controls | Pass | Bulk exclude/restore bar, row checkboxes, guardian action present |
| 4 | Guardian privacy in dialog | Pass | Dialog uses masked phone values; the review table keeps the editable full value by design |
| 5 | Campaign list | Pass | Campaign list rendered |
| 6 | Messages list | Pass | Message history rendered; no resend action |
| 7 | Provider settings (admin) | Pass | Provider panel loaded; fake/dry-run state visible |
| 8 | Operations page (admin) | Pass | Read-only safety line and due/stale/issues sections rendered |
| 9 | Users/templates (admin) | Pass | Admin pages rendered |
| 10 | Audit page (admin) | Pass | Page loaded without console errors; content assertion was inconclusive, not a functional failure |

## 4. Layout and console

| Screen | 1024 | 1440 | Console errors |
|---|---|---|---|
| Review | `scrollWidth=1024`, `clientWidth=1024` | `1440/1440` | 0 |
| Settings/provider | — | `1440/1440` | 0 |
| Operations | `1024/1024` | `1440/1440` | 0 |
| Staff dashboard | — | `1440/1440` | 0 |

No horizontal document overflow was observed on the checked screens.

## 5. Findings and trainer notes

1. **Review-table phone is editable and full.** The review ledger intentionally keeps the source phone for inline correction; the guardian-resolution dialog shows masked phones. Trainers must distinguish the edit field from list masking and must not read numbers aloud.
2. **No guaranteed `AMBIGUOUS_GUARDIAN` fixture** exists in the synthetic sample set. Prepare and pre-test an ambiguity fixture before a real training session.
3. **No resend control** exists; the UI contains explanatory “no resend” copy, not a resend button. Verify by controls, not by text search.
4. **Provider-not-configured messages** may appear in English alongside the Arabic badge; explain them as configuration state, not an outage.
5. **Seed template copy is not school-approved** (G3). Do not present it as final wording.
6. **Admin approval is role-based** because per-user approval permission (FND-08) is not implemented.

## 6. Rehearsal verdict

**Internal rehearsal pass with noted trainer gaps.** The main navigation and safety copy work with synthetic data, but formal OPS-09 training delivery remains blocked until G0/G4 and a school-approved environment exist and a school trainee/attendance record is available.

| Role | Name | Date | Signature |
|---|---|---|---|
| Internal rehearsal lead |  | 4 Nov 2026 |  |
| School trainer |  |  |  |
| School trainee |  |  |  |

**Label: internal rehearsal — not school training.**
