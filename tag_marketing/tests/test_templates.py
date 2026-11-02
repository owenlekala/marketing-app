"""Company-scoped local template lifecycle tests using the disposable site."""

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.utils.file_manager import save_file

from tag_marketing.application.template_jobs import run_template_operation
from tag_marketing.application.templates import save_draft, submit
from tag_marketing.domain.errors import CommandError
from tag_marketing.domain.templates import content_hash, validate_definition
from tag_marketing.infrastructure.meta_cloud import FailureKind, ProviderFailure, TemplateSubmission
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw


class TestTemplateCommands(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self._clean_abandoned_run()
		self.company = "_WA Template " + uuid4().hex[:8]
		self.previous_company = frappe.db.get_single_value("WA Settings", "marketing_company")
		raw(
			"Company",
			name=self.company,
			company_name=self.company,
			abbr=uuid4().hex[:3].upper(),
			country="South Africa",
			default_currency="ZAR",
		)
		frappe.db.set_single_value("WA Settings", "marketing_company", self.company)
		self.actor = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": "wa-template-" + uuid4().hex + "@example.invalid",
					"first_name": "WA Template",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
					"roles": [{"role": "Marketing Manager"}],
				}
			)
			.insert()
			.name
		)
		self.connection = raw(
			"WA Connection",
			company=self.company,
			connection_name="Template Test",
			public_id="template-connection-" + uuid4().hex,
			meta_app_id=str(int(uuid4().hex[:12], 16)),
			waba_id=str(int(uuid4().hex[:12], 16)),
			api_version="v26.0",
			status="Ready",
		)
		self.second_connection = raw(
			"WA Connection",
			company=self.company,
			connection_name="Template Test Other",
			public_id="template-connection-" + uuid4().hex,
			meta_app_id=str(int(uuid4().hex[:12], 16)),
			waba_id=str(int(uuid4().hex[:12], 16)),
			api_version="v26.0",
			status="Ready",
		)
		self.files: list[Path] = []

	def _clean_abandoned_run(self):
		"""Remove only this suite's synthetic fixtures left by an interrupted old run."""
		companies = [
			name
			for name in frappe.get_all("Company", pluck="name")
			if name.startswith("_WA Template ") and len(name) == len("_WA Template ") + 8
		]
		for company in companies:
			templates = frappe.get_all("WA Template", filters={"company": company}, pluck="name")
			for template in templates:
				frappe.db.delete("WA Template Revision", {"template": template})
			frappe.db.delete("WA Template Revision", {"company": company})
			frappe.db.delete("WA Audit Event", {"company": company})
			frappe.db.delete("WA Operation", {"company": company})
			frappe.db.delete("WA Template", {"company": company})
			frappe.db.delete("WA Connection", {"company": company})
			frappe.db.delete("Company", {"name": company})
		users = frappe.get_all("User", fields=["name", "email"])
		for user in users:
			if user.email.startswith("wa-template-") and user.email.endswith("@example.invalid"):
				frappe.delete_doc("User", user.name, ignore_permissions=True)
		for file in frappe.get_all("File", fields=["name", "owner"]):
			if file.owner.startswith("wa-template-") and file.owner.endswith("@example.invalid"):
				path = Path(frappe.get_doc("File", file.name).get_full_path())
				frappe.db.delete("File", {"name": file.name})
				path.unlink(missing_ok=True)
		current_company = frappe.db.get_single_value("WA Settings", "marketing_company")
		if isinstance(current_company, str) and current_company.startswith("_WA Template "):
			frappe.db.set_single_value("WA Settings", "marketing_company", None)
		frappe.db.commit()

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		for template in frappe.get_all("WA Template", filters={"company": self.company}, pluck="name"):
			frappe.db.delete("WA Template Revision", {"template": template})
		frappe.db.delete("WA Template Revision", {"company": self.company})
		frappe.db.delete("WA Audit Event", {"company": self.company})
		frappe.db.delete("WA Operation", {"company": self.company})
		frappe.db.delete("WA Template", {"company": self.company})
		frappe.db.delete("WA Connection", {"company": self.company})
		for file in frappe.get_all("File", filters={"owner": self.actor}, fields=["name"]):
			path = Path(frappe.get_doc("File", file.name).get_full_path())
			frappe.db.delete("File", {"name": file.name})
			path.unlink(missing_ok=True)
		if frappe.db.exists("User", self.actor):
			frappe.delete_doc("User", self.actor, ignore_permissions=True)
		frappe.db.set_single_value("WA Settings", "marketing_company", self.previous_company)
		frappe.db.delete("Company", {"name": self.company})
		frappe.db.commit()
		return super().tearDown()

	def _save(
		self, *, connection=None, request_id="template-save-001", template=None, modified=None, **overrides
	):
		frappe.set_user(self.actor)
		args = {
			"connection_name": connection or self.connection.name,
			"template_name": "order_update",
			"language_code": "en_US",
			"category": "Utility",
			"components": [{"type": "BODY", "text": "Hello {{1}}"}],
			"request_id": request_id,
			"template": template,
			"expected_modified": modified,
		}
		args.update(overrides)
		return save_draft(**args)

	def test_draft_save_is_idempotent_and_content_hash_is_bound(self):
		first = self._save()
		replay = self._save()
		self.assertEqual(first, replay)
		self.assertEqual(frappe.db.get_value("WA Template", first["template"], "status"), "Draft")
		self.assertEqual(frappe.db.get_value("WA Template", first["template"], "revision_number"), 1)
		with self.assertRaises(CommandError) as error:
			self._save(request_id="template-save-001", language_code="fr")
		self.assertEqual(error.exception.code, "IDEMPOTENCY_CONFLICT")

	def test_draft_cannot_cross_connection_and_authentication_is_sync_only(self):
		result = self._save()
		with self.assertRaises(CommandError) as error:
			self._save(
				connection=self.second_connection.name,
				request_id="template-cross-connection",
				template=result["template"],
				modified=str(frappe.db.get_value("WA Template", result["template"], "modified")),
			)
		self.assertEqual(error.exception.code, "NOT_FOUND")
		with self.assertRaises(CommandError) as error:
			self._save(request_id="template-auth-001", category="Authentication")
		self.assertEqual(error.exception.code, "INVALID_INPUT")

	def test_fake_png_signature_with_wrong_content_is_rejected(self):
		frappe.set_user(self.actor)
		file_doc = save_file(
			"fake.png", b"\x89PNG\r\n\x1a\nthis is not a PNG image", None, None, is_private=1
		)
		self.files.append(Path(file_doc.get_full_path()))
		with self.assertRaises(CommandError) as error:
			self._save(request_id="template-media-001", media_file=file_doc.name)
		self.assertEqual(error.exception.code, "INVALID_INPUT")

	def test_private_media_rejects_file_size_metadata_mismatch(self):
		frappe.set_user(self.actor)
		file_doc = save_file(
			"fake.png", b"\x89PNG\r\n\x1a\nthis is not a PNG image", None, None, is_private=1
		)
		self.files.append(Path(file_doc.get_full_path()))
		frappe.db.set_value("File", file_doc.name, "file_size", len(file_doc.get_content()) + 1)
		with self.assertRaises(CommandError) as error:
			self._save(request_id="template-media-size", media_file=file_doc.name)
		self.assertEqual(error.exception.code, "INVALID_INPUT")

	def test_approved_edit_archives_provider_revision_before_local_draft_change(self):
		components = [{"type": "BODY", "text": "Approved {{1}}"}]
		canonical = validate_definition("order_update", "en_US", "Utility", components)
		frappe.set_user("Administrator")
		approved = raw(
			"WA Template",
			company=self.company,
			connection=self.connection.name,
			provider_template_id="provider-approved-id",
			template_name="order_update",
			language_code="en_US",
			category="Utility",
			components_json=json.dumps(canonical),
			status="Approved",
			content_hash=content_hash("order_update", "en_US", "Utility", canonical),
			revision_number=1,
		)
		result = self._save(
			request_id="template-approved-edit",
			template=approved.name,
			modified=str(approved.modified),
			components=[{"type": "BODY", "text": "Updated {{1}}"}],
		)
		revision_name = frappe.db.get_value(
			"WA Template Revision", {"template": approved.name, "revision_number": 1}, "name"
		)
		revision = frappe.get_doc("WA Template Revision", revision_name)
		self.assertEqual(revision.content_hash, approved.content_hash)
		self.assertEqual(revision.provider_template_id, "provider-approved-id")
		self.assertEqual(frappe.db.get_value("WA Template", approved.name, "status"), "Draft")
		self.assertEqual(frappe.db.get_value("WA Template", approved.name, "revision_number"), 2)
		self.assertEqual(result["status"], "Draft")

	def test_submit_requires_exact_hash_and_queues_one_manager_operation(self):
		draft = self._save()
		template = frappe.get_doc("WA Template", draft["template"])
		with self.assertRaises(CommandError) as error:
			submit(template.name, "0" * 64, str(template.modified), "template-submit-bad")
		self.assertEqual(error.exception.code, "INVALID_STATE")
		with patch("tag_marketing.application.templates.frappe.enqueue") as enqueue:
			first = submit(template.name, template.content_hash, str(template.modified), "template-submit-01")
			replay = submit(
				template.name, template.content_hash, str(template.modified), "template-submit-01"
			)
		self.assertEqual(first, replay)
		self.assertEqual(enqueue.call_count, 1)
		self.assertEqual(frappe.db.get_value("WA Operation", first["operation"], "status"), "Pending")

	def test_submit_worker_persists_provider_pending_without_claiming_approval(self):
		draft = self._save()
		template = frappe.get_doc("WA Template", draft["template"])
		with patch("tag_marketing.application.templates.frappe.enqueue"):
			operation = submit(
				template.name,
				template.content_hash,
				str(template.modified),
				"template-submit-worker",
			)
		frappe.set_user("Administrator")
		fake_provider = type(
			"FakeProvider",
			(),
			{"create_template": lambda self, **kwargs: TemplateSubmission("provider-template-1", "PENDING")},
		)()
		with patch("tag_marketing.application.template_jobs.provider_factory", return_value=fake_provider):
			run_template_operation(operation["operation"])
		self.assertEqual(frappe.db.get_value("WA Template", template.name, "status"), "Pending")
		self.assertEqual(
			frappe.db.get_value("WA Template", template.name, "provider_template_id"), "provider-template-1"
		)
		self.assertEqual(frappe.db.get_value("WA Operation", operation["operation"], "status"), "Succeeded")

	def test_unknown_submission_outcome_is_terminal_and_blocks_duplicate_submit(self):
		draft = self._save()
		template = frappe.get_doc("WA Template", draft["template"])
		with patch("tag_marketing.application.templates.frappe.enqueue"):
			operation = submit(
				template.name,
				template.content_hash,
				str(template.modified),
				"template-submit-unknown",
			)
		frappe.set_user("Administrator")
		fake_provider = type(
			"FakeProvider",
			(),
			{
				"create_template": lambda self, **kwargs: (_ for _ in ()).throw(
					ProviderFailure(FailureKind.UNKNOWN_OUTCOME)
				)
			},
		)()
		with patch("tag_marketing.application.template_jobs.provider_factory", return_value=fake_provider):
			run_template_operation(operation["operation"])
		self.assertEqual(frappe.db.get_value("WA Template", template.name, "status"), "Unknown")
		self.assertEqual(
			frappe.db.get_value("WA Operation", operation["operation"], "error_code"), "UNKNOWN_OUTCOME"
		)
