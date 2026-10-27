# ADR-001: App and design baseline

Status: Accepted. Date: 27 October 2026. Decision source: user selections and approved documentation plan.

## Context

The workspace contains Frappe/ERPNext v16 source and a separate payroll localisation app. Marketing needs independent ownership while retaining the ERPNext user experience. Official messaging needs auditable consent, approval, queued work and human reply handling.

## Decision

Build `tag_marketing` as a separate Frappe app. Require ERPNext/Frappe; do not require payroll or localisation. Use Meta Cloud API with administrator credential setup. Support one company/multiple numbers, ERPNext/CSV sources, manager-approved campaigns, a team inbox and native ordered-step automations. Preserve the capacity and configuration defaults in [product requirements](../PRODUCT_REQUIREMENTS.md).

Use native Desk navigation, forms, lists, widgets and reports. Custom inbox content remains inside a Desk Page; automation preview is read-only. Use layered server services and a durable database outbox; queues are transport. Unknown submissions require reconciliation.

## Alternatives considered

- Adding marketing to payroll couples unrelated releases/data permissions; user selected a separate app.
- BSP-first integration and self-service Embedded Signup add provider/onboarding scope; user selected direct Meta setup.
- Visual drag-and-drop journeys and AI widen the first release; user selected a native step editor and rule-based execution.
- Campaigns alone would omit requested reply handling and automation; include both in the first production release.

## Consequences

Own install/migrate metadata, roles, navigation and operational jobs. Build an optional shared-navigation adapter without a hard localisation dependency. Qualify compatibility against inspected revisions and a real disposable site before production claims. Keep app implementation unchecked until evidence exists.

Related: [architecture](../ARCHITECTURE.md), [UI rules](../UI_DESIGN_SYSTEM.md), [task sequence](../tasks/README.md), [release tests](../TESTING_AND_ACCEPTANCE.md).
