"""Pure CSV import and consent chronology rules."""

import csv
import hashlib
import io
import json
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from typing import Any

from tag_marketing.domain.phones import to_e164

MAX_CSV_BYTES = 5 * 1024 * 1024
MAX_CSV_ROWS = 100_000
MAX_CELL_LENGTH = 2_000
MAPPING_FIELDS = frozenset(
	{
		"phone",
		"display_name",
		"country_code",
		"consent_occurred_at",
		"consent_notice_version",
		"consent_reference",
	}
)
GRANT_FIELDS = frozenset({"consent_occurred_at", "consent_notice_version", "consent_reference"})


def canonical_json(value: Any) -> str:
	return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def safe_csv_cell(value: Any) -> str:
	"""Neutralize spreadsheet formulas when emitting user-facing CSV diagnostics."""
	text = str(value if value is not None else "")
	return "'" + text if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else text


def import_hash(file_bytes: bytes, mapping: Mapping[str, Any]) -> str:
	return hashlib.sha256(file_bytes + b"\0" + canonical_json(mapping).encode("utf-8")).hexdigest()


def csv_headers(file_bytes: bytes) -> list[str]:
	if not isinstance(file_bytes, bytes) or not file_bytes or len(file_bytes) > MAX_CSV_BYTES:
		raise ValueError("invalid_file_size")
	try:
		reader = csv.reader(
			io.StringIO(file_bytes.decode("utf-8-sig", errors="strict"), newline=""), strict=True
		)
		headers = next(reader)
	except (UnicodeDecodeError, csv.Error, StopIteration) as exc:
		raise ValueError("invalid_csv") from exc
	clean_headers = [name.strip() for name in headers]
	if (
		not headers
		or len(headers) > 100
		or len(clean_headers) != len(set(clean_headers))
		or any(not name or len(name) > 200 for name in clean_headers)
	):
		raise ValueError("invalid_headers")
	return clean_headers


def validate_mapping(mapping: Any, headers: Iterable[str]) -> dict[str, Any]:
	if not isinstance(mapping, Mapping) or set(mapping) - {"columns", "default_country_code"}:
		raise ValueError("invalid_mapping")
	columns = mapping.get("columns")
	if not isinstance(columns, Mapping) or set(columns) - MAPPING_FIELDS or "phone" not in columns:
		raise ValueError("invalid_mapping")
	known_headers = {header.strip() for header in headers}
	clean: dict[str, str] = {}
	for field, header in columns.items():
		if not isinstance(header, str) or not header.strip() or header.strip() not in known_headers:
			raise ValueError("invalid_mapping")
		if header.strip() in clean.values():
			raise ValueError("duplicate_mapping")
		clean[field] = header.strip()
	country = mapping.get("default_country_code")
	if country is not None and (not isinstance(country, str) or len(country) != 2 or not country.isalpha()):
		raise ValueError("invalid_country")
	if GRANT_FIELDS.intersection(clean) and not GRANT_FIELDS.issubset(clean):
		raise ValueError("incomplete_evidence_mapping")
	return {"columns": clean, "default_country_code": country.upper() if country else None}


def parse_csv(file_bytes: bytes, mapping: Mapping[str, Any]) -> tuple[list[dict[str, Any]], str]:
	if not isinstance(file_bytes, bytes) or not file_bytes or len(file_bytes) > MAX_CSV_BYTES:
		raise ValueError("invalid_file_size")
	try:
		text = file_bytes.decode("utf-8-sig", errors="strict")
		reader = csv.DictReader(io.StringIO(text, newline=""), strict=True)
		headers = reader.fieldnames
		if (
			not headers
			or len(headers) > 100
			or any(not h or len(h) > 200 for h in headers)
			or len(headers) != len(set(headers))
		):
			raise ValueError("invalid_headers")
		clean_mapping = validate_mapping(mapping, headers)
		rows: list[dict[str, Any]] = []
		for ordinal, raw in enumerate(reader, start=2):
			if ordinal - 1 > MAX_CSV_ROWS:
				raise ValueError("too_many_rows")
			if None in raw or any(value is None for value in raw.values()):
				rows.append({"row_number": ordinal, "status": "Invalid", "error_code": "INVALID_COLUMNS"})
				continue
			projection = {
				field: (raw.get(header) or "").strip() for field, header in clean_mapping["columns"].items()
			}
			if any(len(value) > MAX_CELL_LENGTH for value in projection.values()):
				rows.append({"row_number": ordinal, "status": "Invalid", "error_code": "CELL_TOO_LARGE"})
				continue
			phone = to_e164(
				projection.get("phone", ""),
				projection.get("country_code") or clean_mapping["default_country_code"],
			)
			if not phone:
				rows.append({"row_number": ordinal, "status": "Invalid", "error_code": "INVALID_PHONE"})
				continue
			name = projection.get("display_name", "").strip() or phone
			if len(name) > 140:
				rows.append(
					{"row_number": ordinal, "status": "Invalid", "error_code": "INVALID_DISPLAY_NAME"}
				)
				continue
			evidence = None
			if GRANT_FIELDS.issubset(clean_mapping["columns"]):
				occurred = projection.get("consent_occurred_at", "")
				try:
					parsed = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
					evidence_time = (
						parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)
					)
				except (ValueError, TypeError):
					evidence_time = None
				if (
					evidence_time
					and projection.get("consent_notice_version")
					and projection.get("consent_reference")
				):
					evidence = {
						"occurred_at": evidence_time.replace(tzinfo=None).isoformat(sep=" "),
						"notice_version": projection["consent_notice_version"][:140],
						"reference": projection["consent_reference"][:500],
					}
			row = {
				"row_number": ordinal,
				"status": "Valid",
				"phone_e164": phone,
				"display_name": name[:140],
				"consent_evidence": evidence,
			}
			rows.append(row)
		return rows, import_hash(file_bytes, clean_mapping)
	except (UnicodeDecodeError, csv.Error) as exc:
		raise ValueError("invalid_csv") from exc


def effective_consent(events: Iterable[Mapping[str, Any]]) -> str:
	"""Withdraw wins at equal occurrence times; older grants never reopen permission."""
	latest: tuple[datetime, int, str] | None = None
	for event in events:
		kind = event.get("event_type")
		occurred = event.get("occurred_at")
		if kind not in {"Granted", "Withdrawn"} or not occurred:
			continue
		if isinstance(occurred, str):
			try:
				occurred = datetime.fromisoformat(occurred.replace("Z", "+00:00"))
			except ValueError:
				continue
		if not isinstance(occurred, datetime):
			continue
		instant = occurred.replace(tzinfo=UTC) if occurred.tzinfo is None else occurred.astimezone(UTC)
		candidate = (instant, 1 if kind == "Withdrawn" else 0, kind)
		if latest is None or candidate[:2] > latest[:2]:
			latest = candidate
	return "Unknown" if latest is None else ("Withdrawn" if latest[2] == "Withdrawn" else "Granted")
