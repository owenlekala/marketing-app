# Operations and release

Owner: WA-R15–WA-R17. No deployment is authorised by this documentation change. Initial implementation steps are in [framework/setup](FRAMEWORK_AND_SETUP.md).

## Service layout

Production uses an immutable custom image containing the tested Frappe/ERPNext revisions, `tag_marketing`, pinned dependencies and built assets. Run web, supported realtime process, scheduler, Redis, MariaDB and a dedicated `marketing` queue worker. Keep payroll workers separate. Record image digests, application commits, database version and explicit API version for every release.

Start with one marketing worker and bounded claims; scale after measuring queue age and Meta limits. Configure worker health and scheduler heartbeat checks. Treat raw provider callbacks and files as sensitive data. TLS terminates at the approved reverse proxy; only the narrow callback is publicly unauthenticated and it always validates signatures.

Do not copy the existing Compose Node websocket command blindly: inspect the installed checkout's realtime entrypoint. Development uses `bench start`; production uses supervised/container services, developer mode off and test hooks disabled.

## Before deploy

- Confirm all relevant task evidence and acceptance scenarios pass on the selected immutable image.
- Back up database, private/public files and encryption-key recovery material securely; verify restore access without printing secrets.
- Disable new marketing sending and drain or safely classify existing claims. Keep inbound intake available where possible; use non-200 callbacks if persistence is unavailable.
- Deploy compatible app images, run `bench --site <site> migrate`, build/ship assets as part of the image, clear caches as needed and restart workers/services on the same revision.
- Confirm schema, queues, scheduler, realtime, private-file access and webhook processing before re-enabling. Run an authorised synthetic/pilot check; do not auto-send to real audiences as a health probe.
- Roll back application images only when schema-compatible. For incompatible schema rollback use a reviewed restore/reconciliation procedure, not an untested reverse migration.

## Monitoring and alerts

Expose safe operational metrics: due/oldest outbox age, Ready webhook/source event age, unknown/failed attempts, operation heartbeat, scheduler lag, worker heartbeat, provider throttles, authentication failures and restricted number/template states. Track database query/memory usage during campaigns.

Initial local alerts: no scheduler/worker heartbeat for 3 minutes, oldest due work over 5 minutes, any new Unknown outcome, authentication failure, or persistent webhook failure. These are operator defaults, adjustable through documented configuration; they are not Meta delivery guarantees. Avoid message text/phone numbers in alert payloads. No external messages are sent by this documentation work.

## Incident runbooks

### Provider/authentication failure

Disable affected connection/sender submissions, preserve pending records and valid inbound receipt processing, inspect safe correlation/error codes, rotate/fix credentials and revalidate. Retry only explicitly safe rejected work. Leave uncertain attempts Unknown until reconciled.

### Queue/Redis outage

Keep durable database receipts. Repair service, verify heartbeats, run recovery scan and inspect claim leases. Pre-submission claims may be reclaimed; post-Submitting work is reconciled as Unknown. Do not reset the entire outbox.

### Opt-out or template incident

Activate company suppression or pause affected template/campaigns, audit pending/in-flight timing and stop new work. Accepted sends cannot be recalled. Verify no alternate sender bypasses suppression. Updated template content requires new approval.

### Unknown submission

Review attempt and provider correlation evidence, late events and safe trace references. Manager records resolution/evidence. If an unresolved replacement is necessary, create a separate explicitly confirmed delivery with duplicate-risk disclosure; never mutate history into an apparently safe retry.

### Restore

Restore into isolated services with sending disabled before starting workers. Restore secrets/encryption-key access securely, confirm schema/image compatibility and private files, then reconcile provider-accepted messages and potentially stale outbox/source triggers. Mark ambiguous post-boundary items Unknown. Require an operator-reviewed reconciliation before enabling sends.

### Retention or access incident

Stop affected cleanup/export operations, retain audit evidence under legal hold and restrict download access. Verify the owning record permissions and cached UI/realtime behaviour. Correct the service and re-run privacy acceptance; do not resolve a leak by hiding a button alone.

## Pilot and production gates

1. All relevant [acceptance checks](TESTING_AND_ACCEPTANCE.md) pass, including capacity, permission, migration and restore evidence.
2. Configure company, privacy notice, retention periods, supported API version, rates, numbers, verified webhook, template approvals and operator ownership.
3. System Manager sets the explicit 1–20-contact pilot allowlist while sending is disabled, then enables Pilot scope after offline readiness passes. Run a limited approved campaign to those opted-in authorised recipients; verify delivery evidence, STOP handling, inbox reply and handover. Record recipient approval without placing personal data in public docs.
4. Manager records reviewed pilot outcomes through the pilot-result command; System Manager selects Live scope through the audited readiness command. Increase audience size gradually up to the v1 ceiling while observing quality and queue metrics. A failed pilot leaves Live unavailable; disable Pilot until corrected where needed.

Application tasks remain incomplete until evidence exists. Documentation publication, mock fixtures or credential validation alone cannot enable general production use.
