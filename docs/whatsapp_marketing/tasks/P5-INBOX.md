# P5: Inbox

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P5-001

- [ ] **Project verified inbound messages into conversations**

**Depends on:** `WA-P4-004`

**Requirements:** `WA-R09`, `WA-R10`, `WA-R05`. **Acceptance:** `WA-A06`, `WA-A09`, `WA-A10`.

**Read first:** [Webhooks And Delivery](../flows/WEBHOOKS_AND_DELIVERY.md), [Data Model](../DATA_MODEL.md), [Inbox And Handover](../flows/INBOX_AND_HANDOVER.md).

**Implementation and boundaries:** Implement unique company/contact/number conversations, inbound message/callback correlation, trusted timestamp maxima, reopen behaviour, read cursors and opt-out-first processing. Retain unresolved identities/unsupported content safely; resolve sender only through supported provider contract.

**Failure cases and verification:** Replay events, delay old inbound messages, use future timestamps, mixed media and status-before-acceptance. Duplicate messages cannot extend a window or trigger duplicate work.

**Completion evidence:** Record projection/status/time tests with controlled clock and safe event diagnostics.

## WA-P5-002

- [ ] **Build authorised native Desk inbox and assignment**

**Depends on:** `WA-P5-001`

**Requirements:** `WA-R10`, `WA-R02`, `WA-R13`. **Acceptance:** `WA-A02`, `WA-A09`.

**Read first:** [Inbox](../pages/INBOX.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Build wa-inbox inside native Page shell with paginated three-panel layout, allowed search/filtering, team/assignment controls and minimal source/contact context. Implement server list/document/download scope and stale-assignment protection. Narrow layout shows one panel with preserved navigation state.

**Failure cases and verification:** Test Agent without team, cross-team direct IDs, reassignment while viewing, empty/loading/error and lost network. No unrestricted conversation list or secondary app shell.

**Completion evidence:** Capture two-agent access tests and light/dark/390px screenshots against native ERPNext shell.

## WA-P5-003

- [ ] **Implement replies, notes, read state and private attachments**

**Depends on:** `WA-P5-002`

**Requirements:** `WA-R10`, `WA-R13`. **Acceptance:** `WA-A09`, `WA-A10`, `WA-A14`.

**Read first:** [Api Contracts](../API_CONTRACTS.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md), [Inbox](../pages/INBOX.md).

**Implementation and boundaries:** Implement idempotent Text/Media/Template replies through shared outbox, composer capability flags, worker-time window validation, private attachment retrieval, internal notes and per-user read commands. Resolve recipients from conversation; agent actions never accept arbitrary phone/token payloads.

**Failure cases and verification:** Expire a reply between enqueue/submission, repeat clicks/requests, change attachment ownership, and inject XSS/unsupported file content. Internal notes must never call Meta.

**Completion evidence:** Record reply/window/private-file tests and actual pending/unknown/error UI behaviour.

## WA-P5-004

- [ ] **Implement human handover and privacy-safe realtime**

**Depends on:** `WA-P5-003`

**Requirements:** `WA-R10`, `WA-R11`, `WA-R13`. **Acceptance:** `WA-A09`, `WA-A10`, `WA-A13`.

**Read first:** [Inbox And Handover](../flows/INBOX_AND_HANDOVER.md), [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md), [Inbox](../pages/INBOX.md).

**Implementation and boundaries:** Coordinate agent reply/handover with automatic submission; explicit Human/Automatic mode controls and resume checks. Publish ID-only invalidations to authorised document/user channels after commit, use refetch and bounded reconnect polling, and clear inaccessible content after reassignment.

**Failure cases and verification:** Race handover against automatic claims, disconnect/reconnect clients and revoke assignment during download. No site-wide message bodies or auto-renewed service window.

**Completion evidence:** Record multi-user/realtime/race tests and end-to-end campaign reply→agent→explicit resume evidence.
