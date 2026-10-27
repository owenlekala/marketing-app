# Implementation plan

The agreed scope/defaults are owned by [product requirements](PRODUCT_REQUIREMENTS.md); app boundaries by [ADR-001](decisions/ADR-001-APP-AND-DESIGN-BASELINE.md). Start from [kickoff](IMPLEMENTATION_KICKOFF.md).

## Phase sequence and gates

1. **P0 — Environment/bootstrap:** establish the exact compatible container/Bench/site, app repository and instruction bridge. Gate: reproducible disposable site, explicit runtime evidence and configured test harness. No real campaign traffic.
2. **P1 — App/native UI:** schema foundations, roles/settings, owned navigation and native components. Gate: repeatable install/migrate and reviewed shell/theme screenshots.
3. **P2 — Connections/webhooks:** verified Meta contract, protected connection/number setup, signed durable callbacks and contract/recovery checks. Gate: replay-safe intake and verified provider contracts; outbound test acceptance waits for the complete P3/P4 eligibility/outbox path.
4. **P3 — Audiences/templates:** source projections, profiles/tags, CSV/evidence/suppression, segments and provider template lifecycle. Gate: explainable eligible audiences and approved supported templates with permission tests.
5. **P4 — Campaigns/dispatch:** shared workers/reservations/recovery first, then hash-bound snapshots/tests/approval, scheduling and campaign results. Gate: end-to-end qualification using a controlled fake provider and authorised test commands; restricted live campaign pilot occurs in P7, with no blind retries or approval bypass.
6. **P5 — Inbox:** inbound projection, native Desk page, authorised replies/media, assignment/realtime and human mode. Gate: two-agent privacy/window/handover evidence.
7. **P6 — Automations:** native definition editor, immutable publication, source/inbound trigger intake, durable engine and simulation. Gate: replay/crash/version tests and all initial journeys.
8. **P7 — Reporting/release:** metrics/estimates, privacy/operations, load/restore/migrations and authorised live pilot. Gate: recorded production qualification and explicit live readiness.

Detailed work and individual prerequisites are in [task index](tasks/README.md). Each phase has four identifiable tasks; complete or explicitly record blockers before dependent work.

## Delivery method

Complete vertical slices: metadata, validation, application service, adapter, API, permission, native UI, failure recovery and tests. A half-connected UI or provider-success-only implementation does not complete a feature.

Commit changes in the future app repository, not framework/payroll repositories. Record commits and evidence in [progress](PROGRESS.md). Keep the docs versioned as described in P0; this workspace root is not a repository.

Material product/architecture changes follow [ADR procedure](decisions/README.md). Routine compatible implementation choices do not need an approval ceremony. Update owning contracts when behaviour changes and rerun affected consistency checks.
