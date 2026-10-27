app_name = "tag_marketing"
app_title = "TAG Marketing"
app_publisher = "TAG Projects"
app_description = "WhatsApp marketing and automation for ERPNext"
app_email = "owenlekala@gmail.com"
app_license = "mit"

# Frappe is the framework; ERPNext is the only additional required app.
required_apps = ["erpnext"]

# Test-only site safety gate; no product fixture mutation during installation.
before_tests = "tag_marketing.tests.support.site.require_disposable_site"

# Owned metadata is synced before setup runs on both install and migration.
after_sync = "tag_marketing.setup.install.sync_foundation"
after_migrate = "tag_marketing.setup.install.sync_foundation"

from tag_marketing.infrastructure.schema import PARENT_TYPES

permission_query_conditions = {
	doctype: "tag_marketing.infrastructure.permissions.query_conditions" for doctype in PARENT_TYPES
}
has_permission = {
	doctype: "tag_marketing.infrastructure.permissions.has_permission" for doctype in PARENT_TYPES
}

doc_events = {"DocShare": {"validate": "tag_marketing.infrastructure.permissions.reject_owned_share"}}
