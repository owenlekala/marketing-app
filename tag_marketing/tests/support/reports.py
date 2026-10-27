"""Fail-closed interpretation of the Playwright negative-probe JSON report."""

from typing import Any

EGRESS_MARKER = "WA_EGRESS_GUARD"
PROBES = {"egress:http", "egress:websocket", "egress:api"}


def verify_egress_report(report: dict[str, Any]) -> None:
	stats = report.get("stats", {})
	if report.get("errors") or any(
		stats.get(key) != value
		for key, value in {
			"expected": 0,
			"unexpected": 3,
			"flaky": 0,
			"skipped": 0,
		}.items()
	):
		raise ValueError("Negative browser report has missing, additional or unrelated failures")
	seen: set[str] = set()

	def inspect(suites: list[dict[str, Any]]) -> None:
		for suite in suites:
			inspect(suite.get("suites", []))
			for spec in suite.get("specs", []):
				title = spec.get("title", "")
				if title not in PROBES or title in seen or len(spec.get("tests", [])) != 1:
					raise ValueError("Unexpected or duplicate negative probe")
				seen.add(title)
				test = spec["tests"][0]
				results = test.get("results", [])
				if test.get("expectedStatus") != "passed" or len(results) != 1:
					raise ValueError("Negative probe was retried or marked expected-to-fail")
				result = results[0]
				errors = result.get("errors", [])
				if result.get("status") != "failed" or len(errors) != 1:
					raise ValueError("Negative probe failed outside its guard assertion")
				message = errors[0].get("message", "")
				if EGRESS_MARKER not in message or "provider.invalid" not in message:
					raise ValueError("Negative probe did not prove the intended egress rejection")

	inspect(report.get("suites", []))
	if seen != PROBES:
		raise ValueError("Negative browser probes are incomplete")
