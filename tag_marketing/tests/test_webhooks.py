"""Authenticated, durable callback tests through Frappe's actual WSGI route."""

import hashlib
import hmac
import json
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4

import frappe
from frappe.utils import get_test_client
from werkzeug.test import TestResponse

from tag_marketing.application.event_recovery import _recover_webhooks
from tag_marketing.application.webhook_processing import process_webhook_event
from tag_marketing.tests.support.integration import AppIntegrationTestCase
from tag_marketing.tests.support.persistence import raw

SECRET = "synthetic-webhook-secret-value"


class TestWebhookIntake(AppIntegrationTestCase):
	def setUp(self):
		super().setUp()
		frappe.set_user("Administrator")
		self.run_id = uuid4().hex
		self.company = f"_WA Webhook {self.run_id[:8]}"
		self.public_id = f"webhook-fixture-{self.run_id}"
		self.connection = f"_wa_webhook_connection_{self.run_id}"
		self.phone_id = str(int(self.run_id[:12], 16))
		self.previous_marketing_company = frappe.db.get_single_value("WA Settings", "marketing_company")
		raw(
			"Company",
			name=self.company,
			company_name=self.company,
			abbr=f"W{self.run_id[:4].upper()}",
			country="South Africa",
			default_currency="ZAR",
		)
		frappe.db.set_single_value("WA Settings", "marketing_company", self.company)
		raw(
			"WA Connection",
			name=self.connection,
			company=self.company,
			connection_name="Webhook fixture",
			public_id=self.public_id,
			meta_app_id=str(int(self.run_id[12:20], 16)),
			waba_id=str(int(self.run_id[20:28], 16)),
			api_version="v26.0",
			status=(
				"Disabled"
				if self._testMethodName == "test_signed_receipt_is_durable_and_duplicate_envelope_is_safe"
				else "Ready"
			),
		)
		from frappe.utils.password import set_encrypted_password

		set_encrypted_password("WA Connection", self.connection, SECRET, "app_secret")
		set_encrypted_password("WA Connection", self.connection, "synthetic-verify-token", "verify_token")
		raw(
			"WA Sending Number",
			name=f"_wa_webhook_number_{self.run_id}",
			company=self.company,
			connection=self.connection,
			provider_phone_id=self.phone_id,
			status="Ready",
		)
		self.waba_id = frappe.db.get_value("WA Connection", self.connection, "waba_id")
		self.site = frappe.local.site
		self.client = get_test_client(use_cookies=False)
		self.base_url = f"http://{self.site}/api/method/tag_marketing.api.webhooks.receive"
		frappe.db.commit()

	def request(self, method, url, **kwargs):
		headers = kwargs.setdefault("headers", {})
		headers.setdefault("Host", self.site)
		kwargs.setdefault("environ_overrides", {"HTTP_HOST": self.site, "SERVER_NAME": self.site})
		try:
			return getattr(self.client, method)(url, **kwargs)
		finally:
			# The WSGI request initializes its own site context. Restore the integration
			# runner's disposable site and DB handle before touching test fixtures.
			frappe.init(self.site)
			frappe.connect()
			frappe.set_user("Administrator")

	def tearDown(self):
		frappe.db.rollback()
		frappe.set_user("Administrator")
		frappe.db.delete("WA Message Event", {"company": self.company})
		frappe.db.delete("WA Webhook Event", {"company": self.company})
		frappe.db.delete("WA Sending Number", {"company": self.company})
		frappe.db.delete("WA Connection", {"company": self.company})
		frappe.db.delete("__Auth", {"doctype": "WA Connection", "name": self.connection})
		frappe.db.delete("Company", {"name": self.company})
		frappe.db.set_single_value("WA Settings", "marketing_company", self.previous_marketing_company)
		frappe.db.commit()
		super().tearDown()

	def url(self, **query):
		return self.base_url + "?" + urlencode({"integration": self.public_id, **query})

	def signed_post(
		self, payload: bytes, *, signature_body: bytes | None = None, content_type="application/json"
	):
		signed = payload if signature_body is None else signature_body
		signature = "sha256=" + hmac.new(SECRET.encode(), signed, hashlib.sha256).hexdigest()
		return self.request(
			"post",
			self.url(),
			data=payload,
			headers={"Content-Type": content_type, "X-Hub-Signature-256": signature},
		)

	def response(self, payload: dict, *, public_id: str | None = None) -> TestResponse:
		body = json.dumps(payload, separators=(",", ":")).encode()
		signature = "sha256=" + hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
		url = self.base_url + "?" + urlencode({"integration": public_id or self.public_id})
		return self.request(
			"post",
			url,
			data=body,
			headers={"Content-Type": "application/json", "X-Hub-Signature-256": signature},
		)

	def payload(self, entries=None):
		return {"object": "whatsapp_business_account", "entry": entries or []}

	def entry(self, changes):
		return {
			"id": self.waba_id,
			"changes": [
				{"field": field, "value": {"metadata": {"phone_number_id": self.phone_id}, **value}}
				for field, value in changes
			],
		}

	def test_get_challenge_is_raw_and_rejects_wrong_mode_or_token(self):
		query = {
			"hub.mode": "subscribe",
			"hub.verify_token": "synthetic-verify-token",
			"hub.challenge": "synthetic-challenge-42",
		}
		response = self.request("get", self.url(**query))
		self.assertEqual(response.status_code, 200, response.get_data(as_text=True)[:1000])
		self.assertEqual(response.get_data(as_text=True), query["hub.challenge"])
		self.assertIn("text/plain", response.content_type)
		self.assertEqual(
			self.request("get", self.url(**{**query, "hub.verify_token": "wrong-token"})).status_code, 403
		)
		self.assertEqual(self.request("get", self.url(**{**query, "hub.mode": "other"})).status_code, 403)
		self.assertTrue(frappe.db.get_value("WA Connection", self.connection, "last_webhook_verified_at"))

	def test_post_authenticates_exact_raw_body_and_owned_waba_and_number(self):
		valid = self.payload([self.entry([("messages", {"messages": []})])])
		body = json.dumps(valid, separators=(",", ":")).encode()
		changed = self.signed_post(body + b" ", signature_body=body)
		self.assertEqual(changed.status_code, 401)
		wrong_waba = self.payload([{"id": str(int(self.waba_id) + 1), "changes": []}])
		self.assertEqual(self.response(wrong_waba).status_code, 401)
		wrong_number = self.payload([self.entry([("messages", {"messages": []})])])
		wrong_number["entry"][0]["changes"][0]["value"]["metadata"]["phone_number_id"] = str(
			int(self.phone_id) + 1
		)
		self.assertEqual(self.response(wrong_number).status_code, 401)
		self.assertEqual(self.response(valid, public_id=f"missing-{self.run_id}").status_code, 401)
		self.assertEqual(frappe.db.count("WA Webhook Event", {"company": self.company}), 0)

	def test_signed_receipt_is_durable_and_duplicate_envelope_is_safe(self):
		payload = self.payload([self.entry([("messages", {"messages": []})])])
		body = json.dumps(payload, separators=(",", ":")).encode()
		with patch("tag_marketing.application.webhook_intake.frappe.enqueue") as enqueue:
			first = self.signed_post(body)
			second = self.signed_post(body)
		self.assertEqual(first.status_code, 200)
		self.assertEqual(second.status_code, 200)
		self.assertEqual(frappe.db.count("WA Webhook Event", {"company": self.company}), 1)
		event = frappe.db.get_value(
			"WA Webhook Event", {"company": self.company}, ["raw_payload", "status"], as_dict=True
		)
		self.assertEqual(event.raw_payload, body.decode())
		self.assertEqual(event.status, "Ready")
		self.assertTrue(frappe.db.get_value("WA Connection", self.connection, "last_webhook_at"))
		self.assertEqual(enqueue.call_count, 2)  # duplicate Ready receipts reawaken durable work
		self.assertTrue(enqueue.call_args.kwargs["enqueue_after_commit"])
		self.assertEqual(enqueue.call_args.kwargs["queue"], "marketing")
		self.assertNotIn(SECRET, first.get_data(as_text=True) + second.get_data(as_text=True))
		self.assertEqual(frappe.db.get_value("WA Connection", self.connection, "status"), "Disabled")
		meta = frappe.get_meta("WA Webhook Event")
		self.assertEqual(
			[permission.role for permission in meta.permissions if permission.read], ["System Manager"]
		)
		self.assertEqual(meta.get_field("raw_payload").permlevel, 2)

	def test_recovery_requeues_ready_receipts_with_a_stable_deduplicated_job(self):
		from datetime import timedelta

		event = raw(
			"WA Webhook Event",
			name=f"_wa_recovery_ready_{self.run_id}",
			company=self.company,
			connection=self.connection,
			receipt_key=f"recovery-ready-{self.run_id}",
			raw_payload='{"object":"whatsapp_business_account","entry":[]}',
			status="Ready",
			received_at=frappe.utils.now_datetime() - timedelta(minutes=2),
			attempt_count=0,
		)
		frappe.db.set_value(
			"WA Webhook Event",
			event.name,
			"modified",
			frappe.utils.now_datetime() - timedelta(minutes=2),
			update_modified=False,
		)
		with patch("tag_marketing.application.event_recovery.frappe.enqueue") as enqueue:
			_recover_webhooks()
		self.assertEqual(enqueue.call_count, 1)
		self.assertEqual(enqueue.call_args.kwargs["job_id"], f"wa-webhook:{event.name}")
		self.assertTrue(enqueue.call_args.kwargs["deduplicate"])

	def test_webhook_retries_are_delayed_and_stop_after_five_attempts(self):
		from datetime import timedelta

		old = frappe.utils.now_datetime() - timedelta(minutes=6)
		retry = raw(
			"WA Webhook Event",
			name=f"_wa_recovery_retry_{self.run_id}",
			company=self.company,
			connection=self.connection,
			receipt_key=f"recovery-retry-{self.run_id}",
			raw_payload='{"object":"whatsapp_business_account","entry":[]}',
			status="Failed",
			error_code="PROCESSING_FAILED",
			received_at=old,
			attempt_count=2,
		)
		terminal = raw(
			"WA Webhook Event",
			name=f"_wa_recovery_terminal_{self.run_id}",
			company=self.company,
			connection=self.connection,
			receipt_key=f"recovery-terminal-{self.run_id}",
			raw_payload='{"object":"whatsapp_business_account","entry":[]}',
			status="Failed",
			error_code="PROCESSING_FAILED",
			received_at=old,
			attempt_count=5,
		)
		for event in (retry, terminal):
			frappe.db.set_value("WA Webhook Event", event.name, "modified", old, update_modified=False)
		with patch("tag_marketing.application.event_recovery.frappe.enqueue") as enqueue:
			_recover_webhooks()
		self.assertEqual(frappe.db.get_value("WA Webhook Event", retry.name, "status"), "Ready")
		self.assertEqual(frappe.db.get_value("WA Webhook Event", terminal.name, "status"), "Failed")
		self.assertEqual(enqueue.call_count, 1)
		self.assertEqual(enqueue.call_args.kwargs["event_name"], retry.name)

	def test_persistence_failure_is_not_acknowledged(self):
		body = json.dumps(self.payload([self.entry([])]), separators=(",", ":")).encode()
		with patch(
			"tag_marketing.application.webhook_intake._persist_receipt",
			side_effect=RuntimeError("synthetic private database detail"),
		):
			response = self.signed_post(body)
		self.assertEqual(response.status_code, 503)
		self.assertEqual(response.get_data(as_text=True), "PERSISTENCE_UNAVAILABLE")
		self.assertNotIn("synthetic private database detail", response.get_data(as_text=True))
		self.assertEqual(frappe.db.count("WA Webhook Event", {"company": self.company}), 0)

	def test_body_bounds_and_content_type_fail_before_persistence(self):
		oversize = b'{"data":"' + b"a" * 1_048_576 + b'"}'
		response = self.request(
			"post", self.url(), data=oversize, headers={"Content-Type": "application/json"}
		)
		self.assertEqual(response.status_code, 413)
		response = self.signed_post(b"{}", content_type="text/plain")
		self.assertEqual(response.status_code, 415)
		self.assertEqual(self.signed_post(b"").status_code, 411)
		response = self.request(
			"post",
			self.url(),
			data=b"",
			headers={"Content-Type": "application/json", "Content-Length": "0"},
			environ_overrides={
				"HTTP_HOST": self.site,
				"SERVER_NAME": self.site,
				"CONTENT_LENGTH": "0",
			},
		)
		self.assertEqual(response.status_code, 400)
		self.assertEqual(frappe.db.count("WA Webhook Event", {"company": self.company}), 0)

	def test_processor_keeps_valid_siblings_and_deduplicates_elements_across_receipts(self):
		message_a = {
			"id": "wamid.synthetic-a",
			"from": "27123456789",
			"timestamp": "1793300000",
			"type": "text",
		}
		message_b = {
			"id": "wamid.synthetic-b",
			"from": "27876543210",
			"timestamp": "1793300001",
			"type": "image",
		}
		status = {
			"id": "wamid.synthetic-outbound",
			"status": "delivered",
			"timestamp": "1793300002",
			"recipient_id": "27876543210",
		}
		payload = self.payload(
			[
				self.entry([("messages", {"messages": [message_a], "statuses": [status, status]})]),
				self.entry([("messages", {"messages": [message_b]}), ("unknown_future_event", {})]),
			]
		)
		first = self.response(payload)
		self.assertEqual(first.status_code, 200)
		first_event = frappe.db.get_value("WA Webhook Event", {"company": self.company}, "name")
		process_webhook_event(first_event)
		message_a_late_duplicate = {**message_a, "timestamp": "1793300099"}
		second_payload = self.payload(
			[self.entry([("messages", {"messages": [message_a_late_duplicate], "statuses": [status]})])]
		)
		second_payload["delivery_attempt"] = "different-envelope-with-same-element"
		second = self.response(second_payload)
		self.assertEqual(second.status_code, 200)
		events = frappe.get_all("WA Webhook Event", filters={"company": self.company}, pluck="name")
		second_event = next(name for name in events if name != first_event)
		process_webhook_event(second_event)
		self.assertEqual(frappe.db.count("WA Message Event", {"company": self.company}), 3)
		self.assertEqual(frappe.db.get_value("WA Webhook Event", first_event, "status"), "Processed")
		self.assertEqual(
			frappe.db.get_value("WA Webhook Event", first_event, "error_code"), "UNSUPPORTED_EVENT"
		)
		self.assertEqual(frappe.db.get_value("WA Webhook Event", second_event, "status"), "Processed")
		self.assertFalse(
			frappe.db.exists("WA Message", {"provider_message_id": status["id"]}),
			"A status received before local submission acceptance must remain unmatched evidence.",
		)
		self.assertEqual(
			frappe.db.get_value("WA Message Event", {"provider_message_id": status["id"]}, "event_type"),
			"Provider Status",
		)

	def test_processing_failure_is_redacted_and_retained_for_recovery(self):
		payload = self.payload([self.entry([("messages", {"messages": []})])])
		self.assertEqual(self.response(payload).status_code, 200)
		event = frappe.db.get_value("WA Webhook Event", {"company": self.company}, "name")
		with patch(
			"tag_marketing.application.webhook_processing._process_payload",
			side_effect=RuntimeError("synthetic sensitive processing detail"),
		):
			process_webhook_event(event)
		self.assertEqual(frappe.db.get_value("WA Webhook Event", event, "status"), "Failed")
		self.assertEqual(frappe.db.get_value("WA Webhook Event", event, "error_code"), "PROCESSING_FAILED")
		self.assertEqual(frappe.db.get_value("WA Webhook Event", event, "attempt_count"), 1)

	def test_invalid_json_and_unknown_routes_are_rejected(self):
		# Frappe's request initializer rejects invalid JSON before method dispatch.
		self.assertEqual(self.signed_post(b"not-json").status_code, 417)
		self.assertEqual(self.request("get", self.url(integration="invalid")).status_code, 403)
		self.assertEqual(frappe.db.count("WA Webhook Event", {"company": self.company}), 0)
