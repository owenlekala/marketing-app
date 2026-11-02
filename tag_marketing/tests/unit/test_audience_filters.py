"""Pure tests for the versioned bounded audience filter language."""

from typing import Any

from tag_marketing.domain.audience_filters import InvalidAudienceFilters, validate_filter_ast
from tag_marketing.tests.support.cases import OfflineTestCase


class TestAudienceFilterAst(OfflineTestCase):
	def test_valid_filter_ast_normalizes_values_and_preserves_groups(self) -> None:
		filters = validate_filter_ast(
			{
				"version": 1,
				"logic": "and",
				"rules": [{"field": "language", "operator": "equals", "value": " en "}],
				"groups": [
					{
						"logic": "or",
						"rules": [{"field": "source_type", "operator": "in", "value": ["Lead", "Customer"]}],
						"groups": [],
					}
				],
			}
		)
		self.assertEqual(filters["rules"][0]["value"], "en")
		self.assertEqual(filters["groups"][0]["rules"][0]["value"], ["Lead", "Customer"])

	def test_arbitrary_keys_fields_operators_and_source_types_are_rejected(self) -> None:
		base = {"version": 1, "logic": "and", "rules": [], "groups": []}
		changes: list[dict[str, Any]] = [
			{"unexpected": "anything"},
			{"rules": [{"field": "phone_e164", "operator": "equals", "value": "+27821234567"}]},
			{"rules": [{"field": "language", "operator": "sql", "value": "en"}]},
			{"rules": [{"field": "source_type", "operator": "equals", "value": "User"}]},
		]
		for change in changes:
			with self.subTest(change=change), self.assertRaises(InvalidAudienceFilters):
				validate_filter_ast({**base, **change})

	def test_predicate_and_depth_budgets_are_enforced(self) -> None:
		rule = {"field": "language", "operator": "equals", "value": "en"}
		too_many = {"version": 1, "logic": "and", "rules": [rule] * 21, "groups": []}
		with self.assertRaises(InvalidAudienceFilters):
			validate_filter_ast(too_many)
		deep: dict[str, Any] = {"logic": "and", "rules": [], "groups": []}
		for _ in range(3):
			deep = {"logic": "and", "rules": [], "groups": [deep]}
		with self.assertRaises(InvalidAudienceFilters):
			validate_filter_ast({"version": 1, **deep})

	def test_numeric_source_attributes_keep_their_field_type(self) -> None:
		valid: dict[str, Any] = {
			"version": 1,
			"logic": "and",
			"rules": [{"field": "Sales Order.docstatus", "operator": "equals", "value": 1}],
			"groups": [],
		}
		self.assertEqual(validate_filter_ast(valid)["rules"][0]["value"], 1)
		for value in ("1", True, 3):
			invalid = {**valid, "rules": [{**valid["rules"][0], "value": value}]}
			with self.assertRaises(InvalidAudienceFilters):
				validate_filter_ast(invalid)
