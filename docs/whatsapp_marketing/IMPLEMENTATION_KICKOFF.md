# Implementation kickoff

Use this instruction when starting an implementation session:

> Implement the first unblocked unchecked task in `docs/whatsapp_marketing/tasks/README.md`. Read the handbook, product requirements, implementation rules, framework/setup, progress and the task's owning specifications first. Preserve native ERPNext Desk design and clean architecture. Recheck current local instructions and source/runtime versions. Implement a complete vertical slice, including relevant permissions, failures, tests and UI evidence. Do not modify framework/payroll code or widen v1 scope. Record actual evidence and remaining blockers; never mark a task complete on mock/partial verification. If architecture must change, record the decision and update linked specs before the affected implementation.

## First session

1. Begin [WA-P0-001](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md#wa-p0-001), not connection or UI scaffolding based on an assumed runtime.
2. Confirm the source versions and whether a Bench/site now exists. The documentation-time runtime state is unverified.
3. Follow WA-P0-002 to establish the disposable environment; use explicit paths/site names and avoid secrets in command output.
4. WA-P0-003 creates the future app repository and its app-level AGENTS.md bridge. Keep this handbook in the app repository under `docs/whatsapp_marketing` as the canonical version; update its local source links to the checked-out workspace layout and leave only a pointer at the previous location if needed. Move the canonical handbook; do not retain a synchronised or independently editable copy.
5. Record the canonical location and commit in progress before application work continues.

## Every session

Read [progress](PROGRESS.md), inspect uncommitted changes, choose a dependency-ready task and state its acceptance target. Use the actual implemented APIs and contracts; do not invent alternate schemas in UI code. Finish by recording commands/results, relevant screenshots/commits and any unfinished checks. Return a precise outcome and limitations to the user.

The documentation-folder [AGENTS.md](AGENTS.md) has subtree scope only. The repository-level [instruction bridge](../../AGENTS.md) supplies automatic code-work discoverability.
