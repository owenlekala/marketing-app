# Requirement traceability

The authoritative register is [product requirements](PRODUCT_REQUIREMENTS.md). Each item below links owning specs, implementation work and acceptance scenarios. All tasks remain unchecked until recorded evidence exists. Coverage is specification coverage, not implemented status.

## WA-R01 — Foundation

**Owning specification:** [Framework And Setup](FRAMEWORK_AND_SETUP.md), [Architecture](ARCHITECTURE.md).

**Implementation:** [WA-P0-001](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-001), [WA-P0-002](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-002), [WA-P0-003](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-003), [WA-P1-001](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-001), [WA-P7-003](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-003).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A15](TESTING_AND_ACCEPTANCE.md#wa-a15--upgrade-and-restore), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests), [WA-A18](TESTING_AND_ACCEPTANCE.md#wa-a18--documentation-consistency).

## WA-R02 — Native UI

**Owning specification:** [Ui Design System](UI_DESIGN_SYSTEM.md), [Readme](pages/README.md).

**Implementation:** [WA-P1-002](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-002), [WA-P1-003](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-003), [WA-P1-004](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-004), [WA-P5-002](tasks/P5-INBOX.md#wa-p5-002), [WA-P6-001](tasks/P6-AUTOMATIONS.md#wa-p6-001).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media).

## WA-R03 — Connections

**Owning specification:** [Api Contracts](API_CONTRACTS.md), [Connections](pages/CONNECTIONS.md).

**Implementation:** [WA-P2-001](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-001), [WA-P2-002](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-002), [WA-P2-004](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-004).

**Acceptance:** [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media).

## WA-R04 — Audiences

**Owning specification:** [Erpnext Integration](ERPNext_INTEGRATION.md), [Audience Segments](pages/AUDIENCE_SEGMENTS.md).

**Implementation:** [WA-P3-001](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-001), [WA-P3-002](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-002), [WA-P3-003](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-003).

**Acceptance:** [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests).

## WA-R05 — Consent

**Owning specification:** [Permissions And Privacy](PERMISSIONS_AND_PRIVACY.md), [Audience And Consent](flows/AUDIENCE_AND_CONSENT.md).

**Implementation:** [WA-P3-002](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-002), [WA-P3-003](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-003), [WA-P4-001](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-001), [WA-P4-002](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-002), [WA-P5-001](tasks/P5-INBOX.md#wa-p5-001), [WA-P6-002](tasks/P6-AUTOMATIONS.md#wa-p6-002).

**Acceptance:** [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests).

## WA-R06 — Templates

**Owning specification:** [Templates](pages/TEMPLATES.md), [Api Contracts](API_CONTRACTS.md).

**Implementation:** [WA-P2-001](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-001), [WA-P3-004](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-004), [WA-P4-002](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-002).

**Acceptance:** [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media).

## WA-R07 — Campaigns

**Owning specification:** [Campaigns](pages/CAMPAIGNS.md), [Campaign Approval And Dispatch](flows/CAMPAIGN_APPROVAL_AND_DISPATCH.md).

**Implementation:** [WA-P4-002](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-002), [WA-P4-003](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-003), [WA-P4-004](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-004).

**Acceptance:** [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls).

## WA-R08 — Dispatch

**Owning specification:** [Messaging And Reliability](MESSAGING_AND_RELIABILITY.md).

**Implementation:** [WA-P4-001](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-001), [WA-P4-004](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-004), [WA-P6-003](tasks/P6-AUTOMATIONS.md#wa-p6-003).

**Acceptance:** [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness).

## WA-R09 — Inbound

**Owning specification:** [Webhooks And Delivery](flows/WEBHOOKS_AND_DELIVERY.md), [Api Contracts](API_CONTRACTS.md).

**Implementation:** [WA-P2-001](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-001), [WA-P2-003](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-003), [WA-P2-004](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-004), [WA-P5-001](tasks/P5-INBOX.md#wa-p5-001).

**Acceptance:** [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media).

## WA-R10 — Inbox

**Owning specification:** [Inbox](pages/INBOX.md), [Inbox And Handover](flows/INBOX_AND_HANDOVER.md).

**Implementation:** [WA-P5-001](tasks/P5-INBOX.md#wa-p5-001), [WA-P5-002](tasks/P5-INBOX.md#wa-p5-002), [WA-P5-003](tasks/P5-INBOX.md#wa-p5-003), [WA-P5-004](tasks/P5-INBOX.md#wa-p5-004), [WA-P6-003](tasks/P6-AUTOMATIONS.md#wa-p6-003).

**Acceptance:** [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media).

## WA-R11 — Automations

**Owning specification:** [Automation Execution](flows/AUTOMATION_EXECUTION.md), [Automations](pages/AUTOMATIONS.md).

**Implementation:** [WA-P5-004](tasks/P5-INBOX.md#wa-p5-004), [WA-P6-001](tasks/P6-AUTOMATIONS.md#wa-p6-001), [WA-P6-002](tasks/P6-AUTOMATIONS.md#wa-p6-002), [WA-P6-003](tasks/P6-AUTOMATIONS.md#wa-p6-003), [WA-P6-004](tasks/P6-AUTOMATIONS.md#wa-p6-004).

**Acceptance:** [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls).

## WA-R12 — CRM events

**Owning specification:** [Erpnext Integration](ERPNext_INTEGRATION.md).

**Implementation:** [WA-P3-001](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-001), [WA-P6-002](tasks/P6-AUTOMATIONS.md#wa-p6-002), [WA-P6-004](tasks/P6-AUTOMATIONS.md#wa-p6-004).

**Acceptance:** [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events).

## WA-R13 — Access/privacy

**Owning specification:** [Permissions And Privacy](PERMISSIONS_AND_PRIVACY.md).

**Implementation:** [WA-P1-001](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-001), [WA-P1-003](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-003), [WA-P3-002](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-002), [WA-P3-004](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-004), [WA-P5-002](tasks/P5-INBOX.md#wa-p5-002), [WA-P5-003](tasks/P5-INBOX.md#wa-p5-003), [WA-P5-004](tasks/P5-INBOX.md#wa-p5-004), [WA-P7-001](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-001), [WA-P7-002](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-002).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests).

## WA-R14 — Reporting

**Owning specification:** [Reports](pages/REPORTS.md).

**Implementation:** [WA-P4-004](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-004), [WA-P7-001](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-001).

**Acceptance:** [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness).

## WA-R15 — Operations

**Owning specification:** [Operations And Release](OPERATIONS_AND_RELEASE.md).

**Implementation:** [WA-P0-002](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-002), [WA-P2-004](tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-004), [WA-P4-001](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-001), [WA-P4-003](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-003), [WA-P7-002](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-002), [WA-P7-004](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-004).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A06](TESTING_AND_ACCEPTANCE.md#wa-a06--webhook-authentication-and-replay), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A15](TESTING_AND_ACCEPTANCE.md#wa-a15--upgrade-and-restore), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests), [WA-A18](TESTING_AND_ACCEPTANCE.md#wa-a18--documentation-consistency).

## WA-R16 — Capacity

**Owning specification:** [Messaging And Reliability](MESSAGING_AND_RELIABILITY.md), [Testing And Acceptance](TESTING_AND_ACCEPTANCE.md).

**Implementation:** [WA-P3-003](tasks/P3-AUDIENCES-AND-TEMPLATES.md#wa-p3-003), [WA-P4-001](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-001), [WA-P7-003](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-003).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A04](TESTING_AND_ACCEPTANCE.md#wa-a04--consent-imports-and-suppression), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A15](TESTING_AND_ACCEPTANCE.md#wa-a15--upgrade-and-restore), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests), [WA-A18](TESTING_AND_ACCEPTANCE.md#wa-a18--documentation-consistency).

## WA-R17 — Quality

**Owning specification:** [Testing And Acceptance](TESTING_AND_ACCEPTANCE.md).

**Implementation:** [WA-P0-004](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-004), [WA-P1-004](tasks/P1-APP-AND-NATIVE-UI.md#wa-p1-004), [WA-P4-004](tasks/P4-CAMPAIGNS-AND-DISPATCH.md#wa-p4-004), [WA-P6-004](tasks/P6-AUTOMATIONS.md#wa-p6-004), [WA-P7-003](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-003), [WA-P7-004](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-004).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A02](TESTING_AND_ACCEPTANCE.md#wa-a02--native-ui), [WA-A03](TESTING_AND_ACCEPTANCE.md#wa-a03--audience-and-source-permissions), [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A14](TESTING_AND_ACCEPTANCE.md#wa-a14--security-and-media), [WA-A15](TESTING_AND_ACCEPTANCE.md#wa-a15--upgrade-and-restore), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests), [WA-A18](TESTING_AND_ACCEPTANCE.md#wa-a18--documentation-consistency).

## WA-R18 — Governance

**Owning specification:** [Implementation Rules](IMPLEMENTATION_RULES.md), [Readme](decisions/README.md).

**Implementation:** [WA-P0-001](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-001), [WA-P0-003](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-003), [WA-P0-004](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-004), [WA-P7-004](tasks/P7-REPORTING-AND-RELEASE.md#wa-p7-004).

**Acceptance:** [WA-A01](TESTING_AND_ACCEPTANCE.md#wa-a01--foundation-and-migrations), [WA-A05](TESTING_AND_ACCEPTANCE.md#wa-a05--connections-and-templates), [WA-A07](TESTING_AND_ACCEPTANCE.md#wa-a07--campaign-approval-and-state), [WA-A08](TESTING_AND_ACCEPTANCE.md#wa-a08--dispatch-failure-recovery), [WA-A09](TESTING_AND_ACCEPTANCE.md#wa-a09--inbox-scope-and-realtime), [WA-A10](TESTING_AND_ACCEPTANCE.md#wa-a10--reply-window-and-human-ownership), [WA-A11](TESTING_AND_ACCEPTANCE.md#wa-a11--automations-and-crm-events), [WA-A12](TESTING_AND_ACCEPTANCE.md#wa-a12--reports-and-estimates), [WA-A13](TESTING_AND_ACCEPTANCE.md#wa-a13--operational-controls), [WA-A15](TESTING_AND_ACCEPTANCE.md#wa-a15--upgrade-and-restore), [WA-A16](TESTING_AND_ACCEPTANCE.md#wa-a16--capacity-and-responsiveness), [WA-A17](TESTING_AND_ACCEPTANCE.md#wa-a17--retention-and-subject-requests), [WA-A18](TESTING_AND_ACCEPTANCE.md#wa-a18--documentation-consistency).

## Completion rule

A requirement is Verified only when its linked tasks and applicable acceptance checks have evidence in [progress](PROGRESS.md). If behaviour changes, update this map, the owning spec and affected tests together. Add new IDs for new requirements; do not repurpose an existing ID to conceal a scope change.
