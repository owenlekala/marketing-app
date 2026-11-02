"""Pure outbound eligibility policy used while a contact coordination lock is held."""


def is_marketing_eligible(consent_status: str, suppressed: bool, archived: bool) -> bool:
	return consent_status == "Granted" and not suppressed and not archived
