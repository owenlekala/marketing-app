# Native UI design system

Requirements: WA-R02, WA-R10, WA-R17. Native examples and files are linked in [references](REFERENCES.md). This defines implementation behaviour; live screenshots have not yet been collected.

## Shell and navigation

Use an owned TAG Marketing app tile, Dock entry and **WhatsApp Marketing** Sidebar. Keep the installed ERPNext navbar, search, user menu, breadcrumbs and page actions. Stable sidebar destinations are specified in [page index](pages/README.md). Respect role visibility, but never treat a hidden link as authorisation.

Inspect this checkout's Sidebar/Dock implementation before registering routes. Use framework-generated form/list/report routes; do not assume old `/app` paths behave identically in its shell. For the custom page use the stable Page name `wa-inbox`; read-only journey preview lives inside the WA Automation form, not a new standalone application.

## Component decisions

- Configuration and business records use native DocType forms, tabs, sections, columns and field descriptions.
- Collections use native List views with standard filtering, sorting, paging, saved filters and authorised bulk actions.
- Reports use native Script Reports with server-side permission filters. Large exports run as persisted operations and produce private files.
- Overview uses native Workspace, Number Card and Dashboard Chart records. Prefer permission-checked custom metric methods over unrestricted aggregates.
- Dialogs use `frappe.ui.Dialog`; inputs use native controls. Custom Page header/actions use `frappe.ui.make_app_page` and supported Page methods.
- Feedback uses native alerts, indicators, validation messages and progress UI. Long actions return operation IDs and remain recoverable on page reload.
- Inbox panels and message bubbles are custom content within the native shell. Use standard buttons, controls, badges and a labelled composer.
- Automation is a standard form with ordered steps and controlled forward targets; a read-only preview visualises the saved draft. No drag-and-drop dependency.

## Tokens and assets

Use actual tokens from the inspected styles, including `--fg-color`, `--text-color`, `--text-muted`, `--control-bg`, `--border-color`, `--radius` and `--radius-lg` where defined. Read spacing/typography/shadow definitions instead of inventing a parallel scale. Match adjacent ERPNext controls in computed size and focus behaviour.

Scope custom selectors under `.tag-marketing`. Use a scoped bundle and supported `app_include_css`/Page loading as appropriate. Avoid body-level selectors, hardcoded theme backgrounds, overriding core controls, remote fonts, and a second CSS framework. Reuse existing icon symbols; add an owned sprite via `app_include_icons` only for missing module imagery. Never use colour as the sole status signal.

## Interaction rules

- Exactly one principal action for the current form state; destructive/lifecycle actions identify their consequences and expected document revision.
- Approval review displays resolved counts, excluded reasons, sender, language, expiry, timezone and representative variable previews before the manager acts.
- Distinguish sample previews from frozen recipient values. Escape provider/customer content; do not render inbound HTML.
- Disable duplicate submissions while pending, but use server idempotency and optimistic concurrency as the real protection.
- On stale records refetch and show what needs review; do not discard unsaved edits without notice.
- Loading skeletons reserve layout. Empty states provide a permitted next action. Error states retain entered data and show a retry only when safe.
- Network failure after reply/send shows Pending or Unknown from the server; do not invite an unverified resend.

## Accessibility and responsive behaviour

Support keyboard navigation, visible focus, labelled controls, readable errors associated with fields, sufficient contrast and live progress announcements without announcing each status callback. Focus returns to the initiating control after dialogs close.

Reference viewport checks: 1440px desktop, 1024px tablet and 390px phone. The inbox becomes one panel at a time on narrow screens; maintain conversation state and back navigation. Native forms follow the framework grid. Avoid horizontal page overflow; large technical tables may scroll inside their container.

## Visual acceptance checklist

- [ ] Capture reference ERPNext CRM, Lead/Customer form, List, dialog and report in light/dark themes.
- [ ] Capture matching marketing views using the same user, theme, browser zoom and viewport.
- [ ] Compare header height, action alignment, typography, field labels, grid gaps, panel borders, indicators and focus.
- [ ] Confirm native widget interactions, filter drill-down and permission-aware metrics.
- [ ] Check keyboard flow and narrow layouts, including loading/empty/error states.
- [ ] Attach evidence paths and review findings to WA-P1-004 and each feature's UI task; fix material mismatches before completion.

No marketing page may claim visual parity solely because Bootstrap classes were reused. Verify the rendered result. The implementation gate is [WA-A02](TESTING_AND_ACCEPTANCE.md).
