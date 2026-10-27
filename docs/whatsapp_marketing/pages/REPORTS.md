# Reports

Page contract: **WA-UI-REPORTS**. Sidebar label: **Reports**. [Navigation index](README.md).

## Purpose and implementation

Sidebar section linking native Script Reports; no separate reporting SPA.

**Users:** Analyst/Manager aggregate views; raw delivery/contact detail and exports require explicit Manager/export/source scope.

## Layout and fields

- WA Campaign Performance: snapshot count, skipped/cancelled, accepted, sent, delivered, read, failed, unknown and exact/inferred replies.
- WA Recipient Outcomes: paginated diagnostic rows with current state/reason/provider trace for permitted managers.
- WA Consent and Suppression: reason/source trends; evidence details restricted.
- WA Automation Executions and WA Inbox Workload: run states, waits, assignments and response-time distributions.
- WA Connection Health and WA Cost Estimates: account diagnostics, dated rate/currency assumptions and estimate-versus-provider distinction.

## Filters and data behaviour

Default last 30 days; explicit company, sender, campaign, state and timestamp basis. Campaign recipient denominator excludes tests; provider states are cumulative evidence, not mutually exclusive pie slices. Delivery rate = delivered unique campaign messages / accepted unique campaign messages; show denominator and missing data. Exact replies count distinct contacts with provider reply context; inferred replies separate. First response = first human outbound submission after first inbound in an open/reopened conversation; show pending separately.

## Actions and prerequisites

Run/Refresh use permission-aware query services. Export is a persisted operation producing a private File and neutralised CSV cells; Analyst has no raw export by default. Metric drill-down retains filters and access scope. Rates are explicit dated estimate inputs; no fabricated price or ROI.

Managers maintain WA Rate Card through the native configuration link defined in the [sidebar hierarchy](README.md#native-sidebar-hierarchy); currency, effective period, market/category rows and official source are required. Active cards are immutable and cannot overlap for the same pricing scope. Missing matching currency produces unavailable estimates; no implicit exchange-rate assumption.

## UI states, access and responsive behaviour

No data shows empty results plus active filters. Missing read receipts and unknown rate cards show unavailable, never zero certainty. Slow exports show progress/reload recovery. Native report controls support theme/keyboard and internal horizontal scrolling without page overflow.

## Interfaces and records

WA Campaign/Recipient, WA Message/Event, WA Automation Run, WA Conversation, WA Operation; `reports.summary`, `reports.export`.

## Implementation and acceptance

Tasks: [WA-P7-001](../tasks/P7-REPORTING-AND-RELEASE.md). Scenarios: [WA-A12, WA-A03, WA-A16](../TESTING_AND_ACCEPTANCE.md).

- Report totals reconcile to underlying deduplicated messages for the same actor/filters.
- Analyst cannot drill into message bodies or retrieve a manager export.
- Estimates show effective date/currency and do not claim actual provider invoice totals.
