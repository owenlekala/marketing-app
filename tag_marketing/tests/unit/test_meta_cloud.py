import hashlib
import json
import unittest

from tag_marketing.application.ports import TransportResponse
from tag_marketing.infrastructure.meta_cloud import (
	FailureKind,
	MetaCloudAPI,
	MetaConfig,
	MetaCredentials,
	ProviderFailure,
)
from tag_marketing.tests.support.cases import OfflineTestCase
from tag_marketing.tests.support.fakes import FakeProvider


def response(status: int, body: dict[str, object] | bytes) -> TransportResponse:
	encoded = body if isinstance(body, bytes) else json.dumps(body).encode()
	return TransportResponse(status, encoded)


def adapter(outcomes: list[TransportResponse | Exception]) -> tuple[MetaCloudAPI, FakeProvider]:
	transport = FakeProvider(outcomes)
	return (
		MetaCloudAPI(
			MetaConfig(api_version="v26.0", waba_id="synthetic-waba"),
			MetaCredentials(access_token="synthetic-access-token", app_secret="synthetic-app-secret"),
			transport,
		),
		transport,
	)


class TestMetaCloudContract(OfflineTestCase):
	def test_graph_version_is_explicitly_pinned_and_unknown_version_fails_closed(self) -> None:
		with self.assertRaises(ProviderFailure) as caught:
			MetaCloudAPI(
				MetaConfig(api_version="v27.0", waba_id="synthetic-waba"),
				MetaCredentials("token", "secret"),
				FakeProvider([]),
			)
		self.assertEqual(caught.exception.kind, FailureKind.UNSUPPORTED_VERSION)

	def test_validation_and_number_template_reads_use_documented_waba_edges(self) -> None:
		api, transport = adapter(
			[
				response(200, {"id": "synthetic-waba", "name": "Synthetic Business"}),
				response(
					200,
					{
						"data": [
							{
								"id": "synthetic-phone-id",
								"display_phone_number": "+27115550123",
								"verified_name": "Synthetic",
								"quality_rating": "GREEN",
							}
						],
						"paging": {
							"next": "https://graph.facebook.com/v26.0/synthetic-waba/phone_numbers?after=synthetic-cursor",
							"cursors": {"after": "synthetic-cursor"},
						},
					},
				),
				response(
					200, {"data": [{"id": "synthetic-phone-id-2", "display_phone_number": "+27115550124"}]}
				),
				response(
					200,
					{
						"data": [
							{
								"id": "synthetic-template-id",
								"name": "welcome",
								"language": "en_ZA",
								"category": "UTILITY",
								"status": "APPROVED",
								"components": [{"type": "BODY", "text": "Synthetic"}],
							}
						]
					},
				),
			]
		)
		self.assertEqual(api.validate_connection()["id"], "synthetic-waba")
		numbers = api.list_numbers()
		self.assertEqual(numbers.items[0].provider_phone_id, "synthetic-phone-id")
		self.assertEqual(numbers.next_cursor, "synthetic-cursor")
		self.assertEqual(
			api.list_numbers(cursor=numbers.next_cursor).items[0].provider_phone_id, "synthetic-phone-id-2"
		)
		self.assertEqual(api.list_templates().items[0].status, "APPROVED")
		self.assertIn("/v26.0/synthetic-waba/phone_numbers?", transport.calls[1][1])
		self.assertIn("after=synthetic-cursor", transport.calls[2][1])
		self.assertIn("/v26.0/synthetic-waba/message_templates?", transport.calls[3][1])
		self.assertTrue(
			all(call[3]["Authorization"] == "Bearer synthetic-access-token" for call in transport.calls)
		)
		transport.assert_consumed()

	def test_wrong_waba_and_expired_permission_are_classified_without_body_leak(self) -> None:
		api, transport = adapter([response(200, {"id": "another-waba", "name": "Synthetic"})])
		with self.assertRaises(ProviderFailure) as wrong_account:
			api.validate_connection()
		self.assertEqual(wrong_account.exception.kind, FailureKind.WRONG_ACCOUNT)
		transport.assert_consumed()

		api, transport = adapter([response(401, {"error": {"code": 190, "message": "private-token-detail"}})])
		with self.assertRaises(ProviderFailure) as expired:
			api.validate_connection()
		self.assertEqual(expired.exception.kind, FailureKind.INVALID_CREDENTIAL)
		self.assertNotIn("private-token-detail", str(expired.exception))
		transport.assert_consumed()

	def test_template_create_uses_official_waba_endpoint_and_only_exposes_safe_result(self) -> None:
		api, transport = adapter([response(200, {"id": "synthetic-template-id", "status": "PENDING"})])
		result = api.create_template(
			name="synthetic_offer",
			language="en_ZA",
			category="MARKETING",
			components=({"type": "BODY", "text": "Synthetic offer {{1}}"},),
		)
		self.assertEqual(result.provider_template_id, "synthetic-template-id")
		self.assertEqual(result.status, "PENDING")
		method, url, body, _headers = transport.calls[0]
		self.assertEqual(method, "POST")
		self.assertEqual(url, "https://graph.facebook.com/v26.0/synthetic-waba/message_templates")
		self.assertEqual(json.loads(body)["category"], "MARKETING")
		transport.assert_consumed()

		api, transport = adapter([])
		with self.assertRaises(ValueError):
			api.create_template(
				name="Synthetic Offer",
				language="en_ZA",
				category="AUTHENTICATION",
				components=({"type": "BODY", "text": "Synthetic"},),
			)
		transport.assert_consumed()

		api, transport = adapter([response(200, b"not-json")])
		with self.assertRaises(ProviderFailure) as uncertain:
			api.create_template(
				name="synthetic_offer",
				language="en_ZA",
				category="MARKETING",
				components=({"type": "BODY", "text": "Synthetic"},),
			)
		self.assertEqual(uncertain.exception.kind, FailureKind.UNKNOWN_OUTCOME)
		transport.assert_consumed()

	def test_send_acceptance_is_distinct_from_delivery_and_ambiguous_results_stay_unknown(self) -> None:
		api, transport = adapter(
			[response(200, {"messages": [{"id": "synthetic-wamid", "message_status": "accepted"}]})]
		)
		result = api.submit_message("synthetic-phone-id", {"messaging_product": "whatsapp", "type": "text"})
		self.assertEqual(result.provider_message_id, "synthetic-wamid")
		self.assertTrue(result.accepted)
		transport.assert_consumed()

		for uncertain in (
			TimeoutError("secret-token-must-not-escape"),
			response(503, {"error": {"code": 1, "message": "private response"}}),
			response(200, {"messages": []}),
		):
			api, transport = adapter([uncertain])
			with self.assertRaises(ProviderFailure) as caught:
				api.submit_message("synthetic-phone-id", {"messaging_product": "whatsapp", "type": "text"})
			self.assertEqual(caught.exception.kind, FailureKind.UNKNOWN_OUTCOME)
			self.assertNotIn("secret-token", str(caught.exception))
			transport.assert_consumed()

	def test_explicit_throttle_and_permanent_rejection_are_not_confused_with_unknown(self) -> None:
		for scripted, expected in (
			(response(429, {"error": {"code": 4}}), FailureKind.RATE_LIMITED),
			(response(400, {"error": {"code": 100, "message": "private"}}), FailureKind.REJECTED),
		):
			api, transport = adapter([scripted])
			with self.assertRaises(ProviderFailure) as caught:
				api.submit_message("synthetic-phone-id", {"messaging_product": "whatsapp", "type": "text"})
			self.assertEqual(caught.exception.kind, expected)
			transport.assert_consumed()

	def test_media_download_requires_meta_host_allowed_type_size_and_matching_hash(self) -> None:
		body = b"synthetic private media bytes"
		digest = hashlib.sha256(body).hexdigest()
		api, transport = adapter(
			[
				response(
					200,
					{
						"url": "https://lookaside.fbsbx.com/synthetic",
						"mime_type": "image/jpeg",
						"sha256": digest,
						"file_size": len(body),
					},
				),
				response(200, body),
			]
		)
		asset = api.retrieve_media("synthetic-media-id")
		self.assertEqual(asset.content, body)
		self.assertEqual(asset.sha256, digest)
		self.assertEqual(transport.calls[1][0], "GET")
		self.assertEqual(transport.calls[1][1], "https://lookaside.fbsbx.com/synthetic")
		transport.assert_consumed()

		api, transport = adapter(
			[
				response(
					200, {"url": "https://attacker.invalid/file", "mime_type": "image/jpeg", "sha256": digest}
				)
			]
		)
		with self.assertRaises(ProviderFailure) as unsafe_url:
			api.retrieve_media("synthetic-media-id")
		self.assertEqual(unsafe_url.exception.kind, FailureKind.INVALID_RESPONSE)
		self.assertEqual(len(transport.calls), 1)
		transport.assert_consumed()

		api, transport = adapter(
			[
				response(
					200,
					{
						"url": "https://lookaside.fbsbx.com/synthetic",
						"mime_type": "application/x-executable",
						"sha256": digest,
					},
				)
			]
		)
		with self.assertRaises(ProviderFailure) as unsupported:
			api.retrieve_media("synthetic-media-id")
		self.assertEqual(unsupported.exception.kind, FailureKind.UNSUPPORTED_MEDIA)
		self.assertEqual(len(transport.calls), 1)
		transport.assert_consumed()

		api, transport = adapter(
			[
				response(
					200,
					{
						"url": "https://lookaside.fbsbx.com/synthetic",
						"mime_type": "image/jpeg",
						"sha256": digest,
						"file_size": 16 * 1024 * 1024 + 1,
					},
				)
			]
		)
		with self.assertRaises(ProviderFailure) as oversized:
			api.retrieve_media("synthetic-media-id")
		self.assertEqual(oversized.exception.kind, FailureKind.UNSUPPORTED_MEDIA)
		self.assertEqual(len(transport.calls), 1)
		transport.assert_consumed()

	def test_large_response_and_invalid_identifiers_never_reach_transport(self) -> None:
		api, transport = adapter([])
		with self.assertRaises(ValueError):
			api.submit_message("synthetic-phone-id/../secret", {"messaging_product": "whatsapp"})
		transport.assert_consumed()

		api, transport = adapter([TransportResponse(200, b" " * (8 * 1024 * 1024 + 1))])
		with self.assertRaises(ProviderFailure):
			api.validate_connection()
		transport.assert_consumed()


if __name__ == "__main__":
	unittest.main()
