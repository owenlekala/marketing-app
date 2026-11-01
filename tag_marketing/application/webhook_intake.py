"""Durable, authenticated receipt handling for Meta webhooks."""

import hmac
from datetime import UTC, datetime
from typing import Any

import frappe

from tag_marketing.infrastructure.meta_webhooks import (
	InvalidWebhook,
	UnauthenticatedWebhook,
	parse_payload,
	receipt_key,
	validate_ownership,
	verify_signature,
)


def _connection_for_public_id(public_id: str) -> Any:
	if not isinstance(public_id, str) or not (20 <= len(public_id) <= 128):
		raise UnauthenticatedWebhook from None
	connection_name = frappe.db.get_value("WA Connection", {"public_id": public_id}, "name")
	if not connection_name:
		raise UnauthenticatedWebhook from None
	connection = frappe.get_doc("WA Connection", connection_name)
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or connection.company != company:
		raise UnauthenticatedWebhook from None
	return connection


def verify_challenge(public_id: str, mode: str | None, token: str | None, challenge: str | None) -> str:
	connection = _connection_for_public_id(public_id)
	configured = connection.get_password("verify_token", raise_exception=False) or ""
	if (
		mode != "subscribe"
		or not token
		or not challenge
		or len(challenge) > 256
		or not configured
		or not hmac.compare_digest(configured, token)
	):
		raise UnauthenticatedWebhook from None
	frappe.db.set_value(
		"WA Connection",
		connection.name,
		"last_webhook_verified_at",
		datetime.now(UTC).replace(tzinfo=None),
		update_modified=False,
	)
	frappe.db.commit()
	return challenge


def _number_is_owned(connection: str, provider_phone_id: str) -> bool:
	return bool(
		frappe.db.exists(
			"WA Sending Number", {"connection": connection, "provider_phone_id": provider_phone_id}
		)
	)


def _persist_receipt(connection: Any, key: str, raw_body: bytes) -> tuple[str, str, bool]:
	existing = frappe.db.get_value("WA Webhook Event", {"receipt_key": key}, ["name", "status"], as_dict=True)
	if existing:
		return existing.name, existing.status, True

	doc = frappe.get_doc(
		{
			"doctype": "WA Webhook Event",
			"company": connection.company,
			"connection": connection.name,
			"receipt_key": key,
			"raw_payload": raw_body.decode("utf-8"),
			"status": "Ready",
			"received_at": datetime.now(UTC).replace(tzinfo=None),
			"attempt_count": 0,
		}
	)
	try:
		# Trusted server-side persistence deliberately bypasses the closed generic
		# DocType write path. Guest never receives a record or its raw payload.
		doc.db_insert()
	except frappe.DuplicateEntryError:
		existing = frappe.db.get_value(
			"WA Webhook Event", {"receipt_key": key}, ["name", "status"], as_dict=True
		)
		if not existing:
			raise
		return existing.name, existing.status, True
	return doc.name, "Ready", False


def accept_webhook(public_id: str, raw_body: bytes, signature: str | None) -> dict[str, Any]:
	connection = _connection_for_public_id(public_id)
	app_secret = connection.get_password("app_secret", raise_exception=False) or ""
	if not app_secret:
		raise UnauthenticatedWebhook from None
	verify_signature(raw_body, signature, app_secret)
	payload = parse_payload(raw_body)
	validate_ownership(
		payload,
		connection.waba_id,
		lambda phone_id: _number_is_owned(connection.name, phone_id),
	)
	key = receipt_key(public_id, raw_body)
	event_name, status, duplicate = _persist_receipt(connection, key, raw_body)
	frappe.db.set_value(
		"WA Connection",
		connection.name,
		"last_webhook_at",
		datetime.now(UTC).replace(tzinfo=None),
		update_modified=False,
	)
	if status == "Ready":
		frappe.enqueue(
			"tag_marketing.application.webhook_processing.process_webhook_event",
			queue="marketing",
			timeout=120,
			enqueue_after_commit=True,
			job_id=f"wa-webhook:{event_name}",
			deduplicate=True,
			event_name=event_name,
		)
	return {"accepted": True, "duplicate": duplicate}


def webhook_timestamp(value: Any) -> datetime | None:
	if not isinstance(value, (str, int)) or isinstance(value, bool):
		return None
	try:
		seconds = int(value)
		if seconds < 0:
			return None
		return datetime.fromtimestamp(seconds, UTC).replace(tzinfo=None)
	except (ValueError, OverflowError, OSError):
		return None
