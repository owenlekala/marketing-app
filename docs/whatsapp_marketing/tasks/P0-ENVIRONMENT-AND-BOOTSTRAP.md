# P0: Environment and bootstrap

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P0-001

- [x] **Verify source and deployment baseline**

**Depends on:** None; first implementation task.

**Requirements:** `WA-R01`, `WA-R18`. **Acceptance:** `WA-A01`, `WA-A18`.

**Read first:** [Framework And Setup](../FRAMEWORK_AND_SETUP.md), [References](../REFERENCES.md).

**Implementation and boundaries:** Inspect current AGENTS instructions, repository statuses, version/manifest requirements and fork revisions. Identify whether a Bench and site exist without dumping credentials. Record which facts are inspected and which runtime assumptions remain unverified; preserve unrelated user changes.

**Failure cases and verification:** Detect mismatched forks, unsupported Python/Node, absent site and inaccessible Docker inventory. Do not proceed as if source folders are an installed bench.

**Completion evidence:** Attach safe version/status output and runtime inventory to progress; correct source references and mark unresolved prerequisites.

## WA-P0-002

- [x] **Establish reproducible disposable Docker/Bench runtime**

**Depends on:** `WA-P0-001`

**Requirements:** `WA-R01`, `WA-R15`. **Acceptance:** `WA-A01`, `WA-A13`.

**Read first:** [Framework And Setup](../FRAMEWORK_AND_SETUP.md), [Operations And Release](../OPERATIONS_AND_RELEASE.md).

**Implementation and boundaries:** Prepare implementation-owned dev Compose/image configuration using Python 3.14, Node 24, MariaDB 11.8 and supported pinned Redis/bench images. Mount matching source revisions, initialise Bench, install ERPNext on a disposable named site, and verify database/assets/realtime/worker/scheduler. Record exact image digests, paths, CLI commands and service entrypoints.

**Failure cases and verification:** Handle missing runtime versions, old websocket commands, wrong mounts and unavailable services. No production-site changes or demo passwords in shared deployment.

**Completion evidence:** Provide reproducible setup commands, successful safe health checks and explicit outstanding runtime failures; no live-provider traffic.

## WA-P0-003

- [x] **Create application repository and scoped instruction bridge**

**Depends on:** `WA-P0-002`

**Requirements:** `WA-R01`, `WA-R18`. **Acceptance:** `WA-A01`, `WA-A18`.

**Read first:** [Architecture](../ARCHITECTURE.md), [Implementation Rules](../IMPLEMENTATION_RULES.md), [Implementation Kickoff](../IMPLEMENTATION_KICKOFF.md).

**Implementation and boundaries:** Scaffold tag_marketing with Bench; initialise its own Git repository and dependency metadata for the inspected compatible versions. Add app-level AGENTS.md pointing to the canonical handbook. Move this canonical handbook under app docs/whatsapp_marketing and the owned runtime controller into the repository; adjust source links/mounts and preserve the Compose project, credentials and named volumes. Record canonical locations; retain only pointers at previous locations if needed, never second editable copies.

**Failure cases and verification:** Check package/module naming collisions, missing required apps and instructions accidentally scoped only to docs. Do not change framework/payroll source or create a remote/push without separate authorisation.

**Completion evidence:** Record initial app commit, instruction resolution and link-check results from the canonical documentation location.

## WA-P0-004

- [x] **Configure test harness and deterministic adapters**

**Depends on:** `WA-P0-003`

**Requirements:** `WA-R17`, `WA-R18`. **Acceptance:** `WA-A01`, `WA-A18`.

**Read first:** [Testing And Acceptance](../TESTING_AND_ACCEPTANCE.md), [Architecture](../ARCHITECTURE.md).

**Implementation and boundaries:** Configure supported Frappe integration tests, pure domain tests, app lint/type checks and Playwright browser harness. Add fake clock/provider boundaries and a rule that automated tests reject unexpected external network calls. Document exact commands, synthetic fixtures and two-user test setup.

**Failure cases and verification:** Prove rollback isolation and deterministic time; fail a deliberate unexpected-provider call. Do not send test traffic to real users.

**Completion evidence:** Run a meaningful scaffold integration check and harness verification; record commands and dependency versions, then update the test guide.
