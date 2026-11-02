"""Versioned, bounded audience filter language. This module has no Frappe dependency."""

from __future__ import annotations

from datetime import date
from typing import Any

FILTER_VERSION = 1
MAX_PREDICATES = 20
MAX_DEPTH = 3
MAX_GROUPS = 20
MAX_VALUE_LENGTH = 100
SOURCE_TYPES = frozenset({"Lead", "Customer", "Contact", "Sales Order"})
SOURCE_ATTRIBUTES = frozenset(
	{
		"Lead.country",
		"Lead.company",
		"Customer.customer_name",
		"Contact.full_name",
		"Sales Order.company",
		"Sales Order.docstatus",
	}
)
INTEGER_SOURCE_ATTRIBUTES = frozenset({"Sales Order.docstatus"})
FILTER_FIELDS = frozenset({"tag", "language", "source_type", "created_on", "archived", *SOURCE_ATTRIBUTES})

_OPERATORS: dict[str, frozenset[str]] = {
	"tag": frozenset({"equals", "not_equals", "in", "not_in"}),
	"language": frozenset({"equals", "not_equals", "in", "not_in"}),
	"source_type": frozenset({"equals", "not_equals", "in", "not_in"}),
	**{field: frozenset({"equals", "not_equals", "in", "not_in"}) for field in SOURCE_ATTRIBUTES},
	"created_on": frozenset({"before", "after", "on_or_before", "on_or_after", "between"}),
	"archived": frozenset({"equals"}),
}


class InvalidAudienceFilters(ValueError):
	"""Raised when an audience AST is malformed or outside its bounded grammar."""


def validate_filter_ast(value: Any) -> dict[str, Any]:
	"""Validate and return a normalized v1 filter AST.

	Shape: {version: 1, logic: and|or, rules: [...], groups: [...]}.
	The limits count predicates across the complete tree, before any query is run.
	"""
	if (
		not isinstance(value, dict)
		or set(value) != {"version", "logic", "rules", "groups"}
		or value.get("version") != FILTER_VERSION
	):
		raise InvalidAudienceFilters("unsupported filter version")
	count = [0]
	return _validate_group(
		{"logic": value["logic"], "rules": value["rules"], "groups": value["groups"]},
		1,
		count,
	)


def _validate_group(value: Any, depth: int, count: list[int]) -> dict[str, Any]:
	if depth > MAX_DEPTH or not isinstance(value, dict) or set(value) != {"logic", "rules", "groups"}:
		raise InvalidAudienceFilters("group depth or shape is invalid")
	logic = value.get("logic")
	rules = value.get("rules")
	groups = value.get("groups")
	if logic not in {"and", "or"} or not isinstance(rules, list) or not isinstance(groups, list):
		raise InvalidAudienceFilters("group shape is invalid")
	if len(rules) + len(groups) > MAX_GROUPS:
		raise InvalidAudienceFilters("group is too large")
	normalized_rules = [_validate_rule(rule, count) for rule in rules]
	normalized_groups = [_validate_group(group, depth + 1, count) for group in groups]
	if not normalized_rules and not normalized_groups:
		# An empty root means match all; empty nested groups are ambiguous and rejected.
		if depth > 1:
			raise InvalidAudienceFilters("empty nested group")
	return {"logic": logic, "rules": normalized_rules, "groups": normalized_groups}


def _validate_rule(value: Any, count: list[int]) -> dict[str, Any]:
	if not isinstance(value, dict) or set(value) != {"field", "operator", "value"}:
		raise InvalidAudienceFilters("predicate shape is invalid")
	field = value.get("field")
	operator = value.get("operator")
	if field not in FILTER_FIELDS or operator not in _OPERATORS[field]:
		raise InvalidAudienceFilters("field or operator is not allowed")
	count[0] += 1
	if count[0] > MAX_PREDICATES:
		raise InvalidAudienceFilters("too many predicates")
	if field == "created_on":
		if operator == "between":
			bounds = value.get("value")
			if not isinstance(bounds, list) or len(bounds) != 2:
				raise InvalidAudienceFilters("date range requires two values")
			start, end = (_date_string(item) for item in bounds)
			if end < start:
				raise InvalidAudienceFilters("date range is reversed")
			return {"field": field, "operator": operator, "value": [start, end]}
		return {"field": field, "operator": operator, "value": _date_string(value.get("value"))}
	if field == "archived":
		if not isinstance(value.get("value"), bool):
			raise InvalidAudienceFilters("archived requires a boolean")
		return {"field": field, "operator": operator, "value": value["value"]}
	item = value.get("value")
	if operator in {"in", "not_in"}:
		if not isinstance(item, list) or not 1 <= len(item) <= 20:
			raise InvalidAudienceFilters("list value must contain 1 to 20 items")
		values: list[Any] = (
			[_integer_source_value(field, item_value) for item_value in item]
			if field in INTEGER_SOURCE_ATTRIBUTES
			else [_string(item_value) for item_value in item]
		)
		if field == "source_type" and any(item not in SOURCE_TYPES for item in values):
			raise InvalidAudienceFilters("source type is not allowed")
		if len(set(values)) != len(values):
			raise InvalidAudienceFilters("duplicate list values")
		return {"field": field, "operator": operator, "value": values}
	item = _integer_source_value(field, item) if field in INTEGER_SOURCE_ATTRIBUTES else _string(item)
	if field == "source_type" and item not in SOURCE_TYPES:
		raise InvalidAudienceFilters("source type is not allowed")
	return {"field": field, "operator": operator, "value": item}


def _string(value: Any) -> str:
	if not isinstance(value, str) or not value.strip() or len(value) > MAX_VALUE_LENGTH:
		raise InvalidAudienceFilters("value must be a non-empty short string")
	return value.strip()


def _integer_source_value(field: str, value: Any) -> int:
	if field != "Sales Order.docstatus" or isinstance(value, bool) or value not in {0, 1, 2}:
		raise InvalidAudienceFilters("integer source value is outside the supported range")
	return value


def _date_string(value: Any) -> str:
	if not isinstance(value, str):
		raise InvalidAudienceFilters("date must use ISO format")
	try:
		return date.fromisoformat(value).isoformat()
	except ValueError as error:
		raise InvalidAudienceFilters("date must use ISO format") from error
