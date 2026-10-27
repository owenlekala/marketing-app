#!/usr/bin/env python3
"""Qualify fresh ERPNext/TAG installation and two migrations on an owned temporary site."""

import json
import re
import subprocess
import sys
from pathlib import Path

from runtime import compose

SITE = "wa-foundation-qualification.localhost"
BENCH = Path("/home/frappe/dev/frappe-bench")


def inside():
	# Only the bootstrap service receives these files; normal web/test services do not.
	root_password = Path("/run/secrets/db_root").read_text().strip()
	admin_password = Path("/run/secrets/site_admin").read_text().strip()
	if (BENCH / "sites" / SITE).exists():
		raise RuntimeError("Qualification site already exists; inspect it before rerunning")

	def run(label, *args):
		result = subprocess.run(["bench", *args], cwd=BENCH, capture_output=True, text=True)
		if result.returncode:
			# A subprocess argument list or framework traceback could contain credentials.
			output = result.stdout + "\n" + result.stderr
			classes = re.findall(r"(?m)^([A-Za-z_][\w.]*(?:Error|Exception)):", output)
			reason = " -> ".join(dict.fromkeys(classes)) or "CLIError"
			details = re.findall(r"(?m)^[A-Za-z_][\w.]*(?:Error|Exception): (.+)$", output)
			if details:
				detail = details[-1]
				redactions = [root_password, admin_password]
				config_path = BENCH / "sites" / SITE / "site_config.json"
				if config_path.exists():
					config = json.loads(config_path.read_text())
					redactions += [
						value
						for key, value in config.items()
						if isinstance(value, str) and ("password" in key or "key" in key)
					]
				for value in redactions:
					if value:
						detail = detail.replace(value, "[REDACTED]")
				reason += ": " + detail[:400]
			raise RuntimeError(
				"%s failed (%s, exit %s); captured output suppressed" % (label, reason, result.returncode)
			)
		print("PASS:", label, flush=True)

	created = False
	try:
		run(
			"fresh site",
			"new-site",
			SITE,
			"--db-root-username",
			"root",
			"--db-root-password",
			root_password,
			"--admin-password",
			admin_password,
			"--mariadb-user-host-login-scope",
			"%",
		)
		created = True
		for app in ("erpnext", "tag_marketing"):
			run("install " + app, "--site", SITE, "install-app", app)
		# Run inspections in an isolated process with Frappe's required sites working directory.
		inspect = (
			"""
import hashlib, json, frappe
from frappe.utils.password import get_decrypted_password
from tag_marketing.infrastructure.schema import UNIQUE_KEYS, INDEXES, constraint_name
frappe.init(site=%r, sites_path='.')
frappe.connect()
try:
 assert set(frappe.get_installed_apps()) == {'frappe','erpnext','tag_marketing'}
 assert frappe.db.count('DocType', {'module':'WhatsApp Marketing'}) == 36
 assert frappe.db.get_single_value('WA Settings','sending_enabled') == 0
 for manifest,prefix in ((UNIQUE_KEYS,'uq'),(INDEXES,'ix')):
  for kind,keys in manifest.items():
   for fields in keys:
    assert frappe.db.has_index('tab'+kind,constraint_name(prefix,fields)),(kind,fields)
 digest=hashlib.sha256(get_decrypted_password('WA Settings','WA Settings','suppression_hmac_key').encode()).hexdigest()
 %%s
finally:
 frappe.destroy()
"""
			% SITE
		)
		seed = "frappe.db.set_single_value('WA Settings','marketing_cap',3); frappe.db.set_value('Role','Marketing Analyst','desk_access',0); frappe.db.commit(); print(json.dumps({'key_digest':digest}))"
		result = subprocess.run(
			[str(BENCH / "env/bin/python"), "-c", inspect % seed],
			cwd=BENCH / "sites",
			capture_output=True,
			text=True,
		)
		if result.returncode:
			raise RuntimeError("Fresh-install inspection failed; captured output suppressed")
		before = json.loads(result.stdout)
		for iteration in range(2):
			run("migration %s/2" % (iteration + 1), "--site", SITE, "migrate")
		verify = (
			"assert frappe.db.get_single_value('WA Settings','marketing_cap')==3; assert frappe.db.get_value('Role','Marketing Analyst','desk_access')==0; assert digest==%r; print('PASS: settings, role customisation and encrypted key preserved')"
			% before["key_digest"]
		)
		result = subprocess.run(
			[str(BENCH / "env/bin/python"), "-c", inspect % verify],
			cwd=BENCH / "sites",
			capture_output=True,
			text=True,
		)
		if result.returncode:
			raise RuntimeError("Repeated-migration inspection failed; captured output suppressed")
		print(result.stdout.strip(), flush=True)
	finally:
		if created:
			run(
				"dispose owned qualification site",
				"drop-site",
				SITE,
				"--db-root-username",
				"root",
				"--db-root-password",
				root_password,
				"--force",
				"--no-backup",
			)


def main():
	if sys.argv[1:] == ["--inside"]:
		inside()
	elif not sys.argv[1:]:
		compose(
			"run",
			"--rm",
			"--no-deps",
			"-T",
			"bootstrap",
			str(BENCH / "env/bin/python"),
			"/source/tag_marketing/development/whatsapp_marketing/qualify_foundation.py",
			"--inside",
		)
	else:
		raise RuntimeError("Run without arguments from the app root")


if __name__ == "__main__":
	try:
		main()
	except (RuntimeError, subprocess.CalledProcessError) as exc:
		message = str(exc) if isinstance(exc, RuntimeError) else "Qualification container failed"
		raise SystemExit(message) from None
