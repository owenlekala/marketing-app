"""CLI-only persisted progress fixtures with recoverable setting ownership."""

import json
from hashlib import sha256
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import frappe

from tag_marketing.tests.support.persistence import raw
from tag_marketing.tests.support.site import require_disposable_site, user_email, validate_run_id

STATES = ("Pending", "Running", "Succeeded", "Failed", "Cancelled")


def manifest_path(run_id):
	require_disposable_site()
	return Path(frappe.get_site_path("private", "wa-progress-" + validate_run_id(run_id) + ".json"))


def identity(run_id, state):
	return "wa-progress-" + validate_run_id(run_id) + "-" + state.lower()


def locked_company():
	rows = frappe.db.sql(
		"SELECT value FROM tabSingles WHERE doctype='WA Settings' AND field='marketing_company' FOR UPDATE"
	)
	return rows[0][0] if rows else None


def prepare(run_id):
	path = manifest_path(run_id)
	previous = locked_company()
	company = previous or "_WA Harness " + run_id
	metadata = {"run_id": run_id, "previous": previous, "company": company, "changed": not bool(previous)}
	with path.open("x") as stream:
		path.chmod(0o600)
		json.dump(metadata, stream)
	if not previous:
		raw(
			"Company",
			name=company,
			company_name=company,
			abbr="W" + run_id[:4],
			country="South Africa",
			default_currency="ZAR",
		)
		frappe.db.set_single_value("WA Settings", "marketing_company", company)
	connection = raw(
		"WA Connection",
		name="wa-progress-connection-" + run_id,
		company=company,
		connection_name="WA Harness " + run_id,
		# A fixture-only ready connection exposes the native template draft flow.
		status="Ready",
	)
	result = {}
	for state in STATES:
		name = identity(run_id, state)
		raw(
			"WA Operation",
			name=name,
			company=company,
			operation_type="connections.validate_connection",
			requested_by=user_email("manager", run_id),
			request_id=str(uuid5(NAMESPACE_URL, name)),
			request_hash=sha256(name.encode()).hexdigest(),
			target_doctype="WA Connection",
			target_name=connection.name,
			status=state,
			progress_percent=100 if state == "Succeeded" else 35 if state != "Pending" else 0,
		)
		result[state] = name
	return result


def cleanup(run_id):
	path = manifest_path(run_id)
	if not path.exists():
		return
	metadata = json.loads(path.read_text())
	if (
		metadata.get("run_id") != run_id
		or metadata.get("changed") != (not bool(metadata.get("previous")))
		or metadata.get("company") != (metadata.get("previous") or "_WA Harness " + run_id)
	):
		raise RuntimeError("Invalid progress fixture ownership metadata")
	company = metadata["company"]
	connection_name = "wa-progress-connection-" + run_id
	owned = []
	for state in STATES:
		name = identity(run_id, state)
		if not frappe.db.exists("WA Operation", name):
			continue
		doc = frappe.get_doc("WA Operation", name)
		if (
			doc.company != company
			or doc.requested_by != user_email("manager", run_id)
			or doc.request_hash != sha256(name.encode()).hexdigest()
			or doc.target_name != connection_name
			or doc.target_doctype != "WA Connection"
			or doc.operation_type != "connections.validate_connection"
		):
			raise RuntimeError("Refusing to delete an operation not owned by this fixture run")
		owned.append(name)
	connection = (
		frappe.get_doc("WA Connection", connection_name)
		if frappe.db.exists("WA Connection", connection_name)
		else None
	)
	if connection and (connection.company != company or connection.connection_name != "WA Harness " + run_id):
		raise RuntimeError("Refusing to delete an unrelated connection")
	templates = frappe.get_all(
		"WA Template",
		filters={"connection": connection_name},
		fields=["name", "company", "template_name"],
	)
	for template in templates:
		if template.company != company or not template.template_name.startswith(
			"wa_browser_template_" + run_id + "_"
		):
			raise RuntimeError("Refusing to delete a template not owned by this browser fixture")
		frappe.db.delete("WA Template Revision", {"template": template.name})
		frappe.db.delete("WA Operation", {"target_doctype": "WA Template", "target_name": template.name})
		frappe.db.delete("WA Template", {"name": template.name})
	# Lock the exact setting before compare-and-restore; never overwrite another editor's change.
	current_company = locked_company()
	owned_company = metadata["changed"] and frappe.db.exists("Company", company)
	if owned_company and current_company != company:
		raise RuntimeError("Marketing company changed during the fixture run; inspect before cleanup")
	for name in owned:
		frappe.db.delete("WA Operation", {"name": name})
	if connection:
		from frappe.model.delete_doc import check_if_doc_is_dynamically_linked, check_if_doc_is_linked

		check_if_doc_is_linked(connection)
		check_if_doc_is_dynamically_linked(connection)
		frappe.db.delete("WA Connection", {"name": connection_name})
	if owned_company:
		from frappe.model.delete_doc import check_if_doc_is_dynamically_linked, check_if_doc_is_linked

		frappe.db.set_single_value("WA Settings", "marketing_company", metadata["previous"])
		doc = frappe.get_doc("Company", company)
		check_if_doc_is_linked(doc)
		check_if_doc_is_dynamically_linked(doc)
		frappe.db.delete("Company", {"name": company})
		frappe.clear_document_cache("Company", company)


def finish_cleanup(run_id):
	# Called only after the transaction committed, so failed cleanup remains recoverable.
	manifest_path(run_id).unlink(missing_ok=True)
