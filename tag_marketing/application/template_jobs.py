"""Durable template provider submission and selected-template synchronization."""

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import frappe

from tag_marketing.application.connection_jobs import (
	KNOWN_TEMPLATE_CATEGORIES,
	KNOWN_TEMPLATE_STATUSES,
	_safe_provider_error,
	_write_audit,
	provider_factory,
)
from tag_marketing.infrastructure.meta_cloud import FailureKind, ProviderFailure

PAGE_CAP = 100
RECOVERY_BATCH = 100


def run_template_operation(operation_id: str) -> None:
	frappe.db.sql(
		"""
		UPDATE `tabWA Operation`
		SET status = 'Running', attempt_count = COALESCE(attempt_count, 0) + 1,
			progress_percent = 5, heartbeat_at = NOW(), modified = NOW(), modified_by = %s
		WHERE name = %s AND status = 'Pending' AND operation_type IN ('templates.submit','templates.sync')
		""",
		(frappe.session.user, operation_id),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		return
	frappe.db.commit()
	operation = frappe.get_doc("WA Operation", operation_id)
	try:
		request = frappe.parse_json(operation.request_json or "{}")
		if not isinstance(request, dict):
			raise ValueError
		template = frappe.get_doc("WA Template", operation.target_name)
		connection = frappe.get_doc("WA Connection", template.connection)
		if (
			operation.target_doctype != "WA Template"
			or operation.company != template.company
			or connection.company != template.company
			or template.company != frappe.db.get_single_value("WA Settings", "marketing_company")
		):
			_finish(operation, "Failed", error="SCOPE_CHANGED")
			return
		if not _actor_authorized(operation.requested_by, operation.operation_type):
			_finish(operation, "Failed", error="NOT_AUTHORIZED")
			return
		if connection.status not in {"Ready", "Degraded"}:
			_finish(operation, "Failed", error="READINESS_FAILED")
			return
		api = provider_factory(connection)
		if operation.operation_type == "templates.submit":
			_submit(api, template, operation, request)
		else:
			_sync(api, template, operation)
	except ProviderFailure as error:
		code = _safe_provider_error(error)
		if error.kind == FailureKind.UNKNOWN_OUTCOME:
			frappe.db.set_value("WA Template", operation.target_name, "status", "Unknown")
		elif error.kind == FailureKind.REJECTED:
			frappe.db.set_value(
				"WA Template",
				operation.target_name,
				{"status": "Rejected", "provider_reason": "The provider rejected this template."},
			)
		_finish(operation, "Failed", error=code)
	except Exception as error:
		frappe.logger("tag_marketing").error(
			"Template operation %s failed (%s)", operation.name, type(error).__name__
		)
		_finish(operation, "Failed", error="PROVIDER_UNAVAILABLE")


def _submit(api: Any, template: Any, operation: Any, request: dict[str, Any]) -> None:
	if (
		template.status not in {"Draft", "Rejected"}
		or template.category not in {"Marketing", "Utility"}
		or template.provider_template_id
		or template.content_hash != request.get("content_hash")
		or request.get("expected_modified") != str(template.modified)
		or template.media_file
	):
		_finish(operation, "Failed", error="STALE_DOCUMENT")
		return
	try:
		components = frappe.parse_json(template.components_json)
		response = api.create_template(
			name=template.template_name,
			language=template.language_code,
			category=template.category.upper(),
			components=tuple(components),
		)
	except ProviderFailure:
		raise
	status = KNOWN_TEMPLATE_STATUSES.get(response.status.upper(), "Unknown")
	template.db_set(
		{
			"provider_template_id": response.provider_template_id,
			"status": status,
			"last_sync_at": frappe.utils.now_datetime(),
			"provider_reason": None,
		}
	)
	_write_audit(
		frappe.get_doc("WA Connection", template.connection),
		"Template Submitted",
		{"template": template.name, "content_hash": template.content_hash, "status": status},
		actor=operation.requested_by,
	)
	_finish(operation, "Succeeded", result={"status": status})


def _sync(api: Any, template: Any, operation: Any) -> None:
	if not template.provider_template_id:
		_finish(operation, "Failed", error="INVALID_STATE")
		return
	cursor = None
	seen: set[str] = set()
	for _page in range(PAGE_CAP):
		page = api.list_templates(cursor=cursor, limit=100)
		for item in page.items:
			if item.provider_template_id != template.provider_template_id:
				continue
			components = json.dumps(
				item.components, ensure_ascii=False, sort_keys=True, separators=(",", ":")
			)
			status = KNOWN_TEMPLATE_STATUSES.get(item.status.upper(), "Unknown")
			category = KNOWN_TEMPLATE_CATEGORIES.get(item.category.upper(), "Unknown")
			template.db_set(
				{
					"status": status,
					"category": category,
					"components_json": components,
					"content_hash": _provider_hash(
						template.template_name, template.language_code, category, components
					),
					"provider_reason": None,
					"last_sync_at": frappe.utils.now_datetime(),
				}
			)
			_write_audit(
				frappe.get_doc("WA Connection", template.connection),
				"Template Synced",
				{"template": template.name, "status": status, "category": category},
				actor=operation.requested_by,
			)
			_finish(operation, "Succeeded", result={"status": status})
			return
		cursor = page.next_cursor
		if not cursor:
			break
		if cursor in seen:
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		seen.add(cursor)
	_finish(operation, "Failed", error="NOT_FOUND")


def _provider_hash(name: str, language: str, category: str, components: str) -> str:
	import hashlib

	payload = json.dumps(
		{
			"name": name,
			"language": language,
			"category": category,
			"components": frappe.parse_json(components),
		},
		ensure_ascii=False,
		sort_keys=True,
		separators=(",", ":"),
	)
	return hashlib.sha256(payload.encode()).hexdigest()


def _actor_authorized(user: str, operation_type: str) -> bool:
	if (
		not frappe.db.get_value("User", user, "enabled")
		or frappe.db.get_value("User", user, "user_type") != "System User"
	):
		return False
	roles = set(frappe.get_roles(user))
	return bool(roles.intersection({"Marketing Manager", "System Manager"}))


def _finish(doc: Any, status: str, *, result: dict[str, Any] | None = None, error: str | None = None) -> None:
	doc.db_set(
		{
			"status": status,
			"progress_percent": 100 if status == "Succeeded" else doc.progress_percent,
			"result_json": json.dumps(result, separators=(",", ":")) if result else None,
			"result_file": None,
			"error_code": error,
			"heartbeat_at": datetime.now(UTC).replace(tzinfo=None),
		}
	)
	frappe.db.commit()


def recover_template_operations() -> None:
	"""Recover never-started jobs; stale submissions become Unknown and are never replayed."""
	now = frappe.utils.now_datetime()
	stale_before = now - timedelta(minutes=5)
	frappe.db.sql(
		"""
		UPDATE `tabWA Operation` o
		JOIN `tabWA Template` t ON t.name=o.target_name
		SET o.status='Failed', o.error_code='UNKNOWN_OUTCOME', o.heartbeat_at=%s,
			t.status='Unknown', t.modified=%s
		WHERE o.status='Running' AND o.operation_type='templates.submit'
			AND o.heartbeat_at < %s AND o.target_doctype='WA Template'
		""",
		(now, now, stale_before),
	)
	frappe.db.sql(
		"""
		UPDATE `tabWA Operation`
		SET status='Pending', attempt_count=0, error_code=NULL, heartbeat_at=%s
		WHERE status='Running' AND operation_type='templates.sync'
			AND heartbeat_at < %s AND target_doctype='WA Template'
		""",
		(now, stale_before),
	)
	frappe.db.commit()
	ready_before = now - timedelta(minutes=1)
	rows = frappe.get_all(
		"WA Operation",
		filters={
			"status": "Pending",
			"operation_type": ["in", ["templates.submit", "templates.sync"]],
			"target_doctype": "WA Template",
			"modified": ["<", ready_before],
		},
		fields=["name"],
		order_by="modified asc",
		limit=RECOVERY_BATCH,
	)
	for row in rows:
		frappe.db.sql(
			"""
			UPDATE `tabWA Operation` SET modified=%s, modified_by=%s
			WHERE name=%s AND status='Pending' AND modified < %s
			""",
			(now, frappe.session.user, row.name, ready_before),
		)
		if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
			continue
		frappe.db.commit()
		frappe.enqueue(
			"tag_marketing.application.template_jobs.run_template_operation",
			queue="marketing",
			enqueue_after_commit=True,
			job_id=f"wa:{row.name}",
			deduplicate=True,
			operation_id=row.name,
		)
