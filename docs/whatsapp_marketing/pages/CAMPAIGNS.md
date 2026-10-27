# Campaigns

Page contract: **WA-UI-CAMPAIGNS**. Sidebar label: **Campaigns**. [Navigation index](README.md).

## Purpose and implementation

Native WA Campaign List/Form with linked read-only snapshot/recipient records.

**Users:** Marketing User prepares/tests/requests approval; Manager approves, schedules, launches and controls dispatch.

## Layout and fields

- List: name, status, sender, schedule, expiry, recipients, dispatch progress and unresolved count.
- Details tab: name, Marketing purpose, sender, optional ERPNext Campaign.
- Audience tab: segment, exclusions, preview, snapshot version/hash, eligible count and reason counts.
- Message tab: approved template/language, variable mappings, private media and labelled preview.
- Schedule tab: Now/Scheduled start mode, UTC-backed start/expiry, timezone/offset, effective sending rules and estimate guard.
- Review tab: frozen summary, source scope, same-hash test result, approval and audit history.
- Results tab: recipient dispatch, message evidence, exact/inferred replies, excluded/failed/unknown drill-down.

## Filters and data behaviour

Filters: state, sender, scheduled interval and campaign name. Use native indicators for defined states. Recipient detail is paginated; no 10,000-row embedded child grid. Show dispatch completion separately from final provider delivery.

## Actions and prerequisites

Actions follow API lifecycle: Validate, Send Test, Request Approval, Approve/Reject, Schedule/Launch, Pause/Resume, Cancel and Clone. Require expected_modified and snapshot hash. Material edits invalidate approval before dispatch; after submission require Clone. A future approved start cannot be bypassed by Launch.

## UI states, access and responsive behaviour

No audience or zero eligible recipients blocks request approval with reasons. Loading snapshot shows Building, not Ready. Pause/cancel warns that submitted messages cannot be recalled. Unknown outcomes link to diagnostics with no generic Retry All. Native form stacks; review summary remains readable without a separate visual theme.

## Interfaces and records

WA Campaign, WA Campaign Snapshot, WA Campaign Recipient, WA Message, WA Operation; `campaigns.*`.

## Implementation and acceptance

Tasks: [WA-P4-001, WA-P4-002, WA-P4-003, WA-P4-004](../tasks/P4-CAMPAIGNS-AND-DISPATCH.md). Scenarios: [WA-A07, WA-A08, WA-A10, WA-A16](../TESTING_AND_ACCEPTANCE.md).

- Manager approves exactly the tested frozen hash and selected audience.
- Withdrawal after approval skips pending delivery without adding replacement contacts.
- Pausing/resuming/reload preserve progress; late callbacks update results after Completed.
