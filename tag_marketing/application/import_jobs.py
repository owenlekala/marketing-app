"""Durable, resumable private contact-import workers."""

import hashlib
import json
from datetime import timedelta
from typing import Any

import frappe

from tag_marketing.application.imports import _evidence_grant, _file_bytes
from tag_marketing.application.suppression import is_identity_suppressed
from tag_marketing.domain.imports import parse_csv
from tag_marketing.infrastructure.permissions import company_allowed

CLAIM_CHUNK = 100
RECOVERY_BATCH = 100
STALE_AFTER = timedelta(minutes=5)
REQUEUE_AFTER = timedelta(minutes=1)
MAX_ATTEMPTS = 5


def run_import_operation(operation_id: str) -> None:
	"""Import ledger rows in committed chunks; completed rows make retries safe."""
	frappe.db.sql(
		"""
		UPDATE `tabWA Operation`
		SET status = 'Running', attempt_count = COALESCE(attempt_count, 0) + 1,
			progress_percent = GREATEST(progress_percent, 1), heartbeat_at = NOW(), modified = NOW(), modified_by = %s
		WHERE name = %s AND status = 'Pending' AND operation_type = 'imports.confirm_batch'
		""",
		(frappe.session.user, operation_id),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		return
	frappe.db.commit()
	operation = frappe.get_doc("WA Operation", operation_id)
	try:
		batch = frappe.get_doc("WA Import Batch", operation.target_name)
		request = operation.request_json
		if isinstance(request, str):
			request = frappe.parse_json(request)
		if (
			batch.operation != operation.name
			or batch.status != "Importing"
			or batch.company != operation.company
			or batch.requested_by != operation.requested_by
			or not _actor_still_authorized(operation.requested_by, batch.company)
			or frappe.db.get_single_value("WA Settings", "marketing_company") != batch.company
		):
			_finish(operation, batch, "SCOPE_CHANGED")
			return
		try:
			content = _file_bytes(batch.source_file, batch_name=batch.name, owner=batch.requested_by)
			rows, digest = parse_csv(content, frappe.parse_json(batch.mapping_json))
		except ValueError:
			_finish(operation, batch, "INVALID_INPUT")
			return
		if not isinstance(request, dict) or digest != batch.input_hash or digest != request.get("input_hash"):
			_finish(operation, batch, "STALE_DOCUMENT")
			return
		valid_rows = [row for row in rows if row["status"] == "Valid"]
		imported = int(
			frappe.db.count(
				"WA Import Row", {"batch": batch.name, "input_hash": digest, "status": "Imported"}
			)
		)
		for offset in range(0, len(valid_rows), CLAIM_CHUNK):
			chunk = valid_rows[offset : offset + CLAIM_CHUNK]
			for row in chunk:
				if _import_row(batch, digest, row):
					imported += 1
			percent = 10 + int(85 * min(offset + len(chunk), len(valid_rows)) / max(1, len(valid_rows)))
			frappe.db.set_value(
				"WA Operation",
				operation.name,
				{"progress_percent": min(95, percent), "heartbeat_at": frappe.utils.now_datetime()},
				update_modified=False,
			)
			frappe.db.commit()
		frappe.db.set_value(
			"WA Import Batch", batch.name, {"status": "Completed", "operation": operation.name}
		)
		_finish(
			operation,
			batch,
			None,
			result={
				"imported_count": imported,
				"suppressed_count": int(
					frappe.db.count("WA Import Row", {"batch": batch.name, "status": "Suppressed"})
				),
				"rejected_count": batch.rejected_count,
			},
		)
		frappe.db.commit()
	except Exception as exc:
		frappe.db.rollback()
		# Keep a durable Running lease so the scheduled recovery scan can resume
		# from the last committed ledger row without exposing data or exception text.
		frappe.logger("tag_marketing").error(
			"Import operation %s interrupted (%s)", operation_id, type(exc).__name__
		)


def recover_import_operations() -> None:
	"""Recover queue loss and stale workers from durable operation/row state."""
	try:
		_now = frappe.utils.now_datetime()
		stale_before = _now - STALE_AFTER
		stale = frappe.get_all(
			"WA Operation",
			filters={
				"status": "Running",
				"target_doctype": "WA Import Batch",
				"operation_type": "imports.confirm_batch",
				"heartbeat_at": ["<", stale_before],
			},
			fields=["name", "attempt_count"],
			limit=RECOVERY_BATCH,
		)
		for operation in stale:
			status = "Pending" if int(operation.attempt_count or 0) < MAX_ATTEMPTS else "Failed"
			frappe.db.sql(
				"""
				UPDATE `tabWA Operation`
				SET status = %s, error_code = %s, heartbeat_at = NOW(), modified = NOW(), modified_by = %s
				WHERE name = %s AND status = 'Running' AND heartbeat_at < %s
				""",
				(
					status,
					None if status == "Pending" else "OPERATION_INTERRUPTED",
					frappe.session.user,
					operation.name,
					stale_before,
				),
			)
			frappe.db.commit()
			if status == "Pending":
				_enqueue(operation.name)
			else:
				frappe.db.set_value(
					"WA Import Batch",
					frappe.db.get_value("WA Operation", operation.name, "target_name"),
					"status",
					"Failed",
				)
				frappe.db.commit()
		ready_before = _now - REQUEUE_AFTER
		pending = frappe.get_all(
			"WA Operation",
			filters={
				"status": "Pending",
				"target_doctype": "WA Import Batch",
				"operation_type": "imports.confirm_batch",
				"modified": ["<", ready_before],
			},
			fields=["name"],
			limit=RECOVERY_BATCH,
		)
		for operation in pending:
			frappe.db.sql(
				"""
				UPDATE `tabWA Operation` SET modified = NOW(), modified_by = %s
				WHERE name = %s AND status = 'Pending' AND modified < %s
				""",
				(frappe.session.user, operation.name, ready_before),
			)
			if frappe.db.sql("SELECT ROW_COUNT()")[0][0] == 1:
				frappe.db.commit()
				_enqueue(operation.name)
	except Exception as exc:
		frappe.db.rollback()
		frappe.logger("tag_marketing").error("Import recovery scan failed (%s)", type(exc).__name__)


def _enqueue(operation_id: str) -> None:
	frappe.enqueue(
		"tag_marketing.application.import_jobs.run_import_operation",
		queue="marketing",
		timeout=3600,
		enqueue_after_commit=True,
		job_id=f"wa-import:{operation_id}",
		deduplicate=True,
		operation_id=operation_id,
	)


def _import_row(batch: Any, digest: str, row: dict[str, Any]) -> bool:
	ledger = frappe.db.get_value(
		"WA Import Row",
		{"batch": batch.name, "row_number": row["row_number"], "input_hash": digest},
		["name", "status", "projection_json"],
		as_dict=True,
	)
	if not ledger:
		raise RuntimeError("missing import ledger row")
	if ledger.status in {"Imported", "Suppressed"}:
		return False
	projection = frappe.parse_json(ledger.projection_json)
	if is_identity_suppressed(batch.company, projection["phone_e164"], lock=True):
		frappe.db.set_value(
			"WA Import Row",
			ledger.name,
			{"status": "Suppressed", "error_code": "ACTIVE_SUPPRESSION"},
			update_modified=False,
		)
		return False
	contact_name = frappe.db.get_value(
		"WA Contact", {"company": batch.company, "phone_e164": projection["phone_e164"]}, "name"
	)
	if not contact_name:
		point = "wa_import_" + hashlib.sha256(f"{batch.name}:{row['row_number']}".encode()).hexdigest()[:16]
		frappe.db.savepoint(point)
		try:
			contact = frappe.get_doc(
				{
					"doctype": "WA Contact",
					"company": batch.company,
					"phone_e164": projection["phone_e164"],
					"display_name": projection["display_name"],
					"consent_status": "Unknown",
					"suppressed": 0,
					"archived": 0,
				}
			)
			contact.flags.wa_import_command = True
			contact.db_insert()
			contact_name = contact.name
		except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
			frappe.db.rollback(save_point=point)
			contact_name = frappe.db.get_value(
				"WA Contact", {"company": batch.company, "phone_e164": projection["phone_e164"]}, "name"
			)
			if not contact_name:
				raise
	_evidence_grant(batch, contact_name, projection.get("consent_evidence"), digest, row["row_number"])
	frappe.db.set_value(
		"WA Import Row", ledger.name, {"contact": contact_name, "status": "Imported"}, update_modified=False
	)
	return True


def _finish(operation: Any, batch: Any, error: str | None, *, result: dict[str, Any] | None = None) -> None:
	status = "Failed" if error else "Succeeded"
	frappe.db.set_value(
		"WA Import Batch",
		batch.name,
		{"status": "Failed" if error else "Completed", "operation": operation.name},
	)
	frappe.db.set_value(
		"WA Operation",
		operation.name,
		{
			"status": status,
			"progress_percent": 100 if not error else operation.progress_percent,
			"error_code": error,
			"result_json": json.dumps(result, sort_keys=True) if result else None,
			"heartbeat_at": frappe.utils.now_datetime(),
		},
		update_modified=False,
	)
	frappe.db.commit()


def _actor_still_authorized(user: str, company: str) -> bool:
	if not frappe.db.get_value("User", user, "enabled"):
		return False
	if frappe.db.get_value("User", user, "user_type") != "System User":
		return False
	return bool(
		set(frappe.get_roles(user)).intersection({"Marketing User", "Marketing Manager"})
		and company_allowed(company, user, "WA Import Batch")
	)
