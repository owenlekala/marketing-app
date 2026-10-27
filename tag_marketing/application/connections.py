"""Company-scoped connection commands and safe health projections."""

import hashlib
import json
import re
from typing import Any
from uuid import uuid4

import frappe
from frappe import _

from tag_marketing.application.navigation import can_open_app
from tag_marketing.domain.errors import CommandError, require_revision
from tag_marketing.infrastructure.permissions import company_allowed

REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
CONNECTION_OPERATIONS = {
	"validate_connection": "connections.validate_connection",
	"sync_numbers": "connections.sync_numbers",
	"sync_templates": "connections.sync_templates",
	"set_enabled": "connections.set_enabled",
}


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


def _insert_idempotent_operation(doc: Any) -> tuple[str, bool]:
	"""Enforce the operation uniqueness key even when duplicate requests race."""
	savepoint = "wa_op_" + uuid4().hex
	frappe.db.savepoint(savepoint)
	try:
		doc.db_insert()
		return doc.name, True
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		frappe.db.rollback(save_point=savepoint)
		prior = frappe.db.get_value(
			"WA Operation",
			{
				"requested_by": doc.requested_by,
				"operation_type": doc.operation_type,
				"request_id": doc.request_id,
			},
			["name", "request_hash"],
			as_dict=True,
		)
		if not prior:
			raise
		if prior.request_hash != doc.request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT") from None
		return prior.name, False


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
	return rows


def enqueue_connection_operation(
	operation: str,
	connection_name: str,
	request_id: str,
	*,
	expected_modified: str | None = None,
	enabled: bool | None = None,
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
	if operation == "set_enabled":
		if not isinstance(enabled, bool):
			raise CommandError("INVALID_INPUT", "enabled")
		args.update({"enabled": enabled, "expected_modified": expected_modified})
	request_hash = hashlib.sha256(
		json.dumps({"operation": operation, **args}, sort_keys=True, separators=(",", ":")).encode()
	).hexdigest()
	operation_type = CONNECTION_OPERATIONS[operation]
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
	company = _company()
	if not frappe.db.exists("WA Connection", {"name": connection_name, "company": company}):
		raise CommandError("NOT_FOUND")
	connection = frappe.get_doc("WA Connection", connection_name)
	if operation == "validate_connection":
		require_revision(str(connection.modified), expected_modified)
	if operation == "set_enabled":
		require_revision(str(connection.modified), expected_modified)
		if enabled and connection.status != "Disabled":
			raise CommandError("INVALID_STATE")
		if not enabled and connection.status == "Disabled":
			raise CommandError("INVALID_STATE")
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
	operation_name, created = _insert_idempotent_operation(doc)
	if not created:
		return {"operation": operation_name}
	frappe.enqueue(
		"tag_marketing.application.connection_jobs.run_connection_operation",
		queue="marketing",
		enqueue_after_commit=True,
		job_id=f"wa:{operation_name}",
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
) -> None:
	"""Validate test-send intent while dispatch remains gated on the shared P4 outbox."""
	_authorize("validate_connection")
	company = _company()
	if not all(isinstance(value, str) and value for value in (connection, sending_number, contact, template)):
		raise CommandError("INVALID_INPUT")
	if (
		not isinstance(sample_values, list)
		or len(sample_values) > 100
		or any(not isinstance(value, (str, int, float)) or len(str(value)) > 1024 for value in sample_values)
	):
		raise CommandError("INVALID_INPUT", "sample_values")
	if not frappe.db.exists(
		"WA Sending Number", {"name": sending_number, "company": company, "connection": connection}
	):
		raise CommandError("NOT_FOUND")
	if not frappe.db.exists(
		"WA Contact",
		{"name": contact, "company": company, "consent_status": "Granted", "suppressed": 0, "archived": 0},
	):
		raise CommandError("READINESS_FAILED")
	if not frappe.db.exists(
		"WA Template", {"name": template, "company": company, "connection": connection, "status": "Approved"}
	):
		raise CommandError("READINESS_FAILED")
	# Deliberately no success response or provider call until P4 implements the shared outbox.
	if not isinstance(request_id, str) or not REQUEST_ID.fullmatch(request_id):
		raise CommandError("INVALID_INPUT", "request_id")
	raise CommandError("READINESS_FAILED")


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
	operation_type = CONNECTION_OPERATIONS["set_enabled"]
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
			"status": "Pending" if enabled else "Succeeded",
			"progress_percent": 0 if enabled else 100,
			"target_doctype": "WA Connection",
			"target_name": connection_name,
			"result_json": None if enabled else json.dumps({"enabled": False}),
			"result_file": None,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	operation_name, created = _insert_idempotent_operation(doc)
	if not created:
		return {"operation": operation_name}
	if enabled:
		connection.db_set({"status": "Verifying", "last_error_code": None, "last_error_summary": None})
		frappe.enqueue(
			"tag_marketing.application.connection_jobs.run_connection_operation",
			queue="marketing",
			enqueue_after_commit=True,
			job_id=f"wa:{operation_name}",
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
