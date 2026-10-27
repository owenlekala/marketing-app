"""CLI-only fixture helpers. Not whitelisted and never called by product code."""

import json
import secrets
from pathlib import Path

import frappe

USERS = {
	"agent": ("wa-harness-agent@example.invalid", "Sales User"),
	"manager": ("wa-harness-manager@example.invalid", "System Manager"),
}


def require_disposable_site():
	lock = json.loads(
		(Path(__file__).resolve().parents[3] / "development/whatsapp_marketing/runtime.lock.json").read_text()
	)
	if frappe.local.site != lock["site"] or not frappe.conf.allow_tests:
		raise RuntimeError("Harness fixtures require the owned disposable site with allow_tests enabled")


def create_user(kind, password=None):
	email, role = USERS[kind]
	if frappe.db.exists("User", email):
		raise RuntimeError("Harness user already exists; run explicit fixture cleanup before setup")
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "WA Harness " + kind.title(),
			"enabled": 1,
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": role}],
		}
	)
	if password:
		user.new_password = password
	user.insert(ignore_permissions=True)
	return user


def prepare_browser():
	require_disposable_site()
	frappe.set_user("Administrator")
	result = {}
	try:
		for kind in USERS:
			password = secrets.token_urlsafe(36)
			user = create_user(kind, password)
			result[kind] = {"username": user.name, "password": password}
		frappe.db.commit()
	except Exception:
		frappe.db.rollback()
		raise
	return result


def cleanup_browser():
	require_disposable_site()
	frappe.set_user("Administrator")
	for kind, (email, _) in USERS.items():
		if not frappe.db.exists("User", email):
			continue
		user = frappe.get_doc("User", email)
		if user.first_name != "WA Harness " + kind.title():
			raise RuntimeError("Refusing to delete a user not owned by the harness")
		frappe.delete_doc("User", email, ignore_permissions=True)
	frappe.db.commit()
