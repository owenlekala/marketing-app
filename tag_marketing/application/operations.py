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
	"imports.validate_batch": "WA Import Batch",
	"imports.confirm_batch": "WA Import Batch",
	"audiences.preview": "WA Audience Segment",
	"templates.save_draft": "WA Template",
	"templates.submit": "WA Template",
	"templates.sync": "WA Template",
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
		doc.operation_type in {"connections.sync_templates", "templates.submit", "templates.sync"}
		and "Marketing Manager" in roles
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
			elif doc.operation_type in {"imports.validate_batch", "imports.confirm_batch"} and isinstance(
				stored, dict
			):
				result = {
					key: value
					for key, value in stored.items()
					if key in {"valid_count", "rejected_count", "evidence_missing_count", "imported_count"}
					and isinstance(value, int)
					and 0 <= value <= 100_000
				}
			elif doc.operation_type == "audiences.preview" and isinstance(stored, dict):
				counts: dict[str, Any] = {
					key: value
					for key, value in stored.items()
					if key in {"matched_count", "eligible_count"}
					and isinstance(value, int)
					and 0 <= value <= 50_000
				}
				excluded = stored.get("excluded")
				items = stored.get("items")
				if isinstance(excluded, dict) and isinstance(items, list) and len(items) <= 50:
					counts["excluded"] = {
						key: value
						for key, value in excluded.items()
						if key in {"suppressed", "archived", "withdrawn", "unknown_consent"}
						and isinstance(value, int)
						and 0 <= value <= 50_000
					}
					safe_items = []
					for item in items:
						if not isinstance(item, dict):
							continue
						if all(
							isinstance(item.get(key), str) and len(item[key]) <= max_length
							for key, max_length in (("name", 140), ("display_name", 140), ("phone", 32))
						) and (
							item.get("language") is None
							or (isinstance(item.get("language"), str) and len(item["language"]) <= 32)
						):
							safe_items.append(
								{key: item.get(key) for key in ("name", "display_name", "phone", "language")}
							)
					counts["items"] = safe_items
					next_cursor = stored.get("next_cursor")
					if next_cursor is None or (isinstance(next_cursor, str) and len(next_cursor) <= 140):
						counts["next_cursor"] = next_cursor
					result = counts
			elif doc.operation_type == "templates.save_draft" and isinstance(stored, dict):
				if (
					isinstance(stored.get("template"), str)
					and isinstance(stored.get("status"), str)
					and isinstance(stored.get("content_hash"), str)
					and len(stored["content_hash"]) == 64
				):
					result = {
						"template": stored["template"],
						"status": stored["status"],
						"content_hash": stored["content_hash"],
					}
			elif doc.operation_type in {"templates.submit", "templates.sync"} and isinstance(stored, dict):
				if stored.get("status") in {
					"Draft",
					"Pending",
					"Approved",
					"Rejected",
					"Paused",
					"Disabled",
					"Unknown",
				}:
					result = {"status": stored["status"]}
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
