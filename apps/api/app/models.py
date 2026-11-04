from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


def new_id() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="staff")
    job_title: Mapped[str | None] = mapped_column(String(120))
    can_approve_campaigns: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failed_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index(
    "uq_users_username_lower",
    func.lower(User.username),
    unique=True,
)


class UserSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    csrf_token: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SchoolSettings(Base):
    __tablename__ = "school_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    school_name: Mapped[str] = mapped_column(String(255), nullable=False, default="FeeDesk School")
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="SYP")
    currency_symbol: Mapped[str] = mapped_column(String(12), nullable=False, default="د.س")
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Damascus")
    locale: Mapped[str] = mapped_column(String(20), nullable=False, default="ar-SY")
    contact_phone: Mapped[str | None] = mapped_column(String(40))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    send_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    batch_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_type: Mapped[str] = mapped_column(String(20), nullable=False)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="uploaded", index=True)
    worksheet_name: Mapped[str | None] = mapped_column(String(255))
    available_sheets: Mapped[list[Any] | None] = mapped_column(JsonType)
    column_mapping: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    warnings: Mapped[list[Any] | None] = mapped_column(JsonType)
    error_summary: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    duplicate_reason: Mapped[str | None] = mapped_column(Text)
    total_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    valid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    invalid_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duplicate_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    excluded_rows: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    totals_by_currency: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SourceFile(Base):
    __tablename__ = "source_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    import_batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    uploaded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    retention_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class StagedRow(Base):
    __tablename__ = "staged_rows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    import_batch_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_row_number: Mapped[int | None] = mapped_column(Integer)
    source_page_number: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    raw_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    normalized_data: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    parser_warnings: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    validation_errors: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    is_excluded: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    guardian_resolution_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default="auto", server_default=text("'auto'")
    )
    resolved_guardian_id: Mapped[str | None] = mapped_column(
        ForeignKey("guardians.id", ondelete="SET NULL"), index=True
    )
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Guardian(Base, TimestampMixin):
    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class GuardianContact(Base, TimestampMixin):
    __tablename__ = "guardian_contacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    guardian_id: Mapped[str] = mapped_column(
        ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True
    )
    original_phone: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_phone: Mapped[str | None] = mapped_column(String(20), index=True)
    contact_type: Mapped[str] = mapped_column(String(20), nullable=False, default="mobile")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Student(Base, TimestampMixin):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    student_reference: Mapped[str | None] = mapped_column(String(120), unique=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class GuardianStudentRelationship(Base):
    __tablename__ = "guardian_student_relationships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    guardian_id: Mapped[str] = mapped_column(
        ForeignKey("guardians.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[str] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(40), nullable=False, default="guardian")
    source_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FeeBalance(Base, TimestampMixin):
    __tablename__ = "fee_balances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    guardian_id: Mapped[str] = mapped_column(
        ForeignKey("guardians.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.id", ondelete="SET NULL"))
    import_batch_id: Mapped[str] = mapped_column(
        ForeignKey("import_batches.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_row_id: Mapped[str | None] = mapped_column(
        ForeignKey("staged_rows.id", ondelete="SET NULL")
    )
    fee_period: Mapped[str | None] = mapped_column(String(80))
    total_fee: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    amount_paid: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    remaining_balance_source: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    remaining_balance_calculated: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    record_status: Mapped[str] = mapped_column(String(32), nullable=False, default="confirmed")
    reviewed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MessageTemplate(Base, TimestampMixin):
    __tablename__ = "message_templates"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_message_templates_name_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="ar")
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="sms")
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class Campaign(Base, TimestampMixin):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_import_id: Mapped[str | None] = mapped_column(
        ForeignKey("import_batches.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="sms")
    template_id: Mapped[str | None] = mapped_column(
        ForeignKey("message_templates.id", ondelete="SET NULL")
    )
    template_version: Mapped[int | None] = mapped_column(Integer)
    recipient_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    excluded_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    invalid_contact_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    totals_by_currency: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    warnings: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    excluded_snapshot: Mapped[list[Any]] = mapped_column(
        JsonType, nullable=False, default=list
    )
    preview_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    revision: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    previewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot_hash: Mapped[str | None] = mapped_column(String(64))


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"
    __table_args__ = (
        UniqueConstraint(
            "campaign_id", "guardian_id", "currency_snapshot", name="uq_campaign_guardian_currency"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guardian_id: Mapped[str] = mapped_column(
        ForeignKey("guardians.id", ondelete="RESTRICT"), nullable=False
    )
    destination_phone_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    guardian_name_snapshot: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_snapshot: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency_snapshot: Mapped[str] = mapped_column(String(3), nullable=False)
    fee_details_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    message_body_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    eligibility_status: Mapped[str] = mapped_column(String(32), nullable=False, default="eligible")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ProviderCredential(Base, TimestampMixin):
    __tablename__ = "provider_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    # Fernet ciphertext only. The plaintext key must never be stored or logged.
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text)
    sender_id: Mapped[str | None] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(
        String(32), nullable=False, default="local_sms", server_default=text("'local_sms'")
    )
    key_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default=text("1")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rotated_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    campaign_id: Mapped[str] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True
    )
    campaign_recipient_id: Mapped[str] = mapped_column(
        ForeignKey("campaign_recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="rasel")
    channel: Mapped[str] = mapped_column(String(30), nullable=False, default="local_sms")
    internal_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )
    provider_status: Mapped[str | None] = mapped_column(String(80))
    provider_request_id: Mapped[str | None] = mapped_column(String(120))
    provider_message_id: Mapped[str | None] = mapped_column(String(120), index=True)
    idempotency_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    provider_payload_redacted: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    resend_of_message_id: Mapped[str | None] = mapped_column(
        ForeignKey("messages.id", ondelete="SET NULL")
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    last_error_summary: Mapped[str | None] = mapped_column(Text)


class SendJob(Base, TimestampMixin):
    __tablename__ = "send_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    message_id: Mapped[str] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked_by: Mapped[str | None] = mapped_column(String(120))
    # Fencing token written on every claim. Provider results are applied only
    # when the token/worker/attempt still match, so a worker whose lease was
    # reclaimed can never overwrite the new owner's state.
    claim_token: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)


class ProviderEvent(Base):
    __tablename__ = "provider_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_provider_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    provider: Mapped[str] = mapped_column(String(30), nullable=False, default="rasel")
    provider_event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(120), index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    event_payload_redacted: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    action: Mapped[str] = mapped_column(String(120), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(80))
    before_data: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    after_data: Mapped[dict[str, Any] | None] = mapped_column(JsonType)
    request_id: Mapped[str | None] = mapped_column(String(64))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DashboardMetricDaily(Base):
    __tablename__ = "dashboard_metrics_daily"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    metric_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    totals_by_currency: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    counts: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
