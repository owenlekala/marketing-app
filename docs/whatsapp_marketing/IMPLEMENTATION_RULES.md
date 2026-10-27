# Implementation rules

Scope: all future `tag_marketing` application code, assets, tests, migrations and documentation. These rules become discoverable from app-level AGENTS.md in [WA-P0-003](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-003).

1. Start with the linked task and its owning specifications. Implement the first unblocked task; record scope changes before affected code changes.
2. Preserve [v1 scope and defaults](PRODUCT_REQUIREMENTS.md). AI, other channels, n8n, embedded signup and drag-and-drop editing require a later decision.
3. Keep domain decisions in server-side services. Controllers and endpoints validate permissions and delegate. UI validation improves feedback but never supplies authorisation.
4. Use DocTypes and supported Frappe APIs. Follow the inspected v16 manifests and [reference source](REFERENCES.md); do not copy an older tutorial's runtime requirements.
5. Do not edit `frappe`, `erpnext`, payroll, or shared localisation code to implement marketing. Use owned hooks and adapters. An exceptional integration change needs an ADR and explicit scope review.
6. Use native Desk forms, lists, widgets, reports, controls and tokens. Custom layouts stay inside a native Page and scoped `.tag-marketing` styles. No global theme overrides or new UI framework without an ADR.
7. Treat companies, source permissions, attachments, reports, exports and realtime recipients as authorisation boundaries. Deny direct REST edits to managed workflow and delivery fields.
8. Freeze approved content and audience; invalidate approval after material changes. Recheck live consent, suppression and readiness before submission.
9. Persist work before enqueueing. Queue on commit and recover from database records. Never call Meta during a CRM source transaction or hold a database transaction across HTTP.
10. Do not promise exactly-once provider delivery. Unknown submission outcomes require reconciliation; never blindly resend them.
11. Store secrets in protected fields, files privately, and sensitive logs with redaction. Never include actual credentials or customer data in tests or docs.
12. Complete vertical slices: data, service, permissions, UI states, failure recovery, meaningful tests and operator evidence. Do not ship empty handlers or success-only implementations as complete.
13. Run the [relevant checks](TESTING_AND_ACCEPTANCE.md), capture UI evidence against ERPNext, and record actual commands/results in [progress](PROGRESS.md).
14. Update the owning spec, tasks, flows and acceptance checks for changed behaviour. Record architecture changes through [ADR procedure](decisions/README.md) before implementing the affected design.
15. Never label mocks, unchecked migrations, untested runtime assumptions or partial features production-ready. Passing documentation checks does not satisfy application release gates.
16. Preserve operator customisations during migrations. Install and migrate twice on a disposable site; never run destructive qualification tests on production.

17. Keep one canonical handbook at `docs/whatsapp_marketing/`. Move it when repository ownership changes; retain only a pointer if necessary. Define fields, defaults, APIs, policies, UI rules and completion rules in their owning document and link elsewhere. Do not duplicate task/phase status checklists or maintain synchronised editable handbook copies.
