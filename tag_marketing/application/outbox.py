"""Durable outbound message creation, leases, submission, and recovery."""

from __future__ import annotations

import hashlib
import json
import secrets
import traceback
import uuid
from datetime import UTC, datetime, timedelta
from math import ceil, floor
from typing import Any, NoReturn

import frappe

from tag_marketing.application.connection_jobs import provider_factory
from tag_marketing.application.eligibility import lock_contact_for_submission
from tag_marketing.domain.errors import CommandError, require_revision
from tag_marketing.domain.outbox import retry_decision, uncertain_submission
from tag_marketing.infrastructure.meta_cloud import FailureKind, ProviderFailure

LEASE_SECONDS = 120
RECOVERY_LIMIT = 100


def _system_now() -> datetime:
	"""Use Frappe's system-timezone convention for persisted DATETIME fields."""
	return frappe.utils.now_datetime()


def _validation_error(message: str) -> NoReturn:
	frappe.throw(message, frappe.ValidationError)
	raise frappe.ValidationError(message)


def enqueue_message(
	*,
	company: str,
	contact: str,
	phone_e164: str,
	sending_number: str,
	purpose: str,
	template: str,
	template_payload: dict[str, Any],
	logical_key: str,
	initiated_by: str,
	conversation: str | None = None,
	campaign_recipient: str | None = None,
	automation_run: str | None = None,
	due_at: datetime | None = None,
) -> dict[str, str]:
	"""Create one immutable logical message and its outbox row before enqueue."""
	if purpose not in {"Marketing", "Utility", "Support", "Test"}:
		raise CommandError("INVALID_INPUT", "purpose")
	if not isinstance(logical_key, str) or not 8 <= len(logical_key) <= 180:
		raise CommandError("INVALID_INPUT", "request_id")
	if not isinstance(template_payload, dict) or len(json.dumps(template_payload)) > 32_000:
		raise CommandError("INVALID_INPUT", "template")
	if not frappe.db.exists("WA Sending Number", {"name": sending_number, "company": company}):
		raise CommandError("NOT_FOUND")
	if not frappe.db.exists("WA Contact", {"name": contact, "company": company}):
		raise CommandError("NOT_FOUND")
	savepoint = "wa_outbox_" + uuid.uuid4().hex
	frappe.db.savepoint(savepoint)
	try:
		message = frappe.get_doc(
			{
				"doctype": "WA Message",
				"company": company,
				"conversation": conversation,
				"contact": contact,
				"sending_number": sending_number,
				"recipient_phone": phone_e164,
				"direction": "Outbound",
				"purpose": purpose,
				"template": template,
				"template_payload_json": template_payload,
				"logical_key": logical_key,
				"status": "Queued",
				"campaign_recipient": campaign_recipient,
				"automation_run": automation_run,
				"initiated_by": initiated_by,
			}
		)
		message.db_insert()
		outbox = frappe.get_doc(
			{
				"doctype": "WA Outbox Item",
				"company": company,
				"message": message.name,
				"logical_key": logical_key,
				"status": "Pending",
				"due_at": due_at or _system_now(),
				"attempt_count": 0,
			}
		)
		outbox.db_insert()
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		frappe.db.rollback(save_point=savepoint)
		prior = frappe.db.get_value(
			"WA Message",
			{"logical_key": logical_key},
			[
				"name",
				"company",
				"contact",
				"sending_number",
				"recipient_phone",
				"template",
				"template_payload_json",
			],
			as_dict=True,
		)
		if not prior:
			raise
		stored = _parse_payload(prior.template_payload_json)
		if (
			prior.company,
			prior.contact,
			prior.sending_number,
			prior.recipient_phone,
			prior.template,
			stored,
		) != (company, contact, sending_number, phone_e164, template, template_payload):
			raise CommandError("IDEMPOTENCY_CONFLICT") from None
		return {"message": prior.name}
	frappe.enqueue(
		"tag_marketing.application.outbox.process_outbox_item",
		queue="marketing",
		enqueue_after_commit=True,
		job_id=f"wa-outbox:{outbox.name}",
		deduplicate=True,
		outbox_name=outbox.name,
	)
	return {"message": message.name, "outbox": outbox.name}


def process_outbox_item(outbox_name: str) -> None:
	"""Claim one item, reserve eligibility, submit without a DB lock, then reconcile."""
	lease = secrets.token_urlsafe(24)
	frappe.db.sql(
		"""
		UPDATE `tabWA Outbox Item`
		SET status = 'Claimed', lease_owner = %s,
			lease_until = DATE_ADD(UTC_TIMESTAMP(), INTERVAL %s SECOND),
			modified = NOW(), modified_by = %s
		WHERE name = %s AND status IN ('Pending','Retry')
			AND COALESCE(next_retry_at, due_at) <= %s
	""",
		(lease, LEASE_SECONDS, frappe.session.user, outbox_name, _system_now()),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		return
	frappe.db.commit()
	rate_lock: str | None = None
	phase = "load_submission_context"
	try:
		outbox = frappe.get_doc("WA Outbox Item", outbox_name)
		message = frappe.get_doc("WA Message", outbox.message)
		context = _submission_context(message)
		reservation = _reserve(context, message)
		phase = "persist_attempt"
		rate_lock = context.get("rate_lock")
		if reservation == "deferred":
			return
		if reservation == "ineligible":
			_finish_pre_submit(outbox, message, lease, "Suppressed", "CONSENT_REQUIRED")
			return
		attempt_no = int(outbox.attempt_count or 0) + 1
		attempt = frappe.get_doc(
			{
				"doctype": "WA Message Attempt",
				"company": message.company,
				"message": message.name,
				"attempt_no": attempt_no,
				"started_at": _system_now(),
				"result": "Started",
			}
		)
		attempt.db_insert()
		frappe.db.sql(
			"""
			UPDATE `tabWA Outbox Item`
			SET status='Submitting', submission_started_at=UTC_TIMESTAMP(),
				attempt_count=%s, modified=NOW(), modified_by=%s
			WHERE name=%s AND status='Claimed' AND lease_owner=%s
		""",
			(attempt_no, frappe.session.user, outbox.name, lease),
		)
		if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
			frappe.db.rollback()
			_release_rate_lock(rate_lock)
			rate_lock = None
			return
		frappe.db.set_value("WA Message", message.name, "status", "Submitting", update_modified=False)
		frappe.db.commit()
		_release_rate_lock(rate_lock)
		rate_lock = None
		phase = "provider_factory"
		connection = frappe.get_doc("WA Connection", context["connection"])
		api = provider_factory(connection)
		phase = "provider_submit"
		try:
			result = api.submit_message(context["provider_phone_id"], context["payload"])
		except ProviderFailure as error:
			_handle_provider_failure(outbox.name, message.name, attempt.name, lease, error)
			return
		phase = "complete_accepted"
		_complete_accepted(outbox.name, message.name, attempt.name, lease, result.provider_message_id)
	except Exception as error:
		frappe.db.rollback()
		_release_rate_lock(rate_lock)
		frames = traceback.extract_tb(error.__traceback__)
		location = frames[-1] if frames else None
		frappe.logger("tag_marketing").error(
			"Outbox item %s failed during %s (%s at %s:%s)",
			outbox_name,
			phase,
			type(error).__name__,
			location.name if location else "unknown",
			location.lineno if location else 0,
		)
		# If the submission marker committed, uncertainty must be preserved.
		row = frappe.db.get_value(
			"WA Outbox Item", outbox_name, ["status", "submission_started_at"], as_dict=True
		)
		if row and uncertain_submission(row.status, row.submission_started_at):
			_mark_unknown(outbox_name, "PROVIDER_UNAVAILABLE", lease=lease)
		else:
			_fail_before_submit(outbox_name, "INTERNAL_ERROR", lease)


def _submission_context(message: Any) -> dict[str, Any]:
	contact = (
		frappe.db.get_value(
			"WA Campaign Recipient", message.campaign_recipient, ["contact", "phone_e164"], as_dict=True
		)
		if message.campaign_recipient
		else None
	)
	if not contact and message.contact:
		contact = frappe._dict(contact=message.contact, phone_e164=message.recipient_phone)
	if not contact and message.conversation:
		contact = frappe.db.get_value("WA Conversation", message.conversation, ["contact"], as_dict=True)
		if contact:
			contact.phone_e164 = frappe.db.get_value("WA Contact", contact.contact, "phone_e164")
	if not contact:
		_validation_error("Outbound message has no authorised recipient.")
	template = frappe.get_doc("WA Template", message.template)
	number_name = None
	if message.campaign_recipient:
		recipient = frappe.db.get_value(
			"WA Campaign Recipient",
			message.campaign_recipient,
			["campaign", "snapshot", "contact"],
			as_dict=True,
		)
		if not recipient or recipient.contact != contact.contact:
			_validation_error("Campaign recipient scope is invalid.")
		campaign = frappe.get_doc("WA Campaign", recipient.campaign)
		snapshot = frappe.get_doc("WA Campaign Snapshot", recipient.snapshot)
		if (
			campaign.company != message.company
			or campaign.status != "Running"
			or snapshot.status != "Ready"
			or campaign.current_snapshot != snapshot.name
			or campaign.approval_hash != snapshot.snapshot_hash
			or (
				campaign.expires_at
				and frappe.utils.get_datetime(campaign.expires_at) <= _system_now()
			)
		):
			_validation_error("Campaign approval or dispatch state is no longer valid.")
		number_name = campaign.sending_number
	elif message.conversation:
		number_name = frappe.db.get_value("WA Conversation", message.conversation, "sending_number")
	if not number_name:
		number_name = message.sending_number
	if not number_name:
		_validation_error("Outbound message has no authorised sending number.")
	number = frappe.db.get_value(
		"WA Sending Number",
		{"name": number_name, "company": message.company},
		["connection", "provider_phone_id", "status", "rate_per_second"],
		as_dict=True,
	)
	if not number or number.status != "Ready":
		_validation_error("Sending number is unavailable.")
	connection_status = frappe.db.get_value("WA Connection", number.connection, "status")
	if connection_status != "Ready":
		_validation_error("Connection is unavailable.")
	if template.company != message.company or template.connection != number.connection:
		frappe.throw("Template scope is invalid.", frappe.ValidationError)
	if template.status != "Approved" or template.category not in {"Marketing", "Utility"}:
		_validation_error("Template is not sendable.")
	if template.media_file:
		_validation_error("Media template dispatch is unavailable until media upload is verified.")
	settings = frappe.get_single("WA Settings")
	if message.purpose != "Test" and not settings.sending_enabled:
		_validation_error("Sending is disabled.")
	if message.purpose != "Test" and settings.sending_scope == "Pilot":
		if not frappe.db.exists("WA Pilot Contact", {"parent": "WA Settings", "contact": contact.contact}):
			_validation_error("Recipient is outside the authorised pilot allowlist.")
	payload = {
		"messaging_product": "whatsapp",
		"recipient_type": "individual",
		"to": contact.phone_e164,
		"type": "template",
		"template": {
			"name": template.template_name,
			"language": {"code": template.language_code},
			"components": _parse_payload(message.template_payload_json).get("components", []),
		},
	}
	return {
		"contact": contact.contact if hasattr(contact, "contact") else contact.name,
		"phone_e164": contact.phone_e164,
		"connection": number.connection,
		"provider_phone_id": number.provider_phone_id,
		"sending_number": number_name,
		"number_rate": number.rate_per_second,
		"payload": payload,
		"template": template.name,
		"settings": settings,
	}


def _reserve(context: dict[str, Any], message: Any) -> str:
	settings = context["settings"]
	eligible = lock_contact_for_submission(message.company, context["contact"])
	if not eligible:
		return "ineligible"
	existing_reservation = frappe.db.exists(
		"WA Send Reservation", {"message": message.name, "state": ["in", ["Reserved", "Retained"]]}
	)
	window_start = _system_now() - timedelta(hours=int(settings.cap_window_hours or 24))
	active = frappe.db.count(
		"WA Send Reservation",
		{
			"company": message.company,
			"contact": context["contact"],
			"state": ["in", ["Reserved", "Retained"]],
			"reserved_at": [">=", window_start],
		},
	)
	if active - int(bool(existing_reservation)) >= int(settings.marketing_cap or 1):
		frappe.db.set_value(
			"WA Outbox Item",
			{"message": message.name},
			{
				"status": "Pending",
			"due_at": _system_now() + timedelta(minutes=15),
				"lease_owner": None,
				"lease_until": None,
			},
			update_modified=False,
		)
		frappe.db.commit()
		return "deferred"
	lock_name = "wa_rate_" + hashlib.sha256(message.company.encode()).hexdigest()[:48]
	got_lock = frappe.db.sql("SELECT GET_LOCK(%s, 0)", lock_name)[0][0]
	if got_lock != 1:
		_defer_outbox(message.name, 1)
		return "deferred"
	context["rate_lock"] = lock_name
	settings_rate = float(settings.company_rate_per_second or 0)
	number_rate = float(context["number_rate"] or 0)
	if settings_rate <= 0 or number_rate <= 0:
		_release_rate_lock(lock_name)
		context.pop("rate_lock", None)
		frappe.throw("Company and number send rates must be configured.", frappe.ValidationError)
	company_period = max(1, ceil(1 / settings_rate))
	company_limit = max(1, floor(settings_rate * company_period))
	number_period = max(1, ceil(1 / number_rate))
	number_limit = max(1, floor(number_rate * number_period))
	recent_company = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabWA Message Attempt` a
		JOIN `tabWA Message` m ON m.name=a.message
		WHERE m.company=%s AND a.started_at >= %s""",
		(message.company, _system_now() - timedelta(seconds=company_period)),
	)[0][0]
	recent_number = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabWA Message Attempt` a
		JOIN `tabWA Message` m ON m.name=a.message
		WHERE m.company=%s AND m.sending_number=%s
		AND a.started_at >= %s""",
		(message.company, context["sending_number"], _system_now() - timedelta(seconds=number_period)),
	)[0][0]
	if recent_company >= company_limit or recent_number >= number_limit:
		_release_rate_lock(lock_name)
		context.pop("rate_lock", None)
		_defer_outbox(message.name, 1)
		return "deferred"
	if not existing_reservation:
		frappe.get_doc(
			{
				"doctype": "WA Send Reservation",
				"company": message.company,
				"contact": context["contact"],
				"message": message.name,
			"reserved_at": _system_now(),
				"state": "Reserved",
				"purpose": "Test" if message.purpose == "Test" else "Marketing",
			}
		).db_insert()
	return "reserved"


def _defer_outbox(message: str, seconds: int) -> None:
	frappe.db.set_value(
		"WA Outbox Item",
		{"message": message},
		{
			"status": "Pending",
			"due_at": _system_now() + timedelta(seconds=seconds),
			"lease_owner": None,
			"lease_until": None,
		},
		update_modified=False,
	)
	frappe.db.commit()


def _parse_payload(value: Any) -> dict[str, Any]:
	if isinstance(value, str):
		value = json.loads(value)
	return value if isinstance(value, dict) else {}


def _release_rate_lock(lock_name: str | None) -> None:
	if lock_name:
		frappe.db.sql("SELECT RELEASE_LOCK(%s)", lock_name)


def _finish_pre_submit(outbox: Any, message: Any, lease: str, status: str, error: str) -> None:
	frappe.db.set_value(
		"WA Message", message.name, {"status": status, "error_code": error}, update_modified=False
	)
	frappe.db.sql(
		"UPDATE `tabWA Outbox Item` SET status='Failed', last_error_code=%s, lease_owner=NULL, lease_until=NULL, modified=NOW() WHERE name=%s AND lease_owner=%s AND status='Claimed'",
		(error, outbox.name, lease),
	)
	frappe.db.commit()


def _handle_provider_failure(
	outbox: str, message: str, attempt: str, lease: str, error: ProviderFailure
) -> None:
	if error.kind == FailureKind.UNKNOWN_OUTCOME:
		_mark_unknown(outbox, error.kind.value, lease=lease)
		return
	if error.kind == FailureKind.RATE_LIMITED:
		_mark_attempt(attempt, "Rejected", error.kind.value)
		_retry_or_fail_before_submit(outbox, error.kind.value, lease)
		return
	frappe.db.sql(
		"UPDATE `tabWA Outbox Item` SET status='Failed', last_error_code=%s, lease_owner=NULL, lease_until=NULL, modified=NOW() WHERE name=%s AND lease_owner=%s AND status='Submitting'",
		(error.kind.value, outbox, lease),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		frappe.db.rollback()
		return
	_mark_attempt(attempt, "Rejected", error.kind.value)
	_release_reservation(message)
	frappe.db.set_value(
		"WA Message", message, {"status": "Failed", "error_code": error.kind.value}, update_modified=False
	)
	frappe.db.commit()


def _retry_or_fail_before_submit(outbox: str, code: str, lease: str) -> None:
	row = frappe.db.get_value("WA Outbox Item", outbox, ["attempt_count", "message"], as_dict=True)
	decision = retry_decision(
		int(row.attempt_count or 0),
		datetime.now(UTC).replace(tzinfo=None),
		explicitly_retryable=True,
		key=outbox,
	)
	if row.message and frappe.db.get_value("WA Message", row.message, "campaign_recipient"):
		recipient = frappe.get_doc(
			"WA Campaign Recipient", frappe.db.get_value("WA Message", row.message, "campaign_recipient")
		)
		campaign = frappe.get_doc("WA Campaign", recipient.campaign)
		if (
			campaign.expires_at
			and decision.due_at
			and decision.due_at >= frappe.utils.get_datetime(campaign.expires_at)
		):
			decision = type(decision)("Failed", None)
	if decision.status == "Retry":
		frappe.db.sql(
			"UPDATE `tabWA Outbox Item` SET status='Retry', next_retry_at=%s, due_at=%s, last_error_code=%s, lease_owner=NULL, lease_until=NULL, submission_started_at=NULL, modified=NOW() WHERE name=%s AND lease_owner=%s",
			(
				frappe.utils.convert_utc_to_system_timezone(decision.due_at).replace(tzinfo=None)
				if decision.due_at
				else None,
				frappe.utils.convert_utc_to_system_timezone(decision.due_at).replace(tzinfo=None)
				if decision.due_at
				else None,
				code,
				outbox,
				lease,
			),
		)
		if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
			frappe.db.rollback()
			return
		frappe.db.set_value("WA Message", row.message, "status", "Queued", update_modified=False)
	else:
		frappe.db.sql(
			"UPDATE `tabWA Outbox Item` SET status='Failed', last_error_code=%s, lease_owner=NULL, lease_until=NULL, modified=NOW() WHERE name=%s AND lease_owner=%s AND status='Submitting'",
			(code, outbox, lease),
		)
		if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
			frappe.db.rollback()
			return
		_release_reservation(row.message)
		frappe.db.set_value(
			"WA Message", row.message, {"status": "Failed", "error_code": code}, update_modified=False
		)
	frappe.db.commit()


def _fail_before_submit(outbox: str, code: str, lease: str) -> None:
	row = frappe.db.get_value("WA Outbox Item", outbox, ["message"], as_dict=True)
	if not row:
		return
	_release_reservation(row.message)
	frappe.db.set_value(
		"WA Message", row.message, {"status": "Failed", "error_code": code}, update_modified=False
	)
	frappe.db.sql(
		"UPDATE `tabWA Outbox Item` SET status='Failed', last_error_code=%s, lease_owner=NULL, lease_until=NULL, modified=NOW() WHERE name=%s AND lease_owner=%s AND status='Claimed'",
		(code, outbox, lease),
	)
	frappe.db.commit()


def _complete_accepted(outbox: str, message: str, attempt: str, lease: str, provider_id: str) -> None:
	now = _system_now()
	frappe.db.sql(
		"UPDATE `tabWA Message` SET provider_message_id=%s, status='Accepted', submitted_at=%s, modified=NOW() WHERE name=%s AND status='Submitting'",
		(provider_id, now, message),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		frappe.db.rollback()
		return
	frappe.db.sql(
		"UPDATE `tabWA Outbox Item` SET status='Done', lease_owner=NULL, lease_until=NULL, last_error_code=NULL, modified=NOW() WHERE name=%s AND status='Submitting' AND lease_owner=%s",
		(outbox, lease),
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		frappe.db.rollback()
		return
	frappe.db.set_value(
		"WA Message Attempt",
		attempt,
		{"finished_at": now, "result": "Accepted", "provider_message_id": provider_id},
		update_modified=False,
	)
	frappe.db.set_value(
		"WA Send Reservation", {"message": message}, "state", "Retained", update_modified=False
	)
	frappe.db.commit()


def _mark_unknown(outbox: str, code: str, *, lease: str | None = None) -> None:
	where = "name=%s AND status='Submitting'" + (" AND lease_owner=%s" if lease else "")
	params: tuple[Any, ...] = (code, outbox, lease) if lease else (code, outbox)
	frappe.db.sql(
		f"UPDATE `tabWA Outbox Item` SET status='Unknown', last_error_code=%s, lease_owner=NULL, lease_until=NULL, modified=NOW() WHERE {where}",
		params,
	)
	if frappe.db.sql("SELECT ROW_COUNT()")[0][0] != 1:
		frappe.db.rollback()
		return
	message = frappe.db.get_value("WA Outbox Item", outbox, "message")
	frappe.db.set_value(
		"WA Message", message, {"status": "Unknown", "error_code": code}, update_modified=False
	)
	frappe.db.set_value(
		"WA Send Reservation", {"message": message}, "state", "Retained", update_modified=False
	)
	attempt = frappe.db.get_value(
		"WA Message Attempt", {"message": message, "result": "Started"}, "name", order_by="attempt_no desc"
	)
	if attempt:
		frappe.db.set_value(
			"WA Message Attempt",
			attempt,
			{"finished_at": _system_now(), "result": "Unknown", "error_code": code},
			update_modified=False,
		)
	frappe.db.commit()


def _mark_attempt(name: str, result: str, code: str) -> None:
	frappe.db.set_value(
		"WA Message Attempt",
		name,
		{
			"finished_at": _system_now(),
			"result": result,
			"error_code": code,
		},
		update_modified=False,
	)


def _release_reservation(message: str) -> None:
	frappe.db.set_value(
		"WA Send Reservation", {"message": message}, "state", "Released", update_modified=False
	)


def recover_outbox() -> None:
	"""Re-enqueue due records, reclaim pre-submit leases, and make stale submissions Unknown."""
	stale = frappe.db.sql(
		"SELECT name FROM `tabWA Outbox Item` WHERE status='Claimed' AND lease_until < UTC_TIMESTAMP(6) ORDER BY lease_until, name LIMIT %s",
		(RECOVERY_LIMIT,),
		as_dict=True,
	)
	for row in stale:
		frappe.db.sql(
			"UPDATE `tabWA Outbox Item` SET status='Pending', lease_owner=NULL, lease_until=NULL WHERE name=%s AND status='Claimed' AND lease_until < UTC_TIMESTAMP()",
			row.name,
		)
	stale_submissions = frappe.db.sql(
		"SELECT name FROM `tabWA Outbox Item` WHERE status='Submitting' AND submission_started_at < DATE_SUB(UTC_TIMESTAMP(6), INTERVAL %s SECOND) ORDER BY submission_started_at, name LIMIT %s",
		(LEASE_SECONDS, RECOVERY_LIMIT),
		as_dict=True,
	)
	for row in stale_submissions:
		_mark_unknown(row.name, "OPERATION_INTERRUPTED")
	due = frappe.db.get_all(
		"WA Outbox Item",
		filters={"status": ["in", ["Pending", "Retry"]], "due_at": ["<=", _system_now()]},
		fields=["name"],
		order_by="due_at asc, name asc",
		limit=RECOVERY_LIMIT,
	)
	frappe.db.commit()
	for row in due:
		frappe.enqueue(
			"tag_marketing.application.outbox.process_outbox_item",
			queue="marketing",
			enqueue_after_commit=True,
			job_id=f"wa-outbox:{row.name}",
			deduplicate=True,
			outbox_name=row.name,
		)


def reconcile_unknown(
	message_name: str,
	resolution: str,
	*,
	evidence_reference: str,
	expected_modified: str,
	request_id: str,
	provider_message_id: str | None = None,
) -> dict[str, str]:
	"""Resolve an ambiguous submission from manager supplied evidence; never resend."""
	roles = set(frappe.get_roles())
	if not roles.intersection({"Marketing Manager", "System Manager"}):
		frappe.throw("Only a Marketing Manager can reconcile an unknown send.", frappe.PermissionError)
	if resolution not in {"Accepted With Evidence", "Not Submitted With Evidence", "Leave Unknown"}:
		raise CommandError("INVALID_INPUT", "resolution")
	if not isinstance(request_id, str) or not 8 <= len(request_id) <= 128:
		raise CommandError("INVALID_INPUT", "request_id")
	if not isinstance(evidence_reference, str) or not 1 <= len(evidence_reference.strip()) <= 512:
		raise CommandError("INVALID_INPUT", "evidence_reference")
	if resolution == "Accepted With Evidence":
		if not isinstance(provider_message_id, str) or not 1 <= len(provider_message_id) <= 128:
			raise CommandError("INVALID_INPUT", "provider_message_id")
	elif provider_message_id:
		raise CommandError("INVALID_INPUT", "provider_message_id")
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company:
		raise CommandError("NOT_FOUND")
	arguments = {
		"message": message_name,
		"resolution": resolution,
		"evidence_reference": evidence_reference.strip(),
		"provider_message_id": provider_message_id,
	}
	request_hash = hashlib.sha256(
		json.dumps(arguments, sort_keys=True, separators=(",", ":")).encode()
	).hexdigest()
	idempotency_key = hashlib.sha256(
		f"{frappe.session.user}:messages.reconcile_unknown:{request_id}".encode()
	).hexdigest()
	prior = frappe.db.get_value(
		"WA Audit Event",
		{"idempotency_key": idempotency_key},
		["request_hash", "details_json"],
		as_dict=True,
	)
	if prior:
		return _reconciliation_replay(prior, request_hash, message_name)
	locked = frappe.db.sql(
		"SELECT name, status, modified FROM `tabWA Message` WHERE name=%s AND company=%s FOR UPDATE",
		(message_name, company),
		as_dict=True,
	)
	if not locked:
		raise CommandError("NOT_FOUND")
	prior = frappe.db.get_value(
		"WA Audit Event",
		{"idempotency_key": idempotency_key},
		["request_hash", "details_json"],
		as_dict=True,
	)
	if prior:
		return _reconciliation_replay(prior, request_hash, message_name)
	require_revision(str(locked[0]["modified"]), expected_modified)
	if locked[0]["status"] != "Unknown":
		raise CommandError("INVALID_STATE")
	if not frappe.db.exists("WA Outbox Item", {"message": message_name, "status": "Unknown"}):
		raise CommandError("INVALID_STATE")
	result_status = (
		"Unknown"
		if resolution == "Leave Unknown"
		else "Accepted"
		if resolution == "Accepted With Evidence"
		else "Failed"
	)
	savepoint = "wa_reconcile_" + uuid.uuid4().hex
	frappe.db.savepoint(savepoint)
	try:
		if resolution == "Accepted With Evidence":
			frappe.db.set_value(
				"WA Message",
				message_name,
				{
					"status": "Accepted",
					"provider_message_id": provider_message_id,
					"error_code": None,
				},
			)
			frappe.db.set_value(
				"WA Outbox Item",
				{"message": message_name, "status": "Unknown"},
				{
					"status": "Done",
					"last_error_code": None,
				},
				update_modified=False,
			)
			frappe.db.set_value(
				"WA Message Attempt",
				{"message": message_name, "result": "Unknown"},
				{
					"result": "Accepted",
					"provider_message_id": provider_message_id,
				},
				update_modified=False,
			)
			frappe.db.set_value(
				"WA Send Reservation", {"message": message_name}, "state", "Retained", update_modified=False
			)
		elif resolution == "Not Submitted With Evidence":
			frappe.db.set_value(
				"WA Message",
				message_name,
				{
					"status": "Failed",
					"error_code": "NOT_SUBMITTED_EVIDENCE",
				},
			)
			frappe.db.set_value(
				"WA Outbox Item",
				{"message": message_name, "status": "Unknown"},
				{
					"status": "Failed",
					"last_error_code": "NOT_SUBMITTED_EVIDENCE",
				},
				update_modified=False,
			)
			frappe.db.set_value(
				"WA Send Reservation", {"message": message_name}, "state", "Released", update_modified=False
			)
		frappe.get_doc(
			{
				"doctype": "WA Audit Event",
				"company": company,
				"action": "Unknown Message Reconciled",
				"actor": frappe.session.user,
				"target_doctype": "WA Message",
				"target_name": message_name,
				"occurred_at": _system_now(),
				"idempotency_key": idempotency_key,
				"request_hash": request_hash,
				"details_json": json.dumps(
					{**arguments, "status": result_status}, sort_keys=True, separators=(",", ":")
				),
			}
		).db_insert()
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		frappe.db.rollback(save_point=savepoint)
		prior = frappe.db.get_value(
			"WA Audit Event",
			{"idempotency_key": idempotency_key},
			["request_hash", "details_json"],
			as_dict=True,
		)
		if not prior:
			raise
		return _reconciliation_replay(prior, request_hash, message_name)
	return {"message": message_name, "status": result_status}


def _reconciliation_replay(prior: Any, request_hash: str, message_name: str) -> dict[str, str]:
	if prior.request_hash != request_hash:
		raise CommandError("IDEMPOTENCY_CONFLICT")
	details = _parse_payload(prior.details_json)
	if details.get("message") != message_name or details.get("status") not in {
		"Accepted",
		"Failed",
		"Unknown",
	}:
		raise CommandError("IDEMPOTENCY_CONFLICT")
	return {"message": message_name, "status": details["status"]}
