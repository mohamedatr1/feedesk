from __future__ import annotations

import json
import logging
import random
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import delete, select, update

from app.config import settings
from app.db import SessionLocal
from app.messaging.credentials import revoke_credential, upsert_credential
from app.messaging.fake import FakeProvider
from app.messaging.status import derive_campaign_status
from app.messaging.worker import MessagingWorker
from app.models import AuditEvent, Campaign, Message, ProviderCredential, SendJob

from .campaign_helpers import clean_campaign_tables
from .messaging_helpers import create_campaign_messages, messaging_config, utcnow


@pytest.fixture(autouse=True)
def campaign_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        settings, "provider_credential_key", Fernet.generate_key().decode()
    )
    _clear_credentials()
    clean_campaign_tables()
    yield
    clean_campaign_tables()
    _clear_credentials()


def _clear_credentials() -> None:
    with SessionLocal() as db:
        db.execute(delete(ProviderCredential))
        db.commit()


def _store_credential(
    *,
    api_key: str = "db-secret-key",
    sender_id: str = "DB-SENDER",
    channel: str = "local_sms",
) -> None:
    with SessionLocal() as db:
        upsert_credential(
            db,
            api_key=api_key,
            sender_id=sender_id,
            channel=channel,
        )
        db.commit()


def _worker(
    provider: FakeProvider | None = None,
    *,
    scenario: str = "delivered",
    **config_updates: object,
) -> tuple[MessagingWorker, FakeProvider]:
    fake = provider or FakeProvider(scenario=scenario)
    worker = MessagingWorker(
        config=messaging_config(**config_updates),
        provider=fake,
        session_factory=SessionLocal,
        rng=random.Random(7),
        sleep_fn=lambda _seconds: None,
    )
    return worker, fake


def _state(message_id: str) -> tuple[Message, SendJob, Campaign]:
    with SessionLocal() as db:
        message = db.get(Message, message_id)
        assert message is not None
        job = db.scalar(select(SendJob).where(SendJob.message_id == message_id))
        assert job is not None
        campaign = db.get(Campaign, message.campaign_id)
        assert campaign is not None
        return message, job, campaign


@pytest.mark.parametrize(
    ("scenario", "message_status", "job_status", "campaign_status"),
    [
        ("delivered", "delivered", "completed", "completed"),
        ("accepted", "provider_accepted", "completed", "completed"),
        ("queued", "queued_by_provider", "completed", "completed"),
        ("failed", "failed", "failed", "failed"),
        ("duplicate", "provider_accepted", "completed", "completed"),
        ("timeout", "unknown", "unknown", "completed_with_errors"),
        ("insufficient_balance", "failed", "failed", "failed"),
        ("invalid_recipient", "failed", "failed", "failed"),
    ],
)
def test_worker_applies_scenario_outcomes(
    scenario: str,
    message_status: str,
    job_status: str,
    campaign_status: str,
) -> None:
    created = create_campaign_messages()
    worker, fake = _worker(scenario=scenario)

    report = worker.run_once()

    assert report.claimed is True
    assert report.outcome is not None
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == message_status
    assert job.status == job_status
    assert campaign.status == campaign_status
    assert fake.send_count == 1
    assert job.locked_by is None
    assert job.lease_expires_at is None

    # A second pass must not resend a terminal/unknown message.
    again = worker.run_once()
    assert again.claimed is False
    assert fake.send_count == 1


def test_provider_acceptance_is_not_delivery() -> None:
    created = create_campaign_messages()
    worker, _ = _worker(scenario="accepted")

    worker.run_once()

    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "provider_accepted"
    assert message.provider_status == "accepted"
    assert message.submitted_at is not None
    assert message.delivered_at is None
    assert message.provider_payload_redacted == {
        "provider": "fake",
        "scenario": "accepted",
        "channel": "local_sms",
    }
    assert job.status == "completed"
    assert campaign.status == "completed"


def test_worker_audit_records_outcome_without_phone_or_body() -> None:
    created = create_campaign_messages(
        [{"phone": "+963993000701", "body": "نص رسالة سري للغاية"}]
    )
    worker, _ = _worker(scenario="delivered")

    worker.run_once()

    with SessionLocal() as db:
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.entity_id == created["message_ids"][0]
                )
            ).all()
        )
    assert events
    actions = {event.action for event in events}
    assert "message.provider_response" in actions
    serialized = json.dumps(
        [event.after_data for event in events], ensure_ascii=False
    )
    assert "+963993000701" not in serialized
    assert "نص رسالة سري للغاية" not in serialized
    assert "api_key" not in serialized.lower()


def test_worker_duplicate_execution_keeps_one_logical_send() -> None:
    created = create_campaign_messages()
    worker, fake = _worker(scenario="delivered")

    assert worker.run_once().claimed is True
    assert worker.run_once().claimed is False

    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "delivered"
    assert job.attempt_count == 1
    assert fake.send_count == 1


def test_worker_rate_limit_retries_with_backoff_then_fails() -> None:
    created = create_campaign_messages()
    worker, fake = _worker(scenario="rate_limited", messaging_max_attempts=3)

    first = worker.run_once()
    assert first.claimed is True
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "pending"
    assert job.status == "retry"
    assert job.attempt_count == 1
    assert job.next_attempt_at is not None
    assert job.next_attempt_at > utcnow()
    assert campaign.status == "sending"

    for expected_attempt in (2, 3):
        with SessionLocal() as db:
            db.execute(
                update(SendJob)
                .where(SendJob.id == job.id)
                .values(next_attempt_at=utcnow() - timedelta(seconds=1))
            )
            db.commit()
        report = worker.run_once()
        assert report.claimed is True
        message, job, campaign = _state(created["message_ids"][0])
        assert job.attempt_count == expected_attempt

    assert message.internal_status == "failed"
    assert job.status == "failed"
    assert campaign.status == "failed"
    assert fake.send_count == 1


def test_worker_temporary_error_retries_then_fails() -> None:
    created = create_campaign_messages()
    worker, _ = _worker(scenario="temporary_error", messaging_max_attempts=2)

    worker.run_once()
    _, job, _ = _state(created["message_ids"][0])
    assert job.status == "retry"

    with SessionLocal() as db:
        db.execute(
            update(SendJob)
            .where(SendJob.id == job.id)
            .values(next_attempt_at=utcnow() - timedelta(seconds=1))
        )
        db.commit()
    worker.run_once()
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "failed"
    assert job.status == "failed"
    assert campaign.status == "failed"


@pytest.mark.parametrize(
    ("enabled", "kill_switch", "reason"),
    [
        (False, False, "messaging_disabled"),
        (True, True, "kill_switch"),
    ],
)
def test_worker_refuses_when_disabled_or_kill_switched(
    enabled: bool, kill_switch: bool, reason: str
) -> None:
    created = create_campaign_messages()
    worker, fake = _worker(
        messaging_enabled=enabled, messaging_kill_switch=kill_switch
    )

    report = worker.run_once()

    assert report.claimed is False
    assert report.skipped_reason == reason
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "pending"
    assert job.status == "pending"
    assert job.attempt_count == 0
    assert fake.send_count == 0


def test_worker_refuses_incomplete_rasel_config() -> None:
    created = create_campaign_messages()
    worker = MessagingWorker(
        config=messaging_config(
            messaging_provider="rasel",
            rasel_api_key="",
            rasel_sender_id="",
        ),
        provider=None,
        session_factory=SessionLocal,
        sleep_fn=lambda _seconds: None,
    )

    report = worker.run_once()

    assert report.claimed is False
    assert report.skipped_reason == "provider_credential_unavailable"
    _, job, _ = _state(created["message_ids"][0])
    assert job.status == "pending"


def test_worker_does_not_claim_cancelled_campaign_jobs() -> None:
    created = create_campaign_messages(campaign_status="cancelled")
    worker, fake = _worker()

    report = worker.run_once()

    assert report.claimed is False
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "pending"
    assert job.status == "pending"
    assert fake.send_count == 0


def test_worker_cancels_cancelled_message_without_sending() -> None:
    created = create_campaign_messages([{"message_status": "cancelled"}])
    worker, fake = _worker()

    report = worker.run_once()

    assert report.skipped_reason == "message_cancelled"
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "cancelled"
    assert job.status == "cancelled"
    assert job.attempt_count == 0
    assert fake.send_count == 0


def test_worker_completes_already_delivered_message_without_resend() -> None:
    created = create_campaign_messages(
        [{"message_status": "delivered", "delivered_at": utcnow()}]
    )
    worker, fake = _worker()

    report = worker.run_once()

    assert report.skipped_reason == "message_terminal"
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "delivered"
    assert job.status == "completed"
    assert fake.send_count == 0


def test_worker_hard_disables_non_sms_channels() -> None:
    created = create_campaign_messages([{"channel": "whatsapp"}])
    worker, fake = _worker()

    report = worker.run_once()

    assert report.skipped_reason == "unsupported_channel"
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "failed"
    assert message.last_error_code == "UNSUPPORTED_CHANNEL"
    assert job.status == "failed"
    assert campaign.status == "failed"
    assert fake.send_count == 0


def test_worker_honors_allowlist() -> None:
    created = create_campaign_messages([{"phone": "+963993000701"}])
    worker, fake = _worker(messaging_allowlist="+963993000999")

    report = worker.run_once()

    assert report.skipped_reason == "recipient_not_allowlisted"
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "failed"
    assert message.last_error_code == "RECIPIENT_NOT_ALLOWLISTED"
    assert job.status == "failed"
    assert fake.send_count == 0


def test_worker_reclaims_expired_lease() -> None:
    created = create_campaign_messages(
        [
            {
                "job_status": "claimed",
                "attempt_count": 1,
                "locked_by": "dead-worker",
                "locked_at": utcnow() - timedelta(minutes=5),
                "heartbeat_at": utcnow() - timedelta(minutes=5),
                "lease_expires_at": utcnow() - timedelta(minutes=1),
            }
        ]
    )
    worker, fake = _worker(scenario="delivered")

    report = worker.run_once()

    assert report.claimed is True
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "delivered"
    assert job.status == "completed"
    assert job.attempt_count == 2
    assert campaign.status == "completed"
    assert fake.send_count == 1


def test_reclaimed_submitting_message_becomes_unknown_without_resend() -> None:
    created = create_campaign_messages(
        [
            {
                "message_status": "submitting",
                "job_status": "claimed",
                "attempt_count": 1,
                "locked_by": "dead-worker",
                "claim_token": "expired-token",
                "locked_at": utcnow() - timedelta(minutes=5),
                "heartbeat_at": utcnow() - timedelta(minutes=5),
                "lease_expires_at": utcnow() - timedelta(minutes=1),
            }
        ]
    )
    worker, fake = _worker(scenario="delivered")

    report = worker.run_once()

    assert report.claimed is True
    assert report.skipped_reason == "reclaimed_submitting"
    assert report.outcome == "unknown"
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "unknown"
    assert message.last_error_code == "RECONCILIATION_REQUIRED"
    assert job.status == "unknown"
    assert job.claim_token is None
    assert campaign.status == "completed_with_errors"
    # The provider must never be called again for a submitting message.
    assert fake.send_count == 0

    again = worker.run_once()
    assert again.claimed is False
    assert fake.send_count == 0


def test_crash_after_provider_call_is_not_resent() -> None:
    created = create_campaign_messages()

    class CrashAfterSendProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__(scenario="delivered")
            self.calls = 0

        def send(self, **kwargs: object):  # type: ignore[no-untyped-def]
            self.calls += 1
            super().send(**kwargs)  # type: ignore[arg-type]
            raise SystemExit("simulated crash after provider call")

    crashing = CrashAfterSendProvider()
    first = MessagingWorker(
        config=messaging_config(),
        provider=crashing,
        session_factory=SessionLocal,
        rng=random.Random(11),
        sleep_fn=lambda _seconds: None,
    )
    with pytest.raises(SystemExit):
        first.run_once()

    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "submitting"
    assert job.status == "claimed"
    assert crashing.calls == 1

    # Simulate the lease expiring after the crash.
    with SessionLocal() as db:
        db.execute(
            update(SendJob)
            .where(SendJob.id == job.id)
            .values(lease_expires_at=utcnow() - timedelta(seconds=1))
        )
        db.commit()

    class CountingProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__(scenario="delivered")
            self.calls = 0

        def send(self, **kwargs: object):  # type: ignore[no-untyped-def]
            self.calls += 1
            return super().send(**kwargs)  # type: ignore[arg-type]

    second = MessagingWorker(
        config=messaging_config(),
        provider=(reclaimer_provider := CountingProvider()),
        session_factory=SessionLocal,
        rng=random.Random(12),
        sleep_fn=lambda _seconds: None,
    )
    report = second.run_once()

    assert report.claimed is True
    assert report.skipped_reason == "reclaimed_submitting"
    assert reclaimer_provider.calls == 0
    assert crashing.calls == 1
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "unknown"
    assert job.status == "unknown"


def test_late_result_from_expired_lease_does_not_overwrite_new_owner() -> None:
    created = create_campaign_messages()

    class ReclaimDuringSendProvider(FakeProvider):
        def __init__(self, second: MessagingWorker) -> None:
            super().__init__(scenario="delivered")
            self.second = second
            self.calls = 0
            self.reclaim_report: object | None = None

        def send(self, **kwargs: object):  # type: ignore[no-untyped-def]
            self.calls += 1
            with SessionLocal() as db:
                job = db.scalar(
                    select(SendJob).where(
                        SendJob.message_id == created["message_ids"][0]
                    )
                )
                assert job is not None
                job.lease_expires_at = utcnow() - timedelta(seconds=1)
                db.commit()
            self.reclaim_report = self.second.run_once()
            return super().send(**kwargs)  # type: ignore[arg-type]

    second = MessagingWorker(
        config=messaging_config(),
        provider=FakeProvider(scenario="delivered"),
        session_factory=SessionLocal,
        rng=random.Random(13),
        sleep_fn=lambda _seconds: None,
    )
    provider = ReclaimDuringSendProvider(second)
    first = MessagingWorker(
        config=messaging_config(),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(14),
        sleep_fn=lambda _seconds: None,
    )

    report = first.run_once()

    assert report.skipped_reason == "result_fenced"
    assert report.outcome == "unknown"
    assert provider.calls == 1
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "unknown"
    assert job.status == "unknown"
    with SessionLocal() as db:
        actions = set(
            db.scalars(
                select(AuditEvent.action).where(
                    AuditEvent.entity_id == created["message_ids"][0]
                )
            ).all()
        )
    assert "message.result_discarded" in actions


def test_cancel_during_send_preserves_cancelled_state() -> None:
    created = create_campaign_messages()

    class CancelDuringSendProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__(scenario="delivered")
            self.calls = 0

        def send(self, **kwargs: object):  # type: ignore[no-untyped-def]
            self.calls += 1
            with SessionLocal() as db:
                message = db.get(Message, created["message_ids"][0])
                job = db.scalar(
                    select(SendJob).where(
                        SendJob.message_id == created["message_ids"][0]
                    )
                )
                assert message is not None and job is not None
                message.internal_status = "cancelled"
                job.status = "cancelled"
                job.locked_by = None
                job.locked_at = None
                job.heartbeat_at = None
                job.lease_expires_at = None
                job.claim_token = None
                db.commit()
            return super().send(**kwargs)  # type: ignore[arg-type]

    provider = CancelDuringSendProvider()
    worker = MessagingWorker(
        config=messaging_config(),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(15),
        sleep_fn=lambda _seconds: None,
    )

    report = worker.run_once()

    assert report.skipped_reason == "result_fenced"
    assert provider.calls == 1
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "cancelled"
    assert job.status == "cancelled"


def test_two_workers_cannot_claim_the_same_job() -> None:
    create_campaign_messages()
    first, _ = _worker()
    second, _ = _worker()

    first_job = first.claim_next()
    assert first_job is not None
    assert second.claim_next() is None


def test_worker_graceful_stop_finishes_in_flight_then_exits() -> None:
    created = create_campaign_messages([{}, {}])

    class StopAfterSendFake(FakeProvider):
        def __init__(self) -> None:
            super().__init__(scenario="delivered")
            self.worker: MessagingWorker | None = None

        def send(self, **kwargs: object):  # type: ignore[no-untyped-def]
            result = super().send(**kwargs)  # type: ignore[arg-type]
            if self.worker is not None:
                self.worker.request_stop()
            return result

    provider = StopAfterSendFake()
    worker = MessagingWorker(
        config=messaging_config(),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(3),
        sleep_fn=lambda _seconds: None,
    )
    provider.worker = worker

    report = worker.run_loop(poll_interval=0.01)

    assert report.claimed == 1
    assert provider.send_count == 1
    statuses = [_state(message_id)[0].internal_status for message_id in created["message_ids"]]
    assert sorted(statuses) == ["delivered", "pending"]


def test_campaign_status_derivation_from_message_outcomes() -> None:
    created = create_campaign_messages([{}, {}, {}])
    campaign_id = created["campaign_id"]

    with SessionLocal() as db:
        assert derive_campaign_status(db, campaign_id) == "sending"
        db.commit()

        db.execute(
            update(Message)
            .where(Message.campaign_id == campaign_id)
            .values(internal_status="delivered")
        )
        db.execute(
            update(SendJob)
            .where(SendJob.message_id.in_(created["message_ids"]))
            .values(status="completed")
        )
        assert derive_campaign_status(db, campaign_id) == "completed"
        db.commit()

        db.execute(
            update(Message)
            .where(Message.id == created["message_ids"][0])
            .values(internal_status="failed")
        )
        assert derive_campaign_status(db, campaign_id) == "completed_with_errors"
        db.commit()

        db.execute(
            update(Message)
            .where(Message.campaign_id == campaign_id)
            .values(internal_status="failed")
        )
        assert derive_campaign_status(db, campaign_id) == "failed"
        db.commit()

        db.execute(
            update(Message)
            .where(Message.campaign_id == campaign_id)
            .values(internal_status="unknown")
        )
        assert derive_campaign_status(db, campaign_id) == "completed_with_errors"
        db.commit()

        db.execute(
            update(Message)
            .where(Message.campaign_id == campaign_id)
            .values(internal_status="cancelled")
        )
        assert derive_campaign_status(db, campaign_id) == "cancelled"
        db.commit()


def test_worker_uses_database_credential_with_empty_environment() -> None:
    created = create_campaign_messages()
    _store_credential(api_key="database-key", sender_id="DB-SENDER")
    seen: list[object] = []

    def factory(config, resolved):  # type: ignore[no-untyped-def]
        seen.append(resolved)
        return FakeProvider(scenario="delivered")

    worker = MessagingWorker(
        config=messaging_config(
            messaging_provider="rasel",
            rasel_api_key="",
            rasel_sender_id="",
        ),
        provider=None,
        provider_factory=factory,
        session_factory=SessionLocal,
        rng=random.Random(31),
        sleep_fn=lambda _seconds: None,
    )

    report = worker.run_once()

    assert report.outcome == "delivered"
    assert seen
    resolved = seen[-1]
    assert resolved is not None
    assert resolved.api_key == "database-key"
    assert resolved.sender_id == "DB-SENDER"
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "delivered"
    assert job.status == "completed"


def test_revoked_credential_releases_claim_without_send() -> None:
    created = create_campaign_messages()
    _store_credential()
    fake = FakeProvider(scenario="delivered")
    builds = {"count": 0}

    def factory(config, resolved):  # type: ignore[no-untyped-def]
        builds["count"] += 1
        if builds["count"] == 1:
            # Simulate an admin revoking the credential after the provider was
            # built but before the message is submitted.
            with SessionLocal() as db:
                revoke_credential(db)
                db.commit()
        return fake

    worker = MessagingWorker(
        config=messaging_config(
            messaging_provider="rasel",
            rasel_api_key="",
            rasel_sender_id="",
        ),
        provider=None,
        provider_factory=factory,
        session_factory=SessionLocal,
        rng=random.Random(32),
        sleep_fn=lambda _seconds: None,
    )

    report = worker.run_once()

    assert report.claimed is True
    assert report.skipped_reason == "provider_credential_unavailable"
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "pending"
    assert job.status == "pending"
    assert job.attempt_count == 0
    assert job.claim_token is None
    assert campaign.status == "approved"
    assert fake.send_count == 0


def test_key_version_rotation_rebuilds_provider() -> None:
    created = create_campaign_messages([{}, {}])
    _store_credential(api_key="first-key")
    keys: list[str] = []

    def factory(config, resolved):  # type: ignore[no-untyped-def]
        keys.append(resolved.api_key)
        return FakeProvider(scenario="delivered")

    worker = MessagingWorker(
        config=messaging_config(
            messaging_provider="rasel",
            rasel_api_key="",
            rasel_sender_id="",
        ),
        provider=None,
        provider_factory=factory,
        session_factory=SessionLocal,
        rng=random.Random(33),
        sleep_fn=lambda _seconds: None,
    )

    assert worker.run_once().outcome == "delivered"
    assert keys == ["first-key"]

    _store_credential(api_key="second-key")

    assert worker.run_once().outcome == "delivered"
    assert keys == ["first-key", "second-key"]
    statuses = [_state(mid)[0].internal_status for mid in created["message_ids"]]
    assert statuses == ["delivered", "delivered"]


def test_database_row_suppresses_environment_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    created = create_campaign_messages()
    _store_credential()
    with SessionLocal() as db:
        revoke_credential(db)
        db.commit()
    monkeypatch.setattr(settings, "rasel_api_key", "environment-key")
    monkeypatch.setattr(settings, "rasel_sender_id", "ENV-SENDER")

    def factory(config, resolved):  # type: ignore[no-untyped-def]
        raise AssertionError("environment credentials must not be used")

    worker = MessagingWorker(
        config=messaging_config(
            messaging_provider="rasel",
            rasel_api_key="environment-key",
            rasel_sender_id="ENV-SENDER",
        ),
        provider=None,
        provider_factory=factory,
        session_factory=SessionLocal,
        rng=random.Random(34),
        sleep_fn=lambda _seconds: None,
    )

    report = worker.run_once()

    assert report.claimed is False
    assert report.skipped_reason == "provider_credential_unavailable"
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "pending"
    assert job.status == "pending"


def test_worker_never_logs_or_audits_credential_secrets(
    caplog: pytest.LogCaptureFixture,
) -> None:
    created = create_campaign_messages()
    _store_credential(api_key="super-secret-key", sender_id="SECRET-SENDER")

    worker = MessagingWorker(
        config=messaging_config(
            messaging_provider="rasel",
            rasel_api_key="",
            rasel_sender_id="",
        ),
        provider=None,
        provider_factory=lambda config, resolved: FakeProvider("delivered"),
        session_factory=SessionLocal,
        rng=random.Random(35),
        sleep_fn=lambda _seconds: None,
    )

    with caplog.at_level(logging.INFO, logger="feedesk.worker"):
        assert worker.run_once().outcome == "delivered"

    assert "super-secret-key" not in caplog.text
    assert "SECRET-SENDER" not in caplog.text
    with SessionLocal() as db:
        events = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.entity_id == created["message_ids"][0]
                )
            ).all()
        )
    audit_payload = json.dumps(
        [
            {"before": event.before_data, "after": event.after_data}
            for event in events
        ],
        ensure_ascii=False,
    )
    assert "super-secret-key" not in audit_payload
    assert "SECRET-SENDER" not in audit_payload


def test_run_once_paces_before_provider_send() -> None:
    created = create_campaign_messages()
    message_id = created["message_ids"][0]
    sleeps: list[float] = []
    observed_during_pacing: list[tuple[str, str]] = []

    def sleep_fn(seconds: float) -> None:
        sleeps.append(seconds)
        # Regression: pacing must not happen after ``submitting`` is committed.
        # A crash during this sleep must leave a safely retryable claim.
        with SessionLocal() as db:
            message = db.get(Message, message_id)
            job = db.scalar(select(SendJob).where(SendJob.message_id == message_id))
            assert message is not None and job is not None
            observed_during_pacing.append((message.internal_status, job.status))

    provider = FakeProvider(scenario="delivered")
    worker = MessagingWorker(
        config=messaging_config(messaging_rate_limit_per_second=2.0),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(36),
        sleep_fn=sleep_fn,
    )

    report = worker.run_once()

    assert report.outcome == "delivered"
    assert provider.send_count == 1
    assert sleeps == [0.5]
    assert observed_during_pacing == [("pending", "claimed")]


def test_run_loop_does_not_double_sleep() -> None:
    create_campaign_messages([{}, {}])
    sleeps: list[float] = []
    provider = FakeProvider(scenario="delivered")
    worker = MessagingWorker(
        config=messaging_config(messaging_rate_limit_per_second=2.0),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(37),
        sleep_fn=sleeps.append,
    )

    report = worker.run_loop(poll_interval=0.01, max_jobs=2)

    assert report.claimed == 2
    assert provider.send_count == 2
    assert sleeps == [0.5, 0.5]
