# Synthetic Statement Fixtures

**Location:** `F:\FeeDesk\.local\samples\` (gitignored)  
**Purpose:** Unblock parser and validation development while real school samples are pending.  
**Important:** These are synthetic fixtures. They do not satisfy the G0 requirement for real anonymized school statements.

## XLSX

| File | What it exercises |
|---|---|
| `xlsx/sample-01-multi-sheet.xlsx` | Two sheets, Arabic headers, SYP/USD, zero balance, missing phone, negative balance, sibling rows sharing a guardian/phone |
| `xlsx/sample-02-arabic-digits.xlsx` | Arabic-Indic digits, `ل.س` suffixes, currency column, zero balance |
| `xlsx/sample-03-messy-headers.xlsx` | Blank rows before the header, merged title rows, header variants, comma/dot ambiguity, an empty sheet, a notes-only sheet |

## PDF

| File | What it exercises |
|---|---|
| `pdf/sample-01-text-table.pdf` | Text layer plus a table; extractable with pdfplumber |
| `pdf/sample-02-scanned-image.pdf` | Image-only page; zero extractable text; must be detected as scanned |

## Parser notes discovered while creating the fixtures

- The Chromium-generated Arabic PDF exposes a text layer, but pdfplumber returns Arabic in presentation forms (`\ufeXX` codepoints). The PDF parser must normalize Arabic presentation forms before comparison.
- The scanned PDF has `0` extractable characters and `0` tables. It must be flagged for OCR/manual handling, never silently interpreted.
- The text PDF yielded one table object and 739 extracted characters.
- XLSX dates and currency values are stored as numbers/strings; the parser must preserve the raw value and apply decimal parsing separately.

## Regeneration

The XLSX fixtures were generated with openpyxl. The PDFs were rendered from a local HTML table with Chromium/Playwright. Generation scripts are intentionally not committed because the fixtures are local test assets; create new fixtures from real anonymized samples when they arrive.
