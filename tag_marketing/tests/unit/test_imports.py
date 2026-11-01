"""Offline checks for CSV normalization and consent chronology."""

from datetime import UTC, datetime

from tag_marketing.domain.imports import effective_consent, import_hash, parse_csv, safe_csv_cell
from tag_marketing.tests.support.cases import OfflineTestCase


class TestImportRules(OfflineTestCase):
	def test_csv_projection_normalizes_phone_and_keeps_missing_consent_ineligible(self) -> None:
		mapping = {"columns": {"phone": "Mobile", "display_name": "Name"}, "default_country_code": "ZA"}
		rows, digest = parse_csv(b"Name,Mobile\nAda,0821234567\n", mapping)
		self.assertEqual(rows[0]["phone_e164"], "+27821234567")
		self.assertIsNone(rows[0]["consent_evidence"])
		self.assertEqual(len(digest), 64)

	def test_csv_requires_complete_explicit_evidence_mapping_and_rejects_bad_phone(self) -> None:
		with self.assertRaises(ValueError):
			parse_csv(
				b"Mobile,Date\n0821234567,2026-01-01\n",
				{"columns": {"phone": "Mobile", "consent_occurred_at": "Date"}, "default_country_code": "ZA"},
			)
		rows, _digest = parse_csv(
			b"Mobile\nnot-a-phone\n", {"columns": {"phone": "Mobile"}, "default_country_code": "ZA"}
		)
		self.assertEqual(rows[0]["error_code"], "INVALID_PHONE")

	def test_consent_chronology_ties_withdrawal_and_older_grant_cannot_reopen(self) -> None:
		at = datetime(2026, 10, 1, tzinfo=UTC)
		self.assertEqual(effective_consent([{"event_type": "Granted", "occurred_at": at}]), "Granted")
		self.assertEqual(
			effective_consent(
				[{"event_type": "Withdrawn", "occurred_at": at}, {"event_type": "Granted", "occurred_at": at}]
			),
			"Withdrawn",
		)
		self.assertEqual(
			effective_consent(
				[
					{"event_type": "Withdrawn", "occurred_at": at},
					{"event_type": "Granted", "occurred_at": datetime(2026, 9, 1, tzinfo=UTC)},
				]
			),
			"Withdrawn",
		)

	def test_hash_binds_file_bytes_and_mapping(self) -> None:
		mapping = {"columns": {"phone": "Mobile"}, "default_country_code": "ZA"}
		self.assertNotEqual(import_hash(b"one", mapping), import_hash(b"two", mapping))
		self.assertNotEqual(
			import_hash(b"one", mapping),
			import_hash(b"one", {"columns": {"phone": "Phone"}, "default_country_code": "ZA"}),
		)

	def test_csv_diagnostics_neutralize_formula_prefixes(self) -> None:
		for value in ("=1+1", "+SUM(A1:A2)", "-1+2", "@cmd", "\t=1"):
			self.assertTrue(safe_csv_cell(value).startswith("'"))
		self.assertEqual(safe_csv_cell("row 2"), "row 2")
