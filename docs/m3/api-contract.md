# M3 — Campaign and Approval API Contract

**Status:** Binding for M3 implementation. Sending is out of scope: approval freezes the campaign and creates pending messages/jobs, but no worker or provider call exists in M3.

**Base:** `/api/v1`  
**Auth:** session cookie; mutating requests require `X-CSRF-Token`.

**Permissions**

| Action | Permission |
|---|---|
| View campaigns | `campaigns.view` |
| Create/edit draft | `campaigns.create` / `campaigns.edit` |
| Preview | `campaigns.preview` |
| Submit for approval | `campaigns.submit` |
| Approve | `campaigns.approve` (admin only for now) |
| Cancel draft/awaiting | `campaigns.edit` |
| Cancel approved | `campaigns.approve` |
| View templates | `templates.view` (staff) |
| Manage templates | `templates.manage` (admin) |

Staff already has the campaign permissions except approve. Add `templates.view` to staff; admin has `*`.

---

## 1. Data shapes

### CampaignSummary

```json
{
  "id": "uuid",
  "name": "تذكير رسوم الفصل الأول",
  "status": "draft",
  "channel": "sms",
  "source_import_id": "uuid",
  "source_filename": "sample-01-multi-sheet.xlsx",
  "template_id": "uuid",
  "template_name": "تذكير الرسوم الدراسية",
  "template_version": 1,
  "recipient_count": 4,
  "excluded_count": 2,
  "invalid_contact_count": 1,
  "totals_by_currency": { "SYP": "2100000.00", "USD": "400.00" },
  "warnings": [
    { "code": "SHARED_PHONE", "message_ar": "رقم هاتف مشترك بين أكثر من ولي أمر.", "count": 2 }
  ],
  "created_by": "user-id",
  "created_by_name": "admin",
  "created_at": "2026-11-03T20:00:00Z",
  "updated_at": "2026-11-03T20:00:00Z",
  "submitted_at": null,
  "approved_by": null,
  "approved_by_name": null,
  "approved_at": null,
  "cancelled_at": null,
  "cancel_reason": null,
  "snapshot_hash": null,
  "revision": 0
}
```

Statuses used in M3: `draft`, `awaiting_approval`, `approved`, `cancelled`. The model may reserve the full PRD lifecycle, but the API rejects transitions outside the M3 set.

### CampaignDetail

`CampaignSummary` plus:

```json
{
  "template_body": "عزيزنا {{guardian_name}} ...",
  "previewed_at": "2026-11-03T20:00:00Z",
  "blocking_reasons": [
    { "code": "UNRESOLVED_VARIABLES", "message_ar": "قالب الرسالة يحتوي متغيرات غير معروفة." }
  ],
  "warnings": [
    { "code": "SHARED_PHONE", "message_ar": "رقم هاتف مشترك بين أكثر من ولي أمر.", "count": 2 }
  ],
  "recipients": [CampaignRecipient],
  "excluded": [ExcludedRecord],
  "can_submit": true,
  "can_approve": false,
  "can_cancel": true,
  "message_count": 0,
  "pending_job_count": 0
}
```

`message_count` and `pending_job_count` are 0 before approval and equal the number of frozen recipients/messages and pending jobs after approval. They are counts only; they do not imply delivery.

After approval, `excluded` and `warnings` return the frozen snapshots taken at approval. Draft/awaiting campaigns compute them from current confirmed data.

### CampaignRecipient

```json
{
  "id": null,
  "key": "guardian-id:SYP",
  "guardian_id": "uuid",
  "guardian_name": "ولي أمر 001",
  "phone": "+963993000001",
  "student_names": ["طالب 001"],
  "fee_periods": ["الفصل الأول"],
  "amount": "600000.00",
  "currency": "SYP",
  "message": "عزيزنا ولي أمر 001 ...",
  "validation_status": "valid",
  "warnings": [],
  "fee_balance_ids": ["uuid", "uuid"]
}
```

`id` is populated only after approval (persisted snapshot). `key` is stable for preview. `validation_status` is `valid` or `warning`; warnings never block approval once acknowledged.

### ExcludedRecord

```json
{
  "guardian_id": "uuid",
  "guardian_name": "ولي أمر 004",
  "phone": null,
  "amount": "500000.00",
  "currency": "SYP",
  "reasons": [
    { "code": "MISSING_PHONE", "message_ar": "لا يوجد رقم هاتف صالح." }
  ],
  "fee_balance_ids": ["uuid"]
}
```

### TemplateSummary / TemplateDetail

```json
{
  "id": "uuid",
  "name": "تذكير الرسوم الدراسية",
  "language": "ar",
  "channel": "sms",
  "version": 1,
  "is_active": true,
  "body_preview": "عزيزنا {{guardian_name}} ...",
  "unknown_variables": [],
  "created_by_name": "admin",
  "created_at": "2026-11-03T20:00:00Z"
}
```

Detail adds `template_body`. `unknown_variables` lists `{{...}}` placeholders not in the allowed set.

---

## 2. Endpoints

### Templates

#### `GET /templates`

Query: `channel` (default `sms`), `language`, `active_only` (default false), `page`, `page_size`.

Returns `{ items: [TemplateSummary], total, page, page_size }`, ordered by name then version desc.

#### `GET /templates/active`

Query: `channel=sms`, `language=ar`. Returns the active `TemplateDetail` or `404 TEMPLATE_NOT_FOUND`.

#### `GET /templates/variables`

Returns allowed variables with Arabic labels and fallback descriptions:

```json
{
  "variables": [
    { "name": "guardian_name", "label": "اسم ولي الأمر", "fallback": null },
    { "name": "student_list", "label": "أسماء الطلاب", "fallback": "أبنائكم" }
  ]
}
```

#### `GET /templates/{id}`

Returns `TemplateDetail`.

#### `POST /templates`

Admin only. Body:

```json
{
  "name": "تذكير الرسوم الدراسية",
  "language": "ar",
  "channel": "sms",
  "template_body": "عزيزنا {{guardian_name}} ..."
}
```

If `name` already exists, creates version `max(version)+1`, deactivates previous versions, and returns the new active `TemplateDetail`. Unknown variables are allowed at save time but reported and block campaign approval. Reject empty body/name.

#### `POST /templates/{id}/activate`

Admin only. Deactivates other versions with the same name and activates this row. Returns `TemplateDetail`.

### Campaigns

#### `GET /campaigns`

Query: `status`, `page`, `page_size`. Returns `{ items: [CampaignSummary], total, page, page_size }`, newest first.

#### `POST /campaigns`

Body:

```json
{
  "name": "تذكير رسوم الفصل الأول",
  "source_import_id": "uuid",
  "template_id": "uuid"
}
```

Rules:

- `source_import_id` must reference a `confirmed` import batch.
- `template_id` is optional; default to the active SMS/Arabic template. If none → `422 NO_ACTIVE_TEMPLATE`.
- Campaign is created in `draft`; preview is computed and stored in the summary fields.
- Returns `201 CampaignDetail`.

Error codes: `IMPORT_NOT_CONFIRMED`, `TEMPLATE_NOT_FOUND`, `NO_ACTIVE_TEMPLATE`.

#### `PATCH /campaigns/{id}`

Allowed only in `draft`. Body: `{ "name"?, "template_id"? }`. Recomputes preview, increments `revision`, returns `CampaignDetail`. Cannot change `source_import_id` after creation; create a new draft instead.

#### `GET /campaigns/{id}`

Returns `CampaignDetail`. For `draft`/`awaiting_approval`, preview is computed from current confirmed balances. For `approved`, persisted recipient snapshots are returned. For `cancelled`, only stored data is returned.

#### `GET /campaigns/{id}/preview`

Same response shape as `GET /campaigns/{id}`; exists for the PRD baseline. For approved/cancelled it returns the persisted/read-only view.

#### `POST /campaigns/{id}/submit`

Body:

```json
{ "expected_revision": 3 }
```

Rules:

- Allowed from `draft`.
- Recompute preview; reject with `422 CAMPAIGN_BLOCKED` when there are blocking reasons or zero eligible recipients.
- Warnings do not block submission.
- Sets `awaiting_approval`, `submitted_at`, increments `revision`.
- Audit `campaign.submit`.

#### `POST /campaigns/{id}/approve`

Admin only. Body:

```json
{ "acknowledge_warnings": true, "expected_revision": 4 }
```

Rules:

- Allowed from `awaiting_approval`. If already `approved`, return the existing detail without creating duplicates.
- Recompute preview; block on any blocking reason, zero recipients, or inactive/missing template.
- If warnings exist and `acknowledge_warnings` is false → `422 WARNINGS_UNACKNOWLEDGED`.
- In one transaction:
  1. freeze `CampaignRecipient` rows for all eligible recipients;
  2. create one `Message` per recipient with `internal_status='pending'`, `provider='rasel'`, `channel='sms'`;
  3. create one `SendJob` per message with `status='pending'`, `attempt_count=0`, `next_attempt_at=null`;
  4. set `approved_by`, `approved_at`, `snapshot_hash`, status `approved`, increment `revision`;
  5. audit `campaign.approve` with counts, totals, and hash.
- No provider call is made. No worker exists in M3.
- `snapshot_hash` is SHA-256 of canonical JSON containing campaign identity, template id/version/body, approver, approval timestamp, and recipients (guardian id/name, phone, amount string, currency, message, fee balance ids, students, periods), sorted deterministically.
- If anything fails, the transaction rolls back with no partial recipients/messages/jobs.

#### `POST /campaigns/{id}/cancel`

Body:

```json
{ "reason": "原因是...", "expected_revision": 5 }
```

Rules:

- Allowed from `draft`, `awaiting_approval`, or `approved`.
- `reason` optional but recommended; store when provided.
- Draft/awaiting requires `campaigns.edit`; approved requires `campaigns.approve`.
- Set status `cancelled`, `cancelled_at`, `cancelled_by`, increment `revision`.
- If messages/jobs were created, mark them `cancelled`; keep recipient snapshots.
- Idempotent: cancelling an already cancelled campaign returns the detail.
- Audit `campaign.cancel`.

---

## 3. Eligibility and grouping

Source balances: `fee_balances.import_batch_id = source_import_id` and `record_status = 'confirmed'`.

Group by `(guardian_id, currency)`. Sum `remaining_balance_source` across the group.

A group is eligible only when:

1. The sum is greater than zero.
2. The currency is non-empty.
3. The guardian is active.
4. A valid destination phone exists.

Destination phone selection:

1. Guardian contacts ordered by `is_primary` desc, `created_at` asc.
2. Normalize the phone to E.164 if needed and require `phonenumbers.is_valid_number` with region `SY`.
3. Use the first valid contact; preserve the normalized E.164 value in the snapshot.
4. Missing phone → `MISSING_PHONE`; no valid phone → `INVALID_PHONE`.

Grouping rules:

- Two currencies for one guardian produce two recipients.
- Multiple balances for one guardian in one currency produce one recipient with summed amount.
- Shared phone across different guardians is a `SHARED_PHONE` warning, not a merge. Both recipients stay eligible and approval requires warning acknowledgment.
- Different currencies are never summed together.
- Zero/negative balances, inactive guardians, missing/invalid phones, and unknown currencies are excluded with reasons.

Exclusion reason codes:

`ZERO_BALANCE`, `NEGATIVE_BALANCE`, `MISSING_CURRENCY`, `MISSING_PHONE`, `INVALID_PHONE`, `GUARDIAN_INACTIVE`.

Campaign-level blocking reasons:

`UNRESOLVED_VARIABLES`, `TEMPLATE_INACTIVE`, `NO_ELIGIBLE_RECIPIENTS`, `TEMPLATE_NOT_FOUND`.

---

## 4. Template rendering

Allowed variables:

| Variable | Source | Fallback |
|---|---|---|
| `guardian_name` | recipient guardian | required; unresolved if empty |
| `school_name` | school settings | `المدرسة` |
| `student_name` | first student | `الطالب` |
| `student_list` | distinct student names joined with `، ` | `أبنائكم` |
| `amount` | formatted outstanding amount with grouping | required |
| `currency` | ISO currency | required |
| `fee_period` | distinct periods joined with `، ` | `الفصل الحالي` |
| `school_contact` | settings contact phone, else email | `إدارة المدرسة` |

Rules:

- Syntax `{{name}}` or `{{ name }}`.
- Unknown variables remain in the body and produce `UNRESOLVED_VARIABLES`.
- Replace allowed variables deterministically; collapse repeated whitespace; trim.
- Plain text only; no HTML rendering.
- The seeded Arabic body is a draft and remains subject to school copy approval before production.

---

## 5. Snapshot and immutability

- Approved campaign recipients/messages/jobs are created only by approval.
- No endpoint edits an approved campaign or its recipient snapshots.
- A database trigger blocks updates/deletes on `campaign_recipients` while the parent campaign is `approved`, `queued`, `sending`, `completed`, or `completed_with_errors`.
- Cancelling an approved campaign changes campaign status and message/job status only; recipient snapshots remain unchanged.
- Source fee/guardian edits after approval do not change the snapshot.
- The approval transaction is all-or-nothing.

---

## 6. Frontend routes

| Route | Screen |
|---|---|
| `/campaigns` | Campaign list with status filters, counts, totals, created/approved by |
| `/campaigns/new` | Builder: confirmed import, name, active template |
| `/campaigns/[id]` | Summary, excluded panel, recipient table, message preview, submit/approve/cancel |
| `/settings/templates` | Admin template list/version editor/activate |

The UI must always show that sending is not enabled in M3. An approved campaign displays a frozen snapshot and hash, not a "send" button.

---

## 7. Dashboard/reporting (`RPT-01..03`)

`GET /api/v1/dashboard?activity_limit=5&trend_days=30` (`dashboard.view`, staff/admin) returns:

- `totals_by_currency`: exact decimal strings for positive confirmed balances, never combined.
- `counts`: outstanding records/guardians, import review/processing, campaign approval/active, recent failed/unknown messages.
- `action_queue`: positive `{code,count,severity,target}` rows.
- `recent_activity`: latest audit actions with actor/entity/time/`status="recorded"`; never payloads.
- `trends`: `{available,basis_days,deltas,series}`; per-currency deltas and daily snapshots, `available=false` with no baseline. No fabricated zero/delta.

Daily snapshot: `python -m app.dashboard.snapshot --date YYYY-MM-DD` (idempotent upsert by date). Frontend route `/` renders the KPI cards, action queue, activity, and per-currency trends only when history exists.
