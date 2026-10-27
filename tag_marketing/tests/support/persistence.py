"""Trusted synthetic test persistence; never imported by product code."""

import frappe


def raw(doctype, **values):
	"""Synthetic SQL fixtures, never a public application write path."""
	doc = frappe.get_doc({"doctype": doctype, "name": frappe.generate_hash(length=16), **values})
	doc.db_insert()
	return doc
