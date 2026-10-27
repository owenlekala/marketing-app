# Application instructions

These instructions govern this repository, including application code, runtime tooling and documentation.

- Start with the [handbook](docs/whatsapp_marketing/README.md), [kickoff](docs/whatsapp_marketing/IMPLEMENTATION_KICKOFF.md), [implementation rules](docs/whatsapp_marketing/IMPLEMENTATION_RULES.md) and [progress](docs/whatsapp_marketing/PROGRESS.md).
- Implement the first dependency-ready task in the [task index](docs/whatsapp_marketing/tasks/README.md), one task at a time. Read its owning specifications before editing code.
- Follow clean architecture and complete the task's permissions, failure handling and verification. Do not label incomplete or unverified work production-ready.
- Reuse native Frappe/ERPNext components and theme tokens under the [UI design system](docs/whatsapp_marketing/UI_DESIGN_SYSTEM.md).
- Keep specifications in their owning handbook documents; link to them rather than duplicating rules here. Record architectural changes through the [ADR procedure](docs/whatsapp_marketing/decisions/README.md) before affected implementation.
- Record actual checks and blockers in progress; task checkboxes belong only to their phase definitions. Preserve stable requirement, task and acceptance IDs.
- Do not change sibling framework, ERPNext or payroll repositories. Keep credentials and private runtime files out of Git.
- The nested documentation AGENTS.md governs documentation edits only; this file supplies repository-wide scope.
