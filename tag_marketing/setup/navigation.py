"""Preflight for owned navigation identities; native imports own the base records."""

import json
from pathlib import Path

import frappe

APP_ROOT = Path(__file__).resolve().parents[1]
MODULE = "WhatsApp Marketing"


def owned_documents():
	for folder in (
		"dock",
		"whatsapp_marketing/sidebar",
		"whatsapp_marketing/workspace",
		"whatsapp_marketing/page",
		"whatsapp_marketing/report",
		"whatsapp_marketing/number_card",
		"whatsapp_marketing/dashboard_chart",
		"whatsapp_marketing/dashboard_chart_source",
	):
		for path in sorted((APP_ROOT / folder).glob("*/*.json")):
			yield json.loads(path.read_text())


def check_navigation_ownership():
	for source in owned_documents():
		kind, name = source["doctype"], source["name"]
		if not frappe.db.exists(kind, name):
			continue
		row = frappe.get_doc(kind, name)
		owner_field = "app" if kind == "Dock" else "module"
		expected = "tag_marketing" if kind == "Dock" else MODULE
		standard_field = "is_standard" if kind in ("Number Card", "Dashboard Chart", "Report") else "standard"
		if row.get(owner_field) != expected or (
			kind != "Dashboard Chart Source" and row.get(standard_field) not in (1, "1", "Yes")
		):
			frappe.throw(
				frappe._(
					"Navigation identity {0} is already used by a site-owned or unrelated record. Resolve the collision before installing marketing navigation."
				).format(name)
			)


def sync_desktop_icon():
	from frappe.desk.doctype.desktop_settings.desktop_settings import is_desktop_icons_page

	if not is_desktop_icons_page():
		return
	# Only this app's compatibility row. Never regenerate or rearrange another app's icons.
	if frappe.db.exists("Desktop Icon", {"app": "tag_marketing", "icon_type": "App"}):
		return
	if frappe.db.exists("Desktop Icon", "TAG Marketing"):
		frappe.throw(frappe._("The TAG Marketing desktop icon name is already in use."))
	from tag_marketing.application.navigation import APP_ROLES

	frappe.get_doc(
		{
			"doctype": "Desktop Icon",
			"label": "TAG Marketing",
			"icon_type": "App",
			"app": "tag_marketing",
			"link_type": "External",
			"link": "/desk/whatsapp-marketing",
			"logo_url": "/assets/tag_marketing/images/tag-marketing.svg",
			"roles": [{"role": role} for role in sorted(APP_ROLES)],
		}
	).insert(ignore_permissions=True)
