"""The sole unauthenticated boundary: Meta's signed webhook callback."""

import re

import frappe
from werkzeug.wrappers import Response

from tag_marketing.application.webhook_intake import accept_webhook, verify_challenge
from tag_marketing.infrastructure.meta_webhooks import (
	MAX_WEBHOOK_BODY_BYTES,
	InvalidWebhook,
	UnauthenticatedWebhook,
)

INTEGRATION_ID_RE = re.compile(r"[A-Za-z0-9_-]{20,128}\Z")


def _reply(body: str, status: int) -> Response:
	return Response(
		body,
		status=status,
		content_type="text/plain; charset=utf-8",
		headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
	)


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def receive():
	"""Verify Meta's GET challenge or accept a bounded raw-body signed POST."""
	request = frappe.request
	# Frappe's JSON form parser uses the JSON object alone and omits query
	# arguments, so routing must always come directly from the request URL.
	integrations = request.args.getlist("integration")
	integration = integrations[0] if len(integrations) == 1 else None
	if not integration or not INTEGRATION_ID_RE.fullmatch(integration):
		return _reply("UNAUTHORIZED", 403)
	if request.method == "GET":
		try:
			challenge = verify_challenge(
				integration,
				request.args.get("hub.mode"),
				request.args.get("hub.verify_token"),
				request.args.get("hub.challenge"),
			)
		except UnauthenticatedWebhook:
			return _reply("FORBIDDEN", 403)
		return _reply(challenge, 200)
	if request.method != "POST":
		return _reply("METHOD_NOT_ALLOWED", 405)
	if request.mimetype != "application/json":
		return _reply("UNSUPPORTED_MEDIA_TYPE", 415)
	length = request.content_length
	if length is None:
		return _reply("LENGTH_REQUIRED", 411)
	if length > MAX_WEBHOOK_BODY_BYTES:
		return _reply("PAYLOAD_TOO_LARGE", 413)
	if length == 0:
		return _reply("INVALID_BODY", 400)
	try:
		# Frappe parses JSON during request initialization. Reuse its cached exact
		# bytes so HMAC validation sees the provider's original body.
		raw_body = request.get_data(cache=True, as_text=False)
	except Exception:
		return _reply("INVALID_BODY", 400)
	if len(raw_body) != length:
		return _reply("INVALID_BODY", 400)
	try:
		accept_webhook(integration, raw_body, request.headers.get("X-Hub-Signature-256"))
	except UnauthenticatedWebhook:
		frappe.db.rollback()
		return _reply("UNAUTHORIZED", 401)
	except InvalidWebhook:
		frappe.db.rollback()
		return _reply("INVALID_PAYLOAD", 400)
	except Exception as exc:
		frappe.db.rollback()
		frappe.logger("tag_marketing").error("Webhook receipt failed (%s)", type(exc).__name__)
		return _reply("PERSISTENCE_UNAVAILABLE", 503)
	return _reply("EVENT_RECEIVED", 200)
