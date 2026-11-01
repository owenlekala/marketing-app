"""Scheduled recovery policy for durable webhook receipts and setup operations."""

import json
from datetime import timedelta
from typing import Any

import frappe

RECOVERY_BATCH = 100
WEBHOOK_STALE_AFTER = timedelta(minutes=5)
OPERATION_STALE_AFTER = timedelta(minutes=5)
READY_REQUEUE_AFTER = timedelta(minutes=1)
WEBHOOK_RETRY_DELAYS = (1, 5, 15, 60)
MAX_WEBHOOK_ATTEMPTS = 5
MAX_OPERATION_ATTEMPTS = 2
CONNECTION_OPERATIONS = {
	"connections.validate_connection": "validate_connection",
	"connections.sync_numbers": "sync_numbers",
	"connections.sync_templates": "sync_templates",
	"connections.set_enabled": "set_enabled",
}


def recover_due_work() -> None:
	"""Re-enqueue eligible durable work; never retries provider message submissions."""
	try:
		_recover_webhooks()
		_recover_connection_operations()
	except Exception as exc:
		frappe.db.rollback()
		frappe.logger("tag_marketing").error("Marketing recovery scan failed (%s)", type(exc).__name__)


def _recover_webhooks() -> None:
	now = frappe.utils.now_datetime()
	stale_before = now - WEBHOOK_STALE_AFTER
	ready_before = now - READY_REQUEUE_AFTER
	# A worker that died after claim left a durable Processing lease. Reclassify it
	# as Failed; the normal bounded-delay policy below decides whether it is retried.
	frappe.db.sql(
		"""
		UPDATE `tabWA Webhook Event`
		SET status = 'Failed', error_code = 'PROCESSING_INTERRUPTED', modified = NOW(), modified_by = %s
		WHERE status = 'Processing' AND modified < %s
		""",
		(frappe.session.user, stale_before),
	)
	frappe.db.commit()

	failed = frappe.get_all(
		"WA Webhook Event",
		filters={"status": "Failed", "attempt_count": ["<", MAX_WEBHOOK_ATTEMPTS], "modified": ["<", now]},
		fields=["name", "attempt_count", "modified"],
		order_by="modified asc",
		limit=RECOVERY_BATCH,
	)
	for event in failed:
		attempt = max(1, int(event.attempt_count or 1))
		delay = WEBHOOK_RETRY_DELAYS[min(attempt - 1, len(WEBHOOK_RETRY_DELAYS) - 1)]
		if frappe.utils.get_datetime(event.modified) + timedelta(minutes=delay) > now:
			continue
		frappe.db.sql(
			"""
			UPDATE `tabWA Webhook Event`
			SET status = 'Ready', error_code = NULL, modified = NOW(), modified_by = %s
			WHERE name = %s AND status = 'Failed' AND attempt_count < %s
			""",
			(frappe.session.user, event.name, MAX_WEBHOOK_ATTEMPTS),
		)
		if frappe.db.sql("SELECT ROW_COUNT()")[0][0] == 1:
			frappe.db.commit()
			_enqueue_webhook(event.name)

	ready = frappe.get_all(
		"WA Webhook Event",
		filters={"status": "Ready", "modified": ["<", ready_before]},
		fields=["name"],
		order_by="modified asc",
		limit=RECOVERY_BATCH,
	)
	for event in ready:
		frappe.db.sql(
			"""
			UPDATE `tabWA Webhook Event`
			SET modified = NOW(), modified_by = %s
			WHERE name = %s AND status = 'Ready' AND modified < %s
			""",
			(frappe.session.user, event.name, ready_before),
		)
		if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
			continue
		frappe.db.commit()
		_enqueue_webhook(event.name)


def _enqueue_webhook(event_name: str) -> None:
	frappe.enqueue(
		"tag_marketing.application.webhook_processing.process_webhook_event",
		queue="marketing",
		timeout=120,
		enqueue_after_commit=True,
		job_id=f"wa-webhook:{event_name}",
		deduplicate=True,
		event_name=event_name,
	)


def _recover_connection_operations() -> None:
	now = frappe.utils.now_datetime()
	stale_before = now - OPERATION_STALE_AFTER
	stale = frappe.get_all(
		"WA Operation",
		filters={
			"status": "Running",
			"target_doctype": "WA Connection",
			"operation_type": ["in", list(CONNECTION_OPERATIONS)],
			"heartbeat_at": ["<", stale_before],
		},
		fields=["name", "attempt_count"],
		limit=RECOVERY_BATCH,
	)
	for operation in stale:
		attempt = int(operation.attempt_count or 0)
		if attempt < MAX_OPERATION_ATTEMPTS:
			frappe.db.sql(
				"""
				UPDATE `tabWA Operation`
				SET status = 'Pending', progress_percent = 0, error_code = NULL,
					heartbeat_at = NOW(), modified = NOW(), modified_by = %s
				WHERE name = %s AND status = 'Running' AND heartbeat_at < %s
				""",
				(frappe.session.user, operation.name, stale_before),
			)
		else:
			frappe.db.sql(
				"""
				UPDATE `tabWA Operation`
				SET status = 'Failed', error_code = 'OPERATION_INTERRUPTED',
					heartbeat_at = NOW(), modified = NOW(), modified_by = %s
				WHERE name = %s AND status = 'Running' AND heartbeat_at < %s
				""",
				(frappe.session.user, operation.name, stale_before),
			)
		frappe.db.commit()

	ready_before = now - READY_REQUEUE_AFTER
	pending = frappe.get_all(
		"WA Operation",
		filters={
			"status": "Pending",
			"target_doctype": "WA Connection",
			"operation_type": ["in", list(CONNECTION_OPERATIONS)],
			"modified": ["<", ready_before],
		},
		fields=["name", "operation_type", "target_name", "request_json"],
		order_by="modified asc",
		limit=RECOVERY_BATCH,
	)
	for operation in pending:
		request = operation.request_json
		if isinstance(request, str):
			try:
				request = json.loads(request)
			except (TypeError, ValueError):
				request = None
		if not isinstance(request, dict) or not operation.target_name:
			frappe.db.set_value(
				"WA Operation", operation.name, {"status": "Failed", "error_code": "RECOVERY_UNAVAILABLE"}
			)
			frappe.db.commit()
			continue
		if _claim_pending_operation(operation.name, ready_before):
			_enqueue_operation(operation, request)


def _claim_pending_operation(name: str, older_than: Any) -> bool:
	frappe.db.sql(
		"""
		UPDATE `tabWA Operation`
		SET heartbeat_at = NOW(), modified = NOW(), modified_by = %s
		WHERE name = %s AND status = 'Pending' AND modified < %s
		""",
		(frappe.session.user, name, older_than),
	)
	claimed = frappe.db.sql("SELECT ROW_COUNT()")[0][0] == 1
	if claimed:
		frappe.db.commit()
	return claimed


def _enqueue_operation(operation: Any, request: dict[str, Any]) -> None:
	job_operation = CONNECTION_OPERATIONS[operation.operation_type]
	frappe.enqueue(
		"tag_marketing.application.connection_jobs.run_connection_operation",
		queue="marketing",
		enqueue_after_commit=True,
		job_id=f"wa:{operation.name}",
		deduplicate=True,
		operation_id=operation.name,
		operation=job_operation,
		connection_name=operation.target_name,
		kwargs=request,
	)
