"""Permission-aware ERPNext source projections and contact linking commands."""

from datetime import UTC, datetime
from typing import Any

import frappe
from frappe import _

from tag_marketing.application.navigation import require_capability
from tag_marketing.application.suppression import is_identity_suppressed
from tag_marketing.domain.errors import CommandError
from tag_marketing.domain.phones import to_e164
from tag_marketing.domain.settings import SOURCES
from tag_marketing.infrastructure.permissions import company_allowed

SOURCE_FIELDS: dict[str, tuple[str, ...]] = {
	"Lead": ("name", "lead_name", "mobile_no", "country", "company"),
	"Customer": ("name", "customer_name", "customer_primary_contact", "mobile_no"),
	"Contact": ("name", "full_name", "first_name", "last_name", "mobile_no"),
	"Sales Order": ("name", "customer", "contact_person", "company", "docstatus"),
}
MAX_PREVIEW = 20


def _company() -> str:
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or not company_allowed(company, frappe.session.user, "WA Contact"):
		raise CommandError("COMPANY_MISMATCH")
	return company


def _source_enabled(doctype: str) -> None:
	if doctype not in SOURCES or doctype not in SOURCE_FIELDS:
		raise CommandError("INVALID_INPUT", "source_doctype")
	enabled = frappe.get_all("WA Source Type", filters={"parent": "WA Settings"}, pluck="source_doctype")
	if doctype not in enabled:
		raise CommandError("INVALID_STATE")


def _read_source(
	doctype: str, name: str, company: str, *, include_unassigned_lead: bool = False
) -> dict[str, Any]:
	"""Read only allowlisted fields through Frappe's permission-aware list API."""
	_source_enabled(doctype)
	filters: dict[str, Any] = {"name": name}
	or_filters = None
	if doctype == "Lead" and include_unassigned_lead:
		or_filters = [["Lead", "company", "=", company], ["Lead", "company", "is", "not set"]]
	elif doctype in ("Lead", "Sales Order"):
		filters["company"] = company
	if doctype == "Sales Order":
		filters["docstatus"] = 1
	rows = frappe.get_list(
		doctype, filters=filters, or_filters=or_filters, fields=list(SOURCE_FIELDS[doctype]), limit=1
	)
	if not rows:
		raise CommandError("SOURCE_ACCESS_DENIED")
	return rows[0]


def _phones_for_contact(contact_name: str) -> list[tuple[str, str]]:
	"""Return mobile candidates only; Contact Phone rows are read after Contact permission."""
	if not frappe.has_permission("Contact", "read", doc=contact_name):
		raise CommandError("SOURCE_ACCESS_DENIED")
	contact = frappe.get_doc("Contact", contact_name)
	values: list[tuple[str, str]] = []
	for row in contact.phone_nos:
		if row.phone and row.is_primary_mobile_no:
			values.append((row.phone, "Contact Phone (primary mobile)"))
	if contact.mobile_no:
		values.append((contact.mobile_no, "Contact mobile"))
	# Preserve source choices but suppress exact duplicates.
	unique: dict[str, str] = {}
	for phone, source in values:
		unique.setdefault(phone, source)
	return list(unique.items())


def _source_identity(
	doctype: str, name: str, company: str, *, include_unassigned_lead: bool = False
) -> tuple[str, list[tuple[str, str]], str | None]:
	row = _read_source(doctype, name, company, include_unassigned_lead=include_unassigned_lead)
	label = row.get("lead_name") or row.get("customer_name") or row.get("full_name") or name
	region = row.get("country")
	phones: list[tuple[str, str]] = []
	if doctype == "Lead":
		if row.get("company") and row.get("company") != company:
			raise CommandError("COMPANY_MISMATCH")
		if row.get("mobile_no"):
			phones.append((row["mobile_no"], "Lead mobile"))
	elif doctype == "Customer":
		if row.get("customer_primary_contact"):
			try:
				phones.extend(_phones_for_contact(row["customer_primary_contact"]))
			except CommandError:
				# A Customer may be readable while its linked Contact is not; do not disclose it.
				pass
		if not phones and row.get("mobile_no"):
			phones.append((row["mobile_no"], "Customer mobile summary"))
	elif doctype == "Contact":
		phones.extend(_phones_for_contact(name))
	elif doctype == "Sales Order":
		if row.get("company") != company or row.get("docstatus") != 1:
			raise CommandError("COMPANY_MISMATCH")
		if row.get("contact_person"):
			try:
				phones.extend(_phones_for_contact(row["contact_person"]))
			except CommandError:
				pass
		if not phones and row.get("customer"):
			try:
				customer = _read_source("Customer", row["customer"], company)
				if customer.get("customer_primary_contact"):
					phones.extend(_phones_for_contact(customer["customer_primary_contact"]))
				if not phones and customer.get("mobile_no"):
					phones.append((customer["mobile_no"], "Customer mobile summary"))
			except CommandError:
				pass
	return str(label), phones, region


def _normalise(phone: str, region: str | None) -> str | None:
	return to_e164(phone, region)


def source_preview(
	source_doctype: str, search: str = "", country_code: str = "", start: int = 0, page_length: int = 20
) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company = _company()
	_source_enabled(source_doctype)
	if (
		not isinstance(start, int)
		or start < 0
		or start > 10000
		or not isinstance(page_length, int)
		or not 1 <= page_length <= MAX_PREVIEW
	):
		raise CommandError("INVALID_INPUT")
	search = (search or "").strip()[:100]
	fields = SOURCE_FIELDS[source_doctype]
	label_field = {
		"Lead": "lead_name",
		"Customer": "customer_name",
		"Contact": "full_name",
		"Sales Order": "name",
	}[source_doctype]
	filters: list[list[Any]] = []
	if search:
		filters.append([source_doctype, label_field, "like", f"%{search}%"])
	if source_doctype == "Sales Order":
		filters.append([source_doctype, "company", "=", company])
	if source_doctype == "Sales Order":
		filters.append([source_doctype, "docstatus", "=", 1])
	or_filters = (
		[["Lead", "company", "=", company], ["Lead", "company", "is", "not set"]]
		if source_doctype == "Lead"
		else None
	)
	rows = frappe.get_list(
		source_doctype,
		filters=filters,
		or_filters=or_filters,
		fields=list(fields),
		limit_start=start,
		limit=page_length,
		order_by="modified desc",
	)
	items = []
	for row in rows:
		if source_doctype == "Lead" and row.get("company") and row.get("company") != company:
			continue
		label, phones, source_region = _source_identity(source_doctype, row["name"], company)
		region = (country_code or "").upper()
		options = []
		for raw_phone, source in phones:
			e164 = _normalise(raw_phone, region)
			if e164:
				options.append({"phone": raw_phone, "phone_e164": e164, "source": source})
		items.append(
			{
				"name": row["name"],
				"label": label,
				"phones": options,
				"requires_phone_choice": len(options) > 1,
				"unassigned_lead": source_doctype == "Lead" and not row.get("company"),
				"source_country_available": bool(source_region),
			}
		)
	return {"items": items, "start": start, "page_length": page_length, "has_more": len(rows) == page_length}


def source_options() -> list[str]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	_company()
	return sorted(frappe.get_all("WA Source Type", filters={"parent": "WA Settings"}, pluck="source_doctype"))


def add_source(
	source_doctype: str,
	source_name: str,
	selected_phone: str,
	country_code: str,
	include_unassigned_lead: bool = False,
) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company = _company()
	label, phones, _source_region = _source_identity(
		source_doctype, source_name, company, include_unassigned_lead=include_unassigned_lead
	)
	if source_doctype == "Lead":
		lead = _read_source("Lead", source_name, company, include_unassigned_lead=include_unassigned_lead)
		if not lead.get("company") and not include_unassigned_lead:
			raise CommandError("INVALID_INPUT", "include_unassigned_lead")
	choices = [(raw, _normalise(raw, country_code)) for raw, phone_source in phones]
	selected = next(((raw, e164) for raw, e164 in choices if raw == selected_phone), None)
	if not selected or not selected[1]:
		raise CommandError("INVALID_INPUT", "selected_phone")
	raw_phone, e164 = selected
	assert e164
	if is_identity_suppressed(company, e164, lock=True):
		# Do not reveal whether an address is present in the minimised suppression set.
		raise CommandError("READINESS_FAILED")
	frappe.db.savepoint("wa_contact_source")
	contact_name = frappe.db.get_value("WA Contact", {"company": company, "phone_e164": e164}, "name")
	created = not contact_name
	if created:
		doc = frappe.get_doc(
			{
				"doctype": "WA Contact",
				"company": company,
				"phone_e164": e164,
				"display_name": label or e164,
				"consent_status": "Unknown",
				"suppressed": 0,
				"archived": 0,
				"source_links": [
					{
						"source_doctype": source_doctype,
						"source_name": source_name,
						"selected_phone": raw_phone,
						"included_unassigned_lead": bool(
							source_doctype == "Lead"
							and not frappe.db.get_value("Lead", source_name, "company")
						),
						"selected_by": frappe.session.user,
						"selected_at": datetime.now(UTC).replace(tzinfo=None),
					}
				],
			}
		)
		doc.flags.wa_source_command = True
		try:
			doc.insert(ignore_permissions=True)
			contact_name = doc.name
		except (frappe.DuplicateEntryError, frappe.UniqueValidationError):
			frappe.db.rollback(save_point="wa_contact_source")
			contact_name = frappe.db.get_value("WA Contact", {"company": company, "phone_e164": e164}, "name")
			if not contact_name:
				# A concurrent unique winner can be invisible inside this transaction's
				# repeatable-read snapshot. The unique index prevents duplication; retry
				# in a fresh request transaction to resolve the canonical record.
				raise CommandError("PERSISTENCE_UNAVAILABLE")
			contact = frappe.get_doc("WA Contact", contact_name)
			if not any(
				link.source_doctype == source_doctype and link.source_name == source_name
				for link in contact.source_links
			):
				contact.append(
					"source_links",
					{
						"source_doctype": source_doctype,
						"source_name": source_name,
						"selected_phone": raw_phone,
						"included_unassigned_lead": bool(
							source_doctype == "Lead"
							and not frappe.db.get_value("Lead", source_name, "company")
						),
						"selected_by": frappe.session.user,
						"selected_at": datetime.now(UTC).replace(tzinfo=None),
					},
				)
				contact.flags.wa_source_command = True
				contact.save(ignore_permissions=True)
	else:
		contact = frappe.get_doc("WA Contact", contact_name)
		if not any(
			link.source_doctype == source_doctype and link.source_name == source_name
			for link in contact.source_links
		):
			contact.append(
				"source_links",
				{
					"source_doctype": source_doctype,
					"source_name": source_name,
					"selected_phone": raw_phone,
					"included_unassigned_lead": bool(
						source_doctype == "Lead" and not frappe.db.get_value("Lead", source_name, "company")
					),
					"selected_by": frappe.session.user,
					"selected_at": datetime.now(UTC).replace(tzinfo=None),
				},
			)
			contact.flags.wa_source_command = True
			contact.save(ignore_permissions=True)
	return {"contact": contact_name, "created": created, "phone_e164": e164}
