from copy import deepcopy
from typing import Any

from tag_marketing.tests.support.cases import OfflineTestCase
from tag_marketing.tests.support.reports import PROBES, verify_egress_report


def valid_report() -> dict[str, Any]:
	return {
		"stats": {"expected": 0, "unexpected": 3, "flaky": 0, "skipped": 0},
		"errors": [],
		"suites": [
			{
				"specs": [
					{
						"title": title,
						"tests": [
							{
								"expectedStatus": "passed",
								"results": [
									{
										"status": "failed",
										"errors": [{"message": "WA_EGRESS_GUARD: provider.invalid"}],
									}
								],
							}
						],
					}
					for title in sorted(PROBES)
				]
			}
		],
	}


class TestEgressReport(OfflineTestCase):
	def test_all_three_intended_failures_are_required(self) -> None:
		verify_egress_report(valid_report())

	def test_false_positive_reports_are_rejected(self) -> None:
		for failure in ("missing", "duplicate", "unrelated", "extra_error", "retry", "skipped", "expected"):
			with self.subTest(failure=failure):
				report = deepcopy(valid_report())
				specs = report["suites"][0]["specs"]
				test = specs[0]["tests"][0]
				if failure == "missing":
					specs.pop()
				elif failure == "duplicate":
					specs[1]["title"] = specs[0]["title"]
				elif failure == "unrelated":
					test["results"][0]["errors"][0]["message"] = "Startup timeout"
				elif failure == "extra_error":
					test["results"][0]["errors"].append({"message": "Unrelated error"})
				elif failure == "retry":
					test["results"].append(deepcopy(test["results"][0]))
				elif failure == "skipped":
					report["stats"]["skipped"] = 1
				else:
					test["expectedStatus"] = "failed"
				with self.assertRaises(ValueError):
					verify_egress_report(report)
