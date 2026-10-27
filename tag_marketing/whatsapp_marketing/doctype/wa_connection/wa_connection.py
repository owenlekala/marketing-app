from tag_marketing.application.connection_records import audit_connection_change
from tag_marketing.infrastructure.documents import FoundationDocument


class WAConnection(FoundationDocument):
	def on_update(self):
		audit_connection_change(self)
