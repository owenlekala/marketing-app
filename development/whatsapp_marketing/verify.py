"""End-to-end disposable runtime probes; no credentials or message traffic."""

import json
import os
import re
from pathlib import Path
import sys
import time
import tomllib
import urllib.request
import uuid

LOCK = json.loads(Path("/runtime/runtime.lock.json").read_text())
BENCH = Path("/home/frappe/dev/frappe-bench")


def get(url):
    request = urllib.request.Request(url, headers={"Host": LOCK["site"]})
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, response.read().decode(errors="replace")


def main():
    import frappe
    from packaging.specifiers import SpecifierSet
    from frappe.utils.background_jobs import get_redis_conn
    from frappe.utils.doctor import get_workers
    from frappe.utils.scheduler import is_scheduler_inactive, is_schduler_process_running

    # Match Bench CLI's sites-directory convention for relative log/config paths.
    os.chdir(BENCH / "sites")
    frappe.init(site=LOCK["site"], sites_path=str(BENCH / "sites"))
    try:
        frappe.connect()
        result = {"python": sys.version.split()[0], "apps": frappe.get_installed_apps()}
        result["database_version"] = frappe.db.sql("select version()")[0][0]
        result["redis_cache"] = bool(frappe.cache.ping())
        result["redis_queue"] = bool(get_redis_conn().ping())
        if not {"frappe", "erpnext", "tag_marketing"}.issubset(result["apps"]):
            raise RuntimeError("Required site apps are missing")
        source = Path("/source/tag_marketing")
        if (BENCH / "apps/tag_marketing").resolve() != source:
            raise RuntimeError("Bench is not using the canonical marketing source")
        metadata = tomllib.loads((source / "pyproject.toml").read_text())
        for app, bounds in metadata["tool"]["bench"]["frappe-dependencies"].items():
            if frappe.get_attr(app + ".__version__") not in SpecifierSet(bounds):
                raise RuntimeError("Incompatible required application: " + app)
        if not frappe.db.exists("Module Def", {"name": "WhatsApp Marketing", "app_name": "tag_marketing"}):
            raise RuntimeError("Marketing module was not registered correctly")
        if frappe.get_hooks("required_apps", app_name="tag_marketing") != ["erpnext"]:
            raise RuntimeError("Unexpected marketing app dependencies")
        result["marketing_scaffold"] = True
        private = source / "development/whatsapp_marketing/.local"
        if os.access(private, os.R_OK) or Path("/run/secrets/db_root").exists() or Path("/run/secrets/site_admin").exists():
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
        status, body = get("http://realtime:%s/socket.io/?EIO=4&transport=polling" % LOCK["ports"]["realtime"])
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
        job = frappe.enqueue("frappe.utils.now", queue="marketing", job_id="runtime-probe-" + uuid.uuid4().hex)
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
        probe = frappe.get_doc({
            "doctype": "Scheduled Job Type", "method": "frappe.utils.now",
            "frequency": "Cron", "cron_format": "* * * * *", "create_log": 1,
            "last_execution": frappe.utils.add_to_date(frappe.utils.now_datetime(), minutes=-2),
        }).insert()
        frappe.db.commit()
        try:
            for _ in range(90):
                frappe.db.rollback()
                executed = frappe.db.get_value("Scheduled Job Log", {"scheduled_job_type": probe.name, "status": "Complete"}, "name")
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
