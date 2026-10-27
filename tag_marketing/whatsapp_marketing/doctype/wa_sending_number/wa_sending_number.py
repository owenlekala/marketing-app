from tag_marketing.application.connection_records import audit_number_change
from tag_marketing.infrastructure.documents import FoundationDocument


class WASendingNumber(FoundationDocument):
	def on_update(self):
		audit_number_change(self)
