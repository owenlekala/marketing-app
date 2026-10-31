"""Contact and tag DocType invariants; commands own source linking."""

from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import frappe
from frappe import _

from tag_marketing.application.audiences import _source_enabled, _source_identity
from tag_marketing.infrastructure.permissions import company_allowed

DERIVED_FIELDS = frozenset({"consent_status", "suppressed", "last_inbound_at", "archived"})


def _validate_contact(doc: Any) -> None:
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if (
		not company
		or doc.company != company
		or not company_allowed(company, frappe.session.user, "WA Contact")
	):
		frappe.throw(_("Select the configured marketing company."), frappe.PermissionError)
	if not doc.phone_e164 or not doc.phone_e164.startswith("+") or len(doc.phone_e164) < 8:
		frappe.throw(_("Phone identity must be a valid E.164 number."))
	if not doc.display_name or not doc.display_name.strip():
		frappe.throw(_("Enter a contact display name."))
	if doc.timezone:
		try:
			ZoneInfo(doc.timezone)
		except (ZoneInfoNotFoundError, ValueError):
			frappe.throw(_("Choose a valid IANA timezone."))
	for row in doc.tags:
		if frappe.db.get_value("WA Tag", row.tag, "company") != company or frappe.db.get_value(
			"WA Tag", row.tag, "disabled"
		):
			frappe.throw(_("Contact tags must be enabled and belong to the configured company."))
	old = doc.get_doc_before_save()
	if old:
		for field in ("company", "phone_e164", *DERIVED_FIELDS):
			if doc.get(field) != old.get(field):
				frappe.throw(
					_("{0} is service-managed.").format(_(field.replace("_", " ").title())),
					frappe.PermissionError,
				)
		old_links = list(old.source_links)
		new_links = list(doc.source_links)
		old_keys = [_source_link_key(link) for link in old_links]
		new_keys = [_source_link_key(link) for link in new_links]
		if new_keys != old_keys:
			if not doc.flags.wa_source_command or len(doc.source_links) < len(old.source_links):
				frappe.throw(
					_("Source links are managed by the source-selection command."), frappe.PermissionError
				)
			for index, prior_key in enumerate(old_keys):
				if new_keys[index] != prior_key:
					frappe.throw(
						_("Existing source links cannot be changed or removed."), frappe.PermissionError
					)
			for link in new_links[len(old_links) :]:
				_validate_source_links_for_current_actor(link, company)
		if doc.get("display_name") != old.get("display_name") and doc.get("phone_e164") != old.get(
			"phone_e164"
		):
			frappe.throw(_("A phone number change creates a new contact identity."))
	else:
		if not doc.flags.wa_source_command or not doc.source_links:
			frappe.throw(
				_("Create contacts by selecting an authorised ERPNext source."), frappe.PermissionError
			)
		if doc.consent_status != "Unknown" or doc.suppressed or doc.archived or doc.last_inbound_at:
			frappe.throw(_("New source-linked contacts start with unknown consent and no derived activity."))
		_validate_source_links(doc, company)
	if doc.language and not frappe.db.exists("Language", doc.language):
		frappe.throw(_("Choose a valid language."))


def _validate_source_links(doc: Any, company: str) -> None:
	seen = set()
	for link in doc.source_links:
		key = (link.source_doctype, link.source_name)
		if key in seen:
			frappe.throw(_("A source can be linked only once."))
		seen.add(key)
		_validate_source_links_for_current_actor(link, company)


def _validate_source_links_for_current_actor(link: Any, company: str) -> None:
	_source_enabled(link.source_doctype)
	if link.included_unassigned_lead and link.source_doctype != "Lead":
		frappe.throw(_("Only Leads can be explicitly included without a Company."))
	_label, phones, _region = _source_identity(
		link.source_doctype,
		link.source_name,
		company,
		include_unassigned_lead=bool(link.included_unassigned_lead),
	)
	if link.selected_phone not in {phone for phone, _source in phones}:
		frappe.throw(_("The selected mobile number is no longer available on this source."))
	if not link.selected_by or not link.selected_at:
		frappe.throw(_("Source selection audit fields are required."))
	if link.selected_by != frappe.session.user:
		frappe.throw(_("Source selection actor is service-managed."), frappe.PermissionError)


def _source_link_key(link: Any) -> tuple[str, str, str, str, str, bool]:
	return (
		link.source_doctype,
		link.source_name,
		link.selected_phone,
		link.selected_by,
		str(link.selected_at),
		bool(link.included_unassigned_lead),
	)


def _validate_tag(doc: Any) -> None:
	if "Marketing Manager" not in frappe.get_roles() and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Only Marketing Managers may manage contact tags."), frappe.PermissionError)
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or doc.company != company or not company_allowed(company, frappe.session.user, "WA Tag"):
		frappe.throw(_("Select the configured marketing company."), frappe.PermissionError)
	doc.label = (doc.label or "").strip()
	if not doc.label or len(doc.label) > 80:
		frappe.throw(_("Tag labels must contain 1 to 80 characters."))
	old = doc.get_doc_before_save()
	if old and old.company != doc.company:
		frappe.throw(_("Tag company is immutable."), frappe.PermissionError)


def validate_contact(doc: Any) -> None:
	_validate_contact(doc)


def validate_tag(doc: Any) -> None:
	_validate_tag(doc)
