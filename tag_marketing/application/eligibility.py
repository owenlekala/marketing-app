"""Contact-row coordination shared by consent changes and outbound reservations."""

from typing import Any

import frappe

from tag_marketing.domain.eligibility import is_marketing_eligible
from tag_marketing.domain.errors import CommandError


def lock_contact_for_change(company: str, contact_name: str) -> dict[str, Any]:
	"""Lock and read current contact state inside the caller's transaction.

	Consent/suppression mutations and P4 reservations must use this same row lock.
	Never hold it across provider HTTP.
	"""
	rows = frappe.db.sql(
		"""
		SELECT company, consent_status, suppressed, archived
		FROM `tabWA Contact` WHERE name = %s FOR UPDATE
		""",
		contact_name,
		as_dict=True,
	)
	if not rows or rows[0]["company"] != company:
		raise CommandError("NOT_FOUND")
	return rows[0]


def lock_contact_for_submission(company: str, contact_name: str) -> bool:
	"""Return live eligibility while holding the shared reservation coordination lock.

	P4 must call this before checking caps and inserting reservations, in the same
	transaction. A caller that receives False must not create new send work.
	"""
	state = lock_contact_for_change(company, contact_name)
	return is_marketing_eligible(
		state["consent_status"],
		bool(state["suppressed"]),
		bool(state["archived"]),
	)
