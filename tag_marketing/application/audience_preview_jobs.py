"""Durable workers for audience previews that exceed the synchronous query budget."""

import json
from datetime import timedelta
from typing import Any

import frappe

from tag_marketing.domain.errors import CommandError
from tag_marketing.infrastructure.permissions import company_allowed

OPERATION_TYPE = "audiences.preview"
RECOVERY_BATCH = 100
REQUEUE_AFTER = timedelta(minutes=1)
STALE_AFTER = timedelta(minutes=5)
MAX_ATTEMPTS = 5
PROGRESS_INTERVAL = 5_000


def run_audience_preview_operation(operation_id: str) -> None:
	"""Claim and compute one preview under its initiating actor's current permissions."""
	frappe.db.sql(
		"""UPDATE `tabWA Operation`
		SET status = 'Running', attempt_count = COALESCE(attempt_count, 0) + 1,
			progress_percent = 1, heartbeat_at = NOW(), modified = NOW(), modified_by = %s
		WHERE name = %s AND status = 'Pending' AND operation_type = %s""",
		(frappe.session.user, operation_id, OPERATION_TYPE),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		return
	frappe.db.commit()
	operation = frappe.get_doc("WA Operation", operation_id)
	previous_user = frappe.session.user
	try:
		request = operation.request_json
		if isinstance(request, str):
			request = frappe.parse_json(request)
		if not isinstance(request, dict):
			_finish(operation.name, "RECOVERY_UNAVAILABLE")
			return
		company = frappe.db.get_single_value("WA Settings", "marketing_company")
		actor = operation.requested_by
		if (
			operation.company != company
			or operation.target_doctype != "WA Audience Segment"
			or not company_allowed(company, actor, "WA Contact")
			or not {"Marketing User", "Marketing Manager"}.intersection(frappe.get_roles(actor))
		):
			_finish(operation.name, "SCOPE_CHANGED")
			return
		frappe.set_user(actor)
		segment = frappe.get_doc("WA Audience Segment", operation.target_name)
		if (
			segment.company != company
			or segment.disabled
			or not segment.has_permission("read")
			or str(segment.modified) != str(request.get("expected_modified"))
		):
			_finish(operation.name, "STALE_DOCUMENT")
			return
		candidate_count = request.get("candidate_count")
		if not isinstance(candidate_count, int) or not 2_000 < candidate_count <= 50_000:
			_finish(operation.name, "RECOVERY_UNAVAILABLE")
			return
		limit = request.get("limit")
		cursor = request.get("cursor", "")
		if not isinstance(limit, int) or not isinstance(cursor, str):
			_finish(operation.name, "RECOVERY_UNAVAILABLE")
			return
		last_progress = 0

		def progress(scanned: int) -> None:
			nonlocal last_progress
			if scanned - last_progress < PROGRESS_INTERVAL and scanned < candidate_count:
				return
			last_progress = scanned
			percent = min(95, 5 + int(88 * min(scanned, candidate_count) / candidate_count))
			frappe.db.set_value(
				"WA Operation",
				operation.name,
				{"progress_percent": percent, "heartbeat_at": frappe.utils.now_datetime()},
				update_modified=False,
			)
			frappe.db.commit()

		from tag_marketing.application.audience_segments import preview

		result = preview(
			operation.target_name,
			request.get("exclusions"),
			limit,
			cursor,
			on_progress=progress,
		)
		frappe.db.set_value(
			"WA Operation",
			operation.name,
			{
				"status": "Succeeded",
				"progress_percent": 100,
				"result_json": json.dumps(result, sort_keys=True, default=str),
				"heartbeat_at": frappe.utils.now_datetime(),
			},
			update_modified=False,
		)
		frappe.db.commit()
	except CommandError as error:
		frappe.db.rollback()
		_finish(operation.name, error.code)
	except Exception as error:
		frappe.db.rollback()
		if isinstance(error, frappe.ValidationError):
			_finish(operation.name, "INVALID_INPUT")
		else:
			# Keep the lease recoverable; never expose request data or exception text.
			frappe.logger("tag_marketing").error(
				"Audience preview operation %s interrupted (%s)", operation_id, type(error).__name__
			)
	finally:
		if frappe.session.user != previous_user:
			frappe.set_user(previous_user)


def recover_audience_preview_operations() -> None:
	"""Requeue lost jobs and recover stale claims with a fixed retry ceiling."""
	try:
		now = frappe.utils.now_datetime()
		stale_before = now - STALE_AFTER
		stale = frappe.get_all(
			"WA Operation",
			filters={
				"operation_type": OPERATION_TYPE,
				"status": "Running",
				"heartbeat_at": ["<", stale_before],
			},
			fields=["name", "attempt_count"],
			limit=RECOVERY_BATCH,
		)
		for operation in stale:
			status = "Pending" if int(operation.attempt_count or 0) < MAX_ATTEMPTS else "Failed"
			frappe.db.set_value(
				"WA Operation",
				operation.name,
				{
					"status": status,
					"error_code": None if status == "Pending" else "OPERATION_INTERRUPTED",
					"heartbeat_at": now,
				},
				update_modified=False,
			)
			frappe.db.commit()
			if status == "Pending":
				_enqueue(operation.name)
		ready_before = now - REQUEUE_AFTER
		pending = frappe.get_all(
			"WA Operation",
			filters={"operation_type": OPERATION_TYPE, "status": "Pending", "modified": ["<", ready_before]},
			fields=["name"],
			limit=RECOVERY_BATCH,
		)
		for operation in pending:
			frappe.db.sql(
				"""UPDATE `tabWA Operation` SET modified = NOW(), modified_by = %s
				WHERE name = %s AND status = 'Pending' AND modified < %s""",
				(frappe.session.user, operation.name, ready_before),
			)
			if frappe.db.sql("SELECT ROW_COUNT()")[0][0] == 1:
				frappe.db.commit()
				_enqueue(operation.name)
	except Exception as error:
		frappe.db.rollback()
		frappe.logger("tag_marketing").error("Audience preview recovery failed (%s)", type(error).__name__)


def _finish(operation: str, error_code: str) -> None:
	frappe.db.set_value(
		"WA Operation",
		operation,
		{
			"status": "Failed",
			"error_code": error_code,
			"progress_percent": 100,
			"heartbeat_at": frappe.utils.now_datetime(),
		},
		update_modified=False,
	)
	frappe.db.commit()


def _enqueue(operation: str) -> None:
	frappe.enqueue(
		"tag_marketing.application.audience_preview_jobs.run_audience_preview_operation",
		queue="marketing",
		timeout=900,
		enqueue_after_commit=True,
		job_id=f"wa-audience-preview:{operation}",
		deduplicate=True,
		operation_id=operation,
	)
