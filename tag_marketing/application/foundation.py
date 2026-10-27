"""Foundation policies. No feature command or sending path is enabled here."""

import json
from datetime import UTC, datetime
from typing import Any

import frappe
from frappe import _

from tag_marketing.domain.settings import SOURCES, validate_settings
from tag_marketing.infrastructure.schema import PARENT_TYPES

MANAGED_SETTINGS = (
	"pilot_verified_at",
	"pilot_verified_by",
	"pilot_evidence_reference",
	"suppression_hmac_key",
)


def deny_feature_write(doctype: str = "Marketing record") -> None:
	frappe.throw(
		_("{0} is service-managed. Its feature commands are not available yet.").format(_(doctype)),
		frappe.PermissionError,
	)


def validate_company_links(doc: Any) -> None:
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or doc.company != company:
		frappe.throw(_("Select the configured marketing company."))
	for field in doc.meta.fields:
		value = doc.get(field.fieldname)
		if (
			field.fieldtype == "Link"
			and field.options in PARENT_TYPES
			and field.options != "WA Settings"
			and value
		):
			linked_company = frappe.db.get_value(field.options, value, "company")
			if linked_company != company:
				frappe.throw(_("Linked marketing records must belong to the configured company."))
	if doc.doctype == "WA Contact":
		for row in doc.tags:
			if frappe.db.get_value("WA Tag", row.tag, "company") != company:
				frappe.throw(_("Contact tags must belong to the configured company."))


def validate_record(doc: Any) -> None:
	if doc.docstatus != 0:
		frappe.throw(_("Marketing records do not use submission or cancellation."))
	if doc.doctype == "WA Settings":
		validate_settings_record(doc)
		return
	validate_company_links(doc)
	# Fail closed while feature services are absent, including Administrator/import/ignore_permissions.
	# Feature tasks replace this gate with action-specific managed-field/state policies.
	deny_feature_write(doc.doctype)


def validate_settings_record(doc: Any) -> None:
	if "System Manager" not in frappe.get_roles() and frappe.session.user != "Administrator":
		frappe.throw(_("Only System Managers may change marketing settings."), frappe.PermissionError)
	old = doc.get_doc_before_save() or frappe.get_doc("WA Settings")
	for field in MANAGED_SETTINGS:
		value = doc.get(field)
		if field == "suppression_hmac_key":
			if value != "********":
				frappe.throw(_("Suppression credentials are server-managed."), frappe.PermissionError)
		elif value != (old.get(field) if old else None):
			frappe.throw(_("Pilot evidence is service-managed."), frappe.PermissionError)
	if old and old.marketing_company and old.marketing_company != doc.marketing_company:
		if any(
			frappe.db.exists(kind, {"company": old.marketing_company})
			for kind in PARENT_TYPES
			if kind != "WA Settings"
		):
			frappe.throw(_("Marketing company cannot change while company-owned records exist."))
	try:
		validate_settings(doc.as_dict())
	except ValueError as exc:
		messages = {
			"invalid_timezone_hours": _("Use a valid IANA timezone and marketing start/end times"),
			"invalid_hours": _("Marketing end must be later than start"),
			"invalid_cap": _("Marketing cap and window must be positive integers"),
			"invalid_recipient_limit": _("The v1 campaign recipient limit is 10000"),
			"invalid_retention_rate": _("Retention periods and rates cannot be negative or non-finite"),
			"invalid_retention_days": _("Retention periods must be whole days"),
			"invalid_privacy_url": _("Privacy notice must use an HTTPS URL without credentials"),
			"invalid_scope": _("Choose Pilot or Live sending scope"),
		}
		frappe.throw(messages[str(exc)])
	if doc.sending_enabled:
		frappe.throw(
			_(
				"Sending cannot be enabled until connection, consent and dispatch readiness are implemented and verified."
			)
		)
	if doc.sending_scope == "Live" and not all(doc.get(field) for field in MANAGED_SETTINGS[:3]):
		frappe.throw(_("Live scope requires reviewed pilot evidence."))
	if (
		old
		and old.sending_enabled
		and [row.as_dict() for row in doc.pilot_contacts] != [row.as_dict() for row in old.pilot_contacts]
	):
		frappe.throw(_("Disable sending before changing the pilot allowlist."))
	contacts = [row.contact for row in doc.pilot_contacts]
	if len(contacts) > 20 or len(contacts) != len(set(contacts)):
		frappe.throw(_("Pilot contacts must be unique with a maximum of 20."))
	for contact in contacts:
		profile = frappe.db.get_value(
			"WA Contact", contact, ["company", "consent_status", "suppressed", "archived"], as_dict=True
		)
		if (
			not profile
			or profile.company != doc.marketing_company
			or profile.consent_status != "Granted"
			or profile.suppressed
			or profile.archived
		):
			frappe.throw(
				_(
					"Pilot contacts require current consent in the marketing company without suppression or archival."
				)
			)
	sources = [row.source_doctype for row in doc.enabled_source_types]
	if len(sources) != len(set(sources)) or any(source not in SOURCES for source in sources):
		frappe.throw(
			_("Source types must be unique and selected from Lead, Customer, Contact and Sales Order.")
		)


def audit_settings(doc: Any) -> None:
	old = doc.get_doc_before_save()
	changed = sorted(
		field.fieldname
		for field in doc.meta.fields
		if field.fieldtype not in ("Password", "Section Break", "Column Break", "Tab Break")
		and doc.get(field.fieldname) != (old.get(field.fieldname) if old else None)
	)
	if not changed:
		return
	# Explicit trusted persistence: no public bypass flag or whitelisted write method.
	frappe.get_doc(
		{
			"doctype": "WA Audit Event",
			"company": doc.marketing_company,
			"action": "Settings Updated",
			"actor": frappe.session.user,
			"target_doctype": doc.doctype,
			"target_name": doc.name,
			"occurred_at": datetime.now(UTC).replace(tzinfo=None),
			"details_json": json.dumps({"changed_fields": changed}),
		}
	).db_insert()
