#!/usr/bin/env python3
"""Run app checks against the single locked disposable environment."""

import argparse
import fcntl
import json
import re
import subprocess
import sys
import uuid

from runtime import LOCK, PLAYWRIGHT_VERSION, ROOT, compose

PYTHON = "/home/frappe/dev/frappe-bench/env/bin/python"
APP = "/source/tag_marketing"
PRIVATE = ROOT / ".local"
MANIFEST = PRIVATE / "browser-run.json"
sys.path.insert(0, str(ROOT.parents[1]))
from tag_marketing.tests.support.reports import verify_egress_report


def python(*args):
	compose("exec", "-T", "-w", APP, "web", PYTHON, *args)


def fixtures(method, run_id):
	try:
		result = compose(
			"exec",
			"-T",
			"web",
			"bench",
			"--site",
			LOCK["site"],
			"execute",
			"tag_marketing.tests.support.site." + method,
			"--kwargs",
			json.dumps({"run_id": run_id}),
			capture_output=True,
			text=True,
		)
	except subprocess.CalledProcessError as exc:
		# Report only the exception type; tracebacks can contain fixture secrets.
		classes = re.findall(r"(?m)^([A-Za-z_][\w.]*(?:Error|Exception)):", exc.stderr + "\n" + exc.stdout)
		reason = " -> ".join(dict.fromkeys(classes)) if classes else "CLIError"
		raise RuntimeError("Fixture %s failed (%s, exit %s)" % (method, reason, exc.returncode)) from None
	return json.loads(result.stdout) if method == "prepare_browser" else None


def cleanup():
	if not MANIFEST.exists():
		print("No pending browser fixture run")
		return
	manifest = json.loads(MANIFEST.read_text())
	if manifest.get("site") != LOCK["site"] or not re.fullmatch(r"[a-f0-9]{32}", manifest.get("run_id", "")):
		raise RuntimeError("Invalid fixture recovery manifest; inspect it before cleanup")
	fixtures("cleanup_browser", manifest["run_id"])
	(PRIVATE / "browser-users.json").unlink(missing_ok=True)
	MANIFEST.unlink()


def run_egress_probes():
	try:
		compose(
			"run",
			"--rm",
			"--no-deps",
			"-e",
			"WA_TEST_OUTPUT=/test-results/network-negative",
			"-e",
			"WA_NEGATIVE_NETWORK_PROBE=1",
			"browser",
			"node",
			"node_modules/@playwright/test/cli.js",
			"test",
			"--project=desktop-light",
			"--reporter=json",
			"--max-failures=0",
			capture_output=True,
			text=True,
		)
	except subprocess.CalledProcessError as exc:
		if exc.returncode != 1:
			raise RuntimeError("Browser negative probe did not finish normally") from None
		try:
			verify_egress_report(json.loads(exc.stdout))
		except (ValueError, KeyError, TypeError, IndexError):
			raise RuntimeError("Browser negative report did not prove all intended guard failures") from None
		print("PASS: HTTP, WebSocket and API egress probes failed only for their guard assertions")
	else:
		raise RuntimeError("Browser guard failed to reject deliberate external traffic")


def egress():
	# Negative probes use no account or server; the existing Compose file expects a file mount.
	credentials = PRIVATE / "browser-users.json"
	placeholder = not credentials.exists()
	if placeholder:
		with credentials.open("x"):
			credentials.chmod(0o600)
	try:
		run_egress_probes()
	finally:
		if placeholder:
			credentials.unlink()


def browser(project=None):
	credentials = PRIVATE / "browser-users.json"
	if MANIFEST.exists() or credentials.exists():
		raise RuntimeError(
			"Pending browser fixture state; run quality.py cleanup before starting another run"
		)
	run_id = uuid.uuid4().hex
	with MANIFEST.open("x") as stream:
		MANIFEST.chmod(0o600)
		json.dump({"site": LOCK["site"], "run_id": run_id}, stream)
	try:
		accounts = fixtures("prepare_browser", run_id)
		with credentials.open("x") as stream:
			credentials.chmod(0o600)
			json.dump(accounts, stream)
		compose("run", "--rm", "--no-deps", "browser", "npm", "run", "typecheck")
		compose(
			"run",
			"--rm",
			"--no-deps",
			"-e",
			"WA_TEST_OUTPUT=/test-results/browser/" + run_id,
			"browser",
			"npm",
			"run",
			"test:browser",
			*(["--", "--project=" + project] if project else []),
		)
		print(
			"Browser evidence: development/whatsapp_marketing/.local/test-results/browser/" + run_id,
			flush=True,
		)
		run_egress_probes()
	finally:
		# The manifest survives cleanup failure, so recovery can target only this run.
		cleanup()


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"action",
		choices=["setup", "cleanup", "egress", "docs", "lint", "unit", "integration", "browser", "all"],
	)
	parser.add_argument("--browser-project", choices=["desktop-light", "desktop-dark", "tablet", "mobile"])
	args = parser.parse_args()
	action = args.action
	if args.browser_project and action != "browser":
		parser.error("--browser-project is supported only with browser")
	PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
	(PRIVATE / "test-results").mkdir(exist_ok=True)
	if action == "egress":
		egress()
		return
	if action == "cleanup":
		cleanup()
		return
	if action == "setup":
		if MANIFEST.exists() or (PRIVATE / "browser-users.json").exists():
			raise RuntimeError("Pending fixture state; run quality.py cleanup before setup")
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
		browser(args.browser_project)


if __name__ == "__main__":
	try:
		PRIVATE.mkdir(parents=True, exist_ok=True, mode=0o700)
		PRIVATE.chmod(0o700)
		with (PRIVATE / "quality.lock").open("w") as lock:
			try:
				fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
			except BlockingIOError:
				raise SystemExit("Another quality run is active; retry after it finishes") from None
			main()
	except RuntimeError as exc:
		raise SystemExit(str(exc)) from None
	except subprocess.CalledProcessError as exc:
		# Captured fixture output may contain temporary credentials: never echo it.
		raise SystemExit("Quality command failed (exit %s)" % exc.returncode) from None
