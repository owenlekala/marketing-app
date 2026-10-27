# Connections

Page contract: **WA-UI-CONNECTIONS**. Sidebar label: **Connections**. [Navigation index](README.md).

## Purpose and implementation

The Connections sidebar destination is a small native Desk Page that shows a permission-safe health summary. System Managers open the native WA Connection List/Form from it; Marketing Managers never receive generic credential-record access. WA Sending Number and WA Template remain linked list/form records with their existing role permissions.

**Users:** System Manager configures credentials; Marketing Manager may read safe health and synchronise templates; no other role sees secret fields.

## Layout and fields

- Summary columns: connection name, status, last validation, last webhook, number/template counts and safe error code. The summary API never returns credentials, app/WABA IDs, provider payloads, or generic technical diagnostics.
- System Manager opens the standard Connection List/Form from the page. Native form tabs: Account (app/WABA IDs, explicit API version), Credentials (Password controls), Numbers, Webhook, Diagnostics.
- Form tabs: Account (app/WABA IDs, explicit API version), Credentials (Password controls), Numbers, Webhook, Diagnostics.
- Number details: provider ID, display name/phone, readiness, available quality/limits, configured local rate and default team.
- Webhook panel: public integration URL, verification instructions, last valid POST timestamp; distinguish GET verification from actual event delivery.

## Filters and data behaviour

Filters: status and last validation. Show credential-present indicators rather than token values. Readiness indicators are text plus native colour, not an optimistic Connected badge based solely on saved fields.

## Actions and prerequisites

Validate Connection, Sync Numbers, Sync Templates, Reconnect and Disable use persisted `WA Operation` commands and native progress dialogs. Marketing Managers may sync templates from the safe summary page; they cannot open a connection document. Credential edits clear validation. Disable immediately blocks new sends without discarding authenticated callbacks. Reconnect requires fresh provider reads. Test-send input remains disabled until P4's shared outbox and dispatch policy are complete; validation never produces a success-only send.

## UI states, access and responsive behaviour

No connection: Create Connection for System Manager, otherwise contact-administrator guidance. Pending operations persist across reload. Provider failures retain safe codes/correlation IDs; no header/token dumps. Forms stack normally; long IDs/URLs wrap and have labelled copy actions.

## Interfaces and records

WA Connection, WA Sending Number, WA Operation, WA Audit Event; `connections.*`.

## Implementation and acceptance

Tasks: [WA-P2-001, WA-P2-002, WA-P2-003](../tasks/P2-CONNECTIONS-AND-WEBHOOKS.md). Scenarios: [WA-A05, WA-A06, WA-A14](../TESTING_AND_ACCEPTANCE.md).

- Saved credentials alone never show Ready.
- Rotating secrets invalidates readiness; denied users cannot fetch credentials through direct API/list/export.
- A signed test event and authorised test message are visible with safe diagnostics.
