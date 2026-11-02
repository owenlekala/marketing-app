"""Pure identity hashing rules for minimized marketing suppression."""

import hashlib
import hmac


def identity_digest(key: str, company: str, phone_e164: str) -> str:
	"""Return a keyed, non-reversible digest for company-scoped phone suppression."""
	if not key or not company or not phone_e164:
		raise ValueError("suppression_identity_required")
	return hmac.new(key.encode(), f"{company}|{phone_e164}".encode(), hashlib.sha256).hexdigest()
