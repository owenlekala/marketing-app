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

- [x] **Implement protected connection and number setup**

**Depends on:** `WA-P2-001`

**Requirements:** `WA-R03`. **Acceptance:** `WA-A05`, `WA-A14`.

**Read first:** [Connections](../pages/CONNECTIONS.md), [Data Model](../DATA_MODEL.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Implement connection forms, protected credential storage, validation/sync operations, number identity/rate/team configuration, diagnostics and disable/reconnect. Use persisted WA Operation results. Build explicit test command input validation; provider dispatch uses the shared outbox once P4 is ready, so no direct success-only test sender is introduced.

**Failure cases and verification:** Test secret rotation/readiness invalidation, safe diagnostics, stale commands, duplicate sync and unauthorised credential access. Qualify operation-specific target/result permissions before enabling producers, including permitted Manager template-sync progress without granting credential or generic technical-record access. Recheck revocation and private result-file access through the [progress contract](../API_CONTRACTS.md#operation-progress-foundation). Keep live sending disabled.

**Completion evidence:** Run fake-provider integration checks and connection UI evidence; record that actual outbound test readiness depends on the complete P3/P4 eligibility/outbox slice.

**Completion evidence (30 October 2026):** `quality.py integration` passed 59 Frappe integration tests and 17 unit tests; `quality.py browser --browser-grep connection` passed 6 cases, 6 expected matrix skips, strict TypeScript and all 3 egress probes; `quality.py lint` passed Ruff, formatting and mypy across 150 sources. Final disposable-site runtime verification passed database/Redis, web/assets, realtime, marketing queue and scheduler probes after a backed-up Redis AOF tail repair. Screenshot evidence and detailed scope limits are recorded in [Progress](../PROGRESS.md#wa-p2-002--protected-connection-and-number-setup). Outbound test-send remains gated by P4; P2-003 signed webhooks remain next.

## WA-P2-003

- [x] **Implement authenticated durable webhook intake**

**Depends on:** `WA-P2-002`

**Requirements:** `WA-R09`. **Acceptance:** `WA-A06`, `WA-A14`.

**Read first:** [Webhooks And Delivery](../flows/WEBHOOKS_AND_DELIVERY.md), [Api Contracts](../API_CONTRACTS.md), [Data Model](../DATA_MODEL.md).

**Implementation and boundaries:** Implement exact GET challenge and raw-body POST HMAC boundary with route/size/WABA/number validation. Commit bounded receipts before acknowledgement; deduplicate envelopes/elements and persist Message Events for correlation. Enqueue after commit and retain safe failed-event diagnostics. The operator recovery scan/replay surface is owned by WA-P2-004.

**Failure cases and verification:** Inject persistence failure before 200, changed raw bytes, duplicate/mixed elements and status-before-acceptance. Unsupported types must not discard valid siblings.

**Completion evidence:** Record signature/replay/rollback/acknowledgement tests; an authorised signed callback may verify intake without any campaign launch.

**Completion evidence (30 October 2026):** Added the Guest GET challenge and signed POST boundary, exact-byte HMAC-SHA256 validation, bounded payload/ownership checks, unique durable receipts, after-commit marketing queue delivery and append-only deduplicated message/status observations. The processor traverses every entry, preserves supported siblings beside unknown changes, stores only minimal status/type diagnostics and retains failures with a generic code. `quality.py integration` passed 67 Frappe integration tests and 17 unit tests, including 8 real WSGI webhook cases for changed bytes, wrong identities, duplicate envelope/elements, queue-after-commit, persistence failure, oversized/wrong-type bodies, status-before-acceptance, Guest permission metadata and redacted worker failures. `quality.py lint` and `quality.py docs` passed. No live Meta credential or callback was used. Production ingress still must enforce the route-specific 1 MiB limit before Frappe parses JSON; recovery tooling, official callback qualification and production HTTPS verification remain open under P2-004/operations.

## WA-P2-004

- [x] **Qualify provider event recovery and operator diagnostics**

**Depends on:** `WA-P2-003`

**Requirements:** `WA-R03`, `WA-R09`, `WA-R15`. **Acceptance:** `WA-A05`, `WA-A06`, `WA-A13`.

**Read first:** [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md), [Operations And Release](../OPERATIONS_AND_RELEASE.md), [Connections](../pages/CONNECTIONS.md).

**Implementation and boundaries:** Implement receipt/source-operation recovery scans, bounded event retries, correlation queues and connection-health projection. Wire manager/system diagnostics to native views. Establish the signed-intake/contract gate; defer real send evidence until the complete shared outbox and audience policy are available.

**Execution checklist:**

1. Persist and atomically claim only allowlisted webhook and connection-operation work; use stable deduplicated job IDs.
2. Recover old Ready receipts and Pending operations after enqueue/Redis loss; reconstruct operations only from permission-hidden, non-secret request arguments.
3. Recover stale Processing/Running leases with bounded webhook backoff and one safe connection read/sync retry; never retry message submissions.
4. Track GET verification separately from signed POST delivery; expose event counts and safe readiness through permission-checked application projections.
5. Wire native Connections summary and System Manager diagnostics using standard Frappe controls and escaped text values.
6. Verify duplicate, poison/unknown, interrupted worker, missing queue job, role-denial and redaction cases; run the full WhatsApp harness gates and attach evidence.

**Failure cases and verification:** Stop Redis/worker between commit and enqueue, replay poison/unknown events and check redacted logs. No silent loss and no arbitrary payload exposure.

**Completion evidence:** Attach recovery tests, callback evidence if available and clear prerequisites for future authorised test submission.

**Completion evidence (30 October 2026):** Added minute-scheduled recovery for durable webhook receipts and allowlisted connection operations. Both use stable deduplicated job IDs and atomic claims; connection jobs recover from hidden non-secret request snapshots, while stale reads/syncs receive one retry. Webhook receipts recover after enqueue loss or stale processing and use 1/5/15/60-minute backoff with five total claims; unsupported authenticated events are retained as processed diagnostics. No outbound message submission enters this retry path. Added separate GET challenge and signed POST timestamps, role-safe event counts/health projection, System Manager-only webhook diagnostics and a labeled native Frappe dialog. `quality.py integration` passed **71 Frappe integration tests and 17 unit tests**; targeted browser checks passed **6** cases with **6 expected matrix skips**, strict TypeScript and all **3 egress probes**; `quality.py lint` and `quality.py docs` passed. Browser screenshots: `development/whatsapp_marketing/.local/test-results/browser/01140f22c90d46e099420e8ba120d27d/`. Recovery, retry-bound, safe-projection, role-denial and migration metadata checks passed. No live Meta callback or outbound send was performed. Production still requires the route-specific 1 MiB ingress limit before Frappe parses JSON, public HTTPS reachability, official signed callback qualification and P7 operational approval.
