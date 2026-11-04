# Statement Taxonomy and Field Dictionary

**Status:** Draft based on PRD v1.0; must be validated against real anonymized samples.

## Required fields for a sendable fee record

| Field | Required | Source example | Normalization | Notes |
|---|---|---|---|---|
| Guardian name | Yes | `اسم ولي الأمر` | Trim, collapse whitespace, preserve Arabic | Never invent |
| Guardian phone | Yes | `رقم الهاتف` / `الموبايل` | E.164 (`+9639...`) with original retained | Invalid/shared numbers block sending |
| Remaining balance | Yes | `المتبقي` / `الرصيد` | Decimal, explicit currency | Source value preserved |
| Currency | Yes | `العملة` / `د.س` / `SYP` | ISO code; symbol is display-only | Never combine currencies |
| Amount paid | Expected | `المدفوع` | Decimal | Optional if statement lacks it |
| Total fee | Optional | `إجمالي القسط` | Decimal | Never invent |
| Student name/reference | Optional | `اسم الطالب` | Preserve | Absence must not block import |
| Fee period | Optional | `الفصل` / `الشهر` | Preserve text | Used in message if available |
| Source filename | Yes | Upload metadata | Store path-safe key | Provenance |
| Source row/page | Yes where available | Sheet/row or PDF page | Integer | Provenance |

## Likely source column variants

| Canonical field | Possible headers |
|---|---|
| Guardian name | `ولي الأمر`, `اسم ولي الأمر`, `الأب`, `الأم`, `Guardian` |
| Phone | `الهاتف`, `رقم الهاتف`, `الموبايل`, `الجوال`, `Phone` |
| Student | `الطالب`, `اسم الطالب`, `الطالبة`, `Student` |
| Amount paid | `المدفوع`, `الواصل`, `المسدد`, `Paid` |
| Remaining | `المتبقي`, `الرصيد`, `المستحق`, `الباقي`, `Remaining` |
| Total fee | `الإجمالي`, `قيمة القسط`, `Total` |
| Currency | `العملة`, `Currency` |
| Period | `الفصل`, `الشهر`, `الفترة`, `Period` |

## Validation rules

1. Money is parsed into `Decimal`, never binary float.
2. Arabic-Indic digits are accepted and converted.
3. Ambiguous decimal separators are flagged, not guessed.
4. Negative balances are flagged and blocked from campaigns.
5. Zero balances are retained and excluded from campaigns.
6. If total fee and paid amount exist, a comparison balance is calculated for validation only; the source balance is never overwritten.
7. A missing phone keeps the financial record but blocks the contact from messaging.
8. A shared phone is a duplicate/ambiguity flag, never an automatic guardian merge.
9. Source row/page references are preserved for every staged row.
10. Duplicate file hashes require an explicit override with a reason and audit event.

## Open questions for the school

- What is the official currency symbol, and is more than one currency used?
- How are fee periods named (month, semester, academic year)?
- Are guardian and student names in separate columns or combined?
- Do statements include siblings under one guardian?
- Are there credit balances or prepayments represented as negative values?
- Which rows are considered "paid" versus "partially paid"?
