"""Company-scoped connection commands and safe health projections."""

import hashlib
import json
import re
from typing import Any

import frappe
from frappe import _

from tag_marketing.application.navigation import can_open_app
from tag_marketing.application.operation_store import insert_idempotent_operation
from tag_marketing.application.outbox import enqueue_message
from tag_marketing.domain.errors import CommandError, require_revision
from tag_marketing.domain.templates import content_hash as template_content_hash
from tag_marketing.infrastructure.permissions import company_allowed

REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
CONNECTION_OPERATIONS = {
	"validate_connection": "connections.validate_connection",
	"sync_numbers": "connections.sync_numbers",
	"sync_templates": "connections.sync_templates",
}
SET_ENABLED_OPERATION = "connections.set_enabled"


def _roles() -> set[str]:
	return set(frappe.get_roles())


def _company() -> str:
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or not company_allowed(company, frappe.session.user, "WA Connection"):
		raise CommandError("NOT_FOUND")
	return company


def _authorize(operation: str) -> None:
	if not can_open_app():
		frappe.throw(_("You do not have access to this marketing view."), frappe.PermissionError)
	roles = _roles()
	if operation == "sync_templates" and roles.intersection({"Marketing Manager", "System Manager"}):
		return
	if "System Manager" not in roles and frappe.session.user != "Administrator":
		frappe.throw(_("Only System Managers can manage this connection."), frappe.PermissionError)


def connection_health() -> list[dict[str, Any]]:
	"""Safe company health projection. It never serializes credentials or internal diagnostics."""
	if not can_open_app() or not _roles().intersection({"Marketing Manager", "System Manager"}):
		frappe.throw(_("You do not have access to connection health."), frappe.PermissionError)
	company = _company()
	rows = frappe.db.get_all(
		"WA Connection",
		filters={"company": company},
		fields=[
			"name",
			"connection_name",
			"status",
			"last_validated_at",
			"last_webhook_at",
			"last_webhook_verified_at",
			"last_error_code",
		],
		order_by="connection_name asc",
	)
	for row in rows:
		row["number_count"] = frappe.db.count(
			"WA Sending Number", {"company": company, "connection": row["name"]}
		)
		row["template_count"] = frappe.db.count(
			"WA Template", {"company": company, "connection": row["name"]}
		)
		statuses = (
			("Ready", "webhook_pending_count"),
			("Processing", "webhook_processing_count"),
			("Failed", "webhook_failed_count"),
		)
		for status, key in statuses:
			row[key] = frappe.db.count(
				"WA Webhook Event", {"company": company, "connection": row["name"], "status": status}
			)
	return rows


def connection_webhook_diagnostics(connection_name: str) -> dict[str, Any]:
	"""Return System Manager diagnostics without exposing payloads, IDs or credentials."""
	_authorize("check_webhook")
	company = _company()
	if not isinstance(connection_name, str) or not 1 <= len(connection_name) <= 140:
		raise CommandError("INVALID_INPUT", "connection")
	connection = frappe.db.get_value(
		"WA Connection",
		{"name": connection_name, "company": company},
		["status", "last_webhook_verified_at", "last_webhook_at", "last_error_code"],
		as_dict=True,
	)
	if not connection:
		raise CommandError("NOT_FOUND")
	counts = {
		status.lower(): frappe.db.count(
			"WA Webhook Event", {"company": company, "connection": connection_name, "status": status}
		)
		for status in ("Ready", "Processing", "Processed", "Failed")
	}
	return {
		"last_verified_at": connection.last_webhook_verified_at,
		"last_signed_post_at": connection.last_webhook_at,
		"subscription_diagnostic": "Verified" if connection.last_webhook_verified_at else "Not Verified",
		"readiness": "Ready" if connection.last_webhook_verified_at else "Action Required",
		"last_error_code": connection.last_error_code,
		"events": counts,
	}


def enqueue_connection_operation(
	operation: str,
	connection_name: str,
	request_id: str,
	*,
	expected_modified: str | None = None,
) -> dict[str, str]:
	if operation not in CONNECTION_OPERATIONS:
		raise CommandError("INVALID_INPUT", "operation")
	_authorize(operation)
	if not isinstance(connection_name, str) or not 1 <= len(connection_name) <= 140:
		raise CommandError("INVALID_INPUT", "connection")
	if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
		raise CommandError("INVALID_INPUT", "request_id")
	args: dict[str, Any] = {"connection": connection_name}
	if operation == "validate_connection":
		args["expected_modified"] = expected_modified
	request_hash = hashlib.sha256(
		json.dumps({"operation": operation, **args}, sort_keys=True, separators=(",", ":")).encode()
	).hexdigest()
	operation_type = CONNECTION_OPERATIONS[operation]
	company = _company()
	if not frappe.db.exists("WA Connection", {"name": connection_name, "company": company}):
		raise CommandError("NOT_FOUND")
	prior = frappe.db.get_value(
		"WA Operation",
		{"requested_by": frappe.session.user, "operation_type": operation_type, "request_id": request_id},
		["name", "request_hash"],
		as_dict=True,
	)
	if prior:
		if prior.request_hash != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return {"operation": prior.name}
	connection = frappe.get_doc("WA Connection", connection_name)
	if operation == "validate_connection":
		require_revision(str(connection.modified), expected_modified)
	if operation == "validate_connection" and connection.status == "Disabled":
		raise CommandError("INVALID_STATE")
	if operation == "sync_numbers" and connection.status not in {"Ready", "Degraded"}:
		raise CommandError("READINESS_FAILED")
	if operation == "sync_templates" and connection.status not in {"Ready", "Degraded"}:
		raise CommandError("READINESS_FAILED")
	doc = frappe.get_doc(
		{
			"doctype": "WA Operation",
			"company": company,
			"operation_type": operation_type,
			"requested_by": frappe.session.user,
			"request_id": request_id,
			"request_hash": request_hash,
			"request_json": args,
			"attempt_count": 0,
			"status": "Pending",
			"progress_percent": 0,
			"target_doctype": "WA Connection",
			"target_name": connection_name,
			"result_json": None,
			"result_file": None,
			"error_code": None,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	operation_name, created = insert_idempotent_operation(doc)
	if not created:
		return {"operation": operation_name}
	frappe.enqueue(
		"tag_marketing.application.connection_jobs.run_connection_operation",
		queue="marketing",
		enqueue_after_commit=True,
		job_id=f"wa:{operation_name}",
		deduplicate=True,
		operation_id=operation_name,
		operation=operation,
		connection_name=connection_name,
		kwargs=args,
	)
	return {"operation": doc.name}


def send_test(
	*,
	connection: str,
	sending_number: str,
	contact: str,
	template: str,
	sample_values: list[Any],
	request_id: str,
) -> dict[str, str]:
	"""Queue an explicitly authorised test through the shared durable sender."""
	_authorize("validate_connection")
	company = _company()
	if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
		raise CommandError("INVALID_INPUT", "request_id")
	if not all(isinstance(value, str) and value for value in (connection, sending_number, contact, template)):
		raise CommandError("INVALID_INPUT")
	if (
		not isinstance(sample_values, list)
		or len(sample_values) > 100
		or any(not isinstance(value, (str, int, float)) or len(str(value)) > 1024 for value in sample_values)
	):
		raise CommandError("INVALID_INPUT", "sample_values")
	connection_state = frappe.db.get_value(
		"WA Connection", {"name": connection, "company": company}, "status"
	)
	if not connection_state:
		raise CommandError("NOT_FOUND")
	if connection_state != "Ready":
		raise CommandError("READINESS_FAILED")
	number = frappe.db.get_value(
		"WA Sending Number",
		{"name": sending_number, "company": company, "connection": connection},
		["status", "rate_per_second"],
		as_dict=True,
	)
	if not number:
		raise CommandError("NOT_FOUND")
	if number.status != "Ready" or not number.rate_per_second or number.rate_per_second <= 0:
		raise CommandError("READINESS_FAILED")
	contact_state = frappe.db.get_value(
		"WA Contact",
		{"name": contact, "company": company},
		["consent_status", "suppressed", "archived", "phone_e164"],
		as_dict=True,
	)
	if not contact_state:
		raise CommandError("NOT_FOUND")
	if contact_state.consent_status != "Granted" or contact_state.suppressed or contact_state.archived:
		raise CommandError("READINESS_FAILED")
	template_doc = frappe.db.get_value(
		"WA Template",
		{"name": template, "company": company, "connection": connection},
		["status", "category", "components_json", "content_hash"],
		as_dict=True,
	)
	if not template_doc:
		raise CommandError("NOT_FOUND")
	if (
		template_doc.status != "Approved"
		or template_doc.category == "Authentication"
		or not frappe.db.get_value("WA Template", template, "provider_template_id")
		or not template_doc.content_hash
	):
		raise CommandError("READINESS_FAILED")
	try:
		components = (
			json.loads(template_doc.components_json)
			if isinstance(template_doc.components_json, str)
			else template_doc.components_json
		)
		actual_hash = template_content_hash(
			frappe.db.get_value("WA Template", template, "template_name"),
			frappe.db.get_value("WA Template", template, "language_code"),
			template_doc.category,
			components,
			frappe.db.get_value("WA Template", template, "media_sha256"),
		)
		variables = _template_variable_indexes(components)
	except (TypeError, ValueError):
		raise CommandError("READINESS_FAILED") from None
	if actual_hash != template_doc.content_hash:
		raise CommandError("READINESS_FAILED")
	if variables != list(range(1, len(variables) + 1)) or len(sample_values) != len(variables):
		raise CommandError("INVALID_INPUT", "sample_values")
	parameters = [{"type": "text", "text": str(value)} for value in sample_values]
	payload = {"components": ([{"type": "body", "parameters": parameters}] if parameters else [])}
	logical_key = "test:" + hashlib.sha256(f"{frappe.session.user}:{request_id}".encode()).hexdigest()
	prior = frappe.db.get_value(
		"WA Message",
		{"logical_key": logical_key},
		[
			"name",
			"company",
			"contact",
			"sending_number",
			"template",
			"template_payload_json",
			"status",
		],
		as_dict=True,
	)
	if prior:
		stored = prior.template_payload_json
		if isinstance(stored, str):
			stored = json.loads(stored)
		if (prior.company, prior.contact, prior.sending_number, prior.template, stored) != (
			company,
			contact,
			sending_number,
			template,
			payload,
		):
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return {"message": prior.name, "status": prior.status}
	queued = enqueue_message(
		company=company,
		contact=contact,
		phone_e164=contact_state.phone_e164,
		sending_number=sending_number,
		purpose="Test",
		template=template,
		template_payload=payload,
		logical_key=logical_key,
		initiated_by=frappe.session.user,
	)
	return {
		"message": queued["message"],
		"status": frappe.db.get_value("WA Message", queued["message"], "status"),
	}


def _template_variable_indexes(components: Any) -> list[int]:
	indexes: set[int] = set()
	stack = [components]
	while stack:
		value = stack.pop()
		if isinstance(value, dict):
			stack.extend(value.values())
		elif isinstance(value, list):
			stack.extend(value)
		elif isinstance(value, str):
			indexes.update(int(match) for match in re.findall(r"\{\{(\d{1,3})\}\}", value))
	return sorted(indexes)


def set_enabled(
	connection_name: str, enabled: bool, expected_modified: str, request_id: str
) -> dict[str, str]:
	"""Disable immediately or re-enable only by queueing fresh provider validation."""
	_authorize("validate_connection")
	if (
		not isinstance(enabled, bool)
		or not isinstance(request_id, str)
		or not REQUEST_ID.fullmatch(request_id)
	):
		raise CommandError("INVALID_INPUT")
	company = _company()
	if not isinstance(connection_name, str) or not frappe.db.exists(
		"WA Connection", {"name": connection_name, "company": company}
	):
		raise CommandError("NOT_FOUND")
	operation_type = SET_ENABLED_OPERATION
	args = {"connection": connection_name, "enabled": enabled}
	request_hash = hashlib.sha256(
		json.dumps({"operation": "set_enabled", **args}, sort_keys=True, separators=(",", ":")).encode()
	).hexdigest()
	prior = frappe.db.get_value(
		"WA Operation",
		{"requested_by": frappe.session.user, "operation_type": operation_type, "request_id": request_id},
		["name", "request_hash"],
		as_dict=True,
	)
	if prior:
		if prior.request_hash != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return {"operation": prior.name}
	connection = frappe.get_doc("WA Connection", connection_name)
	require_revision(str(connection.modified), expected_modified)
	if enabled and connection.status != "Disabled":
		raise CommandError("INVALID_STATE")
	if not enabled and connection.status == "Disabled":
		raise CommandError("INVALID_STATE")
	doc = frappe.get_doc(
		{
			"doctype": "WA Operation",
			"company": company,
			"operation_type": operation_type,
			"requested_by": frappe.session.user,
			"request_id": request_id,
			"request_hash": request_hash,
			"request_json": args,
			"attempt_count": 0,
			"status": "Pending" if enabled else "Succeeded",
			"progress_percent": 0 if enabled else 100,
			"target_doctype": "WA Connection",
			"target_name": connection_name,
			"result_json": None if enabled else json.dumps({"enabled": False}),
			"result_file": None,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	operation_name, created = insert_idempotent_operation(doc)
	if not created:
		return {"operation": operation_name}
	if enabled:
		connection.db_set({"status": "Verifying", "last_error_code": None, "last_error_summary": None})
		frappe.enqueue(
			"tag_marketing.application.connection_jobs.run_connection_operation",
			queue="marketing",
			enqueue_after_commit=True,
			job_id=f"wa:{operation_name}",
			deduplicate=True,
			operation_id=operation_name,
			operation="set_enabled",
			connection_name=connection_name,
			kwargs=args,
		)
	else:
		connection.db_set({"status": "Disabled", "last_error_code": None, "last_error_summary": None})
		frappe.get_doc(
			{
				"doctype": "WA Audit Event",
				"company": company,
				"action": "Connection Disabled",
				"actor": frappe.session.user,
				"target_doctype": "WA Connection",
				"target_name": connection_name,
				"occurred_at": frappe.utils.now_datetime(),
				"details_json": "{}",
			}
		).db_insert()
	return {"operation": operation_name}
