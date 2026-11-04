from __future__ import annotations

import random
import threading
import time
from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import func, select, update

from app.db import SessionLocal
from app.messaging.fake import FakeProvider
from app.messaging.worker import MessagingWorker
from app.models import AuditEvent, Campaign, Message, ProviderEvent, SendJob

from .campaign_helpers import clean_campaign_tables
from .messaging_helpers import create_campaign_messages, messaging_config, utcnow

LOAD_RECIPIENTS = 100


@pytest.fixture(autouse=True)
def campaign_environment() -> Any:
    clean_campaign_tables()
    yield
    clean_campaign_tables()


def _worker(
    provider: FakeProvider | None = None,
    *,
    scenario: str = "delivered",
    sleep_fn: Any = None,
    **config_updates: object,
) -> tuple[MessagingWorker, FakeProvider]:
    fake = provider or FakeProvider(scenario=scenario)
    worker = MessagingWorker(
        config=messaging_config(**config_updates),
        provider=fake,
        session_factory=SessionLocal,
        rng=random.Random(70),
        sleep_fn=sleep_fn or (lambda _seconds: None),
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


def _provider_event_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(ProviderEvent)) or 0


def _rewind_next_attempt(job_id: str) -> None:
    with SessionLocal() as db:
        db.execute(
            update(SendJob)
            .where(SendJob.id == job_id)
            .values(next_attempt_at=utcnow() - timedelta(seconds=1))
        )
        db.commit()


def _expire_lease(job_id: str) -> None:
    with SessionLocal() as db:
        job = db.get(SendJob, job_id)
        assert job is not None
        job.lease_expires_at = utcnow() - timedelta(seconds=1)
        db.commit()


# ---------------------------------------------------------------------------
# 1. Load: 100 recipients through the real claim/process loop.
# ---------------------------------------------------------------------------


def test_fake_provider_load_100_recipients(
    monkeypatch: pytest.MonkeyPatch,
    record_property: Any,
) -> None:
    def explode(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("load run must never perform network I/O")

    monkeypatch.setattr(httpx.Client, "send", explode)
    monkeypatch.setattr(httpx.AsyncClient, "send", explode)

    specs = [
        {
            "phone": f"+963993{index:06d}",
            "body": f"رسالة تحميل رقم {index + 1}",
        }
        for index in range(LOAD_RECIPIENTS)
    ]
    created = create_campaign_messages(specs)
    campaign_id = created["campaign_id"]
    events_before = _provider_event_count()

    worker, fake = _worker()

    started = time.perf_counter()
    report = worker.run_loop(poll_interval=0.01, max_jobs=LOAD_RECIPIENTS)
    elapsed = time.perf_counter() - started
    record_property("load_elapsed_seconds", round(elapsed, 3))
    print(f"\nMSG-14 load: {LOAD_RECIPIENTS} jobs in {elapsed:.2f}s")

    assert report.claimed == LOAD_RECIPIENTS
    assert report.outcomes == {"delivered": LOAD_RECIPIENTS}
    assert fake.send_count == LOAD_RECIPIENTS

    with SessionLocal() as db:
        messages = list(
            db.scalars(select(Message).where(Message.campaign_id == campaign_id))
        )
        jobs = list(
            db.scalars(
                select(SendJob)
                .join(Message, SendJob.message_id == Message.id)
                .where(Message.campaign_id == campaign_id)
            )
        )
        campaign = db.get(Campaign, campaign_id)
        assert campaign is not None
        campaign_status = campaign.status
        recipient_count = campaign.recipient_count

    assert len(messages) == LOAD_RECIPIENTS
    assert len(jobs) == LOAD_RECIPIENTS
    assert {message.internal_status for message in messages} == {"delivered"}
    assert {job.status for job in jobs} == {"completed"}
    assert {job.attempt_count for job in jobs} == {1}
    assert all(job.locked_by is None for job in jobs)
    assert all(job.claim_token is None for job in jobs)
    assert all(job.lease_expires_at is None for job in jobs)
    assert all(job.next_attempt_at is None for job in jobs)

    # No duplicate logical message or idempotency key.
    assert len({message.id for message in messages}) == LOAD_RECIPIENTS
    assert len({message.idempotency_key for message in messages}) == LOAD_RECIPIENTS
    assert (
        len({message.provider_message_id for message in messages})
        == LOAD_RECIPIENTS
    )

    assert campaign_status == "completed"
    assert recipient_count == LOAD_RECIPIENTS

    # A second pass must not claim or send anything again.
    again = worker.run_once()
    assert again.claimed is False
    assert fake.send_count == LOAD_RECIPIENTS

    # Fake provider writes no provider events and the network guard never fired.
    assert _provider_event_count() == events_before

    # Generous hang guard only; this is deliberately not a tight performance
    # threshold, and the measured value is recorded above for the report.
    assert elapsed < 120.0


# ---------------------------------------------------------------------------
# 2. Crash / lease reclaim / stale-result fencing.
# ---------------------------------------------------------------------------


def test_expired_lease_is_reclaimed_exactly_once() -> None:
    created = create_campaign_messages(
        [
            {
                "job_status": "claimed",
                "attempt_count": 1,
                "locked_by": "dead-worker",
                "claim_token": "dead-token",
                "locked_at": utcnow() - timedelta(minutes=5),
                "heartbeat_at": utcnow() - timedelta(minutes=5),
                "lease_expires_at": utcnow() - timedelta(minutes=1),
            }
        ]
    )
    worker, fake = _worker()

    first = worker.run_once()

    assert first.claimed is True
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "delivered"
    assert job.status == "completed"
    assert job.attempt_count == 2
    assert job.claim_token is None
    assert campaign.status == "completed"
    assert fake.send_count == 1

    second = worker.run_once()

    assert second.claimed is False
    message, job, _ = _state(created["message_ids"][0])
    assert job.attempt_count == 2
    assert fake.send_count == 1


def test_reclaimed_submitting_is_unknown_and_never_resent() -> None:
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
    worker, fake = _worker()

    report = worker.run_once()

    assert report.claimed is True
    assert report.skipped_reason == "reclaimed_submitting"
    assert report.outcome == "unknown"
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "unknown"
    assert message.last_error_code == "RECONCILIATION_REQUIRED"
    assert job.status == "unknown"
    assert job.claim_token is None
    assert job.next_attempt_at is None
    assert campaign.status == "completed_with_errors"
    assert fake.send_count == 0

    again = worker.run_once()
    assert again.claimed is False
    assert fake.send_count == 0


def test_stale_result_from_expired_claim_is_fenced_without_resend() -> None:
    created = create_campaign_messages()
    message_id = created["message_ids"][0]

    with SessionLocal() as db:
        job_id = db.scalar(select(SendJob.id).where(SendJob.message_id == message_id))
    assert job_id is not None

    second, second_fake = _worker()

    class ReclaimDuringSendProvider(FakeProvider):
        def __init__(self) -> None:
            super().__init__(scenario="delivered")
            self.reclaim_report: Any = None

        def send(self, **kwargs: object) -> Any:
            # The first owner's lease expires while the provider call is in
            # flight; a second worker reclaims the job and fences this result.
            _expire_lease(job_id)
            self.reclaim_report = second.run_once()
            return super().send(**kwargs)  # type: ignore[arg-type]

    provider = ReclaimDuringSendProvider()
    worker = MessagingWorker(
        config=messaging_config(),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(71),
        sleep_fn=lambda _seconds: None,
    )

    report = worker.run_once()

    assert report.skipped_reason == "result_fenced"
    assert report.outcome == "unknown"
    assert provider.reclaim_report is not None
    assert provider.reclaim_report.claimed is True
    assert provider.reclaim_report.skipped_reason == "reclaimed_submitting"
    assert provider.send_count == 1
    assert second_fake.send_count == 0

    message, job, campaign = _state(message_id)
    assert message.internal_status == "unknown"
    assert message.last_error_code == "RECONCILIATION_REQUIRED"
    assert job.status == "unknown"
    assert job.claim_token is None
    assert campaign.status == "completed_with_errors"

    with SessionLocal() as db:
        discarded = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.entity_id == message_id,
                    AuditEvent.action == "message.result_discarded",
                )
            ).all()
        )
    assert len(discarded) == 1
    assert discarded[0].after_data["observed_outcome"] == "delivered"
    assert discarded[0].after_data["internal_status"] == "unknown"

    # The fence holds: no later pass reclaims the unknown message or resends.
    again = worker.run_once()
    assert again.claimed is False
    assert provider.send_count == 1
    assert second_fake.send_count == 0


# ---------------------------------------------------------------------------
# 3. Duplicate execution and idempotency replay.
# ---------------------------------------------------------------------------


def test_two_workers_racing_one_due_job_produce_one_send() -> None:
    create_campaign_messages()
    reports: list[Any] = []
    errors: list[BaseException] = []
    providers: list[FakeProvider] = []
    barrier = threading.Barrier(3, timeout=10)

    def run_worker() -> None:
        worker, fake = _worker()
        providers.append(fake)
        barrier.wait()
        try:
            reports.append(worker.run_once())
        except BaseException as exc:  # pragma: no cover - failure diagnostic
            errors.append(exc)

    threads = [threading.Thread(target=run_worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join(timeout=30)

    assert not errors
    assert len(reports) == 2
    assert sum(1 for report in reports if report.claimed) == 1
    assert len(providers) == 2
    assert sum(fake.send_count for fake in providers) == 1

    with SessionLocal() as db:
        job = db.scalar(select(SendJob))
        message = db.scalar(select(Message))
        assert job is not None and message is not None
        assert job.status == "completed"
        assert job.attempt_count == 1
        assert message.internal_status == "delivered"

    # A third pass cannot claim the completed job either.
    third, third_fake = _worker()
    assert third.run_once().claimed is False
    assert third_fake.send_count == 0


def test_idempotency_key_replay_does_not_increment_fake_send_count() -> None:
    fake = FakeProvider(scenario="delivered")
    params = {
        "to": "+963993000001",
        "text": "رسالة مكررة",
        "idempotency_key": "campaign:recipient:stable",
        "channel": "local_sms",
    }

    first = fake.send(**params)
    second = fake.send(**params)

    assert fake.send_count == 1
    assert first is second
    assert first.provider_message_id == second.provider_message_id
    assert first.outcome == "delivered"


# ---------------------------------------------------------------------------
# 4. Chaos outcomes: 429/temporary retry, exhaustion, timeout/unknown.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", ["rate_limited", "temporary_error"])
def test_temporary_outcome_retries_with_backoff(scenario: str) -> None:
    created = create_campaign_messages()
    worker, fake = _worker(scenario=scenario, messaging_max_attempts=3)
    before = utcnow()

    report = worker.run_once()

    assert report.claimed is True
    assert report.outcome == scenario
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "pending"
    assert job.status == "retry"
    assert job.attempt_count == 1
    assert job.next_attempt_at is not None
    assert job.next_attempt_at > before
    delay = (job.next_attempt_at - before).total_seconds()
    # 2s base backoff with +-20% jitter, and the fake 429 also requests
    # Retry-After: 2. Generous bounds to avoid clock/jitter flakiness.
    assert 1.5 <= delay <= 5.0
    assert campaign.status == "sending"
    assert fake.send_count == 1


@pytest.mark.parametrize("scenario", ["rate_limited", "temporary_error"])
def test_retry_exhaustion_ends_failed_with_one_logical_send(scenario: str) -> None:
    created = create_campaign_messages()
    worker, fake = _worker(scenario=scenario, messaging_max_attempts=3)
    message_id = created["message_ids"][0]

    for expected_attempt in (1, 2, 3):
        report = worker.run_once()
        assert report.claimed is True
        message, job, _ = _state(message_id)
        assert job.attempt_count == expected_attempt
        if expected_attempt < 3:
            assert job.status == "retry"
            assert message.internal_status == "pending"
            _rewind_next_attempt(job.id)

    message, job, campaign = _state(message_id)
    assert message.internal_status == "failed"
    assert job.status == "failed"
    assert job.next_attempt_at is None
    assert job.claim_token is None
    assert campaign.status == "failed"
    # The fake deduplicates replaying the stable idempotency key, so retries
    # never become additional logical sends.
    assert fake.send_count == 1

    assert worker.run_once().claimed is False
    assert fake.send_count == 1


def test_timeout_becomes_unknown_and_is_never_auto_resent() -> None:
    created = create_campaign_messages()
    worker, fake = _worker(scenario="timeout", messaging_max_attempts=3)

    report = worker.run_once()

    assert report.claimed is True
    assert report.outcome == "unknown"
    message, job, campaign = _state(created["message_ids"][0])
    assert message.internal_status == "unknown"
    assert message.last_error_code == "TIMEOUT"
    assert job.status == "unknown"
    assert job.next_attempt_at is None
    assert job.claim_token is None
    assert campaign.status == "completed_with_errors"
    assert fake.send_count == 1

    # No next_attempt_at, no claimable status: never re-armed automatically.
    _rewind_next_attempt(job.id)
    again = worker.run_once()
    assert again.claimed is False
    assert fake.send_count == 1
    message, job, _ = _state(created["message_ids"][0])
    assert message.internal_status == "unknown"
    assert job.status == "unknown"


# ---------------------------------------------------------------------------
# 5. Pacing before provider I/O, no double sleep, per-process limitation.
# ---------------------------------------------------------------------------


def test_run_once_paces_once_before_provider_io() -> None:
    created = create_campaign_messages()
    message_id = created["message_ids"][0]
    sleeps: list[float] = []
    observed_during_pacing: list[tuple[str, str]] = []

    provider = FakeProvider(scenario="delivered")

    def sleep_fn(seconds: float) -> None:
        # Pacing must happen before the provider call and before ``submitting``
        # is committed, so a crash during the sleep leaves a retryable claim.
        assert provider.send_count == 0
        sleeps.append(seconds)
        with SessionLocal() as db:
            message = db.get(Message, message_id)
            job = db.scalar(select(SendJob).where(SendJob.message_id == message_id))
            assert message is not None and job is not None
            observed_during_pacing.append((message.internal_status, job.status))

    worker = MessagingWorker(
        config=messaging_config(messaging_rate_limit_per_second=2.0),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(72),
        sleep_fn=sleep_fn,
    )

    assert worker.run_once().outcome == "delivered"

    assert sleeps == [0.5]
    assert observed_during_pacing == [("pending", "claimed")]
    assert provider.send_count == 1


def test_run_loop_paces_once_per_send_without_double_sleep() -> None:
    create_campaign_messages([{}, {}, {}])
    sleeps: list[float] = []
    order: list[tuple[str, int]] = []

    class OrderingProvider(FakeProvider):
        def send(self, **kwargs: object) -> Any:
            order.append(("send", len(sleeps)))
            return super().send(**kwargs)  # type: ignore[arg-type]

    provider = OrderingProvider(scenario="delivered")
    worker = MessagingWorker(
        config=messaging_config(messaging_rate_limit_per_second=2.0),
        provider=provider,
        session_factory=SessionLocal,
        rng=random.Random(73),
        sleep_fn=sleeps.append,
    )

    report = worker.run_loop(poll_interval=0.01, max_jobs=3)

    assert report.claimed == 3
    assert provider.send_count == 3
    assert order == [("send", 1), ("send", 2), ("send", 3)]
    assert sleeps == [0.5, 0.5, 0.5]


def test_pacing_is_per_process_not_globally_coordinated() -> None:
    create_campaign_messages([{}, {}])
    first_sleeps: list[float] = []
    second_sleeps: list[float] = []

    first, first_fake = _worker(
        messaging_rate_limit_per_second=2.0, sleep_fn=first_sleeps.append
    )
    second, second_fake = _worker(
        messaging_rate_limit_per_second=2.0, sleep_fn=second_sleeps.append
    )

    assert first.run_once().claimed is True
    assert second.run_once().claimed is True

    # Each process paced its own send independently; there is no shared
    # cross-process limiter. This is the documented per-process limitation.
    assert first_sleeps == [0.5]
    assert second_sleeps == [0.5]
    assert first_fake.send_count == 1
    assert second_fake.send_count == 1
