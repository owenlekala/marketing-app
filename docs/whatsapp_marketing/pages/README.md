# Page and navigation index

Owner: WA-R02. Build one native Sidebar named **WhatsApp Marketing** in the owned TAG Marketing Dock/app. Resolve routes through the installed framework; names below identify documents/destinations, not hardcoded legacy URLs.

- **Overview** — [Overview](OVERVIEW.md). Native Workspace named WhatsApp Marketing; home destination in the owned Sidebar.
- **Connections** — [Connections](CONNECTIONS.md). Native WA Connection List/Form with linked WA Sending Number records; no custom dashboard application.
- **Contacts** — [Contacts and imports](CONTACTS_AND_IMPORTS.md). Native WA Contact List/Form; private CSV import handled through WA Import Batch form and native mapping/confirmation dialogs.
- **Audience Segments** — [Audience segments](AUDIENCE_SEGMENTS.md). Native WA Audience Segment List/Form with native filter controls and paginated preview.
- **Templates** — [Templates](TEMPLATES.md). Native WA Template List/Form with a scoped rendered message preview.
- **Campaigns** — [Campaigns](CAMPAIGNS.md). Native WA Campaign List/Form with linked read-only snapshot/recipient records.
- **Inbox** — [Inbox](INBOX.md). Custom Page wa-inbox inside native Desk shell; native header, filters, buttons, controls and dialogs.
- **Automations** — [Automations](AUTOMATIONS.md). Native WA Automation List/Form with ordered-step controls and read-only journey preview; no drag-and-drop app.
- **Reports** — [Reports](REPORTS.md). Sidebar section linking native Script Reports; no separate reporting SPA.
- **Settings** — [Settings](SETTINGS.md). Native Single WA Settings form; restricted technical DocTypes accessible through manager diagnostics, not extra public sidebar entries.

Reports is a Sidebar section containing named Script Report links. Connections also exposes owned sending-number records. Templates belong to a connection. Technical recipients, attempts, events, outbox, operations and audits are accessible only through authorised drill-down/diagnostics; do not crowd the primary sidebar.

The Overview workspace is the home destination for Marketing User/Manager/Analyst according to capability; Agent-only users open Inbox. Missing role visibility never substitutes for endpoint/document checks. Native document titles and Page names must not collide with ERPNext CRM/Campaign routes.

## Native sidebar hierarchy

Use the installed HRMS Recruitment and ERPNext CRM Sidebar pattern: an icon on each top-level row, indented child links and native collapsible section controls. Overview remains the first standalone row. Start sections closed; let the framework preserve each user's expansion state and remove inaccessible links and empty groups.

- Overview (`house`): the workspace home.
- Audiences (`users`): Contacts, Audience Segments.
- Messaging (`megaphone`): Campaigns, Templates.
- Conversations (`message-circle`): Inbox.
- Automation (`workflow`): Automations.
- Reports (`chart-column`): the named Script Reports defined in [Reports](REPORTS.md).
- Setup (`settings`): Connections, Rate Cards, Settings. Rate Cards belong to the [cost-report configuration](REPORTS.md).

Each destination appears once. Imports remain a Contacts action; sending numbers remain linked from Connections. Do not add technical processing records as extra menu entries. Use standard Sidebar Section Break records with `indent=1`, `collapsible=1`, `child=0`; contained links use `child=1`, without repeated icons. Keep the native Dock and the TAG Marketing Apps-screen logo; this hierarchy does not introduce custom navigation JavaScript or CSS.

## Shared page contract

Every page inherits the [design system](../UI_DESIGN_SYSTEM.md), [field definitions](../DATA_MODEL.md), [wire contracts](../API_CONTRACTS.md) and [permission policy](../PERMISSIONS_AND_PRIVACY.md). Individual page files define layout, visible capabilities, actions and feature-specific UI states; they do not redefine those shared contracts.

For every implemented page, follow the design system's visual acceptance checklist, including ERPNext comparisons in light/dark themes and narrow layouts. An empty shell or mock data is not completion. End-to-end orchestration belongs to [flows](../flows/README.md); execution work belongs to [tasks](../tasks/README.md).
