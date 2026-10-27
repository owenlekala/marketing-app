"""Company and conversation boundaries shared by list and direct document checks."""

import frappe
from frappe.permissions import get_allowed_docs_for_doctype, get_user_permissions

from tag_marketing.infrastructure.schema import PARENT_TYPES

INBOX_TYPES = frozenset({"WA Conversation", "WA Conversation Read", "WA Conversation Note", "WA Message"})
# These projections require feature-specific source/target reauthorisation, not bare DocPerms.
DEFERRED_READ_TYPES = frozenset(
	{
		"WA Contact",
		"WA Campaign",
		"WA Campaign Snapshot",
		"WA Campaign Recipient",
		"WA Import Row",
		"WA Operation",
	}
)


def company_allowed(company, user, doctype):
	if not company or user == "Guest":
		return False
	permissions = get_user_permissions(user).get("Company", [])
	allowed = get_allowed_docs_for_doctype(permissions, doctype)
	return not allowed or company in allowed


def conversation_scope(user, alias):
	principal = frappe.db.escape(user)
	return (
		f"({alias}.`assigned_to` = {principal} OR EXISTS "
		f"(SELECT 1 FROM `tabUser Group Member` gm WHERE gm.parent={alias}.`team` "
		f"AND gm.parenttype='User Group' AND gm.user={principal}))"
	)


def query_conditions(user=None, doctype=None):
	user = user or frappe.session.user
	if doctype not in PARENT_TYPES or doctype == "WA Settings":
		return "1=0"
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if not company_allowed(company, user, doctype) or doctype in DEFERRED_READ_TYPES:
		return "1=0"
	table = f"`tab{doctype}`"
	conditions = [f"{table}.`company`={frappe.db.escape(company)}"]
	roles = set(frappe.get_roles(user))
	if doctype in INBOX_TYPES:
		if "Marketing Manager" not in roles:
			if "WhatsApp Agent" not in roles:
				return "1=0"
			if doctype == "WA Conversation":
				conditions.append(conversation_scope(user, table))
			else:
				conditions.append(
					f"EXISTS (SELECT 1 FROM `tabWA Conversation` c WHERE c.name={table}.`conversation` "
					f"AND c.company={table}.company AND {conversation_scope(user, 'c')})"
				)
		if doctype == "WA Conversation Read":
			conditions.append(f"{table}.`user`={frappe.db.escape(user)}")
	return " AND ".join(conditions)


def has_permission(doc, ptype=None, user=None, **kwargs):
	user = user or frappe.session.user
	if doc.doctype == "WA Settings":
		return "System Manager" in frappe.get_roles(user)
	if ptype not in ("read", "select") or doc.doctype in DEFERRED_READ_TYPES:
		return False
	company = frappe.db.get_single_value("WA Settings", "marketing_company")
	if doc.company != company or not company_allowed(company, user, doc.doctype):
		return False
	if doc.doctype in INBOX_TYPES:
		if doc.doctype == "WA Conversation Read" and doc.user != user:
			return False
		if "Marketing Manager" in frappe.get_roles(user):
			return True
		if "WhatsApp Agent" not in frappe.get_roles(user):
			return False
		conversation = (
			doc if doc.doctype == "WA Conversation" else frappe.get_doc("WA Conversation", doc.conversation)
		)
		if conversation.company != company:
			return False
		return conversation.assigned_to == user or bool(
			conversation.team
			and frappe.db.exists(
				"User Group Member", {"parent": conversation.team, "parenttype": "User Group", "user": user}
			)
		)
	return True


def reject_owned_share(doc, method=None):
	if doc.share_doctype in PARENT_TYPES:
		frappe.throw(
			frappe._("Marketing records use company and assignment permissions and cannot be shared."),
			frappe.PermissionError,
		)
