# ADR 004 — Import parsing and provenance

**Status:** Accepted  
**Date:** 3 November 2026

## Context

Statements arrive as XLSX and PDF with inconsistent layouts. Financial values must be reviewable and traceable to the source.

## Decision

- Every upload creates an import batch.
- XLSX parsing uses openpyxl in read-only mode with cached formula values.
- PDF parsing uses pdfplumber for text and table extraction.
- Scanned PDFs are detected; OCR is an assisted fallback and every OCR-derived value requires human verification.
- Extracted rows are stored in staging with raw and normalized JSON plus source row/page references.
- Column mapping is auto-suggested and manually correctable.
- Confirmation is transactional; a failed confirmation leaves no partial fee records.
- Duplicate file hashes require an explicit override with a reason and audit event.

## Consequences

- Source documents must be stored privately and retained only as long as policy allows.
- The parser must fail visibly rather than invent values.
- Real samples are required before the supported-format boundary is final.
