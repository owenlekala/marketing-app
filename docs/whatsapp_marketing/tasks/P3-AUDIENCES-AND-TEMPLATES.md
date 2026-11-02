# P3: Audiences and templates

[Task index and shared completion rules](README.md) · [Phase gates](../IMPLEMENTATION_PLAN.md). Task checkboxes in this file are authoritative.

## WA-P3-001

- [x] **Implement company-scoped contacts and ERPNext projections**

**Depends on:** `WA-P2-004`

**Requirements:** `WA-R04`, `WA-R12`. **Acceptance:** `WA-A03`, `WA-A04`.

**Read first:** [Erpnext Integration](../ERPNext_INTEGRATION.md), [Data Model](../DATA_MODEL.md), [Contacts And Imports](../pages/CONTACTS_AND_IMPORTS.md).

**Implementation and boundaries:** Implement contact/tag forms, allowlisted source links, actor-permission-aware source previews, explicit company and selected-phone mapping, E.164 normalisation and company/phone constraints. Use actual Customer primary Contact/Contact Phone structure and preserve multiple source links without copying inaccessible fields.

**Failure cases and verification:** Test shared Customers, multiple phones, missing/mismatched company, source revocation, number change and concurrent duplicate inserts. Do not infer marketing consent.

**Completion evidence:** Record source/schema permission tests and real native contact/list/source-selection UI evidence.

**Completion evidence (30 October 2026):** Implemented company-scoped source projections and native contact/tag profile policies, with explicit E.164 selection, append-only authorised ERPNext source links, and `Unknown` consent on creation. Customer primary Contact and primary-mobile Contact Phone choices are read only after source permission checks; Lead and submitted Sales Order reads are company scoped. `quality.py integration` passed **76 Frappe integration tests and 20 unit tests**, including source permission/revocation, explicit unassigned Lead inclusion, stale company scope, Customer mobile alternatives, no consent inference and a real two-connection uniqueness race. `quality.py lint` passed Ruff, formatting and mypy across **163 sources**; `quality.py docs` passed with no broken references or duplicate groups. The browser acceptance passed in desktop light, desktop dark, tablet and mobile; mobile correctly invokes the action from Frappe's native overflow menu. Screenshots: [light source selection](../../../development/whatsapp_marketing/.local/test-results/browser/867fd80789b146008f15af692323ae80/audiences-Marketing-Manage-e271b-hrough-native-Desk-controls-desktop-light/contacts-authorised-source-selection.png), [dark linked contact](../../../development/whatsapp_marketing/.local/test-results/browser/867fd80789b146008f15af692323ae80/audiences-Marketing-Manage-e271b-hrough-native-Desk-controls-desktop-dark/contacts-source-linked-native-form.png), [tablet linked contact](../../../development/whatsapp_marketing/.local/test-results/browser/867fd80789b146008f15af692323ae80/audiences-Marketing-Manage-e271b-hrough-native-Desk-controls-tablet/contacts-source-linked-native-form.png), [mobile linked contact](../../../development/whatsapp_marketing/.local/test-results/browser/ea2dd4e1b90a4712931616e46a8b509f/audiences-Marketing-Manage-e271b-hrough-native-Desk-controls-mobile/contacts-source-linked-native-form.png). Only the WA-P3-001 portion of WA-A03/WA-A04 is closed: consent/import/suppression, full audience queries and template lifecycle remain explicitly open. No provider calls or live messaging were used.

## WA-P3-002

- [x] **Implement resumable CSV, consent and suppression**

**Depends on:** `WA-P3-001`

**Requirements:** `WA-R04`, `WA-R05`, `WA-R13`. **Acceptance:** `WA-A04`, `WA-A14`, `WA-A17`.

**Read first:** [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md), [Audience And Consent](../flows/AUDIENCE_AND_CONSENT.md), [Contacts And Imports](../pages/CONTACTS_AND_IMPORTS.md).

**Implementation and boundaries:** Implement private CSV validation/mapping preview, WA Import Row ledger and exact-hash confirmation. Add evidence commands, append-only consent history, effective-state projection and cross-number suppression; process withdrawals before automation. Coordinate live eligibility/reservations with withdrawal and protect minimised suppression identities during erasure.

**Failure cases and verification:** Replay row confirmations, crash mid-import, supply bad evidence/backdated grants and race opt-out. Validate private diagnostics and formula-safe output.

**Completion evidence:** Provide import counts/results, race tests, evidence chronology tests and consent UI screenshots using synthetic data.

**Completion evidence (2 November 2026):** Implemented private, exact-hash CSV preview/confirmation with durable 100-row chunk processing, a resumable import ledger and terminal replay-safe outcomes. Append-only consent events derive effective state by occurrence chronology; withdrawals suppress immediately and backdated grants cannot reopen permission. Company-wide keyed suppression digests are checked before CSV and ERPNext source-link contact creation; detached digest records block re-import after identity-bearing rows are removed. `application.eligibility.lock_contact_for_submission` is the shared short-transaction lock/read contract for future P4 reservations, and suppression changes use the same contact-row lock. A two-connection test proves withdrawal waits for an active submission eligibility lock and closes the next eligibility check. The manager-only release path now rechecks consent after acquiring that lock. `quality.py integration` passed **85 Frappe integration tests and 25 unit tests**, including suppression replay after state change, both re-import paths, withdrawal chronology and a crash after a committed 100-row chunk. `quality.py lint` passed Ruff, formatting and mypy across **172 sources**. `quality.py docs` passed 48 Markdown files, 705 links, 79 source references, 7 Mermaid diagrams, 18 requirements, 32 tasks and 18 acceptance scenarios with zero errors or duplicate groups. The focused browser acceptance passed 8 cases without skips across desktop light/dark, tablet and mobile; evidence is under `development/whatsapp_marketing/.local/test-results/browser/f6e6a6d30bb042d6ad6360bad790ed83/`. P4 must use the published lock contract in its actual reservation path and run sender-level dispatch tests; approved erasure workflow remains P7-owned. This closes P3-002 only; it does not qualify production or enable live sending.

## WA-P3-003

- [x] **Implement explainable segments and bounded audience queries**

**Depends on:** `WA-P3-002`

**Requirements:** `WA-R04`, `WA-R05`, `WA-R16`. **Acceptance:** `WA-A03`, `WA-A04`, `WA-A16`.

**Read first:** [Audience Segments](../pages/AUDIENCE_SEGMENTS.md), [Data Model](../DATA_MODEL.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Implement versioned bounded filter AST, native editor, permission-aware preview counts/samples and exclusions. Apply eligibility independently of user filters. Provide chunked stable audience iterator for snapshots and enforce 10,000 recipient ceiling at snapshot completion.

**Failure cases and verification:** Reject arbitrary fields/operators/SQL, deep groups and bypass attempts. Test 50,000-contact pagination and source access changes.

**Completion evidence:** Verified 2 November 2026. Implemented a framework-independent version 1 filter AST with strict field/operator/type allowlists, group-depth and predicate budgets, plus native segment create/edit/preview/disable controls. SQL compilation and persistence are isolated in the infrastructure adapter; values are bound, candidate-threshold counting stops at 50,001, keyset scans use 1,000-row permission-rechecked batches, and source access is checked for the initiating actor on every page. Preview counts reconcile against samples, applies eligibility independently of user filters, caps scans at 50,000 contacts, and switches above 2,000 candidates to an idempotent durable operation with actor/revision rechecks, bounded progress and stale/pending recovery. Snapshot consumers receive a stable 100-row iterator that yields at most 10,000 eligible recipients and fails on the 10,001st; WA-P4-002 must consume it in the snapshot write transaction.

`python3 development/whatsapp_marketing/quality.py integration` passed **88 Frappe integration tests and 30 unit tests**. Coverage includes arbitrary AST rejection, source permission changes, count/sample/exclusion reconciliation, queued idempotency and worker recovery, the 50,000-contact scan with less than 32 MiB additional traced Python peak, and the 10,001st snapshot-recipient failure. `quality.py lint` passed Ruff, formatting and mypy across **177 sources**. `quality.py docs` passed 48 Markdown files, 705 relative links, 79 source references, 7 diagrams, 18 requirements, 32 tasks and 18 acceptance scenarios with zero duplicate groups or errors. The focused Desk browser matrix passed **4 cases without skips** across desktop light/dark, tablet and mobile; strict TypeScript and all **3 egress probes** passed. Evidence: `development/whatsapp_marketing/.local/test-results/browser/0ef1f276a03a4474bf89aa7d86b6b06c/`. The native preview demonstrates an Unknown-consent exclusion and empty eligible state. This closes the audience-query slice of WA-A03/WA-A16; broader staging throughput targets, snapshot persistence, WA-P3-004 templates and WA-P4-002 campaigns remain open. Production is not qualified and live sending remains disabled.

## WA-P3-004

- [ ] **Implement template lifecycle and private media validation**

**Depends on:** `WA-P3-003`

**Requirements:** `WA-R06`, `WA-R13`. **Acceptance:** `WA-A05`, `WA-A07`, `WA-A14`.

**Read first:** [Templates](../pages/TEMPLATES.md), [Api Contracts](../API_CONTRACTS.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md).

**Implementation and boundaries:** Implement local template drafts, supported components/language/category, provider submit/sync operations, content hashes and safe previews. Add private JPEG/PNG/PDF validation with provider size limits, safe ID/host-based inbound retrieval and quarantine failures. Keep Authentication sync-only and surface unsupported components read-only.

**Failure cases and verification:** Handle duplicate submit, rejected/paused/reclassified templates, invalid placeholders, cross-connection selection, hostile redirect and fake MIME. Invalidate affected stale campaign approval readiness when WA-P4-002 introduces campaign snapshots.

**Completion evidence:** Record contract/UI/media permission tests and, if authorised credentials exist, actual approval-sync evidence without claiming provider approval on local save.

**Implementation evidence (In Progress, 2 November 2026):** Added pure editable-subset validation and canonical hashes, owner/private/unattached media checks with structural JPEG/PNG/PDF validation, exact stored-size matching, private revision snapshots for approved edits, role/company-scoped application commands, safe previews, native Desk draft/validate/submit/sync controls, and durable submit/sync operations. Authentication remains sync-only and provider status is never inferred from local save. New drafts start at revision 1 and malformed placeholders fail closed. `python3 development/whatsapp_marketing/quality.py integration` previously passed **95 Frappe integration tests and 35 unit tests**, before the latest media-validation changes. Focused tests for malformed JPEG wrappers, trailing bytes, and File-size mismatch were added but could not be run because Docker is unavailable in this environment. The focused browser acceptance previously passed **4 cases without skips** across desktop light/dark, tablet and mobile, with strict TypeScript and all **3 egress probes** passing. The native flow creates and validates a draft and proves script-like sample text renders as escaped content. Evidence: `development/whatsapp_marketing/.local/test-results/browser/428c64acfd554671b68d8deb7fb56b49/`. Final lint, documentation and whitespace checks are recorded in [Progress](../PROGRESS.md#wa-p3-004--template-lifecycle-and-private-media-validation).

This task remains open: media-backed submission needs a verified provider upload-handle contract; provider-ID edit/resubmission behavior needs a verified edit contract; invalid media quarantine/retention needs an explicit lifecycle; WA-P4-002 must invalidate affected campaign readiness; and authorised provider approval-sync evidence remains outstanding. No live credentials or provider calls were used; this implementation does not qualify production readiness.
