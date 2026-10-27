# P1: App and native UI

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P1-001

- [x] **Implement owned schema, roles and settings guards**

**Depends on:** `WA-P0-004`

**Requirements:** `WA-R01`, `WA-R13`. **Acceptance:** `WA-A01`, `WA-A03`.

**Read first:** [Data Model](../DATA_MODEL.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md).

**Implementation and boundaries:** Create the documented DocType metadata, child types, indexes and ownership/migration helpers. Implement settings validation, company constraints, sensitive field permissions and denial of direct managed-field edits; feature services remain unavailable until their tasks. Seed roles conservatively and keep sending disabled. Include schema-only records for later feature services without presenting them as usable features.

**Failure cases and verification:** Test duplicate composite/provider keys, NULL provider IDs, wrong companies, generic REST/import bypass and second migration. Preserve administrator customisations.

**Completion evidence:** Record fresh install/repeated migrate and permission tests, plus exact schema constraints verified on the staging database.

## WA-P1-002

- [x] **Register owned Dock, Sidebar and workspace**

**Depends on:** `WA-P1-001`

**Requirements:** `WA-R02`. **Acceptance:** `WA-A02`, `WA-A03`.

**Read first:** [Ui Design System](../UI_DESIGN_SYSTEM.md), [Overview](../pages/OVERVIEW.md), [Readme](../pages/README.md).

**Implementation and boundaries:** Create the TAG Marketing tile/Dock and WhatsApp Marketing Sidebar/Workspace using the current source metadata. Wire every documented destination, role visibility, native cards/charts and safe unavailable-data states. Create permission-scoped metric interfaces; optional shared-navigation adapter is conditional on a verified public extension point.

**Failure cases and verification:** Check route collisions, localisation absent, user customisations and aggregate leakage. Do not seed fake engagement or edit ERPNext navigation JSON.

**Completion evidence:** Capture owned navigation for User/Agent/Analyst/Manager and verify target resolution plus repeated seed behaviour.

## WA-P1-003

- [x] **Build native UI and error/progress foundations**

**Depends on:** `WA-P1-002`

**Requirements:** `WA-R02`, `WA-R13`. **Acceptance:** `WA-A02`, `WA-A14`.

**Read first:** [Ui Design System](../UI_DESIGN_SYSTEM.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Create scoped bundles/icon registration, shared safe command/error handling, operation progress retrieval and native dialogs/controls. Apply translation wrappers, stale-document feedback, loading/empty/error components and keyboard focus behaviour. Use native forms/list/report routes; custom content stays under the owned Page scope.

**Failure cases and verification:** Check light/dark tokens, escaped inbound/sample content, lost network and standard Frappe error envelopes. No global CSS overrides or secrets in browser payloads.

**Completion evidence:** Record asset build/lint results and browser coverage of real stateful feedback components, not tests that merely mirror class names.

## WA-P1-004

- [x] **Verify ERPNext parity and install behaviour**

**Depends on:** `WA-P1-003`

**Requirements:** `WA-R02`, `WA-R17`. **Acceptance:** `WA-A01`, `WA-A02`.

**Read first:** [Ui Design System](../UI_DESIGN_SYSTEM.md), [Testing And Acceptance](../TESTING_AND_ACCEPTANCE.md).

**Implementation and boundaries:** Collect same-version ERPNext shell/form/list/dialog/report screenshots and compare marketing foundation screens at defined viewports/themes. Verify keyboard/focus and permission-denied destinations. Reinstall/migrate on a disposable site and retain native customisations; repair actual mismatches.

**Failure cases and verification:** Exercise missing setup, unavailable metrics and restricted roles. Clearly separate foundation screen parity from future feature completion.

**Completion evidence:** Attach reference/comparison screenshots, review findings and install/migration logs before closing the native-shell gate.
