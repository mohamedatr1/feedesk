from __future__ import annotations

import random

BACKOFF_BASE_SECONDS = 2.0
BACKOFF_CAP_SECONDS = 300.0
BACKOFF_JITTER = 0.2


def compute_backoff_seconds(
    attempt: int,
    *,
    base: float = BACKOFF_BASE_SECONDS,
    cap: float = BACKOFF_CAP_SECONDS,
    jitter: float = BACKOFF_JITTER,
    rng: random.Random | None = None,
) -> float:
    """Exponential backoff with bounded jitter.

    ``attempt`` is 1-based: the delay after the first failed attempt starts at
    ``base`` and doubles for each subsequent attempt, capped at ``cap``.
    """
    safe_attempt = max(1, int(attempt))
    raw = min(cap, base * (2 ** (safe_attempt - 1)))
    random_source = rng or random.Random()
    factor = 1.0 + random_source.uniform(-jitter, jitter)
    delay = raw * factor
    return round(max(0.0, min(cap, delay)), 3)
