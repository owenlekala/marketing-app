import unittest

from tag_marketing.application.templates import _sniff_media
from tag_marketing.domain.templates import content_hash, render_preview, validate_definition


class TestTemplateDefinitions(unittest.TestCase):
	def setUp(self) -> None:
		self.components = [
			{"type": "HEADER", "format": "TEXT", "text": "Hello"},
			{"type": "BODY", "text": "Hi {{1}}, your order is {{2}}."},
			{"type": "FOOTER", "text": "Reply STOP to opt out"},
		]

	def test_hash_is_canonical_and_stable(self) -> None:
		self.assertEqual(
			content_hash("order_update", "en_US", "Utility", self.components),
			content_hash("order_update", "en_US", "Utility", list(self.components)),
		)
		self.assertNotEqual(
			content_hash("order_update", "en_US", "Utility", self.components),
			content_hash("order_update", "en_US", "Utility", self.components, "a" * 64),
		)

	def test_preview_substitutes_only_positional_sample_values(self) -> None:
		preview = render_preview(self.components, ["Ava", "ready"])
		self.assertEqual(preview["body"], "Hi Ava, your order is ready.")
		self.assertEqual(
			preview["components"][1]["example"],
			{"body_text": [["Example 1", "Example 2"]]},
		)

	def test_rejects_missing_or_noncontiguous_placeholders(self) -> None:
		for components in (
			[{"type": "FOOTER", "text": "footer only"}],
			[{"type": "BODY", "text": "Hello {{2}}"}],
			[{"type": "BODY", "text": "Hello {{1}} {{3}}"}],
			[{"type": "BODY", "text": "Hello {{0}}"}],
			[{"type": "BODY", "text": "Hello {{name}}"}],
			[{"type": "BODY", "text": "Hello {{1"}],
			[{"type": "BODY", "text": "Hello 1}}"}],
		):
			with self.subTest(components=components), self.assertRaises(ValueError):
				validate_definition("sample", "en_US", "Marketing", components)

	def test_rejects_unknown_components_fields_and_authentication_editing(self) -> None:
		for category, component in (
			("Authentication", self.components),
			("Marketing", [{"type": "BODY", "text": "Hi", "url": "https://bad.invalid"}]),
			("Marketing", [{"type": "CAROUSEL", "cards": []}]),
		):
			with self.subTest(category=category, component=component), self.assertRaises(ValueError):
				validate_definition("sample", "en_US", category, component)

	def test_rejects_insecure_or_arbitrary_button_targets(self) -> None:
		components = [
			{"type": "BODY", "text": "Hello"},
			{"type": "BUTTONS", "buttons": [{"type": "URL", "text": "Visit", "url": "http://bad.invalid"}]},
		]
		with self.assertRaises(ValueError):
			validate_definition("sample", "en_US", "Marketing", components)

	def test_media_sniffing_rejects_jpeg_signature_wrappers_without_structure(self) -> None:
		self.assertIsNone(_sniff_media(b"\xff\xd8\xffarbitrary bytes\xff\xd9"))

	def test_media_sniffing_accepts_structurally_valid_minimal_jpeg(self) -> None:
		jpeg = (
			b"\xff\xd8"
			+ b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
			+ b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
			+ b"\x00\xff\xd9"
		)
		self.assertEqual(_sniff_media(jpeg), "image/jpeg")

	def test_media_sniffing_rejects_trailing_bytes_after_jpeg_end(self) -> None:
		jpeg = (
			b"\xff\xd8"
			+ b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
			+ b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
			+ b"\x00\xff\xd9junk"
		)
		self.assertIsNone(_sniff_media(jpeg))


if __name__ == "__main__":
	unittest.main()
