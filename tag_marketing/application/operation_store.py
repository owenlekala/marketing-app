"""Shared durable-operation insertion and idempotency race handling."""

from typing import Any
from uuid import uuid4

import frappe

from tag_marketing.domain.errors import CommandError


def insert_idempotent_operation(doc: Any) -> tuple[str, bool]:
	"""Enforce WA Operation's actor/type/request uniqueness under concurrent requests."""
	savepoint = "wa_op_" + uuid4().hex
	frappe.db.savepoint(savepoint)
	try:
		doc.db_insert()
		return doc.name, True
	except (frappe.UniqueValidationError, frappe.DuplicateEntryError):
		frappe.db.rollback(save_point=savepoint)
		prior = frappe.db.get_value(
			"WA Operation",
			{
				"requested_by": doc.requested_by,
				"operation_type": doc.operation_type,
				"request_id": doc.request_id,
			},
			["name", "request_hash"],
			as_dict=True,
		)
		if not prior:
			raise
		if prior.request_hash != doc.request_hash:
			raise CommandError("IDEMPOTENCY_CONFLICT") from None
		return prior.name, False
