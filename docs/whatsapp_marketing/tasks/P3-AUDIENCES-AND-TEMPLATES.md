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

- [ ] **Implement resumable CSV, consent and suppression**

**Depends on:** `WA-P3-001`

**Requirements:** `WA-R04`, `WA-R05`, `WA-R13`. **Acceptance:** `WA-A04`, `WA-A14`, `WA-A17`.

**Read first:** [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md), [Audience And Consent](../flows/AUDIENCE_AND_CONSENT.md), [Contacts And Imports](../pages/CONTACTS_AND_IMPORTS.md).

**Implementation and boundaries:** Implement private CSV validation/mapping preview, WA Import Row ledger and exact-hash confirmation. Add evidence commands, append-only consent history, effective-state projection and cross-number suppression; process withdrawals before automation. Coordinate live eligibility/reservations with withdrawal and protect minimised suppression identities during erasure.

**Failure cases and verification:** Replay row confirmations, crash mid-import, supply bad evidence/backdated grants and race opt-out. Validate private diagnostics and formula-safe output.

**Completion evidence:** Provide import counts/results, race tests, evidence chronology tests and consent UI screenshots using synthetic data.

## WA-P3-003

- [ ] **Implement explainable segments and bounded audience queries**

**Depends on:** `WA-P3-002`

**Requirements:** `WA-R04`, `WA-R05`, `WA-R16`. **Acceptance:** `WA-A03`, `WA-A04`, `WA-A16`.

**Read first:** [Audience Segments](../pages/AUDIENCE_SEGMENTS.md), [Data Model](../DATA_MODEL.md), [Api Contracts](../API_CONTRACTS.md).

**Implementation and boundaries:** Implement versioned bounded filter AST, native editor, permission-aware preview counts/samples and exclusions. Apply eligibility independently of user filters. Provide chunked stable audience iterator for snapshots and enforce 10,000 recipient ceiling at snapshot completion.

**Failure cases and verification:** Reject arbitrary fields/operators/SQL, deep groups and bypass attempts. Test 50,000-contact pagination and source access changes.

**Completion evidence:** Record count/sample reconciliation, bounded query/memory evidence and native empty/exclusion states.

## WA-P3-004

- [ ] **Implement template lifecycle and private media validation**

**Depends on:** `WA-P3-003`

**Requirements:** `WA-R06`, `WA-R13`. **Acceptance:** `WA-A05`, `WA-A07`, `WA-A14`.

**Read first:** [Templates](../pages/TEMPLATES.md), [Api Contracts](../API_CONTRACTS.md), [Permissions And Privacy](../PERMISSIONS_AND_PRIVACY.md).

**Implementation and boundaries:** Implement local template drafts, supported components/language/category, provider submit/sync operations, content hashes and safe previews. Add private JPEG/PNG/PDF validation with provider size limits, safe ID/host-based inbound retrieval and quarantine failures. Keep Authentication sync-only and surface unsupported components read-only.

**Failure cases and verification:** Handle duplicate submit, rejected/paused/reclassified templates, invalid placeholders, cross-connection selection, hostile redirect and fake MIME. Invalidate affected stale campaign approval readiness.

**Completion evidence:** Record contract/UI/media permission tests and, if authorised credentials exist, actual approval-sync evidence without claiming provider approval on local save.
