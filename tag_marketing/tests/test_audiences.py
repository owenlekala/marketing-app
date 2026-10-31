"""P3 source projections enforce current ERPNext access and phone identity rules."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import frappe

from tag_marketing.application.audiences import add_source, source_preview
from tag_marketing.domain.errors import CommandError
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
