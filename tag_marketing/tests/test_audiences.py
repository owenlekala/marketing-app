"""P3 source projections enforce current ERPNext access and phone identity rules."""

import tracemalloc
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import frappe

from tag_marketing.application.audience_preview_jobs import (
	recover_audience_preview_operations,
	run_audience_preview_operation,
)
from tag_marketing.application.audience_segments import (
	iterate_snapshot_recipients,
	request_preview,
	save_segment,
	set_segment_disabled,
)
from tag_marketing.application.audience_segments import preview as preview_segment
from tag_marketing.application.audiences import add_source, source_preview
from tag_marketing.application.operations import get_progress
from tag_marketing.application.suppression import digest_for_identity
from tag_marketing.domain.errors import CommandError
from tag_marketing.infrastructure.audience_repository import count_candidates
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw

COMPANY = "_WA Audiences Company"
OTHER = "_WA Audiences Other"


class TestAudienceSources(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.run_id = uuid4().hex[:12]
		self.created_companies = []
		self.created_users = []
		self.created_segments = []
		self.created_operations = []
		self.created_contacts = []
		for name, abbr in ((COMPANY, "WAA"), (OTHER, "WAB")):
			if not frappe.db.exists("Company", name):
				raw(
					"Company",
					name=name,
					company_name=name,
					abbr=abbr,
					country="South Africa",
					default_currency="ZAR",
				)
				self.created_companies.append(name)
		self.phone = f"082{int(self.run_id, 16) % 10_000_000:07d}"
		self.previous_company = frappe.db.get_single_value("WA Settings", "marketing_company")
		self.previous_sources = frappe.get_all(
			"WA Source Type", filters={"parent": "WA Settings"}, fields=["source_doctype", "idx"]
		)
		frappe.db.set_single_value("WA Settings", "marketing_company", COMPANY)
		frappe.db.delete("WA Source Type", {"parent": "WA Settings"})
		raw(
			"WA Source Type",
			parent="WA Settings",
			parenttype="WA Settings",
			parentfield="enabled_source_types",
			source_doctype="Lead",
			idx=1,
		)
		self.manager = self.user("Marketing Manager", "Sales User")
		self.lead = raw(
			"Lead",
			lead_name=f"Audience Fixture {self.run_id}",
			mobile_no=self.phone,
			country="South Africa",
			company=COMPANY,
		)

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		frappe.db.set_single_value("WA Settings", "marketing_company", self.previous_company)
		frappe.db.delete("WA Source Type", {"parent": "WA Settings"})
		for row in self.previous_sources:
			raw(
				"WA Source Type",
				parent="WA Settings",
				parenttype="WA Settings",
				parentfield="enabled_source_types",
				source_doctype=row.source_doctype,
				idx=row.idx,
			)
		lead_names = frappe.get_all(
			"Lead",
			filters={"company": COMPANY},
			or_filters=[
				["Lead", "lead_name", "like", "Audience Fixture %"],
				["Lead", "lead_name", "=", "Audience Fixture"],
			],
			pluck="name",
		)
		contact_names = (
			set(
				frappe.get_all(
					"WA Source Link",
					filters={"source_doctype": "Lead", "source_name": ["in", lead_names]},
					pluck="parent",
				)
			)
			if lead_names
			else set()
		)
		contact = frappe.db.get_value(
			"WA Contact", {"company": COMPANY, "phone_e164": "+27" + self.phone[1:]}, "name"
		)
		if contact:
			contact_names.add(contact)
		for contact_name in contact_names:
			frappe.db.delete("WA Contact Tag", {"parent": contact_name})
			frappe.db.delete("WA Source Link", {"parent": contact_name})
			frappe.db.delete("WA Contact", {"name": contact_name})
		if getattr(self, "tag_name", None):
			frappe.db.delete("WA Tag", {"name": self.tag_name})
		for segment in self.created_segments:
			frappe.db.delete("WA Audience Segment", {"name": segment})
		for operation in self.created_operations:
			frappe.db.delete("WA Operation", {"name": operation})
		for contact_name in self.created_contacts:
			frappe.db.delete("WA Contact Tag", {"parent": contact_name})
			frappe.db.delete("WA Source Link", {"parent": contact_name})
			frappe.db.delete("WA Contact", {"name": contact_name})
		if lead_names:
			frappe.db.delete("Lead", {"name": ["in", lead_names]})
		for user in self.created_users:
			frappe.delete_doc("User", user, ignore_permissions=True, force=True)
		for name in self.created_companies:
			frappe.db.delete("Company", {"name": name})
		frappe.db.commit()
		super().tearDown()

	def user(self, *roles):
		email = f"wa-audience-{self.run_id}-{'-'.join(role.lower().replace(' ', '-') for role in roles)}@example.invalid"
		previous_user = frappe.session.user
		frappe.set_user("Administrator")
		user = (
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": "WA Audience",
					"enabled": 1,
					"user_type": "System User",
					"send_welcome_email": 0,
					"roles": [{"role": role} for role in roles],
				}
			)
			.insert()
			.name
		)
		frappe.set_user(previous_user)
		self.created_users.append(user)
		return user

	def test_source_preview_is_permission_aware_and_add_is_idempotent_by_company_phone(self):
		frappe.set_user(self.manager)
		preview = source_preview("Lead", search=self.lead.lead_name, country_code="ZA")
		self.assertEqual([item["name"] for item in preview["items"]], [self.lead.name])
		self.assertTrue(preview["items"][0]["phones"][0]["phone_e164"].startswith("+2782"))
		first = add_source("Lead", self.lead.name, self.phone, "ZA")
		second = add_source("Lead", self.lead.name, self.phone, "ZA")
		self.assertEqual(first["contact"], second["contact"])
		self.assertTrue(first["created"])
		self.assertFalse(second["created"])
		contact = frappe.get_doc("WA Contact", first["contact"])
		self.assertEqual(contact.consent_status, "Unknown")
		self.assertEqual(len(contact.source_links), 1)
		tag = frappe.get_doc({"doctype": "WA Tag", "company": COMPANY, "label": f"P3-{self.run_id}"}).insert()
		self.tag_name = tag.name
		contact.display_name = "Edited by Marketing Manager"
		contact.append("tags", {"tag": tag.name})
		contact.save()
		self.assertEqual(
			frappe.db.get_value("WA Contact", first["contact"], "display_name"), "Edited by Marketing Manager"
		)
		contact.consent_status = "Granted"
		with self.assertRaises(frappe.PermissionError):
			contact.save()
		self.assertEqual(frappe.db.get_value("WA Contact", first["contact"], "consent_status"), "Unknown")

	def test_source_link_cannot_recreate_an_identity_in_minimized_suppression(self):
		phone_e164 = "+27" + self.phone[1:]
		frappe.set_user("Administrator")
		raw(
			"WA Suppression",
			company=COMPANY,
			contact=None,
			purpose="Marketing",
			reason="Opt Out",
			active=1,
			identity_digest=digest_for_identity(COMPANY, phone_e164),
			changed_at=frappe.utils.now_datetime(),
			changed_by="Administrator",
		)
		frappe.set_user(self.manager)
		with self.assertRaises(CommandError):
			add_source("Lead", self.lead.name, self.phone, "ZA")
		self.assertFalse(frappe.db.exists("WA Contact", {"company": COMPANY, "phone_e164": phone_e164}))

	def test_concurrent_contact_inserts_leave_one_company_phone_identity(self):
		site, sites_path = frappe.local.site, frappe.local.sites_path
		barrier = Barrier(2)
		frappe.db.commit()

		def compete():
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
			frappe.set_user(self.manager)
			try:
				barrier.wait(timeout=10)
				try:
					raw(
						"WA Contact",
						company=COMPANY,
						phone_e164="+27" + self.phone[1:],
						display_name=self.lead.lead_name,
						consent_status="Unknown",
					)
					frappe.db.commit()
					return "inserted"
				except frappe.UniqueValidationError:
					frappe.db.rollback()
					return "duplicate"
			finally:
				frappe.destroy()

		with ThreadPoolExecutor(max_workers=2) as pool:
			results = list(pool.map(lambda _index: compete(), range(2)))
		self.assertEqual(sorted(results), ["duplicate", "inserted"])
		self.assertEqual(
			frappe.db.count("WA Contact", {"company": COMPANY, "phone_e164": "+27" + self.phone[1:]}),
			1,
		)

	def test_unassigned_lead_requires_explicit_opt_in_and_stale_company_scope_fails(self):
		self.lead.company = None
		self.lead.db_update()
		frappe.set_user(self.manager)
		with self.assertRaises(CommandError):
			add_source("Lead", self.lead.name, self.phone, "ZA")
		self.assertTrue(add_source("Lead", self.lead.name, self.phone, "ZA", True)["created"])
		frappe.set_user("Administrator")
		frappe.db.set_value("Lead", self.lead.name, "company", OTHER)
		frappe.set_user(self.manager)
		with self.assertRaises(CommandError):
			add_source("Lead", self.lead.name, self.phone, "ZA")

	def test_customer_primary_contact_exposes_mobile_choices_without_inferring_consent(self):
		frappe.set_user("Administrator")
		frappe.db.delete("WA Source Type", {"parent": "WA Settings"})
		raw(
			"WA Source Type",
			parent="WA Settings",
			parenttype="WA Settings",
			parentfield="enabled_source_types",
			source_doctype="Customer",
			idx=1,
		)
		base = int(self.run_id, 16) % 1_000_000
		primary_mobile = f"082{base:07d}"
		alternate_mobile = f"083{(base + 1) % 10_000_000:07d}"
		contact = raw(
			"Contact",
			first_name="Primary",
			last_name=self.run_id,
			full_name=f"Primary {self.run_id}",
			mobile_no=primary_mobile,
		)
		raw(
			"Contact Phone",
			parent=contact.name,
			parenttype="Contact",
			parentfield="phone_nos",
			phone=alternate_mobile,
			is_primary_mobile_no=1,
			idx=1,
		)
		customer = raw(
			"Customer",
			customer_name=f"Shared Customer {self.run_id}",
			customer_primary_contact=contact.name,
			mobile_no="0101234567",
		)
		frappe.set_user(self.manager)
		preview = source_preview("Customer", search=customer.customer_name, country_code="ZA")
		self.assertEqual(len(preview["items"]), 1)
		self.assertTrue(preview["items"][0]["requires_phone_choice"])
		self.assertEqual(len(preview["items"][0]["phones"]), 2)
		linked = add_source("Customer", customer.name, alternate_mobile, "ZA")
		contact_record = frappe.get_doc("WA Contact", linked["contact"])
		self.assertEqual(contact_record.phone_e164, "+27" + alternate_mobile[1:])
		self.assertEqual(contact_record.consent_status, "Unknown")
		self.assertEqual(contact_record.source_links[0].selected_phone, alternate_mobile)
		new_identity = add_source("Customer", customer.name, primary_mobile, "ZA")
		self.assertNotEqual(new_identity["contact"], linked["contact"])
		self.assertEqual(
			frappe.db.get_value("WA Contact", new_identity["contact"], "consent_status"), "Unknown"
		)

	def test_contact_lists_are_company_scoped_and_not_exposed_to_agents_or_analysts(self):
		frappe.set_user(self.manager)
		contact_name = add_source("Lead", self.lead.name, self.phone, "ZA")["contact"]
		self.assertEqual(frappe.get_list("WA Contact", pluck="name"), [contact_name])
		agent = self.user("WhatsApp Agent")
		analyst = self.user("Marketing Analyst")
		for user in (agent, analyst):
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				frappe.get_list("WA Contact", pluck="name")
			self.assertFalse(frappe.has_permission("WA Contact", "read", doc=contact_name))

	def test_segment_preview_reconciles_eligibility_and_rechecks_live_source_access(self):
		frappe.set_user(self.manager)
		linked = add_source("Lead", self.lead.name, self.phone, "ZA")["contact"]
		self.created_contacts.append(linked)
		frappe.db.set_value("WA Contact", linked, "consent_status", "Granted")
		for index, consent, suppressed, archived in (
			(1, "Granted", 1, 0),
			(2, "Granted", 0, 1),
			(3, "Withdrawn", 0, 0),
			(4, "Unknown", 0, 0),
		):
			contact = raw(
				"WA Contact",
				company=COMPANY,
				phone_e164=f"+2782{index:07d}",
				display_name=f"Audience exclusion {index}",
				consent_status=consent,
				suppressed=suppressed,
				archived=archived,
			)
			self.created_contacts.append(contact.name)
			raw(
				"WA Source Link",
				parent=contact.name,
				parenttype="WA Contact",
				parentfield="source_links",
				source_doctype="Lead",
				source_name=self.lead.name,
				selected_phone=self.phone,
				selected_by=self.manager,
				selected_at=frappe.utils.now_datetime(),
			)
		with self.assertRaises(CommandError) as invalid_filter:
			save_segment(
				f"Invalid {self.run_id}",
				{
					"version": 1,
					"logic": "and",
					"rules": [{"field": "phone_e164", "operator": "equals", "value": self.phone}],
					"groups": [],
				},
			)
		self.assertEqual(invalid_filter.exception.code, "INVALID_FILTER")
		segment = save_segment(
			f"Segment {self.run_id}",
			{
				"version": 1,
				"logic": "and",
				"rules": [
					{"field": "source_type", "operator": "equals", "value": "Lead"},
					{"field": "Lead.country", "operator": "equals", "value": "South Africa"},
				],
				"groups": [],
			},
		)
		self.created_segments.append(segment["name"])
		disabled = set_segment_disabled(segment["name"], True, segment["modified"])
		with self.assertRaises(CommandError):
			preview_segment(segment["name"], limit=1)
		set_segment_disabled(segment["name"], False, disabled["modified"])
		preview = preview_segment(segment["name"], limit=1)
		self.assertEqual(preview["matched_count"], 5)
		self.assertEqual(preview["eligible_count"], 1)
		self.assertEqual([item["name"] for item in preview["items"]], [linked])
		self.assertEqual(
			preview["excluded"], {"suppressed": 1, "archived": 1, "withdrawn": 1, "unknown_consent": 1}
		)
		limited_manager = self.user("Marketing Manager")
		frappe.set_user(limited_manager)
		denied_preview = preview_segment(segment["name"], limit=1)
		self.assertEqual(denied_preview["matched_count"], 0)
		self.assertEqual(denied_preview["eligible_count"], 0)

	def test_large_preview_is_durable_idempotent_and_exposes_only_safe_progress(self):
		self._durable_audience_test = True
		frappe.set_user(self.manager)
		segment = save_segment(
			f"Async segment {self.run_id}",
			{"version": 1, "logic": "and", "rules": [], "groups": []},
		)
		self.created_segments.append(segment["name"])
		request_id = f"audience-preview-{self.run_id}"
		with (
			patch("tag_marketing.infrastructure.audience_repository.count_candidates", return_value=2_001),
			patch("tag_marketing.application.audience_segments.frappe.enqueue") as enqueue,
		):
			first = request_preview(segment["name"], {}, 20, "", request_id)
			replay = request_preview(segment["name"], {}, 20, "", request_id)
			enqueue.assert_called_once()
		self.assertEqual(first, replay)
		self.created_operations.append(first["operation"])
		self.assertEqual(first["status"], "Pending")
		self.assertEqual(frappe.db.get_value("WA Operation", first["operation"], "status"), "Pending")
		progress = get_progress(first["operation"])
		self.assertEqual(progress["status"], "Pending")
		self.assertIsNone(progress["result"])
		frappe.db.set_value(
			"WA Operation",
			first["operation"],
			{"modified": datetime.now(UTC) - timedelta(minutes=2)},
			update_modified=False,
		)
		frappe.db.commit()
		with patch("tag_marketing.application.audience_preview_jobs.frappe.enqueue") as enqueue:
			recover_audience_preview_operations()
			enqueue.assert_called_once()
		run_audience_preview_operation(first["operation"])
		self.assertEqual(frappe.db.get_value("WA Operation", first["operation"], "status"), "Succeeded")
		self.assertEqual(frappe.db.get_value("WA Operation", first["operation"], "attempt_count"), 1)
		progress = get_progress(first["operation"])
		self.assertEqual(progress["result"]["matched_count"], 0)
		with patch("tag_marketing.infrastructure.audience_repository.count_candidates", return_value=2_002):
			with self.assertRaises(CommandError) as conflict:
				request_preview(segment["name"], {}, 20, "", request_id)
		self.assertEqual(conflict.exception.code, "IDEMPOTENCY_CONFLICT")
		with patch("tag_marketing.infrastructure.audience_repository.count_candidates", return_value=50_001):
			with self.assertRaises(CommandError) as too_large:
				request_preview(segment["name"], {}, 20, "", f"oversize-{self.run_id}")
		self.assertEqual(too_large.exception.code, "AUDIENCE_PREVIEW_TOO_LARGE")

	def test_segment_preview_scans_fifty_thousand_contacts_in_bounded_pages_and_caps_snapshots(self):
		frappe.set_user("Administrator")
		company = f"_WA Capacity {self.run_id}"
		abbr = f"C{self.run_id[:2].upper()}"
		raw(
			"Company",
			name=company,
			company_name=company,
			abbr=abbr,
			country="South Africa",
			default_currency="ZAR",
		)
		self.created_companies.append(company)
		frappe.db.set_single_value("WA Settings", "marketing_company", company)
		frappe.db.bulk_insert(
			"WA Contact",
			[
				"name",
				"owner",
				"creation",
				"modified",
				"modified_by",
				"docstatus",
				"idx",
				"company",
				"phone_e164",
				"display_name",
				"consent_status",
				"suppressed",
				"archived",
			],
			[
				(
					f"WA-CAP-{self.run_id}-{index:05d}",
					"Administrator",
					frappe.utils.now_datetime(),
					frappe.utils.now_datetime(),
					"Administrator",
					0,
					0,
					company,
					f"+2782{index:07d}",
					f"Capacity {index:05d}",
					"Granted",
					0,
					0,
				)
				for index in range(50_000)
			],
			chunk_size=1000,
		)
		frappe.set_user(self.manager)
		segment = save_segment(
			f"Capacity {self.run_id}",
			{"version": 1, "logic": "and", "rules": [], "groups": []},
		)
		self.created_segments.append(segment["name"])
		self.assertEqual(
			count_candidates(
				company,
				{"logic": "and", "rules": [], "groups": []},
				[],
				[],
			),
			50_000,
		)
		tracemalloc.start()
		try:
			preview = preview_segment(segment["name"], limit=20)
			_peak_bytes = tracemalloc.get_traced_memory()[1]
		finally:
			tracemalloc.stop()
		self.assertEqual(preview["matched_count"], 50_000)
		self.assertEqual(preview["eligible_count"], 50_000)
		self.assertEqual(len(preview["items"]), 20)
		self.assertIsNotNone(preview["next_cursor"])
		self.assertLess(_peak_bytes, 32 * 1024 * 1024)
		consumed = 0
		with self.assertRaises(CommandError):
			for _contact in iterate_snapshot_recipients(
				company,
				{"version": 1, "logic": "and", "rules": [], "groups": []},
				self.manager,
			):
				consumed += 1
		self.assertEqual(consumed, 10_000)
