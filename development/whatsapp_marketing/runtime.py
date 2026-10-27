#!/usr/bin/env python3
"""Host-side control for the single isolated, locked development project."""

import argparse
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCK = json.loads((ROOT / "runtime.lock.json").read_text())
PLAYWRIGHT_VERSION = json.loads((ROOT.parents[1] / "package.json").read_text())["devDependencies"][
	"@playwright/test"
]
if not re.fullmatch(r"\d+\.\d+\.\d+", PLAYWRIGHT_VERSION):
	raise RuntimeError("Browser toolchain must use an exact Playwright version")


def prepare_secrets():
	directory = ROOT / ".local" / "secrets"
	directory.mkdir(parents=True, exist_ok=True, mode=0o700)
	(ROOT / ".local").chmod(0o700)
	directory.chmod(0o700)
	for name in ("db_root", "site_admin"):
		path = directory / name
		if not path.exists():
			# The private directory protects the host copy. Read-only Compose file
			# secrets must be readable by the unprivileged container UID as well.
			fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
			with os.fdopen(fd, "w") as stream:
				stream.write(secrets.token_urlsafe(36) + "\n")
			path.chmod(0o444)


def compose(*args, **options):
	env = dict(os.environ, **LOCK["images"])
	env["BROWSER_IMAGE"] = LOCK["project"] + "-chromium:" + PLAYWRIGHT_VERSION
	env.update(WEB_PORT=str(LOCK["ports"]["web"]), REALTIME_PORT=str(LOCK["ports"]["realtime"]))
	return subprocess.run(
		["docker", "compose", "--project-name", LOCK["project"], "--file", str(ROOT / "compose.yaml"), *args],
		cwd=ROOT,
		env=env,
		check=True,
		**options,
	)


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("action", choices=["config", "up", "bootstrap", "verify", "status", "stop"])
	args = parser.parse_args()
	prepare_secrets()
	if args.action == "config":
		compose("config", "--quiet")
	elif args.action == "up":
		compose("up", "-d", "--wait", "mariadb", "redis-cache", "redis-queue")
		compose("run", "--rm", "volume-init")
		compose("run", "--rm", "bootstrap")
		compose("up", "-d", "web", "realtime", "scheduler", "worker", "marketing-worker")
	elif args.action == "bootstrap":
		compose("run", "--rm", "bootstrap")
	elif args.action == "verify":
		compose("exec", "-T", "web", "env/bin/python", "/runtime/verify.py")
	elif args.action == "status":
		compose("ps", "--all")
	elif args.action == "stop":
		# Intentionally retain named volumes; there is no implicit data reset.
		compose("stop")


if __name__ == "__main__":
	try:
		main()
	except subprocess.CalledProcessError as exc:
		print("Runtime action failed with exit code %s." % exc.returncode, file=sys.stderr)
		sys.exit(exc.returncode)
