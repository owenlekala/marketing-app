# Overview

Page contract: **WA-UI-OVERVIEW**. Sidebar label: **Overview**. [Navigation index](README.md).

## Purpose and implementation

Native Workspace named WhatsApp Marketing; home destination in the owned Sidebar.

**Users:** Marketing User/Manager see authorised metrics; Analyst sees aggregate-only content; Agent uses Inbox shortcut and assigned-work counts.

## Layout and fields

- Setup/readiness panel: connection, webhook, sender, worker, policy and pilot checks with permitted remediation links.
- Number Cards: eligible marketing contacts, active campaigns, delivered messages, exact replies and unassigned conversations. Scope all counts by allowed company and date.
- Two-column chart area: daily delivered/failed outcomes and recent campaign dispatch outcomes. Show empty series honestly; do not seed invented engagement.
- Quick lists: upcoming campaigns, paused/failed campaigns, unresolved Unknown messages and assigned/open conversations.
- Native shortcuts: Create Campaign, Import Contacts, Inbox and Automations; hide unauthorised actions.

## Filters and data behaviour

- Company is the configured marketing company, not an unrestricted selector. Default period is last 30 days; apply the same period to cards/charts and explain timestamp basis.
- A count opens the native destination with matching filters. Delivered charts use delivered_at; scheduled lists use scheduled_at.
- Operational alert cards remain visible to authorised managers when sending is disabled; the workspace itself is not blocked by incomplete setup.

## Actions and prerequisites

Cards call permission-scoped metric/query services. Do not aggregate unrestricted tables in a public card method. Setup actions navigate to Connections/Settings; no implicit test send or live enable button on a metric.

## UI states, access and responsive behaviour

Initial site shows setup checklist and zero/empty business activity. Failed metric loading offers query retry, never a zero disguised as success. Analyst receives no raw message drill-down. Native widgets wrap at narrow widths and inherit both themes.

## Interfaces and records

WA Campaign, WA Message, WA Contact, WA Conversation, WA Settings; `reports.summary`, `connections.check_webhook`.

## Implementation and acceptance

Tasks: [WA-P1-002, WA-P1-004](../tasks/P1-APP-AND-NATIVE-UI.md). Scenarios: [WA-A02, WA-A03, WA-A12](../TESTING_AND_ACCEPTANCE.md).

- Confirm every card equals its filtered report for the same user/date scope.
- Verify disabled sending and absent connection produce actionable native empty states.
- Compare workspace spacing, chart controls and shortcuts against ERPNext CRM in both themes.
