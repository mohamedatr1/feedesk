# M1 Design & Accessibility Review

**Scope:** M1 UI only (login, forced password change, shell, dashboard, settings, users, audit).
**Reference:** `FeeDesk-Dashboard.png` (approved visual direction).
**Reviewed:** 3 November 2026, ~20:15–20:30 (local).
**Method:** visual comparison of the six screenshots in `.local/`, source review of `apps/web/**`, token review of `docs/design/tokens.css`, contrast ratios computed from the token hex values (WCAG 2.x relative luminance).
**Not tested:** live hover/focus states, error banners, the new dialogs, 1024/768 renders, screen-reader output, browser zoom, production build. Findings derived from CSS/layout are marked **[C]**; findings seen in a screenshot are marked **[S]**; findings inferred from layout math but not measured are marked **[I]**.

**Post-fix captures (P1 implementation):** `.local/qa-login-1440.png`, `qa-dashboard-1440.png`, `qa-dashboard-1024.png`, `qa-settings-1440.png`, `qa-users-1440.png`, `qa-user-edit-1440.png`, `qa-audit-1440.png`, `qa-change-password-1440.png`, `qa-login-768.png`. These were captured from the production build with a temporary local QA admin, which was removed afterward.

---

## 0. Evidence hygiene (read this first)

The screenshots predate the code that is currently in the tree. Do not sign off the visual direction against them.

| Artifact | Timestamp | Status |
|---|---|---|
| `dashboard.png` | 19:26 | Shell/topbar captured before `AppShell.tsx` was last changed (19:34) and before `globals.css` (20:18) |
| `users.png` | 19:26 | **Stale.** `settings/users/page.tsx` was rewritten at 20:25 (confirm/edit dialogs, three row actions, pills, captions) |
| `audit.png` | 19:26 | Page code unchanged (19:18), but the date format in the shot predates `lib/api.ts` (20:18). The shot shows `2026/11/03`; current `formatDateTime` produces `03‏/11‏/2026` |
| `settings.png` | 19:26 | Representative (page code 19:18; tokens unchanged) |
| `login.png` | 19:21 | Representative (page code 19:17) |
| `change-password.png` | 19:37 | Representative (page code 19:17) |
| `login-debug.png` | — | Byte-identical to `dashboard.png` (same MD5), not a login capture |

All screenshots show the black **Next.js dev indicator** (bottom-left "N"). Re-capture from `next build && next start` before design sign-off, and include 1440, 1024, 768, and 375 widths plus the users dialogs.

The users screen is being changed while this review was written. Treat the users findings as applying to the 20:25 state; the new `Dialog`/`ConfirmDialog`/`UserEditDialog` are reviewed from source only.

---

## 1. Verdict

The direction is right and the foundation is real: the calm cream/green palette, the RTL shell, the tabular data language, and the honest "provider not activated" messaging all match the approved board. What is missing is **scale** (type and spacing are compressed relative to the mockup), **finish** (focus/border contrast, loading states, empty-state consistency), and a handful of **navigation/permission contradictions** that a user will hit in the first five minutes.

- **P0 blockers: none.** No flow is broken and no value is presented as a different value than it is.
- **P1 (fix before M1 sign-off): 10 items**, three of which are WCAG 2.2 AA failures (four success criteria: 1.4.3, 1.4.11, 2.4.1, 2.4.2).
- **P2 (fix during M2 polish): 15 items.**

Design-quality summary against the approved board:

| Dimension | Approved board | Current M1 | Verdict |
|---|---|---|---|
| Page hierarchy | H1 ~36px, section ~18px, KPI ~34px | 30 / 14 / 30 | Under-scaled; two loud levels only |
| Spacing | airy, ~24px card insets | 20px cards, 20px rhythm | Slightly tight but consistent |
| Typography | IBM Plex Sans Arabic | Same | Match (Latin wordmark excepted) |
| Color | cream + deep olive green | Same tokens | Match |
| RTL | right sidebar, first column right | Same | Match; 2 nits |
| Tables | 13px, tinted header, dotted pills | 13px, tinted header, no dots | Close |
| Status pills | dot + label | label only | Partial (not a11y-failing; text carries meaning) |
| Empty states | populated in board | calm and specific | Good content, two implementations |
| Topbar/sidebar balance | 80px bar, 220px rail, identity + utilities clustered | 72px bar, 240px rail, two islands | Diverges |
| Brand | vertical lockup, high-contrast serif | horizontal lockup, Georgia/Times | Diverges |

---

## 2. What works

1. **RTL is structural, not cosmetic.** `html dir="rtl" lang="ar"`, sidebar on the right, first table column on the right, labels above fields, right-aligned numeric cells, and Latin codes isolated with `dir="ltr"`. This is the part most RTL builds get wrong, and it is right here.
2. **One palette, one radius, one shadow.** Every screen reads as the same product. The deep olive brand carries white text at 9.43:1 and sits calmly against the cream page.
3. **Pill contrast is solid.** All four tones pass AA for 12px text: green 6.71:1, red 6.57:1, amber 5.37:1, neutral 5.67:1. The danger button is 5.44:1.
4. **Honest financial posture.** No fake deltas, no invented counts, and the provider warning ("لم يتم اعتماد اسم المرسل بعد…") is accurate to the G0 blocker. The empty states are specific ("ستظهر هنا الكشوف التي تحتاج إلى مراجعة…") rather than "لا توجد بيانات".
5. **The dialog implementation is above average** (`components/Dialog.tsx`): native `<dialog>` + `showModal`, `aria-labelledby`/`aria-describedby`, focus restoration, Esc guarded while busy, and the safe action ("إلغاء") is the autofocus target in `ConfirmDialog`.
6. **The users screen has caught up on semantics** (in flight): `<caption class="sr-only">`, `scope="col"`, `sr-only` action header, per-row `aria-label`s that include the username, `role="alert"` for errors and `role="status"` for success, and self-deactivation blocked.
7. **Settings handles the staff role explicitly** — fields disabled, save hidden, "العرض فقط — التعديل متاح لمدير النظام."
8. **The login screen is the strongest screen visually.** The split card, the soft circles, the restrained brand panel, and the cream tip box are a confident interpretation of the board's atmosphere.

---

## 3. Issues

Legend: **P0** blocks a demo flow or misstates money/status · **P1** WCAG AA failure or a broken/contradictory path · **P2** polish, consistency, or craft.

### P0

None found in the states inspected.

### P1

| ID | Area | Where | Issue | Fix |
|---|---|---|---|---|
| **P1-1** | Contrast & focus | `app/globals.css` (`:focus-visible`, `.fd-input`), `components/Logo.tsx`, `app/login/page.tsx` | Three problems. (a) `--fd-ink-subtle` on `--fd-sidebar` = **4.39:1** — the 10px logo tagline and the 11px `v0.1.0` fail 1.4.3. (b) `text-white/55` on brand = **4.13:1** — the login footnote fails 1.4.3. (c) `.fd-input` sets `outline-none`, so keyboard focus on every field relies only on a 1px border colour change; the designed `focus:ring` uses `--fd-brand-soft` (**1.15:1**) and is invisible. Focus is technically visible but fragile at 100% zoom (2.4.7 at risk). The global ring itself is fine: with `outline-offset: 2px` it sits on the cream surface, not on the brand fill. | Use `--fd-ink-muted` (5.46:1) for sidebar metadata; `white/70` (5.59:1) for the login footnote; restore a real 2px `:focus-visible` outline on `.fd-input`/`select` and drop the invisible soft ring (CSS in §8.2). |
| **P1-2** | Non-text contrast | `.fd-input` border `--fd-line-strong` (#d6d1c4) on `--fd-surface` (#fdfcfa) | **1.49:1.** The input boundary is the only thing identifying the control. WCAG 1.4.11 requires 3:1. | Add `--fd-line-input: #96907f` (**3.11:1**) for form controls only; keep `--fd-line` for cards. |
| **P1-3** | Orientation | `app/layout.tsx`; `AppShell` | One document title for every route ("FeeDesk — إدارة الأقساط"). WCAG 2.4.2. Also **no skip link**, so every page begins with 6 nav links + 2 topbar controls (bell, logout) before content. WCAG 2.4.1. | Add a `metadata` layout per route (`app/settings/layout.tsx`, `app/audit/layout.tsx`, …) and a visible-on-focus "تخطَّ إلى المحتوى" link to `<main id="main">`. |
| **P1-4** | Perceived performance / focus loss | `components/Protected.tsx` | Every page wraps itself in `Protected`, which fetches `/auth/me` on mount and returns a full-screen skeleton while `me` is null. Client-side navigation therefore **unmounts the whole shell on every click** and replaces it with a centred skeleton, then restores it. | Move the session fetch into a route-group layout (or a module-level cached `useSession()`), render `AppShell` immediately, and skeleton only the page body. |
| **P1-5** | Loading truth | `app/audit/page.tsx`; `app/page.tsx` | Audit has no loading state: `events=[]` while fetching, so it briefly renders **"لا توجد أحداث بعد"** and a subtitle with `0 حدث`. The dashboard renders four **0** KPIs before settings load. These are false empty states on a financial product. | Add `loading` gates: skeleton rows/values, empty state only after resolve, "—" for unknown amounts and counts. |
| **P1-6** | Money/format integrity | `app/page.tsx` (currency symbol fallback); `app/settings/page.tsx`; `lib/api.ts` `formatDate`/`formatDateTime` | The mockup's **sample** symbol `د.س` is used as a runtime fallback — directly against `screen-gap.md` ("It is configuration, not a constant"). If settings fail, the dashboard shows an amount in a fabricated currency. Separately, `locale` and `timezone` are free-text settings that are never read by the date formatters (they are hardcoded `ar-SY-u-nu-latn`), so two visible controls do nothing and can be set to invalid values. | Never fall back to a currency symbol; show "—" until settings resolve. Read `locale`/`timezone` in the formatters (with a try/catch), or render those two fields read-only with "قريبًا". |
| **P1-7** | Permissions vs navigation | `AppShell` `NAV`; `app/page.tsx` "عرض الكل" | Two contradictions: (a) **الإعدادات is `adminOnly`** in the sidebar, but `/settings` is served to staff read-only — staff have a page they cannot reach; (b) the dashboard's activity card links **"عرض الكل" → `/audit`** for every role, but `/audit` is `requireAdmin` — staff land on "غير مصرح". | Remove `adminOnly` from الإعدادات (keep the read-only footer). Render the activity link only for admins (or drop it while the table is empty). |
| **P1-8** | Login at ≤1023px | `app/login/page.tsx` | The brand panel is the first grid child, so in RTL it occupies the reading start (right) and the form is pushed to the left; below `md` it stacks **above** the form. At 768 the two-column split leaves a 254px-wide form column. On a 390px phone the brand block is ~380px tall, so the submit button is below the fold. | Keep the form at the start: swap the sections and set `lg:grid-cols-[0.95fr_1.05fr]`. Hide the brand panel below `lg`, and put a compact logo lockup above the form instead. |
| **P1-9** | Forced-password screen | `app/change-password/page.tsx` | Behind a blocking gate: the 12-character rule is only revealed **after** a failed submit; there is no way to sign out; the page never names the account; and the heading (18px) is the smallest H1 in the product. | Add persistent help "12 حرفًا على الأقل", a show/hide toggle, a secondary "تسجيل الخروج" link, the username, and a 24px heading. |
| **P1-10** | Audit readiness | `app/audit/page.tsx` | The screen exists to answer *who did what*, but there is no **actor** column (the API exposes `actor_user_id`), actions are raw codes (`auth.login`), entities are raw English (`user`), and IDs are 8-char UUID fragments with no disclosure. For an admin this reads as a developer log. | Add an actor column (username or short ID); map actions/entities to Arabic with the raw code as a muted secondary line; expose the full ID via a details row or copy control (not a title tooltip); see the copy table in §7. |

### P2

| ID | Area | Where | Issue | Fix |
|---|---|---|---|---|
| P2-1 | KPI anatomy | `components/StatCard.tsx` | Icons are 17px in pale 36px tiles (the board uses ~22px line icons, unboxed); the currency symbol renders at the same 30px/700 as the number; the sparkline is a **decorative squiggle identical on all four cards**, in green even on neutral cards. It implies trend data that does not exist. | Unbox the icon at 20–22px, split the unit (`30px` number + `16px` symbol, `font-medium`, muted), and **remove the sparkline** until daily snapshots exist. |
| P2-2 | Type scale | `PageHeader`, section headers | H1 30px, card titles 14px. The board is ~36/18. Card titles do not read as sections. | H1 32–34, section 16–17, card title 15–16; raise the dashboard card padding to 24px. |
| P2-3 | Section headers | `app/page.tsx` | 4×16 brand bar is fine, but "عرض الكل" has no direction cue (the board uses "← عرض الكل"); both cards link to different targets while one label says "عرض الكل" over a queue that includes statements, campaigns, and messages. | 18px bar, 16px title, arrow icon; rename to "عرض الكشوف" or point to a combined queue when it exists. |
| P2-4 | Pills | `components/StatusPill.tsx` | No status dot; the board uses dot + label for fast scanning. | Add `<span aria-hidden class="h-1.5 w-1.5 rounded-full bg-current" />`. |
| P2-5 | Empty states | `app/page.tsx` activity card | Bespoke markup (icon + one line) instead of `EmptyState`; no action; the card header still offers a link. | Use `EmptyState` with a title and a primary action ("رفع كشوف جديدة") so the empty dashboard has a next step. |
| P2-6 | Tables | `app/page.tsx`, `app/audit/page.tsx` | No `<caption>`/`aria-labelledby`, no `scope="col"` (users already has both); audit uses four equal 25% columns; date cells can wrap; no row hover. | Add caption/scope, natural column widths, `whitespace-nowrap` on dates/IDs, `tabular-nums`, and `hover:bg-[var(--fd-surface-alt)]`. |
| P2-7 | Provider card | `app/page.tsx` | "العملة: SYP — د.س" is settings data, not provider status; "SMS محلي" is mixed script; the warning has **no next step**. | Drop the currency row; write "رسائل SMS محلية"; add a "عرض متطلبات التفعيل" link (or "قريبًا" for M2). |
| P2-8 | Audit footer | `app/audit/page.tsx` | "عرض أحدث 25 حدثًا" is static, and a lone `History` icon sits at the far left looking like a refresh button but is not interactive. | Show "عرض 8 من 27"; replace the icon with a real labelled refresh button (44px) or remove it. |
| P2-9 | Sidebar rail | `AppShell` + `globals.css` ≤1024 | Labels are `display:none`, so the accessible name depends on `title`; at exactly 1024px the logo is `lg:justify-start` while the rail is 76px, so it is off-centre; `title` tooltips do not exist on touch. | Use a visually-hidden label (CSS in §8) plus `aria-label={item.label}`; centre the mark at ≤1024. |
| P2-10 | Sidebar finish | `AppShell` | 240px rail with 6 items and ~600px of empty height; the version line is 11px and buried at the bottom. The watercolour illustration is still missing (known). | 220–232px rail, 8px nav gaps, illustration at 12–18% opacity (`aria-hidden`, hidden <1024), footer block with version + help. |
| P2-11 | Brand | `components/Logo.tsx` | "FeeDesk" uses `font-serif`, i.e. Georgia/Times — generic next to the board's high-contrast wordmark. The lockup is horizontal while the board is vertical; the 10px tagline can swap from "إدارة الأقساط" to the school name asynchronously. | Load a display serif for the Latin wordmark only (`--fd-font-display`), keep the school name stable, raise the tagline to 11px/4.5:1. |
| P2-12 | Login details | `app/login/page.tsx` | The user/lock icons sit at the right while the LTR text starts at the left, leaving the icon stranded; no password reveal. | Move icons to the inline-end for LTR fields (`left-3` + `pl-9`); add a reveal toggle. |
| P2-13 | Change-password alignment | `app/change-password/page.tsx` | The 40px amber badge is the first flex child, so the title/subtitle are inset 52px from the form labels — the heading does not align with the fields. Amber also reads as warning. | Absolute/flex-end badge at 36px, or stack it above the title; use brand-soft instead of amber. |
| P2-14 | Users details | `app/settings/users/page.tsx` | (a) Create form is **above** the list and only goes two-column at `2xl` (1536) — at 1440 the admin scrolls past four fields to reach the table. (b) `job_title` defaults to the literal "موظف إداري" and is saved silently. (c) "أنت" pill is amber (warning semantics). (d) The temp-password banner is at the top; on a long list it can be off-screen with no focus move and no copy button. | Make "إضافة مستخدم" a dialog and give the table the full width; empty `job_title` + placeholder; neutral tone for "أنت"; focus/scroll the banner (`tabIndex={-1}`) and add "نسخ". |
| P2-15 | Motion | `globals.css` `.fd-skeleton` | `animate-pulse` runs regardless of `prefers-reduced-motion`. | Add a `@media (prefers-reduced-motion: reduce)` block that disables the pulse and shortens transitions. |

---

## 4. Screen notes

### 4.1 App shell + dashboard

- **Topbar**: current code places date + bell at the inline-start and identity + avatar + logout at the inline-end. At 1440 that splits the bar into two islands with most of its width empty between them. The approved board keeps identity and utilities together toward the inline-end and leaves the start for context. Recommend one group at the inline-end and the **school name** (today a 10px sidebar tagline) at the start — this simultaneously fixes the dead space, the unreadable tagline, and the async brand-text swap. **[C]** *(the screenshot's placement predates the current shell — verify in a fresh capture)*.
- **Logout**: a bare 36px icon next to the avatar signs out immediately with no confirmation. The board shows a user block with a chevron. Recommend a small user menu containing "تسجيل الخروج", which also removes the accidental-logout risk.
- **Notification bell**: focusable, no action. Either remove it for M1 or mark it "قريبًا".
- **"رفع كشوف جديدة"** is the loudest element on the home screen and lands on "قيد التنفيذ". Acceptable for M1, but it should be disabled with a "قريبًا" tag until the flow exists, otherwise the first click reads as a failure.
- **KPI row**: structurally close to the board (label at start, icon at end, value, hint), but the value dominates four zeros and the fake sparkline suggests data. In an empty state, "—" plus the hint is more honest than "0".
- **Provider card**: the amber block is the right pattern (icon + text, 5.37:1). It duplicates the pill's message, which is fine; what is missing is an action.
- **Activity table**: the empty row sits inside `<tbody>` with a different treatment from `EmptyState`. The header is worth keeping; the body should use the shared component.

### 4.2 Login

- The brand panel is beautiful but occupies the RTL reading start; the first fixation is a promise, not the task. Form at the start is the conventional and faster pattern.
- The 768px two-column split is the weak point (254px form column). Details in §6.
- Error handling is a single `role="alert"` banner after the fields; add `aria-invalid`/`aria-describedby` when the error belongs to a field, and keep focus on the form.
- No reveal toggle and no Caps-Lock hint for Latin passwords in an Arabic UI.

### 4.3 Forced password change

- Traps users at a blocking step without the rule, without a reveal, without a way out, and without naming the account. The 18px heading makes a mandatory security step look like a footnote.
- The lock badge in amber reads as "warning" rather than "security".
- No success confirmation after the redirect.

### 4.4 Settings

- The page is a **developer console** in places: `SYP`, `ar-SY`, `Asia/Damascus` are editable free text. A school admin can set an invalid locale/timezone; nothing validates it, and nothing uses it (P1-6).
- "رمز العرض" and "حد الدفعة" are ambiguous without examples/units.
- Staff see disabled inputs (exempt from contrast, but low-contrast and not selectable). Consider read-only text rows instead of disabled controls.
- Error and success share `role="status"`; errors should be `role="alert"` (users already does this).
- The staff-facing permission contradiction (sidebar hides Settings, route allows it) is the most visible bug on this screen.

### 4.5 Users

- The 20:25 rewrite is a clear improvement (captions, scope, per-row labels, dialogs, loading row, self-guard).
- The layout is now the problem: two columns only at ≥1536, form above the table, and a 680px min-width table. At 1440 (the board width) the list is buried; at 768 the table scrolls 20px inside its card.
- The temp password is a security-critical, show-once value in a banner at the top of a scrolling page.

### 4.6 Audit

- The page reads as `auth.login / user / beabeff4` — accurate data, wrong audience. The fix is a presentation layer, not new API surface (except actor names).
- Loading = false empty (P1-5).
- Date format is ambiguous (`03/11/2026` after the latest change; `2026/11/03` in the capture). The board uses `2025-08-16 14:32`; adopt it.

---

## 5. RTL behaviour

| Check | Result |
|---|---|
| `html dir="rtl" lang="ar"` | Pass |
| Sidebar on the right, border on the content side (`border-l`) | Pass |
| Table starts on the right; headers and cells agree | Pass |
| Labels above fields, right-aligned | Pass |
| Latin values isolated (`dir="ltr"` on username/ID/timezone fields) | Pass in forms and audit; the topbar username is not explicitly isolated (pure Latin runs survive, but punctuation-heavy handles can reorder — wrap in `<bdi>`). Audit sets `dir="ltr"` on the whole `<td>`; it works but moves the alignment intent into the cell — prefer a `<bdi>` inside a right-aligned cell |
| Currency order (`number symbol`) | Pass; but the symbol is a 30px bold sibling of the amount (P2-1) and the fallback is hardcoded (P1-6) |
| Logical properties | Mostly; `mr-2` in the temp-password banner is physical — use `ms-2` |
| Icon placement vs LTR text in login inputs | Mismatch: icon at the physical right, text starts at the physical left (P2-12) |
| Mirrored assets | No directional icons to mirror except the missing "عرض الكل" arrow |
| Arabic date + Latin digits | Pass in the topbar ("الثلاثاء، 3 تشرين الثاني 2026"); the table format should follow the board |

---

## 6. Responsive risks

Derived from the breakpoints in the source (`sm` 640, `md` 768, `lg` 1024, `xl` 1280, `2xl` 1536) and the sidebar collapse at `max-width: 1024px`. **Not visually verified.**

### 1024px

| Area | Risk |
|---|---|
| Shell | Sidebar collapses to 76px at exactly 1024 (media query), but the logo uses `lg:justify-start` (min-width 1024) → off-centre mark at the one-pixel overlap. Fix with a single breakpoint (`lg` for both) or `max-width: 1023px`. |
| KPI row | `sm:grid-cols-2` → 2×2 at ~450px each. Cards become wide and short with a 30px "0" floating. Consider 4-up at `lg` with 16px padding, or keep 2-up and drop the sparkline. |
| Dashboard row | `xl:grid-cols` is not active → the provider card spans 916px with three short rows. Use `lg` for the split or cap the stacked card's width. |
| Users | Stacked (needs 1536 for two columns): full-width 4-field form above the table. |
| Audit | 4×~229px columns: fine. |
| Settings | 2×448px: fine. |

### 768px

| Area | Risk |
|---|---|
| Login | The weakest screen: `md` kicks in at 768 and creates a 736px card split 386/350 with `p-12`, i.e. **254px inputs**. Move the split to `lg` and stack with a compact brand band. |
| Users | Table `min-w-[680px]` inside ~660px of content → 20px of hidden horizontal scroll with no affordance. |
| Users form | Full-width single column; 44px fields stacked 5-deep push the table far below. |
| Audit | 4 columns at ~165px; the date has no `whitespace-nowrap` and will wrap onto two lines, breaking row rhythm. |
| Topbar | ~640px of content in 692px — fits, but nothing is truncating, so any longer name/job title wraps in a fixed 72px bar. |
| KPI | 2×322px cards: labels fit; hints + sparkline are one line at ~246px of 282px — tight but OK. |

### 375px (not in scope, but worth recording)

- The topbar's date (~230px) + bell + identity + avatar + logout ≈ 630px inside 267px of content → page-level horizontal scroll and clipped 72px bar. WCAG 1.4.10 risk.
- The 76px sidebar takes 20% of the viewport with no labels and no way to expand.
- The login brand panel (~380px) pushes the form's submit below the fold.

**Recommendation:** treat the mobile shell as M2 work, but make the topbar safe now — hide the date and job title below `sm`, and let the identity block truncate (`min-w-0` + `truncate`).

---

## 7. Arabic copy

### 7.1 Status vocabulary (set this before M2)

| Data | Arabic | Rule |
|---|---|---|
| `internal_status=pending` | بانتظار الإرسال | not yet submitted |
| `submitted_at` set, no `delivered_at` | **تم الإرسال إلى المزوّد** | never "تم الإرسال" alone |
| `delivered_at` set | **تم التسليم** | only when a delivery event exists |
| `failed_at` set | فشل الإرسال / تحتاج متابعة | list vs detail label |
| campaign `draft` | مسودة | |
| campaign pending approval | بانتظار الاعتماد | matches the board |
| campaign sending | قيد الإرسال | |
| campaign completed | مكتملة | |
| statement `uploaded` | تم الرفع | |
| statement in review | بانتظار المراجعة | matches the board |
| statement `confirmed` | مؤكد | |
| user active / inactive | نشط / معطّل | |

Provider status strings (`provider_status`) must never be the user-facing label; show them only inside a details panel. Never infer "تم التسليم" from `sent`. Confirm the exact enum values with the API lane before wiring labels — the Arabic strings above are the contract, the DB values are illustrative.

### 7.2 Corrections

| Location | Current | Proposed | Why |
|---|---|---|---|
| Audit subtitle | `سجل غير قابل للتعديل للمهام الإدارية — 8 حدث.` | `سجل غير قابل للتعديل للمهام الإدارية. إجمالي الأحداث: 8.` | "8 حدث" is the wrong plural (3–10 → أحداث). Use `Intl.PluralRules("ar")`: 0 "لا أحداث"، 1 "حدث واحد"، 2 "حدثان"، 3–10 "أحداث"، 11+ "حدثًا". |
| Audit footer | `عرض أحدث 25 حدثًا` | `عرض 8 من 27 حدثًا` | Says what is actually on screen; keeps the cap visible. |
| Audit column | `التاريخ` | `التاريخ والوقت` | The cell shows both. |
| Audit cells | `auth.login`, `user` | `تسجيل دخول` + muted `auth.login`; `مستخدم` + muted code | Arabic-first for admins, raw code still available. |
| KPI hint | `لا توجد كشوف معلقة` | `لا توجد كشوف بانتظار المراجعة` | Matches the card label. |
| KPI hint | `لا توجد حملات معلقة` | `لا توجد حملات بانتظار الاعتماد` | Same. |
| Login tip | `كلمة المرور المؤقتة تُغيَّر عند أول دخول.` | `سيُطلب منك تغيير كلمة المرور المؤقتة عند أول دخول.` | Passive "تُغيَّر" does not say by whom. |
| Change password | (none) | `12 حرفًا على الأقل` under the new-password field | Disclose the rule before the error. |
| Settings subtitle | `بيانات المدرسة، العملة، اللغة، وحدود التشغيل.` | `بيانات المدرسة والعملة واللغة وحدود التشغيل.` | Arabic conjunction reads better than the comma run. |
| Settings label | `رمز العرض` | `رمز العملة في الواجهة` + `مثال: د.س` | "رمز العرض" is ambiguous. |
| Settings | `اللغة` = `ar-SY` | `العربية` (select; keep `ar-SY` as the value) | A locale code is not a setting a school admin should type. |
| Settings | `المنطقة الزمنية` = `Asia/Damascus` | `دمشق (Asia/Damascus)` select | Same; also prevents invalid values. |
| Settings label | `حد الدفعة` | `الحد الأقصى لكل دفعة` + `عدد الرسائل في الدفعة الواحدة` | Units are missing. |
| Provider card | `SMS محلي` | `رسائل SMS محلية` | Mixed script without a noun. |
| Provider card | `العملة — SYP — د.س` | remove | Currency is not a provider attribute. |
| Currency | `0 د.س` before settings load / on failure | `—` | Never display the sample symbol (P1-6). |
| Table dates | `03‏/11‏/2026، 8:26 م` | `2026-11-03 20:26` | Unambiguous and matches the approved board's `2025-08-16 14:32`; 24h avoids the "م/ص" bidi edges. |
| Users create | `job_title` prefilled `موظف إداري` | empty + placeholder `مثال: موظف إداري` | A default silently becomes data. |
| Users | `أنت` pill amber | neutral tone | It is identity, not a warning. |

---

## 8. Design tokens & concrete CSS

### 8.1 Tokens to add

| Token | Value | Note |
|---|---|---|
| `--fd-line-input` | `#96907f` | 3.11:1 on `--fd-surface`; inputs/selects only |
| `--fd-font-display` | display serif (e.g. Fraunces / Instrument Serif) | Latin wordmark only |
| `--fd-chart-1…3` | green/amber/neutral | only once real snapshot data exists |

### 8.2 Focus (fixes P1-1)

The global ring already works on this palette: `outline-offset: 2px` draws it on the cream surface around brand-filled buttons, so the only broken case is form controls.

```css
:focus-visible { outline: 2px solid var(--fd-brand); outline-offset: 2px; }

/* fields: keep a real outline; the 1px border alone is too quiet */
.fd-input { border-color: var(--fd-line-input); }
.fd-input:focus-visible {
  outline: 2px solid var(--fd-brand);
  outline-offset: 1px;
  border-color: var(--fd-brand);
  box-shadow: none; /* remove the 1.15:1 brand-soft ring */
}
```

### 8.3 Collapsed rail keeps its accessible name (fixes P2-9)

```css
@media (max-width: 1024px) {
  .fd-nav-label {
    position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
    overflow: hidden; clip-path: inset(50%); white-space: nowrap; border: 0;
  }
}
```

and `aria-label={item.label}` on each nav `Link` so the name never depends on `title`.

### 8.4 KPI anatomy (fixes P2-1)

```tsx
<p className="fd-stat-value mt-3 flex items-baseline gap-1.5">
  <bdi dir="ltr">{formatNumber(value)}</bdi>
  <span className="text-[16px] font-medium text-[var(--fd-ink-muted)]">{symbol}</span>
</p>
```

Icon: 20–22px, no tile, `text-[var(--fd-brand)]` (or amber for the pending cards). Remove the `svg` until snapshots exist.

### 8.5 Status pill dot (fixes P2-4)

```tsx
<span className={`fd-pill fd-pill-${tone}`}>
  <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-current" />
  {children}
</span>
```

### 8.6 Reduced motion (fixes P2-15)

```css
@media (prefers-reduced-motion: reduce) {
  .fd-skeleton { animation: none; }
  * { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
}
```

### 8.7 Visual alignment sweep (P2-2/P2-3/P2-10)

- H1 32–34px; dashboard card padding 24px; section title 16–17px with an 18px bar; "عرض الكل" with a 14px arrow.
- Topbar 80px; one group (date + bell + identity + menu) at the inline-end; school name at the inline-start.
- Sidebar 220–232px, 8px nav gaps, 20px icons, 11px tagline at `--fd-ink-muted` (5.46:1), footer block with version.
- Wordmark in a loaded display serif; keep the school name out of the 10px tagline (it can swap asynchronously).

---

## 9. Accessibility checklist (WCAG 2.2 AA)

Status: **Pass**, **Fail**, **Partial**, **n/a**. Method: source + computed contrast; no assistive-technology run.

| SC | Name | Result | Evidence / action |
|---|---|---|---|
| 1.1.1 | Non-text content | Pass | All icons `aria-hidden` or attached to a labelled control |
| 1.3.1 | Info & relationships | Partial | Tables in settings/users have caption + scope; dashboard and audit do not. Login's `<h1>` is the marketing line, the form title is `<h2>` |
| 1.3.2 | Meaningful sequence | Pass | Sidebar → topbar → main matches the visual order |
| 1.4.3 | Contrast (text) | **Fail** | `--fd-ink-subtle` on `--fd-sidebar` = **4.39:1** (logo tagline 10px, `v0.1.0` 11px); `white/55` on brand = **4.13:1** (login footnote). All other sampled pairs pass (5.37–9.43) |
| 1.4.4 | Resize text | Partial | 200% zoom works; px-only type ignores browser font-size preferences |
| 1.4.10 | Reflow | **Partial / fail at 375** | Topbar is a fixed 72px non-wrapping row (~630px of content in 267px) **[I]** |
| 1.4.11 | Non-text contrast | **Fail** | Input/select boundary **1.49:1**; card border 1.29:1 is decorative, not a control |
| 1.4.12 | Text spacing | Partial | 1.6 line-height is good; `h-10` inputs and `h-[72px]` topbar are fixed heights |
| 2.1.1 | Keyboard | Pass | Native controls; dialogs trap natively |
| 2.1.2 | No keyboard trap | Pass | Native `<dialog>` + Esc |
| 2.4.1 | Bypass blocks | **Fail** | No skip link; 8 focusables (6 nav + 2 topbar) before content |
| 2.4.2 | Page titled | **Fail** | One title for every route |
| 2.4.3 | Focus order | Pass | DOM order is logical; dialog restores focus |
| 2.4.6 | Headings & labels | Partial | Login h1/h2 inversion; change-password h1 is 18px |
| 2.4.7 | Focus visible | Partial | Global ring works on cream/brand; form fields remove the outline and rely on a 1px border change, with an invisible soft ring (P1-1) |
| 2.5.3 | Label in name | Pass | Row `aria-label`s contain the visible verb |
| 2.5.8 | Target size (min 24×24) | Pass | Buttons 32–44px; icon buttons 36px |
| 3.1.1 | Language of page | Pass | `lang="ar"` |
| 3.1.2 | Language of parts | Partial | Latin usernames/codes are not `lang="en"`; `dir="ltr"` is present in most places |
| 3.2.3 | Consistent navigation | Pass | Same shell everywhere |
| 3.3.1 | Error identification | Pass | Text errors with `role="alert"` on login/change-password; settings uses `role="status"` for errors (fix) |
| 3.3.2 | Labels or instructions | **Partial** | All fields labelled; the 12-character rule is missing until failure |
| 3.3.3 | Error suggestion | Partial | Messages explain the rule but only after submit |
| 3.3.7 | Redundant entry | Pass | `autocomplete` set on auth fields |
| 4.1.2 | Name, role, value | Pass | Nav names fall back to `title` when collapsed (fragile — P2-9) |
| 4.1.3 | Status messages | Partial | Login/change-password errors alert; users notices fixed; settings errors polite; loading not announced; audit shows a false empty state |

### Table / form semantics

- Settings/users table: **good** (caption, scope, sr-only action column, per-row labels).
- Dashboard activity and audit tables: **missing** caption and scope; audit's action cell is `dir="ltr"` on the `<td>`, so alignment intent should be moved to an inner `<bdi>`.
- All forms: labels are correctly associated. Dialogs label and describe themselves. The dialog's X is 44px with an `aria-label`.

### Status not conveyed by colour alone

Pass. Every pill carries text ("نشط" / "معطّل" / "غير مفعّل") and the provider warning adds an icon. The only colour-only element is the decorative sparkline, which carries no information — a further reason to remove it.

---

## 10. What I could not verify

- The new users dialogs (rendering, focus trap in practice, 90vw at 375, backdrop).
- Hover/focus visuals for every control.
- Error banners and the temporary-password flow.
- 1024/768/375 renders (all responsive findings are from CSS and layout math).
- Screen-reader verbosity, zoom, and reflow.
- Arabic text shaping at 200% / iOS Safari.

Re-capture after the users work lands, from a production build, at 1440 / 1024 / 768 / 375, including: login, login error, change-password, dashboard, settings, users (list + both dialogs), audit, and an empty audit.

---

## 11. Top 5 fixes

1. **Make text and controls contrast-safe** (P1-1, P1-2). Three token-level edits — `--fd-line-input: #96907f` for fields, `--fd-ink-muted` for sidebar metadata, `white/70` for the login footnote — plus a real 2px focus outline on inputs. Fixes 1.4.3 and 1.4.11 with no change to the palette's character.
2. **Stop unmounting the shell, stop flashing false states, and title the pages** (P1-3, P1-4, P1-5). Cache the session in a layout, render `AppShell` immediately, gate every empty state on `loading` (audit currently claims "لا توجد أحداث" before it knows), add per-route titles and a skip link.
3. **Resolve the permission/navigation contradictions and make the audit log readable** (P1-7, P1-10). Staff can open Settings but cannot see it; staff are invited to an admin-only audit log; the audit log never says *who*. These are the first things a reviewer will click.
4. **Fix the first-run path** (P1-8, P1-9). Login: form at the reading start, stack below `lg`, hide the brand panel on phones. Forced password: show the 12-character rule, name the account, and provide an exit.
5. **Fix the money/date contract, then bring the visual language up to the board's scale** (P1-6; P2-1/P2-2/P2-3/P2-10/P2-11). Remove the `د.س` fallback, use `YYYY-MM-DD HH:mm` in tables, then unboxed 22px KPI icons, a 30/16 amount split, no fake sparkline, 16px section titles with an arrow, a 220px rail with the watermark and a real footer, and a display serif for the Latin wordmark.
