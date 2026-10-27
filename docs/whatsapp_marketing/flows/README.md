# Workflow index

Each flow identifies trigger, prerequisites, durable writes, asynchronous boundaries, failures and final outcomes. Mermaid is source documentation; no application runtime depends on a diagram library.

- [Connection and onboarding](CONNECTION_AND_ONBOARDING.md): administrator setup to validated test readiness.
- [Audience and consent](AUDIENCE_AND_CONSENT.md): projection/import, evidence and suppression.
- [Campaign approval and dispatch](CAMPAIGN_APPROVAL_AND_DISPATCH.md): snapshot, manager decision and controlled sending.
- [Webhooks and delivery](WEBHOOKS_AND_DELIVERY.md): authenticated receipt, replay and status reconciliation.
- [Inbox and handover](INBOX_AND_HANDOVER.md): replies, service windows, assignments and human control.
- [Automation execution](AUTOMATION_EXECUTION.md): allowed definitions, publication, triggers, waits and recovery.

State labels must match [data model](../DATA_MODEL.md). Provider retry/uncertainty policy is owned by [reliability](../MESSAGING_AND_RELIABILITY.md), not redefined in diagrams.
