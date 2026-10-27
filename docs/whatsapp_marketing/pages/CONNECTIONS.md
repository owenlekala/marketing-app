# Connections

Page contract: **WA-UI-CONNECTIONS**. Sidebar label: **Connections**. [Navigation index](README.md).

## Purpose and implementation

Native WA Connection List/Form with linked WA Sending Number records; no custom dashboard application.

**Users:** System Manager configures credentials; Marketing Manager may read safe health and synchronise templates; no other role sees secret fields.

## Layout and fields

- List columns: connection name, company, status, last validation, last webhook and safe error code.
- Form tabs: Account (app/WABA IDs, explicit API version), Credentials (Password controls), Numbers, Webhook, Diagnostics.
- Number details: provider ID, display name/phone, readiness, available quality/limits, configured local rate and default team.
- Webhook panel: public integration URL, verification instructions, last valid POST timestamp; distinguish GET verification from actual event delivery.

## Filters and data behaviour

Filters: status and last validation. Show credential-present indicators rather than token values. Readiness indicators are text plus native colour, not an optimistic Connected badge based solely on saved fields.

## Actions and prerequisites

Validate Credentials, Sync Numbers, Sync Templates, Check Webhook, Send Test and Disable/Enable use the connection APIs. Test dialog selects a permitted contact/template, explains one outbound test and requires explicit action. Credential edits clear validation. Disable stops new sends without discarding callbacks.

## UI states, access and responsive behaviour

No connection: Create Connection for System Manager, otherwise contact-administrator guidance. Pending operations persist across reload. Provider failures retain safe codes/correlation IDs; no header/token dumps. Forms stack normally; long IDs/URLs wrap and have labelled copy actions.

## Interfaces and records

WA Connection, WA Sending Number, WA Operation, WA Audit Event; `connections.*`.

## Implementation and acceptance

Tasks: [WA-P2-001, WA-P2-002, WA-P2-003](../tasks/P2-CONNECTIONS-AND-WEBHOOKS.md). Scenarios: [WA-A05, WA-A06, WA-A14](../TESTING_AND_ACCEPTANCE.md).

- Saved credentials alone never show Ready.
- Rotating secrets invalidates readiness; denied users cannot fetch credentials through direct API/list/export.
- A signed test event and authorised test message are visible with safe diagnostics.
