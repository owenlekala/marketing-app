from unittest.mock import patch

import frappe

from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.site import create_user, require_disposable_site

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
