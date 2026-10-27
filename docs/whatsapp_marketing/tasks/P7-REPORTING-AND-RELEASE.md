# P7: Reporting and release

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P7-001

- [ ] **Implement reconciled reports and dated cost estimates**

**Depends on:** `WA-P6-004`

**Requirements:** `WA-R14`, `WA-R13`. **Acceptance:** `WA-A12`, `WA-A03`, `WA-A16`.

**Read first:** [Reports](../pages/REPORTS.md), [Data Model](../DATA_MODEL.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md).

**Implementation and boundaries:** Implement documented native Script Reports and Overview metric services with explicit denominators/timestamp basis, exact/inferred reply separation and safe drill-down. Add manager-maintained dated WA Rate Card inputs and estimates; no silent FX conversion or invoice claim. Exports use private operations and current permissions.

**Failure cases and verification:** Test duplicate/late statuses, test sends, missing reads/rates, unknowns, Analyst detail/export denial and CSV formula escaping. Do not sum cumulative states as mutually exclusive outcomes.

**Completion evidence:** Record fixture-to-report reconciliation, permission tests and native report/card screenshots.

## WA-P7-002

- [ ] **Implement operational readiness, retention and runbooks**

**Depends on:** `WA-P7-001`

**Requirements:** `WA-R15`, `WA-R13`. **Acceptance:** `WA-A13`, `WA-A14`, `WA-A17`.

**Read first:** [Operations And Release](../OPERATIONS_AND_RELEASE.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md), [Settings](../pages/SETTINGS.md).

**Implementation and boundaries:** Implement readiness diagnostics, audited emergency switch, queue/event age metrics and alert hooks. Configure positive retention policy inputs, legal holds, previewed cleanup/erasure/export operations and private outputs. Validate suppression minimisation and document exact production image/worker/realtime/secret procedures.

**Failure cases and verification:** Fail live enablement on incomplete setup, unavailable health, missing pilot evidence or policy. Disable sending during queue work while callbacks continue. Test holds/erasure and unavailable dependencies.

**Completion evidence:** Provide health/incident/retention test evidence, policy configuration checklist and operational ownership.

## WA-P7-003

- [ ] **Run capacity, security, migration and restore qualification**

**Depends on:** `WA-P7-002`

**Requirements:** `WA-R16`, `WA-R17`, `WA-R01`. **Acceptance:** `WA-A01`, `WA-A02`, `WA-A03`, `WA-A08`, `WA-A14`, `WA-A15`, `WA-A16`, `WA-A17`, `WA-A18`.

**Read first:** [Testing And Acceptance](../TESTING_AND_ACCEPTANCE.md), [Operations And Release](../OPERATIONS_AND_RELEASE.md), [Traceability](../TRACEABILITY.md).

**Implementation and boundaries:** Run the full applicable suite, both-theme UI review, 50,000-contact/10,000-recipient load, concurrent claims, failure injection and repeated migrations. Restore a populated backup with sending disabled and reconcile outbox/provider history. Validate current documentation coverage and commands against implemented behaviour.

**Failure cases and verification:** Reject 10,001 eligible recipients; measure query/memory/inbox/webhook targets on recorded staging hardware. No restore-triggered resend, leaked files or omitted failing checks.

**Completion evidence:** Record commits/images, exact commands/results, metrics, restore evidence, screenshots and resolved findings. Any unmet gate remains open.

## WA-P7-004

- [ ] **Complete authorised pilot and production release decision**

**Depends on:** `WA-P7-003`

**Requirements:** `WA-R15`, `WA-R17`, `WA-R18`. **Acceptance:** `WA-A05`, `WA-A07`, `WA-A08`, `WA-A09`, `WA-A10`, `WA-A11`, `WA-A12`, `WA-A13`, `WA-A15`, `WA-A16`, `WA-A17`, `WA-A18`.

**Read first:** [Operations And Release](../OPERATIONS_AND_RELEASE.md), [Implementation Plan](../IMPLEMENTATION_PLAN.md), [Progress](../PROGRESS.md).

**Implementation and boundaries:** Configure the explicit 1–20-contact opted-in pilot allowlist, enable only Pilot scope after offline qualification, and run the limited approved campaign, STOP, inbound agent reply and automation handover on the qualified image. Manager records reviewed pilot evidence; System Manager selects Live scope only after all gates. Record release/rollback ownership and gradual scale plan.

**Failure cases and verification:** If credentials, approvals, recipients or any required gate are unavailable, record Blocked and stop live enablement while retaining completed offline evidence. Documentation approval alone does not authorise arbitrary external sends.

**Completion evidence:** Provide pilot consent/approval references without personal data, provider delivery evidence, manager readiness decision and final honest production status.
