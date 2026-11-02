"""Real-site tests for append-only consent and company-wide suppression."""

from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import frappe
from frappe.utils.file_manager import save_file

from tag_marketing.application.eligibility import lock_contact_for_submission
from tag_marketing.application.import_jobs import (
	_import_row as import_row,
)
from tag_marketing.application.import_jobs import (
	recover_import_operations,
	run_import_operation,
)
from tag_marketing.application.imports import confirm_batch, create_batch, record_consent
from tag_marketing.domain.errors import CommandError
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw


class TestConsentCommands(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		self._durable_import_test = False
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
		if self._durable_import_test:
			frappe.set_user("Administrator")
			batches = frappe.get_all(
				"WA Import Batch", filters={"company": self.company, "requested_by": self.actor}, pluck="name"
			)
			for batch_name in batches:
				frappe.db.delete("WA Import Row", {"batch": batch_name})
			frappe.db.delete(
				"WA Operation",
				{"company": self.company, "requested_by": self.actor, "target_doctype": "WA Import Batch"},
			)
			frappe.db.delete("WA Import Batch", {"company": self.company, "requested_by": self.actor})
			frappe.db.delete("WA Consent Event", {"company": self.company})
			frappe.db.delete("WA Suppression", {"company": self.company})
			frappe.db.delete(
				"WA Contact Tag",
				{
					"parent": [
						"in",
						frappe.get_all("WA Contact", filters={"company": self.company}, pluck="name"),
					]
				},
			)
			frappe.db.delete(
				"WA Source Link",
				{
					"parent": [
						"in",
						frappe.get_all("WA Contact", filters={"company": self.company}, pluck="name"),
					]
				},
			)
			frappe.db.delete("WA Audit Event", {"company": self.company, "actor": self.actor})
			frappe.db.delete("WA Contact", {"company": self.company})
			for file in frappe.get_all("File", filters={"owner": self.actor}, fields=["name"]):
				file_path = Path(frappe.get_doc("File", file.name).get_full_path())
				frappe.db.delete("File", {"name": file.name})
				file_path.unlink(missing_ok=True)
			if frappe.db.exists("User", self.actor):
				frappe.delete_doc("User", self.actor, ignore_permissions=True)
			frappe.db.set_single_value("WA Settings", "marketing_company", self.previous_company)
			frappe.db.delete("Company", {"name": self.company})
			frappe.clear_document_cache("Company", self.company)
			frappe.db.commit()
			return super().tearDown()
		for path in self.file_paths:
			path.unlink(missing_ok=True)
		frappe.db.set_single_value("WA Settings", "marketing_company", self.previous_company)
		super().tearDown()

	def upload(self, content: bytes):
		frappe.set_user(self.actor)
		file_doc = save_file("synthetic.csv", content, None, None, is_private=1)
		self.file_paths.append(Path(file_doc.get_full_path()))
		return file_doc.name

	def confirm_and_run(self, batch, digest, modified, request_id):
		frappe.set_user(self.actor)
		with (
			patch("tag_marketing.application.imports.frappe.enqueue") as enqueue,
			patch("tag_marketing.application.import_jobs.frappe.db.commit"),
		):
			result = confirm_batch(batch, digest, modified, request_id)
			enqueue.assert_called_once()
			run_import_operation(result["operation"])
		frappe.set_user(self.actor)
		self.assertEqual(frappe.db.get_value("WA Operation", result["operation"], "status"), "Succeeded")
		return result

	def test_private_import_preview_rejects_bad_rows_and_confirmation_replays_safely(self):
		file_name = self.upload(b"Name,Mobile\nSynthetic,0821234567\nFormula,not-a-phone\n")
		mapping = {"columns": {"phone": "Mobile", "display_name": "Name"}, "default_country_code": "ZA"}
		preview = create_batch(file_name, mapping)
		self.assertEqual((preview["row_count"], preview["valid_count"], preview["rejected_count"]), (2, 1, 1))
		batch = frappe.get_doc("WA Import Batch", preview["batch"])
		diagnostic = frappe.get_doc("File", batch.result_file)
		self.assertEqual(diagnostic.is_private, 1)
		self.assertNotIn("not-a-phone", diagnostic.get_content())
		result = self.confirm_and_run(
			batch.name, preview["input_hash"], str(batch.modified), "import-confirm-001"
		)
		replay = confirm_batch(batch.name, preview["input_hash"], str(batch.modified), "import-confirm-001")
		self.assertEqual(result["operation"], replay["operation"])
		self.assertEqual(frappe.db.get_value("WA Import Batch", batch.name, "status"), "Completed")
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
		self.confirm_and_run(batch.name, preview["input_hash"], str(batch.modified), "import-confirm-002")
		contact_name = frappe.db.get_value(
			"WA Contact", {"company": self.company, "phone_e164": "+27821234567"}, "name"
		)
		self.assertTrue(contact_name)
		self.assertEqual(frappe.db.count("WA Consent Event", {"contact": contact_name}), 1)
		self.assertEqual(frappe.db.get_value("WA Contact", contact_name, "consent_status"), "Granted")

	def test_minimized_suppression_survives_detached_contact_and_blocks_csv_reimport(self):
		frappe.set_user(self.actor)
		phone = "+27821234561"
		frappe.db.set_value("WA Contact", self.contact.name, "phone_e164", phone, update_modified=False)
		record_consent(
			self.contact.name,
			"Withdrawn",
			datetime.now(UTC).isoformat(),
			"Inbound Keyword",
			request_id="consent-erase-preserve-001",
		)
		suppression = frappe.db.get_value(
			"WA Suppression", {"company": self.company, "contact": self.contact.name}, "name"
		)
		self.assertTrue(frappe.db.get_value("WA Suppression", suppression, "identity_digest"))
		# Simulate approved erasure: delete identity-bearing records and retain only the keyed suppression.
		frappe.db.set_value("WA Suppression", suppression, "contact", None, update_modified=False)
		frappe.db.delete("WA Consent Event", {"contact": self.contact.name})
		frappe.db.delete("WA Contact", self.contact.name)
		file_name = self.upload(f"Name,Mobile\nReimport,{phone}\n".encode())
		mapping = {
			"columns": {"phone": "Mobile", "display_name": "Name"},
			"default_country_code": "ZA",
		}
		preview = create_batch(file_name, mapping)
		batch = frappe.get_doc("WA Import Batch", preview["batch"])
		self.confirm_and_run(batch.name, preview["input_hash"], str(batch.modified), "import-suppressed-001")
		row = frappe.get_value(
			"WA Import Row",
			{"batch": batch.name, "row_number": 2},
			["name", "status", "error_code", "contact"],
			as_dict=True,
		)
		self.assertEqual(
			(row.status, row.error_code, row.contact), ("Suppressed", "ACTIVE_SUPPRESSION", None)
		)
		self.assertEqual(frappe.db.count("WA Contact", {"company": self.company, "phone_e164": phone}), 0)
		frappe.db.set_value("WA Suppression", suppression, "active", 0, update_modified=False)
		self.assertFalse(import_row(batch, preview["input_hash"], {"row_number": 2}))
		self.assertEqual(frappe.db.get_value("WA Import Row", row.name, "status"), "Suppressed")
		self.assertEqual(frappe.db.count("WA Contact", {"company": self.company, "phone_e164": phone}), 0)

	def test_withdrawal_waits_for_shared_submission_lock_and_closes_next_gate(self):
		self._durable_import_test = True
		frappe.set_user(self.actor)
		grant_at = datetime.now(UTC) - timedelta(minutes=1)
		record_consent(
			self.contact.name,
			"Granted",
			grant_at.isoformat(),
			"Web Form",
			"notice-v1",
			"synthetic-form-race",
			request_id="consent-race-grant-001",
		)
		frappe.db.commit()
		self.assertTrue(lock_contact_for_submission(self.company, self.contact.name))
		site, sites_path = frappe.local.site, frappe.local.sites_path
		attempting = Event()
		completed = Event()

		def withdraw():
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
			frappe.set_user(self.actor)
			try:
				attempting.set()
				result = record_consent(
					self.contact.name,
					"Withdrawn",
					datetime.now(UTC).isoformat(),
					"Inbound Keyword",
					request_id="consent-race-withdraw-001",
				)
				frappe.db.commit()
				return result
			finally:
				completed.set()
				frappe.destroy()

		with ThreadPoolExecutor(max_workers=1) as pool:
			pending_withdrawal = pool.submit(withdraw)
			self.assertTrue(attempting.wait(timeout=5))
			self.assertFalse(completed.wait(timeout=0.1))
			frappe.db.commit()
			self.assertEqual(pending_withdrawal.result(timeout=10)["consent_status"], "Withdrawn")
		self.assertTrue(completed.is_set())
		self.assertFalse(lock_contact_for_submission(self.company, self.contact.name))
		frappe.db.commit()

	def test_stale_import_worker_resumes_from_completed_ledger_rows(self):
		file_name = self.upload(b"Name,Mobile\nFirst,0821234567\nSecond,0821234568\n")
		mapping = {"columns": {"phone": "Mobile", "display_name": "Name"}, "default_country_code": "ZA"}
		preview = create_batch(file_name, mapping)
		batch = frappe.get_doc("WA Import Batch", preview["batch"])
		frappe.set_user(self.actor)
		with patch("tag_marketing.application.imports.frappe.enqueue") as enqueue:
			result = confirm_batch(
				batch.name, preview["input_hash"], str(batch.modified), "import-resume-001"
			)
			enqueue.assert_called_once()
		operation = result["operation"]
		first_row = frappe.db.get_value(
			"WA Import Row",
			{"batch": batch.name, "row_number": 2},
			["name", "projection_json"],
			as_dict=True,
		)
		projection = frappe.parse_json(first_row.projection_json)
		first_contact = raw(
			"WA Contact",
			company=self.company,
			phone_e164=projection["phone_e164"],
			display_name=projection["display_name"],
			consent_status="Unknown",
			suppressed=0,
			archived=0,
		)
		frappe.db.set_value(
			"WA Import Row", first_row.name, {"contact": first_contact.name, "status": "Imported"}
		)
		frappe.db.set_value(
			"WA Operation",
			operation,
			{
				"status": "Running",
				"attempt_count": 1,
				"heartbeat_at": datetime.now(UTC) - timedelta(minutes=10),
			},
		)
		with (
			patch("tag_marketing.application.import_jobs.frappe.enqueue") as enqueue,
			patch("tag_marketing.application.import_jobs.frappe.db.commit"),
		):
			recover_import_operations()
			enqueue.assert_called_once()
			run_import_operation(operation)
		self.assertEqual(frappe.db.get_value("WA Operation", operation, "status"), "Succeeded")
		self.assertEqual(frappe.db.get_value("WA Import Batch", batch.name, "status"), "Completed")
		self.assertEqual(frappe.db.count("WA Import Row", {"batch": batch.name, "status": "Imported"}), 2)
		self.assertEqual(frappe.db.count("WA Contact", {"company": self.company}), 3)

	def test_process_crash_after_committed_chunk_resumes_without_duplicate_contacts(self):
		self._durable_import_test = True
		lines = ["Name,Mobile"] + [f"Contact {index},082{1_234_500 + index:07d}" for index in range(101)]
		file_name = self.upload(("\n".join(lines) + "\n").encode())
		mapping = {"columns": {"phone": "Mobile", "display_name": "Name"}, "default_country_code": "ZA"}
		preview = create_batch(file_name, mapping)
		batch = frappe.get_doc("WA Import Batch", preview["batch"])
		frappe.set_user(self.actor)
		with patch("tag_marketing.application.imports.frappe.enqueue") as enqueue:
			result = confirm_batch(batch.name, preview["input_hash"], str(batch.modified), "import-crash-001")
			enqueue.assert_called_once()

		def crash_after_first_committed_chunk(batch_doc, digest, row):
			if row["row_number"] == 102:
				raise RuntimeError("simulated process termination")
			return import_row(batch_doc, digest, row)

		with patch(
			"tag_marketing.application.import_jobs._import_row", side_effect=crash_after_first_committed_chunk
		):
			run_import_operation(result["operation"])
		self.assertEqual(frappe.db.count("WA Import Row", {"batch": batch.name, "status": "Imported"}), 100)
		self.assertEqual(frappe.db.get_value("WA Operation", result["operation"], "status"), "Running")
		frappe.db.set_value(
			"WA Operation",
			result["operation"],
			{"heartbeat_at": datetime.now(UTC) - timedelta(minutes=10)},
		)
		frappe.db.commit()
		with patch("tag_marketing.application.import_jobs.frappe.enqueue") as enqueue:
			recover_import_operations()
			enqueue.assert_called_once()
			run_import_operation(result["operation"])
		self.assertEqual(frappe.db.get_value("WA Operation", result["operation"], "status"), "Succeeded")
		self.assertEqual(frappe.db.get_value("WA Import Batch", batch.name, "status"), "Completed")
		self.assertEqual(frappe.db.count("WA Import Row", {"batch": batch.name, "status": "Imported"}), 101)
		self.assertEqual(frappe.db.count("WA Contact", {"company": self.company}), 102)

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
