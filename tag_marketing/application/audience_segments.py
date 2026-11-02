"""Bounded audience queries and segment commands backed by current permissions."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from hashlib import sha256
from typing import Any

import frappe

from tag_marketing.application.navigation import require_capability
from tag_marketing.domain.audience_filters import InvalidAudienceFilters, validate_filter_ast
from tag_marketing.domain.errors import CommandError
from tag_marketing.infrastructure import audience_repository
from tag_marketing.infrastructure.permissions import company_allowed

SNAPSHOT_BATCH_SIZE = 100
MAX_PREVIEW = 50
MAX_PREVIEW_CANDIDATES = 50_000
MAX_EXCLUSIONS = 500
MAX_RECIPIENTS = 10_000


def _company() -> str:
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company or not company_allowed(company, frappe.session.user, "WA Audience Segment"):
		raise CommandError("COMPANY_MISMATCH")
	return company


def _normalized_filters(value: Any) -> dict[str, Any]:
	try:
		if isinstance(value, str):
			value = frappe.parse_json(value)
			return validate_filter_ast(value)
		return validate_filter_ast(value)
	except (InvalidAudienceFilters, TypeError, ValueError) as error:
		raise CommandError("INVALID_FILTER", "filters_json") from error


def _exclusions(value: Any) -> tuple[list[str], list[str]]:
	if value is None or value == "":
		return [], []
	if isinstance(value, str):
		try:
			value = frappe.parse_json(value)
		except ValueError as error:
			raise CommandError("INVALID_INPUT", "exclusions") from error
	if not isinstance(value, dict):
		raise CommandError("INVALID_INPUT", "exclusions")
	contacts, tags = value.get("contacts", []), value.get("tags", [])
	if (
		not isinstance(contacts, list)
		or not isinstance(tags, list)
		or len(contacts) > MAX_EXCLUSIONS
		or len(tags) > MAX_EXCLUSIONS
		or any(not isinstance(item, str) or not item or len(item) > 140 for item in contacts + tags)
	):
		raise CommandError("INVALID_INPUT", "exclusions")
	return list(dict.fromkeys(contacts)), list(dict.fromkeys(tags))


def iterate_audience(
	company: str,
	filters: Any,
	*,
	actor: str | None = None,
	exclusions: Any = None,
	eligible_only: bool = True,
	chunk_size: int = audience_repository.SCAN_BATCH_SIZE,
	on_scan: Callable[[int], None] | None = None,
) -> Iterator[dict[str, Any]]:
	"""Yield a stable, permission-rechecked audience in bounded keyset chunks."""
	if not 1 <= chunk_size <= audience_repository.SCAN_BATCH_SIZE:
		raise CommandError("INVALID_INPUT", "chunk_size")
	actor = actor or frappe.session.user
	if actor == "Guest" or not {"Marketing User", "Marketing Manager"}.intersection(frappe.get_roles(actor)):
		raise CommandError("COMPANY_MISMATCH")
	if not company_allowed(company, actor, "WA Contact"):
		raise CommandError("COMPANY_MISMATCH")
	validated = _normalized_filters(filters)
	contacts, tags = _exclusions(exclusions)
	yield from audience_repository.iterate_contacts(
		company,
		validated,
		contacts,
		tags,
		actor,
		eligible=eligible_only,
		chunk_size=chunk_size,
		on_batch=on_scan,
	)


def _require_access(segment: str) -> tuple[str, dict[str, Any]]:
	company = _company()
	if not frappe.has_permission("WA Audience Segment", "read", doc=segment):
		raise CommandError("NOT_FOUND")
	row = frappe.db.get_value(
		"WA Audience Segment", segment, ["company", "filters_json", "disabled", "modified"], as_dict=True
	)
	if not row or row["company"] != company:
		raise CommandError("NOT_FOUND")
	if row["disabled"]:
		raise CommandError("INVALID_STATE")
	return company, row


def preview(
	segment: str,
	exclusions: Any = None,
	limit: int = 20,
	cursor: str = "",
	*,
	on_progress: Callable[[int], None] | None = None,
) -> dict[str, Any]:
	"""Permission-aware, bounded count and keyset sample for a saved segment."""
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company, row = _require_access(segment)
	if not isinstance(limit, int) or not 1 <= limit <= MAX_PREVIEW:
		raise CommandError("INVALID_INPUT", "limit")
	if not isinstance(cursor, str) or len(cursor) > 140:
		raise CommandError("INVALID_INPUT", "cursor")
	normalized_filters = _normalized_filters(row["filters_json"])
	filters = {"version": 1, **normalized_filters}
	contacts, tags = _exclusions(exclusions)
	counts: dict[str, int] = {
		"matched_count": 0,
		"eligible_count": 0,
		"suppressed": 0,
		"archived": 0,
		"withdrawn": 0,
		"unknown_consent": 0,
	}
	actor = frappe.session.user
	for item in iterate_audience(
		company,
		filters,
		actor=actor,
		exclusions=exclusions,
		eligible_only=False,
		on_scan=on_progress,
	):
		counts["matched_count"] += 1
		if counts["matched_count"] > MAX_PREVIEW_CANDIDATES:
			raise CommandError("AUDIENCE_PREVIEW_TOO_LARGE")
		if item["consent_status"] == "Granted" and not item["suppressed"] and not item["archived"]:
			counts["eligible_count"] += 1
		elif item["suppressed"]:
			counts["suppressed"] += 1
		elif item["archived"]:
			counts["archived"] += 1
		elif item["consent_status"] == "Withdrawn":
			counts["withdrawn"] += 1
		else:
			counts["unknown_consent"] += 1
	samples, has_more = audience_repository.preview_contacts(
		company, normalized_filters, contacts, tags, actor, cursor, limit
	)
	if samples is None:
		raise CommandError("INVALID_INPUT", "cursor")
	return {
		**counts,
		"excluded": {
			"suppressed": counts["suppressed"],
			"archived": counts["archived"],
			"withdrawn": counts["withdrawn"],
			"unknown_consent": counts["unknown_consent"],
		},
		"items": samples,
		"next_cursor": samples[-1]["name"] if has_more and samples else None,
		"revision": frappe.db.get_value("WA Audience Segment", segment, "modified"),
	}


def request_preview(
	segment: str,
	exclusions: Any,
	limit: int,
	cursor: str,
	request_id: str,
) -> dict[str, Any]:
	"""Run a small preview inline; persist and queue a large one for bounded background work."""
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company, row = _require_access(segment)
	if not isinstance(limit, int) or not 1 <= limit <= MAX_PREVIEW:
		raise CommandError("INVALID_INPUT", "limit")
	if not isinstance(cursor, str) or len(cursor) > 140:
		raise CommandError("INVALID_INPUT", "cursor")
	if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
		raise CommandError("INVALID_INPUT", "request_id")
	normalized = _normalized_filters(row["filters_json"])
	contacts, tags = _exclusions(exclusions)
	candidate_count = audience_repository.count_candidates(company, normalized, contacts, tags)
	if candidate_count <= 2_000:
		return {"preview": preview(segment, exclusions, limit, cursor)}
	if candidate_count > MAX_PREVIEW_CANDIDATES:
		raise CommandError("AUDIENCE_PREVIEW_TOO_LARGE")
	request = {
		"segment": segment,
		"expected_modified": str(row["modified"]),
		"exclusions": {"contacts": contacts, "tags": tags},
		"limit": limit,
		"cursor": cursor,
		"candidate_count": candidate_count,
	}
	request_hash = sha256(
		json.dumps(request, sort_keys=True, separators=(",", ":")).encode("utf-8")
	).hexdigest()
	operation_type = "audiences.preview"
	filters = {
		"requested_by": frappe.session.user,
		"operation_type": operation_type,
		"request_id": request_id,
	}
	prior = frappe.db.get_value("WA Operation", filters, ["name", "request_hash", "status"], as_dict=True)
	if prior:
		if prior["request_hash"] != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return {"operation": prior["name"], "status": prior["status"]}
	doc = frappe.get_doc(
		{
			"doctype": "WA Operation",
			"company": company,
			"operation_type": operation_type,
			"requested_by": frappe.session.user,
			"request_id": request_id,
			"request_hash": request_hash,
			"request_json": json.dumps(request, sort_keys=True, separators=(",", ":")),
			"attempt_count": 0,
			"status": "Pending",
			"progress_percent": 0,
			"target_doctype": "WA Audience Segment",
			"target_name": segment,
			"heartbeat_at": frappe.utils.now_datetime(),
		}
	)
	try:
		doc.db_insert()
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		prior = frappe.db.get_value("WA Operation", filters, ["name", "request_hash", "status"], as_dict=True)
		if not prior:
			raise
		if prior["request_hash"] != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT") from None
		return {"operation": prior["name"], "status": prior["status"]}
	frappe.enqueue(
		"tag_marketing.application.audience_preview_jobs.run_audience_preview_operation",
		queue="marketing",
		timeout=900,
		enqueue_after_commit=True,
		job_id=f"wa-audience-preview:{doc.name}",
		deduplicate=True,
		operation_id=doc.name,
	)
	return {"operation": doc.name, "status": doc.status}


def save_segment(
	segment_name: str, filters: Any, expected_modified: str | None = None, segment: str | None = None
) -> dict[str, Any]:
	"""Create/update editable segment definition through the application boundary."""
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company = _company()
	name = segment_name.strip() if isinstance(segment_name, str) else ""
	if not 1 <= len(name) <= 140:
		raise CommandError("INVALID_INPUT", "segment_name")
	validated = _normalized_filters(filters)
	if segment:
		if not frappe.has_permission("WA Audience Segment", "read", doc=segment):
			raise CommandError("NOT_FOUND")
		doc = frappe.get_doc("WA Audience Segment", segment)
		if doc.company != company:
			raise CommandError("NOT_FOUND")
		if not expected_modified or str(doc.modified) != str(expected_modified):
			raise CommandError("STALE_DOCUMENT")
	else:
		doc = frappe.new_doc("WA Audience Segment")
		doc.company = company
	doc.segment_name = name
	doc.filters_json = json.dumps({"version": 1, **validated}, sort_keys=True, separators=(",", ":"))
	doc.flags.wa_segment_command = True
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "modified": doc.modified, "filters": validated}


def validate_segment_record(doc: Any) -> None:
	"""Controller hook for service-managed segment creation and updates."""
	if not getattr(doc.flags, "wa_segment_command", False):
		raise CommandError("INVALID_STATE")
	company = _company()
	if doc.company != company:
		raise CommandError("COMPANY_MISMATCH")
	if not isinstance(doc.segment_name, str) or not 1 <= len(doc.segment_name.strip()) <= 140:
		raise CommandError("INVALID_INPUT", "segment_name")
	doc.segment_name = doc.segment_name.strip()
	filters = _normalized_filters(doc.filters_json)
	doc.filters_json = json.dumps({"version": 1, **filters}, sort_keys=True, separators=(",", ":"))
	if doc.disabled not in (0, 1, False, True):
		raise CommandError("INVALID_INPUT", "disabled")


def set_segment_disabled(segment: str, disabled: bool, expected_modified: str) -> dict[str, Any]:
	"""Manager-only lifecycle switch; existing campaign snapshots remain immutable."""
	require_capability(frozenset({"Marketing Manager"}))
	company = _company()
	if not isinstance(disabled, bool) or not expected_modified:
		raise CommandError("INVALID_INPUT")
	if not frappe.has_permission("WA Audience Segment", "read", doc=segment):
		raise CommandError("NOT_FOUND")
	doc = frappe.get_doc("WA Audience Segment", segment)
	if doc.company != company:
		raise CommandError("NOT_FOUND")
	if str(doc.modified) != str(expected_modified):
		raise CommandError("STALE_DOCUMENT")
	doc.disabled = int(disabled)
	doc.flags.wa_segment_command = True
	doc.save(ignore_permissions=True)
	return {"name": doc.name, "disabled": bool(doc.disabled), "modified": doc.modified}


def iterate_snapshot_recipients(
	company: str,
	filters: Any,
	actor: str,
	exclusions: Any = None,
	*,
	chunk_size: int = SNAPSHOT_BATCH_SIZE,
) -> Iterator[dict[str, Any]]:
	"""Yield eligible snapshot members in chunks and fail on the 10,001st member.

	Snapshot builders must consume this iterator in the same transaction as their
	Building snapshot writes so the ceiling error rolls back partial work.
	"""
	for index, contact in enumerate(
		iterate_audience(
			company,
			filters,
			actor=actor,
			exclusions=exclusions,
			eligible_only=True,
			chunk_size=chunk_size,
		),
		start=1,
	):
		if index > MAX_RECIPIENTS:
			raise CommandError("AUDIENCE_TOO_LARGE")
		yield contact
