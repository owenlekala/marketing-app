"""Real native navigation resolution and fail-closed foundation interfaces."""

from pathlib import Path

import frappe
from frappe.boot import get_app_data
from frappe.desk.doctype.sidebar.sidebar import resolve_sidebar

from tag_marketing.api import navigation
from tag_marketing.application.navigation import can_open_app
from tag_marketing.setup.navigation import check_navigation_ownership, owned_documents
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.site import create_user


class TestNavigation(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.addCleanup(frappe.clear_cache)

	def login(self, kind):
		user = create_user(kind)
		frappe.set_user(user.name)

	def app(self):
		return next(row for row in get_app_data() if row["app_name"] == "tag_marketing")

	def test_native_app_icon_and_sidebar_for_all_marketing_roles(self):
		for kind in ("marketing", "marketing_manager", "analyst", "inbox", "manager"):
			with self.subTest(kind=kind):
				frappe.set_user("Administrator")
				self.login(kind)
				app = self.app()
				self.assertTrue(can_open_app())
				self.assertTrue(app["on_apps_screen"])
				self.assertEqual(app["app_logo_url"], "/assets/tag_marketing/images/tag-marketing.svg")
				self.assertTrue(app["dock"])
				resolved = resolve_sidebar("WhatsApp Marketing", frappe.session.user)
				self.assertIsNotNone(resolved)
				links = {row["link_to"] for row in resolved.items if row["type"] == "Link"}
				if kind == "inbox":
					self.assertEqual(links, {"wa-inbox"})
				else:
					self.assertIn("WhatsApp Marketing", links)
				if kind == "analyst":
					self.assertNotIn("WA Contact", links)
					self.assertIn("WA Campaign Performance", links)
				if kind != "manager":
					self.assertNotIn("WA Settings", links)

	def test_unrelated_user_and_guest_cannot_access_app_or_interfaces(self):
		self.login("agent")
		for user in (frappe.session.user, "Guest"):
			frappe.set_user(user)
			self.assertFalse(can_open_app())
			self.assertFalse(self.app()["on_apps_screen"])
			for method in (navigation.summary, navigation.inbox_readiness, navigation.eligible_contacts):
				with self.assertRaises(frappe.PermissionError):
					method()

	def test_owned_destinations_exist_and_sections_have_native_dropdown_shape(self):
		check_navigation_ownership()
		seen: set[tuple[str, str]] = set()
		for source in owned_documents():
			self.assertTrue(frappe.db.exists(source["doctype"], source["name"]), source["name"])
		rows = frappe.get_doc("Sidebar", "WhatsApp Marketing").items
		self.assertEqual(rows[0].label, "Overview")
		parent = None
		for row in rows:
			if row.type == "Section Break":
				parent = row.label
				self.assertTrue(row.icon)
				self.assertEqual((row.indent, row.collapsible, row.keep_closed, row.child), (1, 1, 1, 0))
			else:
				self.assertTrue(frappe.db.exists(row.link_type, row.link_to), row.link_to)
				key = (row.link_type, row.link_to)
				self.assertNotIn(key, seen)
				seen.add(key)
				if parent:
					self.assertEqual(row.child, 1)
					self.assertFalse(row.icon)
		icons = (Path(frappe.get_app_path("frappe")) / "public/icons/lucide/icons.svg").read_text()
		for row in rows:
			if row.icon:
				self.assertTrue('id="icon-' + row.icon + '"' in icons, row.icon)

	def test_unavailable_metrics_never_claim_zero_or_accept_arbitrary_filters(self):
		self.login("analyst")
		self.assertFalse(navigation.summary()["metrics_available"])
		self.assertEqual(set(navigation.summary()["metrics"].values()), {None})
		for method in (
			navigation.eligible_contacts,
			navigation.active_campaigns,
			navigation.delivered_messages,
			navigation.exact_replies,
			navigation.unassigned_conversations,
		):
			self.assertIsNone(method()["value"])
			with self.assertRaises(frappe.ValidationError):
				method(filters={"company": "unrelated"})
		for chart in ("WA Delivery Activity", "WA Campaign Activity"):
			self.assertEqual(navigation.activity(chart)["datasets"], [])
		with self.assertRaises(frappe.ValidationError):
			navigation.activity("Unrelated chart")
		with self.assertRaises(frappe.ValidationError):
			navigation.activity("WA Delivery Activity", filters={"company": "unrelated"})

	def test_site_owned_report_collision_is_rejected_without_overwriting(self):
		frappe.db.set_value("Report", "WA Campaign Performance", "is_standard", "No")
		with self.assertRaises(frappe.ValidationError):
			check_navigation_ownership()
		self.assertEqual(frappe.db.get_value("Report", "WA Campaign Performance", "is_standard"), "No")

	def test_company_restrictions_apply_to_every_metric_entry_point(self):
		from tag_marketing.tests.support.persistence import raw

		for name in ("_WA Navigation Allowed", "_WA Navigation Restricted"):
			raw(
				"Company",
				name=name,
				company_name=name,
				abbr="WAN",
				country="South Africa",
				default_currency="ZAR",
			)
		frappe.db.set_single_value("WA Settings", "marketing_company", "_WA Navigation Restricted")
		user = create_user("analyst")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": user.name,
				"allow": "Company",
				"for_value": "_WA Navigation Allowed",
				"apply_to_all_doctypes": 1,
			}
		).insert()
		frappe.set_user(user.name)
		for method in (
			navigation.summary,
			navigation.eligible_contacts,
			navigation.active_campaigns,
			navigation.delivered_messages,
			navigation.exact_replies,
			navigation.unassigned_conversations,
		):
			with self.assertRaises(frappe.PermissionError):
				method()
		with self.assertRaises(frappe.PermissionError):
			navigation.activity("WA Delivery Activity")
		frappe.set_user("Administrator")
		agent = create_user("inbox")
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": agent.name,
				"allow": "Company",
				"for_value": "_WA Navigation Allowed",
				"apply_to_all_doctypes": 1,
			}
		).insert()
		frappe.set_user(agent.name)
		with self.assertRaises(frappe.PermissionError):
			navigation.inbox_readiness()

	def test_native_customization_layers_survive_repeated_base_sync(self):
		from frappe.modules.import_file import import_file_by_path

		from tag_marketing.setup.navigation import APP_ROOT
		from tag_marketing.tests.support.navigation import create_customizations

		customizations = create_customizations()
		before = [frappe.get_doc(doc.doctype, doc.name).as_dict() for doc in customizations]
		for _ in range(2):
			check_navigation_ownership()
			for folder in ("dock", "whatsapp_marketing/sidebar", "whatsapp_marketing/workspace"):
				for path in (APP_ROOT / folder).glob("*/*.json"):
					import_file_by_path(str(path), force=True)
		for original in before:
			self.assertEqual(frappe.get_doc(original.doctype, original.name).as_dict(), original)
		frappe.clear_cache()
		self.assertEqual(
			resolve_sidebar("WhatsApp Marketing", "Administrator").label, "Synthetic Personal Sidebar"
		)

	def test_optional_legacy_icon_is_owned_idempotent_and_has_a_real_route(self):
		from tag_marketing.setup.navigation import sync_desktop_icon

		frappe.db.set_single_value("Desktop Settings", "desktop_page", "Desktop Icons")
		before = frappe.db.count("Desktop Icon", {"app": ["!=", "tag_marketing"]})
		sync_desktop_icon()
		sync_desktop_icon()
		icons = frappe.get_all(
			"Desktop Icon", filters={"app": "tag_marketing", "icon_type": "App"}, fields=["name", "link"]
		)
		self.assertEqual(len(icons), 1)
		self.assertEqual(icons[0].link, "/desk/whatsapp-marketing")
		self.assertEqual(frappe.db.count("Desktop Icon", {"app": ["!=", "tag_marketing"]}), before)
