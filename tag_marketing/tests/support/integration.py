import frappe
from frappe.tests import IntegrationTestCase

from tag_marketing.tests.support.network import NetworkGuard
from tag_marketing.tests.support.site import require_disposable_site


class AppIntegrationTestCase(IntegrationTestCase):
	"""A real site connection with per-test rollback and restricted network."""

	def setUp(self):
		require_disposable_site()
		super().setUp()
		guard = NetworkGuard((("mariadb", 3306), ("redis-cache", 6379), ("redis-queue", 6379)))
		guard.__enter__()
		self.addCleanup(guard.__exit__, None, None, None)
		self.addCleanup(guard.assert_clean)
		self.addCleanup(frappe.set_user, "Administrator")
		self.addCleanup(frappe.db.rollback)
