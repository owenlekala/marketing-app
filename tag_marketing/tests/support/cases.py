import unittest

from tag_marketing.tests.support.network import NetworkGuard


class OfflineTestCase(unittest.TestCase):
	def setUp(self) -> None:
		super().setUp()
		guard = NetworkGuard()
		guard.__enter__()
		self.addCleanup(guard.__exit__, None, None, None)
		self.addCleanup(guard.assert_clean)
