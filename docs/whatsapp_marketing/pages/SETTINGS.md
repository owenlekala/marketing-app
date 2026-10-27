# Settings

Page contract: **WA-UI-SETTINGS**. Sidebar label: **Settings**. [Navigation index](README.md).

## Purpose and implementation

Native Single WA Settings form; restricted technical DocTypes accessible through manager diagnostics, not extra public sidebar entries.

**Users:** System Manager edits settings; Manager sees safe effective sending policies and health without credentials.

## Layout and fields

- Business: selected company, timezone and privacy notice.
- Sending: hours, rolling cap, company rate, campaign-size ceiling and global sending switch.
- Sending scope: Pilot or Live; explicit Pilot allowlist, reviewed evidence and live-readiness result.
- Source policy: enabled ERPNext source types and mapping explanation.
- Retention: explicit positive raw/message/media/consent periods, policy reference and legal hold process.
- Readiness: worker/scheduler/webhook/pilot checks and safe links to outstanding setup.
- Diagnostics links: authorised Operations, failed events, unknown sends and audit history.

## Filters and data behaviour

Show effective defaults from product requirements and explain that rates are local limits, not Meta entitlements. Company becomes immutable after live records exist. Campaigns retain approved policy; apply stricter live limits, and require renewed approval to use relaxed policy values. Pilot allowlist is editable only while sending is disabled.

## Actions and prerequisites

Save validates types/policy. Enable Sending uses the dedicated scope/readiness-checked API; Live requires reviewed pilot evidence, while Pilot restricts recipients to the explicit allowlist. Disable Sending is an immediate audited emergency action, retaining inbound processing. Retention/erasure executions run as explicit restricted operations with preview/hold checks, never on a form field change alone.

## UI states, access and responsive behaviour

Incomplete configuration shows actionable checklist and leaves sending disabled. Unavailable health checks do not count as passed. Pending cleanup displays progress and affected category, without personal payloads. Use native sections and confirmatory dialogs for irreversible privacy actions; forms inherit theme/responsiveness.

## Interfaces and records

WA Settings, WA Audit Event, WA Operation; `settings.set_sending_enabled`, safe health queries.

## Implementation and acceptance

Tasks: [WA-P1-001, WA-P7-002](../tasks/P7-REPORTING-AND-RELEASE.md). Scenarios: [WA-A01, WA-A13, WA-A17](../TESTING_AND_ACCEPTANCE.md).

- Missing retention/rate/privacy settings block live enablement.
- Emergency disable stops new submission claims while valid callbacks continue processing.
- Retention respects holds and suppression identity without exposing erased conversation content.
