"""Stable application error codes and optimistic revision checks, independent of Frappe."""

ERROR_CODES = frozenset(
	{
		"INVALID_INPUT",
		"INVALID_FILTER",
		"NOT_FOUND",
		"SOURCE_ACCESS_DENIED",
		"COMPANY_MISMATCH",
		"STALE_DOCUMENT",
		"IDEMPOTENCY_CONFLICT",
		"INVALID_STATE",
		"READINESS_FAILED",
		"LOCAL_RATE_LIMIT",
		"PROVIDER_UNAVAILABLE",
		"PERSISTENCE_UNAVAILABLE",
	}
)


class CommandError(Exception):
	def __init__(self, code: str, field: str | None = None) -> None:
		if code not in ERROR_CODES:
			raise ValueError("Unregistered application error code")
		self.code = code
		self.field = field
		super().__init__(code)


def require_revision(current: str, expected: str | None) -> None:
	if not isinstance(expected, str) or not expected or len(expected) > 64:
		raise CommandError("INVALID_INPUT", "expected_modified")
	if expected != current:
		raise CommandError("STALE_DOCUMENT", "expected_modified")
