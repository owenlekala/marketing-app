# API contracts

Owner: WA-R03–WA-R14. These are future whitelisted Python methods, not deployed endpoints. Storage: [data model](DATA_MODEL.md). Actor rules: [permissions](PERMISSIONS_AND_PRIVACY.md).

## Transport and shared contract

Desk calls `/api/method/tag_marketing.api.<group>.<method>`. Queries are GET; commands are POST, use Frappe authentication/CSRF and never allow Guest. The signed webhook is the only Guest boundary. Do not disable CSRF globally.

Successful methods return a value under Frappe's normal `message` envelope:

```json
{"message":{"ok":true,"data":{"operation":"synthetic-operation-id","status":"Pending"}}}
```

Expected domain errors use a shared command wrapper with the relevant HTTP status and safe envelope:

```json
{"message":{"ok":false,"error":{"code":"STALE_DOCUMENT","message":"Reload this campaign before approving.","field":"expected_modified","retryable":false,"correlation_id":"synthetic-correlation-id"}}}
```

Framework authentication/permission failures may use Frappe's standard error response; the shared UI adapter handles both without displaying tracebacks. Unexpected exceptions remain server errors with a redacted correlation ID, not false success.

- Record IDs are opaque strings. Clients cannot supply credentials, trusted company overrides, provider payloads, managed statuses or audit actors.
- Every mutation carries `request_id` (UUID) and, for existing editable records, `expected_modified` (exact Frappe revision). Same actor/method/key/arguments reuses the prior operation/result; changed arguments with the same key return `IDEMPOTENCY_CONFLICT`.
- Company is resolved from the target and WA Settings. Any supplied company filter is validated, never used as authorisation.
- List queries accept `limit` (default 25, maximum 100), a server-issued opaque `cursor`, and an allowlisted `filters` object. Stable order includes unique `name`; messages use `(creation,name)`. Return `items`, `next_cursor` and `has_more`; counts are separately permission-scoped.
- Background work returns a persisted WA Operation, not an RQ job ID. Workers recheck actor/target permissions. `operations.get(operation)` returns status, progress, safe results/errors; only requester or authorised Manager with target scope may read.
- Validate payload size, JSON schema and allowlisted fields before costly work. Never accept raw SQL, arbitrary DocType names, executable variable expressions or arbitrary callback URLs.

### Request examples

Authenticated POST to `tag_marketing.api.campaigns.approve`, using synthetic IDs and the current form revision:

```json
{
  "campaign": "WA-CAM-2026-00001",
  "snapshot_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "expected_modified": "2026-10-27 09:00:00.000000",
  "request_id": "00000000-0000-4000-8000-000000000001"
}
```

The server compares the supplied hash to its stored snapshot; this synthetic all-zero example cannot approve a real campaign. A successful response contains `data.campaign`, `data.status="Approved"` and `data.snapshot_hash` under the shared envelope.

Authenticated POST to `tag_marketing.api.inbox.send_reply`:

```json
{
  "conversation": "synthetic-conversation-id",
  "reply_type": "Text",
  "text": "Your request has been assigned to our team.",
  "expected_modified": "2026-10-27 09:00:00.000000",
  "request_id": "00000000-0000-4000-8000-000000000002"
}
```

Response data contains `message`, `operation` and `status="Queued"`; recipient/company come from the authorised conversation. Repeating this command ID must not submit another logical reply. A list response uses `data.items`, `data.next_cursor` (null at the end) and `data.has_more=false` at the final page.

## Connection commands

- `connections.validate_connection(connection, expected_modified, request_id)` — System Manager; starts credential/version/WABA validation, returns operation. Draft/Degraded/Disabled may move to Verifying; only completed evidence enables Ready.
- `connections.sync_numbers(connection, request_id)` — System Manager; returns operation; upserts provider identities without overwriting configured sender rates/team.
- `connections.sync_templates(connection, request_id)` — Manager or System Manager; returns operation; does not return credentials.
- `connections.check_webhook(connection)` — System Manager query; returns last verified receipt, subscription diagnostic and readiness checks; never claims a missing event was received.
- `connections.set_enabled(connection, enabled, expected_modified, request_id)` — System Manager; disabling blocks new sends but preserves authenticated event processing. Enabling requires fresh validation.
- `connections.send_test(connection, sending_number, contact, template, sample_values, request_id)` — System Manager with contact/template scope; explicit test confirmation, authorised opted-in contact, same-company sender. Returns operation/message, never sends implicitly during credential validation.

Credential edits use the restricted connection form; saving secrets invalidates connection readiness. Runtime diagnostic queries return masked metadata only.

Template commands: `templates.validate(template, expected_modified)` returns supported-component errors and a content hash without provider mutation. `templates.submit(template, content_hash, expected_modified, request_id)` is Manager-only and returns a persisted operation for Draft/Rejected definitions; stale content fails. `templates.sync(template, request_id)` refreshes the selected template through the same provider adapter. Template sync/submit never implies approval until Meta reports it.

## Audience and consent

- `audiences.source_preview(source_doctype, filters, selected_company, limit, cursor)` — Marketing User/Manager plus source read permissions; returns safe source identifiers, candidate phones and ambiguity reasons.
- `audiences.preview(segment, exclusions, limit, cursor)` — same marketing roles; returns eligible count, excluded counts by reason, sample contacts and preview revision. Advisory only.
- `imports.validate_batch(batch, expected_modified, request_id)` — returns operation with input hash/counts/private row-error file; no contact changes.
- `imports.confirm_batch(batch, input_hash, expected_modified, request_id)` — requires Preview Ready and unchanged file/mapping; returns resumable import operation. Grants only when independent evidence passes validation.
- `contacts.record_consent(contact, event_type, occurred_at, source, notice_version, evidence_reference, evidence_file, request_id)` — Marketing User/Manager for documented grants; Agent may record withdrawal or explicitly evidenced inbound consent within assigned scope. Returns event and effective consent state; cannot erase history.
- `contacts.set_suppression(contact, active, reason, expected_modified, request_id)` — Manager; releasing Opt Out requires qualifying newer evidence. Returns effective state and audit ID.

Normal contact/tag/segment CRUD still enforces controllers and field permissions. No caller may write derived eligibility fields directly.

## Campaign commands

- `campaigns.validate(campaign, expected_modified, request_id)` — User/Manager; Draft only; creates Building snapshot and async operation. Returns operation; result gives Ready snapshot/hash, counts and exclusions. No approval or live sending.
- `campaigns.send_test(campaign, snapshot, contact, sample_values, expected_modified, request_id)` — User/Manager; Ready snapshot and explicitly selected authorised opted-in test contact; creates one Test message tied to hash. Returns operation/message. Tests are excluded from campaign recipient denominators.
- `campaigns.request_approval(campaign, snapshot, expected_modified, request_id)` — User/Manager; Draft with Ready current snapshot, complete expiry/config and accepted matching-hash test. Returns Pending Approval and snapshot hash.
- `campaigns.approve(campaign, snapshot_hash, expected_modified, request_id)` — Manager; Pending Approval only; rechecks hash/readiness/scope and stores approver. Returns Approved.
- `campaigns.reject(campaign, reason, expected_modified, request_id)` — Manager; Pending Approval → Draft with audit reason.
- `campaigns.schedule(campaign, expected_modified, request_id)` — Manager; Approved with Scheduled start mode, future scheduled time before expiry; returns Scheduled. Start/expiry are already approved values.
- `campaigns.launch(campaign, expected_modified, request_id)` — Manager; Approved with Now mode or approved scheduled start due; enqueues dispatch and returns operation/Running. A scheduled future start cannot be bypassed by Launch.
- `campaigns.pause(campaign, reason, expected_modified, request_id)` — Manager; Scheduled/Running → Paused. Returns state and warning that already-submitted messages are unaffected.
- `campaigns.resume(campaign, expected_modified, request_id)` — Manager; Paused only, valid approval and unexpired; returns Scheduled if start is future, otherwise Running. No recipient reset or new snapshot.
- `campaigns.cancel(campaign, reason, expected_modified, request_id)` — Manager; nonterminal → Cancelled; cancels unsubmitted work. Historical sends remain.
- `campaigns.clone(campaign, request_id)` — User/Manager; returns new Draft with configuration copied but no approval, snapshot, results or test evidence.

Form saves may edit Draft fields; material changes before dispatch clear approval and require a new snapshot/test. After the first submission, material edits return `CLONE_REQUIRED`. Scheduler uses the same transition service, not an unauthorised public launch shortcut. Campaign Failed requires explicit audited repair or clone, not a silent Resume.

`messages.reconcile_unknown(message, resolution, provider_message_id, evidence_reference, expected_modified, request_id)` is Manager-only. Resolution is Accepted With Evidence, Not Submitted With Evidence, or Leave Unknown. Verify identity/evidence; an accepted resolution stores the provider ID and retains the cap reservation, a proven non-submission marks failed/released without automatic resend, and unresolved work stays Unknown. Audit every decision. Any replacement requires a new normally approved campaign or authorised agent reply, links `replacement_for`, uses a new logical key and explicitly acknowledges possible duplication. V1 has no Retry All Unknown action.

## Inbox queries and commands

- `inbox.list_conversations(filters, limit, cursor)` — Agent/Manager; assigned/team scope; returns list projection without entire message bodies.
- `inbox.get_conversation(conversation)` — scoped detail and capability flags: `can_reply_freeform`, `window_expires_at`, assignment and automation mode.
- `inbox.list_messages(conversation, limit, cursor)` — scoped, chronologically ordered pages; includes safe attachment references and event timestamps.
- `inbox.send_reply(conversation, reply_type, text, template, variables, media_file, reply_to_message, expected_modified, request_id)` — scoped Agent/Manager; `reply_type` Text, Media or Template. Resolves recipient from conversation. Checks window at enqueue and immediately before submission; expired free-form work fails with `WINDOW_CLOSED`, without automatic template substitution. Returns message/operation and transfers mode to Human atomically.
- `inbox.assign(conversation, assigned_to, team, expected_modified, request_id)` — Manager or scoped team Agent; targets must have WhatsApp Agent role and matching company/team authorisation. Returns updated conversation.
- `inbox.add_note(conversation, note, request_id)` — scoped Agent/Manager; append-only internal note; never provider traffic.
- `inbox.set_status(conversation, status, expected_modified, request_id)` — Open or Resolved only.
- `inbox.set_automation_mode(conversation, mode, expected_modified, request_id)` — Automatic requires explicit resume and currently active eligible automation; Human suppresses queued automatic replies before submission.
- `inbox.mark_read(conversation, last_read_message, request_id)` — advances current user's cursor only.
- `media.download(file)` — authenticated access check through owning message/evidence/import; redirects/streams only an authorised private file. Not a public sharing URL.

Allow one attachment per outbound message in v1. Reply sends are queued; the composer shows server state on reload rather than pretending network success means Delivered.

## Automations and reports

- `automations.validate(automation, expected_modified)` — Manager; returns errors, step preview and definition hash without sending or publishing.
- `automations.simulate(automation, sample_context)` — Manager; synthetic bounded context; returns branch/action trace with no provider traffic, CRM mutations or real consent changes.
- `automations.publish(automation, definition_hash, expected_modified, request_id)` — Manager; validates run-as user, purpose, forward-only graph and ready sender/templates; creates immutable version and Active status.
- `automations.pause(automation, expected_modified, request_id)` / `resume(...)` — Manager; block/unblock claims with live readiness checks. Do not migrate existing runs to new versions.
- `reports.summary(filters)` — Analyst/Manager aggregate projection; no raw messages or credentials. Native Script Reports apply the same service filters.
- `reports.export(report_name, filters, request_id)` — Manager with report/source export permission; returns operation producing a private File. Analyst has no raw-contact export by default.
- `settings.health()` — Manager/System Manager; safe readiness and queue/scheduler/callback/policy checks, with unavailable checks explicitly failing readiness.
- `settings.set_sending_enabled(enabled, scope, expected_modified, request_id)` — System Manager; scope Pilot or Live. Pilot requires readiness plus an explicit 1–20 opted-in-contact allowlist; Live additionally requires reviewed pilot evidence. Disabling always wins. Audit and read immediately before new submission.
- `settings.record_pilot_result(campaign, evidence_reference, expected_modified, request_id)` — Manager; verifies the campaign was restricted to Pilot recipients and records reviewed delivery, withdrawal and handover evidence. This does not itself enable Live.
- `privacy.preview_cleanup(categories, cutoff)` — System Manager; returns policy-derived counts and legal-hold exclusions, no deletion. Caller cannot shorten configured retention through cutoff.
- `privacy.run_cleanup(preview_hash, request_id)` — System Manager; rechecks current policy/holds and returns operation. If scope changed, require a new preview.
- `privacy.request_subject_action(contact, action, authority_reference, request_id)` — System Manager with current contact scope; action Export or Erase; records authority and returns private operation results. Apply policy/holds and suppression minimisation; no unrestricted public erasure endpoint.

Rate card draft/admin commands use the restricted native WA Rate Card form; activation/retirement is a Manager service with current document revision, effective-period validation and audit. Generic CRUD cannot activate an unreviewed card. Missing matching currency/rate makes an estimate unavailable; a configured estimate guard blocks approval/sending rather than inventing a rate.

## Webhook boundary

Endpoint: `/api/method/tag_marketing.api.webhooks.receive?integration=<public_id>`.

- GET accepts Meta `hub.mode`, `hub.verify_token`, `hub.challenge`; constant-time token match and supported subscription mode return raw challenge text, HTTP 200. Invalid token/mode returns 403. Never echo secrets.
- POST verifies `X-Hub-Signature-256` using the selected connection's app secret over the exact raw bytes before trusting JSON. Reject invalid/unknown routing with 401/403; enforce body bound before parsing. Validate WABA/number ownership after verification.
- Commit WA Webhook Event and return 200 only after durable success. Persistence failure returns 503, allowing provider retry. Valid duplicate receipt returns 200. Unknown authenticated event types are stored as processed/unsupported diagnostics rather than crashing the entire envelope.
- GET verification does not prove POST delivery, credentials, policy readiness or subscription permissions.

No browser login is required for this boundary. Verify CSRF exemption is narrowly implemented using the framework's supported integration mechanism; retain signature checks for every POST.

## Error catalogue

- 400: `INVALID_INPUT`, `INVALID_FILTER`, `INVALID_PHONE`, `INVALID_STEP`, `INVALID_MEDIA`.
- 401/403: framework auth failures, `SOURCE_ACCESS_DENIED`, `COMPANY_MISMATCH`, `INVALID_SIGNATURE`.
- 404: `NOT_FOUND` without leaking inaccessible identities.
- 409: `STALE_DOCUMENT`, `IDEMPOTENCY_CONFLICT`, `INVALID_STATE`, `APPROVAL_STALE`, `CLONE_REQUIRED`.
- 422: `CONSENT_REQUIRED`, `SUPPRESSED`, `TEMPLATE_NOT_APPROVED`, `WINDOW_CLOSED`, `READINESS_FAILED`, `AUDIENCE_TOO_LARGE`, `CAMPAIGN_EXPIRED`.
- 429: `LOCAL_RATE_LIMIT`; due work is deferred, not presented as provider delivery failure.
- 502/503: `PROVIDER_UNAVAILABLE`, `PERSISTENCE_UNAVAILABLE`; uncertain submissions become Unknown instead of automatic retries.

Provider-specific errors are mapped by versioned contract fixtures, not substring matching. Validate contracts through [acceptance tests](TESTING_AND_ACCEPTANCE.md).
