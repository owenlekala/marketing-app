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

Use native AND/OR filter grouping only within the documented bounded AST (maximum 20 predicates, nesting depth 3). Operators are allowlisted by field type. Eligibility is always applied; users cannot filter around suppression. Counts and samples are evaluated under the same source permissions.

## Actions and prerequisites

Preview calls `audiences.preview`; Save validates schema and source fields. Create Campaign opens a Draft with this segment selected, without copying preview membership or granting approval. Disable prevents new selection but preserves historical snapshots.

## UI states, access and responsive behaviour

No eligible contacts explains exclusion counts and links to consent/import guidance. A malformed filter returns a field-level error; expensive previews use an operation if they exceed synchronous budget. Empty/failed preview never means approved zero recipients. Layout uses native controls in both themes.

## Interfaces and records

WA Audience Segment, WA Contact and authorised source projections; `audiences.preview`, `audiences.source_preview`.

## Implementation and acceptance

Tasks: [WA-P3-003](../tasks/P3-AUDIENCES-AND-TEMPLATES.md). Scenarios: [WA-A03, WA-A04, WA-A16](../TESTING_AND_ACCEPTANCE.md).

- Permission-scoped counts match sampled records.
- Arbitrary fields/SQL/recursive filters are rejected.
- 50,000-contact dataset previews remain paginated and campaign snapshots exclude suppressed matches.
