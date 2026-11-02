"""Frappe persistence adapter for private audience imports and consent commands."""

import csv
import hashlib
import io
import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import frappe
from frappe import _
from frappe.utils.file_manager import save_file

from tag_marketing.application.audiences import _company
from tag_marketing.application.eligibility import lock_contact_for_change
from tag_marketing.application.navigation import require_capability
from tag_marketing.application.suppression import digest_for_identity
from tag_marketing.domain.errors import CommandError, require_revision
from tag_marketing.domain.imports import csv_headers, import_hash, parse_csv, safe_csv_cell
from tag_marketing.infrastructure.permissions import company_allowed


def _now() -> datetime:
	return datetime.now(UTC).replace(tzinfo=None)


def _file_bytes(file_name: str, *, batch_name: str | None = None, owner: str | None = None) -> bytes:
	file = frappe.get_doc("File", file_name)
	if (
		file.is_private != 1
		or file.owner != (owner or frappe.session.user)
		or (batch_name is None and file.attached_to_doctype)
		or (
			batch_name is not None
			and (file.attached_to_doctype != "WA Import Batch" or file.attached_to_name != batch_name)
		)
		or not frappe.has_permission("File", "read", doc=file)
	):
		raise CommandError("NOT_FOUND")
	content = file.get_content()
	if not isinstance(content, bytes):
		content = str(content or "").encode("utf-8")
	return content


def create_batch(source_file: str, mapping: Any) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	company = _company()
	content = _file_bytes(source_file)
	try:
		rows, digest = parse_csv(content, mapping)
	except ValueError as exc:
		raise CommandError("INVALID_INPUT", "mapping") from exc
	actor = frappe.session.user
	batch = frappe.get_doc(
		{
			"doctype": "WA Import Batch",
			"company": company,
			"source_file": source_file,
			"mapping_json": json.dumps(mapping, sort_keys=True),
			"status": "Preview Ready",
			"row_count": len(rows),
			"valid_count": sum(row["status"] == "Valid" for row in rows),
			"rejected_count": sum(row["status"] == "Invalid" for row in rows),
			"evidence_missing_count": sum(
				row["status"] == "Valid" and not row.get("consent_evidence") for row in rows
			),
			"requested_by": actor,
			"input_hash": digest,
		}
	)
	batch.db_insert()
	frappe.db.set_value(
		"File",
		source_file,
		{
			"attached_to_doctype": "WA Import Batch",
			"attached_to_name": batch.name,
			"attached_to_field": "source_file",
		},
		update_modified=False,
	)
	_save_diagnostics(batch.name, rows)
	for row in rows:
		projection = {
			key: row[key]
			for key in ("phone_e164", "display_name", "consent_evidence")
			if row.get(key) is not None
		}
		frappe.get_doc(
			{
				"doctype": "WA Import Row",
				"company": company,
				"batch": batch.name,
				"row_number": row["row_number"],
				"input_hash": digest,
				"row_hash": hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest(),
				"status": row["status"],
				"error_code": row.get("error_code"),
				"projection_json": json.dumps(projection, sort_keys=True),
			}
		).db_insert()
	return {
		"batch": batch.name,
		"input_hash": digest,
		"row_count": len(rows),
		"valid_count": batch.valid_count,
		"rejected_count": batch.rejected_count,
		"evidence_missing_count": batch.evidence_missing_count,
		"preview": [
			{
				"row_number": row["row_number"],
				"status": row["status"],
				"error_code": row.get("error_code"),
				"consent_evidence": "provided" if row.get("consent_evidence") else "missing",
			}
			for row in rows[:100]
		],
	}


def inspect_file(source_file: str) -> dict[str, list[str]]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	content = _file_bytes(source_file)
	try:
		return {"columns": csv_headers(content)}
	except ValueError as exc:
		raise CommandError("INVALID_INPUT", "source_file") from exc


def consent_history(contact_name: str, start: int = 0, page_length: int = 20) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	contact = _authorized_contact(contact_name)
	if (
		not isinstance(start, int)
		or not 0 <= start <= 10_000
		or not isinstance(page_length, int)
		or not 1 <= page_length <= 100
	):
		raise CommandError("INVALID_INPUT")
	rows = frappe.get_list(
		"WA Consent Event",
		filters={"contact": contact.name, "company": contact.company, "purpose": "Marketing"},
		fields=[
			"name",
			"event_type",
			"occurred_at",
			"recorded_at",
			"source",
			"notice_version",
			"evidence_reference",
			"evidence_file",
			"recorded_by",
		],
		order_by="occurred_at desc, creation desc",
		start=start,
		page_length=page_length + 1,
	)
	return {"items": rows[:page_length], "has_more": len(rows) > page_length}


def _save_diagnostics(batch_name: str, rows: list[dict[str, Any]]) -> None:
	invalid = [row for row in rows if row["status"] == "Invalid"]
	if not invalid:
		return
	stream = io.StringIO(newline="")
	writer = csv.writer(stream)
	writer.writerow(("row_number", "error_code"))
	for row in invalid:
		writer.writerow((safe_csv_cell(row["row_number"]), safe_csv_cell(row["error_code"])))
	file_doc = save_file(
		f"{batch_name}-diagnostics.csv",
		stream.getvalue().encode("utf-8"),
		"WA Import Batch",
		batch_name,
		is_private=1,
	)
	frappe.db.set_value("WA Import Batch", batch_name, "result_file", file_doc.name, update_modified=False)


def validate_batch(batch_name: str, expected_modified: str, request_id: str) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	batch = _authorized_batch(batch_name)
	if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
		raise CommandError("INVALID_INPUT", "request_id")
	operation, created = _begin_operation(
		"imports.validate_batch", batch, request_id, {"expected_modified": expected_modified}
	)
	if not created:
		return {
			"batch": batch.name,
			"operation": operation.name,
			"status": operation.status,
			"input_hash": batch.input_hash,
		}
	require_revision(str(batch.modified), expected_modified)
	content = _file_bytes(batch.source_file, batch_name=batch.name, owner=batch.requested_by)
	try:
		rows, digest = parse_csv(content, frappe.parse_json(batch.mapping_json))
	except ValueError as exc:
		raise CommandError("INVALID_INPUT", "mapping") from exc
	if digest == batch.input_hash and batch.status == "Preview Ready":
		_finish_operation(
			operation.name,
			{
				"input_hash": digest,
				"valid_count": batch.valid_count,
				"rejected_count": batch.rejected_count,
				"evidence_missing_count": batch.evidence_missing_count,
			},
		)
		return {
			"batch": batch.name,
			"operation": operation.name,
			"input_hash": digest,
			"status": batch.status,
		}
	# Revalidation creates a new ledger version; old rows remain immutable/auditable.
	for row in rows:
		projection = {
			key: row[key]
			for key in ("phone_e164", "display_name", "consent_evidence")
			if row.get(key) is not None
		}
		if frappe.db.exists(
			"WA Import Row", {"batch": batch.name, "row_number": row["row_number"], "input_hash": digest}
		):
			continue
		frappe.get_doc(
			{
				"doctype": "WA Import Row",
				"company": batch.company,
				"batch": batch.name,
				"row_number": row["row_number"],
				"input_hash": digest,
				"row_hash": hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest(),
				"status": row["status"],
				"error_code": row.get("error_code"),
				"projection_json": json.dumps(projection, sort_keys=True),
			}
		).db_insert()
	evidence_missing = sum(r["status"] == "Valid" and not r.get("consent_evidence") for r in rows)
	frappe.db.set_value(
		"WA Import Batch",
		batch.name,
		{
			"input_hash": digest,
			"status": "Preview Ready",
			"row_count": len(rows),
			"valid_count": sum(r["status"] == "Valid" for r in rows),
			"rejected_count": sum(r["status"] == "Invalid" for r in rows),
			"evidence_missing_count": evidence_missing,
		},
	)
	_finish_operation(
		operation.name,
		{
			"input_hash": digest,
			"valid_count": batch.valid_count,
			"rejected_count": batch.rejected_count,
			"evidence_missing_count": evidence_missing,
		},
	)
	return {
		"batch": batch.name,
		"operation": operation.name,
		"input_hash": digest,
		"status": "Preview Ready",
		"evidence_missing_count": evidence_missing,
	}


def confirm_batch(batch_name: str, digest: str, expected_modified: str, request_id: str) -> dict[str, Any]:
	require_capability(frozenset({"Marketing User", "Marketing Manager"}))
	batch = _authorized_batch(batch_name)
	if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
		raise CommandError("INVALID_INPUT", "request_id")
	if batch.input_hash != digest:
		raise CommandError("STALE_DOCUMENT")
	if batch.status == "Completed" and batch.input_hash == digest:
		return {
			"batch": batch.name,
			"operation": batch.operation,
			"status": batch.status,
			"imported_count": frappe.db.count(
				"WA Import Row", {"batch": batch.name, "input_hash": digest, "status": "Imported"}
			),
			"suppressed_count": frappe.db.count(
				"WA Import Row", {"batch": batch.name, "input_hash": digest, "status": "Suppressed"}
			),
		}
	if batch.status == "Importing" and batch.operation:
		return {"batch": batch.name, "operation": batch.operation, "status": batch.status}
	require_revision(str(batch.modified), expected_modified)
	content = _file_bytes(batch.source_file, batch_name=batch.name, owner=batch.requested_by)
	try:
		_, current_hash = parse_csv(content, frappe.parse_json(batch.mapping_json))
	except ValueError as exc:
		raise CommandError("INVALID_INPUT", "mapping") from exc
	if current_hash != digest or current_hash != batch.input_hash:
		raise CommandError("STALE_DOCUMENT")
	operation, created = _begin_operation(
		"imports.confirm_batch", batch, request_id, {"input_hash": digest}, status="Pending"
	)
	if not created:
		return {"batch": batch.name, "operation": operation.name, "status": operation.status}
	frappe.db.set_value("WA Import Batch", batch.name, {"status": "Importing", "operation": operation.name})
	frappe.enqueue(
		"tag_marketing.application.import_jobs.run_import_operation",
		queue="marketing",
		timeout=3600,
		enqueue_after_commit=True,
		job_id=f"wa-import:{operation.name}",
		deduplicate=True,
		operation_id=operation.name,
	)
	return {
		"batch": batch.name,
		"operation": operation.name,
		"status": "Importing",
		"rejected_count": batch.rejected_count,
	}


def _begin_operation(
	operation_type: str,
	batch: Any,
	request_id: str,
	request: dict[str, Any],
	*,
	status: str = "Running",
) -> tuple[Any, bool]:
	request_hash = hashlib.sha256(
		json.dumps(
			{"operation": operation_type, "batch": batch.name, **request},
			sort_keys=True,
			separators=(",", ":"),
		).encode()
	).hexdigest()
	filters = {
		"requested_by": frappe.session.user,
		"operation_type": operation_type,
		"request_id": request_id,
	}
	prior = frappe.db.get_value("WA Operation", filters, ["name", "request_hash", "status"], as_dict=True)
	if prior:
		if prior.request_hash != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return prior, False
	doc = frappe.get_doc(
		{
			"doctype": "WA Operation",
			"company": batch.company,
			"operation_type": operation_type,
			"requested_by": frappe.session.user,
			"request_id": request_id,
			"request_hash": request_hash,
			"request_json": json.dumps(request, sort_keys=True),
			"attempt_count": 0,
			"status": status,
			"progress_percent": 0 if status == "Pending" else 5,
			"target_doctype": "WA Import Batch",
			"target_name": batch.name,
			"heartbeat_at": _now(),
		}
	)
	try:
		doc.db_insert()
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		prior = frappe.db.get_value("WA Operation", filters, ["name", "request_hash", "status"], as_dict=True)
		if not prior:
			raise
		if prior.request_hash != request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT") from None
		return prior, False
	frappe.db.set_value("WA Import Batch", batch.name, "operation", doc.name, update_modified=False)
	return doc, True


def _finish_operation(operation_name: str, result: dict[str, Any]) -> None:
	frappe.db.set_value(
		"WA Operation",
		operation_name,
		{
			"status": "Succeeded",
			"progress_percent": 100,
			"result_json": json.dumps(result, sort_keys=True),
			"heartbeat_at": _now(),
		},
		update_modified=False,
	)


def record_consent(
	contact_name: str,
	event_type: str,
	occurred_at: str,
	source: str,
	notice_version: str = "",
	evidence_reference: str = "",
	evidence_file: str | None = None,
	request_id: str = "",
) -> dict[str, Any]:
	roles = set(frappe.get_roles())
	if event_type == "Granted":
		require_capability(frozenset({"Marketing User", "Marketing Manager"}))
		if source not in {"Web Form", "CSV Evidence", "Agent Recorded"}:
			raise CommandError("INVALID_INPUT", "source")
	elif event_type == "Withdrawn":
		if not roles.intersection(
			{"Marketing User", "Marketing Manager", "WhatsApp Agent", "System Manager"}
		):
			frappe.throw(_("You cannot record a withdrawal."), frappe.PermissionError)
	else:
		raise CommandError("INVALID_INPUT", "event_type")
	contact = _authorized_contact(contact_name)
	if source not in {"Web Form", "CSV Evidence", "Agent Recorded", "Inbound Keyword", "Unsubscribe Button"}:
		raise CommandError("INVALID_INPUT", "source")
	try:
		occurred = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
		occurred = occurred.replace(tzinfo=UTC) if occurred.tzinfo is None else occurred.astimezone(UTC)
	except (ValueError, AttributeError):
		raise CommandError("INVALID_INPUT", "occurred_at") from None
	if occurred > datetime.now(UTC) + timedelta(minutes=5):
		raise CommandError("INVALID_INPUT", "occurred_at")
	if event_type == "Granted" and (
		not notice_version.strip() or (not evidence_reference.strip() and not evidence_file)
	):
		raise CommandError("READINESS_FAILED")
	if evidence_file:
		_file_evidence(evidence_file, contact.name)
	if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
		raise CommandError("INVALID_INPUT", "request_id")
	key = hashlib.sha256(f"manual|{frappe.session.user}|{request_id}".encode()).hexdigest()
	return _record_event(
		contact,
		event_type,
		occurred.replace(tzinfo=None),
		source,
		notice_version,
		evidence_reference,
		evidence_file,
		key,
	)


def _evidence_grant(batch: Any, contact_name: str, evidence: Any, digest: str, row_number: int) -> None:
	if not evidence:
		return
	contact = frappe.get_doc("WA Contact", contact_name)
	# Identical evidence for a duplicate identity in the same or a later import is one grant.
	key = hashlib.sha256(
		(
			"csv|"
			+ "|".join(
				(
					contact.company,
					contact.phone_e164,
					evidence["occurred_at"],
					evidence["notice_version"],
					evidence["reference"],
				)
			)
		).encode()
	).hexdigest()
	_record_event(
		contact,
		"Granted",
		datetime.fromisoformat(evidence["occurred_at"]),
		"CSV Evidence",
		evidence["notice_version"],
		evidence["reference"],
		None,
		key,
	)


def _record_event(
	contact: Any,
	event_type: str,
	occurred: datetime,
	source: str,
	notice: str,
	reference: str,
	evidence_file: str | None,
	key: str,
) -> dict[str, Any]:
	# Shared with P4 reservations so a committed withdrawal closes the send gate.
	lock_contact_for_change(contact.company, contact.name)
	if frappe.db.exists("WA Consent Event", {"source_event_key": key}):
		prior = frappe.db.get_value(
			"WA Consent Event",
			{"source_event_key": key},
			[
				"name",
				"contact",
				"event_type",
				"occurred_at",
				"source",
				"notice_version",
				"evidence_reference",
				"evidence_file",
			],
			as_dict=True,
		)
		if not prior or (
			prior.contact,
			prior.event_type,
			str(prior.occurred_at),
			prior.source,
			prior.notice_version or "",
			prior.evidence_reference or "",
			prior.evidence_file or "",
		) != (
			contact.name,
			event_type,
			str(occurred),
			source,
			notice or "",
			reference.strip() or ("Documented withdrawal" if event_type == "Withdrawn" else ""),
			evidence_file or "",
		):
			raise CommandError("IDEMPOTENCY_CONFLICT")
		return {"event": prior.name, "consent_status": contact.consent_status, "replayed": True}
	event = frappe.get_doc(
		{
			"doctype": "WA Consent Event",
			"company": contact.company,
			"contact": contact.name,
			"purpose": "Marketing",
			"event_type": event_type,
			"occurred_at": occurred,
			"recorded_at": _now(),
			"source": source,
			"notice_version": notice or None,
			"evidence_file": evidence_file,
			"evidence_reference": reference.strip()
			or ("Documented withdrawal" if event_type == "Withdrawn" else ""),
			"source_event_key": key,
			"recorded_by": frappe.session.user,
		}
	)
	event.db_insert()
	if event_type == "Withdrawn":
		_suppress(contact, "Opt Out", event.name)
	consent = _effective(contact.name)
	frappe.db.set_value(
		"WA Contact",
		contact.name,
		{
			"consent_status": consent,
			"suppressed": int(
				bool(
					frappe.db.get_value(
						"WA Suppression",
						{"company": contact.company, "contact": contact.name, "purpose": "Marketing"},
						"active",
					)
				)
			),
		},
		update_modified=False,
	)
	_audit(contact, "Consent " + event_type, {"event": event.name, "source": source})
	return {"event": event.name, "consent_status": consent, "replayed": False}


def _effective(contact_name: str) -> str:
	events = frappe.get_all(
		"WA Consent Event",
		filters={"contact": contact_name, "purpose": "Marketing"},
		fields=["event_type", "occurred_at"],
		order_by="occurred_at asc, creation asc",
	)
	latest = None
	for item in events:
		instant = frappe.utils.get_datetime(item.occurred_at)
		candidate = (instant, 1 if item.event_type == "Withdrawn" else 0, item.event_type)
		if latest is None or candidate[:2] > latest[:2]:
			latest = candidate
	return "Unknown" if latest is None else ("Withdrawn" if latest[2] == "Withdrawn" else "Granted")


def set_suppression(
	contact_name: str, active: bool, reason: str, expected_modified: str, request_id: str
) -> dict[str, Any]:
	roles = set(frappe.get_roles())
	if "Marketing Manager" not in roles and "System Manager" not in roles:
		frappe.throw(_("Only Marketing Managers may change suppression."), frappe.PermissionError)
	contact = _authorized_contact(contact_name)
	if (
		not isinstance(active, bool)
		or reason not in {"Opt Out", "Manual Block", "Invalid Address"}
		or not isinstance(request_id, str)
		or not 8 <= len(request_id) <= 128
	):
		raise CommandError("INVALID_INPUT")
	request_hash = hashlib.sha256(f"suppression|{frappe.session.user}|{request_id}".encode()).hexdigest()
	prior = frappe.db.sql(
		"""SELECT name FROM `tabWA Audit Event` WHERE company=%s AND target_doctype='WA Contact'
		AND target_name=%s AND action=%s AND details_json LIKE %s ORDER BY creation DESC LIMIT 1""",
		(
			contact.company,
			contact.name,
			"Suppression " + ("Enabled" if active else "Released"),
			f"%{request_hash}%",
		),
	)
	if prior:
		return {"contact": contact.name, "suppressed": active, "audit_id": prior[0][0], "replayed": True}
	require_revision(str(contact.modified), expected_modified)
	lock_contact_for_change(contact.company, contact.name)
	if not active and reason == "Opt Out" and _effective(contact.name) != "Granted":
		raise CommandError("READINESS_FAILED")
	_suppress(contact, reason, None, active=active)
	frappe.db.set_value("WA Contact", contact.name, {"suppressed": int(active)}, update_modified=False)
	audit_id = _audit(
		contact,
		"Suppression " + ("Enabled" if active else "Released"),
		{"reason": reason, "request_hash": request_hash},
	)
	return {"contact": contact.name, "suppressed": active, "audit_id": audit_id, "replayed": False}


def _suppress(contact: Any, reason: str, event_name: str | None, active: bool = True) -> None:
	name = frappe.db.get_value(
		"WA Suppression",
		{"company": contact.company, "contact": contact.name, "purpose": "Marketing"},
		"name",
	)
	identity_digest = digest_for_identity(contact.company, contact.phone_e164)
	values = {
		"reason": reason,
		"active": int(active),
		"consent_event": event_name,
		"identity_digest": identity_digest,
		"changed_at": _now(),
		"changed_by": frappe.session.user,
	}
	if name:
		frappe.db.set_value("WA Suppression", name, values, update_modified=False)
	else:
		frappe.get_doc(
			{
				"doctype": "WA Suppression",
				"company": contact.company,
				"contact": contact.name,
				"purpose": "Marketing",
				**values,
			}
		).db_insert()


def _authorized_batch(name: str) -> Any:
	company = _company()
	batch = frappe.db.get_value(
		"WA Import Batch",
		name,
		[
			"name",
			"company",
			"source_file",
			"mapping_json",
			"status",
			"modified",
			"requested_by",
			"input_hash",
			"operation",
			"valid_count",
			"rejected_count",
			"evidence_missing_count",
		],
		as_dict=True,
	)
	if (
		not batch
		or batch.company != company
		or not company_allowed(company, frappe.session.user, "WA Import Batch")
		or (batch.requested_by != frappe.session.user and "Marketing Manager" not in frappe.get_roles())
	):
		raise CommandError("NOT_FOUND")
	return batch


def _authorized_contact(name: str) -> Any:
	company = _company()
	if not frappe.has_permission("WA Contact", "read", doc=name):
		raise CommandError("NOT_FOUND")
	contact = frappe.get_doc("WA Contact", name)
	if contact.company != company or not company_allowed(company, frappe.session.user, "WA Contact"):
		raise CommandError("NOT_FOUND")
	return contact


def _file_evidence(name: str, contact_name: str) -> None:
	file = frappe.get_doc("File", name)
	if (
		file.is_private != 1
		or not frappe.has_permission("File", "read", doc=file)
		or file.attached_to_doctype != "WA Contact"
		or file.attached_to_name != contact_name
	):
		raise CommandError("NOT_FOUND")


def _audit(contact: Any, action: str, details: dict[str, Any]) -> str:
	doc = frappe.get_doc(
		{
			"doctype": "WA Audit Event",
			"company": contact.company,
			"action": action,
			"actor": frappe.session.user,
			"target_doctype": "WA Contact",
			"target_name": contact.name,
			"occurred_at": _now(),
			"details_json": json.dumps(details, sort_keys=True),
		}
	)
	doc.db_insert()
	return doc.name
