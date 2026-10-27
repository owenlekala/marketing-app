# References and source baseline

Reviewed 27 October 2026. Local source facts are inspected, not proof that a site is running these revisions. Web references are living documentation; recheck provider contracts during implementation.

## Local baseline

- Frappe 16.53.0, commit `e8d41dd006`: [version](../../../frappe/frappe/__init__.py), [Python requirements](../../../frappe/pyproject.toml), [Node requirements](../../../frappe/package.json).
- ERPNext 16.52.1, commit `ade850bbd6`: [version](../../../erpnext/erpnext/__init__.py), [dependencies](../../../erpnext/pyproject.toml).
- Inspected fork origins are `github.com/tagprojectsza/frappe.git`, `github.com/tagprojectsza/erpnext.git`, `github.com/tagprojectsza/frappe_za_payroll.git` and `github.com/tagprojectsza/frappe_docker.git`. Preserve these fork identities and pinned revisions rather than silently substituting upstream repositories.
- Separate sibling repositories; initial host/daemon observations are in [WA-P0-001 evidence](PROGRESS.md#wa-p0-001--source-and-deployment-baseline). The qualified disposable runtime and actual probes are recorded in [WA-P0-002 evidence](PROGRESS.md#wa-p0-002--disposable-development-runtime).

## Navigation and widgets

- [ERPNext Dock](../../../erpnext/erpnext/dock/erpnext/erpnext.json), [CRM Sidebar](../../../erpnext/erpnext/crm/sidebar/crm/crm.json), [CRM Workspace](../../../erpnext/erpnext/crm/workspace/crm/crm.json).
- [Dock controller](../../../frappe/frappe/desk/doctype/dock/dock.py), [Sidebar controller](../../../frappe/frappe/desk/doctype/sidebar/sidebar.py), [Workspace controller](../../../frappe/frappe/desk/doctype/workspace/workspace.py), [Number Card metadata](../../../frappe/frappe/desk/doctype/number_card/number_card.json).
- [Existing payroll navigation](../../../frappe_za_payroll/za_local_payroll/dock/za_local_payroll/za_local_payroll.json), [dashboard installation](../../../frappe_za_payroll/za_local_payroll/install.py), [payroll hooks](../../../frappe_za_payroll/za_local_payroll/hooks.py). These demonstrate suite integration but are not dependencies of marketing.

## Controls, styles and services

- [Form view](../../../frappe/frappe/public/js/frappe/form/form.js), [List view](../../../frappe/frappe/public/js/frappe/list/list_view.js), [Dialog](../../../frappe/frappe/public/js/frappe/ui/dialog.js), [report view](../../../frappe/frappe/public/js/frappe/views/reports/query_report.js).
- [Desk variables](../../../frappe/frappe/public/scss/desk/variables.scss), [theme variables](../../../frappe/frappe/public/scss/desk/css_variables.scss), [spacing](../../../frappe/frappe/public/scss/espresso/_spacing.scss), [typography](../../../frappe/frappe/public/scss/espresso/_typography.scss), [borders](../../../frappe/frappe/public/scss/espresso/_borders.scss), [shadows](../../../frappe/frappe/public/scss/espresso/_shadows.scss), [icons](../../../frappe/frappe/public/icons/espresso/icons.svg).
- [Background jobs](../../../frappe/frappe/utils/background_jobs.py), [realtime publishing](../../../frappe/frappe/realtime/__init__.py), [realtime permissions](../../../frappe/frappe/realtime/handlers.py), [ERPNext hooks](../../../erpnext/erpnext/hooks.py).
- [Development Compose example](../../../frappe_docker/devcontainer-example/docker-compose.yml), [installer options](../../../frappe_docker/development/installer.py), [production service layout](../../../frappe_docker/compose.yaml), [development guide](../../../frappe_docker/docs/05-development/01-development.md). The older prose's Node 14/16 examples do not match the inspected application manifests.

## Official framework documentation

- [Installation](https://docs.frappe.io/framework/user/en/installation), [Bench](https://docs.frappe.io/framework/user/en/bench), [Apps](https://docs.frappe.io/framework/user/en/basics/apps), [Create an app](https://docs.frappe.io/framework/user/en/tutorial/create-an-app): development lifecycle and app structure.
- [Document API](https://docs.frappe.io/framework/user/en/api/document), [Database API](https://docs.frappe.io/framework/user/en/api/database), [Hooks](https://docs.frappe.io/framework/user/en/python-api/hooks), [Permissions](https://docs.frappe.io/framework/user/en/basics/users-and-permissions): persistence, integration and access boundaries.
- [Form scripts](https://docs.frappe.io/framework/user/en/api/form), [Page API](https://docs.frappe.io/framework/user/en/api/page), [Controls](https://docs.frappe.io/framework/user/en/api/controls), [Asset bundling](https://docs.frappe.io/framework/user/en/basics/asset-bundling): native UI and assets.
- [Background jobs](https://docs.frappe.io/framework/user/en/api/background_jobs), [Realtime](https://docs.frappe.io/framework/user/en/api/realtime), [Testing](https://docs.frappe.io/framework/user/en/testing): asynchronous execution and validation.
- [ERPNext Campaign](https://docs.frappe.io/erpnext/campaign): CRM campaign semantics. Exact source mappings are in [ERPNext integration](ERPNext_INTEGRATION.md).

## Official messaging and privacy references

- [WhatsApp Business Messaging Policy](https://business.whatsapp.com/policy): inspected policy, including permission, templates, opt-outs and reply-window constraints. App policy is intentionally conservative; see [privacy](PERMISSIONS_AND_PRIVACY.md).
- [WhatsApp pricing](https://whatsappbusiness.com/products/platform-pricing/): rates and charging are external; estimates are never invoices.
- [Meta WhatsApp overview](https://developers.facebook.com/documentation/business-messaging/whatsapp/overview) and [webhooks](https://developers.facebook.com/documentation/business-messaging/whatsapp/webhooks/overview): retrieval was rate-limited during planning. API version, permissions, payloads, supported media and current limits require fresh official verification and captured contract fixtures in WA-P2-001. Do not claim these pages were fully verified.
- [Meta webhook reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/): inspected GET verification/POST signature distinction. This archived SDK is reference evidence only; do not install it.
- [Information Regulator POPIA guidance](https://inforegulator.org.za/popia/): consent and direct-marketing context; configure local retention and privacy policy explicitly.

## Reference maintenance

When a source changes, record review date and affected requirements. Resolve a mismatch against the actual supported deployment version; update the ADR if architecture changes. Keep copied snippets short and annotate whether a statement is a source fact or a chosen product rule.

## Harness references reviewed 27 October 2026

- [Frappe v16 integration testing](https://docs.frappe.io/framework-git/testing/integration-testing) and [unit testing](https://docs.frappe.io/framework-git/testing/unit-testing): supported classes. Actual rollback scope is verified against [the pinned IntegrationTestCase](../../../frappe/frappe/tests/classes/integration_test_case.py); this local implementation adds per-test rollback.
- [Playwright network interception](https://playwright.dev/docs/network) and [BrowserContext](https://playwright.dev/docs/api/class-browsercontext): routes, service-worker blocking and WebSocket interception. The harness uses pinned Playwright 1.58.2, not an implicit latest toolchain.
- [mypy configuration](https://mypy.readthedocs.io/en/stable/config_file.html): pyproject configuration and module overrides; dynamic Frappe code is distinguished from strictly typed boundaries.
