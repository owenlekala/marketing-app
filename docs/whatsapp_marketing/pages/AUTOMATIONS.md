# Automations

Page contract: **WA-UI-AUTOMATIONS**. Sidebar label: **Automations**. [Navigation index](README.md).

## Purpose and implementation

Native WA Automation List/Form with ordered-step controls and read-only journey preview; no drag-and-drop app.

**Users:** Marketing Manager edits/publishes/pauses; run diagnostics follow company/content permissions.

## Layout and fields

- Definition tab: name, purpose, sender, run-as user and one allowlisted trigger.
- Steps tab: stable step IDs, native action selectors, condition/parameter controls, next/otherwise forward targets; up to 100 steps.
- Preview tab: escaped read-only graph generated from the same saved definition, validation errors linked to step controls.
- Publication tab: current published version/hash and draft changes; existing runs retain their version.
- Executions tab: paginated runs with status/current step/due time/error and permitted message links.

## Filters and data behaviour

Filters: status, purpose and sender. Trigger/action schema comes from the automation flow and server validator, not free-form expressions. Users see whether a preview is Draft or Published. Do not let a stale preview hash publish a different definition.

## Actions and prerequisites

Validate gives structured errors. Simulate accepts synthetic context and returns a non-mutating trace. Publish creates an immutable version after policy/permission checks. Pause blocks new claims; Resume rechecks readiness. Human handover is managed from Inbox, not overridden by publishing a new version.

## UI states, access and responsive behaviour

No definition offers a simple welcome/keyword example as an unsaved draft, never an active automation. Invalid forward target or cycle identifies the step. Waiting Human is explained separately from Failed. Controls and preview stack responsively; status remains meaningful without colour.

## Interfaces and records

WA Automation, WA Automation Version, WA Automation Run, WA Source Event; `automations.*`.

## Implementation and acceptance

Tasks: [WA-P6-001, WA-P6-002, WA-P6-003, WA-P6-004](../tasks/P6-AUTOMATIONS.md). Scenarios: [WA-A11, WA-A10](../TESTING_AND_ACCEPTANCE.md).

- Invalid/cyclic or arbitrary-code definitions cannot publish through UI or REST.
- New versions do not change in-progress waits or steps.
- Simulation makes no provider/source/consent mutations; restarted workers resume persisted waits once.
