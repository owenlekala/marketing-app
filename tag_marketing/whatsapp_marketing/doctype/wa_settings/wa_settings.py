from tag_marketing.infrastructure.documents import FoundationDocument


class WASettings(FoundationDocument):
	pass


def on_doctype_update():
	from tag_marketing.setup.install import seed_settings

	seed_settings()
