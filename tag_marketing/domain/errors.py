"""Stable application error codes and optimistic revision checks, independent of Frappe."""

HTTP_STATUS = {
	"INVALID_INPUT": 400, "INVALID_FILTER": 400, "NOT_FOUND": 404,
	"SOURCE_ACCESS_DENIED": 403, "COMPANY_MISMATCH": 403,
	"STALE_DOCUMENT": 409, "IDEMPOTENCY_CONFLICT": 409, "INVALID_STATE": 409,
	"READINESS_FAILED": 422, "LOCAL_RATE_LIMIT": 429,
	"PROVIDER_UNAVAILABLE": 502, "PERSISTENCE_UNAVAILABLE": 503,
}


class CommandError(Exception):
	def __init__(self, code: str, field: str | None = None) -> None:
		if code not in HTTP_STATUS:
			raise ValueError("Unregistered application error code")
		self.code = code
		self.field = field
		super().__init__(code)


def require_revision(current: str, expected: str | None) -> None:
	if not isinstance(expected, str) or not expected or len(expected) > 64:
		raise CommandError("INVALID_INPUT", "expected_modified")
	if expected != current:
		raise CommandError("STALE_DOCUMENT", "expected_modified")
