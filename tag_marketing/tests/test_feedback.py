"""Real database authorization and transactional safe-response tests."""

from unittest.mock import patch

import frappe
from frappe.client import get as generic_get

from tag_marketing.api.operations import get
from tag_marketing.api.responses import boundary
from tag_marketing.application.operations import get_progress
from tag_marketing.domain.errors import CommandError
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw

COMPANY = "_WA Progress Company"
OTHER = "_WA Progress Other"


class TestFeedback(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.clear_cache)
		self.addCleanup(lambda: frappe.local.response.pop("http_status_code", None))
		for company in (COMPANY, OTHER):
			raw(
				"Company",
				name=company,
				company_name=company,
				abbr="WAP",
				country="South Africa",
				default_currency="ZAR",
			)
		frappe.db.set_single_value("WA Settings", "marketing_company", COMPANY)
		self.owner = self.user("owner", ["System Manager"])
		self.other = self.user("other", ["System Manager"])
		self.manager = self.user("manager", ["Marketing Manager", "System Manager"])
		self.target = raw(
			"WA Connection", company=COMPANY, connection_name="Progress fixture", status="Draft"
		)
		self.operation = raw(
			"WA Operation",
			company=COMPANY,
			operation_type="connections.validate_connection",
			requested_by=self.owner,
			request_id="00000000-0000-4000-8000-000000000001",
			request_hash="a" * 64,
			target_doctype="WA Connection",
			target_name=self.target.name,
			status="Pending",
			progress_percent=0,
			result_json='{"secret":"never expose"}',
			error_code="private provider diagnostic",
		)

	def user(self, name, roles):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"wa-progress-{name}@example.invalid",
					"first_name": "WA Progress",
					"send_welcome_email": 0,
					"roles": [{"role": role} for role in roles],
				}
			)
			.insert()
			.name
		)

	def test_progress_is_safe_for_every_lifecycle_state_and_generic_reads_stay_closed(self):
		for status in ("Pending", "Running", "Succeeded", "Failed", "Cancelled"):
			frappe.db.set_value(
				"WA Operation", self.operation.name, {"status": status, "progress_percent": 35}
			)
			frappe.set_user(self.owner)
			result = get(self.operation.name)
			self.assertTrue(result["ok"])
			self.assertEqual(result["data"]["status"], status)
			self.assertIsNone(result["data"]["result"])
			self.assertIsNone(result["data"]["result_file"])
			self.assertNotIn("secret", str(result))
			self.assertNotIn("private provider", str(result))
		with self.assertRaises(frappe.PermissionError):
			generic_get("WA Operation", self.operation.name)

	def test_only_requester_or_currently_authorized_manager_can_read(self):
		frappe.set_user(self.other)
		self.assertEqual(get(self.operation.name)["error"]["code"], "NOT_FOUND")
		frappe.set_user(self.manager)
		self.assertTrue(get(self.operation.name)["ok"])
		frappe.set_user("Administrator")
		frappe.get_doc("User", self.manager).remove_roles("System Manager")
		frappe.set_user(self.manager)
		self.assertEqual(get(self.operation.name)["error"]["code"], "NOT_FOUND")

	def test_company_permissions_target_removal_and_unregistered_targets_fail_closed(self):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": self.owner,
				"allow": "Company",
				"for_value": OTHER,
				"apply_to_all_doctypes": 1,
			}
		).insert()
		frappe.set_user(self.owner)
		self.assertEqual(get(self.operation.name)["error"]["code"], "NOT_FOUND")
		frappe.set_user("Administrator")
		for changes in (
			{"company": OTHER},
			{"operation_type": "unregistered"},
			{"target_doctype": "User"},
			{"target_name": "missing"},
		):
			frappe.db.savepoint("progress_target")
			frappe.db.set_value("WA Operation", self.operation.name, changes)
			frappe.set_user(self.manager)
			self.assertEqual(get(self.operation.name)["error"]["code"], "NOT_FOUND")
			frappe.set_user("Administrator")
			frappe.db.rollback(save_point="progress_target")
		frappe.db.set_value("WA Connection", self.target.name, "company", OTHER)
		frappe.set_user(self.manager)
		self.assertEqual(get(self.operation.name)["error"]["code"], "NOT_FOUND")

	def test_corrupt_progress_is_not_a_success_or_an_invented_value(self):
		frappe.set_user(self.owner)
		for progress in (-1, 101):
			frappe.db.set_value("WA Operation", self.operation.name, "progress_percent", progress)
			result = get(self.operation.name)
			self.assertFalse(result["ok"])
			self.assertEqual(frappe.local.response.http_status_code, 503)

	def test_expected_command_failure_rolls_back_and_redacts_message_log(self):
		@boundary(mutates=True)
		def action():
			raw("WA Tag", name="_WA Failed Command", company=COMPANY, tag_name="fixture")
			frappe.msgprint("secret request value")
			raise CommandError("STALE_DOCUMENT", "expected_modified")

		result = action()
		self.assertFalse(frappe.db.exists("WA Tag", "_WA Failed Command"))
		self.assertEqual(result["error"]["code"], "STALE_DOCUMENT")
		self.assertEqual(frappe.local.response.http_status_code, 409)
		self.assertFalse(frappe.local.message_log)
		self.assertNotIn("secret", str(result))

	def test_unexpected_failure_has_only_a_safe_correlation_reference(self):
		@boundary(mutates=True)
		def action():
			raw("WA Tag", name="_WA Unexpected Command", company=COMPANY, tag_name="fixture")
			raise RuntimeError("secret provider token")

		with patch("frappe.logger") as logger:
			result = action()
			self.assertNotIn("secret", str(logger.mock_calls))
		self.assertFalse(frappe.db.exists("WA Tag", "_WA Unexpected Command"))
		self.assertEqual(frappe.local.response.http_status_code, 500)
		self.assertRegex(result["error"]["correlation_id"], r"^[a-f0-9]{32}$")
		self.assertNotIn("secret", str(result))

	def test_native_validation_is_redacted_and_rolls_back_the_command(self):
		@boundary(mutates=True)
		def action():
			raw("WA Tag", name="_WA Invalid Command", company=COMPANY, tag_name="fixture")
			frappe.throw("secret validation value")

		result = action()
		self.assertFalse(frappe.db.exists("WA Tag", "_WA Invalid Command"))
		self.assertEqual(result["error"]["code"], "INVALID_INPUT")
		self.assertEqual(frappe.local.response.http_status_code, 400)
		self.assertFalse(frappe.local.message_log)
		self.assertNotIn("secret", str(result))
