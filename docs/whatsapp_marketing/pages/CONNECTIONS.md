# Connections

Page contract: **WA-UI-CONNECTIONS**. Sidebar label: **Connections**. [Navigation index](README.md).

## Purpose and implementation

The Connections sidebar destination is a small native Desk Page that shows a permission-safe health summary. System Managers open the native WA Connection List/Form from it; Marketing Managers never receive generic credential-record access. WA Sending Number and WA Template remain linked list/form records with their existing role permissions.

**Users:** System Manager configures credentials; Marketing Manager may read safe health and synchronise templates; no other role sees secret fields.

## Layout and fields

- Summary columns: connection name, status, last validation, last Meta GET verification, last signed POST, number/template counts, pending/failed event counts and safe error code. The summary API never returns credentials, app/WABA IDs, provider payloads, operation arguments, or generic technical diagnostics.
- System Manager opens the standard Connection List/Form from the page. Native form tabs: Account (app/WABA IDs, explicit API version), Credentials (Password controls), Numbers, Webhook, Diagnostics.
- Number details: provider ID, display name/phone, readiness, available quality/limits, configured local rate and default team.
- Webhook panel: public integration URL, verification instructions, GET challenge timestamp and signed POST timestamp; distinguish configuration verification from actual event delivery. System Manager can open **Check Webhook** for bounded event-state counts and safe readiness diagnostics.

## Filters and data behaviour

Filters: status and last validation. Show credential-present indicators rather than token values. Readiness indicators are text plus native colour, not an optimistic Connected badge based solely on saved fields.

## Actions and prerequisites

Validate Connection, Sync Numbers, Sync Templates, Reconnect and Disable use persisted `WA Operation` commands and native progress dialogs. Marketing Managers may sync templates from the safe summary page; they cannot open a connection document. Credential edits clear validation. Disable immediately blocks new sends without discarding authenticated callbacks. Reconnect requires fresh provider reads. Test-send input remains disabled until P4's shared outbox and dispatch policy are complete; validation never produces a success-only send.

## UI states, access and responsive behaviour

No connection: Create Connection for System Manager, otherwise contact-administrator guidance. Pending operations persist across reload. Provider failures retain safe codes/correlation IDs; no header/token dumps. Forms stack normally; long IDs/URLs wrap and have labelled copy actions.

## Interfaces and records

WA Connection, WA Sending Number, WA Operation, WA Audit Event; `connections.*`.

## Implementation and acceptance

Tasks: [WA-P2-001, WA-P2-002, WA-P2-003, WA-P2-004](../tasks/P2-CONNECTIONS-AND-WEBHOOKS.md). Scenarios: [WA-A05, WA-A06, WA-A13, WA-A14](../TESTING_AND_ACCEPTANCE.md).

- Saved credentials alone never show Ready.
- Rotating secrets invalidates readiness; denied users cannot fetch credentials through direct API/list/export.
- Connection setup acceptance covers secret protection/rotation, company-scoped access, safe health projection, persisted operation progress and provider-backed validation/catalog sync. Signed event delivery belongs to [WA-P2-003](../tasks/P2-CONNECTIONS-AND-WEBHOOKS.md#wa-p2-003); an authorised outbound test message remains gated on the shared P4 outbox and is not claimed here.
