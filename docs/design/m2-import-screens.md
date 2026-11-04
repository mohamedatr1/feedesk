# M2 — Import Screens Design Spec

**Scope:** `/statements`, `/statements/upload`, `/statements/[id]/review`, `/statements/[id]`.
**Status:** Spec for the M2 frontend import lane. No application code in this lane.
**Date:** 3 November 2026
**Sources of truth:** `docs/m2/api-contract.md` (binding), `docs/m2/subagent-brief.md`, `docs/design/design-review.md`, `docs/design/tokens.css`, `PRD.md` §7.1, §7.2, §8.3, §13.3, `docs/m0/statement-taxonomy.md`.

**Design language:** unchanged from the approved M1 dashboard — cream `--fd-bg`, olive `--fd-brand`, one card radius (16px), one control radius (10px), IBM Plex Sans Arabic, 13px tables, tinted sticky headers, dot + label pills, calm empty states. **The shell is not redesigned.** `AppShell`, `PageHeader`, `Protected`, `Dialog`, `ConfirmDialog`, `StatusPill`, `EmptyState`, `StatCard` are reused as-is.

This document specifies what is new: the import surfaces, the states they must cover, the Arabic copy, and the rules that keep money, provenance, and RTL honest.

---

## 0. Principles for this screen set (derived, not invented)

1. **Uploading never creates money.** Every path ends at a review screen with an explicit confirmation. No screen may imply that a file is "imported" before `status: confirmed`.
2. **The file is evidence.** Source filename, sheet, row/page number, original values, and corrections are visible, not hidden in a details drawer the user must guess to open.
3. **Errors live next to the record.** PRD §13.3.C. No error tooltips, no "see summary above", no toast-only validation.
4. **Nothing is guessed.** No combined-currency totals, no `Number()` on money strings, no fabricated progress percentages, no auto-redirect, no silent corrections.
5. **Counts and money are unknown until known.** While loading, render `—`, never `0` and never a currency symbol.

### 0.1 PRD coverage

| Requirement | Where this spec answers it |
|---|---|
| FR-IMP-01 upload Excel/PDF | §4.2 |
| FR-IMP-02 reject unsupported formats | §4.2 client check, §9.3 copy |
| FR-IMP-03 configurable size/processing limits | §4.2 (server-side, no invented limit), §11 G4 |
| FR-IMP-04 validate before processing | §4.2 pre-checks, §4.3 in-flight |
| FR-IMP-05 one batch per upload | §1 flow, §3 list rows |
| FR-IMP-06 sheet inspection/selection | §4.5 |
| FR-IMP-07 header detection + suggested mapping | §4.6 (`مطابقة تلقائية`) |
| FR-IMP-08 manual mapping | §4.6 (`عمود غير مدرج…`) |
| FR-IMP-09 PDF text/table extraction | §4.7, §4.8 |
| FR-IMP-10 scanned PDF detection | §4.8 |
| FR-IMP-11 OCR values require human verification | Out of scope (no OCR in M2); §4.8 refuses to invent rows |
| FR-IMP-12 source row/page per record | §5.5 `المصدر`, §5.8, §6.6 |
| FR-IMP-13 review before confirmation | §5 (whole screen), §5.11 |
| FR-IMP-14 correct extracted values | §5.6 |
| FR-IMP-15 duplicate file handling | §4.4 |
| FR-IMP-16 import history | §3 |
| FR-IMP-17 saved mapping profiles (P1) | Not designed; mapping is per-batch in M2 |
| PRD 7.1 (upload never creates sendable records) | §5.11, §5.12, §14 |
| PRD 7.2 (review fields and distinctions) | §5.5, §5.8 |
| PRD 8.3 import states with human-readable explanation | §3.6, §5.13, §6.4 |
| PRD 13.3.B list components | §3.5 |
| PRD 13.3.C errors next to the record | §5.8 |
| PRD 8.4 provenance / no recalculation of balances | §5.7, §5.10 totals, §7.3 |

---

## 1. Screen map and entry points

```
/statements
   ├─ رفع كشف جديد ─────────────► /statements/upload
   │                                  ├─ ملف → ورقة → أعمدة → استخراج
   │                                  └─ نجاح ──────────────► /statements/[id]/review
   ├─ مراجعة (status=review_required) ─────────────────────► /statements/[id]/review
   ├─ متابعة (status=uploaded) ───────► /statements/upload (batch resumed at "الورقة")
   └─ عرض (confirmed / failed / cancelled) ────────────────► /statements/[id]

/statements/[id]
   ├─ مراجعة الأسطر ───────────────────────────────────────► /statements/[id]/review
   ├─ عرض الملف الأصلي ────────────────────────────────────► GET /files/{source_file_id}
   └─ إلغاء الاستيراد ─────────────────────────────────────► dialog → same page

/statements/[id]/review
   └─ تأكيد الاستيراد ─────────────────────────────────────► dialog → /statements/[id]?confirmed=1
```

**Route titles** (build on the M1 per-route `metadata` pattern):

| Route | `<title>` |
|---|---|
| `/statements` | كشوف الأقساط — FeeDesk |
| `/statements/upload` | رفع كشف — FeeDesk |
| `/statements/[id]/review` | مراجعة الاستيراد — FeeDesk |
| `/statements/[id]` | تفاصيل الكشف — FeeDesk |

**Permission gating** (from `/auth/me.permissions`):

| Permission | Controls |
|---|---|
| `imports.view` | `/statements`, `/statements/[id]` |
| `imports.upload` | "رفع كشف جديد", the upload route |
| `imports.review` | inline editing, exclusion, row actions |
| `imports.confirm` | the confirmation panel and confirm dialog |

When a permission is missing, the control is **absent**, not disabled, except the confirmation panel, which becomes a static explanation: "لديك صلاحية المراجعة فقط. التأكيد متاح لمن يملك صلاحية تأكيد الاستيراد."

---

## 2. Shared foundations

### 2.1 Layout rhythm

| Token | Value | Use here |
|---|---|---|
| Page header | `PageHeader` as-is (30px/700 H1, 14px subtitle) | All four screens |
| Card | `.fd-card` + `.fd-card-pad` (20px) | Panels, summary strips |
| Card header strip | `px-5 py-4`, bottom border, 4px×16px brand bar + h2 14px/600 | Table cards, warning lists |
| Vertical rhythm | 20px between cards (`mt-5`), 16px inside grids (`gap-4`) | All screens |
| Max width | `.fd-content` (1440) unchanged | All screens |
| Control radius | 10px | Buttons, inputs, dropzone inner elements |
| Card radius | 16px | Cards, dialogs, dropzone |

The P2 type-scale polish from `design-review.md` (H1 32–34, section 16–17, 24px card padding) is **not** applied here unilaterally; import screens follow the shipped M1 scale so the product does not look like two products. If the P2 sweep lands, it lands everywhere at once.

### 2.2 New primitives (build, don't restyle)

| Primitive | Where | Notes |
|---|---|---|
| `CountStrip` | review, detail | Up to five label/value cells with logical `border-s` dividers |
| `FileDropzone` | upload step 1 | Dashed `--fd-line-input`, 44px+ targets, real file input |
| `StepIndicator` | upload wizard | 4 steps, `aria-current="step"`, no colour-only completion |
| `FilterChips` | list, review | `role="group"` with a group label; `aria-pressed` per chip |
| `UploadProgress` | upload step 1, in-flight | Determinate only if a real byte count exists |
| `EditableCell` | review table | View → edit in place, Enter/Esc, one row editing at a time |
| `RowIssues` | review table | Always-visible message list under the row, expanded on demand |
| `CurrencyTotals` | review confirm bar, detail | One line per currency, never a grand total |
| `StickyActionBar` | review | Summary + primary/secondary; sticky to viewport bottom |
| `ImportStatusPill` | everywhere | Wraps `StatusPill`, adds a spinner for `processing` |

### 2.3 Tokens

No new colour tokens. Row tints are derived from existing tokens so the palette stays closed:

```css
/* invalid row */
background: color-mix(in srgb, var(--fd-red-soft) 55%, var(--fd-surface));
/* excluded row */
background: var(--fd-surface-alt);
/* warning row: no fill, only a 3px inline-start marker */
border-inline-start: 3px solid var(--fd-amber);
```

Hex values are never used directly in import components.

### 2.4 Motion

Restrained, matching the calm dashboard.

- Dropzone drag-over: 120ms background/border transition.
- Sticky bar entrance: 160ms fade + 8px rise, once.
- Row saved: 600ms `--fd-green-soft` flash that settles to transparent.
- Excluded row: 120ms background change; no collapse, no reflow jump.
- Skeletons: existing `.fd-skeleton` (already reduced-motion aware).
- No stepper confetti, no progress shimmer loops beyond the skeleton, no auto-scroll animations (`scrollIntoView` uses `behavior: "auto"`).

---

## 3. Screen 1 — Statements list (`/statements`)

### 3.1 Structure

```
┌──────────────────────────────────────────────────────────────────────┐
│  كشوف الأقساط                                       [رفع كشف جديد]   │  PageHeader
│  رفع كشوف Excel وPDF، مراجعتها، ثم تأكيدها.                           │
│                                                                      │
│  3 كشوف · 1 بانتظار المراجعة · آخر رفع 2026-11-03 20:26   ← summary   │  one line, 12px
├──────────────────────────────────────────────────────────────────────┤
│  [الكل 3] [بانتظار المراجعة 1] [مؤكد 1] [ملغى 1]                    │  filter row
├──────────────────────────────────────────────────────────────────────┤
│  الملف                 الحالة        الأسطر   تاريخ الرفع   رافع  إجراء│  table
│  sample-01.xlsx  ▸     بانتظار المراجعة  7   2026-11-03…   أ. خالد  [مراجعة]│
│  └ 5 صالحة · 1 خطأ · 1 مكرر                                           │
└──────────────────────────────────────────────────────────────────────┘
```

The list **leads with the queue**, not with metrics. No KPI cards on this screen: the dashboard already owns the numbers, and four more cards would push the only actionable table below the fold at 1024.

### 3.2 Header

- H1: `كشوف الأقساط`
- Subtitle: `رفع كشوف Excel وPDF، مراجعتها، ثم تأكيدها.`
- Primary action: `رفع كشف جديد` with `Upload` icon, `h-11`, brand fill.
  - Hidden without `imports.upload`.
  - Never disabled-with-no-reason; if the user lacks the permission the button is absent.

### 3.3 Summary line (single row, no card)

Format: `{count} كشوف · {n} بانتظار المراجعة · آخر رفع {date}`.

- 12px `--fd-ink-muted`, dots as `·` separators, `aria-live="polite"` not needed (it is not a status message, it is page content; it re-renders with the list).
- Segments that are zero are omitted (no `بانتظار المراجعة` segment when the count is 0); the total is always present. When the list is empty, the line is not rendered at all — the empty state carries the message.
- While loading: `— · — · —` placeholders plus a skeleton for the line.
- Dates use the M1 table format `YYYY-MM-DD HH:mm`.
- No currency here.

### 3.4 Filter row

| Control | Detail |
|---|---|
| Chips | `الكل`, `بانتظار المراجعة`, `جاهز للتأكيد`, `مؤكد`, `ملغى`, `فشل` — only statuses that exist in the current result set get a chip, plus `الكل` |
| Chip label | Arabic status + count in `tabular-nums`, e.g. `بانتظار المراجعة 1` |
| Semantics | `role="group" aria-label="تصفية حسب الحالة"`, each chip a `<button aria-pressed>` |
| Search | Optional in M2 (the list endpoint has no `q`). **Do not render a search box that cannot work.** |
| Size | Chip visual height 36px on desktop, 44px at `≤767px`; hit area never below 44×44 |

Filtering is server-side via `?status=`. The chip row is not a link farm: state lives in the URL so back/forward and refresh are honest.

### 3.5 Table

Columns in RTL reading order (first column at the right):

| # | Column | Content | Width @1440 | Alignment |
|---|---|---|---|---|
| 1 | الملف | `FileSpreadsheet` / `FileText` icon (aria-hidden), filename in `<bdi>`, muted second line `xlsx` / `PDF` | 260 | start |
| 2 | الحالة | `ImportStatusPill` + (if errors) a red second line `2 أخطاء · 1 تحذير` | 180 | start |
| 3 | الأسطر | `total_rows` with a muted breakdown `5 صالحة · 1 خطأ · 1 مكرر` | 170 | start |
| 4 | تاريخ الرفع | `2026-11-03 20:26`, `whitespace-nowrap`, tabular | 150 | start |
| 5 | رافع الملف | Name if available, otherwise short ID in `<bdi>` muted (see §11 gap G3) | 140 | start |
| 6 | إجراء | Text button (44px) | 120 | start |

Rules:

- Row height ≥ 60px because column 1 and 2 carry two lines.
- Hover: `background: var(--fd-surface-alt)` on the whole row.
- The filename cell is a `<th scope="row">` so screen readers can navigate rows by file.
- Table has `<caption class="sr-only">قائمة كشوف الأقساط</caption>` and `scope="col"` on every header.
- Long filenames: one line, `truncate`, full name available via the details page (never a `title` tooltip only). `dir="auto"` on the filename plus `<bdi>` so mixed Arabic/Latin names do not reorder.

### 3.6 Status vocabulary and tones

| `status` | Label | Tone | Extra |
|---|---|---|---|
| `uploaded` | تم الرفع | neutral | Action: `متابعة` → upload wizard at "الورقة" |
| `processing` | قيد المعالجة | amber | 12px spinner before the dot; action disabled |
| `review_required` | بانتظار المراجعة | amber | Action: `مراجعة` (primary-weight text button) |
| `ready_to_confirm` | جاهز للتأكيد | green | Action: `مراجعة` |
| `confirmed` | مؤكد | green | Action: `عرض` |
| `failed` | فشل الاستيراد | red | Action: `عرض`; the row shows the reason in the status cell's second line, truncated to 1 line |
| `cancelled` | ملغى | neutral | Action: `عرض` |

`failed` rows are **not** hidden by default and **not** styled as disabled; the reason is the most useful content on the row.

### 3.7 Row action rules

| State | Label | Target |
|---|---|---|
| `review_required`, `ready_to_confirm` | `مراجعة` | `/statements/{id}/review` |
| `uploaded` | `متابعة` | `/statements/upload?import={id}` (resume at step 2) |
| `confirmed`, `cancelled`, `failed` | `عرض` | `/statements/{id}` |
| `processing` | (no action) | Show `جارٍ المعالجة…` as muted text instead of a button |

Each action gets an accessible name that includes the file: `aria-label="مراجعة كشف sample-01.xlsx"`.

### 3.8 States

| State | Treatment |
|---|---|
| **Loading** | 6 skeleton rows at 60px, skeleton in the summary line, filter chips static (`الكل` only, count `—`), CTA visible and usable. Never an empty state while loading. |
| **Empty (no imports)** | `EmptyState` inside the card, `FileText` icon, title `لا توجد كشوف بعد`, description `ارفع كشف Excel أو PDF لاستخراج السجلات المالية ومراجعتها قبل التأكيد.`, action `رفع كشف جديد` (secondary button style — the header already has the primary). Format hint below the action: `Excel (.xlsx) أو PDF`. |
| **Empty (filtered)** | Title `لا توجد كشوف بهذه الحالة`, description `جرّب حالة أخرى.`, action `عرض كل الكشوف`. |
| **Error** | Inline banner above the table, `role="alert"`, `--fd-red-soft`/`--fd-red-text`, text `تعذر تحميل الكشوف.` + the API `message_ar` on a second line, action `إعادة المحاولة` (44px). The table header stays visible; rows show a single full-width error row. No toast. |
| **Partial failure** | If counts load but a row detail fails, the list still renders; no page-level error. |

Pagination: `page_size=20`, footer line `عرض 20 من 47 كشفًا` + previous/next 44px buttons, hidden when `total ≤ page_size`. Pluralisation per §9.4.

---

## 4. Screen 2 — Upload wizard (`/statements/upload`)

### 4.1 Shape

Single column, `max-w-[880px]`, centred in `.fd-content`. The mapping table may exceed this at 1440 but never creates page-level horizontal scroll.

Steps:

| # | Step | When it appears |
|---|---|---|
| 1 | الملف | Always |
| 2 | الورقة | Only when the workbook has more than one sheet |
| 3 | الأعمدة | When the batch needs a mapping decision (multi-sheet, or the user chose `تغيير مطابقة الأعمدة`) |
| 4 | الاستخراج | After `POST /imports/{id}/process` |

Stepper rules:

- `StepIndicator` is an ordered list, not a progress bar: `<ol>` with `aria-label="خطوات رفع الكشف"`, current step `aria-current="step"`.
- Completed steps show a check **and** the step name; do not rely on the check alone.
- Steps that do not apply are not rendered (a 2-sheet workbook shows 4 steps; a single-sheet file jumps from 1 to 4 with the stepper updating to 2 visible steps).
- No step auto-advances without a user action.
- Back navigation is always available except while a request is in flight (`رجوع` disabled, not hidden).

### 4.2 Step 1 — File

```
┌──────────────────────────────────────────────────┐
│  ┌────────────────────────────────────────────┐  │
│  │              ⬆  (24px, brand)              │  │
│  │        اسحب ملف الكشف إلى هنا               │  │
│  │        أو                                   │  │
│  │        [ اختيار ملف ]                       │  │
│  │        Excel (.xlsx) أو PDF                 │  │
│  └────────────────────────────────────────────┘  │
│  3 ميغابايت كحد أقصى حسب إعدادات المدرسة ← omit  │
│  until the API exposes the limit (see §11 G4)    │
└──────────────────────────────────────────────────┘
```

- Dropzone: `border-[1.5px] border-dashed border-[var(--fd-line-input)]`, radius 16, min-height 220px (180 at 768), background `--fd-surface`, centred content.
- Dragover: border `--fd-brand` solid, background `color-mix(in srgb, var(--fd-brand-soft) 55%, var(--fd-surface))`, 120ms.
- **The dropzone is not the only affordance.** A real `<input type="file" accept=".xlsx,.pdf" class="sr-only" id="...">` paired with a visible `<label>` styled as a secondary button, plus a visible `اختيار ملف` button for browsers where label-as-button is awkward. Keyboard: Tab reaches the input, Space/Enter opens the picker.
- Icon: `UploadCloud` 24px, `--fd-ink-subtle`, aria-hidden.
- Helper line: `Excel (.xlsx) أو PDF` — no invented size limit. If the backend returns `max_upload_mb` later, append `· حتى {n} ميغابايت`.

**Client-side pre-checks** (immediate, before the request):

| Check | Copy |
|---|---|
| Extension not `.xlsx`/`.pdf` | `هذا النوع غير مدعوم. المسموح: Excel (.xlsx) أو PDF.` |
| `file.size === 0` | `الملف فارغ. اختر ملفًا يحتوي على بيانات.` |
| Drag with >1 file | `ارفع ملفًا واحدًا في كل مرة.` (the first file is kept, not silently dropped) |

Errors appear in a `role="alert"` block directly under the dropzone, 12px, `--fd-red-text`, with the dropzone border switching to `--fd-red`. The file is not accepted into the dropzone state until the check passes.

**Selected file state** — replaces the dropzone content:

```
┌────────────────────────────────────────────────┐
│ [xlsx]  sample-01-multi-sheet.xlsx       [×]   │
│         1.4 ميغابايت · Excel                   │
└────────────────────────────────────────────────┘
```

- Filename with `<bdi>`; remove button 44×44, `aria-label="إزالة الملف"`.
- Primary action below: `رفع الملف` `h-11`, full width at ≤767, right-aligned at 1440.

### 4.3 Upload in flight

- Step 1 collapses to the file card (not the dropzone); the card shows a status line and a progress bar.
- **Progress honesty:** `fetch` cannot report upload bytes. Either (a) use `XMLHttpRequest` and show a determinate bar from `upload.onprogress`, or (b) keep `fetch` and show an **indeterminate** bar with stage copy `جارٍ رفع الملف…` → `جارٍ تحليل الملف…`.
  - Determinate: `role="progressbar" aria-valuemin=0 aria-valuemax=100 aria-valuenow={n}` + text `تم رفع 62%`.
  - Indeterminate: `role="progressbar"` with no `aria-valuenow`, text `جارٍ تحليل الملف…`.
  - **Never** animate a fake percentage, and never both stage copy and a stuck 90%.
- Bar: 6px height, radius full, track `--fd-surface-alt`, fill `--fd-brand`, 160ms width transition.
- `إلغاء` is hidden while the request is in flight (the browser cannot abort a committed upload safely); it appears again on error.
- No modal during upload. The page stays interactive enough to read the stage text.

### 4.4 Duplicate file (409 `DUPLICATE_FILE`)

Opens a `Dialog` (not `window.confirm`), title `هذا الملف مرفوع مسبقًا`.

Body:

> الملف `{filename}` رُفع بتاريخ `{date}` باسم `{uploader}`.
> [عرض الاستيراد السابق] ← secondary link to `/statements/{existing_import_id}`

Override block (separated by a top border):

- Checkbox `رفع نسخة أخرى من الملف` (this is the `force_duplicate` control; the block is hidden until checked).
- Textarea, required: label `سبب رفع الملف مرة أخرى`, hint `سيُسجَّل السبب في سجل العمليات.`, placeholder `مثال: تصحيح ملف رُفع بالخطأ.`
- Inline error when empty on submit: `اذكر سبب رفع الملف مرة أخرى.`
- Dialog actions: `إلغاء` (autofocus, secondary) and `رفع النسخة` (`fd-btn-primary`, disabled while busy, label becomes `جارٍ الرفع…`).

Semantics follow the existing `Dialog` + `data-autofocus` pattern. Do not use the red `ConfirmDialog` — a duplicate override is an auditable exception, not a destructive action.

### 4.5 Step 2 — Sheet selection (multi-sheet only)

```
┌────────────────────────────────────────────────┐
│  اختر الورقة التي تحتوي على جدول الأقساط        │
│  يحتوي الملف على 2 ورقات.                      │
│  ┌──────────────────────┐ ┌──────────────────┐ │
│  │ ( ) الفصل الأول      │ │ ( ) الفصل الثاني │ │
│  └──────────────────────┘ └──────────────────┘ │
│                          [رجوع] [التالي]        │
└────────────────────────────────────────────────┘
```

- Radio cards: real `<input type="radio" name="worksheet">` visually restyled with `<label>`; the entire card is the hit area, min-height 64px.
- Selected state: `--fd-brand` border 2px, `--fd-brand-soft` background, brand check icon **and** `aria-checked` — never colour alone.
- Sheet name in `<bdi>` because Arabic sheet names can contain Latin digits.
- Row counts are **not** shown: the contract exposes `available_sheets: string[]` only. Do not invent counts (see §11 G5).
- Helper when a sheet looks empty (after process, not here): handled at step 4.
- Validation: `التالي` disabled until a sheet is chosen, with the reason stated: `اختر ورقة للمتابعة.`
- `رجوع` returns to step 1 with the file still selected.

### 4.6 Step 3 — Column mapping

Mapping is the trust contract of the whole import. It gets a full-width table and an explicit required/optional distinction.

```
مطابقة الأعمدة
اختر العمود المقابل لكل حقل. الحقول المعلّمة بـ * مطلوبة.

┌──────────────────────────────────────────────────────────────────┐
│ الحقل              مطلوب   عمود الملف              معاينة        │
│ اسم ولي الأمر      *      [اسم ولي الأمر  ▾]       ولي أمر 001   │
│ رقم الهاتف         †      [رقم الهاتف     ▾]       +963900000001 │
│ المتبقي            *      [المتبقي        ▾]       600000.00     │
│ العملة             *      [العملة         ▾]       SYP           │
│ إجمالي القسط       —      [الإجمالي       ▾]       1000000.00    │
│ المدفوع            —      [المدفوع        ▾]       400000.00     │
│ اسم الطالب         —      [لا شيء         ▾]       —             │
│ الفصل الدراسي      —      [لا شيء         ▾]       —             │
└──────────────────────────────────────────────────────────────────┘
```

Field rules:

| Canonical | Label | Requirement marker | Gate |
|---|---|---|---|
| `guardian_name` | اسم ولي الأمر | `*` مطلوب | blocks `استخراج السجلات` |
| `remaining_balance` | المتبقي | `*` مطلوب | blocks |
| `currency` | العملة | `*` مطلوب | blocks |
| `guardian_phone` | رقم الهاتف | `†` مطلوب لرسائل التذكير | does **not** block; helper line explains |
| `total_fee` | إجمالي القسط | `—` اختياري | — |
| `amount_paid` | المدفوع | `—` اختياري | — |
| `student_name` | اسم الطالب | `—` اختياري | — |
| `fee_period` | الفصل الدراسي | `—` اختياري | — |

- `†` is rendered as an amber dot plus the word `للتذكير`, not as an asterisk; the summary line under the table reads: `بدون رقم هاتف يبقى السجل المالي، لكنه لا يصلح لرسائل التذكير.`
- Source column control: native `<select class="fd-input h-11">` styled with the existing input tokens. Options: `لا شيء`, then every detected source header, then `عمود غير مدرج…` (manual entry).
- **Manual mapping** (PRD FR-IMP-08): choosing `عمود غير مدرج…` reveals a text input `اسم العمود في الملف` with hint `انسخ عنوان العمود كما يظهر في الملف.` The value is sent as the source header string.
- One source column may not be used twice. Choosing a used column shows an inline error on the row: `هذا العمود مستخدم بالفعل في «{field}».` and blocks processing until resolved.
- Suggested mappings carry a muted inline tag `مطابقة تلقائية` so the user knows what the system guessed (never a confidence percentage — the contract has none).
- Each row is `<th scope="row">`; each select is labelled by that header through `aria-labelledby`, not a placeholder.
- The `معاينة` column is shown **only when rows are already staged** for this batch (the single-sheet re-mapping case), using the first row's `raw_data` values. Before the first extraction there are no values to preview, so the column is omitted — never invent a sample (§11 G11).

Gate copy on `استخراج السجلات`:

- Disabled with visible reason (not a tooltip): `اختر عمودًا لكل من: المتبقي، العملة.` — the list is generated live.
- Enabled state: primary `استخراج السجلات`, `h-11`.
- Busy: `جارٍ استخراج السجلات…`, disabled, `aria-busy="true"` on the table card.
- Re-processing warning, shown when the batch already has staged rows: amber inline note `إعادة الاستخراج تستبدل الأسطر الحالية. التعديلات اليدوية على الأسطر الحالية ستُفقد.` with the confirm inside the button label `إعادة الاستخراج` (not a dialog; the note is adjacent and the action is reversible by re-upload).

### 4.7 Step 4 — Extraction result

No auto-redirect. A completed panel is a predictable landing point for keyboard and screen-reader users.

```
┌──────────────────────────────────────────────────┐
│ ✓  تم استخراج الأسطر                              │
│    7 أسطر: 5 صالحة · 1 بها تحذير · 1 بها خطأ      │
│    الورقة: الفصل الأول                            │
│    [فتح المراجعة]  [تعديل مطابقة الأعمدة]         │
└──────────────────────────────────────────────────┘
```

- Success icon `CheckCircle2` + `role="status"`.
- Counts reuse `CountStrip` data, not a new format.
- If zero rows: this is **not** success. See the scanned/empty state.
- If some rows are invalid, the panel is still "extracted" (neutral success), and the primary action is `فتح المراجعة` with the error count visible: `سجل واحد به خطأ يحتاج تصحيحًا أو استثناءً.` Do not call it a failure.

### 4.8 Scanned PDF and empty extraction

| Cause | Panel |
|---|---|
| `SCANNED_PDF` warning, 0 rows | Amber panel, `ScanLine` icon, title `الملف يبدو ممسوحًا ضوئيًا`, body `لم نتمكن من قراءة نص من هذا الملف. تحتاج الكشوف الممسوحة إلى ملف نصي أو إلى إدخال يدوي.` Actions: `رفع ملف آخر` (primary), `إلغاء الاستيراد` (secondary, opens the cancel dialog). No OCR promise, no "قريبًا" wording. |
| Empty sheet / no rows after parse | `لم نستخرج أي سطر من هذه الورقة`, body `الورقة لا تحتوي على بيانات أو أن الجدول غير واضح.` Actions: `اختيار ورقة أخرى` (if the workbook has several), `رفع ملف آخر`, `إلغاء الاستيراد`. |
| No header detected | `لم نجد صف عناوين واضحًا في هذه الورقة.` body `تأكد أن الجدول يحتوي على صف عناوين، أو جرّب ورقة أخرى.` Action: `اختيار ورقة أخرى`. Do **not** offer manual header-row selection in M2 (not in the contract). |
| Parse failure (`failed`) | Red panel, title `تعذر تحليل الملف`, body = API `error_summary`/`message_ar` verbatim, plus `لم تُنشأ أي سجلات مالية.` Actions: `رفع ملف آخر`, `إلغاء الاستيراد`. |

### 4.9 Leaving the wizard

Once a batch exists (201), the user is not trapped:

- `إلغاء الرفع` (text button, `--fd-ink-muted`) in the wizard header, present from step 2 onward.
- If rows are staged, it opens the cancel dialog (§9.2 copy). If the batch is still `uploaded` with no rows, it calls cancel directly and returns to `/statements` with `role="status"` `تم إلغاء الرفع.`
- Browser back does not silently orphan a batch; the list shows it honestly as `تم الرفع` or `بانتظار المراجعة`.

---

## 5. Screen 3 — Import review (`/statements/[id]/review`)

This is the most important screen in M2. It must read as a **ledger under examination**, not a spreadsheet.

### 5.1 Structure

```
┌───────────────────────────────────────────────────────────────────────┐
│ كشوف الأقساط / sample-01.xlsx / مراجعة            ← breadcrumb (nav)  │
│ مراجعة الاستيراد                                    [تغيير المطابقة]   │  H1 30px
│ sample-01-multi-sheet.xlsx · الفصل الأول · 7 أسطر                     │  14px muted
│ رُفع 2026-11-03 20:26 بواسطة أ. خالد                                   │  12px subtle
├───────────────────────────────────────────────────────────────────────┤
│  الأسطر 7 │ صالحة 5 │ بها تحذيرات 1 │ بها أخطاء 1 │ مستثناة 0         │  CountStrip
├───────────────────────────────────────────────────────────────────────┤
│ [الكل 7] [صالحة 5] [تحذيرات 1] [أخطاء 1] [مستثناة 0]   [بحث ...]      │  filters
├───────────────────────────────────────────────────────────────────────┤
│  ولي الأمر   الهاتف   الطالب   المتبقي  المدفوع  العملة  الحالة  المصدر  إجراء│
│  … rows …                                                             │
├───────────────────────────────────────────────────────────────────────┤
│ [تأكيد الاستيراد]  …summary…  ← sticky action bar                     │
└───────────────────────────────────────────────────────────────────────┘
```

The H1 names the **task** (`مراجعة الاستيراد`) and the filename is the first line of context. This keeps `PageHeader` and the 30px scale identical to the rest of the product; a 30px filename would be the only oversized data element in the application. The detail page is the inverse — there the filename *is* the object and becomes the H1.

### 5.2 Header

| Element | Content |
|---|---|
| Breadcrumb | `<nav aria-label="مسار التصفح">` → `كشوف الأقساط` / filename (link to detail) / `مراجعة` (`aria-current="page"`) |
| H1 | `مراجعة الاستيراد` |
| Context line | `<bdi>{filename}</bdi>` · worksheet chip · `{total_rows} أسطر` — 14px, `--fd-ink-muted` |
| Meta line | `رُفع {created_at}` · `بواسطة {uploader}` — 12px, `--fd-ink-subtle` |
| Secondary action | `تغيير مطابقة الأعمدة` → upload wizard step 3 for this batch (guarded by the re-process warning) |

The worksheet name is a real chip (`--fd-surface-alt`, 12px) so the user can confirm which sheet is under review. When the file is a PDF, use `ملف PDF` and omit the sheet.

### 5.3 CountStrip

Five cells: `الأسطر`, `صالحة`, `بها تحذيرات`, `بها أخطاء`, `مستثناة`.

- Cells: 12px muted label, 24px/700 tabular value, separated by logical `border-s`.
- Values take status colour **only when non-zero**: errors red, warnings amber. Zero stays `--fd-ink`.
- Excluded count needs an explicit `excluded_rows` from the API. When it is missing, omit the cell (§11 G2); never show a number that only counts the current page.
- Loading: five `—`, not five zeros.
- At `≤1024`, 3+2 grid with hairline dividers removed on wrapped cells.

### 5.4 Filters and search

| Control | Behaviour |
|---|---|
| Status chips | `الكل`, `صالحة`, `تحذيرات`, `أخطاء`, `مستثناة`; each shows the count and maps to `status=` |
| Search | `q` param; placeholder `ابحث باسم ولي الأمر أو رقم الهاتف`; debounce 300ms; spinner inside the field while fetching |
| Clear | A `مسح عوامل التصفية` text button appears only when a filter/search is active |
| Result line | `عرض 50 من 137 سطرًا` under the table, pluralised |

Server-side filtering. Applying a filter must not lose unsaved row edits — **block filter/search while a row is in edit mode** with a short inline note `احفظ التعديل أو ألغِه أولًا.` rather than silently discarding.

### 5.5 Table columns

RTL order, first column at the right:

| # | Column | Content | @1440 | @1024 | @768 |
|---|---|---|---|---|---|
| 1 | ولي الأمر | `normalized_data.guardian_name`; second line muted `الفصل: {fee_period}` when present | 190 | 170 | 150 |
| 2 | الهاتف | `<bdi dir="ltr">` E.164; muted second line `مفقود` / `غير صالح` when that warning exists | 140 | 130 | hidden→expand |
| 3 | الطالب | student name or `—` | 130 | hidden→expand | hidden→expand |
| 4 | المتبقي | amount, tabular, right edge aligned; red when negative | 120 | 110 | 100 |
| 5 | المدفوع | amount or `—` | 110 | hidden→expand | hidden→expand |
| 6 | العملة | ISO code in `<bdi>`, 11px, muted | 80 | 70 | 64 |
| 7 | الحالة | `StatusPill` + issue count `2 تحذيرات` | 130 | 120 | 100 |
| 8 | المصدر | `صف 5` or `صفحة 3 · صف 12` | 96 | 84 | 72 |
| 9 | إجراء | edit + exclude/restore, 2 × 44px | 104 | 104 | 96 |

- Total ≈ 1100px at 1440 inside ~1140px of usable width. No horizontal scroll.
- When the `العملة` column is dropped (≤768, or any width where it does not fit), the currency moves **inline into the amount cell** as a muted 10px suffix: `600,000.00 SYP` in one `<bdi dir="ltr">`. An amount must never appear without its currency.
- Expanding a row (chevron or the status cell's `عرض التفاصيل`) reveals the hidden columns as a key/value grid plus the full issue list and the original source values.
- `<th scope="row">` on the guardian cell; `<caption class="sr-only">أسطر كشف {filename}</caption>`.
- Sticky `thead` while the page scrolls (`position: sticky; top: 0; z-index: 1` inside the card) — the header row stays readable across 50 rows. Do not stick the sticky action bar and the table header at the same edge.

### 5.6 Inline editing

Editing is **on demand, one row at a time**. Seven always-live inputs per row would turn a review screen into a form and make "what changed?" unanswerable.

Flow:

1. Row is read-only text. On hover/focus the action cell reveals `تعديل` (pencil, 44×44, `aria-label="تعديل سجل {guardian}"`).
2. `تعديل` switches that row into edit mode: editable cells become inputs (`h-10`, `fd-input`, 13px, tabular for money), the action cell becomes `حفظ` + `إلغاء`, the row gets a 2px brand inline-start marker and `aria-busy="false"`.
3. The rest of the table stays read-only and the filter chips are disabled with the note from §5.4.
4. `حفظ` → `PATCH /imports/{id}/rows/{row_id}` with only changed keys. `إلغاء` restores the snapshot. `Esc` = cancel, `Enter` = save, both announced.
5. On save: the row re-renders from the PATCH response and a `role="status"` line announces `تم تحديث السجل وأُعيد التحقق منه.` Focus returns to the row's `تعديل` button. Counts refresh from a background `GET /imports/{id}`; the strip keeps its previous values until the new ones land — never flashes `—` (see §11 G8).
6. On failure: the API `message_ar` appears under the field it belongs to (mapped by `validation_errors[].field`); if unmapped, in a `role="alert"` line under the row. The row stays in edit mode with the user's values — never silently reverted.

Field-level rules:

| Field | Input | Notes |
|---|---|---|
| اسم ولي الأمر | text | Trim on save; empty → the row becomes `invalid` (MISSING_GUARDIAN) |
| رقم الهاتف | `inputMode="tel"`, `dir="ltr"`, `<bdi>` around the value | Original preserved; helper under the field: `يمكن إدخال الأرقام العربية أو اللاتينية.` |
| المتبقي | `inputMode="decimal"`, `dir="ltr"` | Accepts Arabic-Indic digits; helper `لا يعيد النظام حساب الرصيد.` |
| المدفوع | `inputMode="decimal"`, `dir="ltr"` | Optional; clearing sets it to empty, not 0 |
| العملة | select from the school's currencies when known, else text, `dir="ltr"`, uppercase | Never default silently |
| اسم الطالب | text | Optional |
| الفصل الدراسي | text | Optional |

Money inputs are **strings to and from the API**. Never route them through `Number`.

### 5.7 Provenance: corrections and source values

FR-FIN-12 requires prior values to survive. When a field differs from the staged original:

```
600,000.00
الأصل: ٦٠٠٬٠٠٠        ← 11px muted, with a restore affordance
```

- The original is shown beneath the current value, prefixed `الأصل:`.
- Arabic-Indic source values are displayed as-is in the original line (that is the evidence), while the working value uses Latin digits.
- A `استعادة القيمة الأصلية` action lives in the expanded row detail, not as a third affordance in every cell.
- No strikethrough anywhere; strike-through on money reads as a discount.

### 5.8 Row status treatment

| Status | Row | Pill | Issue content |
|---|---|---|---|
| `valid` | default | green `صالح` | none |
| `warning` | 3px amber inline-start marker, no fill | amber `تحذير` | messages always visible when 1, summarised when >2: `2 تحذيرات` + expand |
| `invalid` | tint `color-mix(--fd-red-soft 55%, --fd-surface)` + 3px red inline-start marker | red `خطأ` | first message always visible under the row; `عرض كل الأخطاء` expands |
| `excluded` | `--fd-surface-alt`, text stays `--fd-ink`/`--fd-ink-muted` (contrast preserved, no CSS opacity on text) | neutral `مستثنى` | issues remain readable (a user may restore the row) |

Issue rendering (`RowIssues`):

- Rendered inside the row's second line (a `<tr>` spanning all columns) so it is adjacent to the record and never in a tooltip or a hover-only popover.
- Each issue: 16px icon (`AlertCircle` / `TriangleAlert`), text 12px, severity implied by icon + colour + the word in the message where useful.
- Codes (`MISSING_PHONE`) are **not** shown as primary text. They may appear as a muted monospace suffix in the expanded detail for support purposes.
- Error text uses `--fd-red-text`; warning text `--fd-amber-text`; both on `--fd-surface`/soft tints ≥ 4.5:1.
- `aria-describedby` on the row's primary action points to the issue list id, so a screen-reader user hears the reason when they reach the action.
- Duplicate-specific shortcut: `استثناء هذا السجل` appears as a secondary action on `DUPLICATE_ROW` rows. Do not offer "exclude the other one" — the contract does not return the matched row id (§11 G6).

### 5.9 Exclusion

- Control: a toggle button in the action cell — `استثناء` (`Ban` icon) when included, `استعادة` (`Undo2`) when excluded. `aria-pressed` mirrors state; accessible name includes the guardian.
- Immediate, no dialog: exclusion is reversible, per-row, and a dialog per row would be noise. It is announced with `role="status"`: `تم استثناء السجل. لن يدخل أي حملة.`
- The excluded row does not move or disappear from `الكل`; it restyles in place. Under the `مستثناة` filter it appears; under `صالحة` it does not.
- `PATCH` failure: revert the visual state, `role="alert"` with the API message, focus stays on the toggle.
- Bulk action `استثناء الأسطر ذات الأخطاء` appears next to the `أخطاء` chip when `invalid > 0` (not inside a count cell): opens a `Dialog` — title `استثناء الأسطر ذات الأخطاء`, body `سيتم استثناء {n} من الأسطر. يمكن استعادة السجلات لاحقًا.`, primary `استثناء الأسطر ({n})` in **brand** (reversible, not destructive).
- Never auto-exclude duplicates on load. The user decides.

### 5.10 Sticky confirmation bar

Present when the batch is `review_required` or `ready_to_confirm`. The wireframe shows the **blocked** state (one error present) with warnings acknowledged:

```
┌────────────────────────────────────────────────────────────────────────┐
│ جاهزة 5 · مستثناة 1 · تحذيرات 2              SYP 2,400,000.00         │
│ ✓ راجعت التحذيرات وأفهم أن السجلات ستُستورد كما هي.   [تأكيد الاستيراد] │
│ لا يمكن التأكيد: سجل واحد به خطأ. [عرض الأخطاء]                        │
└────────────────────────────────────────────────────────────────────────┘
```

Layout:

- Sticky to the viewport bottom inside `.fd-content`, `bottom-0`, background `--fd-surface` at 96% with a 1px `--fd-line` top border and `--fd-shadow`, 16px padding, 16px radius on top corners only.
- Start side: eligibility sentence + `CurrencyTotals`. End side: `تأكيد الاستيراد` (`h-11`, brand).
- At `≤1024`: two rows — counts/totals on the first, actions on the second; warnings checkbox moves above the actions.
- At `≤767`: totals collapse to `SYP 2,400,000.00` plus `عرض التفاصيل`; the primary button becomes full width; the bar keeps a 16px safe-area bottom padding (`pb-[max(16px,env(safe-area-inset-bottom))]`).
- The bar must never cover the last row: the table container gets `pb-32` when the bar is present.

Content rules:

- `CurrencyTotals` renders **one line per currency**. Never sum across currencies. If a batch has SYP and USD, two lines, and no combined figure anywhere.
- Totals come from the batch aggregate (`totals_by_currency`), covering all non-excluded, non-invalid rows — never a sum of the visible page. If the API does not return the aggregate, **omit the totals line** instead of showing a partial sum (§11 G12).
- Zero-balance rows count as ready but are labelled: `برصيد صفر: 2 — لن تُرسل لها تذكيرات.` (label-first, so the number never has to agree with the noun).
- Warnings count uses the number of warning **rows**, not issues.
- The acknowledgment checkbox is rendered **only** when warning rows exist; with zero warnings the bar jumps straight from counts to the button.

### 5.11 Confirm gating and disabled state

The primary button is disabled in exactly four situations, each with a **visible, adjacent reason** and `aria-describedby` pointing at it:

| Condition | Button | Reason line |
|---|---|---|
| Blocking errors on included rows | disabled | `لا يمكن التأكيد: {n} سجل به أخطاء. صحّحها أو استثنِها.` + `عرض الأخطاء` (focuses the first invalid row) |
| Warnings present, acknowledgment unchecked | disabled | `أكّد أنك راجعت التحذيرات للمتابعة.` |
| Row save / confirm request in flight | disabled, `aria-busy` | `جارٍ حفظ التعديل…` / `جارٍ التأكيد…` |
| No includable rows | disabled | `لا توجد سجلات قابلة للتأكيد. استعد سجلًا واحدًا على الأقل.` |

Additional rules:

- A disabled button may sit at 50% opacity (exempt from 1.4.3), but the **reason text** is the accessible path and must stay ≥ 4.5:1. Never rely on a greyed button alone.
- The error reason links to the first invalid row: it scrolls with `behavior: "auto"` and moves focus to that row's edit control.
- When errors exist, the primary action shifts emphasis: `عرض الأخطاء` becomes the visually strongest control in the bar.
- Confirm is **never** hidden behind a menu.

### 5.12 Confirmation dialog

Uses `Dialog` (not the red `ConfirmDialog`) because confirmation is the intended action; the destructive treatment belongs to cancel.

```
تأكيد الاستيراد
سيتم إنشاء سجلات مالية من 5 أسطر في «الفصل الأول» من ملف sample-01.xlsx.
لا يمكن التراجع عن التأكيد.

السجلات المالية: 5                  SYP 2,400,000.00
المستثناة: 1
برصيد صفر: 1 — لن تُرسل لها تذكيرات

التحذيرات (2)
• رقم الهاتف مفقود — سجل واحد
• الرصيد صفر — سجل واحد

[x] راجعت التحذيرات وأفهم أن السجلات ستُستورد كما هي.   ← only when warnings > 0

[إلغاء]                              [تأكيد وإنشاء السجلات]
```

- Title 16px/600; body 13px; money right edge aligned; one currency line per currency.
- The stat lines and totals come from the same batch aggregate as the bar; when `totals_by_currency` is unavailable, show counts only (§11 G12).
- `إلغاء` is the autofocus target (`data-autofocus`) — the safe action.
- Primary label `تأكيد وإنشاء السجلات` (specific), busy label `جارٍ التأكيد…`.
- On success: dialog closes, the page navigates to `/statements/{id}?confirmed=1`; the detail page shows a `role="status"` banner `تم تأكيد الاستيراد. أُنشئت 5 سجلات مالية.` and focus moves to that banner (`tabIndex={-1}`).
- On idempotent replay (already confirmed): still navigate to the detail with `تم تأكيد الاستيراد مسبقًا.` — do not show an error.
- On failure: the dialog stays open, `role="alert"` inside it with the API message, all values preserved.

### 5.13 Read-only states

| Batch status | Review screen |
|---|---|
| `confirmed` | Banner green: `تم تأكيد هذا الاستيراد في {confirmed_at} بواسطة {confirmed_by}. السجلات للعرض فقط.` + `عرض التفاصيل`. Editing and confirm controls removed, filters kept. |
| `cancelled` | Banner neutral: `أُلغي هذا الاستيراد. لم تُنشأ أي سجلات مالية.` + `العودة إلى الكشوف`. |
| `failed` | Banner red with `error_summary` + `رفع ملف آخر`. Table absent. |
| `processing` | Skeleton table + `جارٍ تحليل الملف…`; no actions. |
| `uploaded` | Redirect to the wizard at step 2 (no rows to review). |

### 5.14 States

| State | Treatment |
|---|---|
| **Loading** | Skeleton header meta, 5 skeleton count cells, 8 skeleton rows at 64px, skeleton bar. Filters visible but inert. |
| **Filtered empty** | `EmptyState` inside the table card: icon `FilterX`, title `لا توجد أسطر مطابقة`, description `جرّب حالة أخرى أو امسح البحث.`, action `مسح عوامل التصفية`. |
| **No rows at all** | `لم نستخرج أسطرًا من هذا الملف` + the scanned/empty guidance from §4.8 + `رفع ملف آخر`. |
| **Load error** | Inline `role="alert"` banner above the table: `تعذر تحميل أسطر الكشف.` + API message + `إعادة المحاولة`. The header, counts (`—`), and filters remain. |
| **Row save error** | Field-level or row-level as in §5.6; page stays. |

### 5.15 Pagination

`page_size=50`, footer `عرض 50 من 137 سطرًا` + `السابق` / `التالي` 44px buttons. Changing page while editing is blocked by the same rule as filtering. Page changes do not reset filters; filters do reset to page 1.

---

## 6. Screen 4 — Import detail (`/statements/[id]`)

### 6.1 Structure

```
┌────────────────────────────────────────────────────────────────────────┐
│ كشوف الأقساط / sample-01.xlsx                        ← breadcrumb      │
│ sample-01-multi-sheet.xlsx  [مؤكد]               [مراجعة الأسطر] [⋯]  │
│ الفصل الأول · رُفع 2026-11-03 20:26 بواسطة أ. خالد                     │
├────────────────────────────────────────────────────────────────────────┤
│  الأسطر 7 │ صالحة 5 │ بها أخطاء 1 │ مكررة 1 │ مستثناة 0               │
├──────────────────────────────────────────┬─────────────────────────────┤
│ الحالة والتحذيرات                        │ بيانات الملف                │
│ [panel]                                  │ dl: النوع، الورقة…           │
│                                          │ الملف الأصلي ↗              │
│ مطابقة الأعمدة (details)                 │ معرّف الدفعة [نسخ]          │
└──────────────────────────────────────────┴─────────────────────────────┘
```

Two columns at `≥1280` (`grid-cols-[1.6fr_0.9fr]`, 20px gap); one column below, with the metadata card first (it is shorter and answers "what is this file?").

### 6.2 Header

- Breadcrumb: `كشوف الأقساط` / filename (`aria-current="page"`).
- Title: filename, `<bdi>`.
- Status pill next to the title.
- Meta line: `{worksheet_name or "ملف PDF"} · رُفع {created_at} · بواسطة {uploader}`.
- Primary action (conditional): `مراجعة الأسطر` for `review_required` / `ready_to_confirm`.
- Overflow menu (`⋯`, 44×44, `aria-label="إجراءات إضافية"`): `عرض الملف الأصلي`, `تغيير مطابقة الأعمدة` (reviewable only), `إلغاء الاستيراد` (danger text, reviewable statuses only). The menu is the only place cancel lives on this screen.
- `confirmed` batches: primary action becomes `عرض سجلات الأقساط` **only when that route exists**; otherwise show no primary action (M2 has no fee-ledger route).

### 6.3 Counts

Up to five cells, same `CountStrip`:

| Cell | Source | Note |
|---|---|---|
| الأسطر | `total_rows` | |
| صالحة | `valid_rows` | |
| بها أخطاء | `invalid_rows` | red when > 0 |
| مكررة | `duplicate_rows` | amber when > 0 |
| مستثناة | needs an explicit `excluded_rows` count | **omit the cell** when the API does not return it. `total − valid − invalid − duplicate` is not a safe derivation (§11 G2) |

Do not show `مؤكدة` unless the API returns a confirmed count.

### 6.4 Status and warnings panel

- `error_summary` (when present): red panel, title `سبب الفشل`, body verbatim, plus `لم تُنشأ أي سجلات مالية.` and a `رفع ملف آخر` action.
- `warnings[]`: list, one row per warning, `TriangleAlert` (amber) or `CircleAlert` (red for `severity: error`), `message_ar` as primary text; the `code` as an 11px muted `<bdi>` suffix. No accordion; warnings are few and matter.
- Empty warnings: do not render an empty panel. Instead a single muted line under the counts: `لا توجد تحذيرات على هذا الكشف.` — only after load.
- `duplicate_reason` (when present): a `سبب رفع نسخة مكررة` block in the metadata card, quoted verbatim.
- Scanned PDF: the warning list plus the amber guidance block from §4.8, with `رفع ملف بديل` and `إلغاء الاستيراد`.

### 6.5 Metadata card

`<dl>` rows, 12px, label `--fd-ink-muted`, value `--fd-ink`:

| Row | Value |
|---|---|
| نوع الملف | `Excel (.xlsx)` / `PDF` |
| الورقة | `{worksheet_name}` or `—` |
| تاريخ الرفع | `2026-11-03 20:26` |
| رفع بواسطة | name, else short ID in `<bdi>` (see G3) |
| تاريخ التأكيد | `2026-11-03 20:31` or `—` |
| أكّده | name or `—` |
| الملف الأصلي | `عرض الملف` link → `GET /files/{source_file_id}`, `target="_blank" rel="noopener"`, arrow icon, accessible name `عرض الملف الأصلي (يفتح في تبويب جديد)`, 44px tall |
| معرّف الدفعة | first 8 chars, `font-mono` `<bdi>`, `title` = full ID **plus** a `نسخ` button (never title-only) |

Timestamps use the same format as lists so a reviewer can compare them directly. If `cancelled` has no timestamp in the response, the row is omitted rather than replaced with a guess (G1).

### 6.6 Column mapping disclosure

A `<details>` element (native, keyboard accessible, no custom JS) titled `مطابقة الأعمدة المستخدمة`, open by default when the batch is not `confirmed`.

Content: a two-column definition list — `الحقل` (Arabic label) / `العمود في الملف` (source header in `<bdi>`). Missing optional fields: `— (غير مطابق)`.

This is the provenance record for "why did this import produce these numbers", so it is not hidden behind a tooltip or an "advanced" tab.

### 6.7 Actions and states

| Status | Actions |
|---|---|
| `uploaded` | `اختيار الورقة` (→ wizard), overflow: `إلغاء الاستيراد` |
| `review_required`, `ready_to_confirm` | `مراجعة الأسطر`, overflow: `عرض الملف الأصلي`, `تغيير مطابقة الأعمدة`, `إلغاء الاستيراد` |
| `confirmed` | `عرض الملف الأصلي`, `نسخ معرّف الدفعة`. No cancel. |
| `cancelled` | `عرض الملف الأصلي`. No other actions. |
| `failed` | `رفع ملف آخر`, `عرض الملف الأصلي`. No cancel — a failed batch is already terminal. |
| `processing` | none; status pill only + `جارٍ التحليل…` |

404 / not found: `EmptyState` `لم نجد هذا الكشف`, description `قد يكون الرابط قديمًا أو أن الكشف غير متاح لحسابك.`, action `العودة إلى الكشوف`.

403: `لا تملك صلاحية عرض هذا الكشف.` with the same back action. Do not leak existence details.

---

## 7. RTL, tables, numbers, currency

### 7.1 RTL layout

| Rule | Implementation |
|---|---|
| Direction | Inherited from `html dir="rtl" lang="ar"`; no local `dir` flips except LTR-insulated values |
| Column order | First column (guardian/file) at the **right**; actions at the far left |
| Spacing | Logical only: `ps-*`, `pe-*`, `ms-*`, `me-*`, `border-s`, `border-e`, `start-0`, `end-0`. No `ml/mr/pl/pr/left/right` |
| Row markers | `border-inline-start` so the warning/error bar sits on the reading-start edge |
| Breadcrumb separators | `/` in a `bdi`, or a chevron rotated via `rtl:rotate-180`; never a mirrored arrow glyph |
| Icons | Do not mirror: upload, file, check, alert, ban, undo. Mirror only the directional breadcrumb chevron if a chevron is used |
| Numbers inside Arabic text | Wrap the number run in `<bdi dir="ltr">` so "7 أسطر" never renders as "أسطر 7" |
| Mixed-script filenames | `<bdi>` + `dir="auto"` on the container; truncate with `text-overflow: ellipsis` at the logical end |
| Dialogs | Native `<dialog>` centred; content inherits RTL; file names in `<bdi>` |
| Scroll | `overflow-x: auto` only on the mapping `<details>` if a header is very long; never page-level |

### 7.2 Table rules

- Base: `.fd-table` (13px, `text-right` on RTL, tinted header, 44px+ row height).
- Import tables override row height to `min-h-[60px]` (two-line cells).
- `<caption class="sr-only">` on every table; `scope="col"` on every `<th>`; `scope="row"` on the identifying cell.
- Header cells: 11–12px, `--fd-ink-muted`, `font-medium`, `whitespace-nowrap`.
- Numeric cells: `font-variant-numeric: tabular-nums`; the figure is wrapped in `<bdi dir="ltr">`; aligned to the reading-start edge (right in RTL) so decimal points line up column-wise.
- Dates and phone numbers: `whitespace-nowrap`.
- Row hover: `--fd-surface-alt`. Focus-within: `--fd-brand-soft` at 40% (color-mix) so keyboard travel is visible across a row.
- Borders: 1px `--fd-line` horizontal only; no vertical grid lines (the board has none).
- Empty table body: one `<tr><td colSpan={n}>` containing the shared `EmptyState`.
- No zebra striping. Status and error markers already carry the visual rhythm.

### 7.3 Numbers

- **Latin digits everywhere** in UI chrome (`ar-SY-u-nu-latn` behaviour), matching M1.
- Source values typed with Arabic-Indic digits are preserved and displayed **only** in the `الأصل:` line; the working value is Latin.
- Counts: `tabular-nums`; no thousands separators under 10,000 (`7`, `137`), separators above (`2,400`).
- Money: always two decimals (`600,000.00`) because the store is `NUMERIC(18,2)`; trailing zeros are information, not noise.
- Percentages are not used anywhere in M2.
- **Hard rule:** API money is a decimal **string**. Format it as a string — group the integer part with a regex, keep the fraction verbatim. Never `Number()`, `parseFloat`, or arithmetic in the client. Totals come from the API aggregate; only a complete, non-paged row set may be summed client-side, and even then as decimal strings.

### 7.4 Currency

- Currency is a separate column (`SYP`), 11px muted, `<bdi>`, `lang="en"` optional.
- Never mix currencies in one figure. `CurrencyTotals` renders one line per currency, ordered alphabetically, with the ISO code first (`SYP 2,400,000.00`), the whole string in `<bdi dir="ltr">`.
- Never show a currency symbol fallback. If the school symbol is unavailable, show the ISO code only.
- Zero amounts keep the currency: `0.00 SYP` is meaningful (fully paid); `0` alone is not.
- Negative amounts: leading minus, `--fd-red-text`, and the row is `invalid`. Do not use parentheses (ambiguous in RTL) and do not colour alone — the error pill and message are always present.

### 7.5 Target sizes (44px)

- All buttons, toggles, chips, row actions, pagination, menu triggers, and dialog close: **hit area ≥ 44×44**. Visual height may be 36–40px on desktop **only** if a padded hit area reaches 44.
- Table row actions: `h-11 w-11` icon buttons with 8px gaps (two actions = 96px content width).
- Inline edit inputs: `h-10` visual inside a 60px row; the row itself is the target context.
- Filter chips: `min-h-[36px]` with `py-2` and a 4px negative margin wrapper so the effective target is 44px; `min-h-[44px]` at `≤767`.
- Checkboxes (warning acknowledgment, duplicate override): 20px box inside a `<label>` with `min-h-[44px]` and 12px padding; label text clickable.
- Spacing between adjacent targets: ≥ 8px.
- The 2px focus outline with `outline-offset: 2px` must not be clipped: never `overflow: hidden` on the immediate parent of an interactive element. Inside table cells use `outline-offset: -2px` for inline inputs.

---

## 8. Responsive behaviour

### 8.1 1440 (primary target)

- Shell: 240px sidebar, ~1140px usable content.
- Statements: full 6-column table; summary line single row; CTA at the header's end.
- Upload: 880px wizard column; mapping table full width inside it; stepper horizontal with labels.
- Review: 9 columns, ~1100px; sticky action bar single row (summary start, button end).
- Detail: two columns 1.6fr / 0.9fr; counts strip 5 cells in one row.
- No horizontal scroll anywhere at this width. This is the acceptance width for the visual comparison to the approved dashboard.

### 8.2 1024

- Sidebar collapses to 76px (existing media query), content ~916px.
- Statements: drop `رافع الملف`; the uploader moves into the filename cell's second line as `xlsx · أ. خالد`.
- Upload: wizard 760px; stepper labels stay (they fit); mapping select column 220px.
- Review: 7 columns (drop `المدفوع`, `الطالب`); counts strip 3+2; sticky bar two rows (summary + actions); filter chips wrap to a second line rather than scrolling.
- Detail: single column; metadata card **above** the warnings panel (it answers the first question).
- Table header stays sticky; the sticky bar height grows to ~120px, so the table gets `pb-40`.

### 8.3 768

- Content ~660px with 16px padding.
- Statements: 4 columns — `الملف` (with the status pill stacked under the filename), `الأسطر`, `تاريخ الرفع`, `إجراء`. Rows become 72–80px. The summary line wraps to two lines; keep it one line with overflow ellipsis if it would exceed two.
- Upload: wizard full width; dropzone 180px; stepper becomes a **compact** indicator (`الخطوة 2 من 4` + step name) — the full horizontal stepper does not fit; keep the `<ol>` in the DOM with `sr-only` labels for assistive tech if the visual is condensed.
- Mapping table becomes **field cards**: one card per canonical field — label + requirement marker, source select (full width), original-header hint. Required-field errors sit inside the card. No horizontal scroll.
- Review: 5 columns — `ولي الأمر`, `المتبقي` (with the ISO code inline), `الحالة`, `المصدر`, `إجراء`. Hidden fields (`الهاتف`, `الطالب`, `المدفوع`) move to the always-available expanded row, which becomes a `<button aria-expanded>` row titled `تفاصيل السجل` and is expanded by default for `invalid`/`warning` rows.
- Exclusion and edit actions remain 44px; the edit controls become `حفظ`/`إلغاء` text buttons on a second line of the row (not icon-only) to avoid a 3-icon squeeze.
- Sticky bar: full width, two rows, primary full width, totals collapsed to one currency line + `عرض التفاصيل`.
- Detail: single column; counts 2+3; mapping `<details>` collapsed by default (long file headers).
- Dialogs: `w-[min(32rem,90vw)]` already handles this; the confirm dialog's money lines wrap rather than scroll.

### 8.4 Below 768 (not a target, must not break)

- No page-level horizontal scroll (1.4.10). Tables degrade by dropping columns, never by shrinking text below 13px.
- The wizard and dialogs stay usable at 375px.
- The shell's known mobile limits (from `design-review.md` §6) are out of scope here; import screens must not add new ones.

### 8.5 What must never change across widths

- Money is never truncated or abbreviated (`2.4M` is forbidden).
- The status pill is never hidden.
- Currency stays attached to every amount (separate column at 1440/1024, inline suffix below that).
- The blocking-error reason is never hidden.
- The confirm action is never in a menu.
- The source reference is never removed from a row.

---

## 9. Copy

Tone: plain, specific, second person, no system jargon, no English codes in primary text. Every error names the next action.

### 9.1 Status labels

| Value | Label |
|---|---|
| `uploaded` | تم الرفع |
| `processing` | قيد المعالجة |
| `review_required` | بانتظار المراجعة |
| `ready_to_confirm` | جاهز للتأكيد |
| `confirmed` | مؤكد |
| `failed` | فشل الاستيراد |
| `cancelled` | ملغى |

Row statuses:

| Value | Pill | Count label |
|---|---|---|
| `valid` | صالح | صالحة |
| `warning` | تحذير | بها تحذيرات |
| `invalid` | خطأ | بها أخطاء |
| `excluded` | مستثنى | مستثناة |

(Agreement note: the pill describes one record (masculine singular); the counter describes a non-human plural, which takes the feminine singular form.)

### 9.2 Screen copy

| Where | Copy |
|---|---|
| List H1 / subtitle | `كشوف الأقساط` / `رفع كشوف Excel وPDF، مراجعتها، ثم تأكيدها.` |
| CTA | `رفع كشف جديد` |
| List empty | `لا توجد كشوف بعد` / `ارفع كشف Excel أو PDF لاستخراج السجلات المالية ومراجعتها قبل التأكيد.` |
| Wizard steps | `الملف` · `الورقة` · `الأعمدة` · `الاستخراج` |
| Dropzone | `اسحب ملف الكشف إلى هنا` / `أو` / `اختيار ملف` / `Excel (.xlsx) أو PDF` |
| Upload stages | `جارٍ رفع الملف…` → `جارٍ تحليل الملف…` |
| Sheet step | `اختر الورقة التي تحتوي على جدول الأقساط` / `عدد الورقات في الملف: {n}.` |
| Mapping step | `مطابقة الأعمدة` / `اختر العمود المقابل لكل حقل. الحقول المعلّمة بـ * مطلوبة.` |
| Mapping helper | `بدون رقم هاتف يبقى السجل المالي، لكنه لا يصلح لرسائل التذكير.` |
| Process | `استخراج السجلات` / `جارٍ استخراج السجلات…` |
| Extraction done | `تم استخراج الأسطر` / `فتح المراجعة` / `تعديل مطابقة الأعمدة` |
| Review H1 | filename |
| Review filters | `الكل` · `صالحة` · `تحذيرات` · `أخطاء` · `مستثناة` |
| Review search | `ابحث باسم ولي الأمر أو رقم الهاتف` |
| Confirm bar | `جاهزة {n} · مستثناة {n} · تحذيرات {n}` (label-first) |
| Confirm button | `تأكيد الاستيراد` / `جارٍ التأكيد…` |
| Confirm dialog | `تأكيد الاستيراد` / `سيتم إنشاء سجلات مالية من أسطر «{worksheet}» في ملف {filename}. لا يمكن التراجع عن التأكيد.` (the count lives in the stat lines, not the sentence) |
| Acknowledgment | `راجعت التحذيرات وأفهم أن السجلات ستُستورد كما هي.` |
| Dialog primary | `تأكيد وإنشاء السجلات` |
| Success | `تم تأكيد الاستيراد. أُنشئت {n} سجلات مالية.` |
| Cancel import | `إلغاء الاستيراد` / `لن تُنشأ أي سجلات مالية. سيبقى الكشف في السجل بحالة «ملغى».` |
| Cancelled | `أُلغي هذا الاستيراد. لم تُنشأ أي سجلات مالية.` |
| Row saved | `تم تحديث السجل وأُعيد التحقق منه.` |
| Excluded | `تم استثناء السجل. لن يدخل أي حملة.` |
| Restored | `تمت استعادة السجل.` |
| Read-only (confirmed) | `تم تأكيد هذا الاستيراد. السجلات للعرض فقط.` |
| 409 duplicate | `هذا الملف مرفوع مسبقًا` |

### 9.3 Validation and error messages

| Code | Message (API `message_ar` expected) | UI hint / next step |
|---|---|---|
| `MISSING_GUARDIAN` | `اسم ولي الأمر مفقود.` | `أضف الاسم أو استثنِ السجل.` |
| `MISSING_BALANCE` | `المبلغ المتبقي مفقود.` | `أدخل المتبقي من الملف.` |
| `NEGATIVE_BALANCE` | `المبلغ المتبقي سالب.` | `راجع القيمة في الملف الأصلي.` |
| `MISSING_CURRENCY` | `العملة مفقودة.` | `أضف العملة (مثل SYP).` |
| `AMBIGUOUS_MONEY` | `صيغة المبلغ غير واضحة.` | `أدخل المبلغ بصيغة واضحة، مثل 600000.00.` |
| `DUPLICATE_ROW` | `هذا السجل مكرر داخل الملف.` | `استثنِ أحد السجلين للمتابعة.` + `استثناء هذا السجل` |
| `MISSING_PHONE` | `رقم الهاتف مفقود.` | `يمكن استيراد السجل، لكنه لن يكون جاهزًا للرسائل.` |
| `INVALID_PHONE` | `رقم الهاتف غير صالح.` | `صحّح الرقم أو استورد السجل دون رسائل.` |
| `SHARED_PHONE` | `الرقم مستخدم لأكثر من ولي أمر.` | `راجع الأسماء؛ لن يدمج النظام أولياء الأمور تلقائيًا.` |
| `TOTAL_DISCREPANCY` | `المتبقي في الملف يختلف عن (الإجمالي − المدفوع).` | `احتفظنا بقيمة الملف. راجعها قبل التأكيد.` |
| `ZERO_BALANCE` | `الرصيد صفر.` | `لن تُرسل له تذكيرات.` |
| `SCANNED_PDF` | `الملف يبدو ممسوحًا ضوئيًا.` | `ارفع نسخة نصية أو أدخل البيانات يدويًا.` |

UI-level errors (client or transport):

| Situation | Copy |
|---|---|
| Unsupported type | `هذا النوع غير مدعوم. المسموح: Excel (.xlsx) أو PDF.` |
| Empty file | `الملف فارغ. اختر ملفًا يحتوي على بيانات.` |
| Oversize | `حجم الملف أكبر من الحد المسموح ({n} ميغابايت).` (n only when the API returns it) |
| Unreadable file | `تعذر قراءة الملف. تأكد أنه ملف Excel أو PDF سليم.` |
| Too many rows/pages | `الملف أكبر من الحد المسموح ({n} سطرًا). قسّم الكشف ثم ارفع كل جزء.` |
| No header | `لم نجد صف عناوين واضحًا في هذه الورقة.` |
| Empty sheet | `هذه الورقة لا تحتوي على بيانات.` |
| No rows | `لم نستخرج أي سطر من هذا الملف.` |
| Duplicate file | `هذا الملف مرفوع مسبقًا.` |
| Duplicate reason required | `اذكر سبب رفع الملف مرة أخرى.` |
| Confirm blocked | `لا يمكن التأكيد: {n} سجل به أخطاء. صحّحها أو استثنِها.` |
| Warnings unchecked | `أكّد أنك راجعت التحذيرات للمتابعة.` |
| No includable rows | `لا توجد سجلات قابلة للتأكيد. استعد سجلًا واحدًا على الأقل.` |
| Not found | `لم نجد هذا الكشف.` |
| Permission | `لا تملك صلاحية {الرفع/المراجعة/التأكيد}.` |
| Session expired | `انتهت الجلسة. سجّل الدخول مرة أخرى.` |
| Network | `تعذر الاتصال بالخادم. تحقق من الشبكة وأعد المحاولة.` |
| Generic fallback | `تعذر تنفيذ الطلب. أعد المحاولة.` (only when no API `message_ar`) |

Rules:

- Prefer the API's `message_ar` verbatim. Add a UI hint **only** when the API message does not name an action.
- Never show `code` values as primary text; they belong in the expanded detail, muted.
- Never say `خطأ في الخادم` for a validation problem.
- Never say `تم` for a request that has not returned.

### 9.4 Plurals

Use `Intl.PluralRules("ar")` with the correct noun:

| Count | سجل | كشف | تحذير |
|---|---|---|---|
| 0 | `لا سجلات` | `لا كشوف` | `لا تحذيرات` |
| 1 | `سجل واحد` | `كشف واحد` | `تحذير واحد` |
| 2 | `سجلان` | `كشفان` | `تحذيران` |
| 3–10 | `{n} سجلات` | `{n} كشوف` | `{n} تحذيرات` |
| 11–99 | `{n} سجلًا` | `{n} كشفًا` | `{n} تحذيرًا` |
| 100+ | `{n} سجل` | `{n} كشف` | `{n} تحذير` |

Examples: `عرض 50 من 137 سطرًا`, `3 سجلات جاهزة`, `11 سجلًا`, `سجلان بحاجة إلى تصحيح`.

```
/**
 * Arabic counted noun. Every count in the import UI goes through one helper
 * (e.g. formatCountAr(n, "سجل")) so 1 / 2 / 3–10 / 11+ never regress.
 */
```

Every counted noun in this document is a template for that helper. Hand-written strings such as `{n} أسطر` are forbidden: they are wrong for 1 and 2.

**Sentence contexts:** after a verb, the dual changes case and is easy to get wrong (`استثناء سجلين`, not `سجلان`). Prefer a **label-first** form in bars, dialogs, and confirmations, which is agreement-proof and matches `CountStrip`:

| Instead of | Write |
|---|---|
| `2 سجل مستثنى` | `المستثناة: 2` |
| `2 تحذيرات` | `التحذيرات: 2` |
| `سيتم استثناء 2 سجل` | `سيتم استثناء 2 من الأسطر` / `استثناء الأسطر (2)` |

Counted-noun forms are still correct where the number is nominative and the noun is plural, e.g. `5 سجلات مالية`, `3 أسطر بحاجة إلى تصحيح`.

### 9.5 Dates and sizes

- Tables, bars, dialogs: `2026-11-03 20:26` (24h, unambiguous, matches the board).
- Never `03/11/2026` (ambiguous) and never `م/ص` suffixes.
- File size: `1.4 ميغابايت` with Latin digits; `كيلوبايت` under 1 MB.
- Keywords that stay Latin: `Excel`, `PDF`, `.xlsx`, currency codes (`SYP`, `USD`), and file names.

### 9.6 Words to avoid

| Don't | Use |
|---|---|
| `عملية` (for the import) | `استيراد` / `كشف` |
| `خطأ في النظام` | the actual cause + next step |
| `البيانات` (vague) | `السجلات` / `الأسطر` / `الأرصدة` |
| `تم بنجاح` | say what happened: `تم تأكيد الاستيراد. أُنشئت 5 سجلات مالية.` |
| `موافق` / `نعم` as a primary action | the verb: `تأكيد وإنشاء السجلات`, `إلغاء الاستيراد` |
| `معالجة` as a user-visible noun | `تحليل` / `استخراج` / `مراجعة` |
| `لا توجد بيانات` | name what is missing and the next step |

---

## 10. Accessibility checklist (WCAG 2.2 AA)

| SC | Requirement for these screens | How |
|---|---|---|
| 1.1.1 | Non-text content | All icons `aria-hidden`; status conveyed by text; the `processing` spinner has adjacent text |
| 1.3.1 | Info & relationships | Real `<table>` with `<caption>` and `scope`; mapping is a table at ≥1024 and field cards below with `<dl>` semantics; `CountStrip` is a `<dl>` |
| 1.3.2 | Meaningful sequence | Reading order = visual order: breadcrumb → title → counts → filters → table → actions |
| 1.3.4 | Orientation | No orientation lock; both orientations usable at 768 |
| 1.4.1 | Use of colour | Status = dot + label + (for rows) border marker and message. Never colour alone |
| 1.4.3 | Contrast (text) | All pairs from the token set pass (5.37–9.43 on soft tints). Disabled labels exempt but accompanied by ≥4.5:1 reason text |
| 1.4.4 | Resize text | 200% zoom without loss; no fixed-height text containers; rows use `min-height` |
| 1.4.10 | Reflow | 320px wide, no page-level horizontal scroll; tables drop columns; wizard single column |
| 1.4.11 | Non-text contrast | Dropzone border `--fd-line-input` (3.11:1); input borders same; progress bar track vs fill ≥3:1 |
| 1.4.12 | Text spacing | 1.6 line-height; no clipping when spacing is increased; cells use padding, not fixed heights |
| 1.4.13 | Content on hover/focus | No content is hover-only: errors, originals, and full IDs are all reachable without hovering |
| 2.1.1 | Keyboard | Dropzone, selects, chips, inline edit, dialogs, pagination all keyboard operable; file input is a real input |
| 2.1.2 | No keyboard trap | Native `<dialog>` with Esc; inline edit escapes with Esc/Tab |
| 2.1.4 | Character shortcuts | None added |
| 2.2.1 | Timing | No auto-advance, no auto-redirect, no upload timeout countdown |
| 2.4.1 | Bypass blocks | Existing skip link covers these routes |
| 2.4.2 | Page titled | Per-route titles (§1) |
| 2.4.3 | Focus order | After upload → focus the step heading (`tabIndex={-1}`); after process → focus the result heading; after save → focus the row's `تعديل`; after dialog close → the trigger |
| 2.4.6 | Headings & labels | One `<h1>`; wizard steps `<h2>`; card headings `<h2>`; no heading levels skipped |
| 2.4.7 | Focus visible | 2px brand outline; inside cells `outline-offset: -2px`; focus-within row tint |
| 2.5.3 | Label in name | `aria-label` contains the visible verb + the file/guardian name |
| 2.5.7 | Dragging movements | Drag-and-drop is optional; `اختيار ملف` does the same job |
| 2.5.8 | Target size | ≥44×44 on every control (§7.5) |
| 3.1.1 | Language of page | `lang="ar"` inherited |
| 3.1.2 | Language of parts | `lang="en"` on ISO codes and known Latin file names where practical; `<bdi>` otherwise |
| 3.2.2 | On input | Choosing a sheet or mapping does not navigate; only the explicit `التالي`/`استخراج` does |
| 3.3.1 | Error identification | Every error is text in a `role="alert"`; `aria-invalid` + `aria-describedby` on the field |
| 3.3.2 | Labels or instructions | Requirement markers explained in text; phone helper; money helper; duplicate reason hint |
| 3.3.3 | Error suggestion | Every message names the fix (§9.3) |
| 3.3.4 | Error prevention | Confirm dialog with counts; duplicate override requires a reason; exclusion is reversible; destructive cancel is in a dialog |
| 3.3.7 | Redundant entry | File stays selected on back; mapping persists across steps; the sheet choice survives a mapping error |
| 4.1.2 | Name, role, value | Native controls; `aria-pressed` on chips and exclude toggles; `aria-expanded` on row details; no custom div-buttons |
| 4.1.3 | Status messages | `role="status"` for upload stage, save, exclude, confirm success; `role="alert"` for blocking errors and failures. Never both for one message |
| 2.3.1 | Three flashes | No flashing content |
| 2.5.1 | Pointer gestures | No multipoint or path gestures |

### 10.1 Live-region map

| Event | Region | Politeness |
|---|---|---|
| Upload stage change | Wizard status line | `status` (polite) |
| Upload complete / extraction complete | Result panel | `status` |
| Row saved | Table-level status line | `status` |
| Row excluded / restored | Table-level status line | `status` |
| Confirm success | Detail banner | `status` |
| Blocking error (upload, mapping, confirm) | Adjacent alert block | `alert` |
| Network failure | Screen-level banner | `alert` |

Announcements must not fire on initial render; mount the region empty and fill it on the event.

### 10.2 Manual test pass (required before M2 sign-off)

1. Full flow with keyboard only: list → upload → sheet → mapping → process → review → edit → exclude → acknowledge → confirm → detail.
2. Screen reader (NVDA at minimum) on: the review table (row/cell reading), an invalid row's error announcement, the confirm dialog, and the success banner.
3. 200% zoom and 320px width on review and mapping.
4. `prefers-reduced-motion` on: skeletons, sticky bar entrance, row flash.
5. Arabic-Indic digits in a phone field and a money field.
6. A batch with two currencies — confirm no combined total appears anywhere.

---

## 11. Dependencies, gaps, and assumptions

**Resolution note (3 November 2026):** The backend import contract now returns `uploaded_by_name`, `excluded_rows`, `totals_by_currency`, `max_upload_mb`, `cancelled_at`, and `updated_at`. G1–G4 and G12 are resolved; the UI still hides any optional field that is absent.

| ID | Gap | Impact | Proposed handling |
|---|---|---|---|
| G1 | No `cancelled_at` / `updated_at` in `ImportDetail` | The detail page cannot state *when* a batch was cancelled | Omit the row; ask the backend lane to add `cancelled_at` (or show `status` only) |
| G2 | `ImportDetail` has no `excluded_rows` count | The review count strip and detail counts cannot be exact | Omit the `مستثناة` cell; ask the backend for `excluded_rows`. Only derive it when the full row set is on screen (`total ≤ page_size`) |
| G3 | `uploaded_by` is a user id | Staff cannot resolve names (no user list permission) | Show the name if the API adds `uploaded_by_name`; otherwise an 8-char `<bdi>` ID with full disclosure, never a raw UUID as the primary label |
| G4 | No upload-limit value in any response | Copy cannot state the max size | Copy formats only; render the server's size error when it happens. Ask for `max_upload_mb` in the import config payload |
| G5 | `available_sheets` is names only | No row counts per sheet | Show names only; do not invent counts |
| G6 | Duplicate rows expose no partner row id | Cannot link "the other record" or offer "exclude the duplicate pair" | Per-row `استثناء هذا السجل` only |
| G7 | No mapping confidence | Cannot rank suggestions | `مطابقة تلقائية` tag only |
| G8 | `PATCH` returns `StagedRow` but not batch counts | The count strip is briefly stale after an edit | Update the row from the PATCH response, then refetch `GET /imports/{id}`; keep the previous counts visible until the new ones arrive (no `—` flash) |
| G9 | No `q` on `GET /imports` | Search box cannot work on the list | Do not render it |
| G10 | No batch-level "processing" progress | The review screen for `processing` can only say `جارٍ التحليل…` | Honest indeterminate copy; no fake percentage |
| G11 | No pre-process sample values per column | The mapping preview column cannot be populated before the first extraction | Show the preview column only when rows are already staged; otherwise omit it |
| G12 | No per-currency aggregate in `ImportDetail` | The confirm bar and detail cannot show trustworthy totals from a paged row list | Ask for `totals_by_currency` (string amounts) on the batch; until then omit the totals line and rely on counts |

Assumptions to confirm with the backend/frontend lanes:

1. `POST /imports` accepts `FormData` and the client must **not** set `Content-Type` (browser boundary). The existing `apiFetch` sets JSON whenever a body exists — the import client needs its own path that omits the header.
2. `process` can be called repeatedly; re-processing replaces staged rows. The UI warns before it does.
3. `confirm` is idempotent, so a double-click or a retry after a network error is safe; the UI still disables during the request.
4. Warning acknowledgment is only required when warning rows exist; `acknowledge_warnings: true` is always sent when the checkbox is shown and checked.
5. Excluded rows are never counted as blocking, even with errors.

---

## 12. Component inventory for the frontend lane

Suggested files (under the agreed scope `apps/web/components/imports/`):

| File | Responsibility |
|---|---|
| `ImportStatusPill.tsx` | status → label/tone, `processing` spinner |
| `CountStrip.tsx` | up to 5-cell `<dl>` with logical dividers and status colouring |
| `FilterChips.tsx` | `role="group"`, `aria-pressed`, counts, 44px targets |
| `FileDropzone.tsx` | input + label + drag handlers + client checks + selected-file state |
| `UploadProgress.tsx` | determinate/indeterminate bar + `role="progressbar"` |
| `StepIndicator.tsx` | `<ol>` steps, `aria-current="step"`, condensed variant at ≤768 |
| `SheetPicker.tsx` | radio cards with real inputs |
| `ColumnMappingTable.tsx` | required/optional markers, duplicate-column validation, manual header entry; card variant ≤768 |
| `ExtractionResult.tsx` | success / zero-row / scanned / failed panels |
| `DuplicateFileDialog.tsx` | 409 override with reason |
| `StagedRowsTable.tsx` | table shell, sticky head, row expansion, card variant |
| `EditableCell.tsx` | view/edit toggle, Enter/Esc, original-value line |
| `RowIssues.tsx` | always-visible issue list, expand/collapse, `aria-describedby` wiring |
| `CurrencyTotals.tsx` | one line per currency, `<bdi>` |
| `ConfirmImportBar.tsx` | sticky bar, gating reasons, acknowledgment |
| `ConfirmImportDialog.tsx` | `Dialog`-based confirmation summary |
| `CancelImportDialog.tsx` | danger-styled cancel with consequence copy |
| `ImportWarnings.tsx` | warning/error list with severity icons |
| `format.ts` (in `lib/`) | `formatDecimalString`, `formatCountAr`, `formatFileSize`, `shortId` |

Component conventions:

- Server data in, callbacks out; no fetch inside presentational components.
- Every interactive element gets an explicit type (`type="button"`).
- No `window.confirm`, no `alert`, no tooltip-only information.
- Money formatted from strings only; currency never inferred.
- All colours via CSS variables; all spacing via logical properties.

---

## 13. Top 5 design decisions

1. **The list is a queue, not a dashboard.** `/statements` has no KPI cards; one inline summary line plus filters and the import history. The only actionable table must be visible at 1024 without scrolling past decoration.
2. **Upload is a staged, non-committal flow with no auto-redirect.** File → sheet → mapping → extraction → explicit "open review". Nothing implies money exists before confirmation, and completing a step never moves the user without a keypress.
3. **Review edits are on demand, one row at a time, with the original value always visible.** This keeps a 50-row ledger readable, makes corrections auditable (`الأصل:` line), and prevents a table of live inputs from turning the screen into a form.
4. **Errors sit in the row, never in a tooltip or a summary card.** Every invalid row shows its first message inline with an expandable full list, and the confirm button carries a visible, described reason when it is blocked.
5. **The confirmation bar is the single place where eligibility is decided**: per-currency totals (never combined), eligible/excluded/warning counts, an explicit warning acknowledgment, and a dialog that names exactly what will be created and that it cannot be undone.

---

## 14. Anti-patterns (reject in implementation review)

- A progress percentage that is not measured.
- A disabled confirm button with no visible reason.
- An error that only appears on hover, or only in a toast.
- Status shown by colour alone (including row tint without a pill or message).
- A combined total across currencies.
- `Number()` / `parseFloat` applied to an API money string.
- An empty state rendered before the request resolves.
- `0` used as a loading placeholder.
- A currency symbol fallback when settings are unavailable.
- Auto-excluding duplicates on load.
- `window.confirm` or `alert`.
- Removing a column at 768 without exposing its value in the expanded row.
- Page-level horizontal scrolling.
- A custom `<div>` that looks like a checkbox, radio, or table.
- Red styling for a reversible, non-destructive action (confirm import, exclude row, restore row).

---

## 15. Verification for this spec

Not assigned to this lane beyond producing the document. When the frontend lane reports, the following are the design-visible checks this document is meant to support:

- [ ] 1440 capture of all four screens, default and one error state each.
- [ ] 1024 and 768 captures of the review table and mapping step.
- [ ] Keyboard-only pass of the full import flow.
- [ ] Confirm gating states: errors present, warnings unacknowledged, ready, busy.
- [ ] Two-currency batch shows two total lines and no combined figure.
- [ ] Source row/page visible on every row at every breakpoint.
- [ ] Copy reviewed against §9 for plurals and avoided words.
