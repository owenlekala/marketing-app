from unittest.mock import patch

import frappe

from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.site import cleanup_records, create_user, require_disposable_site, user_email

PROBE = "WA Harness Rollback Probe"


class TestScaffold(AppIntegrationTestCase):
	def test_01_insert_rollback_probe(self):
		require_disposable_site()
		self.assertFalse(frappe.db.exists("Role", PROBE))
		frappe.get_doc({"doctype": "Role", "role_name": PROBE}).insert()
		self.assertTrue(frappe.db.exists("Role", PROBE))

	def test_02_previous_test_was_rolled_back(self):
		self.assertFalse(frappe.db.exists("Role", PROBE))

	def test_scaffold_is_registered_without_payroll_dependency(self):
		self.assertIn("tag_marketing", frappe.get_installed_apps())
		self.assertEqual(frappe.get_hooks("required_apps", app_name="tag_marketing"), ["erpnext"])
		self.assertEqual(frappe.db.get_value("Module Def", "WhatsApp Marketing", "app_name"), "tag_marketing")

	def test_two_synthetic_users_have_distinct_native_permissions(self):
		require_disposable_site()
		agent = create_user("agent")
		manager = create_user("manager")
		frappe.set_user(agent.name)
		self.assertFalse(frappe.has_permission("System Settings", "write"))
		frappe.set_user(manager.name)
		self.assertTrue(frappe.has_permission("System Settings", "write"))

	def test_fixture_gate_rejects_wrong_site_and_disabled_tests(self):
		with patch.object(frappe.local, "site", "unapproved.invalid"), self.assertRaises(RuntimeError):
			require_disposable_site()
		with patch.dict(frappe.local.conf, {"allow_tests": False}), self.assertRaises(RuntimeError):
			require_disposable_site()

	def test_cleanup_is_scoped_to_a_single_run(self):
		first, other = "a" * 32, "b" * 32
		create_user("agent", run_id=first)
		create_user("agent", run_id=other)
		create_user("manager")
		cleanup_records(first)
		self.assertFalse(frappe.db.exists("User", user_email("agent", first)))
		self.assertTrue(frappe.db.exists("User", user_email("agent", other)))
		self.assertTrue(frappe.db.exists("User", user_email("manager")))

	def test_cleanup_rejects_wrong_ownership_and_invalid_identifiers(self):
		run_id = "c" * 32
		untouched = create_user("agent", run_id=run_id)
		user = create_user("manager", run_id=run_id)
		frappe.db.set_value("User", user.name, "last_name", "Other owner")
		with self.assertRaises(RuntimeError):
			cleanup_records(run_id)
		self.assertTrue(frappe.db.exists("User", user.name))
		self.assertTrue(frappe.db.exists("User", untouched.name))
		with self.assertRaises(ValueError):
			cleanup_records("*")
