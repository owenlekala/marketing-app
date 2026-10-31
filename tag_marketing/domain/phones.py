"""Pure phone identity rules shared by source selection and contact validation."""

import phonenumbers


def to_e164(value: str, region: str | None) -> str | None:
	if not value or not region or len(region) != 2:
		return None
	try:
		number = phonenumbers.parse(value, region.upper())
	except phonenumbers.NumberParseException:
		return None
	if not phonenumbers.is_valid_number(number):
		return None
	if phonenumbers.number_type(number) not in (
		phonenumbers.PhoneNumberType.MOBILE,
		phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
	):
		return None
	return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
