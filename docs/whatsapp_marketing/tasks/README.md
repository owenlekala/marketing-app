# Task index

Choose the first dependency-ready task. Each phase contains four tasks in a serial dependency chain. The phase documents own task completion checkboxes; this index is navigation, not a second status tracker.

Read [implementation rules](../IMPLEMENTATION_RULES.md), [kickoff](../IMPLEMENTATION_KICKOFF.md), [phase gates](../IMPLEMENTATION_PLAN.md) and [progress](../PROGRESS.md).

## Ordered backlog

### P0 — Environment and bootstrap

- [WA-P0-001: Verify source and deployment baseline](P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-001)
- [WA-P0-002: Establish reproducible disposable Docker/Bench runtime](P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-002)
- [WA-P0-003: Create application repository and scoped instruction bridge](P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-003)
- [WA-P0-004: Configure test harness and deterministic adapters](P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-004)

### P1 — App and native UI

- [WA-P1-001: Implement owned schema, roles and settings guards](P1-APP-AND-NATIVE-UI.md#wa-p1-001)
- [WA-P1-002: Register owned Dock, Sidebar and workspace](P1-APP-AND-NATIVE-UI.md#wa-p1-002)
- [WA-P1-003: Build native UI and error/progress foundations](P1-APP-AND-NATIVE-UI.md#wa-p1-003)
- [WA-P1-004: Verify ERPNext parity and install behaviour](P1-APP-AND-NATIVE-UI.md#wa-p1-004)

### P2 — Connections and webhooks

- [WA-P2-001: Verify official Meta contract and implement adapter](P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-001)
- [WA-P2-002: Implement protected connection and number setup](P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-002)
- [WA-P2-003: Implement authenticated durable webhook intake](P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-003)
- [WA-P2-004: Qualify provider event recovery and operator diagnostics](P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-004)

### P3 — Audiences and templates

- [WA-P3-001: Implement company-scoped contacts and ERPNext projections](P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-001)
- [WA-P3-002: Implement resumable CSV, consent and suppression](P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-002)
- [WA-P3-003: Implement explainable segments and bounded audience queries](P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-003)
- [WA-P3-004: Implement template lifecycle and private media validation](P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-004)

### P4 — Campaigns and dispatch

- [WA-P4-001: Implement durable sender, reservations and recovery](P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-001)
- [WA-P4-002: Implement campaign snapshots, tests and manager approval](P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-002)
- [WA-P4-003: Implement campaign scheduling and lifecycle controls](P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-003)
- [WA-P4-004: Complete campaign results and end-to-end dispatch qualification](P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-004)

### P5 — Inbox

- [WA-P5-001: Project verified inbound messages into conversations](P5-INBOX.md#wa-p5-001)
- [WA-P5-002: Build authorised native Desk inbox and assignment](P5-INBOX.md#wa-p5-002)
- [WA-P5-003: Implement replies, notes, read state and private attachments](P5-INBOX.md#wa-p5-003)
- [WA-P5-004: Implement human handover and privacy-safe realtime](P5-INBOX.md#wa-p5-004)

### P6 — Automations

- [WA-P6-001: Implement native step editor and immutable publication](P6-AUTOMATIONS.md#wa-p6-001)
- [WA-P6-002: Implement controlled inbound and ERPNext trigger intake](P6-AUTOMATIONS.md#wa-p6-002)
- [WA-P6-003: Implement durable step execution, waits and recovery](P6-AUTOMATIONS.md#wa-p6-003)
- [WA-P6-004: Complete simulation, journey preview and automation qualification](P6-AUTOMATIONS.md#wa-p6-004)

### P7 — Reporting and release

- [WA-P7-001: Implement reconciled reports and dated cost estimates](P7-REPORTING-AND-RELEASE.md#wa-p7-001)
- [WA-P7-002: Implement operational readiness, retention and runbooks](P7-REPORTING-AND-RELEASE.md#wa-p7-002)
- [WA-P7-003: Run capacity, security, migration and restore qualification](P7-REPORTING-AND-RELEASE.md#wa-p7-003)
- [WA-P7-004: Complete authorised pilot and production release decision](P7-REPORTING-AND-RELEASE.md#wa-p7-004)

## Shared completion rules

Apply these once to every task; task documents add feature-specific implementation, failures and evidence:

1. Follow the task's Read first links and the [source register](../REFERENCES.md). Use the [implementation rules](../IMPLEMENTATION_RULES.md) for shared engineering requirements.
2. Run the linked [acceptance scenarios](../TESTING_AND_ACCEPTANCE.md), including relevant negative-path, permission and recovery checks. Use the established harness; incomplete required checks leave the task open.
3. Capture applicable UI comparisons using the [design checklist](../UI_DESIGN_SYSTEM.md#visual-acceptance-checklist) and operational evidence required by the task.
4. Update changed owning specifications and append actual results using the [progress evidence format](../PROGRESS.md#implementation-evidence-format).
5. Check only the task's checkbox in its phase file after its required checks pass. Partial offline success with missing required live evidence stays open; record In progress or Blocked in the evidence entry.

Phase readiness is determined by the [implementation plan gates](../IMPLEMENTATION_PLAN.md), not by duplicate phase checkboxes. [Traceability](../TRACEABILITY.md) maps requirement coverage without owning definitions or status.
