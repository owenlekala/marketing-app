"""Background provider validation and company-scoped catalog synchronization."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import frappe

from tag_marketing.application.ports import ProviderTransport
from tag_marketing.domain.errors import CommandError
from tag_marketing.infrastructure.meta_cloud import (
	FailureKind,
	MetaCloudAPI,
	MetaConfig,
	MetaCredentials,
	ProviderFailure,
)
from tag_marketing.infrastructure.meta_http import RequestsProviderTransport

PAGE_CAP = 100
KNOWN_TEMPLATE_STATUSES = {
	"PENDING": "Pending",
	"APPROVED": "Approved",
	"REJECTED": "Rejected",
	"PAUSED": "Paused",
	"DISABLED": "Disabled",
}
KNOWN_TEMPLATE_CATEGORIES = {
	"MARKETING": "Marketing",
	"UTILITY": "Utility",
	"AUTHENTICATION": "Authentication",
}


def provider_factory(connection: Any, transport: ProviderTransport | None = None) -> MetaCloudAPI:
	return MetaCloudAPI(
		MetaConfig(api_version=connection.api_version, waba_id=connection.waba_id),
		MetaCredentials(
			access_token=connection.get_password("access_token"),
			app_secret=connection.get_password("app_secret"),
		),
		transport or RequestsProviderTransport(),
	)


def run_connection_operation(
	operation_id: str, operation: str, connection_name: str, kwargs: dict[str, Any]
) -> None:
	"""Execute only durable operation records; all provider work stays outside HTTP requests."""
	doc = frappe.get_doc("WA Operation", operation_id)
	connection = frappe.get_doc("WA Connection", connection_name)
	if doc.status not in {"Pending", "Running"} or doc.target_name != connection_name:
		return
	if not _actor_still_authorized(doc.requested_by, operation):
		_finish(doc, "Failed", error="NOT_AUTHORIZED")
		return
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or doc.company != company or connection.company != company:
		_finish(doc, "Failed", error="SCOPE_CHANGED")
		return
	if operation == "validate_connection" and str(connection.modified) != kwargs.get("expected_modified"):
		_finish(doc, "Failed", error="STALE_DOCUMENT")
		return
	if (
		operation in {"validate_connection", "sync_numbers", "sync_templates"}
		and connection.status == "Disabled"
	):
		_finish(doc, "Failed", error="INVALID_STATE")
		return
	if operation == "set_enabled" and connection.status != "Verifying":
		_finish(doc, "Failed", error="INVALID_STATE")
		return
	if operation in {"sync_numbers", "sync_templates"} and connection.status not in {"Ready", "Degraded"}:
		_finish(doc, "Failed", error="READINESS_FAILED")
		return
	doc.db_set({"status": "Running", "progress_percent": 5, "heartbeat_at": frappe.utils.now_datetime()})
	frappe.db.commit()
	try:
		api = provider_factory(connection)
		if operation in {"validate_connection", "set_enabled"}:
			api.validate_connection()
			api.list_numbers(limit=1)
			api.list_templates(limit=1)
			connection.db_set(
				{
					"status": "Ready",
					"last_validated_at": frappe.utils.now_datetime(),
					"last_error_code": None,
					"last_error_summary": None,
				}
			)
			_write_audit(connection, "Connection Validated", {}, actor=doc.requested_by)
			_finish(
				doc,
				"Succeeded",
				result={"validated": True, "enabled": True}
				if operation == "set_enabled"
				else {"validated": True},
			)
		elif operation == "sync_numbers":
			count = _sync_numbers(api, connection, doc)
			_finish(doc, "Succeeded", result={"synced_count": count})
		elif operation == "sync_templates":
			count = _sync_templates(api, connection, doc)
			_finish(doc, "Succeeded", result={"synced_count": count})
		else:
			_finish(doc, "Failed", error="INVALID_OPERATION")
	except ProviderFailure as exc:
		_failure = _safe_provider_error(exc)
		if operation in {"validate_connection", "set_enabled"}:
			connection.db_set(
				{
					"status": "Degraded",
					"last_error_code": _failure,
					"last_error_summary": "Provider validation failed.",
				}
			)
		_finish(doc, "Failed", error=_failure)
	except Exception as exc:
		# Keep raw provider responses and exception messages out of persisted diagnostics.
		frappe.logger("tag_marketing").error(
			"Connection operation %s failed (%s)", doc.name, type(exc).__name__
		)
		_finish(doc, "Failed", error="PROVIDER_UNAVAILABLE")


def _actor_still_authorized(user: str, operation: str) -> bool:
	if (
		not frappe.db.get_value("User", user, "enabled")
		or frappe.db.get_value("User", user, "user_type") != "System User"
	):
		return False
	roles = set(frappe.get_roles(user))
	if operation == "sync_templates":
		return bool(roles.intersection({"Marketing Manager", "System Manager"}))
	return "System Manager" in roles or user == "Administrator"


def _sync_numbers(api: MetaCloudAPI, connection: Any, operation: Any) -> int:
	cursor = None
	seen: set[str] = set()
	count = 0
	for page_no in range(PAGE_CAP):
		page = api.list_numbers(cursor=cursor, limit=100)
		for item in page.items:
			prior = frappe.db.get_value(
				"WA Sending Number", {"provider_phone_id": item.provider_phone_id}, "name"
			)
			if prior:
				doc = frappe.get_doc("WA Sending Number", prior)
				if doc.company != connection.company or doc.connection != connection.name:
					raise ProviderFailure(FailureKind.WRONG_ACCOUNT)
				doc.db_set(
					{
						"display_phone": item.display_phone,
						"display_name": item.display_name,
						"quality_rating": item.quality_rating,
						"last_sync_at": frappe.utils.now_datetime(),
					}
				)
			else:
				frappe.get_doc(
					{
						"doctype": "WA Sending Number",
						"company": connection.company,
						"connection": connection.name,
						"provider_phone_id": item.provider_phone_id,
						"display_phone": item.display_phone,
						"display_name": item.display_name,
						"status": "Unverified",
						"quality_rating": item.quality_rating,
						"provider_limits_json": None,
						"rate_per_second": None,
						"last_sync_at": frappe.utils.now_datetime(),
					}
				).db_insert()
			count += 1
		seen.add(item.provider_phone_id)
		cursor = page.next_cursor
		operation.db_set(
			{"progress_percent": min(95, 10 + (page_no + 1) * 5), "heartbeat_at": frappe.utils.now_datetime()}
		)
		frappe.db.commit()
		if not cursor:
			_write_audit(
				connection, "Sending Numbers Synced", {"synced_count": count}, actor=operation.requested_by
			)
			return count
		if cursor in seen or cursor == operation.request_id:
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		seen.add(cursor)
	# A full final page means the configured bound was reached; avoid partial success.
	raise ProviderFailure(FailureKind.INVALID_RESPONSE)


def _sync_templates(api: MetaCloudAPI, connection: Any, operation: Any) -> int:
	cursor = None
	seen_cursors: set[str] = set()
	count = 0
	for page_no in range(PAGE_CAP):
		page = api.list_templates(cursor=cursor, limit=100)
		for item in page.items:
			components = json.dumps(
				item.components, ensure_ascii=False, sort_keys=True, separators=(",", ":")
			)
			content_hash = hashlib.sha256(components.encode()).hexdigest()
			prior = frappe.db.get_value(
				"WA Template", {"provider_template_id": item.provider_template_id}, "name"
			)
			if prior:
				doc = frappe.get_doc("WA Template", prior)
				if doc.company != connection.company or doc.connection != connection.name:
					raise ProviderFailure(FailureKind.WRONG_ACCOUNT)
				doc.db_set(
					{
						"template_name": item.name,
						"language_code": item.language,
						"category": KNOWN_TEMPLATE_CATEGORIES.get(item.category.upper(), "Unknown"),
						"components_json": components,
						"status": KNOWN_TEMPLATE_STATUSES.get(item.status.upper(), "Unknown"),
						"content_hash": content_hash,
						"provider_reason": None,
						"last_sync_at": frappe.utils.now_datetime(),
					}
				)
			else:
				frappe.get_doc(
					{
						"doctype": "WA Template",
						"company": connection.company,
						"connection": connection.name,
						"provider_template_id": item.provider_template_id,
						"template_name": item.name,
						"language_code": item.language,
						"category": KNOWN_TEMPLATE_CATEGORIES.get(item.category.upper(), "Unknown"),
						"components_json": components,
						"status": KNOWN_TEMPLATE_STATUSES.get(item.status.upper(), "Unknown"),
						"content_hash": content_hash,
						"last_sync_at": frappe.utils.now_datetime(),
					}
				).db_insert()
			count += 1
		operation.db_set(
			{"progress_percent": min(95, 10 + (page_no + 1) * 5), "heartbeat_at": frappe.utils.now_datetime()}
		)
		frappe.db.commit()
		cursor = page.next_cursor
		if not cursor:
			_write_audit(
				connection, "Templates Synced", {"synced_count": count}, actor=operation.requested_by
			)
			return count
		if cursor in seen_cursors:
			raise ProviderFailure(FailureKind.INVALID_RESPONSE)
		seen_cursors.add(cursor)
	raise ProviderFailure(FailureKind.INVALID_RESPONSE)


def _safe_provider_error(exc: ProviderFailure) -> str:
	return {
		FailureKind.INVALID_CREDENTIAL: "INVALID_CREDENTIAL",
		FailureKind.UNSUPPORTED_VERSION: "UNSUPPORTED_VERSION",
		FailureKind.WRONG_ACCOUNT: "WRONG_ACCOUNT",
		FailureKind.RATE_LIMITED: "RATE_LIMITED",
		FailureKind.REJECTED: "PROVIDER_REJECTED",
		FailureKind.UNAVAILABLE: "PROVIDER_UNAVAILABLE",
		FailureKind.UNKNOWN_OUTCOME: "UNKNOWN_OUTCOME",
		FailureKind.INVALID_RESPONSE: "INVALID_PROVIDER_RESPONSE",
		FailureKind.UNSUPPORTED_MEDIA: "UNSUPPORTED_MEDIA",
	}[exc.kind]


def _finish(doc: Any, status: str, *, result: dict[str, Any] | None = None, error: str | None = None) -> None:
	doc.db_set(
		{
			"status": status,
			"progress_percent": 100 if status == "Succeeded" else doc.progress_percent,
			"result_json": json.dumps(result, separators=(",", ":")) if result else None,
			"result_file": None,
			"error_code": error,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	frappe.db.commit()


def _write_audit(connection: Any, action: str, details: dict[str, Any], *, actor: str) -> None:
	frappe.get_doc(
		{
			"doctype": "WA Audit Event",
			"company": connection.company,
			"action": action,
			"actor": actor,
			"target_doctype": "WA Connection",
			"target_name": connection.name,
			"occurred_at": datetime.now(UTC).replace(tzinfo=None),
			"details_json": json.dumps(details, separators=(",", ":")),
		}
	).db_insert()
