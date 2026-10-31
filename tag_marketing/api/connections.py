"""Native connection page queries and asynchronous setup commands."""

import frappe

from tag_marketing.api.responses import boundary
from tag_marketing.application.connections import (
	connection_health,
	connection_webhook_diagnostics,
	enqueue_connection_operation,
	send_test,
)
from tag_marketing.application.connections import (
	set_enabled as set_connection_enabled,
)


@frappe.whitelist(methods=["GET"])
@boundary()
def health():
	return {"items": connection_health()}


@frappe.whitelist(methods=["GET"])
@boundary()
def check_webhook(connection: str):
	return connection_webhook_diagnostics(connection)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def validate_connection(connection: str, expected_modified: str, request_id: str):
	return enqueue_connection_operation(
		"validate_connection", connection, request_id, expected_modified=expected_modified
	)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def sync_numbers(connection: str, request_id: str):
	return enqueue_connection_operation("sync_numbers", connection, request_id)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def sync_templates(connection: str, request_id: str):
	return enqueue_connection_operation("sync_templates", connection, request_id)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def set_enabled(connection: str, enabled, expected_modified: str, request_id: str):
	if isinstance(enabled, bool):
		normalized = enabled
	elif isinstance(enabled, int) and enabled in (0, 1):
		normalized = bool(enabled)
	elif enabled in ("0", "1", "true", "false"):
		normalized = enabled in ("1", "true")
	else:
		frappe.throw(frappe._("Choose whether the connection should be enabled."))
	return set_connection_enabled(
		connection,
		normalized,
		expected_modified,
		request_id,
	)


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def test_send(
	connection: str,
	sending_number: str,
	contact: str,
	template: str,
	sample_values: str,
	request_id: str,
):
	import json

	try:
		values = json.loads(sample_values)
	except (TypeError, ValueError):
		frappe.throw(frappe._("Enter valid sample values."))
	return send_test(
		connection=connection,
		sending_number=sending_number,
		contact=contact,
		template=template,
		sample_values=values,
		request_id=request_id,
	)
