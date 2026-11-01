"""Phone identity normalization uses explicit regions and valid E.164 output."""

import unittest

from tag_marketing.domain.phones import to_e164


class TestPhoneNormalization(unittest.TestCase):
	def test_requires_explicit_region_for_local_numbers(self) -> None:
		self.assertIsNone(to_e164("082 123 4567", None))
		self.assertEqual(to_e164("082 123 4567", "ZA"), "+27821234567")

	def test_international_number_does_not_depend_on_region(self) -> None:
		self.assertEqual(to_e164("+27821234567", "GB"), "+27821234567")

	def test_invalid_and_landline_like_values_fail_validation(self) -> None:
		self.assertIsNone(to_e164("not a phone", "ZA"))
		self.assertIsNone(to_e164("010 123 4567", "ZA"))
