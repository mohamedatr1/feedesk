from __future__ import annotations

import random

from app.messaging.backoff import BACKOFF_CAP_SECONDS, compute_backoff_seconds


def test_backoff_is_exponential_bounded_and_deterministic() -> None:
    first_rng = random.Random(1234)
    second_rng = random.Random(1234)
    first = [compute_backoff_seconds(attempt, rng=first_rng) for attempt in range(1, 8)]
    second = [compute_backoff_seconds(attempt, rng=second_rng) for attempt in range(1, 8)]
    assert first == second
    assert first[0] > 0
    assert first[1] > first[0]
    assert first[2] > first[1]
    assert all(delay <= BACKOFF_CAP_SECONDS for delay in first)


def test_backoff_jitter_stays_within_twenty_percent() -> None:
    rng = random.Random(7)
    for attempt in range(1, 6):
        raw = min(BACKOFF_CAP_SECONDS, 2.0 * (2 ** (attempt - 1)))
        for _ in range(50):
            delay = compute_backoff_seconds(attempt, rng=rng)
            assert raw * 0.8 <= delay <= min(BACKOFF_CAP_SECONDS, raw * 1.2)


def test_backoff_caps_at_five_minutes() -> None:
    rng = random.Random(99)
    assert compute_backoff_seconds(20, rng=rng) <= BACKOFF_CAP_SECONDS
    assert compute_backoff_seconds(20, rng=rng) >= BACKOFF_CAP_SECONDS * 0.8
