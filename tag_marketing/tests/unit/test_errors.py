from tag_marketing.domain.errors import CommandError, require_revision
from tag_marketing.tests.support.cases import OfflineTestCase


class TestRevisionPolicy(OfflineTestCase):
	def test_only_exact_revision_is_accepted(self) -> None:
		require_revision("2026-10-27 10:00:00.123456", "2026-10-27 10:00:00.123456")
		for value, code in (
			(None, "INVALID_INPUT"),
			("", "INVALID_INPUT"),
			("x" * 65, "INVALID_INPUT"),
			("2026-10-27 10:00:00", "STALE_DOCUMENT"),
		):
			with self.assertRaises(CommandError) as raised:
				require_revision("2026-10-27 10:00:00.123456", value)
			self.assertEqual(raised.exception.code, code)
			self.assertEqual(raised.exception.field, "expected_modified")
