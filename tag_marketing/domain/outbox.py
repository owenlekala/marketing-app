"""Pure outbox state and retry decisions."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from hashlib import sha256
from math import ceil

MAX_ATTEMPTS = 5
RETRY_DELAYS_MINUTES = (1, 5, 15, 60)


@dataclass(frozen=True)
class RetryDecision:
	status: str
	due_at: datetime | None


def retry_decision(
	attempt_count: int, now: datetime, *, explicitly_retryable: bool, key: str = ""
) -> RetryDecision:
	"""Retry only provider outcomes known not to have been accepted."""
	if not explicitly_retryable or attempt_count >= MAX_ATTEMPTS:
		return RetryDecision("Failed", None)
	delay = RETRY_DELAYS_MINUTES[min(max(attempt_count - 1, 0), len(RETRY_DELAYS_MINUTES) - 1)]
	jitter = int(sha256(f"{key}:{attempt_count}".encode()).hexdigest()[:8], 16) % 4001 - 2000
	delay_seconds = ceil(delay * 60 * (10_000 + jitter) / 10_000)
	return RetryDecision("Retry", now + timedelta(seconds=delay_seconds))


def uncertain_submission(status: str, submission_started_at: datetime | None) -> bool:
	return status == "Submitting" and submission_started_at is not None
