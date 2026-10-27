"""Idempotent owned setup; never resets operator records or permissions."""

import secrets

import frappe
from frappe.utils.password import get_decrypted_password, set_encrypted_password

from tag_marketing.infrastructure.schema import INDEXES, PARENT_TYPES, UNIQUE_KEYS, constraint_name

ROLES = ("Marketing User", "Marketing Manager", "WhatsApp Agent", "Marketing Analyst")


def sync_foundation():
	if frappe.db.exists("DocShare", {"share_doctype": ["in", list(PARENT_TYPES)]}):
		frappe.throw(frappe._("Remove unsupported marketing document shares before migrating."))
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)
	seed_settings()
	for doctype, keys in UNIQUE_KEYS.items():
		for fields in keys:
			ensure_unique(doctype, fields)
	for doctype, keys in INDEXES.items():
		for fields in keys:
			frappe.db.add_index(doctype, [f"`{field}`" for field in fields], constraint_name("ix", fields))


def ensure_unique(doctype, fields):
	"""The pinned adapter's add_unique lookup is not database-scoped; use SHOW INDEX."""
	name = constraint_name("uq", fields)
	if not frappe.db.has_index("tab" + doctype, name):
		if frappe.db.db_type != "mariadb":
			raise RuntimeError("Foundation constraints are qualified only on MariaDB")
		frappe.db.commit()
		columns = ", ".join(f"`{field}`" for field in fields)
		# Identifiers come exclusively from the owned static manifest, never command arguments.
		frappe.db.sql(f"ALTER TABLE `tab{doctype}` ADD UNIQUE INDEX `{name}` ({columns})")


def seed_settings():
	"""Seed before Frappe post_install.init_singles attempts an unconfigured save."""
	stored = frappe.db.get_singles_dict("WA Settings")
	if not stored.get("name"):
		frappe.db.set_single_value("WA Settings", "name", "WA Settings")
	for field in frappe.get_meta("WA Settings").fields:
		if field.default not in (None, "") and field.fieldname not in stored:
			frappe.db.set_single_value("WA Settings", field.fieldname, field.default)
	# Never rotate the digest key implicitly, including a corrupt/inaccessible existing key.
	if not frappe.db.sql(
		"SELECT 1 FROM `__Auth` WHERE doctype=%s AND name=%s AND fieldname=%s",
		("WA Settings", "WA Settings", "suppression_hmac_key"),
	):
		if stored.get("suppression_hmac_key") or any(
			frappe.db.table_exists(kind) and frappe.db.count(kind)
			for kind in ("WA Contact", "WA Suppression")
		):
			raise RuntimeError("Suppression key is missing on an existing setup; recover it before migrating")
		set_encrypted_password(
			"WA Settings", "WA Settings", secrets.token_urlsafe(48), "suppression_hmac_key"
		)
		frappe.db.set_single_value("WA Settings", "suppression_hmac_key", "********")
	else:
		get_decrypted_password("WA Settings", "WA Settings", "suppression_hmac_key", raise_exception=True)
