"""Recovery fixtures must restore configuration and refuse foreign ownership."""

import frappe

from tag_marketing.tests.support import progress
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw
from tag_marketing.tests.support.site import cleanup_records, create_user


class TestProgressFixtures(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.clear_cache)

	def prepare(self, run_id):
		create_user("manager", run_id=run_id)
		path = progress.manifest_path(run_id)
		self.addCleanup(lambda: path.unlink(missing_ok=True))
		return progress.prepare(run_id)

	def test_cleanup_restores_temporary_company_and_removes_only_owned_records(self):
		previous = frappe.db.get_single_value("WA Settings", "marketing_company")
		run_id = "d" * 32
		operations = self.prepare(run_id)
		self.assertEqual(progress.manifest_path(run_id).stat().st_mode & 0o777, 0o600)
		cleanup_records(run_id)
		self.assertEqual(frappe.db.get_single_value("WA Settings", "marketing_company"), previous)
		for operation in operations.values():
			self.assertFalse(frappe.db.exists("WA Operation", operation))
		self.assertTrue(progress.manifest_path(run_id).exists())
		# Cleanup's caller owns commit; metadata is retained until then.

	def test_changed_operation_owner_refuses_cleanup_without_deleting_any_user(self):
		run_id = "e" * 32
		operations = self.prepare(run_id)
		frappe.db.set_value("WA Operation", operations["Running"], "request_hash", "foreign")
		with self.assertRaises(RuntimeError):
			cleanup_records(run_id)
		self.assertTrue(frappe.db.exists("WA Operation", operations["Pending"]))
		self.assertTrue(progress.manifest_path(run_id).exists())

	def test_changed_company_refuses_cleanup_even_with_a_stale_setting_cache(self):
		frappe.db.set_single_value("WA Settings", "marketing_company", None)
		run_id = "f" * 32
		operations = self.prepare(run_id)
		frappe.db.get_single_value("WA Settings", "marketing_company")
		frappe.db.sql(
			"UPDATE tabSingles SET value=%s WHERE doctype='WA Settings' AND field='marketing_company'",
			("Foreign configuration",),
		)
		with self.assertRaises(RuntimeError):
			cleanup_records(run_id)
		self.assertTrue(frappe.db.exists("WA Operation", operations["Pending"]))
		self.assertEqual(progress.locked_company(), "Foreign configuration")

	def test_cleanup_preserves_an_existing_company_and_configuration(self):
		company = raw(
			"Company",
			name="_WA Existing Progress Company",
			company_name="_WA Existing Progress Company",
			abbr="WAE",
			country="South Africa",
			default_currency="ZAR",
		)
		frappe.db.set_single_value("WA Settings", "marketing_company", company.name)
		run_id = "c" * 32
		self.prepare(run_id)
		cleanup_records(run_id)
		self.assertTrue(frappe.db.exists("Company", company.name))
		self.assertEqual(progress.locked_company(), company.name)
		self.assertFalse(frappe.db.exists("WA Connection", "wa-progress-connection-" + run_id))
