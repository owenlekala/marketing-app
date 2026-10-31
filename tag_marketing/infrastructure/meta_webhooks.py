"""Strict parsing and authentication for the Meta webhook boundary."""

import hashlib
import hmac
import json
import re
from collections.abc import Callable
from typing import Any

MAX_WEBHOOK_BODY_BYTES = 1_048_576
MAX_ENTRIES = 100
MAX_CHANGES_PER_ENTRY = 100
SIGNATURE_RE = re.compile(r"sha256=[0-9a-fA-F]{64}\Z")


class InvalidWebhook(ValueError):
	"""The signed body is malformed or outside the supported bounded shape."""


class UnauthenticatedWebhook(ValueError):
	"""The route, signature, WABA or sending-number identity is not trusted."""


def verify_signature(raw_body: bytes, signature: str | None, app_secret: str) -> None:
	if not signature or not SIGNATURE_RE.fullmatch(signature):
		raise UnauthenticatedWebhook from None
	expected = "sha256=" + hmac.new(app_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
	if not hmac.compare_digest(expected, signature.lower()):
		raise UnauthenticatedWebhook from None


def parse_payload(raw_body: bytes) -> dict[str, Any]:
	def reject_constant(_value: str):
		raise InvalidWebhook from None

	try:
		payload = json.loads(raw_body.decode("utf-8"), parse_constant=reject_constant)
	except (UnicodeDecodeError, json.JSONDecodeError):
		raise InvalidWebhook from None
	if (
		not isinstance(payload, dict)
		or payload.get("object") != "whatsapp_business_account"
		or not isinstance(payload.get("entry"), list)
		or len(payload["entry"]) > MAX_ENTRIES
	):
		raise InvalidWebhook from None
	for entry in payload["entry"]:
		if not isinstance(entry, dict) or not isinstance(entry.get("id"), (str, int)):
			raise InvalidWebhook from None
		changes = entry.get("changes", [])
		if not isinstance(changes, list) or len(changes) > MAX_CHANGES_PER_ENTRY:
			raise InvalidWebhook from None
		for change in changes:
			if not isinstance(change, dict) or not isinstance(change.get("value", {}), dict):
				raise InvalidWebhook from None
	return payload


def validate_ownership(
	payload: dict[str, Any],
	waba_id: str,
	number_is_owned: Callable[[str], bool],
) -> None:
	for entry in payload["entry"]:
		if str(entry["id"]) != waba_id:
			raise UnauthenticatedWebhook from None
		for change in entry.get("changes", []):
			metadata = change["value"].get("metadata")
			if change.get("field") != "messages":
				continue
			if not isinstance(metadata, dict):
				raise InvalidWebhook from None
			phone_id = metadata.get("phone_number_id")
			if (
				not isinstance(phone_id, (str, int))
				or isinstance(phone_id, bool)
				or not str(phone_id)
				or not number_is_owned(str(phone_id))
			):
				raise UnauthenticatedWebhook from None


def receipt_key(public_id: str, raw_body: bytes) -> str:
	return hashlib.sha256(public_id.encode("ascii") + b"\0" + raw_body).hexdigest()
