const API_BASE = "/api/v1";
const CSRF_STORAGE_KEY = "fd_csrf";

let csrfMemory = "";

export class ApiError extends Error {
  status: number;
  code: string;
  messageAr: string;
  details: Record<string, unknown> | null;

  constructor(
    status: number,
    code: string,
    messageAr: string,
    messageEn: string,
    details: Record<string, unknown> | null = null,
  ) {
    super(messageEn);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.messageAr = messageAr;
    this.details = details;
  }
}

export type User = {
  id: string;
  username: string;
  email: string | null;
  role: "admin" | "staff" | string;
  job_title: string | null;
  is_active: boolean;
  must_change_password: boolean;
  /**
   * Per-user approval grant (FND-08). Admin approval is implicit, so this only
   * matters for staff accounts. Treat a missing value as false.
   */
  can_approve_campaigns: boolean;
};

export type Me = {
  user: User;
  permissions: string[];
  csrf_token: string;
};

export type SchoolSettings = {
  school_name: string;
  default_currency: string;
  currency_symbol: string;
  timezone: string;
  locale: string;
  contact_phone: string | null;
  contact_email: string | null;
  send_limit: number;
  batch_limit: number;
  updated_at: string | null;
  /** Optional until the import config endpoint exposes it. */
  max_upload_mb?: number | null;
};

/* ------------------------------------------------------------------ */
/* Messaging provider control — admin only                            */
/* ------------------------------------------------------------------ */

/** Channels the provider-control endpoints accept. */
export type MessagingChannel = "local_sms" | "sms";

/**
 * Provider state returned by the credential and revoke endpoints.
 * The API key is intentionally absent: the server never returns it, so the
 * UI has nothing to cache, prefill, or echo.
 */
export type MessagingProviderStatus = {
  provider: string;
  configured: boolean;
  /** Where the server loaded the credential from (env, database, …). */
  credential_source: string | null;
  credential_error: string | null;
  sender_id: string | null;
  /** Null until a credential source (and therefore a channel) exists. */
  channel: string | null;
  key_version: number | null;
  rotated_at: string | null;
  rotated_by_name: string | null;
  /** Test-send mode reported by the backend (e.g. dry_run, live). */
  test_send_mode: string;
  /** False while live sending is gated behind G0/G4. */
  live_send_available: boolean;
};

export type MessagingCredentialPayload = {
  /** Write-only: sent once, never stored in component state after success. */
  api_key: string;
  sender_id: string;
  channel: MessagingChannel;
};

export type MessagingTestSendPayload = {
  /** E.164 destination; the backend keeps the full number. */
  recipient: string;
  message: string;
};

export type MessagingTestSendResult = {
  provider: string;
  dry_run: boolean;
  outcome: string;
  provider_status: string | null;
  error_code: string | null;
  error_summary: string | null;
  provider_message_id: string | null;
  /** Privacy-safe recipient echo; render this instead of the typed number. */
  recipient_masked: string | null;
  sent_at: string | null;
};

export type MessagingBalance = {
  provider: string;
  available: boolean;
  /** Decimal string (preferred) or number; never coerce a string to a number. */
  balance: string | number | null;
  currency: string | null;
  /** Boolean preflight result from the backend. */
  preflight: boolean;
  reason?: string | null;
};

export type AuditEvent = {
  id: string;
  actor_user_id: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  before_data: Record<string, unknown> | null;
  after_data: Record<string, unknown> | null;
  request_id: string | null;
  created_at: string;
};

/* ------------------------------------------------------------------ */
/* Imports (M2) — typed against docs/m2/api-contract.md               */
/* ------------------------------------------------------------------ */

export type ImportStatus =
  | "uploaded"
  | "processing"
  | "review_required"
  | "ready_to_confirm"
  | "confirmed"
  | "failed"
  | "cancelled";

export type IssueSeverity = "warning" | "error";

export type ImportIssue = {
  code: string;
  field?: string | null;
  message_ar: string;
  severity: IssueSeverity;
};

export type ImportBatchSummary = {
  id: string;
  source_filename: string;
  file_type: "xlsx" | "pdf" | string;
  status: ImportStatus;
  worksheet_name: string | null;
  available_sheets: string[];
  total_rows: number;
  valid_rows: number;
  invalid_rows: number;
  duplicate_rows: number;
  /** Optional until the backend exposes excluded-row counts. */
  excluded_rows?: number | null;
  warnings: ImportIssue[];
  uploaded_by: string | null;
  /** Optional display name added by the backend; never invent one. */
  uploaded_by_name?: string | null;
  /** Optional per-currency aggregates. String amounts only; never combined. */
  totals_by_currency?: Record<string, string> | null;
  created_at: string;
  confirmed_at: string | null;
  /** Optional terminal timestamp; omit the row when absent. */
  cancelled_at?: string | null;
  updated_at?: string | null;
  /** Optional upload limit exposure, in megabytes. */
  max_upload_mb?: number | null;
  error_summary?: ImportErrorSummary;
};

export type ColumnMapping = Record<string, string>;

export type ImportErrorSummary =
  | {
      count?: number;
      by_code?: Record<string, number>;
      code?: string;
      message_ar?: string;
      details?: Record<string, unknown> | null;
    }
  | string
  | null;

export type ImportDetail = ImportBatchSummary & {
  source_file_id: string | null;
  column_mapping: ColumnMapping | null;
  /** Header names only; never cell values. Optional until the backend exposes it. */
  available_headers?: string[];
  error_summary: ImportErrorSummary;
  confirmed_by: string | null;
  duplicate_reason: string | null;
};

export type StagedRowData = {
  guardian_name?: string | null;
  guardian_phone_original?: string | null;
  guardian_phone_normalized?: string | null;
  student_name?: string | null;
  total_fee?: string | null;
  amount_paid?: string | null;
  remaining_balance?: string | null;
  remaining_balance_calculated?: string | null;
  currency?: string | null;
  fee_period?: string | null;
  is_excluded?: boolean;
};

export type StagedRowStatus = "valid" | "warning" | "invalid" | "excluded";

export type StagedRow = {
  id: string;
  source_row_number: number | null;
  source_page_number: number | null;
  normalized_data: StagedRowData;
  validation_status: StagedRowStatus;
  validation_errors: ImportIssue[];
  is_excluded: boolean;
};

/* Bulk exclusion and guardian resolution (M2 review). */

export type ImportExclusionScope = "invalid" | "selected";

export type ImportExclusionPayload = {
  is_excluded: boolean;
  /** `invalid` ignores row_ids and targets every invalid row in the import. */
  scope: ImportExclusionScope;
  row_ids: string[];
};

export type GuardianCandidateStatus =
  | "ambiguous"
  | "exact"
  | "same_name"
  | "shared_phone"
  | "manual";

export type GuardianMatch = "exact" | "name" | "phone";

export type GuardianResolutionMode = "auto" | "link_existing" | "create_new";

export type GuardianCandidate = {
  guardian_id: string;
  full_name: string;
  /** Privacy-safe phone; the full number never reaches this view. */
  phone_masked: string;
  status: GuardianCandidateStatus | string;
  match: GuardianMatch | string;
};

/**
 * One staged row that may need a guardian decision. `mode` is loose so a new
 * backend mode renders safely instead of breaking the union.
 */
export type GuardianCandidateRow = {
  row_id: string;
  guardian_name: string;
  /** Privacy-safe phone for the row; render this, never the raw row phone. */
  guardian_phone_masked: string;
  status: GuardianCandidateStatus | string;
  mode: GuardianResolutionMode | string;
  resolved_guardian_id: string | null;
  resolved_guardian_name: string | null;
  candidates: GuardianCandidate[];
};

export type GuardianCandidateCounts = {
  ambiguous: number;
  same_name: number;
  shared_phone: number;
  manual: number;
};

export type GuardianCandidatesResponse = {
  items: GuardianCandidateRow[];
  counts: GuardianCandidateCounts;
};

export type GuardianResolution = {
  mode: GuardianResolutionMode;
  /** Required when mode is `link_existing`; omitted otherwise. */
  guardian_id?: string;
};

export type Paginated<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type ImportListParams = {
  page?: number;
  page_size?: number;
  status?: ImportStatus | "";
};

export type ImportRowParams = {
  page?: number;
  page_size?: number;
  status?: StagedRowStatus | "";
  q?: string;
};

export type ImportRowPatch = {
  normalized_data?: StagedRowData;
  is_excluded?: boolean;
  guardian_resolution?: GuardianResolution;
};

export type ProcessImportPayload = {
  worksheet_name?: string;
  mapping?: ColumnMapping;
};

export type UploadImportOptions = {
  worksheetName?: string;
  mapping?: ColumnMapping;
  forceDuplicate?: boolean;
  duplicateReason?: string;
  /** null means the browser could not compute upload bytes (indeterminate). */
  onProgress?: (percent: number | null) => void;
};

export const IMPORT_FIELD_LABELS: Record<string, string> = {
  guardian_name: "اسم ولي الأمر",
  guardian_phone: "رقم الهاتف",
  student_name: "اسم الطالب",
  total_fee: "إجمالي القسط",
  amount_paid: "المدفوع",
  remaining_balance: "المتبقي",
  currency: "العملة",
  fee_period: "الفترة",
};

export const MAPPING_FIELDS = Object.keys(IMPORT_FIELD_LABELS);

function buildImportQuery(params: object): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function importSourceFileUrl(sourceFileId: string | null | undefined): string | null {
  if (!sourceFileId) return null;
  return `${API_BASE}/files/${sourceFileId}`;
}


export function setCsrfToken(token: string): void {
  csrfMemory = token;
  if (typeof window !== "undefined") {
    window.sessionStorage.setItem(CSRF_STORAGE_KEY, token);
  }
}

export function getCsrfToken(): string {
  if (csrfMemory) return csrfMemory;
  if (typeof window !== "undefined") {
    return window.sessionStorage.getItem(CSRF_STORAGE_KEY) ?? "";
  }
  return "";
}

export function clearCsrfToken(): void {
  csrfMemory = "";
  if (typeof window !== "undefined") {
    window.sessionStorage.removeItem(CSRF_STORAGE_KEY);
  }
}

type ApiErrorBody = {
  error?: {
    code?: string;
    message_ar?: string;
    message_en?: string;
    details?: Record<string, unknown> | null;
  };
};

function errorFromBody(status: number, data: unknown): ApiError {
  const error = (data as ApiErrorBody | null)?.error;
  return new ApiError(
    status,
    error?.code ?? "REQUEST_FAILED",
    error?.message_ar ?? "تعذر تنفيذ الطلب.",
    error?.message_en ?? "Request failed.",
    error?.details ?? null,
  );
}

/**
 * `confirm` can refuse with AMBIGUOUS_GUARDIAN and list the rows that need a
 * decision. Returns null for any other error, and [] when the code matches but
 * the payload carries no row ids.
 */
export function ambiguousGuardianRowIds(err: unknown): string[] | null {
  if (!(err instanceof ApiError) || err.code !== "AMBIGUOUS_GUARDIAN") return null;
  const raw = err.details?.row_ids;
  if (!Array.isArray(raw)) return [];
  return raw.filter((id): id is string => typeof id === "string" && id.trim() !== "");
}

function isFormDataBody(body: BodyInit | null | undefined): boolean {
  if (!body) return false;
  if (typeof FormData !== "undefined" && body instanceof FormData) return true;
  if (typeof URLSearchParams !== "undefined" && body instanceof URLSearchParams) return true;
  if (typeof Blob !== "undefined" && body instanceof Blob) return true;
  return false;
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const method = (options.method ?? "GET").toUpperCase();

  // Multipart bodies must keep the browser-generated boundary. Setting
  // application/json here would corrupt the upload.
  if (options.body && !isFormDataBody(options.body) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrf = getCsrfToken();
    if (csrf) headers.set("X-CSRF-Token", csrf);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
    cache: "no-store",
  });

  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw errorFromBody(response.status, data);
  }
  return data as T;
}

/* ------------------------------------------------------------------ */
/* Campaigns and templates (M3) — typed against docs/m3/api-contract.md */
/* ------------------------------------------------------------------ */

/**
 * M3 statuses plus the four M4 derived processing outcomes. Additive: the
 * backend owns derivation; the UI only labels what the API returns.
 */
export type CampaignStatus =
  | "draft"
  | "awaiting_approval"
  | "approved"
  | "sending"
  | "completed"
  | "completed_with_errors"
  | "failed"
  | "cancelled";

export type CampaignNotice = {
  code: string;
  message_ar: string;
  count?: number | null;
};

export type CampaignRecipient = {
  /** Populated only after approval (persisted snapshot). */
  id: string | null;
  key: string;
  guardian_id: string;
  guardian_name: string;
  /** Full phone, only in preview responses; never render it in the list. */
  phone: string;
  /** Privacy-safe masked phone used by the campaign detail tables. */
  phone_masked: string;
  /** Count preserved in detail responses, where student_names is empty. */
  student_count?: number;
  student_names: string[];
  fee_periods: string[];
  /** Decimal string; never convert to a JS number. */
  amount: string;
  currency: string;
  message: string;
  validation_status: "valid" | "warning" | string;
  warnings: CampaignNotice[];
  fee_balance_ids: string[];
};

export type ExcludedRecord = {
  guardian_id: string;
  guardian_name: string;
  /** Full phone, only in preview data; the table must prefer the masked value. */
  phone: string | null;
  /** Privacy-safe masked phone used by the campaign detail tables. */
  phone_masked: string | null;
  amount: string;
  currency: string | null;
  reasons: CampaignNotice[];
  fee_balance_ids: string[];
  key?: string | null;
};

export type CampaignSummary = {
  id: string;
  name: string;
  status: CampaignStatus | string;
  channel: string;
  source_import_id: string | null;
  source_filename: string | null;
  template_id: string | null;
  template_name: string | null;
  template_version: number | null;
  recipient_count: number;
  excluded_count: number;
  invalid_contact_count: number;
  totals_by_currency: Record<string, string>;
  warnings: CampaignNotice[];
  created_by: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  approved_by: string | null;
  approved_by_name: string | null;
  approved_at: string | null;
  cancelled_at: string | null;
  /** Present in the current backend response; absent from the M3 contract table. */
  cancelled_by?: string | null;
  /** Present in the current backend response; absent from the M3 contract table. */
  cancel_reason?: string | null;
  snapshot_hash: string | null;
  revision: number;
};

export type CampaignDetail = CampaignSummary & {
  template_body: string | null;
  previewed_at: string | null;
  blocking_reasons: CampaignNotice[];
  recipients: CampaignRecipient[];
  excluded: ExcludedRecord[];
  can_submit: boolean;
  can_approve: boolean;
  can_cancel: boolean;
  /** Counts only; they never imply delivery. Optional in the contract. */
  message_count?: number | null;
  pending_job_count?: number | null;
};

/* ------------------------------------------------------------------ */
/* Messages and campaign results (M4) — typed against                  */
/* docs/m4/api-contract.md                                             */
/* ------------------------------------------------------------------ */

export type MessageStatus =
  | "pending"
  | "submitting"
  | "provider_accepted"
  | "queued_by_provider"
  | "delivered"
  | "failed"
  | "unknown"
  | "cancelled";

export const MESSAGE_STATUSES: MessageStatus[] = [
  "pending",
  "submitting",
  "provider_accepted",
  "queued_by_provider",
  "delivered",
  "failed",
  "unknown",
  "cancelled",
];

export type MessageSummary = {
  id: string;
  campaign_id: string;
  campaign_name: string;
  guardian_name: string;
  /** Privacy-safe masked phone; the full number only appears on the detail. */
  destination_phone_masked: string;
  /** Decimal string; never convert to a JS number. */
  amount: string;
  currency: string;
  channel: string;
  internal_status: MessageStatus | string;
  provider_status: string | null;
  provider_message_id: string | null;
  last_error_code: string | null;
  last_error_summary: string | null;
  /**
   * Contract-additive: the summary may include the scheduled retry time.
   * Absent in the current backend response; the list never infers a retry.
   */
  next_attempt_at?: string | null;
  submitted_at: string | null;
  delivered_at: string | null;
  created_at: string;
  updated_at: string;
};

export type MessageDetail = MessageSummary & {
  /** Full destination phone; detail responses only, never list summaries. */
  destination_phone: string;
  message_body_snapshot: string | null;
  provider_payload_redacted: Record<string, unknown> | null;
  /** Contract-additive; absent in the current backend response. */
  provider_request_id?: string | null;
  attempt_count?: number | null;
  next_attempt_at?: string | null;
};

/* ------------------------------------------------------------------ */
/* M4 operations console (admin-only, read-only) — typed against the   */
/* /messaging/ops contract. No endpoint here mutates anything.         */
/* ------------------------------------------------------------------ */

export type MessagingOpsProvider = {
  name: string;
  configured: boolean;
  /** Where the server loaded the credential from; never the credential. */
  credential_source: string | null;
  key_version: number | null;
  /** Safe operator-facing reason when the credential cannot be loaded. */
  credential_error: string | null;
};

export type MessagingOpsQueue = {
  /** Full backend breakdown; render keys verbatim when a label is unknown. */
  by_job_status: Record<string, number>;
  pending: number;
  claimed: number;
  retry: number;
  due_now: number;
  stale_claims: number;
  oldest_pending_at: string | null;
  next_attempt_at: string | null;
};

export type MessagingOpsMessages = {
  /** Eight message-status keys; a missing key renders "—", never a guess. */
  by_status: Partial<Record<MessageStatus, number>>;
  total: number;
  failed: number;
  unknown: number;
  reconciliation_required: number;
};

export type MessagingOpsProviderEvents = {
  unprocessed: number;
  last_received_at: string | null;
};

export type MessagingOpsSummary = {
  generated_at: string;
  provider: MessagingOpsProvider;
  queue: MessagingOpsQueue;
  messages: MessagingOpsMessages;
  campaigns: {
    by_status: Partial<Record<CampaignStatus, number>>;
    sending: number;
  };
  provider_events: MessagingOpsProviderEvents;
};

/** One queue job, joined with its message and campaign. Phone stays masked. */
export type MessagingOpsJobItem = {
  job_id: string;
  message_id: string;
  campaign_id: string;
  campaign_name: string;
  campaign_status: CampaignStatus | string;
  message_status: MessageStatus | string;
  job_status: string;
  attempt_count: number;
  next_attempt_at: string | null;
  lease_expires_at: string | null;
  heartbeat_at: string | null;
  /** Worker identity. Displaying it is optional; it is never a claim token. */
  locked_by: string | null;
  last_error: string | null;
  last_error_code: string | null;
  last_error_summary: string | null;
  guardian_name: string;
  destination_phone_masked: string;
  created_at: string;
  updated_at: string;
};

export type MessagingOpsIssueItem = MessagingOpsJobItem & {
  reconciliation_required: boolean;
  retry_exhausted: boolean;
};

/**
 * Provider callbacks kept for reconciliation. The payload is expected to be
 * redacted server-side; the UI never needs it to render the ops console.
 */
export type MessagingOpsProviderEvent = {
  id: string;
  event_type?: string | null;
  provider_status?: string | null;
  provider_message_id?: string | null;
  received_at?: string | null;
  processed_at?: string | null;
  payload_redacted?: Record<string, unknown> | null;
};

export type MessagingOpsMessageDetail = MessageDetail & {
  job: MessagingOpsJobItem | null;
  provider_events: MessagingOpsProviderEvent[];
  /** Actions only: audit rows never carry message bodies. */
  recent_audit: AuditEvent[];
};

export type MessagingOpsJobsParams = {
  status?: string;
  campaign_id?: string;
  /** Only meaningful when true; false is never sent. */
  due_only?: boolean;
  stale_only?: boolean;
  page?: number;
  page_size?: number;
};

export type MessagingOpsIssuesParams = {
  kind: "unknown" | "failed";
  campaign_id?: string;
  page?: number;
  page_size?: number;
};

export type MessageListParams = {
  page?: number;
  page_size?: number;
  campaign_id?: string;
  status?: MessageStatus | "";
  q?: string;
};

export type CampaignResults = CampaignSummary & {
  message_count: number;
  /** Eight contract keys. A missing key renders "—", never a derived total. */
  counts: Partial<Record<MessageStatus, number>>;
  last_activity_at: string | null;
  delivery_note_ar: string | null;
};

export type TemplateSummary = {
  id: string;
  name: string;
  language: string;
  channel: string;
  version: number;
  is_active: boolean;
  body_preview: string;
  unknown_variables: string[];
  created_by_name: string | null;
  created_at: string;
};

export type TemplateDetail = TemplateSummary & {
  template_body: string;
};

export type TemplateVariable = {
  name: string;
  label: string;
  fallback: string | null;
};

export type CampaignListParams = {
  status?: CampaignStatus | "";
  page?: number;
  page_size?: number;
};

export type TemplateListParams = {
  channel?: string;
  language?: string;
  active_only?: boolean;
  page?: number;
  page_size?: number;
};

export type CampaignCreatePayload = {
  name: string;
  source_import_id: string;
  template_id?: string | null;
};

export type CampaignUpdatePayload = {
  name?: string;
  template_id?: string | null;
};

export type CampaignApprovePayload = {
  acknowledge_warnings: boolean;
  expected_revision: number;
};

export type CampaignCancelPayload = {
  reason?: string | null;
  expected_revision: number;
};

export type TemplateCreatePayload = {
  name: string;
  language?: string;
  channel?: string;
  template_body: string;
};

/* ------------------------------------------------------------------ */
/* Dashboard (RPT-01 / RPT-02) — typed against the /dashboard contract */
/* ------------------------------------------------------------------ */

export type DashboardCounts = {
  outstanding_records: number;
  outstanding_guardians: number;
  imports_total: number;
  imports_awaiting_review: number;
  imports_processing: number;
  campaigns_total: number;
  campaigns_awaiting_approval: number;
  campaigns_active: number;
  messages_failed_recent: number;
  messages_unknown_recent: number;
};

export type DashboardActionItem = {
  /** Backend code, e.g. `imports_awaiting_review`. Unknown codes render raw. */
  code: string;
  count: number;
  /** Severity is owned by the backend; unknown values fall back to neutral. */
  severity: string;
  /** In-app path the row opens. Validated before being used as a link. */
  target: string;
};

export type DashboardActivityItem = {
  id: string;
  action: string;
  actor_user_id: string | null;
  /** Display name resolved by the backend; never derived from an id here. */
  actor_name: string | null;
  entity_type: string;
  entity_id: string | null;
  created_at: string;
  status: string;
};

/**
 * One currency's movement. `previous` is a decimal string and is never
 * converted; `pct` is the percentage the backend computed (null = no delta).
 */
export type DashboardTrendDelta = {
  previous: string | null;
  pct: number | null;
};

/** One historical snapshot. Currency totals stay decimal strings. */
export type DashboardTrendPoint = {
  date: string;
  totals_by_currency: Record<string, string>;
  counts: DashboardCounts;
};

export type DashboardTrends = {
  available: boolean;
  basis_days: number;
  /** Keyed by currency; a missing key means no delta for that currency. */
  deltas: Record<string, DashboardTrendDelta>;
  /** Ordered snapshots the backend used to compute the deltas. */
  series: DashboardTrendPoint[];
};

export type DashboardData = {
  generated_at: string;
  as_of_date: string;
  /** One decimal string per currency; currencies are never combined. */
  totals_by_currency: Record<string, string>;
  counts: DashboardCounts;
  action_queue: DashboardActionItem[];
  recent_activity: DashboardActivityItem[];
  trends: DashboardTrends;
};

export type DashboardParams = {
  activity_limit?: number;
  trend_days?: number;
};

export const api = {
  async login(username: string, password: string): Promise<Me> {
    const me = await apiFetch<Me>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    });
    setCsrfToken(me.csrf_token);
    return me;
  },

  async me(): Promise<Me> {
    const me = await apiFetch<Me>("/auth/me");
    setCsrfToken(me.csrf_token);
    return me;
  },

  async logout(): Promise<void> {
    await apiFetch<{ ok: boolean }>("/auth/logout", { method: "POST" });
    clearCsrfToken();
  },

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiFetch<{ ok: boolean }>("/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  },

  async getSettings(): Promise<SchoolSettings> {
    return apiFetch<SchoolSettings>("/settings");
  },

  async updateSettings(payload: Partial<SchoolSettings>): Promise<SchoolSettings> {
    return apiFetch<SchoolSettings>("/settings", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  /** Dashboard overview (RPT-01/RPT-02). Read-only. */
  async getDashboard(params: DashboardParams = {}): Promise<DashboardData> {
    return apiFetch(`/dashboard${buildImportQuery(params)}`);
  },

  /* Messaging provider control (admin only). CSRF is added by apiFetch. */

  async getMessagingProvider(): Promise<MessagingProviderStatus> {
    return apiFetch<MessagingProviderStatus>("/messaging/provider");
  },

  async updateMessagingCredential(
    payload: MessagingCredentialPayload,
  ): Promise<MessagingProviderStatus> {
    return apiFetch<MessagingProviderStatus>("/messaging/provider/credential", {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  },

  async revokeMessagingCredential(): Promise<MessagingProviderStatus> {
    return apiFetch<MessagingProviderStatus>("/messaging/provider/revoke", {
      method: "POST",
    });
  },

  async testSendMessage(payload: MessagingTestSendPayload): Promise<MessagingTestSendResult> {
    return apiFetch<MessagingTestSendResult>("/messaging/test-send", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getMessagingBalance(): Promise<MessagingBalance> {
    return apiFetch<MessagingBalance>("/messaging/balance");
  },

  async listUsers(): Promise<User[]> {
    return apiFetch<User[]>("/users");
  },

  async createUser(payload: {
    username: string;
    password: string;
    role: string;
    job_title?: string;
    email?: string;
    can_approve_campaigns?: boolean;
  }): Promise<User> {
    return apiFetch<User>("/users", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateUser(
    userId: string,
    payload: {
      email?: string | null;
      role?: string;
      job_title?: string | null;
      is_active?: boolean;
      can_approve_campaigns?: boolean;
    },
  ): Promise<User> {
    return apiFetch<User>(`/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async resetUserPassword(userId: string): Promise<{ temporary_password: string }> {
    return apiFetch<{ temporary_password: string }>(`/users/${userId}/reset-password`, {
      method: "POST",
    });
  },

  async audit(page = 1, pageSize = 25): Promise<{
    items: AuditEvent[];
    total: number;
    page: number;
    page_size: number;
  }> {
    return apiFetch(`/audit?page=${page}&page_size=${pageSize}`);
  },

  async listImports(params: ImportListParams = {}): Promise<Paginated<ImportBatchSummary>> {
    return apiFetch(`/imports${buildImportQuery(params)}`);
  },

  async getImport(importId: string): Promise<ImportDetail> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}`);
  },

  async listImportRows(
    importId: string,
    params: ImportRowParams = {},
  ): Promise<Paginated<StagedRow>> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}/rows${buildImportQuery(params)}`);
  },

  async processImport(importId: string, payload: ProcessImportPayload): Promise<ImportDetail> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}/process`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async updateImportRow(
    importId: string,
    rowId: string,
    payload: ImportRowPatch,
  ): Promise<StagedRow> {
    return apiFetch(
      `/imports/${encodeURIComponent(importId)}/rows/${encodeURIComponent(rowId)}`,
      {
        method: "PATCH",
        body: JSON.stringify(payload),
      },
    );
  },

  async setImportRowsExclusion(
    importId: string,
    payload: ImportExclusionPayload,
  ): Promise<ImportDetail> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}/rows/exclusion`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getGuardianCandidates(importId: string): Promise<GuardianCandidatesResponse> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}/guardian-candidates`);
  },

  async confirmImport(
    importId: string,
    acknowledgeWarnings: boolean,
  ): Promise<ImportDetail> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}/confirm`, {
      method: "POST",
      body: JSON.stringify({ acknowledge_warnings: acknowledgeWarnings }),
    });
  },

  async cancelImport(importId: string): Promise<ImportDetail> {
    return apiFetch(`/imports/${encodeURIComponent(importId)}/cancel`, {
      method: "POST",
    });
  },

  async listCampaigns(
    params: CampaignListParams = {},
  ): Promise<Paginated<CampaignSummary>> {
    return apiFetch(`/campaigns${buildImportQuery(params)}`);
  },

  async createCampaign(payload: CampaignCreatePayload): Promise<CampaignDetail> {
    return apiFetch("/campaigns", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async getCampaign(campaignId: string): Promise<CampaignDetail> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}`);
  },

  async getCampaignResults(campaignId: string): Promise<CampaignResults> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}/results`);
  },

  async listMessages(params: MessageListParams = {}): Promise<Paginated<MessageSummary>> {
    return apiFetch(`/messages${buildImportQuery(params)}`);
  },

  async getMessage(messageId: string): Promise<MessageDetail> {
    return apiFetch(`/messages/${encodeURIComponent(messageId)}`);
  },

  /* Operations console (admin only). Every call is a read. */

  async getMessagingOpsSummary(): Promise<MessagingOpsSummary> {
    return apiFetch("/messaging/ops/summary");
  },

  async listMessagingOpsJobs(
    params: MessagingOpsJobsParams = {},
  ): Promise<Paginated<MessagingOpsJobItem>> {
    // Booleans are flags here: sending `due_only=false` would still read as
    // "filter present" to some backends, so only true is ever serialized.
    const query = buildImportQuery({
      ...params,
      due_only: params.due_only ? true : undefined,
      stale_only: params.stale_only ? true : undefined,
    });
    return apiFetch(`/messaging/ops/jobs${query}`);
  },

  async listMessagingOpsIssues(
    params: MessagingOpsIssuesParams,
  ): Promise<Paginated<MessagingOpsIssueItem>> {
    return apiFetch(`/messaging/ops/issues${buildImportQuery(params)}`);
  },

  async getMessagingOpsMessage(messageId: string): Promise<MessagingOpsMessageDetail> {
    return apiFetch(`/messaging/ops/messages/${encodeURIComponent(messageId)}`);
  },

  async previewCampaign(campaignId: string): Promise<CampaignDetail> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}/preview`);
  },

  async updateCampaign(
    campaignId: string,
    payload: CampaignUpdatePayload,
  ): Promise<CampaignDetail> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    });
  },

  async submitCampaign(
    campaignId: string,
    expectedRevision: number,
  ): Promise<CampaignDetail> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}/submit`, {
      method: "POST",
      body: JSON.stringify({ expected_revision: expectedRevision }),
    });
  },

  async approveCampaign(
    campaignId: string,
    payload: CampaignApprovePayload,
  ): Promise<CampaignDetail> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async cancelCampaign(
    campaignId: string,
    payload: CampaignCancelPayload,
  ): Promise<CampaignDetail> {
    return apiFetch(`/campaigns/${encodeURIComponent(campaignId)}/cancel`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  async listTemplates(
    params: TemplateListParams = {},
  ): Promise<Paginated<TemplateSummary>> {
    return apiFetch(`/templates${buildImportQuery(params)}`);
  },

  async getActiveTemplate(
    channel = "sms",
    language = "ar",
  ): Promise<TemplateDetail> {
    return apiFetch(`/templates/active${buildImportQuery({ channel, language })}`);
  },

  async getTemplateVariables(): Promise<{ variables: TemplateVariable[] }> {
    return apiFetch("/templates/variables");
  },

  async getTemplate(templateId: string): Promise<TemplateDetail> {
    return apiFetch(`/templates/${encodeURIComponent(templateId)}`);
  },

  async createTemplate(payload: TemplateCreatePayload): Promise<TemplateDetail> {
    return apiFetch("/templates", {
      method: "POST",
      body: JSON.stringify({
        language: "ar",
        channel: "sms",
        ...payload,
      }),
    });
  },

  async activateTemplate(templateId: string): Promise<TemplateDetail> {
    return apiFetch(`/templates/${encodeURIComponent(templateId)}/activate`, {
      method: "POST",
    });
  },
};

/**
 * Multipart upload via XHR so the UI can show real progress.
 * `Content-Type` is deliberately left unset: the browser adds the multipart
 * boundary, and forcing JSON would make the request unsendable.
 */
export function uploadImport(
  file: File,
  options: UploadImportOptions = {},
): Promise<ImportDetail> {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    if (options.worksheetName) form.append("worksheet_name", options.worksheetName);
    if (options.mapping) form.append("mapping", JSON.stringify(options.mapping));
    if (options.forceDuplicate) form.append("force_duplicate", "true");
    if (options.duplicateReason) form.append("duplicate_reason", options.duplicateReason);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/imports`);
    xhr.withCredentials = true;
    const csrf = getCsrfToken();
    if (csrf) xhr.setRequestHeader("X-CSRF-Token", csrf);

    xhr.upload.onprogress = (event) => {
      if (!options.onProgress) return;
      if (event.lengthComputable && event.total > 0) {
        options.onProgress(Math.min(100, Math.round((event.loaded / event.total) * 100)));
      } else {
        options.onProgress(null);
      }
    };

    xhr.onload = () => {
      let data: unknown = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        options.onProgress?.(100);
        resolve(data as ImportDetail);
        return;
      }
      reject(errorFromBody(xhr.status, data));
    };

    xhr.onerror = () => {
      reject(
        new ApiError(0, "NETWORK_ERROR", "تعذر الاتصال بالخادم أثناء الرفع.", "Network error."),
      );
    };

    xhr.onabort = () => {
      reject(new ApiError(0, "UPLOAD_ABORTED", "تم إلغاء الرفع.", "Upload aborted."));
    };

    xhr.send(form);
  });
}


export function roleLabel(role: string): string {
  if (role === "admin") return "مدير النظام";
  return "موظف إداري";
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-US").format(value);
}

export function formatCurrency(value: number, symbol: string | null | undefined): string {
  // Never invent a currency symbol: it is configuration, not a constant.
  if (!symbol) return "—";
  return `${formatNumber(value)} ${symbol}`;
}

export type DateFormatOptions = {
  locale?: string | null;
  timeZone?: string | null;
};

const DEFAULT_LOCALE = "ar-SY-u-nu-latn";

function withLatinDigits(locale?: string | null): string {
  if (!locale) return DEFAULT_LOCALE;
  return /-u-nu-/.test(locale) ? locale : `${locale}-u-nu-latn`;
}

export function formatDate(value: Date = new Date(), options: DateFormatOptions = {}): string {
  try {
    return new Intl.DateTimeFormat(withLatinDigits(options.locale), {
      dateStyle: "full",
      timeZone: options.timeZone || undefined,
    }).format(value);
  } catch {
    try {
      return new Intl.DateTimeFormat(DEFAULT_LOCALE, { dateStyle: "full" }).format(value);
    } catch {
      return value.toLocaleDateString();
    }
  }
}

export function formatDateTime(value: string, options: DateFormatOptions = {}): string {
  // Match the approved board's unambiguous table format: YYYY-MM-DD HH:mm (24h).
  try {
    const parts = new Intl.DateTimeFormat("en-CA", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: options.timeZone || undefined,
    }).formatToParts(new Date(value));
    const part = (type: string) => parts.find((item) => item.type === type)?.value ?? "";
    return `${part("year")}-${part("month")}-${part("day")} ${part("hour")}:${part("minute")}`;
  } catch {
    return value;
  }
}

/**
 * Format an API money string without ever converting it to a JS number.
 * The fraction is kept verbatim; grouping applies to the integer part only.
 */
export function formatDecimalString(value: string): string {
  const trimmed = String(value).trim();
  const match = /^(-?)(\d+)(?:\.(\d+))?$/.exec(trimmed);
  if (!match) return trimmed;
  const [, sign, integer, fraction] = match;
  const grouped = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return fraction === undefined ? `${sign}${grouped}` : `${sign}${grouped}.${fraction}`;
}

/** Human-readable text from either error_summary shape, or null. */
export function importErrorMessage(summary: ImportErrorSummary | undefined | null): string | null {
  if (!summary) return null;
  if (typeof summary === "string") return summary.trim() || null;
  return summary.message_ar?.trim() || null;
}
