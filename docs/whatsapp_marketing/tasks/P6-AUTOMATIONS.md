# P6: Automations

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P6-001

- [ ] **Implement native step editor and immutable publication**

**Depends on:** `WA-P5-004`

**Requirements:** `WA-R11`, `WA-R02`. **Acceptance:** `WA-A02`, `WA-A11`.

**Read first:** [Automations](../pages/AUTOMATIONS.md), [Automation Execution](../flows/AUTOMATION_EXECUTION.md), [Data Model](../DATA_MODEL.md).

**Implementation and boundaries:** Implement typed definition schema, native ordered-step controls, forward target/condition editing, definition hashing and immutable version publication. Validate purpose, sender/templates, run-as user, expiry, 100-step limit and no arbitrary code. Draft edits must not mutate published versions.

**Failure cases and verification:** Reject cycles/backward/unreachable steps, unknown keys/actions, stale publish hash and unauthorised principal. No drag-and-drop dependency.

**Completion evidence:** Record validator/publication/REST bypass tests and native editor state screenshots.

## WA-P6-002

- [ ] **Implement controlled inbound and ERPNext trigger intake**

**Depends on:** `WA-P6-001`

**Requirements:** `WA-R11`, `WA-R12`, `WA-R05`. **Acceptance:** `WA-A11`, `WA-A03`, `WA-A06`.

**Read first:** [Erpnext Integration](../ERPNext_INTEGRATION.md), [Automation Execution](../flows/AUTOMATION_EXECUTION.md), [Data Model](../DATA_MODEL.md).

**Implementation and boundaries:** Implement inbound first/keyword/exact-campaign-reply/qualifying-opt-in triggers and owned Lead/Customer after_insert/Sales Order on_submit hooks. Commit deduplicated source events with source version/actor; resolve configured company/contact and current run-as permissions after commit. New publication affects future events only.

**Failure cases and verification:** Rollback source creation, duplicate webhook/source events, missing company/contact, denied source and order cancellation. No provider calls or marketing consent inference in source transactions.

**Completion evidence:** Record hook rollback/dedup/permission tests and trigger-to-run traceability.

## WA-P6-003

- [ ] **Implement durable step execution, waits and recovery**

**Depends on:** `WA-P6-002`

**Requirements:** `WA-R11`, `WA-R08`, `WA-R10`. **Acceptance:** `WA-A11`, `WA-A08`, `WA-A10`.

**Read first:** [Messaging And Reliability](../MESSAGING_AND_RELIABILITY.md), [Automation Execution](../flows/AUTOMATION_EXECUTION.md), [Data Model](../DATA_MODEL.md).

**Implementation and boundaries:** Implement unique run/step keys, typed conditions, persisted due waits, tags, assignment, send/outbox, handover and End. Claim runs with leases, pause definition claims, recheck consent/window/principal, preserve pinned versions and implement explicit error outcomes. Reuse existing sender rather than a second HTTP path.

**Failure cases and verification:** Restart during wait/tag/message creation, replay triggers, pause/resume after expiry, withdraw consent and publish a new version mid-run. No long worker sleeps or duplicated effective step.

**Completion evidence:** Record fake-clock/crash/replay/handover tests and persisted-run recovery evidence.

## WA-P6-004

- [ ] **Complete simulation, journey preview and automation qualification**

**Depends on:** `WA-P6-003`

**Requirements:** `WA-R11`, `WA-R12`, `WA-R17`. **Acceptance:** `WA-A11`, `WA-A02`.

**Read first:** [Automations](../pages/AUTOMATIONS.md), [Testing And Acceptance](../TESTING_AND_ACCEPTANCE.md), [Automation Execution](../flows/AUTOMATION_EXECUTION.md).

**Implementation and boundaries:** Generate read-only journey preview from the validated saved definition and show Draft/Published provenance. Implement non-mutating synthetic simulation with branch/eligibility traces. Exercise welcome, keyword, campaign routing, consent opt-in and CRM follow-up journeys end to end using controlled fixtures.

**Failure cases and verification:** Prove simulation performs no provider/source/consent mutation and does not publish. Verify Waiting Human/Failed/due states and inaccessible diagnostic details.

**Completion evidence:** Attach journey traces, UI evidence, version-preservation and no-side-effect tests; document any live prerequisite without masking it.
