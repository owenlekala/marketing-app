# Instructions for this documentation subtree

- Read [README](README.md) and [implementation rules](IMPLEMENTATION_RULES.md) before changing specifications.
- Preserve the user's clean architecture and production-readiness requirements.
- Keep scope/defaults in [product requirements](PRODUCT_REQUIREMENTS.md), fields in [data model](DATA_MODEL.md), and wire contracts in [API contracts](API_CONTRACTS.md).
- Update affected diagrams, task references and acceptance checks when behaviour changes; link to the owning definition instead of copying its prose.
- Keep shared completion guidance in tasks/README.md and shared page guidance in pages/README.md/UI_DESIGN_SYSTEM.md. Task checkboxes belong only to phase task files; evidence belongs to PROGRESS.md.
- Record architectural changes in [decisions](decisions/README.md); never silently replace an accepted decision.
- Preserve requirement IDs, task IDs and acceptance IDs. Add IDs rather than repurposing existing ones.
- Use relative links, synthetic examples, translatable UI terminology and Markdown/Mermaid.
- Separate inspected source facts from design choices and unverified runtime assumptions.
- Do not mark application tasks complete without recorded execution evidence.
- Validate links, task dependencies, traceability and terminology after edits.
- These instructions govern this subtree only. The repository-level [AGENTS.md](../../AGENTS.md) bridges these rules to application code; this nested file does not govern sibling repositories.
