"""End-to-end disposable runtime probes; no credentials or message traffic."""

import importlib.metadata
import json
import os
import re
import subprocess
import sys
import time
import tomllib
import urllib.request
import uuid
from pathlib import Path

LOCK = json.loads(Path("/runtime/runtime.lock.json").read_text())
BENCH = Path("/home/frappe/dev/frappe-bench")


def get(url):
	request = urllib.request.Request(url, headers={"Host": LOCK["site"]})
	with urllib.request.urlopen(request, timeout=5) as response:
		return response.status, response.read().decode(errors="replace")


def main():
	import frappe
	from frappe.utils.background_jobs import get_redis_conn
	from frappe.utils.doctor import get_workers
	from frappe.utils.scheduler import is_schduler_process_running, is_scheduler_inactive
	from packaging.specifiers import SpecifierSet

	# Match Bench CLI's sites-directory convention for relative log/config paths.
	os.chdir(BENCH / "sites")
	frappe.init(site=LOCK["site"], sites_path=str(BENCH / "sites"))
	try:
		frappe.connect()
		result = {"python": sys.version.split()[0], "apps": frappe.get_installed_apps()}
		result["database_version"] = frappe.db.sql("select version()")[0][0]
		result["redis_cache"] = bool(frappe.cache.ping())
		result["redis_queue"] = bool(get_redis_conn().ping())
		required_apps = {"frappe", "erpnext", "hrms", "za_local_core", "za_local_payroll", "tag_marketing"}
		if not required_apps.issubset(result["apps"]):
			raise RuntimeError(
				"Required site apps are missing: " + ", ".join(sorted(required_apps - set(result["apps"])))
			)
		for app in ("hrms", "za_local_core", "za_local_payroll", "tag_marketing"):
			source = Path("/source") / app
			app_path = BENCH / "apps" / app
			if app == "tag_marketing":
				if app_path.resolve() != source:
					raise RuntimeError("Bench is not using the canonical marketing source")
			else:
				if app_path.is_symlink():
					raise RuntimeError("%s must be cloned into writable Bench storage" % app)
				revision = subprocess.check_output(
					["git", "-C", str(app_path), "rev-parse", "HEAD"], text=True
				).strip()
				if revision != LOCK["sources"][app]:
					raise RuntimeError("Bench clone revision mismatch for " + app)
			metadata = tomllib.loads((source / "pyproject.toml").read_text())
			for dependency, bounds in (
				metadata.get("tool", {}).get("bench", {}).get("frappe-dependencies", {}).items()
			):
				if frappe.get_attr(dependency + ".__version__") not in SpecifierSet(bounds):
					raise RuntimeError("Incompatible %s dependency: %s" % (app, dependency))
		if frappe.get_hooks("required_apps", app_name="za_local_payroll") != [
			"erpnext",
			"hrms",
			"za_local_core",
		]:
			raise RuntimeError("Payroll dependency metadata changed; review the locked install order")
		tiles = frappe.get_hooks("add_to_apps_screen", app_name="za_local_core") or []
		if not any(tile.get("name") == "za_local_core" for tile in tiles if isinstance(tile, dict)):
			raise RuntimeError("ZA Localisation Apps-screen tile is missing")
		if not frappe.db.exists("Dock", "za_local_payroll"):
			raise RuntimeError("Payroll navigation Dock is missing from ZA Localisation")
		result["payroll_desk_navigation"] = True
		if (
			importlib.metadata.version("reportlab")
			!= json.loads(Path("/runtime/runtime.lock.json").read_text())["python_packages"]["reportlab"]
		):
			raise RuntimeError("Locked reportlab dependency is missing")
		if not frappe.db.exists("Module Def", {"name": "WhatsApp Marketing", "app_name": "tag_marketing"}):
			raise RuntimeError("Marketing module was not registered correctly")
		if frappe.get_hooks("required_apps", app_name="tag_marketing") != ["erpnext"]:
			raise RuntimeError("Unexpected marketing app dependencies")
		result["marketing_scaffold"] = True
		private = source / "development/whatsapp_marketing/.local"
		if (
			os.access(private, os.R_OK)
			or Path("/run/secrets/db_root").exists()
			or Path("/run/secrets/site_admin").exists()
		):
			raise RuntimeError("Ordinary web service can access host credentials")
		result["credential_isolation"] = True
		for _ in range(30):
			try:
				status, body = get("http://web:8000/api/method/ping")
				if status == 200 and json.loads(body).get("message") == "pong":
					break
			except Exception:
				pass
			time.sleep(1)
		else:
			raise RuntimeError("Web endpoint did not become ready")
		result["web_ping"] = True
		status, login = get("http://web:8000/login")
		assets = re.findall(r'(?:src|href)="(/assets/[^"?]+)', login)
		if status != 200 or not assets:
			raise RuntimeError("Login page or built asset references are missing")
		for asset in list(dict.fromkeys(assets))[:3]:
			if get("http://web:8000" + asset)[0] != 200:
				raise RuntimeError("Built static asset could not be served")
		result["built_assets"] = True
		status, body = get(
			"http://realtime:%s/socket.io/?EIO=4&transport=polling" % LOCK["ports"]["realtime"]
		)
		if status != 200 or not body.startswith("0"):
			raise RuntimeError("Realtime Engine.IO handshake failed")
		result["realtime_handshake"] = True
		for _ in range(30):
			workers = get_workers()
			if any(any(q.name.endswith("marketing") for q in worker.queues) for worker in workers):
				break
			time.sleep(1)
		else:
			raise RuntimeError("Dedicated marketing worker is missing")
		result["worker_count"] = len(workers)
		job = frappe.enqueue(
			"frappe.utils.now", queue="marketing", job_id="runtime-probe-" + uuid.uuid4().hex
		)
		for _ in range(30):
			job.refresh()
			if job.is_finished:
				break
			if job.is_failed:
				raise RuntimeError("Marketing queue probe failed")
			time.sleep(1)
		else:
			raise RuntimeError("Marketing queue did not consume the probe")
		result["marketing_queue_probe"] = True
		if is_scheduler_inactive() or not is_schduler_process_running():
			raise RuntimeError("Scheduler is disabled or does not hold its process lock")
		# Observe a real scheduler-to-worker execution, not just an enabled flag.
		probe = frappe.get_doc(
			{
				"doctype": "Scheduled Job Type",
				"method": "frappe.utils.now",
				"frequency": "Cron",
				"cron_format": "* * * * *",
				"create_log": 1,
				"last_execution": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-2),
			}
		).insert()
		frappe.db.commit()
		try:
			for _ in range(90):
				frappe.db.rollback()
				executed = frappe.db.get_value(
					"Scheduled Job Log", {"scheduled_job_type": probe.name, "status": "Complete"}, "name"
				)
				if executed:
					break
				time.sleep(1)
			else:
				raise RuntimeError("Scheduled probe did not execute within 90 seconds")
			result["scheduler_execution_probe"] = True
		finally:
			frappe.delete_doc("Scheduled Job Type", probe.name)
			frappe.db.commit()
		print(json.dumps(result, indent=2))
	finally:
		frappe.destroy()


if __name__ == "__main__":
	main()
