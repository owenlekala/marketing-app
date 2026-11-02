"""Pure retry and uncertainty rules for outbound work."""

from datetime import UTC, datetime, timedelta

from tag_marketing.domain.outbox import MAX_ATTEMPTS, retry_decision, uncertain_submission
from tag_marketing.tests.support.cases import OfflineTestCase


class TestOutboxRules(OfflineTestCase):
	def test_only_explicitly_retryable_results_retry_with_bounded_jitter(self) -> None:
		now = datetime(2026, 11, 2, tzinfo=UTC)
		first = retry_decision(1, now, explicitly_retryable=True, key="outbox-a")
		repeated = retry_decision(1, now, explicitly_retryable=True, key="outbox-a")
		self.assertEqual(first, repeated)
		self.assertEqual(first.status, "Retry")
		assert first.due_at is not None
		self.assertGreaterEqual(first.due_at, now + timedelta(seconds=48))
		self.assertLessEqual(first.due_at, now + timedelta(seconds=72))
		self.assertEqual(retry_decision(1, now, explicitly_retryable=False).status, "Failed")

	def test_fifth_attempt_is_terminal_and_only_submitting_is_uncertain(self) -> None:
		now = datetime(2026, 11, 2, tzinfo=UTC)
		self.assertEqual(retry_decision(MAX_ATTEMPTS, now, explicitly_retryable=True).status, "Failed")
		self.assertTrue(uncertain_submission("Submitting", now))
		self.assertFalse(uncertain_submission("Claimed", now))
		self.assertFalse(uncertain_submission("Submitting", None))
