# M2 — OCR Decision Memo

**Status:** **Assisted local OCR implemented (4 November 2026).** Scanned PDF pages are rendered locally and processed with Tesseract `ara+eng`; candidate rows are staged with `OCR_USED`/confidence warnings and must be reviewed and corrected before confirmation. OCR is never auto-confirmed. Real-school OCR accuracy, school approval, and a measured manual baseline remain pending; detection-only is the fallback when the engine/language data is unavailable. M2 formal acceptance remains blocked on real school samples and G0/G1.

**Implementation update (4 November 2026):**
- Local-only Tesseract OCR (`ara+eng`, 300 DPI, TSV word reconstruction) reconstructs rows and RTL column order.
- OCR pages produce normal staged rows, a source page reference, `OCR_USED`, and `LOW_CONFIDENCE_EXTRACTION` when confidence is low.
- Currency/phone heuristics are shared with the normal PDF path; OCR misreads remain row warnings for human correction.
- OCR can be disabled with `OCR_ENABLED=false`; missing Tesseract/Arabic data degrades to the previous `SCANNED_PDF` warning.
- The scanned fixture now stages 6 candidate rows (5 valid, 1 requiring correction), not zero.

**Date:** 4 November 2026  
**Decision owner:** Technical lead (proposed); school input required if OCR is revisited  
**Related:** ADR 004, decision-log `OD-08`, `api-contract.md`, `verification.md`, `../design/m2-import-screens.md`.

## Current behaviour and evidence

- The PDF parser uses `pdfplumber` for text and table extraction.
- A page with fewer than 10 characters after trimming, and no extracted table rows, is counted as a scanned page.
- If any page is scanned, the import returns `review_required` with zero invented rows and the warning `SCANNED_PDF`.
- The UI message is `الملف يبدو ممسوحًا ضوئيًا.` with the guidance `لم نتمكن من قراءة نص من هذا الملف. تحتاج الكشوف الممسوحة إلى ملف نصي أو إلى إدخال يدوي.`
- The scanned fixture `sample-02-scanned-image.pdf` produced zero rows, the `SCANNED_PDF` warning, and no crash on 3 November 2026.
- There is no OCR dependency, no cloud OCR call, and no image/OCR pipeline.
- There is also **no in-app manual row-entry screen for a zero-row PDF**. "Manual handling" today means uploading a text-based file or re-keying the statement into a supported XLSX/template outside FeeDesk and uploading that. Row editing exists only after rows have been staged.

This is deliberately conservative: a financial import must fail visibly rather than invent values.

## Options considered

| Option | What it means | Advantages | Disadvantages / risks | Fit now? |
|---|---|---|---|---|
| A. Detection + manual handling (current) | Detect a scanned PDF, stop, and ask for a text file or manual re-keying | No new PII processor; no OCR dependency; no false confidence; zero OCR cost; already tested | The school must re-key or obtain a text file; no in-app manual path today; recurring effort if scanned PDFs are common | **Yes — current decision** |
| B. Local OCR (e.g. Tesseract with Arabic trained data) | Run OCR on the application host; keep images/PII local | PII does not leave the host; predictable marginal cost; works offline | Arabic accuracy on tables, names, and digits is unproven; table structure is lost; language packs and image preprocessing add ops burden; review remains mandatory | Not now; candidate for a time-boxed spike |
| C. Cloud document OCR | Send page images to a commercial document-AI service | Often stronger Arabic/table extraction; less local compute; managed scaling | Guardian/student PII leaves the school's environment; DPA, data residency, retention/training terms, credentials, egress, and per-page cost; vendor lock-in; school approval required | Not now; likely blocked by privacy review until proven otherwise |
| D. Hybrid assisted OCR behind a flag | OCR produces candidate rows with page references; a human reviews every field before confirmation | Can reduce re-keying while keeping a human gate; supports a gradual rollout | Needs a side-by-side review UI, OCR provenance/confidence, a kill switch, and a measured accuracy baseline; still has B or C's privacy/cost profile | Only after evidence and school approval |

None of these options may auto-confirm a row. OCR output is untrusted input until a human verifies it.

## Risks

| Risk | Why it matters for FeeDesk | Mitigation if OCR is ever pursued |
|---|---|---|
| Arabic accuracy | Names, ligatures, diacritics, handwriting, stamps, low DPI, rotated pages, and Eastern Arabic digits can be misread; a wrong amount or phone is a financial/communication error | Measure field-level accuracy on real anonymized samples; require 100% human review of amounts and phones; preserve the source page image |
| Table structure | OCR text often loses columns and row boundaries; a plausible-looking row can pair the wrong guardian with the wrong balance | Use a table-aware engine or a human mapping step; never infer missing columns; reconcile totals |
| PII exposure | A cloud OCR call sends guardian/student names, phones, and balances to a third party; logs may retain page images or text | Prefer local processing; otherwise require an approved DPA, no training/retention, data-residency approval, encryption, and access logging |
| Cost | Per-page OCR fees plus engineering plus review time can exceed manual re-keying at low volume | Measure total cost per 100 pages, including review and operations, against the manual baseline |
| Review burden | OCR errors are plausible and easy to miss; reviewing every field can be slower than re-keying for small statements | Build a side-by-side image/row review UI; measure minutes per page and error-detection rate; pilot before rollout |
| False confidence | A clean-looking OCR row may be accepted without checking the image | Mark every OCR-derived row, show confidence/provenance, block confirmation until reviewed, and keep the source image |
| Operational complexity | Language packs, image preprocessing, CPU/memory limits, offline installs, and updates add failure modes | Pin the engine and language data; run offline by default; add resource limits and a kill switch |
| Legal / school policy | The school may not permit PII to leave its environment or may require a specific retention period | Make privacy approval a gate, not a post-launch fix; record the school's decision |

## Decision criteria for revisiting

A future OCR proposal must satisfy all of these. Proposed thresholds are for a time-boxed spike and must be confirmed with the school; they are not commitments.

| Criterion | Question / proposed threshold | Why it decides |
|---|---|---|
| Real demand | Do real anonymized samples show scanned PDFs are recurring, not a one-off? Is the measured share and pages/month material? | OCR is not worth its risk for a rare format |
| Accuracy | On a labelled Arabic sample, are amounts and phone digits at least 98% exact before human correction, names at least 90%, and row segmentation at least 95%? | Below this, review may be slower and less reliable than re-keying |
| Human review | Can every OCR-derived field be reviewed against the source image in a side-by-side UI? Is 100% review of amounts/phones enforced? | OCR must not become silent financial entry |
| Privacy | Is processing local, or is there an approved DPA with no training/retention, approved residency, encryption, and access logging? | Guardian/student PII is the main constraint |
| Cost | Is total cost per 100 pages (OCR + review + operations) below the measured manual baseline? | OCR must save effort, not add a parallel process |
| Safety | Can OCR rows be disabled by a kill switch, marked with provenance, and excluded from confirmation until reviewed? | A bad OCR release must not affect live fee data |
| Operations | Can the engine/language data be pinned, installed offline, resource-limited, and monitored? | The school host is a single server, not an ML platform |
| School approval | Has the school approved the privacy, cost, and review model in writing? | Technical feasibility alone is not consent |

## Evidence needed to revisit

- [ ] At least 3 real anonymized scanned PDFs (ideally 10+ pages), covering different layouts, image quality, stamps, and handwriting; synthetic fixtures are not sufficient.
- [ ] A ground-truth transcription produced by two people, with disagreements resolved and recorded.
- [ ] A measured manual baseline: minutes per page, error rate, and who does the re-keying today.
- [ ] A field-level accuracy report for each OCR option (amounts, phones, names, currency, row boundaries), including failure examples.
- [ ] A privacy review: local vs cloud, DPA, retention/training terms, residency, access logging, and incident path.
- [ ] A cost quote and an operations plan (engine, language data, image preprocessing, resource limits, update path).
- [ ] A UI/design for side-by-side review, OCR provenance, confidence, and a kill switch.
- [ ] A security review of the OCR path, including upload limits and prompt-injection-style risks if a cloud service is used.
- [ ] A pilot plan with the fake provider, no live SMS, and a rollback to detection-only.
- [ ] Written school approval and an updated decision record (ADR/`OD-08`).

## What would change the decision

- Real samples show scanned PDFs are a material share of imports and manual re-keying is a measured bottleneck.
- A local Arabic OCR option reaches the accuracy threshold without sending PII off-host.
- A cloud option clears the school's privacy review and its total cost is lower than manual handling.
- A review UI can make correction faster and safer than re-keying, with provenance and no auto-confirm.

## Current decision and next action

- **Implemented:** assisted local OCR (Tesseract `ara+eng`) now stages candidate rows for scanned PDFs; every row requires human review and OCR is never auto-confirmed.
- OCR can be disabled (`OCR_ENABLED=false`) and degrades safely to `SCANNED_PDF` if the engine or Arabic data is unavailable.
- Do not treat the synthetic scanned fixture as evidence of real-world Arabic OCR accuracy.
- Next action: collect real anonymized scanned samples, measure field-level accuracy, and obtain school approval for OCR processing and the mandatory review workflow before production use.
- Unresolved: the school's actual scanned share, acceptable processing location, review workload, and whether OCR should remain enabled for production imports.
- M2 formal acceptance remains blocked on real school samples and G0/G1; this memo does not change either gate.
