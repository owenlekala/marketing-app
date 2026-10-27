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
