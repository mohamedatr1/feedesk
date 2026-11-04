# Design Gap and Screen Status

**Reference:** `FeeDesk-Dashboard.png` (approved visual direction).  
**Status:** Dashboard shell implemented; remaining product screens are M2–M4.

## Implemented in M1

| Screen | Status | Notes |
|---|---|---|
| Login | Built | RTL, brand panel, error and loading states |
| Forced password change | Built | 12-character minimum, confirmation, error states |
| App shell | Built | Right sidebar, topbar, active nav, logout, date |
| Home dashboard | Built shell | KPI cards, empty action queue, empty activity table, provider status |
| Settings — school | Built | Admin edit, staff read-only |
| Settings — users | Built | Create, edit role/email/job title, deactivate, reset password, accessible confirmations |
| Audit log | Built | Admin-only, latest 25 events |
| Statements / campaigns / messages | Placeholder | M2–M4 |
| Import review / campaign preview / results | Not designed | M2–M4 |

## Design system coverage

| Element | Status |
|---|---|
| Color tokens | Implemented |
| Arabic typography | IBM Plex Sans Arabic via `next/font` |
| RTL primitives | Implemented in layout and tables |
| Buttons / inputs / cards / pills | Implemented |
| Data table / empty state / skeleton | Implemented |
| Dialogs / confirmations | Built |
| Toasts / file dropzone / template editor | Not yet |
| Mobile/tablet layout | Sidebar collapses to 76px; deeper QA pending |
| Accessibility audit | P1 review complete (`docs/design/design-review.md`); full audit M5 |
| Per-route titles / skip link | Built |
| Contrast / focus / input boundaries | P1 fixed |

## Review and fixes

See `docs/design/design-review.md`. The P1 accessibility and navigation fixes are implemented; P2 visual-scale polish remains.

## Known design notes

- The mockup uses `د.س` as a sample currency symbol. It is configuration, not a constant.
- The mockup’s `تم الإرسال` label should become `تم الإرسال إلى المزود` unless delivery is confirmed.
- KPI deltas/sparklines require daily snapshots; no fake deltas are shown.
- The sidebar watercolor illustration is not yet added; it should remain a low-contrast brand asset and hide below 1024px.
- Only the dashboard is designed. The remaining screens must be produced before their frontend milestone.
