"""HTTP boundary for permission-aware ERPNext source projection commands."""

import frappe

from tag_marketing.api.responses import boundary
from tag_marketing.application.audiences import (
	add_source as link_source,
)
from tag_marketing.application.audiences import (
	source_options,
)
from tag_marketing.application.audiences import (
	source_preview as preview,
)


@frappe.whitelist(methods=["GET"])
@boundary()
def enabled_sources():
	return {"items": source_options()}


@frappe.whitelist(methods=["GET"])
@boundary()
def source_preview(
	source_doctype: str, search: str = "", country_code: str = "", start: int = 0, page_length: int = 20
):
	try:
		start, page_length = int(start), int(page_length)
	except (TypeError, ValueError):
		frappe.throw(frappe._("Choose a valid page and page size."))
	return preview(source_doctype, search, country_code, start, page_length)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def add_source(
	source_doctype: str,
	source_name: str,
	selected_phone: str,
	country_code: str,
	include_unassigned_lead: bool = False,
):
	if isinstance(include_unassigned_lead, str):
		include_unassigned_lead = include_unassigned_lead.lower() in {"1", "true"}
	return link_source(source_doctype, source_name, selected_phone, country_code, include_unassigned_lead)
