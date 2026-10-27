"""Read-only progress projection; generic operation CRUD remains closed."""

import math
from datetime import UTC
from typing import Any

import frappe

from tag_marketing.application.navigation import can_open_app
from tag_marketing.domain.errors import CommandError
from tag_marketing.infrastructure.permissions import company_allowed

# Producers are added by their feature tasks, not by this progress query.
TARGETS = {
	"connections.validate_connection": "WA Connection",
	"connections.sync_numbers": "WA Connection",
	"connections.sync_templates": "WA Connection",
	"connections.set_enabled": "WA Connection",
}
STATUSES = frozenset({"Pending", "Running", "Succeeded", "Failed", "Cancelled"})


def get_progress(operation: str) -> dict[str, Any]:
	if not isinstance(operation, str) or not operation or len(operation) > 140:
		raise CommandError("INVALID_INPUT", "operation")
	if not can_open_app() or not frappe.has_permission("WA Operation", "read"):
		raise CommandError("NOT_FOUND")
	try:
		doc = frappe.get_doc("WA Operation", operation)
	except frappe.DoesNotExistError:
		raise CommandError("NOT_FOUND") from None
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	user = frappe.session.user
	if (
		not company
		or doc.company != company
		or not company_allowed(company, user, "WA Operation")
		or (doc.requested_by != user and "Marketing Manager" not in frappe.get_roles())
		or TARGETS.get(doc.operation_type) != doc.target_doctype
		or not doc.target_name
	):
		raise CommandError("NOT_FOUND")
	try:
		target = frappe.get_doc(doc.target_doctype, doc.target_name)
	except frappe.DoesNotExistError:
		raise CommandError("NOT_FOUND") from None
	roles = set(frappe.get_roles(user))
	manager_template_sync = (
		doc.operation_type == "connections.sync_templates" and "Marketing Manager" in roles
	)
	if (
		target.company != company
		or not company_allowed(company, user, doc.target_doctype)
		or (not manager_template_sync and not target.has_permission("read"))
		or (manager_template_sync and not roles.intersection({"Marketing Manager", "System Manager"}))
	):
		raise CommandError("NOT_FOUND")
	try:
		progress = float(doc.progress_percent or 0)
		if not math.isfinite(progress) or not 0 <= progress <= 100 or doc.status not in STATUSES:
			raise ValueError
	except (ValueError, TypeError):
		raise CommandError("PERSISTENCE_UNAVAILABLE") from None
	heartbeat = (
		frappe.utils.get_datetime(doc.heartbeat_at).replace(tzinfo=UTC).isoformat()
		if doc.heartbeat_at
		else None
	)
	result: dict[str, Any] | None = None
	if doc.status == "Succeeded" and doc.result_json:
		try:
			stored: Any = frappe.parse_json(doc.result_json)
			if doc.operation_type == "connections.validate_connection" and stored == {"validated": True}:
				result = {"validated": True}
			elif doc.operation_type == "connections.set_enabled" and stored in (
				{"enabled": False},
				{"validated": True, "enabled": True},
			):
				result = {"enabled": stored["enabled"]}
			elif doc.operation_type in {"connections.sync_numbers", "connections.sync_templates"}:
				count = stored.get("synced_count") if isinstance(stored, dict) else None
				if isinstance(count, int) and 0 <= count <= 100_000:
					result = {"synced_count": count}
		except (TypeError, ValueError):
			pass
	return {
		"operation": doc.name,
		"status": doc.status,
		"progress_percent": progress,
		"heartbeat_at": heartbeat,
		"result": result,
		"result_file": None,
		"error": {
			"code": "OPERATION_FAILED",
			"message": frappe._("Operation failed. Contact your administrator with the operation ID."),
		}
		if doc.status == "Failed"
		else None,
	}
