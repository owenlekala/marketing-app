# P2: Connections and webhooks

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P2-001

- [x] **Verify official Meta contract and implement adapter**

**Depends on:** `WA-P1-004`

**Requirements:** `WA-R03`, `WA-R06`, `WA-R09`. **Acceptance:** `WA-A05`, `WA-A06`, `WA-A14`.

**Read first:** [References](../REFERENCES.md), [Api Contracts](../API_CONTRACTS.md), [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md).

**Implementation and boundaries:** Obtain current official API version/permissions/template/media/webhook documentation and record review date. Define typed provider adapter operations for validation, numbers, template management, submission and media retrieval. Pin a supported configured version and add synthetic contract fixtures with classified safe/uncertain outcomes; never install the archived reference SDK.

**Failure cases and verification:** Cover expired permission, unsupported version, throttling, 5xx uncertainty, wrong WABA and unsupported media. Developer docs unavailable means no unsupported live claim.

**Completion evidence:** Record source references, adapter contract tests, selected version and fixture redaction review.

**Completion evidence (27 October 2026):** Reviewed Meta's maintained Cloud API Postman collection and the current Graph API version reference; `v26.0` is explicitly pinned and no fallback or unversioned endpoint is allowed. The canonical developer changelog returned HTTP 429 during direct retrieval, so [References](../REFERENCES.md#official-messaging-and-privacy-references) records that release-time revalidation is still required. Added a clean-architecture provider adapter with bounded HTTPS transport, typed number/template/message/media results, and fail-closed handling for unsupported version, wrong WABA, expired credentials, throttling, rejection, 5xx and ambiguous submission. Tests use synthetic responses and verify provider bodies and tokens do not escape diagnostics. No live credentials or outbound provider calls were used; runtime permission and delivery qualification remain pending P2-002/P2-003.

## WA-P2-002

- [ ] **Implement protected connection and number setup**

**Depends on:** `WA-P2-001`

**Requirements:** `WA-R03`. **Acceptance:** `WA-A05`, `WA-A14`.

**Read first:** [Connections](../pages/CONNECTIONS.md), [Data Model](../DATA_MODEL.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Implement connection forms, protected credential storage, validation/sync operations, number identity/rate/team configuration, diagnostics and disable/reconnect. Use persisted WA Operation results. Build explicit test command input validation; provider dispatch uses the shared outbox once P4 is ready, so no direct success-only test sender is introduced.

**Failure cases and verification:** Test secret rotation/readiness invalidation, safe diagnostics, stale commands, duplicate sync and unauthorised credential access. Qualify operation-specific target/result permissions before enabling producers, including permitted Manager template-sync progress without granting credential or generic technical-record access. Recheck revocation and private result-file access through the [progress contract](../API_CONTRACTS.md#operation-progress-foundation). Keep live sending disabled.

**Completion evidence:** Run fake-provider integration checks and connection UI evidence; record that actual outbound test readiness depends on the complete P3/P4 eligibility/outbox slice.

## WA-P2-003

- [ ] **Implement authenticated durable webhook intake**

**Depends on:** `WA-P2-002`

**Requirements:** `WA-R09`. **Acceptance:** `WA-A06`, `WA-A14`.

**Read first:** [Webhooks And Delivery](../flows/WEBHOOKS_AND_DELIVERY.md), [Api Contracts](../API_CONTRACTS.md), [Data Model](../DATA_MODEL.md).

**Implementation and boundaries:** Implement exact GET challenge and raw-body POST HMAC boundary with route/size/WABA/number validation. Commit bounded receipts before acknowledgement; deduplicate envelopes/elements and persist Message Events for correlation. Enqueue after commit and expose safe failed-event diagnostics/recovery.

**Failure cases and verification:** Inject persistence failure before 200, changed raw bytes, duplicate/mixed elements and status-before-acceptance. Unsupported types must not discard valid siblings.

**Completion evidence:** Record signature/replay/rollback/acknowledgement tests; an authorised signed callback may verify intake without any campaign launch.

## WA-P2-004

- [ ] **Qualify provider event recovery and operator diagnostics**

**Depends on:** `WA-P2-003`

**Requirements:** `WA-R03`, `WA-R09`, `WA-R15`. **Acceptance:** `WA-A05`, `WA-A06`, `WA-A13`.

**Read first:** [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md), [Operations And Release](../OPERATIONS_AND_RELEASE.md), [Connections](../pages/CONNECTIONS.md).

**Implementation and boundaries:** Implement receipt/source-operation recovery scans, bounded event retries, correlation queues and connection-health projection. Wire manager/system diagnostics to native views. Establish the signed-intake/contract gate; defer real send evidence until the complete shared outbox and audience policy are available.

**Failure cases and verification:** Stop Redis/worker between commit and enqueue, replay poison/unknown events and check redacted logs. No silent loss and no arbitrary payload exposure.

**Completion evidence:** Attach recovery tests, callback evidence if available and clear prerequisites for future authorised test submission.
