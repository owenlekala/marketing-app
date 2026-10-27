"""Safe wire envelopes. Never serialize exception text, request arguments or tracebacks."""

import uuid
from functools import wraps

import frappe
from frappe import _

from tag_marketing.domain.errors import HTTP_STATUS, CommandError


def error_payload(code, correlation_id, field=None):
	messages = {
		"INVALID_INPUT": _("Check the supplied values and try again."),
		"INVALID_FILTER": _("Choose supported filters."),
		"NOT_FOUND": _("This record is unavailable or outside your permitted scope."),
		"SOURCE_ACCESS_DENIED": _("You no longer have access to the source record."),
		"COMPANY_MISMATCH": _("This record is outside your permitted company."),
		"STALE_DOCUMENT": _("This record changed. Reload and review it before trying again."),
		"IDEMPOTENCY_CONFLICT": _("This request identifier was already used with different values."),
		"INVALID_STATE": _("This action is unavailable in the current state."),
		"READINESS_FAILED": _("Required setup or policy checks have not passed."),
		"LOCAL_RATE_LIMIT": _("The local rate limit has been reached."),
		"PROVIDER_UNAVAILABLE": _("The provider is unavailable. Check operation status before trying again."),
		"PERSISTENCE_UNAVAILABLE": _("Operation progress is temporarily unavailable."),
		"INTERNAL_ERROR": _("Unable to complete this request. Give the reference to your administrator."),
	}
	return {"ok": False, "error": {"code": code, "message": messages.get(code, messages["INTERNAL_ERROR"]),
		"field": field, "retryable": code == "PERSISTENCE_UNAVAILABLE", "correlation_id": correlation_id}}


def boundary(*, mutates=False):
	"""A failed command rolls back its slice; the request/worker owns commit and idempotency."""
	def decorate(function):
		@wraps(function)
		def wrapped(*args, **kwargs):
			point = "wa_" + uuid.uuid4().hex
			if mutates:
				frappe.db.savepoint(point)
			try:
				return {"ok": True, "data": function(*args, **kwargs)}
			except Exception as exc:
				if mutates:
					frappe.db.rollback(save_point=point)
				if isinstance(exc, (frappe.PermissionError, frappe.AuthenticationError, frappe.ValidationError)):
					raise
				frappe.local.message_log = []
				correlation = uuid.uuid4().hex
				if isinstance(exc, CommandError):
					frappe.local.response["http_status_code"] = HTTP_STATUS[exc.code]
					return error_payload(exc.code, correlation, exc.field)
				frappe.local.response["http_status_code"] = 500
				# Exception classes are developer-defined. No str(exc), exc_info or request locals.
				frappe.logger("tag_marketing").error("Command failure [%s] %s", correlation, type(exc).__name__)
				return error_payload("INTERNAL_ERROR", correlation)
		return wrapped
	return decorate
