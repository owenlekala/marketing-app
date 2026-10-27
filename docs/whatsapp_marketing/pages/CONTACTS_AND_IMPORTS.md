# Contacts and imports

Page contract: **WA-UI-CONTACTS_AND_IMPORTS**. Sidebar label: **Contacts**. [Navigation index](README.md).

## Purpose and implementation

Native WA Contact List/Form; private CSV import handled through WA Import Batch form and native mapping/confirmation dialogs.

**Users:** Marketing User/Manager manage profiles/imports; scoped Agents see minimum contact context through Inbox, not the full list.

## Layout and fields

- Contact list: display name, phone, language, tags, derived consent, suppression, archived and modified date.
- Form tabs: Profile; ERPNext Source Links; Consent and Suppression; permitted Conversations.
- Evidence panel: purpose, occurrence/source/notice, actor and private evidence reference. Events are read-only; Record Consent/Withdraw opens a command dialog.
- Import form: private File upload, country default, column mapping, evidence fields, validation operation, accepted/rejected counts and private row diagnostics.

## Filters and data behaviour

Filter by tags, consent, suppression, language, source type and archived. Source selection displays ambiguous phones; require explicit choice. Import preview identifies duplicate existing contacts, invalid numbers and missing evidence separately; an import can create a profile without making it marketing-eligible.

## Actions and prerequisites

Validate Import performs no contact mutations. Confirm Import requires the exact input hash. Repeated confirmation resumes the same logical work. Record Consent enforces evidence; Withdraw acts immediately. Manager-only suppression release requires qualifying regrant evidence. Changing a phone creates a new identity, never silently transfers permission.

## UI states, access and responsive behaviour

Empty list offers import/source selection. Invalid rows remain downloadable privately; valid rows can complete with rejected-row counts. Network loss shows persisted import status. Evidence denied by permissions is omitted with an access explanation. Native tabs/controls follow form responsive behaviour.

## Interfaces and records

WA Contact, WA Tag, WA Consent Event, WA Suppression, WA Import Batch; `audiences.source_preview`, `imports.*`, `contacts.*`.

## Implementation and acceptance

Tasks: [WA-P3-001, WA-P3-002](../tasks/P3-AUDIENCES-AND-TEMPLATES.md). Scenarios: [WA-A03, WA-A04](../TESTING_AND_ACCEPTANCE.md).

- Duplicate CSV rows cannot duplicate contacts or grant events on replay.
- Backdated/replayed grants cannot clear withdrawal.
- Verify shared Customer/Contact mapping, phone ambiguity and direct REST protection of derived consent.
