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

scheduler_events = {"cron": {"* * * * *": ["tag_marketing.application.event_recovery.recover_due_work"]}}

from tag_marketing.infrastructure.schema import PARENT_TYPES

permission_query_conditions = {
	doctype: "tag_marketing.infrastructure.permissions.query_conditions" for doctype in PARENT_TYPES
}
has_permission = {
	doctype: "tag_marketing.infrastructure.permissions.has_permission" for doctype in PARENT_TYPES
}

doc_events = {"DocShare": {"validate": "tag_marketing.infrastructure.permissions.reject_owned_share"}}

# The current Desk Apps screen reads this hook; legacy icon rows alone do not show an app.
app_logo_url = "/assets/tag_marketing/images/tag-marketing.svg"
add_to_apps_screen = [
	{
		"name": app_name,
		"title": app_title,
		"logo": app_logo_url,
		"route": "",
		"sequence_id": 30,
		"has_permission": "tag_marketing.application.navigation.can_open_app",
	}
]
before_install = "tag_marketing.setup.navigation.check_navigation_ownership"
before_migrate = "tag_marketing.setup.navigation.check_navigation_ownership"

# Native asset bundling; styles are scoped to owned content.
app_include_js = ["tag_marketing.bundle.js"]
app_include_css = ["tag_marketing.bundle.css"]

doctype_js = {
	"WA Contact": "tag_marketing/whatsapp_marketing/doctype/wa_contact/wa_contact.js",
	"WA Import Batch": "tag_marketing/whatsapp_marketing/doctype/wa_import_batch/wa_import_batch.js",
}
doctype_list_js = {
	"WA Contact": "tag_marketing/whatsapp_marketing/doctype/wa_contact/wa_contact_list.js",
}
