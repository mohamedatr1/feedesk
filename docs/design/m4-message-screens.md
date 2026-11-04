# M4 — Message History, Message Detail, and Campaign Results Design Spec

**Scope:** `/messages`, `/messages/[id]`, `/campaigns/[id]/results`.
**Status:** Spec for the M4 frontend lane. No application code in this lane.
**Date:** 4 November 2026
**Sources of truth:** `docs/m4/api-contract.md` (binding), `docs/m4/subagent-brief.md`, `docs/design/design-review.md`, `docs/design/tokens.css`, `docs/design/m3-campaign-screens.md`, `apps/web/components/**`.

**Design language:** unchanged from the approved M1 dashboard, the M2 import set, and the M3 campaign set — cream `--fd-bg`, olive `--fd-brand`, 16px card radius, 10px control radius, IBM Plex Sans Arabic, 13px tables, tinted headers, dot + label pills, calm empty states. **The shell is not redesigned.** `AppShell`, `PageHeader`, `Protected`, `StatusPill`, `EmptyState`, `TablePager` are reused as-is; no new colour token is introduced.

**The M4 boundary, stated once and enforced everywhere:** messages exist, a worker may hand them to a provider, and the provider may answer. **A provider answer is not a delivery.** Only an explicit `delivered` result becomes «تم التسليم». There is no send control, no resend control, no test-send, no "إرسال الآن", no disabled send button, no `tel:`/`sms:` link, and no delivery percentage anywhere in this slice. Every screen states what is known and what is not in plain Arabic, in the same place, every time.

---

## 0. Principles for this screen set

1. **The record is the product, not the outcome.** These three screens exist to answer *what did we hand to the provider, when, and what did it say*. They do not exist to reassure. A calm «نتيجة غير معروفة» is a correct screen; a green check next to an accepted message is a false one.
2. **Green is never a delivery claim it cannot back.** A green pill appears only for `delivered` and for two lifecycle labels whose words cannot be read as delivery: «معتمدة» (governance) and «اكتملت المعالجة» (a process ended). Acceptance, queuing, submission, retry waiting, and unknown outcomes are amber — the established language of «بانتظار الاعتماد» in M3. Red is failure only, and `unknown` is never red.
3. **Counts, never ratios.** No progress bar, no percentage, no «3 من 4» progress sentence, no donut, no trend. A ratio is a claim about a total the UI does not own; counts are facts the API returns.
4. **Unknown is a first-class state.** It gets its own label, its own tone, its own filter value, its own explanation, and no automatic action. It is never rounded into "failed" or "delivered".
5. **Nothing is resent, ever, from the UI.** Not for `failed`, not for `unknown`, not for `cancelled`. The reason is on screen where the reader would look for the button, not in a tooltip.
6. **Unknown values render `—`.** Loading and missing fields never render `0`, never a currency symbol, never a guessed name, never an invented provider id, never «سيتم التحديث تلقائيًا».
7. **Read-only means read-only.** No mutation is exposed on these routes. The only actions are navigation, filtering, copying a phone or an id, and expanding a payload. Refreshing is explicit, never a timer.

### 0.1 Contract coverage

| Contract requirement | Where this spec answers it |
|---|---|
| `GET /messages` with `page`, `page_size`, `campaign_id`, `status`, `q` | §3.3, §3.6 |
| `MessageSummary` fields (campaign, guardian, phone, amount, currency, statuses, provider id, errors, timestamps) | §3.4, §3.5 |
| Empty / loading / error states | §3.7 |
| `GET /messages/{id}` adding body snapshot, redacted payload, attempts, next retry | §4 |
| No resend; no send endpoint in this slice | §1.5, §4.9, §10 |
| `GET /campaigns/{id}/results` counts, `message_count`, `last_activity_at`, `delivery_note_ar` | §5.3, §5.4 |
| Campaign status derived from message outcomes | §2.3, §5.2 |
| Accepted ≠ delivered wording | §1.5, §2.1, §5.4, §9 |
| Permissions `messages.view`, `campaigns.view` | §1.2, §5.9 |
| Arabic copy for every state | §2, §9 |
| RTL / 44px / 1440 / 1024 / 768 / focus / a11y | §6, §7, §8 |

---

## 1. Shared foundations

### 1.1 Route map, titles, entry points

```
/campaigns/[id]  ──────────────────────────► /campaigns/[id]/results   (secondary action)
/messages?campaign_id=…  ◄──────────────────  «عرض في سجل الرسائل» (results footer)

/messages
   └─ row / «عرض» ─────────────────────────► /messages/[id]
        └─ «الحملة: …» ────────────────────► /campaigns/[id]
        └─ «نتائج الحملة» ─────────────────► /campaigns/[id]/results

/campaigns/[id]/results
   ├─ row / «عرض» ─────────────────────────► /messages/[id]
   ├─ «عرض الحملة» ────────────────────────► /campaigns/[id]
   └─ panel links ─────────────────────────► /messages?campaign_id=…&status=failed|unknown
```

| Route | `<title>` |
|---|---|
| `/messages` | سجل الرسائل — FeeDesk |
| `/messages/[id]` | تفاصيل الرسالة — FeeDesk |
| `/campaigns/[id]/results` | نتائج الرسائل — FeeDesk |

`app/messages/layout.tsx` already sets the list title; `app/messages/[id]/layout.tsx` and `app/campaigns/[id]/results/layout.tsx` are new and set the remaining two. Every page keeps exactly one `<h1>`.

**Entry points added in this slice, and nothing else:**

- `/campaigns/[id]` — a secondary `نتائج الرسائل` action, rendered only when `message_count > 0`, in the existing action bar/facts area (no layout redesign). It sits next to the existing approved-state actions and never replaces `إلغاء الحملة`.
- `/campaigns` list — the approved-row secondary action becomes `عرض` (unchanged). No new row action; the list is for orientation.
- The `/messages` sidebar item is already present and already reads `سجل الرسائل`; it stops being a `ComingSoon` page.

### 1.2 Permissions and failure routes

| Route | Permission | 403 | 404 |
|---|---|---|---|
| `/messages` | `messages.view` | `EmptyState` `لا تملك صلاحية عرض سجل الرسائل.` + `العودة إلى الرئيسية` | — |
| `/messages/[id]` | `messages.view` | `EmptyState` `لا تملك صلاحية عرض هذه الرسالة.` + `العودة إلى سجل الرسائل`. Never reveal whether the id exists | `EmptyState` `لم نجد هذه الرسالة` / `قد يكون الرابط قديمًا أو أن الرسالة غير متاحة لحسابك.` + `العودة إلى سجل الرسائل` |
| `/campaigns/[id]/results` | `campaigns.view` **and** `messages.view` for the table | campaigns 403 → `لا تملك صلاحية عرض هذه الحملة.`; messages 403 → render counts + `لا تملك صلاحية عرض تفاصيل الرسائل.` (§5.9) | `لم نجد هذه الحملة` + `العودة إلى الحملات` |

Permissions come from `/auth/me.permissions` via the existing `hasPermission` helper. The API is authoritative: a 403 renders the state above even if the client thought otherwise. No control on these routes is permission-gated beyond the route itself, because every control is read-only.

### 1.3 Primitives reused, and what is new

Reused without restyling: `PageHeader` (30px/700 H1 + 14px subtitle), `EmptyState`, `StatusPill` (dot + label), `TablePager`, `.fd-card`, `.fd-card-pad`, `.fd-btn-secondary`, `.fd-input`, `.fd-table`, `.fd-skeleton`, `.fd-pill-*`, `formatDateTime`, `formatNumber`, `formatDecimalString`, and the M3 label-first count convention (`m3-campaign-screens.md` §11.2).

| New component | Responsibility |
|---|---|
| `components/messages/message-format.ts` | `MESSAGE_STATUS_META`, group sums, status hints, filter groups, plural helpers |
| `components/messages/MessageStatusPill.tsx` | `status → {label, tone}` on top of `StatusPill` |
| `components/messages/HistoryNotice.tsx` | the one read-only line (strip density only in this slice) |
| `components/messages/MessagesFilterBar.tsx` | URL-backed search + campaign select + status select + clear |
| `components/messages/MessageTable.tsx` | 8-column table at 1440, 6 at 1024; stacked rows below 768 |
| `components/messages/MessagesListView.tsx` | page shell, fetch, pager, states |
| `components/messages/MessageDetailView.tsx` | page shell, fetch, states, card composition |
| `components/messages/MessageBodyCard.tsx` | frozen body, copy, provenance note |
| `components/messages/MessageDestinationCard.tsx` | guardian, phone + copy, campaign link, amount/currency, channel |
| `components/messages/MessageStatusCard.tsx` | internal pill, delivery fact, the one explainer line |
| `components/messages/ProviderReferences.tsx` | provider message id, request id, copy |
| `components/messages/RedactedPayload.tsx` | `<details>` + `<pre>`, empty state |
| `components/messages/AttemptsCard.tsx` | attempt count, next retry, last error |
| `components/campaigns/CampaignResultsView.tsx` | results page shell |
| `components/campaigns/ResultsCounts.tsx` | grouped count cells (§5.3) |
| `components/campaigns/CampaignStatusPill.tsx` | **map extended** with `sending` / `completed` / `completed_with_errors` / `failed` (§2.3) |

Do not fork `StatusPill`, `TablePager`, `EmptyState`, or `PageHeader`. If `TablePager` needs one more label, add an optional prop; do not copy the file.

### 1.4 The read-only notice

One component, two densities, one sentence: **`عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.`**

| Density | Used on | Markup |
|---|---|---|
| **Strip** | `/messages`, `/messages/[id]`, `/campaigns/[id]/results` | Full-width row directly under the header/meta line: `Info` 16px icon (`--fd-brand`), 12.5px `--fd-ink-muted`, `--fd-brand-soft` background, 1px `--fd-line` border, radius 10, `min-h-[44px]`, `px-4 py-2`. |
| **Full** | nowhere in this slice | Reserved; do not use. Two banners on one screen is noise. |

Rules:

- Exactly once per screen.
- Not dismissible, not a toast, not a tooltip, not inside `<details>`.
- Never worded as a coming capability (`قريبًا`, «سيُضاف لاحقًا»). It states a current design decision.
- **This is not the M3 `NoSendNotice`.** M3's sentence «الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة» would be false the moment the worker runs. Do not import `NoSendNotice` into M4 screens; do not replace it in the campaign lane from here (§11, D1).

### 1.5 Truth doctrine: accepted, unknown, waiting, failed

This table is the contract for every status surface in this slice. The UI may not say anything in the right-hand columns.

| Situation | What we know | What the UI says | What the UI must never say |
|---|---|---|---|
| `pending` | Nothing has been handed to a provider | `بانتظار الإرسال` · `لم تُرسل بعد` | «جارٍ الإرسال», a spinner, a percentage |
| `submitting` | A request left; no answer yet | `قيد الإرسال إلى المزوّد` · `بانتظار رد المزوّد` | «تم الإرسال», «في الطريق» |
| `provider_accepted` | The provider acknowledged the request | `قبلها المزوّد` · `لم يصل تأكيد التسليم` | «تم الإرسال», «تم التسليم», a green check |
| `queued_by_provider` | The provider queued it | `في طابور المزوّد` · `لم يصل تأكيد التسليم` | «تم التسليم», an ETA |
| `delivered` | An explicit delivery result exists | `تم التسليم` · `سُلّمت {delivered_at}` | nothing stronger than the record supports |
| `failed` | A definitive failure was returned | `فشل الإرسال` + the error summary | «قد تكون وصلت», a retry promise |
| `unknown` | The attempt ended ambiguously (timeout/transport) | `نتيجة غير معروفة` · `لا نعرف هل وصلت` | «فشل», «تم التسليم», an automatic retry |
| Retry scheduled (`next_attempt_at` in the future) | Another attempt is queued in the record | `المحاولة التالية مجدولة في {time}` | a countdown, a progress bar, «خلال لحظات» |
| `cancelled` | The campaign cancellation stopped it | `ملغاة` · `أُلغيت قبل المعالجة` | «أُوقفت», a failure tone |

**Three sentences this slice owns** (each appears once, on the screen where it is needed):

1. **Accepted ≠ delivered:** `قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط.` (API `delivery_note_ar` preferred verbatim; constant fallback identical.)
2. **No automatic delivery updates:** `لا يصل تحديث تلقائي لحالة التسليم في هذه المرحلة. تبقى الحالة كما وصلت آخر مرة.`
3. **No resend, and why:** `لا تُعاد الرسالة تلقائيًا. قد تكون وصلت، وإعادة إرسالها قد ترسل نسخة ثانية.`

### 1.6 Refresh and motion

- **No polling, no auto-refresh, no timers** (WCAG 2.2.1 and honesty). Each screen loads once and offers an explicit `تحديث` button (`h-11`).
- After a manual refresh: `role="status"` line `حُدِّثت البيانات {time}.` under the header; focus stays on the button; the table gets `aria-busy="true"` while fetching.
- Status is never animated. No pulsing dot on `submitting`, no spinner beside a pill, no count-up.
- Only the existing `.fd-skeleton` animates, and it already respects `prefers-reduced-motion` (globals.css).
- Verdict: the only motion in this slice is the 120ms hover/background transition already in `.fd-table` rows and `.fd-btn-*`.

---

## 2. Status vocabulary

### 2.1 Message states (the only user-facing status labels)

| API value | Pill | Tone | List second line | Detail explainer (one per page) | Filter label |
|---|---|---|---|---|---|
| `pending` | بانتظار الإرسال | neutral | `لم تُرسل بعد` | `لم تُرسل إلى المزوّد بعد. تُعالَج الرسائل بالترتيب.` | بانتظار الإرسال |
| `submitting` | قيد الإرسال إلى المزوّد | amber | `بانتظار رد المزوّد` | `جرت محاولة إرسال ولم يصل ردّها بعد.` | قيد الإرسال |
| `provider_accepted` | قبلها المزوّد | amber | `لم يصل تأكيد التسليم` | `قبول المزوّد ليس تسليمًا. لا يصل تحديث تلقائي لحالة التسليم في هذه المرحلة.` | قبلها المزوّد |
| `queued_by_provider` | في طابور المزوّد | amber | `لم يصل تأكيد التسليم` | `وضع المزوّد الرسالة في طابوره. هذا لا يعني التسليم.` | في طابور المزوّد |
| `delivered` | تم التسليم | green | `سُلّمت {delivered_at}` | `وصل تأكيد تسليم من المزوّد في {delivered_at}.` | تم التسليم |
| `failed` | فشل الإرسال | red | `{last_error_summary}` else `فشلت المحاولة` | `لم يقبل المزوّد الرسالة.` + the error summary when present + `لا تُعاد تلقائيًا.` | فشل الإرسال |
| `unknown` | نتيجة غير معروفة | amber | `لا نعرف هل وصلت` | `انتهت المحاولة دون رد واضح. قد تكون الرسالة وصلت، لذلك لا تُعاد تلقائيًا.` | نتيجة غير معروفة |
| `cancelled` | ملغاة | neutral | `أُلغيت قبل المعالجة` | `أُلغيت مع إلغاء الحملة. لم تُرسل.` | ملغاة |

Rules:

- `provider_accepted` and `queued_by_provider` are **two pills, not one**. They are different provider states, and collapsing them would be the UI inventing a state.
- `unknown` is amber, never red. Red asserts failure; unknown asserts nothing.
- `failed` with no error summary still says `فشلت المحاولة`; the second line never renders empty.
- An unrecognised API value renders the neutral pill `—` plus the raw value in a muted `<bdi>` in the detail page only. Never guess a label.
- The Arabic labels above are a closed set. `تم الإرسال`, `أُرسلت`, `تم التسليم` (except as the delivered label), `مسلَّمة`, `قيد التسليم`, `في الطريق`, `وصلت` are forbidden as status text.

### 2.2 Job states are internal

`send_jobs.status` (`pending`, `claimed`, `retry`, `completed`, `failed`, `unknown`, `cancelled`) and lease fields (`locked_by`, `lease_expires_at`, `heartbeat_at`) are **never rendered**. They are worker mechanics and read as a developer console (the audit-screen lesson, `design-review.md` P1-10). The only job-derived fact the UI shows is `next_attempt_at` as «المحاولة التالية مجدولة في …».

### 2.3 Campaign states

The contract's derivation adds four campaign values to the four M3 already has. The map is extended, not redesigned.

| API value | Pill | Tone | Meaning line (results header / list second line) |
|---|---|---|---|
| `draft` | مسودة | neutral | `لم تُرسل للاعتماد` |
| `awaiting_approval` | بانتظار الاعتماد | amber | `بانتظار اعتماد مدير النظام` |
| `approved` | معتمدة | green | `لم تبدأ معالجة الرسائل` |
| `sending` | قيد المعالجة | amber | `بدأت معالجة الرسائل ولم تنتهِ` |
| `completed` | اكتملت المعالجة | green | `انتهت معالجة كل الرسائل` |
| `completed_with_errors` | اكتملت مع أخطاء | amber | `انتهت المعالجة، وبعض الرسائل فشلت أو نتيجتها غير معروفة` |
| `failed` | فشلت المعالجة | red | `فشلت كل محاولات الإرسال` |
| `cancelled` | ملغاة | neutral | `أُلغيت الحملة` |

Rules:

- The campaign pill describes **processing**, never delivery. `اكتملت المعالجة` is green because a process ended; the delivery truth is in the counts, and on the results screen the counts sit directly under the pill. Green here must never be read as «تم تسليم الجميع», and no surface may pair this pill with the word «مسلَّمة».
- `اكتملت المعالجة` never becomes `مكتملة`, `تم الإرسال`, or `نجحت`.
- These additions are additive to `CAMPAIGN_STATUS_META` and `CampaignStatus`. The campaign list and detail keep their M3 layout; only the label map and the second-line copy change (§11, D4).

---

## 3. Screen 1 — Message history (`/messages`)

### 3.1 Structure (1440)

```
┌───────────────────────────────────────────────────────────────────────────────┐
│ سجل الرسائل                                                                   │  PageHeader
│ بحث وتصفية في الرسائل التي أُنشئت من الحملات المعتمدة.                         │
│ ⓘ عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.                                │  HistoryNotice
├───────────────────────────────────────────────────────────────────────────────┤
│ [🔍 ابحث باسم ولي الأمر أو رقم الهاتف       ] [الحملة ▾] [الحالة ▾] [مسح]    │  filter bar
│ تصفية: حملة «تذكير رسوم الفصل الأول» · الحالة: نتيجة غير معروفة                │  filter summary
├───────────────────────────────────────────────────────────────────────────────┤
│ المستلم     الحملة     الهاتف         المبلغ       الحالة      مرجع المزوّد   آخر تحديث  إجراء│
│ ولي أمر 001 تذكير…     +963993000701  SYP 600,000  ●تم التسليم a1b2c3…9f      2026-11-04 [عرض]│
│             الرسوم…    ···            .00          سُلّمت 09:31               أُنشئت 11-03      │
├───────────────────────────────────────────────────────────────────────────────┤
│ عرض 1–20 من 47 رسالة                          [السابق]  1 / 3  [التالي]       │  TablePager
└───────────────────────────────────────────────────────────────────────────────┘
```

The list is a record, not a dashboard. No stat cards, no counts by status (the API has no per-status count endpoint and eight probes would be noise), no chart.

### 3.2 Header

| Element | Content |
|---|---|
| H1 | `سجل الرسائل` |
| Subtitle | `بحث وتصفية في الرسائل التي أُنشئت من الحملات المعتمدة.` |
| Actions | none. No export, no resend, no "إرسال اختبار". |
| Summary line | `الرسائل: {total}` · `آخر تحديث في هذه الصفحة {YYYY-MM-DD HH:mm}` — 12px `--fd-ink-muted`, rendered only after the first response. Loading: `—`. The second segment is the newest `updated_at` on the current page, and is labelled that way so it is never read as a global fact. |

### 3.3 Filter bar

A single logical form. Server-side filtering; all state lives in the URL (`?campaign_id=&status=&q=&page=`), so back, forward, refresh, and a shared link are honest.

```html
<form role="search" aria-label="تصفية الرسائل" class="...">
  <label for="message-q" class="sr-only">ابحث باسم ولي الأمر أو رقم الهاتف</label>
  <input id="message-q" type="search" class="fd-input h-11 ps-9 pe-9"
         placeholder="ابحث باسم ولي الأمر أو رقم الهاتف" autocomplete="off" />
  <select id="message-campaign" class="fd-input h-11">…</select>
  <select id="message-status" class="fd-input h-11">…</select>
  <a href="/messages">مسح عوامل التصفية</a>
</form>
```

| Control | Behaviour |
|---|---|
| **Search** | `q` param. Native `<input type="search">`, visible label `sr-only`, `Search` icon 16px at the **inline start** (`ps-9`), `h-11`. Debounce 400ms, then `router.replace` (typing never pushes history entries). Enter submits immediately. A `×` clear button inside the field (`pe-9`, 44×44, `aria-label="مسح البحث"`) when non-empty. A 14px spinner sits in the same slot while a request is in flight — it belongs to the input and must never be the only signal (the table also gets `aria-busy`). |
| **Campaign** | `campaign_id`. Native `<select>` with `الكل` first. Options: `GET /campaigns?page=1&page_size=50`, newest first, label `{name} — {YYYY-MM-DD}`. Long names truncate in the closed control; the full name is in the option text a screen reader reads. If the URL carries a `campaign_id` that is not in that page, call `GET /campaigns/{id}` for the name and append it as the selected option. Never show a selection the user cannot read. |
| **Status** | `status`. Native `<select>` with two `<optgroup>`s: `لم تنتهِ` → بانتظار الإرسال · قيد الإرسال · قبلها المزوّد · في طابور المزوّد; `انتهت` → تم التسليم · فشل الإرسال · نتيجة غير معروفة · ملغاة. `الكل` sits above the groups. |
| **Clear** | `مسح عوامل التصفية` — a text link (`min-h-[44px]`, inline-flex) rendered only when at least one of `q`, `campaign_id`, `status` is set. Resets to `/messages`. |
| **Filter summary** | One 12px line under the bar, only when a filter is active: `تصفية: حملة «{name}» · الحالة: {label}` and, when searching, `· البحث: «{q}»`. This is orientation, not a result count — the count lives in the pager. |

Rules:

- Selects use `push` (they change the question being asked); text uses `replace`.
- Changing any filter resets `page` to 1.
- Inputs stay enabled during a fetch; the previous rows stay visible until the new page lands, so the table never collapses to an empty state mid-request.
- The bar is not inside the table card; it sits on the page surface with a 12px gap, matching M2 §5.4.
- Placeholder is not the label. The label is present for assistive tech and the placeholder is the visible hint.

### 3.4 Table (1440)

RTL order, first column at the right. Target ≤1152px usable, no horizontal scroll at 1440.

| # | Column | Content | @1440 | @1024 | Alignment |
|---|---|---|---|---|---|
| 1 | المستلم | `<th scope="row">` link to detail: guardian name, 1 line truncated, `<bdi dir="auto">`. Second line (≤1024 only): `الحملة: {campaign_name}` link | 200 | 200 | start |
| 2 | الحملة | Campaign name link to `/campaigns/{id}`, 1 line truncated, `<bdi dir="auto">` | 170 | hidden → col 1 | start |
| 3 | الهاتف | `<bdi dir="ltr">`, `whitespace-nowrap`, no grouping | 140 | 140 | start |
| 4 | المبلغ | `SYP 600,000.00` — ISO + `formatDecimalString`, whole string in one `<bdi dir="ltr">`, tabular | 130 | 130 | start |
| 5 | الحالة | `MessageStatusPill` + 10px second line from §2.1 | 145 | 145 | start |
| 6 | مرجع المزوّد | `provider_message_id`, mono 11px, `<bdi dir="ltr">`, middle-truncated (`a1b2c3…9f`); `—` when null | 135 | hidden → detail | start |
| 7 | آخر تحديث | `updated_at` (`YYYY-MM-DD HH:mm`), `whitespace-nowrap`, tabular; second line 10px `أُنشئت {created_at}` | 135 | 135 | start |
| 8 | إجراء | `عرض`, `fd-btn-secondary h-11 px-3`, `aria-label="عرض رسالة {guardian} في حملة {campaign}"` | 72 | 72 | start |

Rules:

- `<caption class="sr-only">سجل الرسائل. الأحدث أولًا، مع الحملة ورقم الهاتف والمبلغ وحالة آخر محاولة.</caption>`, `scope="col"` on every header, `scope="row"` on the guardian.
- Row height ≥64px (two-line cells). Hover `--fd-surface-alt`; `focus-within` gets `color-mix(in srgb, var(--fd-brand-soft) 40%, transparent)`.
- Amount always carries its currency. Never a bare `600,000.00`, never the school's display symbol, never a total.
- Phone and provider id are never `title`-only disclosures. The full provider id is on the detail page; the phone is fully visible in the cell (it is short enough) and copyable on the detail page.
- No zebra striping, no vertical rules, 1px horizontal only (`.fd-table`).
- Empty body: one `<tr><td colSpan={8}>` holding the shared `EmptyState`.

### 3.5 Status cell second lines

Use §2.1 verbatim. Three implementation notes:

- `delivered` uses `delivered_at`, formatted `YYYY-MM-DD HH:mm` in `<bdi dir="ltr">`. If `delivered_at` is null while the status says `delivered`, that is a data inconsistency: render `تم التسليم` alone and do not invent a timestamp.
- `failed` uses `last_error_summary` truncated to one line. The raw `last_error_code` is never primary text; it appears in the detail page in 10px muted `<bdi>`.
- When `next_attempt_at` is in the future and the message is not terminal, the second line becomes `إعادة محاولة {time}` (this requires `next_attempt_at` on `MessageSummary`; if the backend does not add it, keep the §2.1 line and do not guess — §11, D2).

### 3.6 Pager

`TablePager` reused unchanged: `page_size=20`, `itemLabel="رسالة"`, range line `عرض 1–20 من 47` with `aria-live="polite"`, `السابق` / `التالي` at 44px, hidden when `total ≤ 20`. The range line has no counted noun — that is the M3 convention and it avoids wrong Arabic agreement; `itemLabel` supplies the noun in the zero case (`لا توجد رسالة`).

- Changing filters resets to page 1; the pager is not rendered while loading the first page.
- The pager range is the only result-count announcement. Do not add a second live region for the same fact.
- If `page` exceeds the last page (stale link), clamp to the last page and show a 12px note `عُرضت الصفحة الأخيرة.` — never an empty table with `total > 0`.

### 3.7 States

| State | Treatment |
|---|---|
| **Loading (first)** | 6 skeleton rows at 64px inside the real table shell; header stays; filters enabled; summary line `—`; pager absent. No empty state before resolve. |
| **Refreshing** | Previous rows stay, `aria-busy="true"` on `<table>`, input spinner only. Never a skeleton over existing data. |
| **Empty — no messages at all** (no filters active) | `EmptyState` in the table card, `MessageSquare` icon, title `لا توجد رسائل بعد`, description `تُنشأ رسالة واحدة لكل مستلم عند اعتماد الحملة، وتظهر هنا بحالة «بانتظار الإرسال».`, action `عرض الحملات` (secondary → `/campaigns`). |
| **Empty — filtered** | `EmptyState`, `FilterX` icon, title `لا توجد رسائل مطابقة`, description `جرّب حالة أخرى أو امسح البحث.`, action `مسح عوامل التصفية` (secondary link). |
| **Error** | Inline banner above the table, `role="alert"`, `--fd-red-soft` / `--fd-red-text`: `تعذر تحميل الرسائل.` + API `message_ar` on a second line + `إعادة المحاولة` (`h-11`). The table header stays visible. |
| **401** | `انتهت الجلسة. سجّل الدخول مرة أخرى.` in the same banner + `تسجيل الدخول` link. |
| **403** | §1.2 `EmptyState`; no table. |
| **Stuck at pending (not an error)** | No banner. If every visible row is `pending` and `total > 0`, one 12px muted line under the table: `لم تبدأ معالجة الرسائل بعد. لا شيء أُرسل إلى المزوّد حتى الآن.` — a fact, not a warning, and never a spinner. |

---

## 4. Screen 2 — Message detail (`/messages/[id]`)

### 4.1 Structure (1440)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ سجل الرسائل / تفاصيل الرسالة                                     ← breadcrumb    │
│ رسالة إلى ولي أمر 001            ●تم التسليم                                    │  H1 30px
│ الحملة: تذكير رسوم الفصل الأول · SYP 600,000.00 · SMS                          │  14px muted
│ أُنشئت 2026-11-03 21:12 · آخر تحديث 2026-11-04 09:31                            │  12px subtle
│ ⓘ عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.                                 │  HistoryNotice
├────────────────────────────────────────────────────────────────────────────────┤
│ نص الرسالة (نسخة مثبّتة)                                              [نسخ النص] │
│ ┌────────────────────────────────────────────────────────────────────────────┐ │
│ │ عزيزنا ولي أمر 001،                                                        │ │
│ │ نذكّركم بأن المبلغ المتبقي 600,000.00 SYP عن الفصل الأول.                   │ │
│ └────────────────────────────────────────────────────────────────────────────┘ │
│ نسخة مثبّتة وقت الاعتماد. لا تتغيّر إذا عُدّل القالب لاحقًا.                     │
├───────────────────────────────────┬────────────────────────────────────────────┤
│ الوجهة                            │ الحالة                                     │
│ ولي الأمر · الهاتف [نسخ] · الحملة │ الحالة الداخلية · وقت الإرسال · التسليم      │
│ المبلغ · القناة                   │ شرح الحالة                                  │
├───────────────────────────────────┼────────────────────────────────────────────┤
│ مراجع المزوّد                      │ المحاولات                                  │
│ معرّف الرسالة [نسخ] · معرّف الطلب  │ عدد المحاولات · المحاولة التالية · آخر خطأ   │
├───────────────────────────────────┴────────────────────────────────────────────┤
│ حمولة استجابة المزوّد (منقّحة)                                    ▸ عرض        │
└────────────────────────────────────────────────────────────────────────────────┘
```

Content column `max-w-[1080px]`. At ≥1024 the middle band is a 2-column grid (`1.05fr / 0.95fr`); below 1024 everything stacks in the DOM order above.

### 4.2 Header

| Element | Content |
|---|---|
| Breadcrumb | `<nav aria-label="مسار التصفح">` → `سجل الرسائل` (link) / `تفاصيل الرسالة` (`aria-current="page"`) |
| H1 | `رسالة إلى {guardian_name}` (`<bdi dir="auto">`). Fallback when the name is missing: `رسالة إلى مستلم`. The phone is never the H1. |
| Status | `MessageStatusPill`, inline after the H1, baseline-aligned |
| Context line | `الحملة: {campaign_name}` (link) · `{CUR} {amount}` · `SMS` — 14px `--fd-ink-muted`, separated by `·` |
| Meta line | `أُنشئت {created_at}` · `آخر تحديث {updated_at}` — 12px `--fd-ink-subtle`, dates in `<bdi dir="ltr">` |
| Actions | None in the header. The only affordances are copy buttons inside the cards. |

The guardian name is user data and may be long; cap at two lines, no ellipsis on the H1 (the whole page is about this one message, so truncating the H1 would be the wrong trade).

### 4.3 Frozen body

Card title `نص الرسالة`, 4px×16px brand bar, 15px/700, plus a `نسخ النص` button at the card's inline end (`h-11`, `Copy` icon). The accessible name is exactly the visible label, `نسخ النص`; the card heading supplies the context (§8.1, 2.5.3).

- Body: `<div dir="rtl" lang="ar" class="whitespace-pre-wrap text-[15px] leading-[1.9] text-[var(--fd-ink)] max-w-[68ch]">` inside a `--fd-surface-alt` box, radius 10, `p-4`, `min-h-[96px]`, `overflow-wrap: anywhere`, selectable text (`user-select: text`).
- **Not a `<textarea readonly>`.** It is text, it must reflow, and a read-only input announces itself as a form field.
- The body is the persisted snapshot. It is not re-rendered, not re-interpolated, not highlighted, and numbers inside it are never wrapped in `<bdi>` — a `<bdi>` per number fragments the sentence for screen readers. The server already produced the text.
- Provenance note under the box, 12px `--fd-ink-subtle`: `نسخة مثبّتة وقت الاعتماد. لا تتغيّر إذا عُدّل القالب لاحقًا.`
- Empty/null body (should not happen): `لا يوجد نص محفوظ لهذه الرسالة.` — never a blank box.
- Character count is **not** shown. It belongs to the template editor, not to a sent record.

Copy behaviour: `navigator.clipboard.writeText` with an `execCommand` fallback; `role="status"` line under the button `تم نسخ نص الرسالة.` for 4 seconds; failure `تعذر النسخ. حدّد النص وانسخه يدويًا.` and the body becomes `user-select: all`. Never `alert()`.

### 4.4 Destination

Card title `الوجهة`. A `<dl>` with 12px label / 13px value:

| Row | Value |
|---|---|
| ولي الأمر | `guardian_name` in `<bdi dir="auto">` |
| الهاتف | `<bdi dir="ltr">+963993000701</bdi>`, mono, `whitespace-nowrap` + a 44×44 `Copy` icon button, `aria-label="نسخ رقم الهاتف"`. **Plain text, never a `tel:` or `sms:` link** — on a phone, an `sms:` link would open the device messaging app on a school record, which is one tap from a real send outside the product. |
| الحملة | Link to `/campaigns/{campaign_id}`: `{campaign_name}` (`<bdi dir="auto">`), second muted line `نتائج الحملة ↗` → `/campaigns/{id}/results` |
| المبلغ | `SYP 600,000.00`, one `<bdi dir="ltr">`, tabular |
| القناة | `SMS` (`<bdi dir="ltr" lang="en">`). If the API returns anything else, render the raw value in `<bdi>` plus the muted line `قناة غير معروفة.` — never translate an unknown channel to "SMS" |

Copy confirmation for the phone uses a single `role="status"` line under the phone row: `تم نسخ رقم الهاتف.` Never a toast.

### 4.5 Status card and the single explainer

Card title `الحالة`. A `<dl>`:

| Row | Value |
|---|---|
| الحالة الداخلية | `MessageStatusPill` (always first — the product's vocabulary leads) |
| وقت الإرسال إلى المزوّد | `submitted_at` (`YYYY-MM-DD HH:mm`, `<bdi dir="ltr">`), or `لم تُرسل إلى المزوّد بعد.` — this is a submission time, never a delivery claim |
| تأكيد التسليم | `{delivered_at}` when present; otherwise `لم يصل تأكيد تسليم.` |
| حالة المزوّد (كما وردت) | `provider_status` raw, mono 11px, `<bdi dir="ltr" lang="en">`, or `—` |
| آخر خطأ | `last_error_summary` verbatim + `last_error_code` in 10px muted `<bdi>`; or `لا يوجد خطأ مسجّل.` |

Then the **one** explainer line from §2.1 for the current state, 12.5px `--fd-ink-muted`, with a 3px inline-start bar in the state's tone colour (neutral / amber / green / red) and no background fill. It is page content, in normal reading order, not a tooltip and not `role="alert"`.

Additional rules:

- The raw provider status is shown **only here and only as data**. It never becomes the pill, the column label, or the Arabic label. The design-review rule stands: provider strings are not user-facing labels.
- If the internal status and the provider status disagree, say nothing clever. Show both, truthfully, with no "mismatch" badge — the mapping belongs to the server.
- No ETA, no "سيتم التحديث تلقائيًا", no countdown. Webhooks are unverified and deferred; the record can stay `provider_accepted` indefinitely and the screen must look honest doing it.

### 4.6 Provider references

Card title `مراجع المزوّد`. `<dl>`:

| Row | Value |
|---|---|
| معرّف رسالة المزوّد | `provider_message_id`, mono 11px, `<bdi dir="ltr" lang="en">`, `break-all` + 44×44 copy button, `aria-label="نسخ معرّف رسالة المزوّد"`. `—` when null |
| معرّف طلب المزوّد | `provider_request_id`, same treatment. `—` when null or not returned |

Rules:

- This card holds ids only. `provider_status` lives in the status card (§4.5) and is not repeated here.
- A missing id renders `—` with a 11px muted line `لم يُسجَّل.` — never `غير متاح`, and never an empty row with no value.
- Full ids are always reachable; truncation is forbidden here (the copy button exists, but the value must be readable and selectable).
- Copy confirmations use one shared `role="status"` line at the bottom of the card, replaced per action.

### 4.7 Redacted payload

Card title `حمولة استجابة المزوّد (منقّحة)` with a `<details>` whose `<summary>` is `عرض الحمولة` (chevron + `min-h-[44px]`, `aria-expanded` native).

- Above the payload, 12px muted, always visible (not inside the collapsed region): `أُزيلت الحقول الحساسة قبل الحفظ. لا تُعرض مفاتيح الوصول ولا نص الطلب الكامل.`
- Payload: `<pre dir="ltr" lang="en" class="max-h-[320px] overflow-auto whitespace-pre-wrap break-all rounded-[10px] bg-[var(--fd-surface-alt)] p-3 font-mono text-[11px] leading-5">` with `JSON.stringify(payload, null, 2)`.
- Empty (`{}` / null): replace the `<details>` entirely with `لا توجد حمولة مسجّلة.` — no empty code box, no `{}` as content.
- The payload is evidence, not a status. Nothing in this card may be summarised as success or failure. No colour coding of fields, no badges derived from payload contents.
- Never render request headers, API keys, or the full request body. If a payload contains a suspiciously sensitive key, that is a backend redaction bug, not something the UI can fix by hiding it — flag it, do not display it.

### 4.8 Attempts, retry, failure

Card title `المحاولات`. `<dl>`:

| Row | Value |
|---|---|
| عدد المحاولات | `attempt_count` tabular, or `—` |
| المحاولة التالية | `next_attempt_at` → `مجدولة في {time}`; null → `لا توجد محاولة مجدولة.` |
| آخر خطأ | summary + code, or `لا يوجد خطأ مسجّل.` |

Rules:

- **Never print a max-attempts denominator** (`2 من 3`). `MESSAGING_MAX_ATTEMPTS` is server config and is not in the response. Inventing the cap would be a claim about retry policy the UI cannot verify.
- A scheduled retry is a fact about the record: `المحاولة التالية مجدولة في {time}.` No countdown, no "سيُعاد خلال دقائق", no progress.
- The retry explainer, shown once when a retry is scheduled, under the `<dl>`: `تُعاد المحاولة تلقائيًا وفق سياسة المحاولات. لا تحتاج إلى إجراء.` — statement of policy, not a promise of delivery.
- `unknown`: `next_attempt_at` must be null; if the API returns a date anyway, still render `لا توجد محاولة مجدولة.` for `unknown` and flag the inconsistency — never imply a blind resend exists.
- For `failed` and `unknown`, the attempts card ends with the **no-resend block** (below), not a button.

### 4.9 What is absent, and why (stated on the page)

There is no `إعادة الإرسال`, no `إرسال مرة أخرى`, no `تجاهل`, no `تعليم كمُسلَّمة`, no status override, no delete, no export. One short block, placed at the end of the content before the back link, 12.5px `--fd-ink-muted`, no icon, no border, no red:

| Current state | Copy |
|---|---|
| `failed` | `لا يوجد إجراء إعادة إرسال. أصلح سبب الفشل — غالبًا رقم الهاتف أو بيانات المستلم — ثم أنشئ حملة جديدة.` |
| `unknown` | `لم نتأكد من نتيجة آخر محاولة. قد تكون الرسالة وصلت، وإعادة إرسالها قد ترسل نسخة ثانية. لذلك لا تُعاد تلقائيًا ولا يدويًا في هذه المرحلة.` |
| `provider_accepted` / `queued_by_provider` | `قبول المزوّد لا يعني التسليم. لا يصل تحديث تلقائي لحالة التسليم في هذه المرحلة.` |
| `delivered` | `هذه الرسالة مؤكدة التسليم. لا يوجد ما يلزم فعله.` |
| `pending` | `لم تُرسل إلى المزوّد بعد. لا يوجد إجراء مطلوب منك.` |
| `cancelled` | `أُلغيت الرسالة مع إلغاء الحملة. لا يمكن إعادتها.` |

This block is the honest answer to the question the missing button raises. It is never replaced by a disabled control with a tooltip (§10).

### 4.10 States

| State | Treatment |
|---|---|
| Loading | Header skeleton (H1 40%, meta 60%), then four card skeletons of matching height. No `—`-filled cards that look loaded. |
| 404 | `EmptyState` `لم نجد هذه الرسالة` (§1.2), `MessageSquare` icon. |
| 403 | `EmptyState` `لا تملك صلاحية عرض هذه الرسالة.` |
| Error | `role="alert"` banner under the header: `تعذر تحميل الرسالة.` + API `message_ar` + `إعادة المحاولة` (`h-11`). No partial cards. |
| Payload fetch fails (if loaded separately) | Only the payload card shows `تعذر تحميل الحمولة.` + inline retry; the rest of the page stays usable. Prefer one request; do not split unless the payload is large. |

---

## 5. Screen 3 — Campaign results (`/campaigns/[id]/results`)

### 5.1 Structure (1440)

```
┌────────────────────────────────────────────────────────────────────────────────┐
│ الحملات / تذكير رسوم الفصل الأول / نتائج الرسائل              ← breadcrumb       │
│ نتائج الرسائل                                              [تحديث]              │
│ الحملة: تذكير رسوم الفصل الأول ↗    ●قيد المعالجة                              │
│ آخر نشاط 2026-11-04 09:31                                                       │
│ ⓘ عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.                                 │
├────────────────────────────────────────────────────────────────────────────────┤
│ قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط.                          │  delivery note
├────────────────────────────────────────────────────────────────────────────────┤
│  الإجمالي 4     لم تبدأ 0        لم يصل تأكيد التسليم 1                          │  ResultsCounts
│  تم التسليم 2   تحتاج مراجعة 1   (خلية «ملغاة» تظهر فقط عند وجود ملغاة)          │  (3 × 2)
│                 فشل الإرسال 1 · نتيجة غير معروفة 0                              │
├────────────────────────────────────────────────────────────────────────────────┤
│ تحتاج مراجعة (1)                                                                │
│ فشل الإرسال 1: لم يقبل المزوّد هذه الرسائل…            [عرض رسائل فشل الإرسال]   │
├────────────────────────────────────────────────────────────────────────────────┤
│ الرسائل (4)                                  [عرض في سجل الرسائل ↗]            │
│ المستلم  الهاتف  المبلغ  الحالة  آخر تحديث  إجراء                                │
│ …                                                                                │
│ هذه الصفحة تعرض 4 من 4. الأعداد أعلاه لكل رسائل الحملة.                           │
├────────────────────────────────────────────────────────────────────────────────┤
│ [العودة إلى الحملات]                              [عرض الحملة]                   │
└────────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Header

| Element | Content |
|---|---|
| Breadcrumb | `الحملات` / campaign name (link to `/campaigns/{id}`) / `نتائج الرسائل` (`aria-current="page"`) |
| H1 | `نتائج الرسائل` |
| Campaign line | `الحملة: {name}` as a link, followed by `CampaignStatusPill` — one line, wraps at 768 |
| Meaning line | §2.3 meaning for the campaign status, 12px `--fd-ink-muted` |
| Activity line | `آخر نشاط {last_activity_at}` (`YYYY-MM-DD HH:mm`, `<bdi dir="ltr">`), or `لا يوجد نشاط بعد.` |
| Action | `تحديث` (secondary, `RefreshCw` 15px, `h-11`) at the inline end |

Rules:

- The campaign pill is **always** accompanied by the meaning line. A bare `اكتملت المعالجة` would be read as "everything arrived".
- `تحديث` is the only action. It never becomes `إعادة المحاولة` (that word belongs to a failed request) and never a spinner that spins on its own.
- No campaign edit, cancel, approve, duplicate, or send control on this route. Those live on `/campaigns/[id]` and this page links back there.

### 5.3 Progress counts

`ResultsCounts`: a `<dl>` grid, 2 columns below 768, 3 columns at ≥768. Six cells, in this order. Values are `formatNumber` of API counts, and `—` while loading.

| Cell | Value | Tone | Muted composition line (when the cell sums several states) |
|---|---|---|---|
| الإجمالي | `message_count` | neutral, 24px/700 | — |
| لم تبدأ | `pending` | neutral | — |
| لم يصل تأكيد التسليم | `submitting + provider_accepted + queued_by_provider` | amber when >0 | `قيد الإرسال {n} · قبلها المزوّد {n} · في الطابور {n}` — zero parts omitted |
| تم التسليم | `delivered` | green when >0 | — |
| تحتاج مراجعة | `failed + unknown` | red when `failed > 0`, amber when only `unknown > 0`, neutral at 0 | `فشل الإرسال {n} · نتيجة غير معروفة {n}` — zero parts omitted, the line is omitted when both are 0 |
| ملغاة | `cancelled` | neutral | rendered **only** when `> 0` |

Rules:

- The composition line is the honest compromise: it keeps the accepted-vs-delivered distinction visible without an eight-cell wall. The per-message table and `/messages` filters carry the exact state.
- The muted composition line is **not** a second count claim — it is the same counts, broken down. It must be generated from the response, never from the visible page.
- A cell whose value is `0` still renders `0`, not `—`: zero is a real, known count. `—` is reserved for unresolved/absent data. This mirrors M3's rule (null → `—`, known zero → `0`) and must be stated in a code comment so it is never "fixed" to `—` later.
- Cell background tint only when the tone's value is `> 0`, matching `CampaignCounts`/`ImportCounts`. Never colour by "good/bad" beyond failure/unknown.
- **No progress bar, no percentage, no donut, no ratio sentence** such as `انتهت 3 من 4`. If the reader needs that, the counts are on screen.
- If a count key is missing from the response, that cell renders `—` and the composition line is omitted. The totals are never back-filled by summing the other cells.

### 5.4 The delivery note

Directly under the counts card, a single line, no icon, no border, 12.5px `--fd-ink-muted`:

> `قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط.`

Source: `delivery_note_ar` verbatim. If it is missing, render the same sentence as a constant. Do not paraphrase, do not add a second sentence, do not repeat the note elsewhere on the page (one statement, one place).

### 5.5 Failed and unknown panels

One card, `تحتاج مراجعة ({failed + unknown})`, rendered only when the sum is `> 0`. Two rows, each a count + a truthful next step + a link:

| Row | Icon / tone | Copy | Link |
|---|---|---|---|
| فشل الإرسال ({n}) | `CircleAlert` 16px, `--fd-red-text` | `لم يقبل المزوّد هذه الرسائل. راجع سبب الفشل في كل رسالة، ثم أنشئ حملة جديدة بعد تصحيح البيانات.` | `عرض رسائل فشل الإرسال` → `/messages?campaign_id={id}&status=failed` |
| نتيجة غير معروفة ({n}) | `TriangleAlert` 16px, `--fd-amber-text` | `لم نتأكد من وصول هذه الرسائل. قد تكون وصلت، ولا تُعاد تلقائيًا.` | `عرض الرسائل غير المعروفة` → `/messages?campaign_id={id}&status=unknown` |

Rules:

- A row with `0` is **not rendered**; the panel disappears when both are `0`. (The counts cell still shows `0`.)
- The panel links out to the filtered history instead of duplicating a message list. Reasons: the results endpoint returns counts, not rows; fetching two extra filtered pages would create three sources of truth for one number, and the list already has the filter, the pager, and the detail links.
- If the backend later adds a small `review[]` preview to the results payload, a compact 5-row preview may be added inside this card. Until then, do not fetch and slice client-side.
- No dismiss button, no acknowledgement checkbox, no "mark as resolved". There is nothing to write.
- The panel is not a `role="alert"`: it is a report of stored outcomes, not an event. Only a *new* failure appearing after a manual refresh could be announced, and this slice does not do that.

### 5.6 Per-message table

Data source: `GET /messages?campaign_id={id}&page=…&page_size=20` — **not** the results payload (it has no rows). The table is the same `MessageTable` component as `/messages` with `campaign` column suppressed and `search` omitted.

| # | Column | Content | @1440 | @1024 |
|---|---|---|---|---|
| 1 | المستلم | `<th scope="row">` link to `/messages/{id}`, guardian name; second line muted `أُنشئت {created_at}` | 240 | 220 |
| 2 | الهاتف | `<bdi dir="ltr">`, no grouping | 150 | 140 |
| 3 | المبلغ | `SYP 600,000.00` | 140 | 130 |
| 4 | الحالة | Pill + §2.1 second line | 170 | 160 |
| 5 | آخر تحديث | `YYYY-MM-DD HH:mm` | 150 | 130 |
| 6 | إجراء | `عرض`, 44px | 80 | 80 |

Rules:

- `<caption class="sr-only">رسائل حملة {name}، مع الحالة ووقت آخر تحديث.</caption>`; `scope="col"`; `scope="row"` on the guardian.
- A `failed` or `unknown` row gets a 3px inline-start marker in its tone colour, in addition to the pill — never colour-only (M2 §5.8 pattern).
- Under the table (or in the pager area), the honesty line: `هذه الصفحة تعرض {shown} من {total}. الأعداد أعلاه لكل رسائل الحملة.` — noun-free, so agreement can never be wrong. This resolves the only place where two API calls could appear to disagree; the UI never "reconciles" them.
- `TablePager`, `page_size=20`, `itemLabel="رسالة"`. Hidden when `total ≤ 20`.
- Footer links: `عرض في سجل الرسائل` → `/messages?campaign_id={id}` (secondary), `العودة إلى الحملات` (secondary), `عرض الحملة` → `/campaigns/{id}`. All 44px, 8px apart, primary weight on none of them: this screen has no primary action.

### 5.7 Campaign state explanations on this screen

| Campaign status | What the screen adds |
|---|---|
| `approved`, no messages moved | Under the counts: `لم تبدأ معالجة الرسائل بعد. لا شيء أُرسل إلى المزوّد حتى الآن.` No spinner, no ETA. |
| `sending` | Nothing beyond the pill + meaning line. The counts and `تحديث` are the whole story. |
| `completed` | Nothing beyond the pill + meaning line. The counts show whether anything is still unconfirmed. |
| `completed_with_errors` | The review panel is present and is the page's main content below the counts. |
| `failed` | Review panel present; the copy is the same (all rows will be `failed`). |
| `cancelled` | One line under the counts: `أُلغيت الحملة في {cancelled_at}. الرسائل التي لم تُعالَج أُلغيت.` The words «أُلغيت» and «لم تُرسل» only — never «فشلت». |
| `draft` / `awaiting_approval` | Do not render counts at all. Replace the lower half with `EmptyState` (`Megaphone` icon): `لم تُنشأ رسائل هذه الحملة بعد` / `تُنشأ الرسائل عند اعتماد الحملة.` action `عرض الحملة`. No table, no panels, no zeros. |

### 5.8 States

| State | Treatment |
|---|---|
| Loading | Counts: every cell it will show renders `—`; the composition lines are absent. Campaign line: skeleton. Table: 5 skeleton rows. No zeros, no empty state. |
| Results fail, messages succeed | Counts card replaced by a `role="alert"` block `تعذر تحميل أعداد الرسائل.` + retry; the table still renders. Never show `0`. |
| Messages fail, results succeed | Counts render; the table card shows the error banner + `إعادة المحاولة`. |
| Both fail | One banner above, both cards replaced by the same retry block. Do not stack two identical errors. |
| No messages (`message_count = 0`) and campaign approved | `EmptyState` `لا توجد رسائل لهذه الحملة` / `لم تُنشأ سجلات رسائل عند الاعتماد.` action `عرض الحملة`. |
| 404 | `لم نجد هذه الحملة` + `العودة إلى الحملات`. |

### 5.9 The permission split on this screen

`campaigns.view` and `messages.view` are separate. If the results call succeeds and the messages call returns 403:

- Render the header, campaign line, counts, delivery note, and review panels (counts only).
- Replace the table card with `EmptyState` (`Lock` icon): `لا تملك صلاحية عرض تفاصيل الرسائل.` / `تظهر الأعداد فقط.`, action `العودة إلى الحملات`.
- Hide the `عرض في سجل الرسائل` link.
- Do **not** render an empty table, and do not claim there are no messages.

---

## 6. RTL, numbers, currency, tables

### 6.1 RTL

| Rule | Implementation |
|---|---|
| Direction | `html dir="rtl" lang="ar"` (inherited); only LTR-isolated values get a local `dir` |
| Column order | First column at the **right**, actions at the far left |
| Spacing | Logical properties only (`ps/pe/ms/me/border-s/start-0`). `mr-2`-style physical utilities are a defect |
| Breadcrumb | `ChevronLeft` with `rtl:rotate-180`; never a mirrored arrow glyph asset |
| Icons on inputs | `ps-9` padding with the icon at the inline start — the RTL equivalent of the M1 login fix (design-review P2-12) |
| Provider ids, phone, raw status | `<bdi dir="ltr">`, `whitespace-nowrap`; ids also `lang="en"` |
| Message body | `dir="rtl"`, `white-space: pre-wrap`; numbers inside the sentence are **not** individually wrapped |
| Timestamps | `<bdi dir="ltr">`, `YYYY-MM-DD HH:mm`, `tabular-nums`, `whitespace-nowrap` |
| Nested links in a cell | Link text inside `<bdi dir="auto">` so an Arabic name with a Latin number keeps its own direction |
| Icons never mirrored | `Info`, `RefreshCw`, `Copy`, `MessageSquare`, `FilterX`, `CircleAlert`, `TriangleAlert`, `Lock` |

### 6.2 Tables

- `.fd-table` 13px, two-line rows `min-h-[64px]`, header 11–12px `--fd-ink-muted` on `--fd-surface-alt`.
- `<caption class="sr-only">` on every table; `scope="col"` on every header; `scope="row"` on the identifying cell.
- Numeric cells `font-variant-numeric: tabular-nums`, `<bdi dir="ltr">`.
- 1px horizontal borders only; no vertical grid; no zebra; last row borderless (already in `.fd-table`).
- Empty body is one `<tr><td colSpan>` containing `EmptyState` — never a bare blank `<tbody>`.
- Header stays visible while a table scrolls inside its card (`position: sticky; top: 0; z-index: 1`). The goal is **no** horizontal scroll at 1440 and 1024; below 1024 the list is not a table (§7.3).
- Row hover `--fd-surface-alt`; `focus-within` tint; the row itself is not a click target — the name cell and `عرض` are.

### 6.3 Numbers

- Latin digits everywhere (`ar-SY-u-nu-latn`), matching M1–M3.
- Counts grouped above 9,999 (`formatNumber`), tabular in cells and count cards.
- Phones and provider ids: no grouping, no separators, no shortening on the detail page.
- Attempt counts are plain integers with no denominator (invented caps are forbidden).

### 6.4 Currency and money

- Per message: `CUR amount` — ISO first, then `formatDecimalString`, whole string in one `<bdi dir="ltr">`. `SYP 600,000.00`.
- No `Number()`, `parseFloat`, or arithmetic on any money string.
- No total on these screens. The results page counts messages; the campaign's per-currency totals stay on `/campaigns/[id]`. Summing visible rows would create a second, page-scoped total that can contradict `totals_by_currency`.
- No currency symbol from settings, no conversion, no combined figure, no "≈".
- A missing currency renders `—` and the amount cell shows `—` as a whole. Never an amount without a currency.

---

## 7. Responsive behaviour

### 7.1 1440 (primary target)

- Shell 240px sidebar, ~1152px usable. Content column `max-w-[1080px]` on the detail page; list and results use the full content width.
- List: 8 columns as §3.4, no horizontal scroll, filter bar one row.
- Detail: body card full width, then two 2-column bands, then the payload full width.
- Results: counts 3×2, review panel full width, table 6 columns, footer links one row.
- This is the acceptance width for the visual comparison against the approved dashboard.

### 7.2 1024

- Sidebar 76px, ~916px usable.
- List: drop `الحملة` and `مرجع المزوّد`; campaign name moves to the guardian cell's second line; provider id lives in the detail. 6 columns: 200 + 140 + 130 + 145 + 135 + 72.
- Filter bar wraps to two rows: search full width on row 1; campaign, status, clear on row 2.
- Detail: the two 2-column bands stack (الوجهة → الحالة → المحاولات → مراجع المزوّد). DOM order changes accordingly; do not use CSS `order` to reorder — a screen reader must follow the visual order.
- Results: counts 3×2; table 6 columns at 220/140/130/160/130/80 = 860; the composition lines may wrap to two lines, never truncate a count.
- `تحديث` moves below the campaign line if the header wraps.

### 7.3 768

- Content ~660px, 16px padding; sidebar still 76px.
- **List becomes stacked rows**, not a narrower table:
  ```
  <li class="rounded-[10px] border border-[var(--fd-line)] p-4">
    <div class="flex items-start justify-between gap-3">
      <Link>ولي أمر 001</Link>  <MessageStatusPill/>
    </div>
    <p class="text-[11px]">الحملة: …</p>        ← link
    <dl class="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[12px]">
      <div><dt>الهاتف</dt><dd>+963…</dd></div>
      <div><dt>المبلغ</dt><dd>SYP 600,000.00</dd></div>
      <div><dt>آخر تحديث</dt><dd>2026-11-04 09:31</dd></div>
      <div><dt>أُنشئت</dt><dd>2026-11-03 21:12</dd></div>
    </dl>
    <Link class="fd-btn fd-btn-secondary h-11">عرض الرسالة</Link>
  </li>
  ```
  Rendered as `<ul>` inside the card. Each `<li>` holds the guardian link, the pill, the campaign link, a `<dl>` of the remaining facts, and the row action. Table semantics are deliberately traded for list semantics because five facts per row cannot survive three columns without horizontal scroll (WCAG 1.4.10).
- The provider id is absent from list contexts below 1024 (table column dropped at 1024, card row absent at 768); the detail page is the single home for it.
- Filter bar: all four controls stack full width, 8px apart; `مسح عوامل التصفية` is a text button under them.
- Detail: single column; body `max-w-none`; copy buttons remain 44px; the payload `<pre>` scrolls horizontally inside its box only.
- Results: counts 2 columns; the `ملغاة` cell joins the flow only when present; review rows stack (label, copy, link); table becomes the same stacked list as `/messages`.
- Breadcrumbs truncate the campaign name in the middle, keeping `نتائج الرسائل` visible.

### 7.4 Below 768 (not a target, must not break)

- No page-level horizontal scroll (1.4.10). Table columns drop or the table becomes a list; type never shrinks below 12px.
- Payload and long ids scroll inside their own containers.
- The read-only notice stays one line-wrapping paragraph; it is never collapsed or hidden.

### 7.5 Never changes across widths

- The status pill is never hidden, never abbreviated, never colour-only.
- `قبول المزوّد لا يعني التسليم` is never hidden.
- The no-resend explanation is never hidden behind a tooltip or an accordion.
- Money always carries its currency.
- The provider id is always reachable somewhere on the path (list at ≥1024, detail always).
- No control ever becomes a send/resend button at any width.

---

## 8. Accessibility (WCAG 2.2 AA)

### 8.1 Checklist

| SC | Requirement | How this slice meets it |
|---|---|---|
| 1.1.1 | Non-text content | Every icon `aria-hidden` or attached to a labelled control; status always has text |
| 1.3.1 | Info & relationships | Real `<table>` with `<caption>`/`scope`; counts are `<dl>`; body is a heading + paragraph; payload is `<pre>` inside `<details>` |
| 1.3.2 | Meaningful sequence | Breadcrumb → H1 → status → notice → content cards → actions; no CSS reordering |
| 1.3.4 / 1.3.5 | Orientation / input purpose | No orientation lock; `type="search"`, `autocomplete="off"`, phone and ids are text, never a special-purpose input |
| 1.4.1 | Use of colour | Pill label + second line; failed/unknown rows add a border marker; no colour-only severity |
| 1.4.3 | Contrast (text) | All pairs from the token set: green 6.71:1, red 6.57:1, amber 5.37:1, neutral 5.67:1; secondary text `--fd-ink-muted`/`--fd-ink-subtle` on surface ≥4.5:1 |
| 1.4.4 | Resize text | 200% zoom: no fixed-height text containers; rows use `min-height`; cards use padding |
| 1.4.10 | Reflow | 320px: list/detail/results stack; nothing scrolls the page horizontally |
| 1.4.11 | Non-text contrast | Inputs/selects `--fd-line-input` (3.11:1); `<summary>` chevron plus text; pill dots are decorative and never the only signal |
| 1.4.12 | Text spacing | 1.6 body, 1.9 message body; padding-based cells, no fixed heights |
| 1.4.13 | Content on hover/focus | The payload is a keyboard-operable `<details>`, not a hover tooltip; full ids are visible, not truncated-only |
| 2.1.1 | Keyboard | Search, selects, clear, row links, copy buttons, `<summary>`, pager, refresh all native |
| 2.1.2 | No keyboard trap | No dialogs on these routes at all |
| 2.2.1 | Timing | No polling, no auto-refresh, no countdown, no auto-dismiss (the copy confirmation is a static line, replaced on the next copy) |
| 2.4.1 | Bypass blocks | Existing skip link in `AppShell` |
| 2.4.2 | Page titled | §1.1 per-route metadata |
| 2.4.3 | Focus order | §8.2 |
| 2.4.6 | Headings & labels | One `<h1>`; cards `<h2>`; no skipped levels; the body section has a visible `<h2>` |
| 2.4.7 | Focus visible | Global 2px `--fd-brand` outline, offset 2 (offset −2 inside table cells); never clipped by `overflow: hidden` |
| 2.5.3 | Label in name | `aria-label="عرض رسالة {guardian} في حملة {campaign}"` contains the visible verb `عرض` |
| 2.5.8 | Target size | 24×24 minimum; project rule ≥44×44 for every control (§8.3) |
| 3.1.1 / 3.1.2 | Language | `lang="ar"` on the page; `lang="en"` on ids and raw provider status; `<bdi>` elsewhere |
| 3.2.2 | On input | Typing filters after a debounce; it never navigates the user away, never steals focus, never opens anything |
| 3.3.1 | Error identification | Errors in `role="alert"` with the API `message_ar`; search has no validation errors |
| 3.3.2 | Labels or instructions | Search labelled; status groups named; the delivery note explains the vocabulary in place; the no-resend block explains the absence |
| 3.3.3 | Error suggestion | Every error names the next step (`إعادة المحاولة`, `تسجيل الدخول`, `العودة إلى سجل الرسائل`) |
| 4.1.2 | Name, role, value | Native controls; `aria-current="page"` on the current breadcrumb; `aria-busy` on loading tables; no div-buttons |
| 4.1.3 | Status messages | `role="status"` for copy/refresh; `role="alert"` for load failures; never both for one event |

### 8.2 Focus order

**`/messages`:** skip link → sidebar nav → topbar → H1 (not focusable, it is first reading content) → search field → campaign select → status select → `مسح عوامل التصفية` → table row link (guardian) → row `عرض` → next row … → pager `السابق` → `التالي`.

**`/messages/[id]`:** skip link → breadcrumb → H1 (`tabIndex={-1}`, focused on client-side entry from a list row) → `نسخ النص` → `نسخ رقم الهاتف` → campaign link → `نتائج الحملة` → provider id copy → request id copy → `<summary>` `عرض الحمولة` (payload content follows in tab order only when open) → back link.

**`/campaigns/[id]/results`:** skip link → breadcrumb → H1 → `تحديث` → review panel links (`عرض رسائل فشل الإرسال`, `عرض الرسائل غير المعروفة`) → table rows → pager → `عرض في سجل الرسائل` → `عرض الحملة` → `العودة إلى الحملات`.

Rules:

- Count cells are not focusable (nothing to do with them); their values are read in document order.
- The read-only notice is not focusable and not a landmark; it is paragraph content.
- No `tabIndex` above 0 anywhere. No focus moves on filter change.
- After a manual refresh, focus stays on `تحديث`; the status line is announced, not focused.

### 8.3 Targets

- Filter inputs/selects `h-11` (44px) — note `.fd-input` defaults to `h-10`; these screens must add `h-11` rather than change the primitive.
- Copy buttons `h-11 w-11`, `aria-label` naming the value.
- `<summary>` `min-h-[44px]`, full card width clickable.
- Row action `h-11 px-3`; pager buttons already `h-11`; `تحديث` `h-11`.
- Text links inside sentences are exempt from 44px (inline exception), but any link used as a row action or a panel action is padded to 44.

### 8.4 Live regions

| Event | Region | Politeness |
|---|---|---|
| Page loads / filters change | Pager range line (`aria-live="polite"`) | `polite` |
| Phone / body / id copied | Line under the copied control | `status` |
| Copy failed | Same line | `status` |
| Manual refresh done | Under the header | `status` |
| Load failure | Banner above the card | `alert` |
| Permission split notice | Rendered on mount as content | — (not announced) |

Announcements mount empty and fill on the event. Nothing fires on first render.

### 8.5 Manual test pass (required before M4 sign-off)

1. Keyboard-only: filter → open a message → copy the phone → expand the payload → open the campaign → open results → filter into a failed message.
2. NVDA: the list table (caption + row header), a count card `<dl>`, the payload `<summary>`/`<pre>`, a `unknown` message's explainer.
3. 200% zoom and 320px width on all three screens.
4. `prefers-reduced-motion`: skeletons stop.
5. A campaign with at least one `provider_accepted`, one `unknown`, one `failed`: no green appears for accepted or unknown anywhere.
6. Confirm the strings `إعادة الإرسال` and `إرسال الآن` appear **nowhere**; `إرسال` appears only in state labels describing what happened (`بانتظار الإرسال`, `قيد الإرسال إلى المزوّد`, `فشل الإرسال`).
7. Confirm no `tel:` or `sms:` link exists in the rendered DOM.

---

## 9. Arabic copy deck

**Voice:** plain Modern Standard Arabic, second person where an action exists, no system jargon, no English codes in primary text. `المزوّد` is the only technical noun and it is unavoidable. Every failure names the next step. Numbers are Latin digits.

### 9.1 Headings and page copy

| Slot | Copy |
|---|---|
| `/messages` H1 | `سجل الرسائل` |
| `/messages` subtitle | `بحث وتصفية في الرسائل التي أُنشئت من الحملات المعتمدة.` |
| List summary (loaded) | `الرسائل: {total}` |
| List summary (page activity) | `آخر تحديث في هذه الصفحة {datetime}` |
| Filter summary | `تصفية: حملة «{name}» · الحالة: {label}` · appends `· البحث: «{q}»` |
| Detail H1 | `رسالة إلى {guardian_name}` |
| Detail context | `الحملة: {name} · {CUR} {amount} · SMS` |
| Detail meta | `أُنشئت {created_at}` · `آخر تحديث {updated_at}` |
| Results H1 | `نتائج الرسائل` |
| Results campaign line | `الحملة: {name}` |
| Results activity | `آخر نشاط {datetime}` / `لا يوجد نشاط بعد.` |
| Read-only notice | `عرض فقط — لا يوجد إرسال أو إعادة إرسال يدوي.` |
| Delivery note | `قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط.` |

### 9.2 Card titles and field labels

`نص الرسالة` · `الوجهة` · `الحالة` · `مراجع المزوّد` · `المحاولات` · `حمولة استجابة المزوّد (منقّحة)` · `تحتاج مراجعة ({n})`

| Field | Label |
|---|---|
| Guardian | `ولي الأمر` |
| Phone | `الهاتف` |
| Campaign | `الحملة` |
| Amount | `المبلغ` |
| Channel | `القناة` |
| Internal status | `الحالة الداخلية` |
| Submission time | `وقت الإرسال إلى المزوّد` |
| Delivery confirmation | `تأكيد التسليم` |
| Raw provider status | `حالة المزوّد (كما وردت)` |
| Provider message id | `معرّف رسالة المزوّد` |
| Provider request id | `معرّف طلب المزوّد` |
| Attempt count | `عدد المحاولات` |
| Next attempt | `المحاولة التالية` |
| Last error | `آخر خطأ` |
| Created | `أُنشئت` |
| Updated | `آخر تحديث` |

### 9.3 States and absence copy

| Slot | Copy |
|---|---|
| No delivery confirmation | `لم يصل تأكيد تسليم.` |
| No submission yet | `لم تُرسل إلى المزوّد بعد.` |
| No error | `لا يوجد خطأ مسجّل.` |
| No payload | `لا توجد حمولة مسجّلة.` |
| Payload privacy note | `أُزيلت الحقول الحساسة قبل الحفظ. لا تُعرض مفاتيح الوصول ولا نص الطلب الكامل.` |
| No scheduled retry | `لا توجد محاولة مجدولة.` |
| Retry explainer | `تُعاد المحاولة تلقائيًا وفق سياسة المحاولات. لا تحتاج إلى إجراء.` |
| No automatic delivery updates | `لا يصل تحديث تلقائي لحالة التسليم في هذه المرحلة. تبقى الحالة كما وصلت آخر مرة.` |
| No-resend reason (`unknown`) | `لا تُعاد الرسالة تلقائيًا. قد تكون وصلت، وإعادة إرسالها قد ترسل نسخة ثانية.` |
| No-resend block (`failed`) | `لا يوجد إجراء إعادة إرسال. أصلح سبب الفشل — غالبًا رقم الهاتف أو بيانات المستلم — ثم أنشئ حملة جديدة.` |
| Nothing started | `لم تبدأ معالجة الرسائل بعد. لا شيء أُرسل إلى المزوّد حتى الآن.` |
| Cancelled campaign | `أُلغيت الحملة في {datetime}. الرسائل التي لم تُعالَج أُلغيت.` |
| Copy success (phone) | `تم نسخ رقم الهاتف.` |
| Copy success (body) | `تم نسخ نص الرسالة.` |
| Copy success (id) | `تم نسخ المعرّف.` |
| Copy failure | `تعذر النسخ. حدّد النص وانسخه يدويًا.` |
| Refresh success | `حُدِّثت البيانات {time}.` |

### 9.4 Empty and error states

| Screen | Title | Description | Action |
|---|---|---|---|
| Messages — none | `لا توجد رسائل بعد` | `تُنشأ رسالة واحدة لكل مستلم عند اعتماد الحملة، وتظهر هنا بحالة «بانتظار الإرسال».` | `عرض الحملات` |
| Messages — filtered | `لا توجد رسائل مطابقة` | `جرّب حالة أخرى أو امسح البحث.` | `مسح عوامل التصفية` |
| Messages — 404 | `لم نجد هذه الرسالة` | `قد يكون الرابط قديمًا أو أن الرسالة غير متاحة لحسابك.` | `العودة إلى سجل الرسائل` |
| Messages — 403 | `لا تملك صلاحية عرض سجل الرسائل.` | — | `العودة إلى الرئيسية` |
| Results — draft/awaiting | `لم تُنشأ رسائل هذه الحملة بعد` | `تُنشأ الرسائل عند اعتماد الحملة.` | `عرض الحملة` |
| Results — approved, none created | `لا توجد رسائل لهذه الحملة` | `لم تُنشأ سجلات رسائل عند الاعتماد.` | `عرض الحملة` |
| Results — 404 | `لم نجد هذه الحملة` | `قد يكون الرابط قديمًا أو أن الحملة غير متاحة لحسابك.` | `العودة إلى الحملات` |
| Results — messages 403 | `لا تملك صلاحية عرض تفاصيل الرسائل.` | `تظهر الأعداد فقط.` | `العودة إلى الحملات` |
| Load error (list) | `تعذر تحميل الرسائل.` | `{API message_ar}` | `إعادة المحاولة` |
| Load error (detail) | `تعذر تحميل الرسالة.` | `{API message_ar}` | `إعادة المحاولة` |
| Counts error | `تعذر تحميل أعداد الرسائل.` | `{API message_ar}` | `إعادة المحاولة` |
| Session | `انتهت الجلسة. سجّل الدخول مرة أخرى.` | — | `تسجيل الدخول` |

### 9.5 Count labels and agreement

Label-first, always: `الإجمالي: 4` · `لم تبدأ: 0` · `لم يصل تأكيد التسليم: 1` · `تم التسليم: 2` · `تحتاج مراجعة: 1` · `ملغاة: 0`.

The pager range stays noun-free (`عرض 1–20 من 47`), which is grammatically safe at every count. Where a counted noun is unavoidable — the `TablePager` zero line, empty states, panel rows — pluralise via `Intl.PluralRules("ar")`: 0 `لا رسائل`, 1 `رسالة واحدة`, 2 `رسالتان`, 3–10 `رسائل`, 11+ `رسالة`.

Forbidden: `4 رسالة`, `1 رسائل`, `2 رسائل مطابقة` where `رسالتان` is correct.

### 9.6 Words to avoid

| Don't | Use |
|---|---|
| `تم الإرسال` as a state | the specific state: `قبلها المزوّد`, `في طابور المزوّد`, `تم التسليم` |
| `تم التسليم` for anything except `delivered` | `لم يصل تأكيد التسليم` |
| `مسلَّمة` / `نجحت` / `مكتملة بنجاح` | `اكتملت المعالجة` |
| `فشل` for `unknown` | `نتيجة غير معروفة` |
| `قيد التسليم` / `في الطريق` / `قريبًا` | the record's own state |
| `مشكلة في الخادم` | the specific failure + next step |
| `لا توجد بيانات` | name what is missing + the next step |
| `خطأ` alone on a status | the state label + the error summary |
| `إعادة المحاولة` for a resend | `إعادة المحاولة` only for a failed **page request** |
| `تحديث الحالة` | `تحديث` (the page refreshes; it does not change the provider's state) |
| English codes as primary text (`PROVIDER_ACCEPTED`) | Arabic label; raw value in 10–11px muted `<bdi>` inside the detail card |
| `WhatsApp` (any spelling) | never displayed; SMS only in this slice |

---

## 10. Anti-patterns (reject in implementation review)

- Any send, resend, test-send, "إرسال الآن", "إعادة الإرسال", "تجاهل", or status-override control — enabled, disabled, or behind a menu.
- A disabled resend button with a "قريبًا" tooltip. A disabled capability still promises a capability.
- Green or a checkmark for `provider_accepted`, `queued_by_provider`, `submitting`, or `completed_with_errors`.
- `unknown` rendered as `failed` (red) or as delivered.
- A delivery percentage, progress bar, donut, ratio sentence, delivery rate, ETA, or "آخر تحديث قبل 3 دقائق" ticking label.
- `تم التسليم` derived from `submitted_at`, `sent`, or any provider string other than an explicit delivered state.
- Showing `send_jobs` status, lease, heartbeat, `locked_by`, or attempt denominators (`2 من 3`).
- Polling, `setInterval` refreshes, a spinner beside a status pill, or an animated status dot.
- A toast for a load error.
- An empty state rendered before the request resolves; `0` as a loading placeholder; a currency symbol fallback.
- Summing money across rows, converting currencies, or printing a total on the results screen.
- `Number()` / `parseFloat` on an API money string.
- Truncating the only copy of a provider id, or making the full value reachable only by `title` attribute.
- Rendering the frozen body as an editable or read-only `<textarea>`.
- Re-interpolating the frozen body client-side, highlighting variables, or wrapping individual numbers in `<bdi>` inside the sentence.
- Hiding the payload privacy note, the delivery note, or the no-resend block behind a tooltip/accordion.
- Duplicating the delivery note on one screen (once, in one place).
- Fetching all messages and filtering/paginating client-side to avoid a real pager.
- A `tel:` or `sms:` link on a phone number.
- Two different Arabic labels for one status in two places.
- English enum values as user-facing text.
- Reordering detail cards with CSS `order` so the DOM and visual order diverge.
- Any change to `AppShell`, `PageHeader`, or the primitives' styling as part of this lane.

---

## 11. Dependencies, gaps, assumptions

**Resolution note (4 November 2026):** `MessageSummary` now includes `next_attempt_at`; `MessageDetail` includes `next_attempt_at` and `provider_request_id`. The campaign status map and D1 read-only copy are implemented additively. D2/D3/D4 are resolved; D1 is implemented in the campaign lane; the remaining gaps are informational.

| ID | Gap | Impact | Handling in this spec |
|---|---|---|---|
| **D1** | M3's `NoSendNotice` says «الإرسال غير مفعّل في هذه المرحلة — لا تُسلَّم أي رسالة» and the approved detail says «لم تُرسل أي رسالة» permanently | Both become false as soon as the worker moves a message. The campaign detail would contradict `/messages` and `/campaigns/[id]/results` | **Outside this lane's write scope, required before sign-off:** on an `approved` campaign with no message past `pending`, keep the M3 copy; once `sending`/`completed*`, replace it with `بدأت معالجة الرسائل. راجع نتائج الرسائل لمعرفة الحالات المؤكدة.` and add the `نتائج الرسائل` link. Do not silently keep the old sentence |
| **D2** | `MessageSummary` has no `next_attempt_at` or `attempt_count` | The list cannot show "retry scheduled" honestly | Ask backend to add `next_attempt_at` (additive) to the summary. Until then the list shows the §2.1 second line only; it never infers a retry |
| **D3** | `MessageDetail` delta is documented as body + payload + attempts + next retry; the brief requires a provider **request** id | The «معرّف طلب المزوّد» row would have no data | Require `provider_request_id` on `MessageDetail`. If absent, render `—`, no placeholder text |
| **D4** | The campaign status enum in the app is 4 values (`draft`, `awaiting_approval`, `approved`, `cancelled`); M4 derives `sending`, `completed`, `completed_with_errors`, `failed` | The results header cannot render a campaign status, and `/campaigns` would fall back to `—` | Contract fix in the backend lane; the frontend `CAMPAIGN_STATUS_META`/`CampaignStatus` extension is additive (§2.3). No campaign screen restructuring |
| **D5** | `GET /campaigns/{id}/results` returns counts, not message rows | The per-message table needs a second call | Compose with `GET /messages?campaign_id=`; never invent a `messages[]` on results; never reconcile the two numbers client-side (§5.6) |
| **D6** | The boundary between `approved` and `sending` is not defined: derivation runs "after each terminal change", so a freshly approved campaign with all-pending messages may stay `approved` until the first message finishes | The results header could flip from معتمدة to قيد المعالجة mid-read | Show the API value as-is; the meaning line for `approved` is `لم تبدأ معالجة الرسائل` and for `sending` is `بدأت معالجة الرسائل ولم تنتهِ` — both are true whenever the API returns them. Ask the backend to state the precedence explicitly |
| **D7** | No webhook or status polling; delivery confirmation may never arrive for a `provider_accepted` message | A message can sit in amber indefinitely | Copy states it (§1.5 #2). No ETA, no auto-update, no "جارٍ التحقق" |
| **D8** | `MESSAGING_MAX_ATTEMPTS` is not returned | Printing "2 من 3" would be fabricated | Never print a denominator (§4.8) |
| **D9** | Message ordering is unspecified | The pager could appear non-monotonic | Assume `created_at desc` (matches the campaign list convention); the UI never re-sorts a page |
| **D10** | `q` matching semantics (substring? phone normalisation?) are unspecified | Search could look broken for `+963` vs `0993` | The UI claims only what the placeholder says. Empty result copy is `لا توجد رسائل مطابقة`, never `الرقم غير موجود` |
| **D11** | `delivery_note_ar` may be absent | The honesty sentence could vanish | Constant fallback with the identical string (§5.4) |
| **D12** | No per-status counts endpoint for `/messages` | Filter chips with counts would need 8 probes | Status is a `<select>`, no counts, no per-status numbers on the list. The pager carries the only total |
| **D13** | Campaign picker needs a list of campaigns; `/campaigns` pages at 20 | A campaign outside the first 50 is not selectable | Fetch `page_size=50`; if the URL's `campaign_id` is absent from it, fetch that campaign for its name (§3.3). Note the limitation rather than inventing a search endpoint |
| **D14** | Redaction quality is a backend concern | A key could leak into `provider_payload_redacted` | The UI displays the payload as returned. If secrets are suspected, that is a backend defect to fix at the source, not to hide in CSS |

**Assumptions to confirm with the backend lane:**

1. `GET /messages` returns items newest-first and `total` for the whole filtered set, not the page.
2. `status` accepts exactly the eight contract values; an unknown value is rejected with 422 rather than silently ignored.
3. `provider_payload_redacted` is always an object (`{}` when empty), never `null`/a string.
4. `message_body_snapshot` is returned on detail only, and is the exact text handed to the provider.
5. `attempt_count` is the number of attempts started, not completed.

---

## 12. Component inventory for the frontend lane

| Path | Responsibility |
|---|---|
| `app/messages/page.tsx` | reads `searchParams` (`page`, `campaign_id`, `status`, `q`), validates, renders the list view |
| `app/messages/[id]/page.tsx` + `layout.tsx` | detail route + title |
| `app/campaigns/[id]/results/page.tsx` + `layout.tsx` | results route + title |
| `components/messages/MessagesListView.tsx` | fetch list, filter wiring, pager, states |
| `components/messages/MessagesFilterBar.tsx` | search/select/clear, URL sync, no fetch |
| `components/messages/MessageTable.tsx` | 8 columns at 1440, 6 at 1024, stacked list at ≤767 |
| `components/messages/MessageStatusPill.tsx` | `status → {label, tone}` |
| `components/messages/MessageStatusCell.tsx` | pill + §2.1 second line (shared by list and results) |
| `components/messages/HistoryNotice.tsx` | the read-only line |
| `components/messages/MessageDetailView.tsx` | fetch detail, compose cards, states |
| `components/messages/MessageBodyCard.tsx` | frozen body + copy + provenance |
| `components/messages/MessageDestinationCard.tsx` | guardian/phone/campaign/amount/channel |
| `components/messages/MessageStatusCard.tsx` | internal pill, delivery row, one explainer |
| `components/messages/ProviderReferences.tsx` | message id, request id, copy |
| `components/messages/RedactedPayload.tsx` | `<details>`/`<pre>`, empty state |
| `components/messages/AttemptsCard.tsx` | attempts, next retry, last error, no-resend block |
| `components/messages/message-format.ts` | `MESSAGE_STATUS_META`, groups, `formatAttemptLine`, `statusExplainer`, `filterGroups` |
| `components/campaigns/CampaignResultsView.tsx` | fetch results + messages, header, composition |
| `components/campaigns/ResultsCounts.tsx` | 6-cell `<dl>` with composition lines |
| `components/campaigns/ResultsReviewPanel.tsx` | failed/unknown counts + links |
| `components/campaigns/CampaignStatusPill.tsx` | **map extension only** |
| `lib/api.ts` | `MessageStatus`, `MessageSummary`, `MessageDetail`, `CampaignResults`, `listMessages`, `getMessage`, `getCampaignResults`, `CampaignStatus` extension |

Conventions:

- Server data in, callbacks out. No `fetch` inside presentational components.
- Every button gets `type="button"`; every link is a real `<a>`/`<Link>`.
- Money only via `formatDecimalString`; dates only via `formatDateTime`; counts only via `formatNumber`.
- All colours via CSS variables; all spacing logical.
- `message-format.ts` is the single source of labels. No Arabic status string is typed inside a component.

---

## 13. Top design decisions

1. **Green is never a delivery claim it cannot back; everything unconfirmed is amber.** Provider acceptance, queuing, submission, and retry waiting all read as "not confirmed yet", the same language M3 established with «بانتظار الاعتماد». `unknown` is amber, not red, because red is a claim the record cannot support. The only greens on these screens are `تم التسليم`, `معتمدة`, and `اكتملت المعالجة` — the last two label a finished step without implying arrival.
2. **Counts, never ratios.** The results screen renders grouped counts with their composition (`قبلها المزوّد 1 · في الطابور 0`) instead of a progress bar or a delivery percentage. A bar invites the one sentence this product must never say.
3. **The absence of resend is explained where the button would be.** Each message state gets one truthful line — for `unknown` it says a second copy may duplicate a message that already arrived — and the payload, delivery note, and no-resend block are never collapsed into tooltips.
4. **The results screen composes two honest endpoints instead of inventing one.** Counts come from `/campaigns/{id}/results`; rows come from `/messages?campaign_id=`. The page says which is which ("هذه الصفحة تعرض 4 من 4… الأعداد أعلاه لكل رسائل الحملة") and never reconciles them in the client.
5. **The raw provider vocabulary is data, not UI language.** `provider_status`, job states, lease fields, and attempt caps stay in the detail card (or not at all); the interface speaks one closed set of eight Arabic message states, and the same label is used in the table, the filter, the detail, and the results.

---

## 14. Verification checklist for the frontend lane

Design-visible checks this spec is meant to support. Not assigned to this lane; listed so the implementation can be reviewed against it.

- [ ] 1440 / 1024 / 768 captures of the list, the detail, and the results screen, plus list empty/loading/error and a detail `unknown`.
- [ ] Zero send/resend controls in any state, including disabled ones; zero `tel:`/`sms:` links.
- [ ] Zero delivery claims: no green, no «تم التسليم», no percentage for `provider_accepted`, `queued_by_provider`, `submitting`, or `unknown`.
- [ ] One Arabic label per status, identical in table, filter, detail, and results.
- [ ] Filter state survives refresh and back/forward; clearing restores `/messages`.
- [ ] Pager and `total` agree; campaign-wide counts and the visible page are labelled as different scopes; no client-side summation; no empty state before resolve.
- [ ] `unknown` and `failed` messages are reachable from the results panel in one click.
- [ ] Payload is collapsed by default, keyboard operable, empty-state handled, and never shows a key.
- [ ] Every control ≥44×44, focus visible, and reachable in the §8.2 order.
- [ ] Campaign status map extended (§2.3) and the M3 approved-detail copy reconciled (D1).
