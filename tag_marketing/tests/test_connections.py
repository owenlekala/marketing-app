"""P2 connection service tests against the migrated disposable Frappe site."""

from unittest.mock import patch

import frappe

from tag_marketing.application.connection_jobs import run_connection_operation
from tag_marketing.application.connections import enqueue_connection_operation, set_enabled
from tag_marketing.application.operations import get_progress
from tag_marketing.domain.errors import CommandError
from tag_marketing.infrastructure.meta_cloud import ProviderNumber, ProviderPage, ProviderTemplate
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw

COMPANY = "_WA Connections Company"


class TestConnectionCommands(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		if not frappe.db.exists("Company", COMPANY):
			frappe.get_doc(
				{
					"doctype": "Company",
					"name": COMPANY,
					"company_name": COMPANY,
					"abbr": "WAC",
					"country": "South Africa",
					"default_currency": "ZAR",
				}
			).db_insert()
		frappe.db.set_single_value("WA Settings", "marketing_company", COMPANY)
		self.manager = self.create_user("Marketing Manager", "connection-manager")
		self.system_manager = self.create_user("System Manager", "connection-admin")
		self.connection = raw(
			"WA Connection",
			name="_wa_connection_command_fixture",
			company=COMPANY,
			connection_name="Command Fixture",
			public_id="connection-fixture-public-id",
			meta_app_id="123456789",
			waba_id="987654321",
			api_version="v26.0",
			status="Ready",
		)

	def create_user(self, role, suffix):
		return (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": f"wa-connection-{suffix}@example.invalid",
					"first_name": "WA Connection Test",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
					"roles": [{"role": role}],
				}
			)
			.insert()
			.name
		)

	def test_manager_can_queue_only_template_sync_and_read_its_safe_progress(self):
		frappe.set_user(self.manager)
		with patch("frappe.enqueue") as enqueue:
			result = enqueue_connection_operation(
				"sync_templates", self.connection.name, "template-sync-0001"
			)
			self.assertTrue(enqueue.called)
			operation = result["operation"]
			progress = get_progress(operation)
		self.assertEqual(progress["status"], "Pending")
		self.assertIsNone(progress["result"])
		self.assertIsNone(progress["result_file"])
		self.assertFalse(frappe.get_doc("WA Connection", self.connection.name).has_permission("read"))

	def test_manager_cannot_validate_connection_or_sync_numbers(self):
		frappe.set_user(self.manager)
		for operation in ("validate_connection", "sync_numbers"):
			with self.subTest(operation=operation), self.assertRaises(frappe.PermissionError):
				enqueue_connection_operation(
					operation,
					self.connection.name,
					f"manager-{operation}-01",
					expected_modified=self.connection.modified,
				)

	def test_sync_request_is_durable_idempotent_and_conflicting_arguments_fail_closed(self):
		frappe.set_user(self.system_manager)
		with patch("frappe.enqueue") as enqueue:
			first = enqueue_connection_operation("sync_numbers", self.connection.name, "number-sync-0001")
			second = enqueue_connection_operation("sync_numbers", self.connection.name, "number-sync-0001")
		self.assertEqual(first, second)
		self.assertEqual(enqueue.call_count, 1)
		other = raw(
			"WA Connection",
			name="_wa_connection_second_fixture",
			company=COMPANY,
			connection_name="Second Fixture",
			public_id="second-connection-public-id",
			meta_app_id="123456788",
			waba_id="987654322",
			api_version="v26.0",
			status="Ready",
		)
		with self.assertRaises(CommandError) as context:
			enqueue_connection_operation("sync_numbers", other.name, "number-sync-0001")
		self.assertEqual(context.exception.code, "IDEMPOTENCY_CONFLICT")

	def test_disable_is_immediate_and_reconnect_requires_fresh_queued_validation(self):
		frappe.set_user(self.system_manager)
		revision = str(self.connection.modified)
		with patch("frappe.enqueue") as enqueue:
			disabled = set_enabled(self.connection.name, False, revision, "disable-connection-0001")
		self.assertEqual(frappe.db.get_value("WA Connection", self.connection.name, "status"), "Disabled")
		self.assertEqual(frappe.db.get_value("WA Operation", disabled["operation"], "status"), "Succeeded")
		self.assertEqual(enqueue.call_count, 0)
		self.assertEqual(
			set_enabled(self.connection.name, False, revision, "disable-connection-0001"), disabled
		)
		revision = str(frappe.db.get_value("WA Connection", self.connection.name, "modified"))
		with patch("frappe.enqueue") as enqueue:
			reconnected = set_enabled(self.connection.name, True, revision, "reconnect-connection-0001")
		self.assertEqual(frappe.db.get_value("WA Connection", self.connection.name, "status"), "Verifying")
		self.assertEqual(frappe.db.get_value("WA Operation", reconnected["operation"], "status"), "Pending")
		self.assertEqual(enqueue.call_count, 1)

	def test_stale_validation_revision_is_rejected_before_an_operation_is_created(self):
		frappe.set_user(self.system_manager)
		old_revision = str(self.connection.modified)
		frappe.db.set_value("WA Connection", self.connection.name, "connection_name", "Changed Concurrently")
		with patch("frappe.enqueue"), self.assertRaises(CommandError) as context:
			enqueue_connection_operation(
				"validate_connection",
				self.connection.name,
				"stale-validation-0001",
				expected_modified=old_revision,
			)
		self.assertEqual(context.exception.code, "STALE_DOCUMENT")

	def test_manager_cannot_read_validation_operation_for_hidden_connection(self):
		frappe.set_user(self.system_manager)
		with patch("frappe.enqueue"):
			operation = enqueue_connection_operation(
				"validate_connection",
				self.connection.name,
				"validate-connection-01",
				expected_modified=self.connection.modified,
			)["operation"]
		frappe.set_user(self.manager)
		with self.assertRaises(CommandError) as context:
			get_progress(operation)
		self.assertEqual(context.exception.code, "NOT_FOUND")

	def test_connection_secrets_remain_encrypted_and_rotate_invalidates_readiness(self):
		frappe.set_user(self.system_manager)
		doc = frappe.get_doc(
			{
				"doctype": "WA Connection",
				"connection_name": "Secret Test",
				"meta_app_id": "123456780",
				"waba_id": "987654320",
				"api_version": "v26.0",
				"access_token": "access-token-value-123456789",
				"app_secret": "app-secret-value-123456789",
				"verify_token": "verify-token-value-123456789",
			}
		).insert()
		self.assertEqual(doc.company, COMPANY)
		self.assertEqual(doc.status, "Draft")
		self.assertEqual(doc.get_password("access_token"), "access-token-value-123456789")
		self.assertNotIn("access-token-value-123456789", str(doc.as_dict()))
		doc.status = "Ready"
		# The lifecycle state cannot be forged by a document save.
		with self.assertRaises(frappe.PermissionError):
			doc.save()
		doc.db_set({"status": "Ready", "last_validated_at": frappe.utils.now_datetime()})
		doc.reload()
		doc.access_token = "rotated-access-token-123456789"
		doc.save()
		self.assertEqual(doc.status, "Degraded")
		self.assertIsNone(doc.last_validated_at)
		self.assertEqual(doc.get_password("access_token"), "rotated-access-token-123456789")

	def test_fake_provider_sync_is_idempotent_and_preserves_local_number_configuration(self):
		frappe.set_user(self.system_manager)
		number = raw(
			"WA Sending Number",
			name="_wa_number_command_fixture",
			company=COMPANY,
			connection=self.connection.name,
			provider_phone_id="111222333",
			display_phone="+27110000000",
			display_name="Old display name",
			status="Unverified",
			rate_per_second=7,
		)
		operation = raw(
			"WA Operation",
			name="_wa_number_sync_operation",
			company=COMPANY,
			operation_type="connections.sync_numbers",
			requested_by=self.system_manager,
			request_id="fake-number-sync-0001",
			request_hash="a" * 64,
			target_doctype="WA Connection",
			target_name=self.connection.name,
			status="Pending",
			progress_percent=0,
		)

		class FakeProvider:
			def list_numbers(self, *, cursor=None, limit=100):
				return ProviderPage(
					items=(ProviderNumber("111222333", "+27110000001", "Updated display name", "GREEN"),),
					next_cursor=None,
				)

		with (
			patch("tag_marketing.application.connection_jobs.provider_factory", return_value=FakeProvider()),
			patch.object(frappe.db, "commit"),
		):
			run_connection_operation(
				operation.name,
				"sync_numbers",
				self.connection.name,
				{"connection": self.connection.name},
			)
		self.assertEqual(frappe.db.get_value("WA Operation", operation.name, "status"), "Succeeded")
		self.assertEqual(
			frappe.db.get_value("WA Operation", operation.name, "result_json"), '{"synced_count":1}'
		)
		self.assertEqual(
			frappe.db.get_value("WA Sending Number", number.name, "display_name"), "Updated display name"
		)
		self.assertEqual(frappe.db.get_value("WA Sending Number", number.name, "rate_per_second"), 7)

	def test_fake_provider_retains_unknown_template_status_without_treating_it_as_approved(self):
		frappe.set_user(self.manager)
		operation = raw(
			"WA Operation",
			name="_wa_template_sync_operation",
			company=COMPANY,
			operation_type="connections.sync_templates",
			requested_by=self.manager,
			request_id="fake-template-sync-0001",
			request_hash="b" * 64,
			target_doctype="WA Connection",
			target_name=self.connection.name,
			status="Pending",
			progress_percent=0,
		)

		class FakeProvider:
			def list_templates(self, *, cursor=None, limit=100):
				return ProviderPage(
					items=(
						ProviderTemplate(
							"444555666",
							"Welcome",
							"en_US",
							"UNRECOGNIZED",
							"IN_REVIEW",
							({"type": "BODY", "text": "Hello"},),
						),
					),
					next_cursor=None,
				)

		with (
			patch("tag_marketing.application.connection_jobs.provider_factory", return_value=FakeProvider()),
			patch.object(frappe.db, "commit"),
		):
			run_connection_operation(
				operation.name,
				"sync_templates",
				self.connection.name,
				{"connection": self.connection.name},
			)
		template_name = frappe.db.get_value("WA Template", {"provider_template_id": "444555666"}, "name")
		template = frappe.get_doc("WA Template", template_name)
		self.assertEqual(template.company, COMPANY)
		self.assertEqual(template.status, "Unknown")
		self.assertEqual(template.category, "Unknown")
		progress = get_progress(operation.name)
		self.assertEqual(progress["result"], {"synced_count": 1})
		self.assertIsNone(progress["result_file"])
