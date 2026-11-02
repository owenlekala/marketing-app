"""Authenticated template draft and validation endpoints."""

import json

import frappe

from tag_marketing.api.responses import boundary
from tag_marketing.application.templates import (
	available_connections,
	save_draft,
)
from tag_marketing.application.templates import (
	preview as preview_template,
)
from tag_marketing.application.templates import (
	submit as submit_template,
)
from tag_marketing.application.templates import (
	sync as sync_template,
)
from tag_marketing.application.templates import (
	validate as validate_template,
)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def save(
	connection: str,
	template_name: str,
	language_code: str,
	category: str,
	components: str,
	request_id: str,
	media_file: str | None = None,
	template: str | None = None,
	expected_modified: str | None = None,
):
	# Stable command key is part of the public contract; local save is deterministic and
	# returns the current target on exact retries without persisting empty operations.
	if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
		frappe.throw(frappe._("Enter a valid request identifier."))
	try:
		component_value = json.loads(components)
	except (TypeError, ValueError):
		frappe.throw(frappe._("Enter valid template components."))
	return save_draft(
		connection,
		template_name,
		language_code,
		category,
		component_value,
		media_file,
		request_id=request_id,
		template=template,
		expected_modified=expected_modified,
	)


@frappe.whitelist(methods=["GET"])
@boundary()
def connections():
	return {"items": available_connections()}


@frappe.whitelist(methods=["POST"])
@boundary()
def validate(template: str, expected_modified: str):
	return validate_template(template, expected_modified)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def submit(template: str, content_hash: str, expected_modified: str, request_id: str):
	return submit_template(template, content_hash, expected_modified, request_id)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def sync(template: str, request_id: str):
	return sync_template(template, request_id)


@frappe.whitelist(methods=["POST"])
@boundary()
def preview(components: str, sample_values: str = "[]"):
	try:
		parsed_components = json.loads(components)
		samples = json.loads(sample_values)
	except (TypeError, ValueError):
		frappe.throw(frappe._("Enter valid template preview data."))
	return preview_template(parsed_components, samples)
