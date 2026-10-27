"""Pure validation of local settings; no framework or provider dependencies."""

import math
from datetime import time
from typing import Any
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

SOURCES = frozenset({"Lead", "Customer", "Contact", "Sales Order"})
RETENTION_FIELDS = (
	"raw_event_retention_days",
	"message_retention_days",
	"media_retention_days",
	"consent_retention_days",
)


def validate_settings(values: dict[str, Any]) -> None:
	try:
		ZoneInfo(values["timezone"])
		start, end = (
			time.fromisoformat(str(values[field])) for field in ("marketing_start", "marketing_end")
		)
	except (ValueError, TypeError, KeyError, ZoneInfoNotFoundError) as exc:
		raise ValueError("invalid_timezone_hours") from exc
	if start.tzinfo is not None or end.tzinfo is not None or start >= end:
		raise ValueError("invalid_hours")
	for field in ("marketing_cap", "cap_window_hours"):
		value = values.get(field)
		if (
			isinstance(value, bool)
			or not isinstance(value, (int, float))
			or not math.isfinite(value)
			or value <= 0
			or int(value) != value
		):
			raise ValueError("invalid_cap")
	if values.get("max_campaign_recipients") != 10000:
		raise ValueError("invalid_recipient_limit")
	for field in (*RETENTION_FIELDS, "company_rate_per_second"):
		value = values.get(field)
		if value is not None and (
			not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0
		):
			raise ValueError("invalid_retention_rate")
		if field in RETENTION_FIELDS and value and int(value) != value:
			raise ValueError("invalid_retention_days")
	url = values.get("privacy_notice_url")
	if url:
		try:
			parsed = urlsplit(url)
			valid = (
				parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password
			)
			parsed.port
		except (ValueError, TypeError):
			valid = False
		if not valid:
			raise ValueError("invalid_privacy_url")
	if values.get("sending_scope") not in ("Pilot", "Live"):
		raise ValueError("invalid_scope")
