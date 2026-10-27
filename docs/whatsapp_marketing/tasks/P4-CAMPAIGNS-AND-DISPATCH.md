# P4: Campaigns and dispatch

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P4-001

- [ ] **Implement durable sender, reservations and recovery**

**Depends on:** `WA-P3-004`

**Requirements:** `WA-R08`, `WA-R05`, `WA-R15`, `WA-R16`. **Acceptance:** `WA-A08`, `WA-A04`, `WA-A13`, `WA-A16`.

**Read first:** [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md), [Data Model](../DATA_MODEL.md), [Operations And Release](../OPERATIONS_AND_RELEASE.md).

**Implementation and boundaries:** Implement shared test/inbox/campaign/automation message-outbox services, atomic leases, pre-submission live checks, company/contact cap and optional estimate reservations, HTTP boundary and conditional completion. Add known-safe bounded retries, Unknown reconciliation actions and recovery scans; use dedicated marketing queue and bounded claims.

**Failure cases and verification:** Inject each crash boundary, concurrent workers, rolled-back enqueue, network ambiguity, credential failure, cap contention and opt-out race. No row lock held across HTTP and no blind unknown resend.

**Completion evidence:** Record failure matrix results, database constraints/claim tests and queue/memory measurements; unblock complete test sending only after eligibility checks pass.

## WA-P4-002

- [ ] **Implement campaign snapshots, tests and manager approval**

**Depends on:** `WA-P4-001`

**Requirements:** `WA-R07`, `WA-R05`, `WA-R06`. **Acceptance:** `WA-A07`, `WA-A04`.

**Read first:** [Campaigns](../pages/CAMPAIGNS.md), [Data Model](../DATA_MODEL.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Implement native campaign tabs, bounded Building/Ready snapshots with frozen resolved variables/media hashes, deterministic configuration hash and optimistic concurrency. Require same-hash test acceptance before approval request; queue tests through the verified shared sender from P4-001. Implement manager approval/rejection, material-change invalidation and Clone after submission.

**Failure cases and verification:** Test partial/oversize/empty snapshots, stale revision/hash, changed template/source access and User approval bypass. Test the full approval path with the real shared sender against a controlled fake provider.

**Completion evidence:** Record domain/integration tests and review-tab screenshots; record external live qualification separately in P7; do not claim provider delivery from offline tests.

## WA-P4-003

- [ ] **Implement campaign scheduling and lifecycle controls**

**Depends on:** `WA-P4-002`

**Requirements:** `WA-R07`, `WA-R15`. **Acceptance:** `WA-A07`, `WA-A13`.

**Read first:** [Campaign Approval And Dispatch](../flows/CAMPAIGN_APPROVAL_AND_DISPATCH.md), [Api Contracts](../API_CONTRACTS.md), [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md).

**Implementation and boundaries:** Implement approved Schedule/Launch/Pause/Resume/Cancel using shared transition services and indexed minute scheduler discovery. Respect UTC/timezone, expiry and frozen policy. Generate recipient logical work once; material edits after Submitting require Clone. Keep dispatch completion distinct from delivery outcomes.

**Failure cases and verification:** Race manager/scheduler launch, pause during batches, future-start launch and expiry during backlog. Resume must not recreate accepted/unknown recipient work.

**Completion evidence:** Record lifecycle/scheduler concurrency tests, action-state UI evidence and audit entries.

## WA-P4-004

- [ ] **Complete campaign results and end-to-end dispatch qualification**

**Depends on:** `WA-P4-003`

**Requirements:** `WA-R07`, `WA-R08`, `WA-R14`, `WA-R17`. **Acceptance:** `WA-A07`, `WA-A08`, `WA-A12`.

**Read first:** [Campaigns](../pages/CAMPAIGNS.md), [Testing And Acceptance](../TESTING_AND_ACCEPTANCE.md), [Webhooks And Delivery](../flows/WEBHOOKS_AND_DELIVERY.md).

**Implementation and boundaries:** Wire exact recipient/message outcomes, exclusion/failure/unknown drill-down and live progress into native Campaign UI. Run full draft→snapshot→test→approval→schedule→send→callback flow with fake provider, then an explicitly authorised test recipient when credentials exist. Verify state reconciliation and audit evidence across reloads.

**Failure cases and verification:** Handle late/duplicate/out-of-order callbacks, template rejection after approval, missing read receipts and Completed with unresolved unknowns. Do not equate browser success with Delivered.

**Completion evidence:** Provide end-to-end logs/screenshots, verified test evidence and remaining live prerequisites; close the earlier campaign/test subchecks only when genuinely passed.
