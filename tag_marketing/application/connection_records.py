"""Server-side validation and audit policy for editable connection records."""

import json
import math
import secrets
from datetime import UTC, datetime
from typing import Any

import frappe

from tag_marketing.infrastructure.meta_cloud import SUPPORTED_GRAPH_VERSIONS

SECRET_FIELDS = ("access_token", "app_secret", "verify_token")
EDITABLE_CONNECTION_FIELDS = frozenset(
	{"connection_name", "meta_app_id", "waba_id", "api_version", *SECRET_FIELDS}
)
PROVIDER_NUMBER_FIELDS = (
	"company",
	"connection",
	"provider_phone_id",
	"display_phone",
	"display_name",
	"status",
	"quality_rating",
	"provider_limits_json",
	"last_sync_at",
)


def _system_manager() -> None:
	if frappe.session.user != "Administrator" and "System Manager" not in frappe.get_roles():
		frappe.throw(
			frappe._("Only System Managers can configure WhatsApp connections."), frappe.PermissionError
		)


def validate_connection_record(doc: Any) -> None:
	_system_manager()
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company:
		frappe.throw(frappe._("Configure the marketing company before adding a WhatsApp connection."))
	old = doc.get_doc_before_save()
	if doc.is_new():
		doc.company = company
		doc.public_id = secrets.token_urlsafe(24)
		if not doc.verify_token or doc.is_dummy_password(doc.verify_token):
			doc.verify_token = secrets.token_urlsafe(32)
		doc.status = "Draft"
		doc.last_webhook_at = None
	else:
		if not old or old.company != company or doc.company != old.company:
			frappe.throw(
				frappe._("Connection company is managed by WhatsApp Settings."), frappe.PermissionError
			)
		if old.public_id != doc.public_id:
			frappe.throw(frappe._("Connection routing identity cannot be changed."), frappe.PermissionError)
		for field in (
			"status",
			"last_validated_at",
			"last_webhook_at",
			"last_error_code",
			"last_error_summary",
		):
			if doc.get(field) != old.get(field):
				frappe.throw(
					frappe._("Connection status and diagnostics are service-managed."), frappe.PermissionError
				)
		for field in SECRET_FIELDS:
			# Password controls submit a mask for an existing secret. Preserve that
			# encrypted value explicitly; an empty form value must never erase it.
			candidate = doc.get(field)
			previous = old.get_password(field, raise_exception=False)
			if not candidate and previous:
				doc.set(field, "*" * 16)
	changed: list[str] = []
	if old:
		changed.extend(
			field
			for field in EDITABLE_CONNECTION_FIELDS - set(SECRET_FIELDS)
			if doc.get(field) != old.get(field)
		)
		for field in SECRET_FIELDS:
			candidate = doc.get(field)
			if candidate and not doc.is_dummy_password(candidate):
				previous = old.get_password(field, raise_exception=False)
				if candidate != previous:
					changed.append(field)
	for field in ("connection_name", "meta_app_id", "waba_id", "api_version"):
		value = (doc.get(field) or "").strip()
		if not value or len(value) > 128:
			frappe.throw(frappe._("Enter a valid connection name, Meta App ID, WABA ID, and API version."))
		doc.set(field, value)
	if not doc.meta_app_id.isdecimal() or not doc.waba_id.isdecimal():
		frappe.throw(frappe._("Meta App ID and WhatsApp Business Account ID must contain digits only."))
	if doc.api_version not in SUPPORTED_GRAPH_VERSIONS:
		frappe.throw(frappe._("This Graph API version is not supported by the installed adapter."))
	for field in SECRET_FIELDS:
		value = doc.get(field)
		if (not value or doc.is_dummy_password(value)) and doc.is_new():
			frappe.throw(frappe._("Complete all connection credentials."))
		if (
			old
			and (not value or doc.is_dummy_password(value))
			and not old.get_password(field, raise_exception=False)
		):
			frappe.throw(frappe._("Complete all connection credentials."))
		if value and not doc.is_dummy_password(value) and (len(value) < 16 or len(value) > 4096):
			frappe.throw(frappe._("Connection credentials must be between 16 and 4096 characters."))
	if old and changed:
		doc.status = (
			"Disabled" if old.status == "Disabled" else ("Draft" if old.status == "Draft" else "Degraded")
		)
		doc.last_validated_at = None
		doc.last_error_code = None
		doc.last_error_summary = None
	doc._wa_connection_changed = changed


def validate_number_record(doc: Any) -> None:
	_system_manager()
	if doc.is_new():
		frappe.throw(frappe._("Sending numbers are created by provider sync."), frappe.PermissionError)
	old = doc.get_doc_before_save()
	if not old:
		frappe.throw(frappe._("Reload this sending number."))
	for field in PROVIDER_NUMBER_FIELDS:
		if doc.get(field) != old.get(field):
			frappe.throw(
				frappe._("Provider identity and readiness are service-managed."), frappe.PermissionError
			)
	if doc.rate_per_second is not None:
		try:
			rate = float(doc.rate_per_second)
		except (TypeError, ValueError):
			frappe.throw(frappe._("Enter a positive rate per second."))
		if not math.isfinite(rate) or rate <= 0:
			frappe.throw(frappe._("Enter a positive rate per second."))
	if doc.default_team and not frappe.db.exists("User Group", doc.default_team):
		frappe.throw(frappe._("Select an existing default agent team."))


def audit_connection_change(doc: Any) -> None:
	old = doc.get_doc_before_save()
	changed = getattr(doc, "_wa_connection_changed", [])
	if not changed and old:
		return
	action = "Connection Created" if not old else "Connection Updated"
	_write_audit(doc.company, action, "WA Connection", doc.name, {"changed_fields": sorted(changed)})


def audit_number_change(doc: Any) -> None:
	old = doc.get_doc_before_save()
	if not old:
		return
	changed = [field for field in ("rate_per_second", "default_team") if old.get(field) != doc.get(field)]
	if changed:
		_write_audit(
			doc.company,
			"Sending Number Configuration Updated",
			"WA Sending Number",
			doc.name,
			{"changed_fields": changed},
		)


def _write_audit(
	company: str, action: str, target_doctype: str, target_name: str, details: dict[str, Any]
) -> None:
	frappe.get_doc(
		{
			"doctype": "WA Audit Event",
			"company": company,
			"action": action,
			"actor": frappe.session.user,
			"target_doctype": target_doctype,
			"target_name": target_name,
			"occurred_at": datetime.now(UTC).replace(tzinfo=None),
			"details_json": json.dumps(details, separators=(",", ":")),
		}
	).db_insert()
