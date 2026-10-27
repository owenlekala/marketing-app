# Architecture decisions

[ADR-001](ADR-001-APP-AND-DESIGN-BASELINE.md) records the accepted baseline. Requirement ownership remains in [product requirements](../PRODUCT_REQUIREMENTS.md).

Create a new `ADR-NNN-<SUBJECT>.md` before implementing a change to app boundaries, provider, UI approach, consent policy, approval invariants, retry semantics, data ownership or v1 scope.

Each ADR includes status (Proposed, Accepted, Superseded), date, context, affected requirement/task IDs, options considered, chosen decision, migration/compatibility impact, test changes and links to superseded records. Retain the old record and mark it Superseded when replaced.

Routine implementation details that preserve contracts do not need an ADR. Update their owning specification and task evidence. A proposal is not an accepted scope change: record the user's decision for material product changes. Do not introduce an approval pause for every ordinary coding choice.
