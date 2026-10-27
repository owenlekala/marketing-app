"""Desk capabilities and scope; no feature aggregates or sending side effects."""

from typing import Any

import frappe
from frappe import _

from tag_marketing.infrastructure.permissions import company_allowed

APP_ROLES = frozenset(
	{"Marketing User", "Marketing Manager", "Marketing Analyst", "WhatsApp Agent", "System Manager"}
)
OVERVIEW_ROLES = APP_ROLES - {"WhatsApp Agent"}
INBOX_ROLES = frozenset({"WhatsApp Agent", "Marketing Manager"})


def can_open_app() -> bool:
	user = frappe.session.user
	if user == "Guest":
		return False
	return bool(APP_ROLES.intersection(frappe.get_roles(user))) and bool(
		frappe.db.get_value("User", user, "enabled")
		and frappe.db.get_value("User", user, "user_type") == "System User"
	)


def require_capability(roles: frozenset[str]) -> None:
	if not can_open_app() or not roles.intersection(frappe.get_roles()):
		frappe.throw(_("You do not have access to this marketing view."), frappe.PermissionError)


def overview_state() -> dict[str, Any]:
	require_capability(OVERVIEW_ROLES)
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if company and not company_allowed(company, frappe.session.user, "WA Contact"):
		frappe.throw(_("The marketing company is outside your permitted scope."), frappe.PermissionError)
	return {
		"availability": "Setup Required" if not company else "Unavailable",
		"sending_enabled": False,
		"metrics_available": False,
		"reason": _(
			"Campaign, consent and reporting services are not yet available. Sending remains disabled."
		),
		"period": "Last 30 Days",
		"metrics": {
			key: None
			for key in (
				"eligible_contacts",
				"active_campaigns",
				"delivered_messages",
				"exact_replies",
				"unassigned_conversations",
			)
		},
	}


def inbox_state() -> dict[str, Any]:
	require_capability(INBOX_ROLES)
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if company and not company_allowed(company, frappe.session.user, "WA Conversation"):
		frappe.throw(_("The marketing company is outside your permitted scope."), frappe.PermissionError)
	return {
		"availability": "Unavailable",
		"reason": _("The shared inbox is not available yet. Replies and automated sending are disabled."),
	}
