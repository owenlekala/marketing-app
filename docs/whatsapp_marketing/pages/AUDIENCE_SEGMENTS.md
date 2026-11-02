# Audience segments

Page contract: **WA-UI-AUDIENCE_SEGMENTS**. Sidebar label: **Audience segments**. [Navigation index](README.md).

## Purpose and implementation

Native WA Audience Segment List/Form with native filter controls and paginated preview.

**Users:** Marketing User/Manager with source permissions.

## Layout and fields

- Form fields: name, company, enabled state and supported condition controls backed by versioned filters_json.
- Supported criteria: tag membership, language, source type, allowed source attributes, creation interval and archived state.
- Preview panel: matched total, eligible total, excluded reasons and paginated sample with display name/phone/eligibility reason.
- Explicit note: preview is live and advisory; campaign approval uses a frozen snapshot.

## Filters and data behaviour

Use the version 1 bounded AST `{version, logic, rules, groups}` with native Desk controls. Root and nested groups use `and` or `or`; the tree has at most 20 predicates and nesting depth 3. Rules allow `tag`, `language`, `source_type`, `created_on`, `archived`, and these source attributes only: `Lead.country`, `Lead.company`, `Customer.customer_name`, `Contact.full_name`, `Sales Order.company`, and `Sales Order.docstatus`. Operators are fixed by field type; lists contain at most 20 values. Arbitrary columns, operators, SQL and extra AST keys are rejected. Eligibility is always applied; users cannot filter around consent, suppression or archive state. Counts and samples recheck linked ERPNext source permissions in bounded batches.

## Actions and prerequisites

Preview calls `audiences.preview`; Save validates schema and source fields. Up to 2,000 candidates are previewed inline. Larger scans (up to 50,000 candidates) create a durable, idempotent operation with bounded background progress; larger audiences must be refined. Create Campaign opens a Draft with this segment selected, without copying preview membership or granting approval. Disable prevents new selection but preserves historical snapshots.

## UI states, access and responsive behaviour

No eligible contacts explains exclusion counts and links to consent/import guidance. A malformed filter returns a safe validation error; preview is paginated, capped at 50,000 scanned contacts, and switches to durable background work above the inline threshold. Empty/failed preview never means approved zero recipients. Disabling prevents new use and leaves historical snapshots intact. Layout uses native controls in both themes.

## Interfaces and records

WA Audience Segment, WA Contact and authorised source projections; `audiences.preview`, `audiences.source_preview`.

## Implementation and acceptance

Tasks: [WA-P3-003](../tasks/P3-AUDIENCES-AND-TEMPLATES.md). Scenarios: [WA-A03, WA-A04, WA-A16](../TESTING_AND_ACCEPTANCE.md).

- Permission-scoped counts match sampled records.
- Arbitrary fields/SQL/recursive filters are rejected.
- 50,000-contact dataset previews remain paginated and campaign snapshots exclude suppressed matches.
