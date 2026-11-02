"""Frappe persistence adapter for bounded permission-aware audience queries."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any

import frappe

from tag_marketing.domain.audience_filters import SOURCE_TYPES

SCAN_BATCH_SIZE = 1000
CANDIDATE_COUNT_LIMIT = 50_001
SOURCE_ATTRIBUTE_COLUMNS = {
	"Lead.country": ("Lead", "country"),
	"Lead.company": ("Lead", "company"),
	"Customer.customer_name": ("Customer", "customer_name"),
	"Contact.full_name": ("Contact", "full_name"),
	"Sales Order.company": ("Sales Order", "company"),
	"Sales Order.docstatus": ("Sales Order", "docstatus"),
}


def _predicate(rule: dict[str, Any]) -> tuple[str, list[Any]]:
	field, operator, value = rule["field"], rule["operator"], rule["value"]
	if field in {"language", "archived"}:
		column = "c.language" if field == "language" else "c.archived"
		if operator == "equals":
			return f"{column} = %s", [int(value) if field == "archived" else value]
		if operator == "not_equals":
			return f"{column} != %s", [value]
		if operator in {"in", "not_in"}:
			marks = ", ".join(["%s"] * len(value))
			negation = " NOT" if operator == "not_in" else ""
			return f"{column}{negation} IN ({marks})", value
	if field in {"tag", "source_type"}:
		table, child_field = (
			("tabWA Contact Tag", "tag") if field == "tag" else ("tabWA Source Link", "source_doctype")
		)
		values = [value] if operator in {"equals", "not_equals"} else value
		marks = ", ".join(["%s"] * len(values))
		negated = operator in {"not_equals", "not_in"}
		return (
			f"{'NOT ' if negated else ''}EXISTS (SELECT 1 FROM `{table}` x "
			f"WHERE x.parent = c.name AND x.`{child_field}` IN ({marks}))",
			values,
		)
	if field in SOURCE_ATTRIBUTE_COLUMNS:
		doctype, column = SOURCE_ATTRIBUTE_COLUMNS[field]
		values = [value] if operator in {"equals", "not_equals"} else value
		marks = ", ".join(["%s"] * len(values))
		negated = operator in {"not_equals", "not_in"}
		return (
			f"{'NOT ' if negated else ''}EXISTS "
			f"(SELECT 1 FROM `tabWA Source Link` x JOIN `tab{doctype}` s ON s.name = x.source_name "
			f"WHERE x.parent = c.name AND x.source_doctype = %s AND s.`{column}` IN ({marks}))",
			[doctype, *values],
		)
	if operator == "between":
		return "DATE(c.creation) BETWEEN %s AND %s", value
	comparison = {
		"before": "<",
		"after": ">",
		"on_or_before": "<=",
		"on_or_after": ">=",
	}[operator]
	return f"DATE(c.creation) {comparison} %s", [value]


def _group(group: dict[str, Any]) -> tuple[str, list[Any]]:
	parts: list[str] = []
	params: list[Any] = []
	for rule in group["rules"]:
		sql, values = _predicate(rule)
		parts.append(f"({sql})")
		params.extend(values)
	for nested in group["groups"]:
		sql, values = _group(nested)
		parts.append(f"({sql})")
		params.extend(values)
	if not parts:
		return "1 = 1", []
	return f" {group['logic'].upper()} ".join(parts), params


def _where(
	company: str, filters: dict[str, Any], contacts: list[str], tags: list[str], *, eligible: bool
) -> tuple[str, list[Any]]:
	user_sql, params = _group(filters)
	clauses = ["c.company = %s", f"({user_sql})"]
	values: list[Any] = [company, *params]
	if eligible:
		clauses.append("c.consent_status = 'Granted' AND c.suppressed = 0 AND c.archived = 0")
	if contacts:
		clauses.append(f"c.name NOT IN ({', '.join(['%s'] * len(contacts))})")
		values.extend(contacts)
	if tags:
		clauses.append(
			"NOT EXISTS (SELECT 1 FROM `tabWA Contact Tag` ex "
			f"WHERE ex.parent = c.name AND ex.tag IN ({', '.join(['%s'] * len(tags))}))"
		)
		values.extend(tags)
	return " AND ".join(clauses), values


def _permitted_names(names: list[str], actor: str) -> set[str]:
	"""Recheck source permissions in bounded chunks; never trust old source links."""
	if not names:
		return set()
	links = frappe.db.sql(
		"""SELECT parent, source_doctype, source_name FROM `tabWA Source Link`
		WHERE parent IN %(names)s ORDER BY parent""",
		{"names": tuple(names)},
		as_dict=True,
	)
	by_contact: dict[str, list[tuple[str, str]]] = {}
	by_type: dict[str, set[str]] = {}
	for link in links:
		by_contact.setdefault(link.parent, []).append((link.source_doctype, link.source_name))
		if link.source_doctype not in SOURCE_TYPES:
			continue
		by_type.setdefault(link.source_doctype, set()).add(link.source_name)
	allowed: dict[str, set[str]] = {}
	for doctype, source_names in by_type.items():
		previous_user = frappe.session.user
		frappe.set_user(actor)
		try:
			allowed[doctype] = set(
				frappe.get_list(
					doctype,
					filters={"name": ["in", sorted(source_names)]},
					pluck="name",
					limit=len(source_names),
				)
			)
		except frappe.PermissionError:
			allowed[doctype] = set()
		finally:
			if previous_user != actor:
				frappe.set_user(previous_user)
	return {
		name
		for name in names
		if not by_contact.get(name)
		or all(source_name in allowed.get(doctype, set()) for doctype, source_name in by_contact[name])
	}


def iterate_contacts(
	company: str,
	filters: dict[str, Any],
	contacts: list[str],
	tags: list[str],
	actor: str,
	*,
	eligible: bool,
	chunk_size: int,
	on_batch: Callable[[int], None] | None = None,
) -> Iterator[dict[str, Any]]:
	"""Yield stable name-keyset rows; each SQL and source-permission page is bounded."""
	where, params = _where(company, filters, contacts, tags, eligible=eligible)
	last_name = ""
	scanned = 0
	while True:
		rows = frappe.db.sql(
			f"""SELECT c.name, c.phone_e164, c.display_name, c.language, c.consent_status,
			c.suppressed, c.archived, c.creation FROM `tabWA Contact` c
			WHERE {where} AND c.name > %s ORDER BY c.name ASC LIMIT %s""",
			[*params, last_name, chunk_size],
			as_dict=True,
		)
		if not rows:
			return
		last_name = rows[-1].name
		scanned += len(rows)
		if on_batch:
			on_batch(scanned)
		permitted = _permitted_names([row.name for row in rows], actor)
		for row in rows:
			if row.name in permitted:
				yield row


def count_candidates(company: str, filters: dict[str, Any], contacts: list[str], tags: list[str]) -> int:
	"""Return a permission-blind upper bound used only to choose sync vs queued preview."""
	where, params = _where(company, filters, contacts, tags, eligible=False)
	rows = frappe.db.sql(
		f"SELECT COUNT(*) FROM (SELECT c.name FROM `tabWA Contact` c WHERE {where} LIMIT %s) bounded_candidates",
		[*params, CANDIDATE_COUNT_LIMIT],
	)
	return int(rows[0][0])


def preview_contacts(
	company: str,
	filters: dict[str, Any],
	contacts: list[str],
	tags: list[str],
	actor: str,
	cursor: str,
	limit: int,
) -> tuple[list[dict[str, Any]] | None, bool]:
	"""Read a permission-safe bounded keyset sample after the supplied contact key."""
	where, params = _where(company, filters, contacts, tags, eligible=True)
	if cursor:
		if not frappe.db.exists("WA Contact", {"name": cursor, "company": company}):
			return None, False
		params.append(cursor)
		cursor_clause = " AND c.name > %s"
	else:
		cursor_clause = ""
	items: list[dict[str, Any]] = []
	last_name = ""
	while len(items) < limit + 1:
		rows = frappe.db.sql(
			f"""SELECT c.name, c.display_name, c.phone_e164, c.language FROM `tabWA Contact` c
			WHERE {where}{cursor_clause} AND c.name > %s ORDER BY c.name ASC LIMIT %s""",
			[*params, last_name, min(SCAN_BATCH_SIZE, limit + 1 - len(items))],
			as_dict=True,
		)
		if not rows:
			break
		last_name = rows[-1].name
		permitted = _permitted_names([row.name for row in rows], actor)
		items.extend(
			{
				"name": row.name,
				"display_name": row.display_name,
				"phone": row.phone_e164,
				"language": row.language,
			}
			for row in rows
			if row.name in permitted
		)
	has_more = len(items) > limit
	return items[:limit], has_more
