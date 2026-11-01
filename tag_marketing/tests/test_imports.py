"""Real-site tests for append-only consent and company-wide suppression."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import frappe
from frappe.utils.file_manager import save_file

from tag_marketing.application.imports import confirm_batch, create_batch, record_consent
from tag_marketing.domain.errors import CommandError
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw


class TestConsentCommands(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.company = "_WA Consent " + uuid4().hex[:8]
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
					"email": "wa-consent-" + uuid4().hex + "@example.invalid",
					"first_name": "WA Consent",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
					"roles": [{"role": "Marketing Manager"}],
				}
			)
			.insert()
			.name
		)
		self.contact = raw(
			"WA Contact",
			company=self.company,
			phone_e164="+2782" + uuid4().hex[:7],
			display_name="Synthetic Consent Contact",
			consent_status="Unknown",
			suppressed=0,
			archived=0,
		)
		self.file_paths: list[Path] = []

	def tearDown(self):
		for path in self.file_paths:
			path.unlink(missing_ok=True)
		frappe.db.set_single_value("WA Settings", "marketing_company", self.previous_company)
		super().tearDown()

	def upload(self, content: bytes):
		frappe.set_user(self.actor)
		file_doc = save_file("synthetic.csv", content, None, None, is_private=1)
		self.file_paths.append(Path(file_doc.get_full_path()))
		return file_doc.name

	def test_private_import_preview_rejects_bad_rows_and_confirmation_replays_safely(self):
		file_name = self.upload(b"Name,Mobile\nSynthetic,0821234567\nFormula,not-a-phone\n")
		mapping = {"columns": {"phone": "Mobile", "display_name": "Name"}, "default_country_code": "ZA"}
		preview = create_batch(file_name, mapping)
		self.assertEqual((preview["row_count"], preview["valid_count"], preview["rejected_count"]), (2, 1, 1))
		batch = frappe.get_doc("WA Import Batch", preview["batch"])
		diagnostic = frappe.get_doc("File", batch.result_file)
		self.assertEqual(diagnostic.is_private, 1)
		self.assertNotIn("not-a-phone", diagnostic.get_content())
		result = confirm_batch(batch.name, preview["input_hash"], str(batch.modified), "import-confirm-001")
		replay = confirm_batch(batch.name, preview["input_hash"], str(batch.modified), "import-confirm-001")
		self.assertEqual(result["operation"], replay["operation"])
		self.assertEqual(frappe.db.count("WA Contact", {"company": self.company}), 2)
		imported = frappe.db.get_value(
			"WA Import Row", {"batch": batch.name, "status": "Imported"}, "contact"
		)
		self.assertEqual(frappe.db.get_value("WA Contact", imported, "consent_status"), "Unknown")

	def test_duplicate_csv_identity_and_evidence_create_one_contact_and_one_grant(self):
		occurred = (datetime.now(UTC) - timedelta(minutes=1)).isoformat()
		content = (
			"Name,Mobile,When,Notice,Reference\n"
			f"Synthetic,0821234567,{occurred},notice-v1,evidence-1\n"
			f"Synthetic duplicate,0821234567,{occurred},notice-v1,evidence-1\n"
		).encode()
		file_name = self.upload(content)
		mapping = {
			"columns": {
				"phone": "Mobile",
				"display_name": "Name",
				"consent_occurred_at": "When",
				"consent_notice_version": "Notice",
				"consent_reference": "Reference",
			},
			"default_country_code": "ZA",
		}
		preview = create_batch(file_name, mapping)
		batch = frappe.get_doc("WA Import Batch", preview["batch"])
		confirm_batch(batch.name, preview["input_hash"], str(batch.modified), "import-confirm-002")
		contact_name = frappe.db.get_value(
			"WA Contact", {"company": self.company, "phone_e164": "+27821234567"}, "name"
		)
		self.assertTrue(contact_name)
		self.assertEqual(frappe.db.count("WA Consent Event", {"contact": contact_name}), 1)
		self.assertEqual(frappe.db.get_value("WA Contact", contact_name, "consent_status"), "Granted")

	def test_withdrawal_is_immediate_and_replayed_or_backdated_grant_cannot_restore(self):
		frappe.set_user(self.actor)
		grant_time = datetime.now(UTC) - timedelta(minutes=2)
		grant = record_consent(
			self.contact.name,
			"Granted",
			grant_time.isoformat(),
			"Web Form",
			"notice-v1",
			"synthetic-form-1",
			request_id="consent-grant-0001",
		)
		replay = record_consent(
			self.contact.name,
			"Granted",
			grant_time.isoformat(),
			"Web Form",
			"notice-v1",
			"synthetic-form-1",
			request_id="consent-grant-0001",
		)
		self.assertEqual(grant["event"], replay["event"])
		self.assertTrue(replay["replayed"])
		withdrawn = record_consent(
			self.contact.name,
			"Withdrawn",
			datetime.now(UTC).isoformat(),
			"Inbound Keyword",
			request_id="consent-withdraw-0001",
		)
		self.assertEqual(withdrawn["consent_status"], "Withdrawn")
		self.assertEqual(frappe.db.get_value("WA Contact", self.contact.name, "suppressed"), 1)
		self.assertTrue(
			frappe.db.get_value(
				"WA Suppression", {"company": self.company, "contact": self.contact.name}, "identity_digest"
			)
		)
		backdated = record_consent(
			self.contact.name,
			"Granted",
			grant_time.isoformat(),
			"Web Form",
			"notice-v1",
			"synthetic-old-form",
			request_id="consent-grant-0002",
		)
		self.assertEqual(backdated["consent_status"], "Withdrawn")
		# The historical grant remains auditable but does not change effective status.
		self.assertEqual(frappe.db.count("WA Consent Event", {"contact": self.contact.name}), 3)
		self.assertEqual(frappe.db.get_value("WA Contact", self.contact.name, "suppressed"), 1)

	def test_public_grant_cannot_claim_provider_only_inbound_source(self):
		frappe.set_user(self.actor)
		with self.assertRaises(CommandError):
			record_consent(
				self.contact.name,
				"Granted",
				datetime.now(UTC).isoformat(),
				"Inbound Keyword",
				"notice-v1",
				"synthetic-reference",
				request_id="consent-grant-0003",
			)
