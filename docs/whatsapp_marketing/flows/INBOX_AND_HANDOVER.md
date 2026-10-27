# Inbox and human handover flow

Trigger: inbound message, agent action or an automation handover step. Prerequisites: authorised assignment/team access, resolved conversation identity and healthy connection for outgoing messages.

```mermaid
flowchart TD
  Inbound[Verified inbound message] --> Conversation[Open or reopen conversation]
  Conversation --> OptOut{Opt-out?}
  OptOut -->|Yes| Suppression[Apply company marketing suppression first]
  OptOut -->|No| Mode{Human mode?}
  Suppression --> Agent[Route permitted support to human]
  Mode -->|Yes| Agent
  Mode -->|No| Automation[Evaluate eligible automation]
  Automation --> Handover[Handover or agent reply]
  Agent --> Compose[Compose reply]
  Compose --> Window{Window still open at send?}
  Window -->|Yes| Queue[Queue permitted text/media or template]
  Window -->|No| Template[Require approved template]
  Template --> Queue
  Queue --> Human[Atomically set Human mode]
  Handover --> Human
  Human --> Resume{Explicit Resume Automation?}
  Resume -->|Yes| Recheck[Recheck run, consent, window and readiness]
  Recheck --> Automation
```

Agent reply and automatic sending compete through conversation coordination: a recorded handover blocks not-yet-submitted automatic replies. In-flight provider requests cannot be recalled. Resume is explicit and does not refresh the customer service window.

Lists/messages use cursor pagination and permission-scoped invalidations. Reassignment immediately blocks subsequent reads/downloads by a former agent; notifications carry IDs rather than body text. Per-user read cursors do not change another agent's read history.

Validate window at compose query and worker submission. A queued free-form reply that becomes stale fails `WINDOW_CLOSED`; retain draft/content context and offer template selection without automatically sending anything. Retrying a browser command reuses its request ID/message.

Resolve closes operational work; new inbound reopens. Adding an internal note never sends a WhatsApp message. Retention and attachment validation can leave safe unavailable-media placeholders.

Outcome: controlled replies, private team collaboration and explicit automated/human ownership. See [Inbox page](../pages/INBOX.md), [P5 tasks](../tasks/P5-INBOX.md), [WA-A09/WA-A10](../TESTING_AND_ACCEPTANCE.md).
