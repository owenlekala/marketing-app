#!/usr/bin/env python3
"""Run app checks against the single locked disposable environment."""

import argparse
import fcntl
import json
import re
import subprocess
import sys

from runtime import LOCK, PLAYWRIGHT_VERSION, ROOT, compose

PYTHON = "/home/frappe/dev/frappe-bench/env/bin/python"
APP = "/source/tag_marketing"
PRIVATE = ROOT / ".local"


def python(*args):
	compose("exec", "-T", "-w", APP, "web", PYTHON, *args)


def fixtures(method):
	result = compose(
		"exec",
		"-T",
		"web",
		"bench",
		"--site",
		LOCK["site"],
		"execute",
		"tag_marketing.tests.support.site." + method,
		capture_output=True,
		text=True,
	)
	return json.loads(result.stdout) if method == "prepare_browser" else None


def browser():
	credentials = PRIVATE / "browser-users.json"
	try:
		accounts = fixtures("prepare_browser")
		credentials.write_text(json.dumps(accounts))
		credentials.chmod(0o600)
		compose("run", "--rm", "--no-deps", "browser", "npm", "run", "typecheck")
		compose("run", "--rm", "--no-deps", "browser", "npm", "run", "test:browser")
		# A negative probe must exit nonzero for the guard's specific assertion.
		try:
			compose(
				"run",
				"--rm",
				"--no-deps",
				"-e",
				"WA_TEST_OUTPUT=/test-results/network-negative",
				"browser",
				"npm",
				"run",
				"test:network-negative",
				capture_output=True,
				text=True,
			)
		except subprocess.CalledProcessError as exc:
			if "Unexpected outbound request" not in exc.stdout:
				raise RuntimeError("Browser negative probe failed for an unexpected reason") from None
			print("PASS: deliberate browser egress was blocked and failed the test")
		else:
			raise RuntimeError("Browser guard failed to reject deliberate external traffic")
	finally:
		# Delete only our owned synthetic users; never rotate real/admin credentials.
		try:
			fixtures("cleanup_browser")
		finally:
			credentials.unlink(missing_ok=True)


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("action", choices=["setup", "docs", "lint", "unit", "integration", "browser", "all"])
	action = parser.parse_args().action
	PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
	(PRIVATE / "test-results").mkdir(exist_ok=True)
	if action == "setup":
		# Placeholder exists only to satisfy the optional service's read-only mount.
		credentials = PRIVATE / "browser-users.json"
		credentials.touch(mode=0o600, exist_ok=True)
		try:
			build = PRIVATE / "browser-build"
			build.mkdir(exist_ok=True)
			(build / "Dockerfile").write_text(
				"FROM " + LOCK["images"]["BENCH_IMAGE"] + "\n"
				"USER root\nENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright\n"
				"RUN npm exec --yes --package=@playwright/test@"
				+ PLAYWRIGHT_VERSION
				+ " -- playwright install --with-deps --only-shell chromium\n"
			)
			compose("build", "browser-setup")
			python(
				"-m",
				"pip",
				"install",
				"--require-hashes",
				"-r",
				"development/whatsapp_marketing/requirements-dev.lock",
			)
			compose("run", "--rm", "--no-deps", "browser-setup", "npm", "ci", "--ignore-scripts")
		finally:
			credentials.unlink(missing_ok=True)
		return
	if action in ("docs", "all"):
		guide = (ROOT.parents[1] / "docs/whatsapp_marketing/TESTING_AND_ACCEPTANCE.md").read_text()
		section = guide.split("## Repeatable documentation structural check", 1)[1]
		check = re.search(r"python3 - <<'PY'\n(.*?)\nPY\n", section, re.S)
		if check is None:
			raise RuntimeError("Canonical documentation checker is missing")
		subprocess.run(
			[sys.executable, "-"], cwd=ROOT.parents[1], input=check.group(1), text=True, check=True
		)
	if action in ("lint", "all"):
		python("-m", "ruff", "check", "tag_marketing", "development/whatsapp_marketing")
		python("-m", "ruff", "format", "--check", "tag_marketing", "development/whatsapp_marketing")
		python("-m", "mypy")
	if action in ("unit", "all"):
		python("-m", "unittest", "discover", "-s", "tag_marketing/tests/unit", "-t", ".", "-v")
	if action in ("integration", "all"):
		compose("exec", "-T", "web", "bench", "--site", LOCK["site"], "run-tests", "--app", "tag_marketing")
	if action in ("browser", "all"):
		browser()


if __name__ == "__main__":
	try:
		PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
		with (PRIVATE / "quality.lock").open("w") as lock:
			try:
				fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
			except BlockingIOError:
				raise SystemExit("Another quality run is active; retry after it finishes") from None
			main()
	except subprocess.CalledProcessError as exc:
		# Captured fixture output may contain temporary credentials: never echo it.
		raise SystemExit("Quality command failed (exit %s)" % exc.returncode) from None
