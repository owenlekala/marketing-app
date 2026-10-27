"""CLI-only, run-owned fixtures. Never whitelisted or used by product code."""

import json
import re
import secrets
from contextlib import contextmanager
from pathlib import Path

import frappe

from tag_marketing.tests.support.network import LOCAL_INFRASTRUCTURE, NetworkGuard

USERS = {
	"agent": ("wa-harness-agent@example.invalid", "Sales User"),
	"manager": ("wa-harness-manager@example.invalid", "System Manager"),
	"marketing": ("wa-marketing@example.invalid", "Marketing User"),
	"marketing_manager": ("wa-marketing-mgr@example.invalid", "Marketing Manager"),
	"analyst": ("wa-analyst@example.invalid", "Marketing Analyst"),
	"inbox": ("wa-inbox@example.invalid", "WhatsApp Agent"),
}


def require_disposable_site():
	lock = json.loads(
		(Path(__file__).resolve().parents[3] / "development/whatsapp_marketing/runtime.lock.json").read_text()
	)
	if frappe.local.site != lock["site"] or not frappe.conf.allow_tests:
		raise RuntimeError("Harness fixtures require the owned disposable site with allow_tests enabled")


def validate_run_id(run_id):
	if not isinstance(run_id, str) or not re.fullmatch(r"[a-f0-9]{32}", run_id):
		raise ValueError("A valid fixture run identifier is required")
	return run_id


def user_email(kind, run_id=None):
	email = USERS[kind][0]
	if run_id is None:
		return email
	return email.replace("@", "-" + validate_run_id(run_id) + "@", 1)


def create_user(kind, password=None, run_id=None):
	require_disposable_site()
	email = user_email(kind, run_id)
	if frappe.db.exists("User", email):
		raise RuntimeError("Harness user already exists; refusing to overwrite it")
	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": "WA Harness " + kind.title(),
			"last_name": run_id or "",
			"enabled": 1,
			"user_type": "System User",
			"send_welcome_email": 0,
			"roles": [{"role": USERS[kind][1]}],
		}
	)
	if password:
		user.new_password = password
	user.insert(ignore_permissions=True)
	return user


@contextmanager
def fixture_transaction():
	"""Apply the same network policy to CLI setup/cleanup as to test bodies."""
	with NetworkGuard(LOCAL_INFRASTRUCTURE) as guard:
		try:
			yield
			guard.assert_clean()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			raise


def prepare_browser(run_id):
	require_disposable_site()
	validate_run_id(run_id)
	frappe.set_user("Administrator")
	result = {}
	with fixture_transaction():
		for kind in USERS:
			password = secrets.token_urlsafe(36)
			user = create_user(kind, password, run_id)
			result[kind] = {"username": user.name, "password": password}
		from tag_marketing.tests.support.progress import prepare
		result["operations"] = prepare(run_id)
	return result


def cleanup_records(run_id):
	"""Validate all ownership markers before deleting anything; caller owns transaction."""
	validate_run_id(run_id)
	owned = []
	for kind in USERS:
		email = user_email(kind, run_id)
		if not frappe.db.exists("User", email):
			continue
		user = frappe.get_doc("User", email)
		if user.first_name != "WA Harness " + kind.title() or user.last_name != run_id:
			raise RuntimeError("Refusing to delete a user not owned by this fixture run")
		owned.append(email)
	from tag_marketing.tests.support.progress import cleanup
	cleanup(run_id)
	for email in owned:
		frappe.delete_doc("User", email, ignore_permissions=True)


def cleanup_browser(run_id):
	require_disposable_site()
	frappe.set_user("Administrator")
	with fixture_transaction():
		cleanup_records(run_id)
	from tag_marketing.tests.support.progress import finish_cleanup
	finish_cleanup(run_id)
