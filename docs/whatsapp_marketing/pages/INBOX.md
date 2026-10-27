# Inbox

Page contract: **WA-UI-INBOX**. Sidebar label: **Inbox**. [Navigation index](README.md).

## Purpose and implementation

Custom Page wa-inbox inside native Desk shell; native header, filters, buttons, controls and dialogs.

**Users:** WhatsApp Agent within assigned/team scope; Manager across authorised company. No access for ordinary User/Analyst without agent permissions.

## Layout and fields

- Left panel: paginated conversation list, search, Mine/Team/Unassigned filters, Open/Resolved, unread and sender filters.
- Centre panel: paginated chronological messages with explicit direction/time/status, supported private attachments, reply context and labelled composer.
- Right panel: minimal contact profile, authorised ERPNext links, consent/suppression, campaign context, team/assignee and automation mode.
- Internal notes are visibly distinct from outbound replies. Delivery indicators describe evidence, never a browser assumption.
- Composer shows customer service window expiry and Text/Media/Template capabilities from the server.

## Filters and data behaviour

Conversation list sorts by last_message_at/name. Load older messages using cursor; preserve scroll and selection on new invalidations. Exact campaign context uses provider reply IDs. Search only permitted records and minimum indexed fields; do not full-scan message bodies in v1.

## Actions and prerequisites

Assign/Reassign validates target team/role. Send Reply is idempotent, queues work and atomically moves mode to Human. Template picker appears when free-form capability is unavailable; no automatic replacement. Resolve, Add Note, Mark Read and Resume Automation call scoped APIs. File retrieval rechecks current access.

## UI states, access and responsive behaviour

Empty selection asks the user to choose a conversation; an Agent with no team sees their assignments only. Invalidated access clears content and selection. Realtime loss shows reconnecting and falls back to bounded polling/refetch. At 390px show one panel at a time with back navigation. Keep input focus and meaningful screen-reader labels.

## Interfaces and records

WA Conversation, WA Conversation Read/Note, WA Message, private File; `inbox.*`, `media.download`.

## Implementation and acceptance

Tasks: [WA-P5-001, WA-P5-002, WA-P5-003, WA-P5-004](../tasks/P5-INBOX.md). Scenarios: [WA-A09, WA-A10, WA-A14](../TESTING_AND_ACCEPTANCE.md).

- Two agents cannot view each other’s private assignments outside team scope.
- A window expiring between compose and submit returns WINDOW_CLOSED without sending free-form text.
- Reassignment, duplicate button clicks, reconnect and inbound opt-out preserve privacy and message correctness.
