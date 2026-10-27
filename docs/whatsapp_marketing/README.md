# TAG WhatsApp Marketing implementation handbook

Baseline agreed 27 October 2026. This handbook is canonical at `docs/whatsapp_marketing/`. See [progress](PROGRESS.md) for actual implementation and verification evidence.

Build `tag_marketing`, a separate Frappe app named **TAG Marketing**, containing the **WhatsApp Marketing** module. Match the installed ERPNext Desk, including navigation, forms, widgets, theme and interaction patterns. Do not add marketing logic to payroll or modify framework core.

## Start here

1. Read [product requirements](PRODUCT_REQUIREMENTS.md), [implementation rules](IMPLEMENTATION_RULES.md), and [framework/setup](FRAMEWORK_AND_SETUP.md).
2. Read [architecture](ARCHITECTURE.md), [UI design system](UI_DESIGN_SYSTEM.md), and the relevant [page](pages/README.md) and [flow](flows/README.md).
3. Select the first unblocked [implementation task](tasks/README.md). Follow [kickoff instructions](IMPLEMENTATION_KICKOFF.md).
4. Verify against [acceptance scenarios](TESTING_AND_ACCEPTANCE.md), update [traceability](TRACEABILITY.md) and [progress](PROGRESS.md).

## Specification owners

- [Product requirements](PRODUCT_REQUIREMENTS.md): scope, requirement IDs, terminology and defaults.
- [Implementation plan](IMPLEMENTATION_PLAN.md): sequencing and phase gates.
- [Framework and setup](FRAMEWORK_AND_SETUP.md): inspected versions, development setup and runtime verification.
- [References](REFERENCES.md): official documentation and inspected source examples.
- [Architecture](ARCHITECTURE.md): boundaries, application structure and transaction ownership.
- [Data model](DATA_MODEL.md): DocTypes, fields, constraints and record lifecycles.
- [API contracts](API_CONTRACTS.md): commands, queries, errors and webhooks.
- [ERPNext integration](ERPNext_INTEGRATION.md): source mapping, source permissions and CRM triggers.
- [UI design system](UI_DESIGN_SYSTEM.md): native components and visual acceptance.
- [Permissions and privacy](PERMISSIONS_AND_PRIVACY.md): access, consent evidence, media and retention.
- [Messaging and reliability](MESSAGING_AND_RELIABILITY.md): delivery, leases, retries and recovery.
- [Operations and release](OPERATIONS_AND_RELEASE.md): deployments, monitoring and incidents.
- [Decisions](decisions/README.md): architecture decision records and change control.

## How to use this pack

These are implementation specifications. Each subject has one owner above: other files link to its definition rather than maintain copies. [Phase task files](tasks/README.md) alone own completion checkboxes; [progress](PROGRESS.md) owns evidence. Page files own presentation, flows own orchestration, and tasks own work sequencing. Proposed app paths describe future files and are not source evidence.

This handbook is versioned inside the `tag_marketing` application repository. In the parent workspace its canonical location is `tag_marketing/docs/whatsapp_marketing/`; the previous workspace location contains only a pointer. Runtime tooling is owned alongside it under `development/whatsapp_marketing/`.

The [documentation AGENTS.md](AGENTS.md) applies inside this folder. It does not automatically govern application code. The repository-level [instruction bridge](../../AGENTS.md) supplies that scope.
