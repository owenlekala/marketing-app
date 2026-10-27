from copy import deepcopy
from typing import Any

from tag_marketing.domain.settings import validate_settings
from tag_marketing.tests.support.cases import OfflineTestCase


def settings() -> dict[str, Any]:
	return {
		"timezone": "Africa/Johannesburg",
		"marketing_start": "09:00:00",
		"marketing_end": "17:00:00",
		"marketing_cap": 1,
		"cap_window_hours": 24,
		"max_campaign_recipients": 10000,
		"sending_scope": "Pilot",
		"company_rate_per_second": 0,
	}


class TestSettingsPolicy(OfflineTestCase):
	def test_incomplete_disabled_policy_has_no_invented_retention_or_rate(self) -> None:
		validate_settings(settings())

	def test_invalid_policy_inputs_are_rejected(self) -> None:
		cases = [
			("timezone", "Missing/Zone"),
			("marketing_end", "08:00:00"),
			("marketing_start", "invalid"),
			("marketing_cap", 0),
			("cap_window_hours", 1.5),
			("company_rate_per_second", float("nan")),
			("message_retention_days", -1),
			("message_retention_days", 1.5),
			("max_campaign_recipients", 10001),
			("sending_scope", "Anything"),
			("privacy_notice_url", "http://example.invalid"),
			("privacy_notice_url", "https://user:secret@example.invalid"),
		]
		for field, value in cases:
			with self.subTest(field=field, value=value):
				values = deepcopy(settings())
				values[field] = value
				with self.assertRaises(ValueError):
					validate_settings(values)
