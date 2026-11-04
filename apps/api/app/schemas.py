from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_CURRENCY_PATTERN = re.compile(r"^[A-Z]{3}$")
_SETTINGS_REQUIRED_FIELDS = (
    "school_name",
    "default_currency",
    "currency_symbol",
    "timezone",
    "locale",
    "send_limit",
    "batch_limit",
)


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str | None = None
    role: str
    job_title: str | None = None
    can_approve_campaigns: bool = False
    is_active: bool
    must_change_password: bool


class LoginResponse(BaseModel):
    user: UserOut
    permissions: list[str]
    csrf_token: str


class MeResponse(LoginResponse):
    pass


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=12, max_length=200)
    email: str | None = Field(default=None, max_length=255)
    role: str = Field(default="staff", pattern="^(admin|staff)$")
    job_title: str | None = Field(default=None, max_length=120)
    can_approve_campaigns: bool = False


class UserUpdate(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, pattern="^(admin|staff)$")
    job_title: str | None = Field(default=None, max_length=120)
    can_approve_campaigns: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _reject_null_required(self) -> UserUpdate:
        for field in ("role", "is_active", "can_approve_campaigns"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class PasswordResetResponse(BaseModel):
    temporary_password: str
    must_change_password: bool = True


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=12, max_length=200)


class SchoolSettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    school_name: str
    default_currency: str
    currency_symbol: str
    timezone: str
    locale: str
    contact_phone: str | None = None
    contact_email: str | None = None
    send_limit: int
    batch_limit: int
    updated_at: datetime | None = None


class SchoolSettingsUpdate(BaseModel):
    school_name: str | None = Field(default=None, min_length=2, max_length=255)
    default_currency: str | None = Field(default=None, min_length=3, max_length=3)
    currency_symbol: str | None = Field(default=None, min_length=1, max_length=12)
    timezone: str | None = Field(default=None, max_length=64)
    locale: str | None = Field(default=None, max_length=20)
    contact_phone: str | None = Field(default=None, max_length=40)
    contact_email: str | None = Field(default=None, max_length=255)
    send_limit: int | None = Field(default=None, ge=1, le=10000)
    batch_limit: int | None = Field(default=None, ge=1, le=10000)

    @field_validator("default_currency")
    @classmethod
    def _validate_currency(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if not _CURRENCY_PATTERN.fullmatch(normalized):
            raise ValueError("default_currency must be a 3-letter ISO 4217 code.")
        return normalized

    @field_validator("timezone")
    @classmethod
    def _validate_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        try:
            ZoneInfo(normalized)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("timezone must be a valid IANA timezone.") from None
        return normalized

    @model_validator(mode="after")
    def _reject_null_required(self) -> SchoolSettingsUpdate:
        for field in _SETTINGS_REQUIRED_FIELDS:
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class AuditEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    actor_user_id: str | None
    action: str
    entity_type: str
    entity_id: str | None
    before_data: dict[str, Any] | None
    after_data: dict[str, Any] | None
    request_id: str | None
    created_at: datetime


class AuditListOut(BaseModel):
    items: list[AuditEventOut]
    total: int
    page: int
    page_size: int


class HealthOut(BaseModel):
    status: str
    service: str
    database: str | None = None


# --- Import (M2) -----------------------------------------------------------


class ImportWarningOut(BaseModel):
    code: str
    message_ar: str
    severity: str


class ValidationIssueOut(BaseModel):
    code: str
    field: str
    message_ar: str
    severity: str


class ImportBatchSummaryOut(BaseModel):
    id: str
    source_filename: str
    file_type: str
    status: str
    worksheet_name: str | None = None
    available_sheets: list[str] = Field(default_factory=list)
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    excluded_rows: int = 0
    totals_by_currency: dict[str, str] = Field(default_factory=dict)
    max_upload_mb: float
    warnings: list[ImportWarningOut] = Field(default_factory=list)
    uploaded_by: str | None = None
    uploaded_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None


class ImportDetailOut(ImportBatchSummaryOut):
    source_file_id: str | None = None
    available_headers: list[str] = Field(default_factory=list)
    column_mapping: dict[str, str] = Field(default_factory=dict)
    error_summary: dict[str, Any] | None = None
    confirmed_by: str | None = None
    duplicate_reason: str | None = None


class StagedRowOut(BaseModel):
    id: str
    source_row_number: int | None = None
    source_page_number: int | None = None
    normalized_data: dict[str, Any]
    validation_status: str
    validation_errors: list[ValidationIssueOut] = Field(default_factory=list)
    is_excluded: bool
    guardian_resolution_mode: str = "auto"
    resolved_guardian_id: str | None = None


class ImportListOut(BaseModel):
    items: list[ImportBatchSummaryOut]
    total: int
    page: int
    page_size: int


class ImportRowsOut(BaseModel):
    items: list[StagedRowOut]
    total: int
    page: int
    page_size: int


class ImportProcessRequest(BaseModel):
    worksheet_name: str | None = Field(default=None, max_length=255)
    mapping: dict[str, str] | None = None


class GuardianResolutionPatch(BaseModel):
    mode: Literal["auto", "link_existing", "create_new"]
    guardian_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def _require_guardian_for_link(self) -> GuardianResolutionPatch:
        if self.mode == "link_existing" and not (self.guardian_id or "").strip():
            raise ValueError("guardian_id is required for link_existing.")
        return self


class ImportRowPatch(BaseModel):
    normalized_data: dict[str, Any] | None = None
    is_excluded: bool | None = None
    guardian_resolution: GuardianResolutionPatch | None = None

    @model_validator(mode="after")
    def _require_change(self) -> ImportRowPatch:
        if (
            self.normalized_data is None
            and self.is_excluded is None
            and self.guardian_resolution is None
        ):
            raise ValueError(
                "normalized_data, is_excluded or guardian_resolution is required."
            )
        return self


class ImportRowsBulkExclusionRequest(BaseModel):
    is_excluded: bool
    scope: Literal["invalid", "selected"]
    row_ids: list[str] = Field(default_factory=list)


class ImportConfirmRequest(BaseModel):
    acknowledge_warnings: bool = False


# --- Campaigns and templates (M3) -----------------------------------------


class NoticeOut(BaseModel):
    code: str
    message_ar: str
    count: int | None = None


class ReasonOut(BaseModel):
    code: str
    message_ar: str


class TemplateVariableOut(BaseModel):
    name: str
    label: str
    fallback: str | None = None


class TemplateVariablesOut(BaseModel):
    variables: list[TemplateVariableOut]


class TemplateSummaryOut(BaseModel):
    id: str
    name: str
    language: str
    channel: str
    version: int
    is_active: bool
    body_preview: str
    unknown_variables: list[str] = Field(default_factory=list)
    created_by_name: str | None = None
    created_at: datetime


class TemplateDetailOut(TemplateSummaryOut):
    template_body: str


class TemplateListOut(BaseModel):
    items: list[TemplateSummaryOut]
    total: int
    page: int
    page_size: int


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    language: str = Field(default="ar", min_length=2, max_length=10)
    channel: str = Field(default="sms", min_length=2, max_length=30)
    template_body: str = Field(min_length=1)

    @field_validator("name", "template_body")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("language", "channel")
    @classmethod
    def _normalized_code(cls, value: str) -> str:
        return value.strip().lower()


class CampaignRecipientOut(BaseModel):
    id: str | None = None
    key: str
    guardian_id: str
    guardian_name: str
    phone: str
    phone_masked: str | None = None
    student_names: list[str] = Field(default_factory=list)
    student_count: int = 0
    fee_periods: list[str] = Field(default_factory=list)
    amount: str
    currency: str
    message: str
    validation_status: str
    warnings: list[ReasonOut] = Field(default_factory=list)
    fee_balance_ids: list[str] = Field(default_factory=list)


class ExcludedRecordOut(BaseModel):
    guardian_id: str
    guardian_name: str
    phone: str | None = None
    phone_masked: str | None = None
    amount: str
    currency: str | None = None
    reasons: list[ReasonOut] = Field(default_factory=list)
    fee_balance_ids: list[str] = Field(default_factory=list)
    key: str | None = None


class CampaignSummaryOut(BaseModel):
    id: str
    name: str
    status: str
    channel: str
    source_import_id: str | None = None
    source_filename: str | None = None
    template_id: str | None = None
    template_name: str | None = None
    template_version: int | None = None
    recipient_count: int
    excluded_count: int
    invalid_contact_count: int
    totals_by_currency: dict[str, str] = Field(default_factory=dict)
    warnings: list[NoticeOut] = Field(default_factory=list)
    created_by: str | None = None
    created_by_name: str | None = None
    created_at: datetime
    updated_at: datetime
    submitted_at: datetime | None = None
    approved_by: str | None = None
    approved_by_name: str | None = None
    approved_at: datetime | None = None
    cancelled_at: datetime | None = None
    cancelled_by: str | None = None
    cancel_reason: str | None = None
    snapshot_hash: str | None = None
    revision: int = 0


class CampaignDetailOut(CampaignSummaryOut):
    template_body: str | None = None
    previewed_at: datetime | None = None
    blocking_reasons: list[NoticeOut] = Field(default_factory=list)
    recipients: list[CampaignRecipientOut] = Field(default_factory=list)
    excluded: list[ExcludedRecordOut] = Field(default_factory=list)
    can_submit: bool = False
    can_approve: bool = False
    can_cancel: bool = False
    message_count: int = 0
    pending_job_count: int = 0


class CampaignListOut(BaseModel):
    items: list[CampaignSummaryOut]
    total: int
    page: int
    page_size: int


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    source_import_id: str = Field(min_length=1, max_length=36)
    template_id: str | None = Field(default=None, max_length=36)

    @field_validator("name")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class CampaignUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    template_id: str | None = Field(default=None, max_length=36)

    @field_validator("name")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def _require_change(self) -> CampaignUpdate:
        if self.name is None and self.template_id is None:
            raise ValueError("name or template_id is required.")
        return self


class CampaignSubmitRequest(BaseModel):
    expected_revision: int = Field(ge=0)


class CampaignApproveRequest(BaseModel):
    expected_revision: int = Field(ge=0)
    acknowledge_warnings: bool = False


class CampaignCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)
    expected_revision: int | None = Field(default=None, ge=0)


# --- Messages and campaign results (M4) -----------------------------------


class MessageSummaryOut(BaseModel):
    id: str
    campaign_id: str
    campaign_name: str
    guardian_name: str
    destination_phone_masked: str
    amount: str
    currency: str
    channel: str
    internal_status: str
    provider_status: str | None = None
    provider_message_id: str | None = None
    last_error_code: str | None = None
    last_error_summary: str | None = None
    submitted_at: datetime | None = None
    delivered_at: datetime | None = None
    next_attempt_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MessageDetailOut(MessageSummaryOut):
    destination_phone: str
    message_body_snapshot: str
    provider_request_id: str | None = None
    provider_payload_redacted: dict[str, Any] = Field(default_factory=dict)
    attempt_count: int = 0


class MessageListOut(BaseModel):
    items: list[MessageSummaryOut]
    total: int
    page: int
    page_size: int


class CampaignResultsOut(CampaignSummaryOut):
    message_count: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    last_activity_at: datetime | None = None
    delivery_note_ar: str = "قبول المزوّد لا يعني التسليم. تظهر الحالات المؤكدة فقط."


# --- Provider credential vault and safe test-send (M4) ---------------------


class ProviderStatusOut(BaseModel):
    provider: str
    configured: bool
    credential_source: str
    credential_error: str | None = None
    sender_id: str | None = None
    channel: str | None = None
    key_version: int | None = None
    rotated_at: datetime | None = None
    rotated_by_name: str | None = None
    test_send_mode: str
    live_send_available: bool = False


class ProviderCredentialUpdate(BaseModel):
    api_key: str = Field(min_length=1, max_length=4096)
    sender_id: str = Field(min_length=1, max_length=64)
    channel: str = Field(default="local_sms", max_length=32)

    @field_validator("api_key", "sender_id")
    @classmethod
    def _strip_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("channel")
    @classmethod
    def _validate_channel(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local_sms", "sms"}:
            raise ValueError("channel must be 'local_sms' or 'sms'")
        return normalized


class TestSendRequest(BaseModel):
    recipient: str = Field(min_length=1, max_length=32)
    message: str = Field(min_length=1, max_length=4096)

    @field_validator("recipient", "message")
    @classmethod
    def _strip_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class TestSendOut(BaseModel):
    provider: str
    dry_run: bool
    outcome: str
    provider_status: str | None = None
    error_code: str | None = None
    error_summary: str | None = None
    provider_message_id: str | None = None
    recipient_masked: str
    sent_at: datetime


class MessagingBalanceOut(BaseModel):
    provider: str
    available: bool
    balance: str | None = None
    currency: str | None = None
    preflight: bool = True
    reason: str | None = None
