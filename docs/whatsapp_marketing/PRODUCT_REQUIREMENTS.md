# Product requirements

Status: accepted design baseline, 27 October 2026. See [ADR-001](decisions/ADR-001-APP-AND-DESIGN-BASELINE.md).

## Scope and success

A marketer connects an official WhatsApp number, selects a permitted audience, prepares and tests a template campaign, obtains manager approval, schedules sending, monitors outcomes and handles replies without leaving Frappe Desk. Operators can explain exclusions and recover interrupted work without silently duplicating submissions.

V1 is one business/company per site with multiple numbers, company-scoped records, ERPNext and CSV sources, approved campaigns, native step automations, an inbox, reporting and production operations. Supporting more companies is a future capability, not a reason to omit company boundaries now.

Exclude AI replies, other channels, client self-service Meta Embedded Signup, unofficial QR/session gateways, n8n integration, arbitrary code steps, looping journeys, drag-and-drop design, general link tracking, A/B testing and revenue attribution.

## Requirement register

- **WA-R01 — Foundation:** separate `tag_marketing` app; Frappe/ERPNext v16; no payroll dependency; idempotent installation and migrations.
- **WA-R02 — Native UI:** ERPNext-consistent Dock, Sidebar, workspace, forms, lists, reports, theme and accessible custom Desk content.
- **WA-R03 — Connections:** protected Meta credentials; explicit Graph API version; multiple numbers; webhook/test readiness and template synchronisation.
- **WA-R04 — Audiences:** permission-aware ERPNext sources and CSV imports; company mapping, phone selection, normalisation, deduplication and explainable segments.
- **WA-R05 — Consent:** append-only opt-in/withdrawal evidence; company-wide marketing suppression; consent rechecked before sending; imports cannot restore withdrawn permission.
- **WA-R06 — Templates:** sync and submit supported templates; approved category/language/components; private media; Meta remains approval authority.
- **WA-R07 — Campaigns:** editable draft, audience/content snapshot, test evidence, manager approval, scheduling, expiry and controlled lifecycle actions.
- **WA-R08 — Dispatch:** durable outbox, claim leases, sending limits, recoverable retries, explicit unknown outcomes and accurate delivery reconciliation.
- **WA-R09 — Inbound:** authenticated webhooks, durable acknowledgement, duplicate handling, replies and opt-outs processed before ordinary automations.
- **WA-R10 — Inbox:** searchable/paginated team conversations, assignment, internal notes, replies, private attachments, window controls and handover.
- **WA-R11 — Automations:** native ordered-step editor, allowlisted triggers/conditions/actions, forward branches, published versions, durable waits and human handover.
- **WA-R12 — CRM events:** Lead/Customer creation and Sales Order submission feed controlled, deduplicated events after commit; CRM membership never grants consent.
- **WA-R13 — Access/privacy:** least-privilege roles, company/assignment boundaries, protected files/exports/realtime, configurable retention and auditability.
- **WA-R14 — Reporting:** documented denominators, accepted/sent/delivered/read distinctions, reply attribution, cost estimates and operational diagnostics.
- **WA-R15 — Operations:** dedicated queues, emergency switch, alerts, upgrades, restore reconciliation and pilot gates.
- **WA-R16 — Capacity:** qualify 50,000 contacts and 10,000 campaign recipients with bounded queries/memory while keeping the inbox usable.
- **WA-R17 — Quality:** unit, integration, permission, UI, failure-injection, migration and release evidence.
- **WA-R18 — Governance:** linked specifications, stable IDs, ADRs, checked task dependencies and truthful progress.

## Chosen defaults

- Identity: app `tag_marketing`; title **TAG Marketing**; module/sidebar **WhatsApp Marketing**.
- Dependencies: initially match inspected Frappe 16.53.0 and ERPNext 16.52.1; target `<17`. Do not substitute similarly versioned upstream code without compatibility checks.
- English labels wrapped in translation functions. Company timezone starts at `Africa/Johannesburg`.
- Marketing sending hours: 09:00 inclusive to 17:00 exclusive in contact timezone, otherwise company timezone; all days. Outside hours defer, subject to expiry. Transactional/support replies are not governed by marketing hours.
- Marketing cap: one submission reservation per company/contact per rolling 24 hours across campaigns and automations. Reserve atomically; an accepted or unknown attempt retains the reservation. Explicitly rejected attempts release it.
- Capabilities: 50,000 contacts; reject campaign snapshots above 10,000 eligible unique contacts in v1 with an actionable error.
- Scheduling requires an explicit expiry later than start. Store instants in UTC; display configured timezone and UTC offset.
- A Marketing Manager approves and launches; the creator may also be that manager. Every campaign needs approval; material edits invalidate it.
- Default account/number and company/number message rates are conservative configurable limits, never assertions of Meta entitlement. Require an administrator to enter limits and a supported Graph API version before live enablement.
- Marketing requires recorded affirmative consent. No automatic existing-customer exception. Inbound support responses are evaluated separately from marketing permission.
- Retention periods, privacy notice, sending limits and credential configuration require explicit administrator setup before live enablement. No invented legal retention period.
- Sending starts disabled with scope **Pilot**. Pilot enablement requires offline readiness and an explicit allowlist of 1–20 opted-in contacts; every campaign/automation submission remains restricted to that list. **Live** scope additionally requires reviewed pilot evidence. Explicit authorised Test commands use their own restricted path and do not enable ordinary campaigns.

## Glossary

- **Company:** responsible business associated with every marketing record.
- **Connection:** one Meta app/WABA integration and its protected secrets; **number:** a sender under that connection.
- **Contact:** company-specific messaging identity; **source link:** an optional authorised ERPNext reference.
- **Eligibility:** current consent, suppression, addressing, readiness and policy checks; not proof of eventual delivery.
- **Snapshot:** frozen audience, message variables and campaign configuration reviewed for approval.
- **Accepted:** Meta returned a provider message ID; **Sent/Delivered/Read:** subsequent provider status evidence.
- **Unknown:** submission may have reached Meta, but acceptance was not recorded reliably.
- **Completed campaign:** dispatch finished; delivery/read callbacks may still arrive.
- **Handover:** human control of a conversation; automation sending is suspended for that conversation.
- **Job:** persisted `WA Operation` for operator-visible background work; an RQ job is only execution transport.
- **Published version:** immutable automation definition used by existing runs after draft changes.

Find coverage in [traceability](TRACEABILITY.md). Fields and transitions are defined in [data model](DATA_MODEL.md); provider processing is defined in [reliability](MESSAGING_AND_RELIABILITY.md).
