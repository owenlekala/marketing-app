"""HTTP boundary for permission-aware ERPNext source projection commands."""

import frappe

from tag_marketing.api.responses import boundary
from tag_marketing.application.audience_segments import request_preview as request_segment_preview
from tag_marketing.application.audience_segments import save_segment, set_segment_disabled
from tag_marketing.application.audiences import add_source as link_source
from tag_marketing.application.audiences import source_options
from tag_marketing.application.audiences import source_preview as preview_source
from tag_marketing.application.imports import confirm_batch as confirm_import
from tag_marketing.application.imports import consent_history as get_consent_history
from tag_marketing.application.imports import create_batch as create_import
from tag_marketing.application.imports import inspect_file as inspect_import_file
from tag_marketing.application.imports import record_consent as record_contact_consent
from tag_marketing.application.imports import set_suppression as set_contact_suppression
from tag_marketing.application.imports import validate_batch as validate_import


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
	return preview_source(source_doctype, search, country_code, start, page_length)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def preview(segment: str, exclusions, limit: int = 20, cursor: str = "", request_id: str = ""):
	try:
		limit = int(limit)
	except (TypeError, ValueError):
		frappe.throw(frappe._("Choose a valid preview size."))
	if isinstance(exclusions, str):
		exclusions = frappe.parse_json(exclusions)
	return request_segment_preview(segment, exclusions, limit, cursor, request_id)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def save_audience_segment(segment_name: str, filters, expected_modified: str = "", segment: str = ""):
	if isinstance(filters, str):
		filters = frappe.parse_json(filters)
	return save_segment(segment_name, filters, expected_modified or None, segment or None)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def disable_audience_segment(segment: str, disabled: bool, expected_modified: str):
	if isinstance(disabled, str):
		value = disabled.lower()
		if value not in {"0", "1", "false", "true"}:
			frappe.throw(frappe._("Choose a valid audience state."))
		disabled = value in {"1", "true"}
	return set_segment_disabled(segment, disabled, expected_modified)


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


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def create_import_batch(source_file: str, mapping):
	if isinstance(mapping, str):
		mapping = frappe.parse_json(mapping)
	return create_import(source_file, mapping)


@frappe.whitelist(methods=["GET"])
@boundary()
def inspect_import_csv(source_file: str):
	return inspect_import_file(source_file)


@frappe.whitelist(methods=["GET"])
@boundary()
def consent_history(contact: str, start: int = 0, page_length: int = 20):
	try:
		start, page_length = int(start), int(page_length)
	except (TypeError, ValueError):
		frappe.throw(frappe._("Choose a valid page and page size."))
	return get_consent_history(contact, start, page_length)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def validate_import_batch(batch: str, expected_modified: str, request_id: str):
	return validate_import(batch, expected_modified, request_id)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def confirm_import_batch(batch: str, input_hash: str, expected_modified: str, request_id: str):
	return confirm_import(batch, input_hash, expected_modified, request_id)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def record_consent(
	contact: str,
	event_type: str,
	occurred_at: str,
	source: str,
	notice_version: str = "",
	evidence_reference: str = "",
	evidence_file: str | None = None,
	request_id: str = "",
):
	return record_contact_consent(
		contact,
		event_type,
		occurred_at,
		source,
		notice_version,
		evidence_reference,
		evidence_file,
		request_id,
	)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def set_suppression(contact: str, active: bool, reason: str, expected_modified: str, request_id: str):
	if isinstance(active, str):
		active = active.lower() in {"1", "true"}
	return set_contact_suppression(contact, active, reason, expected_modified, request_id)
