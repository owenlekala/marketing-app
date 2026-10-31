"""Run-owned ERPNext audience fixtures for native Desk browser tests."""

import json
from pathlib import Path

import frappe

from tag_marketing.tests.support.persistence import raw
from tag_marketing.tests.support.site import require_disposable_site, validate_run_id


def manifest_path(run_id: str) -> Path:
	require_disposable_site()
	return Path(frappe.get_site_path("private", "wa-audience-" + validate_run_id(run_id) + ".json"))


def prepare(run_id: str, company: str) -> dict[str, str]:
	path = manifest_path(run_id)
	previous_sources = frappe.get_all(
		"WA Source Type", filters={"parent": "WA Settings"}, fields=["source_doctype", "idx"]
	)
	lead_name = "wa-browser-audience-" + run_id
	local_phone = f"082{int(run_id[:12], 16) % 10_000_000:07d}"
	metadata = {
		"run_id": run_id,
		"company": company,
		"lead_name": lead_name,
		"phone": local_phone,
		"previous_sources": previous_sources,
	}
	with path.open("x") as stream:
		path.chmod(0o600)
		json.dump(metadata, stream)
	frappe.db.delete("WA Source Type", {"parent": "WA Settings"})
	raw(
		"WA Source Type",
		parent="WA Settings",
		parenttype="WA Settings",
		parentfield="enabled_source_types",
		source_doctype="Lead",
		idx=1,
	)
	lead = raw(
		"Lead",
		name=lead_name,
		lead_name=lead_name,
		mobile_no=local_phone,
		country="South Africa",
		company=company,
	)
	return {"source": lead.name, "source_label": lead.lead_name}


def cleanup(run_id: str) -> None:
	path = manifest_path(run_id)
	if not path.exists():
		return
	metadata = json.loads(path.read_text())
	if metadata.get("run_id") != run_id or metadata.get("lead_name") != "wa-browser-audience-" + run_id:
		raise RuntimeError("Invalid browser audience fixture ownership metadata")
	lead_name = metadata["lead_name"]
	lead = frappe.db.get_value("Lead", lead_name, ["company", "mobile_no", "country"], as_dict=True)
	if lead and (
		lead.company != metadata.get("company")
		or lead.mobile_no != metadata.get("phone")
		or lead.country != "South Africa"
	):
		raise RuntimeError("Refusing to delete an ERPNext source not owned by this browser fixture")
	current_sources = frappe.get_all(
		"WA Source Type", filters={"parent": "WA Settings"}, pluck="source_doctype"
	)
	if current_sources != ["Lead"]:
		raise RuntimeError("Enabled source types changed during the browser fixture; inspect before cleanup")
	contact_names = frappe.get_all(
		"WA Contact",
		filters={"company": metadata["company"], "phone_e164": "+27" + metadata["phone"][1:]},
		pluck="name",
	)
	for contact_name in contact_names:
		frappe.db.delete("WA Contact Tag", {"parent": contact_name})
		frappe.db.delete("WA Source Link", {"parent": contact_name})
		frappe.db.delete("WA Contact", {"name": contact_name})
	if lead:
		frappe.db.delete("Lead", {"name": lead_name})
	frappe.db.delete("WA Source Type", {"parent": "WA Settings"})
	for row in metadata["previous_sources"]:
		raw(
			"WA Source Type",
			parent="WA Settings",
			parenttype="WA Settings",
			parentfield="enabled_source_types",
			source_doctype=row["source_doctype"],
			idx=row["idx"],
		)
	path.unlink(missing_ok=True)
