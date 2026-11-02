"""Authenticated outbound message reconciliation commands."""

import frappe

from tag_marketing.api.responses import boundary
from tag_marketing.application.outbox import reconcile_unknown as reconcile_unknown_message


@frappe.whitelist(methods=["POST"])
@boundary(mutates=True)
def reconcile_unknown(
	message: str,
	resolution: str,
	evidence_reference: str,
	expected_modified: str,
	request_id: str,
	provider_message_id: str | None = None,
):
	return reconcile_unknown_message(
		message,
		resolution,
		evidence_reference=evidence_reference,
		expected_modified=expected_modified,
		request_id=request_id,
		provider_message_id=provider_message_id,
	)
