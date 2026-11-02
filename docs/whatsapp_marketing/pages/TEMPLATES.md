# Templates

Page contract: **WA-UI-TEMPLATES**. Sidebar label: **Templates**. [Navigation index](README.md).

## Purpose and implementation

Native WA Template List/Form with command-backed draft controls and a scoped rendered preview.

**Users:** Marketing User/Manager edit local drafts; Manager submits/syncs; System Manager maintains connection access.

## Layout and fields

- List: name, language, category, connection, provider status and last sync.
- Form tabs: Definition; Header/Body/Footer/Buttons; Preview; Provider Status.
- Body variable controls identify positional/name placeholders supported by the pinned provider schema. Show examples separately from live values.
- Header media selector accepts only authorised private unattached JPEG/PNG/PDF files after byte, structure, digest and size validation. Button editor supports the verified provider subset (URL and quick reply/unsubscribe); unsupported definitions remain sync-readable, not editable as broken forms.

## Filters and data behaviour

Filter by connection, language, category and status. Authentication templates are sync-only in v1. Preview renders escaped plain text plus safe controlled component markup. Status is provider-owned and never directly editable.

## Actions and prerequisites

Save Draft validates components and stores a canonical hash. Submit for Review calls the provider through a persisted operation; Sync refreshes actual state. Approved edits archive a local revision. Media-backed submission, provider-ID edits, and campaign-readiness invalidation remain open pending their owning contracts/tasks; a local save never implies approval. Rejected drafts show safe reason text.

## UI states, access and responsive behaviour

No templates offers Sync or Create Draft according to permission. Pending/Rejected/Paused states explain next action. Network failures retain the local draft and operation identity; repeated submit does not create uncontrolled duplicates. Preview follows Frappe tokens and stacks below controls on narrow screens.

## Interfaces and records

WA Template, private File, WA Operation; template submission/sync contract in API_CONTRACTS.

## Implementation and acceptance

Tasks: [WA-P3-004](../tasks/P3-AUDIENCES-AND-TEMPLATES.md). Scenarios: [WA-A05, WA-A07, WA-A14](../TESTING_AND_ACCEPTANCE.md).

- Approved language/category/components map to provider contract fixtures.
- Paused/rejected templates cannot be used for live submission.
- Unauthorised or unsupported media never appears as an available public attachment.
