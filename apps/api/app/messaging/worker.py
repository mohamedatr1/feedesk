from __future__ import annotations

import logging
import random
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..audit import record_audit
from ..config import Settings
from ..config import settings as default_settings
from ..models import Campaign, CampaignRecipient, Message, SendJob
from .backoff import compute_backoff_seconds
from .credentials import (
    ResolvedCredentials,
    resolve_rasel_credentials,
)
from .credentials import (
    credential_fingerprint as default_credential_fingerprint,
)
from .factory import (
    build_provider_from_credentials,
    provider_name,
    transport_configuration_error,
)
from .port import ProviderPort
from .status import TERMINAL_MESSAGE_STATUSES, derive_campaign_status
from .types import (
    OUTCOME_ACCEPTED,
    OUTCOME_DELIVERED,
    OUTCOME_FAILED,
    OUTCOME_QUEUED,
    OUTCOME_RATE_LIMITED,
    OUTCOME_UNKNOWN,
    RETRYABLE_OUTCOMES,
    ProviderResult,
)

logger = logging.getLogger("feedesk.worker")

SMS_CHANNELS = frozenset({"sms", "local_sms"})
CLAIMABLE_JOB_STATUSES = frozenset({"pending", "retry"})
SUBMITTED_MESSAGE_STATUSES = frozenset(
    {"provider_accepted", "queued_by_provider", "delivered"}
)


@dataclass
class RunReport:
    claimed: bool
    job_id: str | None = None
    message_id: str | None = None
    outcome: str | None = None
    skipped_reason: str | None = None
    campaign_status: str | None = None


@dataclass
class LoopReport:
    claimed: int = 0
    outcomes: dict[str, int] = field(default_factory=dict)
    stopped: bool = True


@dataclass(frozen=True)
class Claim:
    """A fenced claim: only this token may apply the provider result."""

    job_id: str
    token: str


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


class MessagingWorker:
    """PostgreSQL-backed single-job worker.

    Jobs are claimed with ``FOR UPDATE SKIP LOCKED`` and a lease. The provider
    is injected so tests never touch the network.
    """

    def __init__(
        self,
        *,
        config: Settings | None = None,
        provider: ProviderPort | None = None,
        session_factory: Any = None,
        worker_id: str | None = None,
        rng: random.Random | None = None,
        sleep_fn: Any = None,
        now_fn: Any = None,
        credential_resolver: Any = None,
        provider_factory: Any = None,
        credential_fingerprint: Any = None,
    ) -> None:
        if session_factory is None:
            from ..db import SessionLocal

            session_factory = SessionLocal
        self.config = config or default_settings
        self.session_factory = session_factory
        self.worker_id = worker_id or f"worker-{random.Random().randrange(16**12):012x}"
        self._rng = rng or random.Random()
        self._sleep = sleep_fn or time.sleep
        self._now_fn = now_fn or _utcnow
        self._stop = threading.Event()
        self._config_error = transport_configuration_error(self.config)
        self._resolve_credentials = credential_resolver or resolve_rasel_credentials
        self._build_provider = provider_factory or build_provider_from_credentials
        self._fingerprint = credential_fingerprint or default_credential_fingerprint
        self._credential_error: str | None = None
        self._provider_fingerprint: Any = None
        self._provider_injected = provider is not None
        self.provider = provider
        if (
            self.provider is None
            and self._config_error is None
            and provider_name(self.config) == "fake"
        ):
            # Fake mode has no credentials to resolve; build it eagerly so
            # ``--once`` works without a database read.
            self.provider = self._build_provider(self.config, None)

    # -- safety ---------------------------------------------------------

    def _static_preflight_reason(self) -> str | None:
        if not bool(self.config.messaging_enabled):
            return "messaging_disabled"
        if bool(self.config.messaging_kill_switch):
            return "kill_switch"
        return None

    def _preflight_reason(self) -> str | None:
        reason = self._static_preflight_reason()
        if reason is not None:
            return reason
        if self._config_error is not None:
            return "provider_config_incomplete"
        if self.provider is None:
            return self._credential_error or "provider_unavailable"
        return None

    def _close_provider(self) -> None:
        close = getattr(self.provider, "close", None)
        if close is None:
            return
        try:
            close()
        except Exception:
            # Closing an adapter is best-effort; never surface its details.
            logger.debug("worker.provider_close_failed")

    def _refresh_provider(self, db: Session) -> str | None:
        """Resolve the current credential and rebuild the provider on change.

        The database row is authoritative.  Only a secret-free fingerprint
        (source/key_version/is_active) is compared, so rotation is picked up
        without ever logging the key, sender, or ciphertext.  A revoked or
        unresolvable credential disables the provider instead of falling back
        to environment secrets.
        """
        if provider_name(self.config) == "fake":
            if self.provider is None and self._config_error is None:
                built = self._build_provider(self.config, None)
                if built is not None:
                    self.provider = built
            self._credential_error = None
            return None
        if self._config_error is not None:
            return "provider_config_incomplete"

        resolved: ResolvedCredentials | None = self._resolve_credentials(db)
        fingerprint = self._fingerprint(db)

        if resolved is None:
            self._credential_error = "provider_credential_unavailable"
            self._close_provider()
            self.provider = None
            self._provider_fingerprint = fingerprint
            return self._credential_error

        if (
            self.provider is not None
            and self._provider_injected
            and self._provider_fingerprint is None
        ):
            # An explicitly injected provider is honoured for the current
            # credential generation; later rotation still rebuilds it.
            self._provider_fingerprint = fingerprint
            self._provider_injected = False
            self._credential_error = None
            return None

        if self.provider is None or fingerprint != self._provider_fingerprint:
            built = self._build_provider(self.config, resolved)
            if built is None:
                self._credential_error = "provider_credential_unavailable"
                self._close_provider()
                self.provider = None
                self._provider_fingerprint = fingerprint
                return self._credential_error
            self._close_provider()
            self.provider = built
            self._provider_fingerprint = fingerprint
            self._provider_injected = False
            logger.info(
                "worker.provider_ready provider=%s source=%s key_version=%s",
                provider_name(self.config),
                fingerprint.source,
                fingerprint.key_version,
            )

        self._credential_error = None
        return None

    def _refresh_provider_session(self) -> None:
        with self.session_factory() as db:
            self._refresh_provider(db)

    def _allowlist(self) -> tuple[str, ...]:
        raw = self.config.messaging_allowlist or ""
        return tuple(part.strip() for part in raw.split(",") if part.strip())

    def request_stop(self) -> None:
        """Stop claiming new jobs; the in-flight job is allowed to finish."""
        self._stop.set()

    def stop_requested(self) -> bool:
        return self._stop.is_set()

    # -- claim ----------------------------------------------------------

    def claim_next(self) -> Claim | None:
        now = self._now_fn()
        due = or_(
            and_(
                SendJob.status.in_(tuple(CLAIMABLE_JOB_STATUSES)),
                or_(
                    SendJob.next_attempt_at.is_(None),
                    SendJob.next_attempt_at <= now,
                ),
            ),
            and_(
                SendJob.status == "claimed",
                SendJob.lease_expires_at.is_not(None),
                SendJob.lease_expires_at <= now,
            ),
        )
        statement = (
            select(SendJob)
            .join(Message, SendJob.message_id == Message.id)
            .join(Campaign, Message.campaign_id == Campaign.id)
            .where(
                Campaign.status.in_(("approved", "queued", "sending")),
                due,
            )
            .order_by(
                SendJob.next_attempt_at.asc().nulls_first(),
                SendJob.created_at.asc(),
                SendJob.id.asc(),
            )
            .with_for_update(skip_locked=True, of=SendJob)
            .limit(1)
        )
        claim_token = secrets.token_hex(16)
        with self.session_factory() as db:
            # Refresh before claiming so a rotation/revocation is observed as
            # close to the send as possible.
            self._refresh_provider(db)
            job = db.scalar(statement)
            if job is None:
                db.rollback()
                return None
            job.status = "claimed"
            job.locked_by = self.worker_id
            job.locked_at = now
            job.heartbeat_at = now
            # A fresh token on every claim (including expired-lease reclaim)
            # fences the previous owner out of applying its provider result.
            job.claim_token = claim_token
            job.lease_expires_at = now + timedelta(
                seconds=max(1, int(self.config.messaging_lease_seconds))
            )
            job.attempt_count = (job.attempt_count or 0) + 1
            db.commit()
            return Claim(job_id=job.id, token=claim_token)

    # -- execution ------------------------------------------------------

    def run_once(self) -> RunReport:
        reason = self._static_preflight_reason()
        if reason is not None:
            logger.debug("worker.skip reason=%s", reason)
            return RunReport(claimed=False, skipped_reason=reason)
        self._refresh_provider_session()
        reason = self._preflight_reason()
        if reason is not None:
            logger.debug("worker.skip reason=%s", reason)
            return RunReport(claimed=False, skipped_reason=reason)
        claim = self.claim_next()
        if claim is None:
            return RunReport(claimed=False)
        return self.process_job(claim.job_id, claim.token)

    def process_job(self, job_id: str, claim_token: str | None = None) -> RunReport:
        # Pace before any state transition or database work. If the worker
        # crashes during this sleep the job is still ``claimed`` and the
        # message is still ``pending``, so a lease reclaim can safely retry
        # without being forced into ``submitting``/``unknown``. Pacing is per
        # worker process only: multiple processes each pace independently, so
        # run one worker per provider account unless the provider enforces a
        # global rate.
        self._pace()
        with self.session_factory() as db:
            job = db.get(SendJob, job_id)
            if job is None:
                return RunReport(claimed=False, job_id=job_id, skipped_reason="job_missing")
            if claim_token is None:
                claim_token = job.claim_token
            if not self._owns_claim(job, claim_token):
                return RunReport(
                    claimed=False, job_id=job_id, skipped_reason="claim_lost"
                )
            attempt = job.attempt_count or 1
            message = db.get(Message, job.message_id)
            if message is None:
                job.status = "failed"
                job.last_error = "Message row is missing."
                self._clear_lease(job)
                db.commit()
                return RunReport(claimed=True, job_id=job_id, skipped_reason="message_missing")

            campaign = db.get(Campaign, message.campaign_id)
            recipient = db.get(CampaignRecipient, message.campaign_recipient_id)
            if recipient is None:
                self._fail_without_send(
                    db,
                    job,
                    message,
                    code="RECIPIENT_SNAPSHOT_MISSING",
                    summary="Frozen recipient snapshot is missing.",
                )
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome=OUTCOME_FAILED,
                    skipped_reason="recipient_missing",
                )

            preflight = self._preflight_reason()
            if preflight is not None:
                self._release_claim(db, job, reason=preflight)
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    skipped_reason=preflight,
                )

            if message.internal_status == "cancelled":
                self._cancel_job(db, job, message, reason="Message was cancelled.")
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome="cancelled",
                    skipped_reason="message_cancelled",
                )
            if message.internal_status in TERMINAL_MESSAGE_STATUSES:
                self._finish_existing(db, job, message)
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome=message.internal_status,
                    skipped_reason="message_terminal",
                )
            if message.internal_status == "submitting":
                # The previous owner crashed or lost its lease after handing the
                # message to the provider. The provider may already have sent it,
                # so never call the provider again: require reconciliation.
                self._mark_reconciliation_required(db, job, message)
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome=OUTCOME_UNKNOWN,
                    skipped_reason="reclaimed_submitting",
                )

            if campaign is None or campaign.cancelled_at is not None or campaign.status == "cancelled":
                self._cancel_job(db, job, message, reason="Campaign was cancelled.")
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome="cancelled",
                    skipped_reason="campaign_cancelled",
                )
            if campaign.status not in {"approved", "queued", "sending"}:
                self._release_claim(db, job, reason="campaign_not_active")
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    skipped_reason="campaign_not_active",
                )

            if campaign.channel not in SMS_CHANNELS or message.channel not in SMS_CHANNELS:
                self._fail_without_send(
                    db,
                    job,
                    message,
                    code="UNSUPPORTED_CHANNEL",
                    summary="Only SMS channels are enabled.",
                )
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome=OUTCOME_FAILED,
                    skipped_reason="unsupported_channel",
                )

            allowlist = self._allowlist()
            if allowlist and recipient.destination_phone_snapshot not in allowlist:
                self._fail_without_send(
                    db,
                    job,
                    message,
                    code="RECIPIENT_NOT_ALLOWLISTED",
                    summary="Recipient is not in the messaging allowlist.",
                )
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    outcome=OUTCOME_FAILED,
                    skipped_reason="recipient_not_allowlisted",
                )

            # Re-resolve immediately before handing the message to the provider.
            # If the credential was revoked/rotated while this job was being
            # prepared, release the claim (``pending``) and never mark the
            # message failed: no send has happened yet.
            self._refresh_provider(db)
            credential_reason = self._preflight_reason()
            if credential_reason is not None:
                self._release_claim(db, job, reason=credential_reason)
                db.commit()
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message.id,
                    skipped_reason=credential_reason,
                )

            now = self._now_fn()
            message.internal_status = "submitting"
            job.heartbeat_at = now
            job.lease_expires_at = now + timedelta(
                seconds=max(1, int(self.config.messaging_lease_seconds))
            )
            db.commit()
            to = recipient.destination_phone_snapshot
            text = recipient.message_body_snapshot
            idempotency_key = message.idempotency_key
            message_id = message.id

        # Provider I/O happens outside the database transaction while a
        # background heartbeat keeps the lease alive.
        stop_heartbeat = self._start_heartbeat(job_id, claim_token, attempt)
        try:
            result = self.provider.send(
                to=to,
                text=text,
                idempotency_key=idempotency_key,
                channel="local_sms",
            )
        except Exception:
            logger.warning(
                "worker.provider_exception job_id=%s message_id=%s", job_id, message_id
            )
            result = ProviderResult(
                outcome=OUTCOME_UNKNOWN,
                error_code="WORKER_EXCEPTION",
                error_summary="Provider call failed; outcome unknown.",
                payload_redacted={"provider": "unknown"},
            )
        finally:
            stop_heartbeat()

        with self.session_factory() as db:
            job = db.scalar(
                select(SendJob).where(SendJob.id == job_id).with_for_update()
            )
            message = db.get(Message, message_id)
            if job is None or message is None:
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message_id,
                    skipped_reason="context_missing_after_send",
                )
            if not self._owns_claim(job, claim_token, attempt):
                # A different worker/token/attempt owns the job now (lease
                # reclaim, cancellation, or manual intervention). Never
                # overwrite its state and never resend; keep the observed
                # provider outcome only in the audit trail.
                self._audit_fenced_result(
                    db, job, message, result, claim_token=claim_token, attempt=attempt
                )
                db.commit()
                logger.warning(
                    "worker.result_fenced job_id=%s message_id=%s outcome=%s",
                    job_id,
                    message_id,
                    result.outcome,
                )
                return RunReport(
                    claimed=True,
                    job_id=job_id,
                    message_id=message_id,
                    outcome=OUTCOME_UNKNOWN,
                    skipped_reason="result_fenced",
                )
            campaign_status = self._apply_result(db, job, message, result)
            db.commit()
            logger.info(
                "worker.result job_id=%s message_id=%s outcome=%s",
                job_id,
                message_id,
                result.outcome,
            )
            return RunReport(
                claimed=True,
                job_id=job_id,
                message_id=message_id,
                outcome=result.outcome,
                campaign_status=campaign_status,
            )

    # -- lifecycle helpers ---------------------------------------------

    def _pace(self) -> None:
        """Sleep one provider pacing interval before a send."""
        rate = float(self.config.messaging_rate_limit_per_second or 0)
        if rate > 0:
            self._sleep(1.0 / rate)

    def _start_heartbeat(
        self, job_id: str, claim_token: str, attempt: int
    ) -> Any:
        lease_seconds = max(1, int(self.config.messaging_lease_seconds))
        interval = max(0.1, min(30.0, lease_seconds / 3))
        stop = threading.Event()

        def _beat() -> None:
            while not stop.wait(interval):
                try:
                    with self.session_factory() as db:
                        job = db.get(SendJob, job_id)
                        if not self._owns_claim(job, claim_token, attempt):
                            return
                        assert job is not None
                        now = self._now_fn()
                        job.heartbeat_at = now
                        job.lease_expires_at = now + timedelta(seconds=lease_seconds)
                        db.commit()
                except Exception:
                    return

        thread = threading.Thread(
            target=_beat,
            name=f"feedesk-heartbeat-{job_id[:8]}",
            daemon=True,
        )
        thread.start()

        def _stop() -> None:
            stop.set()
            thread.join(timeout=interval + 1)

        return _stop

    def _owns_claim(
        self, job: SendJob | None, claim_token: str | None, attempt: int | None = None
    ) -> bool:
        if job is None or claim_token is None:
            return False
        return (
            job.status == "claimed"
            and job.locked_by == self.worker_id
            and job.claim_token == claim_token
            and (attempt is None or (job.attempt_count or 0) == attempt)
        )

    @staticmethod
    def _clear_lease(job: SendJob) -> None:
        job.locked_by = None
        job.locked_at = None
        job.heartbeat_at = None
        job.lease_expires_at = None
        job.claim_token = None

    def _release_claim(self, db: Session, job: SendJob, *, reason: str) -> None:
        job.status = "pending"
        job.attempt_count = max(0, (job.attempt_count or 0) - 1)
        job.last_error = reason
        self._clear_lease(job)

    def _cancel_job(
        self, db: Session, job: SendJob, message: Message, *, reason: str
    ) -> None:
        job.status = "cancelled"
        job.attempt_count = max(0, (job.attempt_count or 0) - 1)
        job.last_error = reason
        job.next_attempt_at = None
        self._clear_lease(job)
        message.internal_status = "cancelled"
        self._audit_message(
            db,
            message,
            action="message.cancelled",
            job=job,
            attempt=job.attempt_count,
            outcome="cancelled",
            error_code=None,
        )
        self._derive(db, message.campaign_id)

    def _finish_existing(self, db: Session, job: SendJob, message: Message) -> None:
        if message.internal_status in SUBMITTED_MESSAGE_STATUSES:
            job.status = "completed"
        elif message.internal_status == "unknown":
            job.status = "unknown"
        else:
            job.status = "failed"
        job.attempt_count = max(0, (job.attempt_count or 0) - 1)
        job.next_attempt_at = None
        self._clear_lease(job)
        self._derive(db, message.campaign_id)

    def _mark_reconciliation_required(
        self, db: Session, job: SendJob, message: Message
    ) -> None:
        code = "RECONCILIATION_REQUIRED"
        summary = (
            "Message was already submitting when its lease was reclaimed; "
            "provider outcome is unknown and must be reconciled. No resend."
        )
        job.status = "unknown"
        job.attempt_count = max(0, (job.attempt_count or 0) - 1)
        job.last_error = summary
        job.next_attempt_at = None
        self._clear_lease(job)
        message.internal_status = "unknown"
        message.last_error_code = code
        message.last_error_summary = summary
        self._audit_message(
            db,
            message,
            action="message.unknown",
            job=job,
            attempt=job.attempt_count,
            outcome=OUTCOME_UNKNOWN,
            error_code=code,
        )
        self._derive(db, message.campaign_id)

    def _audit_fenced_result(
        self,
        db: Session,
        job: SendJob,
        message: Message,
        result: ProviderResult,
        *,
        claim_token: str,
        attempt: int,
    ) -> None:
        """Record a late/foreign provider result without mutating any state."""
        record_audit(
            db,
            request=None,
            actor_user_id=None,
            action="message.result_discarded",
            entity_type="message",
            entity_id=message.id,
            after={
                "campaign_id": message.campaign_id,
                "observed_outcome": result.outcome,
                "observed_error_code": result.error_code,
                "reason": "claim_fenced",
                "internal_status": message.internal_status,
                "job_status": job.status,
                "attempt": attempt,
                "claim_token_present": bool(claim_token),
            },
        )

    def _fail_without_send(
        self,
        db: Session,
        job: SendJob,
        message: Message,
        *,
        code: str,
        summary: str,
    ) -> None:
        now = self._now_fn()
        job.status = "failed"
        job.attempt_count = max(0, (job.attempt_count or 0) - 1)
        job.last_error = summary
        job.next_attempt_at = None
        self._clear_lease(job)
        message.internal_status = "failed"
        message.last_error_code = code
        message.last_error_summary = summary
        message.failed_at = now
        self._audit_message(
            db,
            message,
            action="message.failed",
            job=job,
            attempt=job.attempt_count,
            outcome=OUTCOME_FAILED,
            error_code=code,
        )
        self._derive(db, message.campaign_id)
        db.commit()

    def _audit_message(
        self,
        db: Session,
        message: Message,
        *,
        action: str,
        job: SendJob,
        attempt: int,
        outcome: str,
        error_code: str | None,
    ) -> None:
        """Record a worker operation without phones, bodies, or credentials."""
        record_audit(
            db,
            request=None,
            actor_user_id=None,
            action=action,
            entity_type="message",
            entity_id=message.id,
            after={
                "campaign_id": message.campaign_id,
                "outcome": outcome,
                "internal_status": message.internal_status,
                "job_status": job.status,
                "attempt": attempt,
                "provider_status": message.provider_status,
                "provider_message_id": message.provider_message_id,
                "error_code": error_code,
                "next_attempt_at": _iso(job.next_attempt_at),
            },
        )

    def _derive(self, db: Session, campaign_id: str) -> str | None:
        # The session factory disables autoflush; persist job/message changes
        # before the derivation query counts them.
        db.flush()
        return derive_campaign_status(db, campaign_id)

    def _apply_result(
        self,
        db: Session,
        job: SendJob,
        message: Message,
        result: ProviderResult,
    ) -> str | None:
        now = self._now_fn()
        attempt = job.attempt_count or 1

        if result.provider_status:
            message.provider_status = result.provider_status
        if result.request_id:
            message.provider_request_id = result.request_id
        if result.provider_message_id:
            message.provider_message_id = result.provider_message_id
        message.provider_payload_redacted = dict(result.payload_redacted or {})

        job.next_attempt_at = None
        self._clear_lease(job)

        if result.outcome in {OUTCOME_DELIVERED, OUTCOME_ACCEPTED, OUTCOME_QUEUED}:
            job.status = "completed"
            job.last_error = None
            message.last_error_code = None
            message.last_error_summary = None
            message.submitted_at = message.submitted_at or now
            if result.outcome == OUTCOME_DELIVERED:
                message.internal_status = "delivered"
                message.delivered_at = now
            elif result.outcome == OUTCOME_QUEUED:
                message.internal_status = "queued_by_provider"
            else:
                message.internal_status = "provider_accepted"
        elif result.outcome == OUTCOME_FAILED:
            job.status = "failed"
            job.last_error = result.error_summary or "Provider rejected the message."
            message.internal_status = "failed"
            message.failed_at = now
            message.last_error_code = result.error_code or "PROVIDER_FAILED"
            message.last_error_summary = (
                result.error_summary or "Provider rejected the message."
            )
        elif result.outcome in RETRYABLE_OUTCOMES:
            self._apply_retry(db, job, message, result, attempt=attempt, now=now)
            action = "message.retry" if job.status == "retry" else "message.failed"
            self._audit_message(
                db,
                message,
                action=action,
                job=job,
                attempt=attempt,
                outcome=result.outcome,
                error_code=result.error_code,
            )
            return self._derive(db, message.campaign_id)
        else:
            job.status = "unknown"
            job.last_error = (
                result.error_summary or "Provider outcome is unknown; no resend."
            )
            message.internal_status = "unknown"
            message.last_error_code = result.error_code or "UNKNOWN_OUTCOME"
            message.last_error_summary = (
                result.error_summary or "Provider outcome is unknown; no resend."
            )

        if message.internal_status == "failed":
            action = "message.failed"
        elif message.internal_status == "unknown":
            action = "message.unknown"
        else:
            action = "message.provider_response"
        self._audit_message(
            db,
            message,
            action=action,
            job=job,
            attempt=attempt,
            outcome=result.outcome,
            error_code=result.error_code,
        )
        return self._derive(db, message.campaign_id)

    def _apply_retry(
        self,
        db: Session,
        job: SendJob,
        message: Message,
        result: ProviderResult,
        *,
        attempt: int,
        now: datetime,
    ) -> None:
        max_attempts = max(1, int(self.config.messaging_max_attempts))
        code = result.error_code or (
            "RATE_LIMITED"
            if result.outcome == OUTCOME_RATE_LIMITED
            else "TEMPORARY_ERROR"
        )
        summary = result.error_summary or "Provider temporary failure."
        if attempt >= max_attempts:
            job.status = "failed"
            job.last_error = summary
            message.internal_status = "failed"
            message.failed_at = now
            message.last_error_code = code
            message.last_error_summary = summary
            return

        delay = compute_backoff_seconds(attempt, rng=self._rng)
        if result.retry_after_seconds is not None:
            delay = max(delay, float(result.retry_after_seconds))
        job.status = "retry"
        job.next_attempt_at = now + timedelta(seconds=max(0.0, delay))
        job.last_error = summary
        message.internal_status = "pending"
        message.last_error_code = code
        message.last_error_summary = summary

    # -- loop -----------------------------------------------------------

    def run_loop(
        self,
        *,
        stop_event: threading.Event | None = None,
        poll_interval: float = 1.0,
        max_jobs: int | None = None,
    ) -> LoopReport:
        report = LoopReport()
        while True:
            if self._stop.is_set():
                break
            if stop_event is not None and stop_event.is_set():
                break
            result = self.run_once()
            if result.claimed:
                report.claimed += 1
                key = result.outcome or result.skipped_reason or "unknown"
                report.outcomes[key] = report.outcomes.get(key, 0) + 1
                if max_jobs is not None and report.claimed >= max_jobs:
                    break
                # Pacing happens in ``process_job`` immediately before the
                # provider call, so ``run_loop`` must not sleep again.
            else:
                wait_for = max(0.05, float(poll_interval))
                if stop_event is not None:
                    stop_event.wait(wait_for)
                else:
                    self._stop.wait(wait_for)
        return report
