"""Real schema, API bypass and scope checks; fixtures bypass services only via trusted test persistence."""

import json
import re
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Barrier

import frappe
from frappe.client import insert, set_value
from frappe.utils.password import get_decrypted_password

from tag_marketing.application.foundation import validate_company_links
from tag_marketing.infrastructure.schema import (
	DOCTYPE_ROOT,
	INDEXES,
	PARENT_TYPES,
	UNIQUE_KEYS,
	constraint_name,
)
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw

COMPANY = "_WA Foundation Company"
OTHER = "_WA Other Company"


class TestFoundation(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		# Minimal Company rows avoid unrelated ERP business side effects in schema tests.
		for company in (COMPANY, OTHER):
			if not frappe.db.exists("Company", company):
				frappe.get_doc(
					{
						"doctype": "Company",
						"name": company,
						"company_name": company,
						"abbr": "WAF",
						"country": "South Africa",
						"default_currency": "ZAR",
					}
				).db_insert()
		frappe.db.set_single_value("WA Settings", "marketing_company", COMPANY)
		self.addCleanup(frappe.clear_cache)

	def user(self, role, suffix):
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": f"wa-foundation-{suffix}@example.invalid",
				"first_name": "WA Foundation",
				"send_welcome_email": 0,
				"roles": [{"role": role}],
			}
		).insert()
		return user.name

	def test_metadata_matches_every_documented_field(self):
		text = (Path(__file__).resolve().parents[2] / "docs/whatsapp_marketing/DATA_MODEL.md").read_text()
		parts = re.split(r"^### (WA .+)\n", text, flags=re.M)
		self.assertEqual(len(PARENT_TYPES), 31)
		self.assertEqual(len(list(DOCTYPE_ROOT.glob("*/*.json"))), 36)
		for i in range(1, len(parts), 2):
			name, body = parts[i : i + 2]
			meta = frappe.get_meta(name)
			self.assertEqual(meta.module, "WhatsApp Marketing")
			self.assertFalse(meta.allow_rename or meta.allow_import or meta.is_submittable)
			for field, kind in re.findall(r"^- `([^`]+)` — \*\*([^*]+)\*\*", body, re.M):
				type_, _, options = kind.partition(" → ")
				actual = meta.get_field(field)
				self.assertIsNotNone(actual, (name, field))
				self.assertEqual(actual.fieldtype, type_, (name, field))
				if options:
					self.assertEqual(actual.options, options)

	def test_all_declared_indexes_exist_with_exact_columns(self):
		for manifest, unique in ((UNIQUE_KEYS, True), (INDEXES, False)):
			for kind, keys in manifest.items():
				indexes = frappe.db.sql(f"SHOW INDEX FROM `tab{kind}`", as_dict=True)
				for fields in keys:
					name = constraint_name("uq" if unique else "ix", fields)
					rows = sorted(
						(row for row in indexes if row.Key_name == name), key=lambda row: row.Seq_in_index
					)
					self.assertEqual(tuple(row.Column_name for row in rows), fields, (kind, fields))
					self.assertEqual({row.Non_unique for row in rows}, {0 if unique else 1})

	def test_database_unique_keys_reject_duplicates_without_controller_help(self):
		for kind, keys in UNIQUE_KEYS.items():
			for fields in keys:
				with self.subTest(kind=kind, fields=fields):
					frappe.db.savepoint("wa_constraint")
					values = {
						field: (
							1
							if frappe.get_meta(kind).get_field(field)
							and frappe.get_meta(kind).get_field(field).fieldtype == "Int"
							else "wa-key"
						)
						for field in fields
					}
					raw(kind, **values)
					with self.assertRaises(frappe.UniqueValidationError):
						raw(kind, **values)
					frappe.db.rollback(save_point="wa_constraint")

	def test_provider_ids_are_nullable_unique_at_database_boundary(self):
		for kind, field in (("WA Template", "provider_template_id"), ("WA Message", "provider_message_id")):
			for index in range(2):
				values = {"company": COMPANY, field: None}
				if kind == "WA Template":
					values.update(
						connection="wa-connection", template_name=f"template-{index}", language_code="en"
					)
				else:
					values["logical_key"] = f"logical-{index}"
				raw(kind, **values)
			values[field] = "provider-unique"
			if kind == "WA Template":
				values["template_name"] = "unique-one"
			else:
				values["logical_key"] = "unique-one"
			raw(kind, **values)
			if kind == "WA Template":
				values["template_name"] = "unique-two"
			else:
				values["logical_key"] = "unique-two"
			with self.assertRaises(frappe.UniqueValidationError):
				raw(kind, **values)

	def test_company_and_link_company_are_enforced(self):
		contact = raw("WA Contact", company=OTHER, phone_e164="+27820000001")
		with self.assertRaises(frappe.ValidationError):
			validate_company_links(
				frappe.get_doc({"doctype": "WA Consent Event", "company": COMPANY, "contact": contact.name})
			)
		with self.assertRaises(frappe.ValidationError):
			validate_company_links(frappe.get_doc({"doctype": "WA Tag", "company": OTHER}))

	def test_generic_insert_and_set_value_cannot_bypass_managed_records(self):
		with self.assertRaises(frappe.PermissionError):
			insert({"doctype": "WA Tag", "company": OTHER, "label": "Outside Company"})
		contact = raw(
			"WA Contact",
			company=COMPANY,
			phone_e164="+27820000002",
			display_name="Synthetic",
			consent_status="Unknown",
		)
		with self.assertRaises(frappe.PermissionError):
			set_value("WA Contact", contact.name, "consent_status", "Granted")
		self.assertEqual(frappe.db.get_value("WA Contact", contact.name, "consent_status"), "Unknown")
		with self.assertRaises(frappe.PermissionError):
			frappe.get_doc("WA Contact", contact.name).delete(ignore_permissions=True)

	def test_settings_save_audits_without_exposing_key_and_denies_forgery(self):
		doc = frappe.get_doc("WA Settings")
		doc.marketing_cap = 2
		doc.save()
		event = frappe.get_last_doc("WA Audit Event")
		self.assertIn("marketing_cap", json.loads(event.details_json)["changed_fields"])
		key_digest = sha256(
			get_decrypted_password("WA Settings", "WA Settings", "suppression_hmac_key").encode()
		).hexdigest()
		self.assertEqual(len(key_digest), 64)
		self.assertFalse(
			get_decrypted_password("WA Settings", "WA Settings", "suppression_hmac_key") in event.as_json()
		)
		for field, value, error in (
			("sending_enabled", 1, frappe.ValidationError),
			("pilot_verified_by", "Administrator", frappe.PermissionError),
			("suppression_hmac_key", "forged", frappe.PermissionError),
			("suppression_hmac_key", "", frappe.PermissionError),
			("max_campaign_recipients", 10001, frappe.ValidationError),
		):
			with self.subTest(field=field):
				candidate = frappe.get_doc("WA Settings")
				candidate.set(field, value)
				with self.assertRaises(error):
					candidate.save()

	def test_settings_company_cannot_orphan_records(self):
		raw("WA Tag", company=COMPANY, label="Existing")
		doc = frappe.get_doc("WA Settings")
		doc.marketing_company = OTHER
		with self.assertRaises(frappe.ValidationError):
			doc.save()

	def test_company_read_permissions_match_lists_and_direct_ids(self):
		user = self.user("Marketing User", "marketer")
		own = raw("WA Tag", company=COMPANY, label="Own")
		other = raw("WA Tag", company=OTHER, label="Other")
		frappe.set_user(user)
		self.assertEqual(frappe.get_list("WA Tag", pluck="name"), [own.name])
		self.assertTrue(frappe.has_permission("WA Tag", doc=own))
		self.assertFalse(frappe.has_permission("WA Tag", doc=other))
		self.assertFalse(frappe.has_permission("WA Connection"))
		self.assertFalse(frappe.has_permission("WA Settings", "write"))

	def test_agent_scope_covers_assignment_team_messages_and_cursors(self):
		agent = self.user("WhatsApp Agent", "agent")
		other = self.user("WhatsApp Agent", "other")
		team = frappe.get_doc(
			{"doctype": "User Group", "name": "WA Foundation Team", "user_group_members": [{"user": agent}]}
		).insert()
		own = raw(
			"WA Conversation", company=COMPANY, contact="one", sending_number="number", assigned_to=agent
		)
		shared = raw(
			"WA Conversation", company=COMPANY, contact="two", sending_number="number", team=team.name
		)
		denied = raw(
			"WA Conversation", company=COMPANY, contact="three", sending_number="number", assigned_to=other
		)
		message = raw("WA Message", company=COMPANY, conversation=own.name, logical_key="scope-message")
		for conv in (own, shared, denied):
			raw("WA Conversation Read", company=COMPANY, conversation=conv.name, user=agent)
		raw("WA Conversation Read", company=COMPANY, conversation=own.name, user=other)
		frappe.set_user(agent)
		self.assertEqual(set(frappe.get_list("WA Conversation", pluck="name")), {own.name, shared.name})
		self.assertFalse(frappe.has_permission("WA Conversation", doc=denied))
		self.assertTrue(frappe.has_permission("WA Message", doc=message))
		self.assertEqual(len(frappe.get_list("WA Conversation Read")), 2)
		self.assertFalse(frappe.has_permission("WA Contact"))

	def test_analyst_and_system_manager_do_not_inherit_content_access(self):
		for role, suffix in (("Marketing Analyst", "analyst"), ("System Manager", "admin")):
			user = self.user(role, suffix)
			frappe.set_user(user)
			for kind in ("WA Message", "WA Contact", "WA Consent Event", "WA Conversation"):
				self.assertFalse(frappe.has_permission(kind), (role, kind))
			frappe.set_user("Administrator")

	def test_setup_preserves_existing_settings_roles_and_key(self):
		from tag_marketing.setup.install import sync_foundation

		key_digest = sha256(
			get_decrypted_password("WA Settings", "WA Settings", "suppression_hmac_key").encode()
		).hexdigest()
		frappe.db.set_single_value("WA Settings", "marketing_cap", 3)
		frappe.db.set_value("Role", "Marketing Analyst", "desk_access", 0)
		# DDL helpers find existing indexes, so this test has no implicit schema commits.
		sync_foundation()
		sync_foundation()
		self.assertEqual(frappe.db.get_single_value("WA Settings", "marketing_cap"), 3)
		self.assertEqual(frappe.db.get_value("Role", "Marketing Analyst", "desk_access"), 0)
		self.assertEqual(
			sha256(
				get_decrypted_password("WA Settings", "WA Settings", "suppression_hmac_key").encode()
			).hexdigest(),
			key_digest,
		)

	def test_document_shares_cannot_override_scope(self):
		from frappe.share import add

		user = self.user("Marketing User", "share")
		tag = raw("WA Tag", company=OTHER, label="Unshareable")
		with self.assertRaises(frappe.PermissionError):
			add("WA Tag", tag.name, user=user, read=1)
		self.assertFalse(frappe.db.exists("DocShare", {"share_doctype": "WA Tag", "share_name": tag.name}))

	def test_unique_identity_race_has_one_committed_winner(self):
		site, sites_path = frappe.local.site, frappe.local.sites_path
		label = "wa-race-" + frappe.generate_hash(length=16)
		barrier = Barrier(2)

		def compete():
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
			try:
				barrier.wait(timeout=10)
				try:
					raw("WA Tag", company=COMPANY, label=label)
					frappe.db.commit()
					return "inserted"
				except frappe.UniqueValidationError:
					frappe.db.rollback()
					return "duplicate"
			finally:
				frappe.destroy()

		def cleanup():
			frappe.init(site=site, sites_path=sites_path)
			frappe.connect()
			try:
				frappe.db.delete("WA Tag", {"label": label})
				frappe.db.commit()
			finally:
				frappe.destroy()

		with ThreadPoolExecutor(max_workers=2) as pool:
			try:
				results = list(pool.map(lambda _: compete(), range(2)))
				self.assertEqual(sorted(results), ["duplicate", "inserted"])
			finally:
				pool.submit(cleanup).result(timeout=15)

	def test_native_company_user_restrictions_apply_to_lists_and_ids(self):
		user = self.user("Marketing User", "restricted")
		contact = raw("WA Tag", company=COMPANY, label="Restricted")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user,
				"allow": "Company",
				"for_value": OTHER,
				"apply_to_all_doctypes": 1,
			}
		).insert()
		frappe.clear_cache(user=user)
		frappe.set_user(user)
		self.assertFalse(frappe.has_permission("WA Tag", doc=contact))
		self.assertEqual(frappe.get_list("WA Tag", pluck="name"), [])

	def test_native_ignore_validate_flag_does_not_disable_critical_guards(self):
		doc = frappe.get_doc({"doctype": "WA Tag", "company": OTHER, "label": "No bypass"})
		doc.flags.ignore_validate = True
		with self.assertRaises(frappe.PermissionError):
			doc.insert(ignore_permissions=True)
		settings = frappe.get_doc("WA Settings")
		settings.flags.ignore_validate = True
		settings.sending_enabled = 1
		with self.assertRaises(frappe.ValidationError):
			settings.save()

	def test_generic_bulk_update_does_not_grant_consent(self):
		from frappe.client import bulk_update

		contact = raw(
			"WA Contact",
			company=COMPANY,
			phone_e164="+27820000003",
			display_name="Bulk Synthetic",
			consent_status="Unknown",
		)
		result = bulk_update(
			json.dumps([{"doctype": "WA Contact", "docname": contact.name, "consent_status": "Granted"}])
		)
		self.assertEqual(len(result["failed_docs"]), 1)
		self.assertEqual(frappe.db.get_value("WA Contact", contact.name, "consent_status"), "Unknown")

	def test_scalar_unique_metadata_has_real_database_enforcement(self):
		for kind in PARENT_TYPES:
			for field in frappe.get_meta(kind).fields:
				if not field.unique:
					continue
				with self.subTest(kind=kind, field=field.fieldname):
					frappe.db.savepoint("wa_scalar_unique")
					raw(kind, **{field.fieldname: "wa-scalar-key"})
					with self.assertRaises(frappe.UniqueValidationError):
						raw(kind, **{field.fieldname: "wa-scalar-key"})
					frappe.db.rollback(save_point="wa_scalar_unique")

	def test_missing_existing_secret_is_not_silently_replaced(self):
		from tag_marketing.setup.install import seed_settings

		frappe.db.sql(
			"DELETE FROM `__Auth` WHERE doctype=%s AND name=%s AND fieldname=%s",
			("WA Settings", "WA Settings", "suppression_hmac_key"),
		)
		with self.assertRaises(RuntimeError):
			seed_settings()
		self.assertFalse(
			frappe.db.sql(
				"SELECT 1 FROM `__Auth` WHERE doctype=%s AND name=%s AND fieldname=%s",
				("WA Settings", "WA Settings", "suppression_hmac_key"),
			)
		)

	def test_system_manager_can_save_settings_after_fieldlevel_projection(self):
		from frappe.client import save

		user = self.user("System Manager", "settings-editor")
		frappe.set_user(user)
		doc = frappe.get_doc("WA Settings")
		doc.apply_fieldlevel_read_permissions()
		doc.marketing_cap = 2
		save(doc.as_json())
		self.assertEqual(frappe.db.get_single_value("WA Settings", "marketing_cap"), 2)
		self.assertTrue(get_decrypted_password("WA Settings", "WA Settings", "suppression_hmac_key"))
