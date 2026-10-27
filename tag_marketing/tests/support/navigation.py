"""Native navigation customisation fixtures shared by migration qualification."""

import frappe


def create_customizations():
	customizations = []
	for user, label in (("", "Site"), ("Administrator", "Personal")):
		customizations.append(
			frappe.get_doc(
				{
					"doctype": "Custom Sidebar",
					"module": "WhatsApp Marketing",
					"user": user,
					"label": "Synthetic " + label + " Sidebar",
					"sidebar_items": [],
				}
			).insert()
		)
		customizations.append(
			frappe.get_doc(
				{
					"doctype": "Dock",
					"app": "tag_marketing",
					"standard": 0,
					"user": user,
					"items": [
						{
							"link_type": "Sidebar",
							"link_to": "WhatsApp Marketing",
							"title": "Synthetic " + label + " Dock",
							"icon": "users",
						}
					],
				}
			).insert()
		)
	customizations.append(
		frappe.get_doc(
			{
				"doctype": "Custom Workspace",
				"workspace": "WhatsApp Marketing",
				"icon": "users",
				"visibility": "Inherit",
			}
		).insert()
	)
	return customizations
