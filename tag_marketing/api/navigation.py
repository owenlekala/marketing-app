"""Authenticated, read-only navigation and unavailable-metric interfaces."""

from typing import Any

import frappe
from frappe import _

from tag_marketing.application.navigation import (
	OVERVIEW_ROLES,
	inbox_state,
	overview_state,
	require_capability,
)


@frappe.whitelist(methods=["GET", "POST"])
def summary() -> dict[str, Any]:
	return overview_state()


@frappe.whitelist(methods=["GET", "POST"])
def inbox_readiness() -> dict[str, Any]:
	return inbox_state()


def validate_empty_filters(filters: Any) -> None:
	# No client-supplied company, SQL, doctypes or metric names are accepted.
	if filters not in (None, "", "[]", "{}", [], {}):
		frappe.throw(_("This metric does not accept filters until reporting is available."))


def unavailable_metric(filters: Any = None) -> dict[str, Any]:
	validate_empty_filters(filters)
	overview_state()
	return {"value": None, "fieldtype": "Int"}


@frappe.whitelist(methods=["GET", "POST"])
def eligible_contacts(filters: Any = None) -> dict[str, Any]:
	return unavailable_metric(filters)


@frappe.whitelist(methods=["GET", "POST"])
def active_campaigns(filters: Any = None) -> dict[str, Any]:
	return unavailable_metric(filters)


@frappe.whitelist(methods=["GET", "POST"])
def delivered_messages(filters: Any = None) -> dict[str, Any]:
	return unavailable_metric(filters)


@frappe.whitelist(methods=["GET", "POST"])
def exact_replies(filters: Any = None) -> dict[str, Any]:
	return unavailable_metric(filters)


@frappe.whitelist(methods=["GET", "POST"])
def unassigned_conversations(filters: Any = None) -> dict[str, Any]:
	return unavailable_metric(filters)


@frappe.whitelist(methods=["GET", "POST"])
def activity(chart_name: str, filters: Any = None, **kwargs: Any) -> dict[str, Any]:
	if chart_name not in ("WA Delivery Activity", "WA Campaign Activity"):
		frappe.throw(_("Unknown marketing chart."))
	validate_empty_filters(filters)
	# Deliberately uncached: the native chart-name-only cache cannot scope future data by user.
	overview_state()
	return {"labels": [], "datasets": [], "availability": "Unavailable"}


def unavailable_report() -> None:
	require_capability(OVERVIEW_ROLES)
	overview_state()
	frappe.throw(_("This report is not available yet. No campaign or delivery totals have been calculated."))
