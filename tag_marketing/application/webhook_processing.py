"""Idempotent persistence of verified provider message/status observations."""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import frappe

from tag_marketing.application.webhook_intake import webhook_timestamp


def _event_key(company: str, kind: str, provider_id: str, status: str = "", timestamp: str = "") -> str:
	material = "\0".join((company, kind, provider_id, status, timestamp)).encode("utf-8")
	return hashlib.sha256(material).hexdigest()


def _insert_message_event(
	company: str,
	provider_id: Any,
	event_type: str,
	occurred_at: Any,
	details: dict[str, Any],
) -> bool:
	if not isinstance(provider_id, str) or not provider_id or len(provider_id) > 140:
		return False
	key = _event_key(
		company,
		event_type,
		provider_id,
		str(details.get("status") or ""),
		str(occurred_at or "") if event_type == "Provider Status" else "",
	)
	if frappe.db.exists("WA Message Event", {"event_key": key}):
		return False
	doc = frappe.get_doc(
		{
			"doctype": "WA Message Event",
			"company": company,
			"provider_message_id": provider_id,
			"event_type": event_type,
			"occurred_at": occurred_at,
			"received_at": datetime.now(UTC).replace(tzinfo=None),
			"event_key": key,
			"details_json": details,
		}
	)
	try:
		doc.db_insert()
	except frappe.DuplicateEntryError:
		if frappe.db.exists("WA Message Event", {"event_key": key}):
			return False
		raise
	return True


def _safe_error_codes(status: dict[str, Any]) -> list[str]:
	codes = []
	errors = status.get("errors", [])
	for error in errors[:10] if isinstance(errors, list) else []:
		if isinstance(error, dict) and isinstance(error.get("code"), (str, int)):
			codes.append(str(error["code"])[:64])
	return codes


def _process_payload(company: str, payload: dict[str, Any]) -> bool:
	unsupported = False
	for entry in payload["entry"]:
		for change in entry.get("changes", []):
			if change.get("field") != "messages":
				unsupported = True
				continue
			value = change["value"]
			messages = value.get("messages", [])
			if not isinstance(messages, list):
				unsupported = True
				messages = []
			for message in messages:
				if not isinstance(message, dict):
					unsupported = True
					continue
				if not isinstance(message.get("id"), str) or not (1 <= len(message["id"]) <= 140):
					unsupported = True
					continue
				occurred = webhook_timestamp(message.get("timestamp"))
				_insert_message_event(
					company,
					message.get("id"),
					"Inbound Message",
					occurred,
					{"message_type": str(message.get("type") or "unknown")[:32]},
				)
			statuses = value.get("statuses", [])
			if not isinstance(statuses, list):
				unsupported = True
				statuses = []
			for status in statuses:
				if not isinstance(status, dict):
					unsupported = True
					continue
				if not isinstance(status.get("id"), str) or not (1 <= len(status["id"]) <= 140):
					unsupported = True
					continue
				state = status.get("status")
				if not isinstance(state, str) or len(state) > 32:
					unsupported = True
					continue
				occurred = webhook_timestamp(status.get("timestamp"))
				_insert_message_event(
					company,
					status.get("id"),
					"Provider Status",
					occurred,
					{"status": state, "error_codes": _safe_error_codes(status)},
				)
	return unsupported


def process_webhook_event(event_name: str) -> None:
	"""Claim one receipt, persist its deduplicated observations, then finish."""
	frappe.db.sql(
		"""
		UPDATE `tabWA Webhook Event`
		SET status = 'Processing', attempt_count = attempt_count + 1,
			modified = NOW(), modified_by = %s
		WHERE name = %s AND status = 'Ready'
		""",
		(frappe.session.user, event_name),
	)
	claimed = frappe.db.sql("SELECT ROW_COUNT()")[0][0]
	if claimed != 1:
		return
	frappe.db.commit()
	try:
		receipt = frappe.db.get_value(
			"WA Webhook Event", event_name, ["company", "raw_payload"], as_dict=True
		)
		if not receipt:
			raise ValueError("receipt_missing")
		payload = json.loads(receipt.raw_payload)
		unsupported = _process_payload(receipt.company, payload)
		frappe.db.set_value(
			"WA Webhook Event",
			event_name,
			{
				"status": "Processed",
				"processed_at": datetime.now(UTC).replace(tzinfo=None),
				"error_code": "UNSUPPORTED_EVENT" if unsupported else None,
			},
		)
		frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		frappe.db.set_value(
			"WA Webhook Event", event_name, {"status": "Failed", "error_code": "PROCESSING_FAILED"}
		)
		frappe.db.commit()
		frappe.logger("tag_marketing").error(
			"Webhook processing failed for event %s (%s)", event_name, type(exc).__name__
		)
