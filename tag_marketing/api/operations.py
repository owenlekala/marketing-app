"""Authenticated operation progress. No create, retry, cancel or dispatch endpoint."""

import frappe

from tag_marketing.api.responses import boundary
from tag_marketing.application.operations import get_progress


@frappe.whitelist(methods=["GET"])
@boundary()
def get(operation: str):
	return get_progress(operation)
