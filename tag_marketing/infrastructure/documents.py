"""Thin lifecycle adapter; application services own validation and audit."""

from frappe.model.document import Document

from tag_marketing.application.foundation import audit_settings, validate_record


class FoundationDocument(Document):
	def before_validate(self):
		validate_record(self)

	def on_update(self):
		if self.doctype == "WA Settings":
			audit_settings(self)

	def on_trash(self):
		from tag_marketing.application.foundation import deny_feature_write

		deny_feature_write(self.doctype)

	def before_rename(self, *args, **kwargs):
		from tag_marketing.application.foundation import deny_feature_write

		deny_feature_write(self.doctype)
