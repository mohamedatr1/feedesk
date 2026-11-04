# M3 — Campaign and Template Screens Design Spec

**Scope:** `/campaigns`, `/campaigns/new`, `/campaigns/[id]`, `/settings/templates` (+ version detail, editor).
**Status:** Spec for the M3 frontend campaign lane. No application code in this lane.
**Date:** 3 November 2026
**Sources of truth:** `docs/m3/api-contract.md` (binding), `docs/m3/subagent-brief.md`, `docs/design/design-review.md`, `docs/design/tokens.css`, `docs/design/m2-import-screens.md`.

**Design language:** unchanged from the approved M1 dashboard and the M2 import set — cream `--fd-bg`, olive `--fd-brand`, 16px card radius, 10px control radius, IBM Plex Sans Arabic, 13px tables, tinted headers, dot + label pills, calm empty states. **The shell is not redesigned.** `AppShell`, `PageHeader`, `Protected`, `Dialog`, `ConfirmDialog`, `StatusPill`, `EmptyState`, `CurrencyTotals`, `TablePager` are reused as-is.

**The M3 boundary, stated once and enforced everywhere:** approval freezes a campaign and creates pending records. **Nothing is sent.** There is no send button, no "sent" state, no delivery count, no progress, no provider status, and no `/messages` link. Every campaign surface says so in plain Arabic, in the same place, every time.

---

## 0. Principles for this screen set

1. **Approval is a governance act, not a send action.** The screen that approves a campaign is the screen that makes it unchangeable. It must never look like the screen that dispatches it.
2. **The snapshot is the product.** After approval the user is looking at a frozen, hashed record. Show the hash, the approver, the timestamp, and say plainly that the data no longer follows the source.
3. **Nothing is previewed that the server has not computed.** Eligibility, grouping, amounts, and rendered Arabic text come from the API. The client never approximates a recipient list, never sums across currencies, and never renders a placeholder message body as if it were real.
4. **Exclusions are explained, not hidden.** Every excluded guardian has a reason and a truthful next step (which, for confirmed-import data, usually means a new import).
5. **Counts and money are unknown until known.** Loading renders `—`, never `0`, never a currency symbol.
6. **One irreversible action per screen.** Submit → approve → cancel are separate, each with its own confirmation. No action hides in a menu.

### 0.1 Contract coverage

| Contract requirement | Where this spec answers it |
|---|---|
| `CampaignSummary` fields (list, totals, creator/approver) | §2, §11.2 |
| Statuses `draft` / `awaiting_approval` / `approved` / `cancelled` | §2.2, §11.1 |
| `POST /campaigns` (confirmed import, template default, 422 codes) | §3 |
| `PATCH /campaigns/{id}` (draft only, revision) | §4.7, §14 G5 |
| `previewed_at`, `blocking_reasons`, `can_submit/can_approve/can_cancel` | §4.3–§4.6 |
| `recipients[]` with per-message `message` | §4.6, §8.4 |
| `excluded[]` with `reasons[].code/message_ar` | §4.5, §11.3 |
| `POST /campaigns/{id}/submit` (`expected_revision`) | §8.1 |
| `POST /campaigns/{id}/approve` (`acknowledge_warnings`, `WARNINGS_UNACKNOWLEDGED`) | §8.2 |
| `snapshot_hash` + immutable snapshot, no provider call | §5, §8.2 |
| `POST /campaigns/{id}/cancel` (reason, approved-cancel permission) | §8.3, §6 |
| `GET /templates`, `/templates/active`, `/templates/variables`, `/templates/{id}`, `POST /templates`, `POST /templates/{id}/activate` | §7 |
| Unknown variables allowed at save, block approval | §7.4, §11.6 |
| Staff `templates.view` read-only | §7.7 |
| "UI must always show that sending is not enabled" | §1.4 |

---

## 1. Shared foundations

### 1.1 Screen map

```
/campaigns
   ├─ حملة جديدة ─────────────────► /campaigns/new
   │                                   └─ إنشاء المسودة ─► /campaigns/[id]
   ├─ متابعة الإعداد (draft) ────────► /campaigns/[id]
   ├─ مراجعة واعتماد (awaiting) ─────► /campaigns/[id]
   └─ عرض (approved / cancelled) ────► /campaigns/[id]

/campaigns/[id]
   ├─ إرسال للاعتماد ────────────────► dialog → same page (awaiting_approval)
   ├─ اعتماد الحملة ─────────────────► dialog (acknowledgement + warning list) → same page
   ├─ إلغاء الحملة ──────────────────► ConfirmDialog (reason) → same page
   └─ معاينة الرسالة (per row) ──────► message preview dialog

/settings
   └─ قوالب الرسائل ─────────────────► /settings/templates
                                          ├─ قالب جديد ──────► /settings/templates/new
                                          ├─ إصدار جديد ─────► /settings/templates/new?from={id}
                                          ├─ عرض الإصدار ────► /settings/templates/[id]
                                          └─ تفعيل ──────────► dialog → same page
```

**Route titles** (per-route `metadata`, matching M1/M2):

| Route | `<title>` |
|---|---|
| `/campaigns` | الحملات — FeeDesk |
| `/campaigns/new` | حملة جديدة — FeeDesk |
| `/campaigns/[id]` | تفاصيل الحملة — FeeDesk |
| `/settings/templates` | قوالب الرسائل — FeeDesk |
| `/settings/templates/new` | محرر القالب — FeeDesk |
| `/settings/templates/[id]` | إصدار القالب — FeeDesk |

### 1.2 Permission gating

From `/auth/me.permissions`:

| Permission | Controls |
|---|---|
| `campaigns.view` | `/campaigns`, `/campaigns/[id]` |
| `campaigns.create` | `حملة جديدة` button and `/campaigns/new` |
| `campaigns.preview` | the recipient table and `معاينة الرسالة` |
| `campaigns.edit` | `تعديل`, submit (`campaigns.submit`), cancel for draft/awaiting |
| `campaigns.submit` | `إرسال للاعتماد` |
| `campaigns.approve` | `اعتماد الحملة`, cancel for approved |
| `templates.view` | `/settings/templates` (read-only for staff) |
| `templates.manage` | create/version/activate |

Rules:

- Missing permission → the control is **absent**, not disabled, with one exception: an approval card that explains who can approve (`الاعتماد متاح لمدير النظام.`). Absence is honest; a disabled button with no reason is not.
- The API is authoritative. `can_submit`, `can_approve`, `can_cancel` from `CampaignDetail` override client-side permission guesses; the UI renders what those flags allow and what the role permits, whichever is stricter.
- 403 on a direct URL: `EmptyState` `لا تملك صلاحية عرض هذه الحملة.` + `العودة إلى الحملات`. Never leak whether the campaign exists.

### 1.3 Primitives reused, and what is new

Reused without restyling: `PageHeader` (30px/700 H1 + 14px subtitle), `EmptyState`, `StatusPill` (dot + label), `Dialog`, `ConfirmDialog`, `CurrencyTotals`, `TablePager`, `.fd-card`, `.fd-btn-*`, `.fd-input`, `.fd-table`, `.fd-skeleton`.

| New component | Responsibility |
|---|---|
| `CampaignStatusPill.tsx` | status → `{label, tone}` map on top of `StatusPill` |
| `CampaignFilterTabs.tsx` | URL-backed status filter, `aria-current="page"`, counts |
| `CampaignCounts.tsx` | 4-cell `<dl>` strip, same anatomy as `ImportCounts` |
| `NoSendNotice.tsx` | the M3 "not sending" strip, two densities |
| `CampaignFacts.tsx` | `<dl>` of source/template/creator/approver/hash |
| `SnapshotHash.tsx` | full hash + copy button + `role="status"` confirmation |
| `RecipientTable.tsx` | recipient rows, validation pills, preview action |
| `ExcludedTable.tsx` | excluded rows, reason list per row |
| `CampaignWarnings.tsx` | warning list with counts (amber) |
| `BlockingReasons.tsx` | blocking list with the fix per code (red) |
| `MessagePreviewDialog.tsx` | per-message preview, prev/next, character count |
| `CampaignActionBar.tsx` | sticky, state-driven primary/secondary actions |
| `SubmitCampaignDialog.tsx` | send-for-approval summary |
| `ApproveCampaignDialog.tsx` | warning list + acknowledgement + irreversible statement |
| `CancelCampaignDialog.tsx` | `ConfirmDialog` + reason field |
| `ConfirmedImportPicker.tsx` | builder step 1 |
| `TemplateVersionList.tsx` | grouped version table |
| `TemplateEditor.tsx` + `VariablePalette.tsx` | Arabic body editor, allowed-variable insertion |
| `ActivateVersionDialog.tsx` | activation consequences |
| `lib/campaign-format.ts` (frontend lane) | `campaignStatusLabel`, `exclusionHint`, `formatCountAr` |

Do **not** refactor the M2 import components in this lane. If `ImportCounts` is generalised into a shared `CountStrip`, that happens as a separate, product-wide change (§0 of `m2-import-screens.md` makes the same argument about the P2 type sweep).

### 1.4 The no-send notice

One component, two densities, one sentence.

| Density | Used on | Markup |
|---|---|---|
| **Strip** | list, builder, draft/awaiting detail, cancelled detail | Full-width row inside or directly under the header: `Info` 16px icon (`--fd-brand`), 12.5px text `--fd-ink-muted`, background `--fd-brand-soft`, 1px `--fd-line` border, radius 10, `min-h-[44px]`, `px-4 py-2`. Text: `الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة.` |
| **Full** | approved detail, directly under the snapshot card | Same colours, 4px inline-start brand bar, title `لم تُرسل أي رسالة` (13px/600) + body `اعتماد الحملة يثبّت نسختها فقط. الإرسال إلى المزوّد غير مفعّل، ولا توجد أي رسالة قيد التسليم.` |

Rules:

- Never dismissible, never a toast, never behind a help icon.
- Never worded as a capability ("قريبًا") — this is a current, deliberate limitation.
- Exactly once per screen. Do not repeat it in the action bar, the dialog, and a banner at the same time; the dialog gets one short clause instead.
- `role="note"` is not a real ARIA role for this; keep it plain text. It is page content, so it is read in the normal flow.

### 1.5 Motion

Restrained and inherited:

- Sticky bar entrance: 160ms fade + 8px rise, once, `prefers-reduced-motion` aware (already global).
- Snapshot card on first approved render: no animation beyond a 200ms background settle. Approval is not a celebration.
- Hash copy: no animation; the status line changes.
- Tabs: 120ms background transition.
- No confetti, no checkmark draw, no count-up numbers, no shimmer except the existing `.fd-skeleton`.

---

## 2. Screen 1 — Campaign list (`/campaigns`)

### 2.1 Structure

```
┌─────────────────────────────────────────────────────────────────────────┐
│  الحملات                                              [حملة جديدة]       │  PageHeader
│  إعداد حملات التذكير من الكشوف المؤكدة، معاينتها، ثم اعتمادها.            │
│                                                                          │
│  ⓘ الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة.               │  NoSendNotice
│                                                                          │
│  الحملات: 5 · بانتظار الاعتماد: 2 · آخر حملة 2026-11-03 20:26            │  summary line
├─────────────────────────────────────────────────────────────────────────┤
│ [الكل 5] [مسودة 2] [بانتظار الاعتماد 1] [معتمدة 2] [ملغاة 0]            │  filter tabs (nav)
├─────────────────────────────────────────────────────────────────────────┤
│  الحملة            المصدر        المستلمون  الإجماليات  الحالة  أنشأها  اعتمادها  …│
│  تذكير رسوم الفصل الأول   sample-01.xlsx  4          SYP 2,100,000.00  ●بانتظار… │
│  القالب: تذكير الرسوم · إ1   مؤكد 2026-11-03       مستثنى 2      USD 400.00       │
└─────────────────────────────────────────────────────────────────────────┘
```

The list leads with the workflow, not with KPIs. No stat cards: the dashboard owns totals, and four cards would push the only actionable table below the fold at 1024.

### 2.2 Header and filters

| Element | Detail |
|---|---|
| H1 | `الحملات` |
| Subtitle | `إعداد حملات التذكير من الكشوف المؤكدة، معاينتها، ثم اعتمادها.` |
| Primary action | `حملة جديدة`, `Plus` icon, `h-11`, brand fill. Absent without `campaigns.create`. |
| Summary line | `الحملات: {n} · بانتظار الاعتماد: {n} · آخر حملة {YYYY-MM-DD HH:mm}` — 12px, `--fd-ink-muted`, segments omitted when zero, whole line omitted when the list is empty. Loading: `— · — · —`. |

Filter row is a **navigation**, not a JavaScript tabset — the filter lives in the URL (`?status=`), so back/forward and refresh stay honest:

```html
<nav aria-label="تصفية الحملات حسب الحالة" class="...">
  <a href="/campaigns"            aria-current="page"> الكل <span class="tabular-nums">5</span></a>
  <a href="/campaigns?status=draft"> مسودة <span class="tabular-nums">2</span></a>
  …
</nav>
```

- Tabs in workflow order: `الكل`, `مسودة`, `بانتظار الاعتماد`, `معتمدة`, `ملغاة`.
- Active tab: brand fill + white text (same treatment as `.fd-nav-item-active`); inactive: transparent with `--fd-ink-muted`, hover `--fd-surface-alt`.
- Visual height 40px, hit area ≥44px (`min-h-[44px]`, `py-2`); at `≤767` the row wraps to two lines instead of scrolling.
- Counts come from `GET /campaigns?status=…&page_size=1` per tab. **While a count is unresolved show no number at all** — not `0`. If a count request fails, keep the label without a number and do not fail the page.
- The tab with zero results is **not** removed: an empty `ملغاة` tab is useful information.

### 2.3 Table

RTL order, first column at the right. Target ≤1152px usable at 1440.

| # | Column | Content | @1440 | Alignment |
|---|---|---|---|---|
| 1 | الحملة | `<th scope="row">` link to detail: name (1 line, truncated, `<bdi dir="auto">`) + muted second line `القالب: {template_name} · إ{version}` | 240 | start |
| 2 | المصدر | Source filename in `<bdi>`, second line `مؤكد 2026-11-03 20:26` | 150 | start |
| 3 | المستلمون | `recipient_count` 15px/600 tabular; second line muted `مستثنى {n}` when `excluded_count > 0` | 100 | start |
| 4 | الإجماليات | `CurrencyTotals` (one line per currency, `SYP 2,100,000.00`), 12px | 170 | start |
| 5 | الحالة | `CampaignStatusPill`; second line depends on status (§2.5) | 128 | start |
| 6 | أنشأها | `created_by_name` + `YYYY-MM-DD HH:mm` muted | 132 | start |
| 7 | اعتمادها | `approved_by_name` + `approved_at`, or `—` | 140 | start |
| 8 | إجراء | 1–2 actions, `h-11` | 96 | start |

Rules:

- Totals are **always per currency, never combined**. If a campaign has three or more currencies, the cell shows two lines plus a `<details>` whose `<summary>` reads `+{n} عملات` and whose content is the full `CurrencyTotals`. Two currencies (the realistic case) render inline. Money is never truncated or abbreviated.
- `أنشأها` and `اعتمادها` are separate columns on purpose: "who approved this and when" is the audit question this screen exists to answer. Both use `whitespace-nowrap` for the date line.
- Missing approver fields render `—`, never an empty cell and never a guessed name.
- Row height ≥64px (two-line cells). Hover `--fd-surface-alt`; focus-within `color-mix(--fd-brand-soft 40%, transparent)`.
- `<caption class="sr-only">قائمة الحملات. الأحدث أولًا، مع عدد المستلمين والإجماليات لكل عملة.</caption>`, `scope="col"` everywhere, `scope="row"` on the campaign name.
- Long Arabic names: one line + `truncate`; the detail page carries the full name. Never a `title`-only disclosure.

### 2.4 Row actions

| Status | Primary action | Secondary |
|---|---|---|
| `draft` | `متابعة الإعداد` → `/campaigns/{id}` (secondary weight) | — |
| `awaiting_approval` | `مراجعة واعتماد` → detail (primary weight **only** for admins) | — |
| `approved` | `عرض` → detail (secondary) | — |
| `cancelled` | `عرض` → detail (secondary) | — |

- The whole campaign-name cell is the row link; the action column is the explicit, labelled control (`aria-label="مراجعة حملة {name}"`).
- **No cancel, no approve, no submit from the list.** Irreversible actions happen on the detail page where the consequences are on screen. The list is for orientation.
- Do not add a `⋯` overflow menu in M3; there is nothing to put in it.

### 2.5 Status vocabulary (list second line)

| Status | Pill | Tone | Second line |
|---|---|---|---|
| `draft` | مسودة | neutral | `آخر معاينة {time}` or `لم تُراجع بعد` |
| `awaiting_approval` | بانتظار الاعتماد | amber | `أُرسلت للاعتماد {time}` |
| `approved` | معتمدة | green | `اعتُمدت {time}` |
| `cancelled` | ملغاة | neutral | `أُلغيت {time}` |

`ملغاة` is neutral, not red: cancellation is an ended state, not a failure. Red is reserved for blocking problems.

### 2.6 States

| State | Treatment |
|---|---|
| **Loading** | 5 skeleton rows at 64px, skeleton summary line, tabs rendered without counts (`—` suppressed, not `0`), CTA usable. No empty state before resolve. |
| **Empty — no campaigns** | `EmptyState` inside the card, `Send` icon, title `لا توجد حملات بعد`, description `أنشئ حملة من كشف أقساط مؤكد لمعاينة المستلمين والمبالغ قبل الاعتماد.`, action `حملة جديدة` (secondary — the header already carries the primary). Second muted line: `تحتاج كشفًا مؤكدًا أولًا.` with a text link `عرض الكشوف`. |
| **Empty — filtered** | Title `لا توجد حملات بهذه الحالة`, description `جرّب حالة أخرى.`, action `عرض كل الحملات`. |
| **Error** | Inline banner above the table, `role="alert"`, `--fd-red-soft`/`--fd-red-text`: `تعذر تحميل الحملات.` + API `message_ar` on line two + `إعادة المحاولة` (`h-11`). Table header stays visible. |
| **Counts fail, list succeeds** | Page renders; tabs lose their numbers silently. Do not surface a second error. |

Pagination: `page_size=20`, `TablePager` footer (`عرض 1–20 من 47`), hidden when `total ≤ page_size`. `إلغاء`/`التالي` 44px. Pluralisation per §11.7.

---

## 3. Screen 2 — Campaign builder (`/campaigns/new`)

### 3.1 Structure

Single column, `max-w-[880px]`, inside `.fd-content`.

```
┌──────────────────────────────────────────────────────────────────┐
│  الحملات / حملة جديدة                              ← breadcrumb   │
│  حملة جديدة                                                       │
│  اختر كشفًا مؤكدًا وقالبًا، ثم أنشئ المسودة لمعاينة المستلمين.      │
│  ⓘ الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة.          │
├──────────────────────────────────────────────────────────────────┤
│  1  الكشف المؤكد                                                  │
│     (•) sample-01-multi-sheet.xlsx                                │
│         مؤكد 2026-11-03 20:26 · 7 أسطر · SYP, USD                 │
│     ( ) sample-02-single.xlsx                                     │
│         مؤكد 2026-11-02 18:04 · 12 سطرًا · SYP                    │
│     عرض كل الكشوف المؤكدة ↗                                       │
├──────────────────────────────────────────────────────────────────┤
│  2  اسم الحملة                                                    │
│     [ مثال: تذكير رسوم الفصل الأول                    ]           │
│     يظهر في القائمة وفي سجل العمليات.                             │
├──────────────────────────────────────────────────────────────────┤
│  3  قالب الرسالة                                                  │
│     [ تذكير الرسوم الدراسية — الإصدار 1 ▾ ]                       │
│     ⚠ متغيرات غير معروفة: {{discount}} — لن تُعتمد الحملة.        │
│     ┌──────────────────────────────────────────┐                  │
│     │ عزيزنا {{guardian_name}}، ...            │  ← raw body       │
│     └──────────────────────────────────────────┘                  │
├──────────────────────────────────────────────────────────────────┤
│  [إنشاء المسودة]                              [إلغاء]            │  sticky bar
│  بعد الإنشاء تُحسب الاستحقاقات وتظهر المعاينة الكاملة.            │
└──────────────────────────────────────────────────────────────────┘
```

### 3.2 Field 1 — confirmed import

- Source: `GET /imports?status=confirmed&page_size=8` (M2 endpoint, already used by `/statements`). Total via `page_size=1`.
- Presentation: **radio cards**, not a select. A filename chosen from a dropdown in an Arabic form is unreadable, and the date and row count are what make the right choice obvious.
  - Real `<input type="radio" name="source_import_id">` inside a `<label>`; whole card is the hit area; `min-h-[64px]`.
  - Selected: 2px `--fd-brand` border, `--fd-brand-soft` background, check icon **and** `checked` state (never colour alone).
  - Card content: filename in `<bdi dir="auto">` (1 line, truncated); second line `مؤكد {date} · {rows} أسطر`; currency chips (`SYP`, `USD`) only when the import summary actually returns per-currency totals — otherwise omit the chips entirely rather than guessing which currencies the file contains.
- Below the cards: text link `عرض كل الكشوف المؤكدة` → `/statements?status=confirmed` (`h-11` target).
- Empty — no confirmed imports: replace the section with `EmptyState` (`FileCheck` icon) title `لا يوجد كشف مؤكد`, description `تُبنى الحملات من كشوف مؤكدة فقط. أكّد كشفًا أولًا.`, action `عرض الكشوف`. The main button is disabled with the visible reason `اختر كشفًا مؤكدًا للبدء.` — here a disabled button is acceptable because the empty state names the fix immediately above it.
- Loading: 2 skeleton cards at 64px.

### 3.3 Field 2 — campaign name

- `<input class="fd-input h-11" maxlength={120}>`, label `اسم الحملة`, placeholder `مثال: تذكير رسوم الفصل الأول`, hint `يظهر في القائمة وفي سجل العمليات.`
- **Not auto-filled.** A generated name would either embed a Latin filename in an Arabic sentence or invent a period name. The placeholder teaches the pattern instead.
- Empty on submit → inline error under the field: `أدخل اسمًا للحملة.` + `aria-invalid` + `aria-describedby`.
- Trim on submit. No other client-side transformation.

### 3.4 Field 3 — template

- Source: `GET /templates?active_only=true` (all active versions, in case several names are active). Default selection is the response of `GET /templates/active`; if that 404s, nothing is preselected and the builder shows the blocking panel (§3.6).
- Control: native `<select class="fd-input h-11">`. Label `قالب الرسالة`. Option text `{name} — الإصدار {version}`.
- Under the select, the raw body in a read-only box: `--fd-surface-alt`, radius 10, `p-4`, `text-[14px] leading-[1.9]`, `dir="rtl"`, `max-h-[220px] overflow-y-auto`.
  - The body is **not interpolated**. Allowed variables render as inline chips `{{guardian_name}}` (§7.3 styling). A note directly above the box: `نص القالب كما هو. تُستبدل المتغيرات عند إنشاء المسودة.`
  - Reason: interpolating with sample data would be fabricated content in a financial product (the `design-review.md` P1-6 lesson, applied to copy).
- If the selected template has `unknown_variables`, show an amber inline note under the select: `متغيرات غير معروفة في هذا القالب: {{x}}، {{y}}. يمكن إنشاء المسودة، لكن لا يمكن اعتمادها قبل تصحيح القالب.` + admin link `فتح القالب` (absent for staff, replaced with `تواصل مع مدير النظام.`).

### 3.5 Pre-flight checklist

Three real, client-verifiable checks — not a preview:

| Row | Pass | Fail |
|---|---|---|
| `كشف مؤكد` | `تم اختيار كشف مؤكد` | `لم يُختر كشف مؤكد` |
| `اسم الحملة` | `الاسم جاهز` | `أدخل اسمًا للحملة` |
| `قالب رسالة` | `{name} — الإصدار {n}` | `لا يوجد قالب نشط` |

Rendered as a compact `<ul>` with `Check`/`Minus` icons in `--fd-green-text` / `--fd-ink-subtle`, 12px, above the sticky bar. It is a readiness list, not a score.

### 3.6 What the builder deliberately does not show

`POST /campaigns` is the first point at which the server computes eligibility. There is **no preview endpoint before creation** (contract §2). Therefore:

- No recipient count, no totals, no "will exclude N records" estimate on this screen. All would be guesses.
- The primary button label says what actually happens: **`إنشاء المسودة ومعاينة الاستحقاق`** (short form in the bar: `إنشاء المسودة`; the helper line beneath states `بعد الإنشاء تُحسب الاستحقاقات وتظهر المعاينة الكاملة.`).
- No "review then create" wizard step. Creating a draft is reversible-by-cancel and creates no messages.

### 3.7 Sticky bar and submit

- Sticky bottom, same anatomy as M2 §5.10: `--fd-surface` at 96%, 1px top border, `--fd-shadow`, 16px padding, safe-area bottom padding.
- Start: the checklist summary does **not** go here (it is directly above). Bar start is the consequence sentence: `لن تُرسل أي رسالة.`
- End: `إلغاء` (secondary, `h-11`) then `إنشاء المسودة` (primary, `h-11`).
- Busy: `جارٍ إنشاء المسودة…`, both buttons disabled, `aria-busy="true"` on the form card.
- Success: `POST /campaigns` → `router.push('/campaigns/' + id)` **and** a `role="status"` banner on the detail page `أُنشئت المسودة. راجع المستلمين والمبالغ قبل الإرسال للاعتماد.` Focus moves to that banner (`tabIndex={-1}`).
- Errors, in place under the bar, `role="alert"`:

| Code | Copy |
|---|---|
| `IMPORT_NOT_CONFIRMED` | `هذا الكشف غير مؤكد. لا يمكن بناء حملة من كشف غير مؤكد.` + `عرض الكشوف` |
| `NO_ACTIVE_TEMPLATE` | `لا يوجد قالب رسائل نشط. اطلب من مدير النظام تفعيل قالب ثم أعد المحاولة.` |
| `TEMPLATE_NOT_FOUND` | `القالب المحدد غير موجود. اختر قالبًا آخر.` |
| 403 | `لا تملك صلاحية إنشاء حملة.` |
| network | `تعذر الاتصال بالخادم. تحقق من الشبكة وأعد المحاولة.` |

### 3.8 Leaving the builder

- `إلغاء` returns to `/campaigns`. No draft was created, so nothing is orphaned.
- Browser back after creation does not delete the draft; the list shows it as `مسودة`. That is correct and must not be "cleaned up".

---

## 4. Screen 3 — Campaign detail (`/campaigns/[id]`), draft and awaiting

### 4.1 Structure (1440)

```
┌────────────────────────────────────────────────────────────────────────────┐
│ الحملات / تذكير رسوم الفصل الأول                        ← breadcrumb       │
│ تذكير رسوم الفصل الأول  ●بانتظار الاعتماد                                   │
│ القالب: تذكير الرسوم الدراسية · الإصدار 1 · المصدر: sample-01.xlsx          │
│ ⓘ الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة.                    │
├────────────────────────────────────────────────────────────────────────────┤
│  المستلمون 4 │ مستثناة 2 │ تحذيرات 2 │ الحالة بانتظار الاعتماد              │  counts
├───────────────────────────────────────────┬────────────────────────────────┤
│ الإجماليات المستحقة                       │ بيانات الحملة                  │
│ لا تُجمع العملات معًا.                    │ المصدر، القالب، أنشأها،        │
│ SYP 2,100,000.00                          │ أُرسلت للاعتماد، آخر معاينة     │
│ USD 400.00                                │                                │
├───────────────────────────────────────────┴────────────────────────────────┤
│ ⚠ التحذيرات (2)                                                            │
│ • رقم هاتف مشترك بين أكثر من ولي أمر. — العدد: 2                            │
├────────────────────────────────────────────────────────────────────────────┤
│ المستلمون (4)                                    [بحث ...]                 │
│ ولي الأمر  الهاتف  الطلاب  الفصول  المبلغ  العملة  الحالة  إجراء            │
│ …                                                                          │
├────────────────────────────────────────────────────────────────────────────┤
│ المستثناة (2)                                                              │
│ ولي الأمر  الهاتف  المبلغ  العملة  سبب الاستثناء                            │
├────────────────────────────────────────────────────────────────────────────┤
│ [المستلمون: 4 · مستثناة: 2]              [إلغاء الحملة] [إرسال للاعتماد]    │  sticky
└────────────────────────────────────────────────────────────────────────────┘
```

Order is deliberate: counts → money → problems → who receives what → who does not → act. A reviewer can answer "is this correct?" without opening a dialog.

### 4.2 Header

| Element | Content |
|---|---|
| Breadcrumb | `<nav aria-label="مسار التصفح">` → `الحملات` / campaign name (`aria-current="page"`) |
| H1 | Campaign name, `<bdi dir="auto">`, wrapped at 2 lines max |
| Status | `CampaignStatusPill` inline after the H1, baseline-aligned |
| Context line | `القالب: {template_name} · الإصدار {n}` · `المصدر: {source_filename}` — 14px `--fd-ink-muted` |
| Meta line | `أُنشئت {date} بواسطة {name}` — 12px `--fd-ink-subtle` |
| Actions | None in the header. All actions live in the sticky bar (§4.8), so they never scroll away. |

The campaign name is user-authored Arabic, so it can be the H1 (unlike the M2 review screen, where the task name had to lead).

### 4.3 Counts strip

`CampaignCounts`, three cells in this state:

| Cell | Value | Tone |
|---|---|---|
| المستلمون | `recipient_count` | neutral, 24px/700 |
| مستثناة | `excluded_count` | neutral (amber only if >0 **and** the reason is data quality — do not colour it at all; it is not an error of the campaign) |
| التحذيرات | number of warning codes, not the sum of `count` | amber when >0 |

- `invalid_contact_count` is **not** rendered as a cell. Its relationship to `excluded` is not defined by the contract (§14 G2); a cell that contradicts the exclusion list is worse than no cell.
- Loading: three `—`.
- After approval a fourth cell appears: `الرسائل المُنشأة` — only if the API exposes a count (§14 G3). Until then, no cell.

### 4.4 Money panel

- Card title `الإجماليات المستحقة`, 4px×16px brand bar, 14px/600.
- One line per currency, 18px/700 tabular, `SYP` prefix in 12px muted, all inside `<bdi dir="ltr">`. Reuses `CurrencyTotals`; the panel only raises the type size.
- Permanent micro-copy under the title: `لا تُجمع العملات معًا.` (12px, `--fd-ink-subtle`).
- No grand total, no "equivalent in SYP", no symbol fallback.
- Loading: one skeleton line 80px wide, not `0.00`.

### 4.5 Warning and blocking panels

**Warnings — amber (`CampaignWarnings`)**

- Rendered only when `warnings.length > 0`. Header `التحذيرات ({n})`.
- One row per warning: `TriangleAlert` 16px, `message_ar` verbatim as primary text (13px), `العدد: {count}` when present, `code` in 10px muted `<bdi>` at the end of the row.
- Footer line: `التحذيرات لا تمنع الاعتماد، لكن يجب تأكيدها عند الاعتماد.`
- For staff (no approve permission) the footer becomes: `سيطّلع مدير النظام على هذه التحذيرات قبل الاعتماد.`
- No accordion. Warnings are few and they matter.

**Blocking reasons — red (`BlockingReasons`)**

Rendered only when `blocking_reasons.length > 0`. Header `ما يمنع الاعتماد ({n})`. Each row: `CircleAlert` 16px, `--fd-red-text`, `message_ar` verbatim, then a fix line and an action:

| Code | Fix line | Action |
|---|---|---|
| `UNRESOLVED_VARIABLES` | list the unknown variables from the template detail: `المتغيرات: {{a}}، {{b}}` | admin: `فتح القالب` → `/settings/templates/{template_id}`; staff: `تواصل مع مدير النظام لتصحيح القالب.` |
| `TEMPLATE_INACTIVE` | `القالب المستخدم لم يعد نشطًا.` | admin: `تفعيل إصدار` → template screen; staff: `تواصل مع مدير النظام.` |
| `NO_ELIGIBLE_RECIPIENTS` | `لا يوجد ولي أمر مؤهل في هذا الكشف. راجع السجلات المستثناة أدناه.` | `عرض المستثناة` (scrolls to the panel, `behavior: "auto"`) |
| `TEMPLATE_NOT_FOUND` | `لم نجد القالب المستخدم في هذه الحملة.` | `اختيار قالب آخر` (opens edit, draft only) |

- Fetching `GET /templates/{id}` for the variable names is allowed (`templates.view` is on staff too). If it fails, keep the generic `message_ar` and drop the name list — never guess.
- The panel is red but not a `role="alert"` on initial render; only a *newly appeared* blocking reason after an action is announced.

### 4.6 Recipients table

| # | Column | Content | @1440 | @1024 |
|---|---|---|---|---|
| 1 | ولي الأمر | `<th scope="row">`, name; second line muted `{n} أرصدة` from `fee_balance_ids.length` | 200 | 190 |
| 2 | الهاتف | `<bdi dir="ltr">` E.164, `whitespace-nowrap` | 140 | 140 |
| 3 | الطلاب | `student_names` joined with `، `, one line truncate | 190 | hidden→detail |
| 4 | الفصول | `fee_periods` joined with `، `, one line truncate or `—` | 150 | hidden→detail |
| 5 | المبلغ | `formatDecimalString(amount)`, tabular, `--fd-ink` | 110 | 110 |
| 6 | العملة | ISO code, 11px muted `<bdi>` | 80 | inline suffix |
| 7 | الحالة | `صالح` green / `تحذير` amber pill + `{n}` count | 110 | 110 |
| 8 | إجراء | `معاينة الرسالة`, `h-11`, secondary | 120 | 120 |

Rules:

- `<caption class="sr-only">مستلمو حملة {name}، مع المبلغ والعملة وحالة التحقق.</caption>`; `scope="col"`; `scope="row"` on the guardian.
- Amount cells keep their own currency column at 1440/1024; below 1024 the code becomes an inline muted suffix in the same `<bdi>`. **An amount never appears without its currency.**
- `validation_status === "warning"` rows get a 3px `--fd-amber` inline-start marker and no fill (M2 §5.8). The warning itself is visible in the message preview dialog; never colour-only.
- Header sticks while the table scrolls inside the card (`position: sticky; top: 0; z-index: 1`).
- Row hover `--fd-surface-alt`; the whole row is not clickable — the action is.
- **Search**: `campaigns` detail returns every recipient in one payload (no pagination in the contract). The table renders all of them with a client-side filter input `ابحث باسم ولي الأمر أو رقم الهاتف` (debounce unnecessary, <200 rows expected). If `recipients.length > 100`, add pagination at 50 with `TablePager`. Never claim a server search that does not exist.
- Empty (0 recipients): `EmptyState` inside the table card, `Users` icon, title `لا يوجد مستلم مؤهل`, description `كل السجلات في هذا الكشف استُثنيت. راجع أسباب الاستثناء أدناه.`, action `عرض المستثناة`.
- Loading: 6 skeleton rows; counts stay `—`.

### 4.7 Facts card

`<dl>`, 12px, two columns (label muted / value):

| Row | Draft / awaiting | Approved |
|---|---|---|
| المصدر | filename link → `/statements/{source_import_id}` | same, frozen note `محفوظ في النسخة` |
| القالب | `{name} · الإصدار {n}` | same |
| أُنشئت | `{date}` · `{created_by_name}` | same |
| أُرسلت للاعتماد | `{submitted_at}` or `—` | `{submitted_at}` |
| آخر معاينة | `{previewed_at}` (`حُسبت المعاينة`) | `—` (frozen) |
| اعتُمدت | `—` | `{date}` · `{approved_by_name}` |
| البصمة | `—` | full hash (§5.3) |

- `revision` is **not** displayed. It is a concurrency token, not a fact a school admin needs; showing it would read as a developer console (`design-review.md` P1-10).
- `PATCH` (edit name/template) is not a separate screen: the draft header gets an `تعديل` secondary action in the bar that turns the H1 into an input and the template row into a select, with `حفظ`/`إلغاء`. One editable region at a time; `source_import_id` is shown but not editable, with the note `لا يمكن تغيير الكشف بعد إنشاء الحملة. أنشئ حملة جديدة.`
- Exception: if the draft has already been submitted, `تعديل` is absent — editing is draft-only (§8.4).

### 4.8 Sticky action bar (state-driven)

Same shell as M2 §5.10. Content by state:

**Draft**

```
┌──────────────────────────────────────────────────────────────────────────┐
│ المستلمون: 4 · مستثناة: 2 · التحذيرات: 2        [إلغاء الحملة] [تعديل] [إرسال للاعتماد] │
│ السبب عند التعطيل: لا يمكن الإرسال للاعتماد: لا يوجد مستلم مؤهل. [عرض الأسباب] │
└──────────────────────────────────────────────────────────────────────────┘
```

- Primary `إرسال للاعتماد` (`h-11`, brand). Disabled **only** when a blocking reason exists or recipients = 0, always with a visible, `aria-describedby`-linked reason line that names the first blocking reason and links to the panel.
- `تعديل` secondary, `campaigns.edit` only. `إلغاء الحملة` ghost/danger text, `campaigns.edit` only, 8px from `تعديل`.
- Start side shows label-first counts (agreement-proof, matches `CampaignCounts`).

**Awaiting approval**

- Start: `بانتظار الاعتماد منذ {submitted_at}`.
- Admin: `اعتماد الحملة` (brand primary) + `إلغاء الحملة` (danger text) + `تعديل` **absent** (draft-only).
- Staff: no approve control. Static line `الاعتماد متاح لمدير النظام.` in `--fd-ink-muted`, plus `إلغاء الحملة`.
- There is **no withdraw/unsubmit action**: the contract has none. Do not invent one. Copy that explains the absence if asked is `لا يمكن سحب الحملة من الاعتماد. يمكنك إلغاؤها وإنشاء حملة جديدة.` (only in a help tooltip? no — nowhere. It is not needed until a user asks; the absence speaks for itself.)

**Approved** and **cancelled**: §5.4 and §6.

Bar mechanics:

- `position: sticky; bottom: 0; z-index: 20`, `--fd-surface` at 96%, `border-t`, `--fd-shadow`, `border-radius: 16px 16px 0 0`, `padding-bottom: max(16px, env(safe-area-inset-bottom))`.
- The page container gets `pb-32` so the last excluded row is never covered.
- At `≤1024`: two rows — counts/totals on the first, actions on the second, primary full-width at `≤767`.
- Never hide the primary action behind a menu; never place two primaries side by side.

---

## 5. Screen 4 — Approved campaign, read-only snapshot

### 5.1 The two-banner stack

```
┌──────────────────────────────────────────────────────────────────────────┐
│ 🔒 نسخة معتمدة ومقفلة                                      ●معتمدة      │
│ اعتُمدت في 2026-11-03 21:12 بواسطة أ. خالد.                               │
│ المستلمون المثبّتون: 4 · الإجماليات: SYP 2,100,000.00 · USD 400.00        │
│ لا يمكن تعديل هذه الحملة أو مستلميها.                                      │
│ البصمة: a3f9c1…7b21   [نسخ البصمة الكاملة]        ← SnapshotHash         │
├──────────────────────────────────────────────────────────────────────────┤
│ ⓘ لم تُرسل أي رسالة                                                       │
│ اعتماد الحملة يثبّت نسختها فقط. الإرسال إلى المزوّد غير مفعّل،            │
│ ولا توجد أي رسالة قيد التسليم.                                           │
└──────────────────────────────────────────────────────────────────────────┘
```

- Snapshot card: `--fd-green-soft` background, 1px `--fd-green` border at 30% via `color-mix`, `Lock` 18px `--fd-green-text`, radius 16, `p-5`. Title 15px/700, body 13px.
- The no-send block sits directly beneath it, full density (§1.4), visually quieter. Two cards, two jobs: *this is fixed* / *nothing was sent*.
- Both appear before any table. The reviewer must not reach a recipient list believing messages went out.

### 5.2 What changes from the draft view

| Element | Approved behaviour |
|---|---|
| Recipients table | Same columns, `id` now populated. Data comes from persisted snapshots — a note under the card header: `بيانات مثبّتة وقت الاعتماد. لا تتغير بتغيّر الكشف أو أولياء الأمور.` |
| Excluded table | Still shown, with a header note `كما كانت وقت الاعتماد`. |
| Warnings panel | Still shown (they were acknowledged). Header becomes `التحذيرات التي تم تأكيدها (n)`. |
| Blocking panel | Never shown (approval clears blocking reasons). |
| Counts strip | Adds `الرسائل المُنشأة` only if the API exposes a count (§14 G3); otherwise unchanged. |
| Facts | `آخر معاينة` hidden; `اعتُمدت` + hash populated. |
| Edit / submit / approve | Absent. |
| No-send wording | Full density only (§1.4). |

### 5.3 Snapshot hash display

`SnapshotHash`:

- Label `بصمة النسخة` + one line of explanation: `تثبت أن هذه النسخة لم تتغيّر. تُحسب من بيانات الحملة والمستلمين عند الاعتماد.`
- Value: 64 hex chars, `dir="ltr"`, `lang="en"`, `font-mono`, 11px, `break-all`, `--fd-ink-muted`, inside a `--fd-surface-alt` box with `p-3`, radius 10.
- A `نسخ` button (`h-11`, 44px, `Copy` icon + text) with `aria-label="نسخ بصمة النسخة"`. On success, a `role="status"` line replaces the helper text for 4 seconds: `تم نسخ البصمة.` Never a toast, never `alert()`.
- Copy uses `navigator.clipboard.writeText` with a `document.execCommand` fallback; on failure: `تعذر النسخ. حدّد النص وانسخه يدويًا.` and the value becomes `user-select: all`.
- In the banner, the hash is abbreviated for scanning (`a3f9c1…7b21`) **with** the full value available below in the facts card and via the copy button. Truncation is never the only representation.
- Never colour, score, or verify the hash in the UI beyond stating what it is. No "valid/invalid" badge — the UI has nothing to compare against.

### 5.4 Approved action bar

- Start: `معتمدة · نسخة مقفلة` + `الرسائل: بانتظار الإرسال` **only if** a real pending count exists; otherwise no message claim at all.
- End: `العودة إلى الحملات` (secondary) and, for `campaigns.approve` holders, `إلغاء الحملة` (danger text, 8px apart).
- **No send, no resend, no "إرسال الآن", no disabled send button with a "قريبًا" tooltip.** A disabled send button is still a promise; the M3 posture is that the capability does not exist on this screen.
- Cancelling an approved campaign opens the danger dialog with the additional consequence line `ستُلغى الرسائل المعلّقة المرتبطة بهذه الحملة. ستبقى نسخة المستلمين محفوظة.` (§8.3).

### 5.5 Immutability, explained in the UI

Three short, permanent statements — no modal, no guided tour:

1. Snapshot card: `لا يمكن تعديل هذه الحملة أو مستلميها.`
2. Recipients card header: `بيانات مثبّتة وقت الاعتماد.`
3. Facts card source row: `تعديلات الكشف بعد الاعتماد لا تغيّر هذه النسخة.`

These answer the three questions an auditor actually asks, in the places they ask them.

---

## 6. Screen 5 — Cancelled campaign

```
┌──────────────────────────────────────────────────────────────────────────┐
│ الحملات / تذكير رسوم الفصل الأول                                          │
│ تذكير رسوم الفصل الأول  ●ملغاة                                            │
│ أُلغيت في 2026-11-03 21:40                                                │
├──────────────────────────────────────────────────────────────────────────┤
│ أُلغيت هذه الحملة                                                        │
│ السبب: تغيير فترة التحصيل.                                               │
│ لم تُرسل أي رسالة. النسخة المحفوظة للعرض فقط.                            │
│                                                    [العودة إلى الحملات]  │
└──────────────────────────────────────────────────────────────────────────┘
```

- Banner tone: `--fd-surface-alt` with `--fd-line` border and a `Ban` icon in `--fd-ink-muted`. **Not red** — a deliberate cancellation is not a system failure.
- Body order: reason (verbatim, quoted, `«...»`), `لم تُرسل أي رسالة.`, then the read-only statement.
- If `reason` is absent: omit the row entirely, no placeholder.
- If the campaign was cancelled **after** approval, add one line: `أُلغيت الرسائل المعلّقة. بقيت نسخة المستلمين محفوظة.` and keep the snapshot card (green, muted) with its hash — the frozen record survives cancellation.
- If cancelled from draft/awaiting, there is no hash and no snapshot card.
- Data below: counts, totals, facts, recipients, exclusions — all read-only, all from the stored data. No pager disabled states that suggest an action; the tables just render.
- **No actions** except `العودة إلى الحملات`. No re-open, no duplicate, no delete. (Duplicating from a cancelled campaign would need a new API; it does not exist in M3.)

---

## 7. Screen 6 — Template management (`/settings/templates`)

### 7.1 Structure

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ الإعدادات / قوالب الرسائل                                                     │
│ قوالب الرسائل                                              [+ قالب جديد]      │
│ نصوص رسائل التذكير وإصداراتها. كل حفظ ينشئ إصدارًا جديدًا.                    │
│ ⓘ الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة.                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ تذكير الرسوم الدراسية                                    النشط: الإصدار 1     │
│ ┌──────────────────────────────────────────────────────────────────────────┐ │
│ │ الإصدار  الحالة  متغيرات غير معروفة  أنشأه   تاريخ الإنشاء   إجراءات      │ │
│ │ 1        ●نشط    —                   admin   2026-11-03      عرض · إصدار  │ │
│ └──────────────────────────────────────────────────────────────────────────┘ │
│ تذكير أولياء الأمور                                      النشط: —            │
│ …                                                                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

- Group by `name`; within a group, versions descending. This mirrors the API ordering (`name`, then `version desc`) and keeps "which version is live" obvious.
- One card per template name. Card header: name (15px/600), `النشط: الإصدار {n}` (or `لا يوجد إصدار نشط` in amber text), and for admins a `إصدار جديد` button on the header's end.
- The active row gets a `--fd-green-soft` row tint **and** the `نشط` pill — never tint alone.

### 7.2 Version table columns

| # | Column | Content | @1440 |
|---|---|---|---|
| 1 | الإصدار | `الإصدار {n}` (`<th scope="row">`), tabular | 110 |
| 2 | الحالة | `نشط` green / `غير نشط` neutral pill | 110 |
| 3 | متغيرات غير معروفة | `—` or amber text `{{x}}، {{y}}` (names, not a count) | 220 |
| 4 | أنشأه | `created_by_name` | 140 |
| 5 | تاريخ الإنشاء | `YYYY-MM-DD HH:mm` | 150 |
| 6 | إجراءات | `عرض` · `تفعيل` (non-active, admin) · `إصدار جديد` | 220 |

- Unknown variables are shown **by name**, because the user has to remove them one by one. A count would force a click.
- `body_preview` appears as a muted second line under the version cell? No — it belongs in the detail view. The list stays scannable.
- `تفعيل` on an active version is absent, not disabled.
- Staff: `إجراءات` column shows only `عرض`; header buttons absent; a read-only banner directly under the PageHeader: `العرض فقط — إدارة القوالب متاحة لمدير النظام.` (matches the settings page's staff treatment).

### 7.3 Version detail (`/settings/templates/[id]`)

Read-only, `max-w-[880px]`:

- Header: `{name} · الإصدار {n}` + `نشط` pill.
- Meta `<dl>`: القناة (`SMS`), اللغة (`العربية`), أنشأه, تاريخ الإنشاء.
- Body box: `--fd-surface-alt`, `p-4`, 15px/1.9, `dir="rtl"`, `white-space: pre-wrap`, variables as chips.
- Unknown variables panel (amber) if any, with `أزل هذه المتغيرات من النص قبل الاعتماد.`
- Actions (admin): `إصدار جديد من هذا النص` → `/settings/templates/new?from={id}` (primary), `تفعيل هذا الإصدار` (secondary, non-active only), `العودة إلى القوالب`.
- Staff: no actions beyond back.

### 7.4 Editor (`/settings/templates/new`)

Two columns at `≥1280` (`grid-cols-[1.4fr_0.9fr]`, 20px gap); stacked above the preview at `≤1024`.

**Left column**

```
اسم القالب
[ تذكير الرسوم الدراسية                                    ]   (locked when ?from=)
يُنشئ الحفظ إصدارًا جديدًا من نفس الاسم.

نص الرسالة
┌───────────────────────────────────────────────────────────────┐
│ [{{guardian_name}}] [{{amount}}] [{{currency}}] [{{student_list}}] … │ ← variable chips
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ عزيزنا {{guardian_name}}،                              │ │
│ │ نذكّركم بأن المبلغ المتبقي {{amount}} {{currency}} …    │ │
│ └───────────────────────────────────────────────────────────┘ │
│ عدد الأحرف: 214                                               │
└───────────────────────────────────────────────────────────────┘
```

- Name: `fd-input h-11`. When opened with `?from={id}`, the name is **read-only text with an explanation** (`الاسم مثبّت لإنشاء إصدار من نفس القالب.`). This prevents a typo from silently creating a parallel template family, which the API would treat as a new template at version 1 (§14 G4).
- Body: native `<textarea class="fd-input min-h-[320px] py-3 text-[15px] leading-[1.9]" dir="rtl" lang="ar" spellCheck={false}>`. Plain text only — the contract renders plain text, so no rich editor, no Markdown, no HTML hints.
- Character count: `عدد الأحرف: {n}` (Latin digits, tabular). **No SMS-segment count and no cost estimate** — segment math depends on encoding and concatenation headers, and cost implies sending exists.
- Save label: `حفظ كإصدار جديد` (never `حفظ` alone — it changes the active version).

**Right column — live checks**

| Check | State | Copy |
|---|---|---|
| الاسم | pass/fail | `الاسم جاهز` / `أدخل اسم القالب` |
| النص | pass/fail | `النص جاهز` / `أدخل نص الرسالة` |
| المتغيرات | pass/warn | `كل المتغيرات معروفة` / `متغيرات غير معروفة: {{x}}` |
| الإصدار التالي | info | `سيُنشأ الإصدار {n+1} ويصبح النشط.` (only when the name matches an existing template) |

Below the checks, the allowed-variable reference (§7.5) and a preview box: the body rendered with variable chips, no interpolation, note `هكذا يظهر النص قبل استبدال المتغيرات.`

### 7.5 Allowed variables

Source: `GET /templates/variables`. Render as an anchored reference list, not a wall of tags:

| Variable chip | Label | Fallback |
|---|---|---|
| `{{guardian_name}}` | اسم ولي الأمر | `مطلوب` |
| `{{student_list}}` | أسماء الطلاب | `أبنائكم` |
| `{{amount}}` | المبلغ المتبقي | `مطلوب` |
| `{{currency}}` | العملة | `مطلوب` |
| `{{fee_period}}` | الفصل الدراسي | `الفصل الحالي` |
| `{{school_name}}` | اسم المدرسة | `المدرسة` |
| `{{student_name}}` | اسم الطالب | `الطالب` |
| `{{school_contact}}` | وسيلة التواصل | `إدارة المدرسة` |

- Insertion: chip is a `<button type="button">` with `min-h-[44px]`, `aria-label="إدراج متغير اسم ولي الأمر"`. Insertion happens at the caret (`selectionStart/End`), replacing any selection, inserting `{{name}}` **with** the double braces and no spaces. After insert, focus returns to the textarea and the caret moves after the token.
- Announce via a `role="status"` line under the palette: `أُضيف المتغير {{guardian_name}}.` (polite, replaced on each insert).
- If the variables request fails, the palette is replaced by `تعذر تحميل المتغيرات. يمكنك كتابة النص دون إدراج.` — the editor still works. Insertion must never require the palette.
- Variables are inserted literally; the editor never wraps them in extra punctuation, because Arabic sentence punctuation belongs to the author.

### 7.6 Save, warnings, and activation

- Save → `POST /templates` with `{name, language:"ar", channel:"sms", template_body}`.
  - Success: `role="status"` banner on the list page `حُفظ الإصدار {n} وأصبح نشطًا.` + focus move; navigate to `/settings/templates`.
  - Unknown variables: **allowed**. Save proceeds. After saving, the version row shows the amber variable names and the list shows an amber note `إصدارات بها متغيرات غير معروفة لا يمكن استخدامها في حملة معتمدة.`
  - Empty name/body: rejected client-side **and** surfaced verbatim from the API if it still fails.
  - 403: `لا تملك صلاحية إدارة القوالب.`
- Activation (`تفعيل`):
  - `Dialog` (not `ConfirmDialog` — reversible), title `تفعيل الإصدار {n}`, body:
    `ستستخدم الحملات الجديدة هذا الإصدار من «{name}». الحملات المعتمدة لا تتغير.`
  - Buttons: `إلغاء` (autofocus, secondary) / `تفعيل` (brand primary, busy `جارٍ التفعيل…`).
  - Non-active version only. Activating a version with unknown variables is allowed but shows the amber note inside the dialog: `هذا الإصدار يحتوي متغيرات غير معروفة، ولن تُعتمد الحملات التي تستخدمه.`
  - Success: `role="status"` `فُعِّل الإصدار {n}.` and the row/group header refresh.
- No delete, no deactivate-to-nothing, no version renumbering. The API has none; do not simulate it.

### 7.7 Staff read-only behaviour

| Element | Staff |
|---|---|
| Sidebar Settings | visible (already) |
| `/settings` → `قوالب الرسائل` link | visible |
| List | visible, no `قالب جديد`, no `إصدار جديد`, no `تفعيل` |
| Version detail | visible, no actions except back |
| Editor route (direct URL) | `EmptyState` `إدارة القوالب متاحة لمدير النظام.` + `العرض فقط` link back to the list. Do not render a disabled editor. |
| Unknown variables | visible (staff need to know why a campaign is blocked) |

---

## 8. Dialogs

All use the existing `Dialog` (native `<dialog>`, focus restoration, Esc guarded while busy, 44px close). `ConfirmDialog` is used only for cancellation.

### 8.1 Submit for approval

`Dialog`, brand primary. Title `إرسال الحملة للاعتماد`.

```
سيتم إعادة حساب المستلمين من الكشف المؤكد قبل الإرسال للاعتماد.

المستلمون: 4                      SYP 2,100,000.00
مستثناة: 2                        USD 400.00
التحذيرات: 2

• رقم هاتف مشترك بين أكثر من ولي أمر. — العدد: 2

لن تُرسل أي رسالة. ستصبح الحملة بانتظار اعتماد مدير النظام.

[إلغاء]                                    [إرسال للاعتماد]
```

- One currency line per currency, right edge aligned, tabular.
- `إلغاء` is `data-autofocus` (safe action).
- Busy: `جارٍ الإرسال للاعتماد…`; the dialog stays open until the response lands.
- `422 CAMPAIGN_BLOCKED`: `role="alert"` inside the dialog, `تعذر الإرسال للاعتماد.` + the blocking reasons listed (reuse `BlockingReasons` compact variant). Do not close.
- `409` revision conflict: `تغيّرت الحملة منذ فتحها. حُدِّثت الصفحة؛ راجع البيانات ثم أعد المحاولة.` + `تحديث` button that refetches and closes.
- Success: close, refetch, `role="status"` banner `أُرسلت الحملة للاعتماد. لم تُرسل أي رسالة.` Focus to the banner.

### 8.2 Approve (the critical dialog)

`Dialog`, brand primary (not the red `ConfirmDialog`: approval is the intended action, not a destructive mistake). Title `اعتماد الحملة`.

```
سيتم تثبيت نسخة غير قابلة للتعديل من هذه الحملة.
لا يمكن تعديل المستلمين أو المبالغ بعد الاعتماد.

المستلمون: 4                      SYP 2,100,000.00
مستثناة: 2                        USD 400.00

التحذيرات (2)
• رقم هاتف مشترك بين أكثر من ولي أمر. — العدد: 2
• …

ⓘ لن تُرسل أي رسالة. سيُنشأ لكل مستلم سجل رسالة بانتظار الإرسال،
   ولا يوجد إرسال إلى المزوّد في هذه المرحلة.

[ ] راجعت التحذيرات وأفهم أن الاعتماد نهائي ولا يمكن تعديل الحملة بعده.

[إلغاء]                              [اعتماد وتثبيت الحملة]
```

Rules:

- The **only** acknowledgment checkbox in the product. It lives here, at the point of commitment, not in the sticky bar — two acknowledgments for one action is ritual, not consent.
- Warnings block **only** this button: disabled until checked, with a visible reason directly above the buttons `أكّد أنك راجعت التحذيرات للاعتماد.` (`aria-describedby` on the button). When `warnings.length === 0`, the checkbox and the reason are **absent** — no empty ritual.
- Checkbox: real `<input type="checkbox" class="h-5 w-5">` inside a `<label class="min-h-[44px] flex items-start gap-3">`; label text clickable; 20px box.
- Primary label is specific: `اعتماد وتثبيت الحملة`; busy `جارٍ الاعتماد…`.
- `إلغاء` autofocus and secondary.
- `422 WARNINGS_UNACKNOWLEDGED` (only possible if the client bug-sends false): `role="alert"` `أكّد أنك راجعت التحذيرات قبل الاعتماد.` and re-enable.
- `422 CAMPAIGN_BLOCKED`: `تعذر الاعتماد: {reason}.` + list; dialog stays open.
- Idempotent replay (already approved): the API returns the detail without duplicates — the UI closes the dialog, refetches, and shows `الحملة معتمدة مسبقًا.` as `role="status"`, never an error.
- Success: dialog closes; banner `تم اعتماد الحملة وتثبيت نسختها. لم تُرسل أي رسالة.` with focus; the snapshot card renders with the hash; `التحذيرات` header becomes `التحذيرات التي تم تأكيدها`.

**Never** in this dialog: a send checkbox, a "send after approval" option, a schedule field, a provider selector, a cost estimate.

### 8.3 Cancel

`ConfirmDialog` (red), because cancellation is destructive and irreversible for the record.

Title `إلغاء الحملة`.

Body:

```
سيتوقف العمل على هذه الحملة نهائيًا وتبقى في السجل بحالة «ملغاة».
لم تُرسل أي رسالة.
```

Plus, for `approved`: `ستُلغى الرسائل المعلّقة المرتبطة بالحملة. ستبقى نسخة المستلمين محفوظة.`

Reason field below the `ConfirmDialog`'s description (extend `ConfirmDialog` with a `children` slot, or compose `Dialog` + a red primary — prefer extending with `children` so the safe-action autofocus, busy guard, and error block stay identical):

- Label `سبب الإلغاء`, `<textarea class="fd-input min-h-[88px]">`, hint `يُسجَّل في سجل العمليات.`
- **Required for approved campaigns** (client-side): empty → `اذكر سبب إلغاء حملة معتمدة.` API allows omission; the UI is stricter because cancelling a frozen record is the heaviest action in M3. Flagged in §14 G6.
- Optional for draft/awaiting, with hint `اختياري، لكنه يساعد في سجل العمليات.`
- Confirm label `إلغاء الحملة`; busy `جارٍ الإلغاء…`. The red button is the destructive action, and the reason is captured before it fires.
- Success: close, refetch, `role="status"` `أُلغيت الحملة.` Focus to the cancellation banner.
- `409`: `تغيّرت الحملة منذ فتحها. حُدِّثت الصفحة.`

### 8.4 Per-message preview

`Dialog`, `w-[min(40rem,92vw)]`, title `معاينة الرسالة`, description `{guardian_name} · {phone in <bdi dir="ltr">}`.

```
┌──────────────────────────────────────────────────────────┐
│ عزيزنا ولي أمر 001،                                       │
│ نذكّركم بأن المبلغ المتبقي 600,000.00 SYP عن الفصل الأول. │
│ …                                                        │
└──────────────────────────────────────────────────────────┘    ← pre-wrap, 15px/1.9

المبلغ: 600,000.00 SYP      الفصول: الفصل الأول
الطلاب: طالب 001            الأرصدة: 2
عدد الأحرف: 214

⚠ تحذيرات على هذا المستلم
• رقم هاتف مشترك بين أكثر من ولي أمر.

[إغلاق]                              [السابق] [التالي]   (المستلم 2 من 4)
```

- Message text: `white-space: pre-wrap`, `dir="rtl"`, real rendered text from `recipient.message` — never re-rendered client-side. Currency and numbers inside it stay LTR-isolated by the server's formatting; if an amount appears wrapped oddly, wrap only the digits, never the whole sentence.
- Footer meta uses a `<dl>`; Latin values in `<bdi>`.
- `السابق`/`التالي` are optional but specified: they move within the **current filtered** list, announce via `role="status"` `المستلم 3 من 4`, and are disabled at the ends (never wrap). Labels carry the guardian name via `aria-label`.
- `إغلاق` is `data-autofocus`.
- No "إرسال اختبار", no copy-to-clipboard of the phone as a primary action (phone copy is a 44px icon button `aria-label="نسخ رقم الهاتف"` — permitted, useful, harmless).

### 8.5 Activate version

§7.6. Brand primary, reversible, `إلغاء` autofocus.

---

## 9. RTL, tables, numbers, currency

### 9.1 RTL

| Rule | Implementation |
|---|---|
| Direction | `html dir="rtl" lang="ar"`; only LTR-isolated values get a local `dir` |
| Column order | First column at the **right**; actions far left |
| Spacing | Logical properties only (`ps/pe/ms/me/border-s/start-0`) |
| Row markers | `border-inline-start` for warning rows |
| Breadcrumb | `ChevronLeft` with `rtl:rotate-180`; never a mirrored arrow glyph |
| Icons | Never mirrored: lock, info, send, ban, copy, users, check, alert. The only mirrorable glyph is the breadcrumb chevron |
| Arabic name + Latin digits | `<bdi dir="auto">` on campaign names; numeric runs in `<bdi dir="ltr">` |
| Phone numbers | `<bdi dir="ltr">` + `whitespace-nowrap`, always |
| Hash | `<bdi dir="ltr" lang="en">` + `break-all` |
| Amounts inside message text | Server-rendered; do not re-order or re-wrap client-side |
| Dialogs | Centred, inherit RTL, filenames/phones in `<bdi>` |

### 9.2 Tables

- `.fd-table` (13px), two-line rows `min-h-[64px]`.
- `<caption class="sr-only">` on every table; `scope="col"` everywhere; `scope="row"` on the identifying cell.
- Header cells 11–12px, `--fd-ink-muted`, `font-medium`, `whitespace-nowrap`, tinted `--fd-surface-alt`.
- Numeric cells `font-variant-numeric: tabular-nums`, `<bdi dir="ltr">`, aligned to the reading-start edge.
- Dates/codes/phones `whitespace-nowrap`.
- Border 1px horizontal only; no vertical grid; no zebra.
- Empty body: one `<tr><td colSpan={n}>` containing the shared `EmptyState`.

### 9.3 Numbers

- Latin digits everywhere (`ar-SY-u-nu-latn`), matching M1/M2.
- Counts: `tabular-nums`, separators above 9,999.
- Money: always two decimals from the API string, grouped integer part, fraction verbatim. **Never `Number()`, `parseFloat`, or arithmetic on money.**
- Totals only from `totals_by_currency`. The client never sums the visible rows.
- No percentages, no deltas, no charts, no "متوسط التذكير" invented metrics.

### 9.4 Currency

- One line per currency, alphabetical, ISO code first: `SYP 2,100,000.00`, whole string in `<bdi dir="ltr">`.
- No conversion, no combined figure, no symbol fallback. If the school symbol is missing, the ISO code alone is sufficient and always present.
- Zero excluded amounts still show currency when shown at all; negative never occurs in campaigns (negative balances are excluded with a reason).

### 9.5 Target sizes

- Every button, tab, chip, toggle, row action, pager, dialog close: **≥44×44**. Visual height may be 40px only with a padded hit area reaching 44; campaign controls use `h-11` (44px) directly.
- Checkbox: 20px box inside a `min-h-[44px]` label.
- Variable chips: `min-h-[44px]`, ≥8px apart.
- Focus outline: 2px `--fd-brand`, `outline-offset: 2px`; inside table cells `-2px`; never clipped by `overflow: hidden` on a parent.

---

## 10. Responsive behaviour

### 10.1 1440 (primary target)

- Shell: 240px sidebar, ~1152px usable.
- List: 8 columns as specified, no horizontal scroll, summary line one row.
- Builder: 880px column; radio cards full width; sticky bar one row.
- Detail: counts 3-up; totals + facts 2 columns (`1.15fr / 0.85fr`); recipients 8 columns (~1100px); excluded 5 columns; sticky bar one row.
- Templates: grouped cards full width; version table 6 columns.
- This is the acceptance width for the visual comparison against the approved dashboard.

### 10.2 1024

- Sidebar 76px, content ~916px.
- List: drop `المصدر` and `أنشأها` as columns; filenames and creator move to the campaign cell's second line (`sample-01.xlsx · أ. خالد · 2026-11-03`). Keep `المستلمون`, `الإجماليات`, `الحالة`, `اعتمادها`, `إجراء`. Tabs wrap to a second line rather than scroll.
- Builder: 760px column, unchanged structure.
- Detail: counts 3-up stays; totals and facts stack (money first); recipients drop `الطلاب` and `الفصول` into an expandable row (`<details>`-style `<tr>` with a `تفاصيل المستلم` toggle, 44px); currency moves inline into the amount cell; sticky bar becomes two rows.
- Excluded table: drop `الهاتف` into the guardian cell's second line.
- Templates: version table drops `أنشأه`; actions keep `عرض` and `تفعيل`.

### 10.3 768

- Content ~660px with 16px padding.
- List: 4 columns — `الحملة` (with status pill stacked under the name), `الإجماليات`, `الحالة`, `إجراء`. `المستلمون` and dates move into an always-available expanded row (`تفاصيل الحملة`) so nothing is lost. Summary line wraps to two lines; beyond that, ellipsis.
- Builder: sticky bar full width, two rows, primary full width; radio cards 72px; body preview 160px max-height.
- Detail: recipients 5 columns — `ولي الأمر`, `المبلغ` (with currency), `الحالة`, `إجراء`; hidden fields in the expanded row. Counts 2+1. Totals card full width. Warnings/blocking panels full width. Sticky bar: counts line + full-width primary + secondary text buttons on a third line.
- Dialogs: `w-[min(36rem,90vw)]`; money lines wrap, never scroll horizontally; approve checkbox full width.
- Templates: version table becomes version cards (version, status, variables, actions) with `<dl>` semantics preserved.

### 10.4 Below 768 (not a target, must not break)

- No page-level horizontal scroll (1.4.10).
- Table columns are dropped, never font-shrunk below 13px.
- Sticky bar keeps `padding-bottom: max(16px, env(safe-area-inset-bottom))`.
- Known shell limits at 375 are M1 debt; campaign screens must not add new ones.

### 10.5 Never changes across widths

- Money is never truncated, abbreviated, or combined across currencies.
- The status pill is never hidden.
- The no-send notice is never collapsed into a tooltip.
- Blocking reasons and exclusion reasons are never hidden.
- Submit, approve, and cancel are never inside a menu.
- Snapshot hash is always reachable in full.

---

## 11. Arabic copy deck

Tone: plain, specific, second person, no system jargon, no English codes in primary text. Every error names the next action. API `message_ar` is preferred verbatim; a client hint is added only when the API text does not name a next step.

### 11.1 Campaign statuses

| Value | Pill | List second line | Count label |
|---|---|---|---|
| `draft` | مسودة | `آخر معاينة {time}` | المسودات |
| `awaiting_approval` | بانتظار الاعتماد | `أُرسلت للاعتماد {time}` | بانتظار الاعتماد |
| `approved` | معتمدة | `اعتُمدت {time}` | المعتمدة |
| `cancelled` | ملغاة | `أُلغيت {time}` | الملغاة |

Tab labels: `الكل` · `مسودة` · `بانتظار الاعتماد` · `معتمدة` · `ملغاة`.

Tones: neutral / amber / green / neutral. Approval is green because it is a completed governance step, not because anything was delivered.

### 11.2 Counts and strips

Label-first, so number agreement can never be wrong:

`المستلمون: 4` · `مستثناة: 2` · `التحذيرات: 2` · `الرسائل المُنشأة: 4` · `الإجماليات: SYP 2,100,000.00`

Sentences where a counted noun is unavoidable: `عرض 1–20 من 47 حملة` (via `formatCountAr`), `4 مستلمين`, `سجلان مستثنيان`, `لا مستلمين مؤهلين`.

Forbidden: `2 مستلم مستثنى`, `4 رسالة`, `1 حملات`.

### 11.3 Exclusion reasons

Primary text is the API `message_ar`, verbatim. The client adds a short label and a truthful next step:

| Code | Label | Next step |
|---|---|---|
| `ZERO_BALANCE` | الرصيد صفر | `لا يوجد مبلغ متبقٍّ على هذا السجل.` |
| `NEGATIVE_BALANCE` | الرصيد سالب | `يحتاج السجل إلى مراجعة مالية قبل التذكير.` |
| `MISSING_CURRENCY` | العملة غير محددة | `صحّح العملة في كشف جديد مؤكد ثم أنشئ حملة.` |
| `MISSING_PHONE` | لا يوجد رقم هاتف | `أضف رقم ولي الأمر في كشف جديد مؤكد ثم أنشئ حملة.` |
| `INVALID_PHONE` | رقم الهاتف غير صالح | `صحّح الرقم بصيغة دولية تبدأ بـ +963 في كشف جديد مؤكد.` |
| `GUARDIAN_INACTIVE` | حساب ولي الأمر غير نشط | `أعد تفعيل الحساب قبل إنشاء حملة جديدة.` |

Panel header: `المستثناة ({n})`. Panel description: `هذه السجلات لم تدخل الحملة. الأسباب من بيانات الكشف المؤكد.`

### 11.4 Warnings and acknowledgment

| Item | Copy |
|---|---|
| Warning panel header | `التحذيرات ({n})` |
| Per-warning count | `العدد: {n}` |
| Warning footer (approver) | `التحذيرات لا تمنع الاعتماد، لكن يجب تأكيدها عند الاعتماد.` |
| Warning footer (staff) | `سيطّلع مدير النظام على هذه التحذيرات قبل الاعتماد.` |
| Shared phone (API) | `رقم هاتف مشترك بين أكثر من ولي أمر.` (verbatim example) |
| Acknowledgment checkbox | `راجعت التحذيرات وأفهم أن الاعتماد نهائي ولا يمكن تعديل الحملة بعده.` |
| Acknowledgment gate reason | `أكّد أنك راجعت التحذيرات للاعتماد.` |

### 11.5 Confirmation dialogs

**Submit**

| Slot | Copy |
|---|---|
| Title | `إرسال الحملة للاعتماد` |
| Body | `سيتم إعادة حساب المستلمين من الكشف المؤكد قبل الإرسال للاعتماد.` |
| Consequence | `لن تُرسل أي رسالة. ستصبح الحملة بانتظار اعتماد مدير النظام.` |
| Primary | `إرسال للاعتماد` / `جارٍ الإرسال للاعتماد…` |
| Blocked | `تعذر الإرسال للاعتماد.` + reasons |

**Approve**

| Slot | Copy |
|---|---|
| Title | `اعتماد الحملة` |
| Body | `سيتم تثبيت نسخة غير قابلة للتعديل من هذه الحملة. لا يمكن تعديل المستلمين أو المبالغ بعد الاعتماد.` |
| No-send line | `لن تُرسل أي رسالة. سيُنشأ لكل مستلم سجل رسالة بانتظار الإرسال، ولا يوجد إرسال إلى المزوّد في هذه المرحلة.` |
| Primary | `اعتماد وتثبيت الحملة` / `جارٍ الاعتماد…` |
| Success | `تم اعتماد الحملة وتثبيت نسختها. لم تُرسل أي رسالة.` |
| Already approved | `الحملة معتمدة مسبقًا.` |
| Unacknowledged | `أكّد أنك راجعت التحذيرات قبل الاعتماد.` |

**Cancel**

| Slot | Copy |
|---|---|
| Title | `إلغاء الحملة` |
| Body | `سيتوقف العمل على هذه الحملة نهائيًا وتبقى في السجل بحالة «ملغاة». لم تُرسل أي رسالة.` |
| Approved addendum | `ستُلغى الرسائل المعلّقة المرتبطة بالحملة. ستبقى نسخة المستلمين محفوظة.` |
| Reason label | `سبب الإلغاء` |
| Reason hint (draft) | `اختياري، لكنه يساعد في سجل العمليات.` |
| Reason error (approved) | `اذكر سبب إلغاء حملة معتمدة.` |
| Confirm | `إلغاء الحملة` / `جارٍ الإلغاء…` |
| Success | `أُلغيت الحملة.` |

### 11.6 Template editor

| Slot | Copy |
|---|---|
| H1 | `قوالب الرسائل` |
| Subtitle | `نصوص رسائل التذكير وإصداراتها. كل حفظ ينشئ إصدارًا جديدًا.` |
| New template CTA | `قالب جديد` |
| New version CTA | `إصدار جديد` |
| Group header active | `النشط: الإصدار {n}` |
| Group header none | `لا يوجد إصدار نشط` (amber) |
| Version label | `الإصدار {n}` |
| Active pill | `نشط` / `غير نشط` |
| Unknown variables column | `متغيرات غير معروفة` |
| Unknown variables note (list) | `إصدارات بها متغيرات غير معروفة لا يمكن استخدامها في حملة معتمدة.` |
| Editor name label | `اسم القالب` |
| Editor name locked hint | `الاسم مثبّت لإنشاء إصدار من نفس القالب.` |
| Editor body label | `نص الرسالة` |
| Editor body hint | `نص عادي فقط. لا تُستخدم وسوم HTML.` |
| Variable palette title | `المتغيرات المسموحة` |
| Variable fallback | `البديل: {fallback}` / `مطلوب` |
| Insert announcement | `أُضيف المتغير {{guardian_name}}.` |
| Character count | `عدد الأحرف: {n}` |
| Next version info | `سيُنشأ الإصدار {n+1} ويصبح النشط.` |
| Save | `حفظ كإصدار جديد` / `جارٍ الحفظ…` |
| Save success | `حُفظ الإصدار {n} وأصبح نشطًا.` |
| Activate title | `تفعيل الإصدار {n}` |
| Activate body | `ستستخدم الحملات الجديدة هذا الإصدار من «{name}». الحملات المعتمدة لا تتغير.` |
| Activate primary | `تفعيل` / `جارٍ التفعيل…` |
| Activate success | `فُعِّل الإصدار {n}.` |
| Staff banner | `العرض فقط — إدارة القوالب متاحة لمدير النظام.` |
| Staff editor route | `إدارة القوالب متاحة لمدير النظام.` |

### 11.7 Validation and error messages

| Code / situation | Message | Next step |
|---|---|---|
| `IMPORT_NOT_CONFIRMED` | `هذا الكشف غير مؤكد. لا يمكن بناء حملة من كشف غير مؤكد.` | `عرض الكشوف` |
| `NO_ACTIVE_TEMPLATE` | `لا يوجد قالب رسائل نشط.` | `اطلب من مدير النظام تفعيل قالب ثم أعد المحاولة.` |
| `TEMPLATE_NOT_FOUND` | `القالب المحدد غير موجود.` | `اختر قالبًا آخر.` |
| `TEMPLATE_INACTIVE` | `القالب المستخدم لم يعد نشطًا.` | admin: `تفعيل إصدار`; staff: `تواصل مع مدير النظام.` |
| `UNRESOLVED_VARIABLES` | `القالب يحتوي متغيرات غير معروفة.` | names + `فتح القالب` |
| `NO_ELIGIBLE_RECIPIENTS` | `لا يوجد ولي أمر مؤهل في هذا الكشف.` | `عرض المستثناة` |
| `CAMPAIGN_BLOCKED` | `تعذر إتمام العملية: الحملة غير جاهزة للاعتماد.` | reasons list |
| `WARNINGS_UNACKNOWLEDGED` | `أكّد أنك راجعت التحذيرات قبل الاعتماد.` | checkbox |
| Empty campaign name | `أدخل اسمًا للحملة.` | field focus |
| Empty template name | `أدخل اسم القالب.` | field focus |
| Empty template body | `أدخل نص الرسالة.` | field focus |
| Unknown variable (editor) | `متغير غير معروف: {{x}}.` | `يمكن الحفظ، لكن الحملات التي تستخدم هذا القالب لن تُعتمد.` |
| Revision conflict (409) | `تغيّرت الحملة منذ فتحها. حُدِّثت الصفحة؛ راجع البيانات ثم أعد المحاولة.` | `تحديث` |
| 403 | `لا تملك صلاحية {عرض/إنشاء/اعتماد/إلغاء} هذه الحملة.` | `العودة إلى الحملات` |
| 401 | `انتهت الجلسة. سجّل الدخول مرة أخرى.` | login |
| Network | `تعذر الاتصال بالخادم. تحقق من الشبكة وأعد المحاولة.` | retry |
| Generic | `تعذر تنفيذ الطلب. أعد المحاولة.` (only when no `message_ar`) | — |

Rules: never show a raw `code` as primary text (10px muted `<bdi>` only, inside details); never say `خطأ في الخادم` for validation; never say `تم` before a response lands.

### 11.8 Empty states

| Screen | Title | Description | Action |
|---|---|---|---|
| List — none | `لا توجد حملات بعد` | `أنشئ حملة من كشف أقساط مؤكد لمعاينة المستلمين والمبالغ قبل الاعتماد.` | `حملة جديدة` (+ `عرض الكشوف`) |
| List — filtered | `لا توجد حملات بهذه الحالة` | `جرّب حالة أخرى.` | `عرض كل الحملات` |
| Builder — no confirmed import | `لا يوجد كشف مؤكد` | `تُبنى الحملات من كشوف مؤكدة فقط. أكّد كشفًا أولًا.` | `عرض الكشوف` |
| Builder — no active template | `لا يوجد قالب رسائل نشط` | `تحتاج الحملة إلى قالب نشط. اطلب من مدير النظام تفعيل قالب.` | `فتح القوالب` (admin) |
| Recipients — none | `لا يوجد مستلم مؤهل` | `كل السجلات في هذا الكشف استُثنيت. راجع أسباب الاستثناء أدناه.` | `عرض المستثناة` |
| Excluded — none | (do not render the panel) | — | — |
| Warnings — none | (do not render the panel) | — | — |
| Templates — none | `لا توجد قوالب بعد` | `أنشئ قالب رسالة ليستخدمه إعداد الحملات.` | `قالب جديد` (admin) |
| Templates — staff empty | `لا توجد قوالب بعد` | `لم يُنشئ مدير النظام أي قالب رسائل بعد.` | — |
| 404 campaign | `لم نجد هذه الحملة` | `قد يكون الرابط قديمًا أو أن الحملة غير متاحة لحسابك.` | `العودة إلى الحملات` |

### 11.9 Words to avoid

| Don't | Use |
|---|---|
| `إرسال` as a campaign action | `اعتماد` / `إرسال للاعتماد` (the only permitted "إرسال" is sending *for approval*) |
| `تم الإرسال` / `أُرسلت الرسائل` | never said in M3 |
| `جاهزة للإرسال` | `جاهزة للاعتماد` |
| `قيد الإرسال` / `تم التسليم` | never shown in M3 |
| `تكلفة` / `عدد الرسائل` (as a forecast) | not shown |
| `عملية` | `حملة` / `اعتماد` / `إلغاء` |
| `تم بنجاح` | say what happened |
| `موافق` / `نعم` | the verb: `اعتماد وتثبيت الحملة` |
| `لا توجد بيانات` | name what is missing + next step |
| `تعديل القالب` (when it creates a version) | `إصدار جديد` |

---

## 12. Accessibility checklist (WCAG 2.2 AA)

| SC | Requirement here | How |
|---|---|---|
| 1.1.1 | Non-text content | All icons `aria-hidden`; status always has text; the lock and info icons are decorative next to text |
| 1.3.1 | Info & relationships | Real tables with `<caption>`/`scope`; counts and facts are `<dl>`; acknowledgment is a `<label>`-bound checkbox; filter tabs are a `<nav>` of links |
| 1.3.2 | Meaningful sequence | Breadcrumb → title → no-send → counts → money → warnings → blocking → recipients → excluded → actions |
| 1.4.1 | Use of colour | Pill label + tone; warning rows have a border marker and text; blocking panel has a title; hash has no colour-coded validity |
| 1.4.3 | Contrast | All pairs from the token set (5.37–9.43); disabled buttons exempt but always paired with ≥4.5:1 reason text |
| 1.4.4 | Resize text | 200% zoom without loss; `min-height` rows, no fixed-height text containers |
| 1.4.10 | Reflow | 320px width, no page-level horizontal scroll; columns drop into expanded rows |
| 1.4.11 | Non-text contrast | Inputs `--fd-line-input` (3.11:1); checkbox border ≥3:1; chips/borders on `--fd-brand-soft` |
| 1.4.12 | Text spacing | 1.6 body / 1.9 message body; padding-based cells, no fixed heights |
| 1.4.13 | Content on hover/focus | Nothing is hover-only: reasons, hashes, and full IDs are always reachable |
| 2.1.1 | Keyboard | Tabs, cards, chips, tables, dialogs, hash copy all native and operable |
| 2.1.2 | No keyboard trap | Native `<dialog>`, Esc guarded only while busy |
| 2.2.1 | Timing | No auto-advance, no auto-redirect, no countdown |
| 2.4.1 | Bypass blocks | Existing skip link |
| 2.4.2 | Page titled | Per-route `metadata` (§1.1) |
| 2.4.3 | Focus order | See §12.1 |
| 2.4.6 | Headings & labels | One `<h1>` per page; card headers `<h2>`; dialog titles `<h2>`; no skipped levels |
| 2.4.7 | Focus visible | 2px brand outline, offset 2 (or −2 inside cells) |
| 2.5.3 | Label in name | `aria-label` contains the visible verb + campaign/guardian name |
| 2.5.8 | Target size | ≥44×44 (§9.5) |
| 3.1.1 / 3.1.2 | Language | `lang="ar"` on the page; `lang="en"` on the hash and ISO codes; `<bdi>` elsewhere |
| 3.2.2 | On input | Filtering navigates only on link activation; typing in the recipient search does not navigate |
| 3.3.1 | Error identification | Text errors in `role="alert"`, `aria-invalid` + `aria-describedby` on fields |
| 3.3.2 | Labels or instructions | Name hint, reason hint, acknowledgment explains consequences, variable palette shows fallbacks |
| 3.3.3 | Error suggestion | Every message names the fix (§11.7) |
| 3.3.4 | Error prevention | Confirmation before submit/approve/cancel; approval requires acknowledgment; cancel reason required for approved |
| 3.3.7 | Redundant entry | Builder keeps selections on failure; dialogs preserve input on error |
| 4.1.2 | Name, role, value | Native controls; `aria-current` on tabs; `aria-busy` on busy cards; no div-buttons |
| 4.1.3 | Status messages | `role="status"` for copy/save/approve/cancel successes; `role="alert"` for failures. Never both |
| 2.3.1 / 2.5.1 | Flashes / gestures | None |

### 12.1 Focus order

**List:** skip link → sidebar nav → topbar → breadcrumb (none) → `حملة جديدة` → no-send notice (not focusable) → filter tabs → campaign row link → row action → pager → footer.

**Builder:** skip link → nav → breadcrumb → import radio group (arrow keys move within the group) → `عرض كل الكشوف المؤكدة` → name field → template select → `فتح القالب` (if shown) → body preview (`tabIndex={0}`, `role="region"` with `aria-label="نص القالب"` so it can be scrolled by keyboard) → `إلغاء` → `إنشاء المسودة`.

**Detail:** skip link → breadcrumb → H1 (`tabIndex={-1}`, receives focus on client-side entry) → counts (`<dl>`, not focusable) → totals → warnings (`details`/links if any) → blocking actions → recipient search → recipient rows → `معاينة الرسالة` → pager → excluded rows → sticky bar (`إلغاء الحملة` → `تعديل` → `إرسال للاعتماد`).

**Approved:** same, minus the editable controls; the snapshot card's copy button comes before the no-send notice in DOM order.

**Templates:** skip link → breadcrumb → `قالب جديد` → group headers → version rows (`عرض` → `تفعيل` → `إصدار جديد`) → footer.

### 12.2 Live-region map

| Event | Region | Politeness |
|---|---|---|
| Draft created / submitted / approved / cancelled | Page banner (`tabIndex={-1}`) | `status` |
| Hash copied / copy failed | Under the hash | `status` |
| Version saved / activated | List banner | `status` |
| Recipient within preview dialog changed | Dialog meta line | `status` |
| Variable inserted | Under the palette | `status` |
| Blocking error, failed action, conflict | Adjacent block or dialog `role="alert"` | `alert` |
| Filter result count | Tabs (`aria-current` moves; no live region needed) | — |

Announcements must not fire on first render; mount empty, fill on event.

### 12.3 Manual test pass (required before M3 sign-off)

1. Keyboard-only: list → builder → create → preview a message → submit → approve (checkbox + dialog) → read snapshot → cancel with reason.
2. NVDA on: counts strip, recipients table, approve dialog (checkbox announcement), snapshot hash copy, a blocking panel.
3. 200% zoom and 320px width on the detail page and the approve dialog.
4. `prefers-reduced-motion` on: sticky bar entrance, skeleton.
5. A campaign with `SYP` and `USD` — no combined figure anywhere, including dialogs.
6. A campaign with zero eligible recipients — blocking panel names the reason, no submit possible.
7. Confirm the string `إرسال` appears **only** in "إرسال للاعتماد" and nowhere as a delivery action.

---

## 13. Anti-patterns (reject in implementation review)

- A `send` button, a disabled send button, a "قريبًا" send tooltip, or a `Send` icon on an approved campaign's action bar.
- Any status, banner, badge, or table cell implying delivery: `تم الإرسال`, `تم التسليم`, `قيد الإرسال`, `فشل الإرسال`, a provider name as a status.
- A message/job count, a progress bar, a delivery rate, or a cost estimate.
- Combining currencies, converting currencies, or showing a grand total.
- `Number()` / `parseFloat` on an API money string.
- A client-side eligibility computation, or a builder that previews recipients before `POST /campaigns`.
- Interpolating variables with sample/placeholder data in the builder or editor.
- Acknowledgment in the sticky bar **and** the dialog (two consents for one action).
- Approve without a confirmation dialog, or a dialog whose only safeguard is the button label.
- Immutability stated only in a tooltip.
- Hash shown truncated with no way to reach the full value.
- A revision counter, endpoint path, or raw UUID as primary text.
- Empty state before the request resolves; `0` as a loading placeholder; a currency symbol fallback.
- Errors in a toast only.
- A cancel action in the list or in a row menu.
- A disabled action with no visible reason.
- `window.confirm` / `alert`.
- Colour-only status, colour-only immutability, colour-only warning severity.
- Renaming an immutable M3 capability into a "coming soon" roadmap item on a financial screen.

---

## 14. Dependencies, gaps, assumptions

**Resolution note (3 November 2026):** The backend now exposes `cancel_reason` and the permission-aware `can_submit`/`can_approve`/`can_cancel` flags, and `CampaignDetail` includes `message_count`/`pending_job_count`. G3 and G7 are resolved; the UI still omits any optional figure that is absent. Cancellation reasons are persisted and shown.

| ID | Gap | Impact | Handling |
|---|---|---|---|
| G1 | No preview endpoint before `POST /campaigns`; the builder cannot show recipient counts or totals | A "review before create" step is impossible without fabricated numbers | Builder shows only real import + template facts and a readiness checklist; the draft detail is the first real preview (§3.6). Optional ask: `POST /campaigns/preview`, out of M3 scope. |
| G2 | `invalid_contact_count` semantics are undefined relative to `excluded[]` | A counts cell could contradict the exclusion list | Do not render it as a cell; surface contact problems only through `excluded[].reasons` |
| G3 | Approved detail exposes no message or send-job counts | Cannot show `الرسائل المُنشأة` or `بانتظار الإرسال` as numbers | Explain the rule in words (`تُنشأ رسالة واحدة لكل مستلم`), never in counts. Ask backend for `message_count` / `pending_job_count` if the reader needs it. |
| G4 | `POST /templates` versions by exact `name`; no update endpoint | A typo creates a parallel template at version 1 | Editor locks the name when creating a version from an existing template (§7.4) |
| G5 | `revision` conflict (409) has no documented payload | Conflict UX could be ambiguous | Treat any 409 on submit/approve/cancel as a stale view: block, state it, refetch, require a re-read (§8.1) |
| G6 | Cancel `reason` is optional in the API | The heaviest action can be recorded without a reason | UI requires it for approved campaigns only (§8.3) |
| G7 | No `cancelled_by` in `CampaignSummary` | The cancelled banner can name the date but not the actor | Show the date only; omit the actor row. Ask backend for `cancelled_by_name`. |
| G8 | No per-status counts endpoint | Tabs need 4–5 list calls with `page_size=1` | Counts degrade to "no number" on failure; never `0` |
| G9 | `warnings[]` has one aggregated acknowledgment flag | Per-warning checkboxes cannot be persisted | One checkbox, one boolean, full warning list visible beside it |
| G10 | No `GET /campaigns/{id}/messages` in M3 | No "what was created" drill-down | Do not link to `/messages` (placeholder). The snapshot is the record. |
| G11 | `previewed_at` may refresh on every `GET` | The "last previewed" label could mislead | Label it `حُسبت المعاينة` and show it for drafts only |
| G12 | Template list ordering is `name`, then `version desc` | A flat table would bury versions | Group by name in the UI (§7.1) |

Assumptions to confirm with the backend lane:

1. `CampaignDetail.recipients` returns **all** recipients for M3 volumes (no pagination); if it pages, the UI must not client-sum and must show `TablePager`.
2. `can_submit` / `can_approve` / `can_cancel` reflect role + status + blocking state, so the UI can rely on them for enabling actions.
3. `POST /campaigns/{id}/approve` is idempotent for an already-approved campaign (contract §2), so the dialog can close without an error on replay.
4. `blocking_reasons` is empty on an `approved` campaign.
5. `totals_by_currency` covers all eligible recipients, not a page.

**Shell flag (out of this lane's scope):** `AppShell`'s nav renders الحملات with the `Send` icon. On a screen that deliberately has no send action, the `Send` glyph is the only remaining "send" signal in the product. This spec does not redesign the shell; the shell owner should consider `Megaphone`, `ClipboardCheck`, or `ListChecks` for الحملات and keep `Send` for nothing. Do not change it inside the campaign lane.

---

## 15. Component inventory for the frontend lane

| Path | Responsibility |
|---|---|
| `components/campaigns/CampaignStatusPill.tsx` | `status → {label, tone}`, wraps `StatusPill` |
| `components/campaigns/CampaignFilterTabs.tsx` | `nav` + link tabs, counts, `aria-current` |
| `components/campaigns/CampaignCounts.tsx` | 3–4 cell `<dl>`, `—` for unknown |
| `components/campaigns/NoSendNotice.tsx` | strip / full densities, one sentence |
| `components/campaigns/CampaignFacts.tsx` | `<dl>` of source/template/creator/submitter/approver |
| `components/campaigns/SnapshotHash.tsx` | full hash, copy, status line |
| `components/campaigns/RecipientTable.tsx` | 8-col table, sticky head, expanded row ≤1024 |
| `components/campaigns/ExcludedTable.tsx` | 5-col table, reason lists, hint per code |
| `components/campaigns/CampaignWarnings.tsx` | amber list, counts, footer line |
| `components/campaigns/BlockingReasons.tsx` | red list, fix per code, actions |
| `components/campaigns/CampaignActionBar.tsx` | sticky bar, state-driven, reason lines |
| `components/campaigns/MessagePreviewDialog.tsx` | message body, meta, prev/next |
| `components/campaigns/SubmitCampaignDialog.tsx` | summary + no-send clause |
| `components/campaigns/ApproveCampaignDialog.tsx` | warnings + single acknowledgment + irreversible copy |
| `components/campaigns/CancelCampaignDialog.tsx` | `ConfirmDialog` + reason |
| `components/campaigns/ConfirmedImportPicker.tsx` | radio cards + empty state |
| `components/templates/TemplateVersionList.tsx` | grouped cards + version table |
| `components/templates/TemplateEditor.tsx` | name, body, checks, save-as-version |
| `components/templates/VariablePalette.tsx` | chips, caret insertion, announcement |
| `components/templates/ActivateVersionDialog.tsx` | consequences + activate |
| `lib/campaign-format.ts` | status labels, exclusion hints, `formatCountAr`, hash shortening |

Conventions:

- Server data in, callbacks out; no fetch inside presentational components.
- Every button gets `type="button"`.
- Money formatted from strings only; currency never inferred or omitted.
- All colours via CSS variables; all spacing logical.
- `ConfirmDialog` may gain a `children` slot; it must not be forked.

---

## 16. Top design decisions

1. **Approval and sending are visually separate products.** The campaign surface has exactly one commit verb (`اعتماد وتثبيت الحملة`) and a permanent, non-dismissible `لم تُرسل أي رسالة` statement. No send affordance exists in any state, not even disabled, because a disabled send button still promises a send.
2. **The builder refuses to preview what the server has not computed.** Import facts and the raw template body are real; recipient counts, totals, and rendered text are not invented and appear only after `POST /campaigns` creates the draft. The primary label says so (`إنشاء المسودة ومعاينة الاستحقاق`).
3. **One acknowledgment, at the point of no return.** The warning checkbox lives inside the approve dialog beside the warning list, not in the sticky bar. One consent, tied to one visible consequence.
4. **The approved screen is a locked record, not a receipt.** A green snapshot card (approver, time, totals, hash) sits above a quieter "nothing was sent" block; the hash is fully reachable and copyable, the recipient data is labelled as frozen, and every edit path is gone.
5. **Exclusions and blocking reasons name a truthful next step.** Because confirmed import data is immutable, phone/currency/balance problems are fixed by a new confirmed import — the copy says that instead of pointing at a control that does not exist. Six reason codes, six honest hints.

---

## 17. Verification for this spec

Not assigned to this lane beyond producing the document. When the frontend lane reports, these are the design-visible checks this spec is meant to support:

- [ ] 1440 capture of list, builder, draft detail, awaiting detail, approved detail, cancelled detail, template list, template editor.
- [ ] 1024 and 768 captures of the list, detail recipient table, and approve dialog.
- [ ] Zero occurrences of a send control or a delivery status string in any state.
- [ ] Approval flow: acknowledgment gate, dialog copy, snapshot card, full hash, focus move to the banner.
- [ ] Two-currency campaign shows two total lines and no combined figure in the table, bar, and both dialogs.
- [ ] Zero-eligible-recipient campaign blocks submit with a visible reason.
- [ ] Excluded table lists every code with its hint; no reason is hover-only.
- [ ] Staff view: no approve, no edit, no template management, read-only banners present.
- [ ] Keyboard-only pass of list → builder → detail → approve → cancel.
- [ ] Copy reviewed against §11 for label-first counts, the banned words table, and `إرسال` usage.
