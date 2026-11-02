"""Suppression identity persistence and lookup use cases."""

import frappe

from tag_marketing.domain.errors import CommandError
from tag_marketing.domain.suppression import identity_digest


def is_identity_suppressed(company: str, phone_e164: str, *, lock: bool = False) -> bool:
	"""Check retained active suppression by normalized identity without exposing it."""
	settings = frappe.get_doc("WA Settings")
	key = settings.get_password("suppression_hmac_key") if settings.suppression_hmac_key else ""
	if not key:
		raise CommandError("PERSISTENCE_UNAVAILABLE")
	digest = identity_digest(key, company, phone_e164)
	query = """
		SELECT name FROM `tabWA Suppression`
		WHERE company = %s AND purpose = 'Marketing' AND active = 1 AND identity_digest = %s
		LIMIT 1
	"""
	if lock:
		query += " FOR UPDATE"
	return bool(frappe.db.sql(query, (company, digest)))


def digest_for_identity(company: str, phone_e164: str) -> str:
	"""Build the minimized suppression key using the site-owned secret."""
	settings = frappe.get_doc("WA Settings")
	key = settings.get_password("suppression_hmac_key") if settings.suppression_hmac_key else ""
	if not key:
		raise CommandError("PERSISTENCE_UNAVAILABLE")
	try:
		return identity_digest(key, company, phone_e164)
	except ValueError:
		raise CommandError("INVALID_INPUT") from None
