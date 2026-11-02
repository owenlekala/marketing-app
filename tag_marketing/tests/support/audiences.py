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
	return {"source": lead.name, "source_label": lead.lead_name, "run_id": run_id, "phone": local_phone}


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
	from tag_marketing.tests.support.site import user_email

	owner = user_email("audience_manager", run_id)
	files = frappe.get_all(
		"File",
		filters={"file_name": ["like", f"wa-browser-import-{run_id}-%"]},
		fields=["name", "file_name", "owner", "is_private", "attached_to_doctype", "attached_to_name"],
	)
	if any(file.owner != owner or file.is_private != 1 for file in files):
		raise RuntimeError("Refusing to clean an import file not owned by the audience browser fixture")
	batch_names = [
		batch.name
		for file in files
		for batch in frappe.get_all(
			"WA Import Batch",
			filters={"source_file": file.name, "requested_by": owner},
			fields=["name", "company"],
		)
		if batch.company == metadata["company"]
	]
	for batch_name in batch_names:
		batch = frappe.db.get_value(
			"WA Import Batch", batch_name, ["source_file", "result_file"], as_dict=True
		)
		if not batch or batch.source_file not in {file.name for file in files}:
			raise RuntimeError("Refusing to remove an import batch without a run-owned source file")
		frappe.db.delete("WA Import Row", {"batch": batch_name})
		frappe.db.delete(
			"WA Operation",
			{"target_doctype": "WA Import Batch", "target_name": batch_name, "requested_by": owner},
		)
		frappe.db.delete(
			"WA Import Batch", {"name": batch_name, "requested_by": owner, "company": metadata["company"]}
		)
		if batch.result_file:
			files.extend(
				frappe.get_all(
					"File",
					filters={"name": batch.result_file},
					fields=[
						"name",
						"file_name",
						"owner",
						"is_private",
						"attached_to_doctype",
						"attached_to_name",
					],
				)
			)
	for file in files:
		if file.attached_to_doctype == "WA Import Batch" and file.attached_to_name not in batch_names:
			raise RuntimeError("Refusing to remove a file attached to a non-fixture batch")
		path = Path(frappe.get_doc("File", file.name).get_full_path())
		frappe.db.delete("File", {"name": file.name})
		path.unlink(missing_ok=True)
	contact_names = frappe.get_all(
		"WA Contact",
		filters={"company": metadata["company"], "phone_e164": "+27" + metadata["phone"][1:]},
		pluck="name",
	)
	for contact_name in contact_names:
		frappe.db.delete(
			"WA Consent Event",
			{"contact": contact_name, "company": metadata["company"], "purpose": "Marketing"},
		)
		frappe.db.delete(
			"WA Suppression",
			{"contact": contact_name, "company": metadata["company"], "purpose": "Marketing"},
		)
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
