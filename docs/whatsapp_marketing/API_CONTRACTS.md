# API contracts

Owner: WA-R03–WA-R14. These are target contracts; the foundation sections identify currently implemented read-only interfaces. Feature commands remain unavailable until their owning tasks pass. Storage: [data model](DATA_MODEL.md). Actor rules: [permissions](PERMISSIONS_AND_PRIVACY.md).

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

## Operation progress foundation

`operations.get(operation)` is an authenticated GET query. It returns the shared envelope with `data.operation`, `status`, `progress_percent` (0..100), UTC `heartbeat_at`, `result`, `result_file` and `error`. Pending/Running are nonterminal; Succeeded/Failed/Cancelled are terminal. A Failed operation is a successful progress read with a generic `OPERATION_FAILED` diagnostic, not an HTTP success for the underlying command.

Recheck native operation read capability, configured company and User Permissions, requester or Marketing Manager status, then the current target's company and operation-specific target permission. Missing, revoked, cross-company and unsupported targets all return `NOT_FOUND` (404). P2 registers `connections.validate_connection`, `connections.sync_numbers`, `connections.sync_templates` and `connections.set_enabled`, each targeting an existing WA Connection. A Marketing Manager can read progress only for template-sync operations without gaining generic WA Connection read access. Other feature tasks must register their exact operation kind and target policy when implementing the producer; unregistered/targetless jobs fail closed.

P2 may return only `{"validated":true}`, `{"enabled":true|false}` or `{"synced_count":N}` for its registered connection operations, and always returns `result_file=null`. Raw result_json, request hashes, actor identifiers, provider diagnostics and attachments are never serialized. Generic WA Operation List/REST reads and all writes remain closed. Progress retrieval does not enqueue, retry or mutate work.

The shared server boundary maps registered domain errors to safe translated envelopes and UUID correlation IDs; HTTP status mapping stays in the API adapter, outside the domain policy. Native ValidationError within this boundary becomes a redacted INVALID_INPUT (400), with no original message log. Unexpected errors log only correlation ID and exception class, and return INTERNAL_ERROR (500) without exception text/arguments/tracebacks. A mutating boundary rolls back to its own savepoint on failure; it never commits and does not replace command-specific authorization, optimistic revision checks or durable idempotency. `require_revision` requires the exact stored revision and reports INVALID_INPUT or STALE_DOCUMENT. Authentication/permission exceptions retain Frappe's native boundary.

## Connection setup interfaces

All methods require an authenticated System User, app role, configured-company scope and CSRF for POST. Mutations return a durable operation ID; provider reads run only in the `marketing` queue after commit. `request_id` is 8–128 characters from `[A-Za-z0-9._:-]`; repeating the same actor, operation and ID with the same arguments returns the existing operation, while changed arguments return `IDEMPOTENCY_CONFLICT`. `expected_modified` must equal the current connection revision for validate, disable and reconnect actions.

- `connections.health()` — GET; Marketing Manager/System Manager; returns `items` with connection name, status, last validation, GET verification and signed POST timestamps, safe error code, number/template counts, and Ready/Processing/Failed webhook event counts. It omits credentials, account IDs, raw payloads and operation arguments.
- `connections.validate_connection(connection, expected_modified, request_id)` — System Manager; queues WABA, number-list and template-list reads; saved credentials alone never make a connection Ready.
- `connections.sync_numbers(connection, request_id)` — System Manager; requires Ready/Degraded and upserts provider identity while preserving local rate/team configuration. New numbers remain Unverified and provider entitlements stay unknown unless explicit provider evidence exists.
- `connections.sync_templates(connection, request_id)` — Marketing Manager/System Manager; requires Ready/Degraded; upserts the bounded provider catalog. Unknown provider status/category is retained as Unknown and cannot satisfy approval eligibility.
- `connections.set_enabled(connection, enabled, expected_modified, request_id)` — System Manager; disable takes effect in the request transaction and records a Succeeded operation; re-enable moves to Verifying and queues fresh reads. Failed revalidation becomes Degraded.
- `connections.test_send(connection, sending_number, contact, template, sample_values, request_id)` — System Manager input-validation boundary only. It checks current company, Granted consent, suppression, number and Approved template, then returns `READINESS_FAILED` until the P4 shared outbox and dispatch policy exist. It never calls Meta in P2.

The system-manager form uses native Frappe controls and operation dialogs. The manager summary is a small Desk Page backed by `connections.health`; it does not confer read permission on WA Connection. An operation failure exposes only a stable safe error code and generic UI message; provider response bodies, headers and tokens are never persisted in user-visible results.

## Foundation navigation interfaces

WA-P1-002 supplies read-only availability adapters under `tag_marketing.api.navigation`; they do not implement the later feature commands. Native Frappe widgets require their own result shape, so these return the following objects directly inside Frappe's `message` envelope rather than the command envelope above. Authenticated GET and native-widget POST are supported; neither mutates state or accepts Guest.

- `summary()` requires Marketing User/Manager/Analyst or System Manager and permitted configured company. It returns `availability` (Setup Required or Unavailable), `sending_enabled=false`, `metrics_available=false`, translated `reason`, `period="Last 30 Days"` and `metrics` with all five values null. No company identity, credential or raw record is returned.
- `eligible_contacts(filters)`, `active_campaigns(filters)`, `delivered_messages(filters)`, `exact_replies(filters)`, `unassigned_conversations(filters)` use the same access/scope check. Only absent/empty filters are accepted. Result: `{"value":null,"fieldtype":"Int"}` so native cards show N/A rather than fabricated zero.
- `activity(chart_name, ...)` accepts only the two owned chart identities from the [Overview](pages/OVERVIEW.md). Native chart date/range arguments do not compute activity during this foundation stage. Result: `{"labels":[],"datasets":[],"availability":"Unavailable"}`. The method is uncached; future user-scoped data must never use a chart-name-only cache.
- `inbox_readiness()` requires WhatsApp Agent or Marketing Manager and permitted configured company. Result: `{"availability":"Unavailable","reason":"..."}`. It exposes no conversations, composer or send capability.

These are constant availability responses, not paginated resources or asynchronous jobs. Forbidden access raises native PermissionError (403); unsupported filters/chart identities raise native ValidationError. Script Report execution raises a translated unavailable error after native report-role and company checks. Replace these adapters with verified feature queries only in the owning feature task; do not silently enable sending or treat schema presence as service readiness.

## Connection commands

The provider boundary is implemented by [`MetaCloudAPI`](../../tag_marketing/infrastructure/meta_cloud.py), with bounded HTTPS in [`RequestsProviderTransport`](../../tag_marketing/infrastructure/meta_http.py). At the 27 October 2026 contract review, only Graph API `v26.0` is accepted; every request includes that version and an explicit timeout. Unsupported versions fail before transport. The adapter provides connection identity validation, cursor-paginated number/template reads, template creation, message submission and authenticated media retrieval. Never follow or replay a provider-supplied `paging.next` URL; send only the validated opaque cursor back to the fixed Graph API route. Meta-owned request shapes and the review limits are recorded in [References](REFERENCES.md).

Provider failures have safe categories: expired credential, wrong account, rejected request, explicit rate limit, unavailable read, unsupported media, invalid provider response, and unknown submission outcome. Only provider code/status metadata is retained; response text, tokens and signed media URLs are not included in exceptions. Message POST transport failures, 5xx responses, missing message IDs and malformed success responses are `Unknown Outcome`; explicit 429 is `Rate Limited`; definitive 4xx rejection is `Rejected`. Acceptance means Meta returned a message ID and does not mean Sent or Delivered. This adapter does not automatically retry.

Requests are HTTPS-only to the Graph host or the explicitly allowed Meta media host, redirects are disabled, IDs/cursors are allowlisted, bodies and responses are bounded, and media MIME type, declared size and SHA-256 are checked before bytes are returned. The transport has a 30-second maximum request deadline and performs one attempt. Its timeout/response limits do not establish Meta tenant entitlements; those remain verified at connection setup and operations time. The adapter tests use synthetic data and the network-deny fixture; no provider request has been sent.

- `connections.check_webhook(connection)` — GET; System Manager only; returns `last_verified_at`, `last_signed_post_at`, `subscription_diagnostic` (`Verified`/`Not Verified`), `readiness` (`Ready`/`Action Required`), safe `last_error_code`, and `events` counts (`ready`, `processing`, `processed`, `failed`). It never claims a missing callback was received and never exposes receipt identifiers or payloads.

Connection operation requests persist only bounded non-secret arguments in permission-level-2 `WA Operation.request_json`, with `attempt_count` and a stable `wa:<operation>` job ID. A one-minute scan re-enqueues old Pending records; missing/malformed snapshots fail as `RECOVERY_UNAVAILABLE`. Workers atomically claim Pending once and recheck actor, company, target and operation kind. Stale Running connection read/sync jobs are retried once, then fail with `OPERATION_INTERRUPTED`.

Webhook receipt recovery uses stable `wa-webhook:<event>` IDs. Ready receipts older than one minute are re-enqueued. Interrupted Processing leases become Failed and use bounded backoff (1, 5, 15, 60 minutes; five total claims); the fifth failure remains terminal. Unknown authenticated event changes are Processed with `UNSUPPORTED_EVENT`, not retried. This is callback-event recovery only and never retries a message submission.

P2 connection commands and the intentionally blocked P4 test-send input contract are defined in [Connection setup interfaces](#connection-setup-interfaces). Credential edits use the restricted connection form; saving secrets invalidates connection readiness. Runtime diagnostic queries return masked metadata only.

Template commands: `templates.validate(template, expected_modified)` returns supported-component errors and a content hash without provider mutation. `templates.submit(template, content_hash, expected_modified, request_id)` is Manager-only and returns a persisted operation for Draft/Rejected definitions; stale content fails. `templates.sync(template, request_id)` refreshes the selected template through the same provider adapter. Template sync/submit never implies approval until Meta reports it.

## Audience and consent

- `audiences.enabled_sources()` — Marketing User/Manager; returns only System Manager-enabled, allowlisted source types.
- `audiences.source_preview(source_doctype, search, country_code, start, page_length)` — Marketing User/Manager plus current source read permissions; returns bounded safe identifiers and valid mobile candidates. `country_code` is required for local-number interpretation; no arbitrary source filters or selected company are accepted.
- `audiences.add_source(source_doctype, source_name, selected_phone, country_code, include_unassigned_lead)` — Marketing User/Manager; POST only. Rechecks current source and company access, selected mobile, enabled source type and explicit unassigned-Lead choice, then atomically creates/reuses `(company, phone_e164)` and appends an immutable source link. It always initializes consent to Unknown.
- `audiences.preview(segment, exclusions, limit, cursor)` — same marketing roles; returns eligible count, excluded counts by reason, sample contacts and preview revision. Advisory only.
- `imports.create_batch(source_file, mapping)` — Marketing User/Manager; accepts only the actor's private, unattached CSV File and an allowlisted field-to-header mapping, binds its exact bytes and mapping hash, then attaches the source privately to a company-scoped batch. It returns bounded diagnostics and valid/rejected/missing-evidence counts without changing contacts.
- `imports.inspect_csv(source_file)` — same roles; reads only an actor-owned private unattached file and returns validated column names for native mapping controls.
- `imports.validate_batch(batch, expected_modified, request_id)` — returns operation with input hash/counts/private row-error file; no contact changes.
- `imports.confirm_batch(batch, input_hash, expected_modified, request_id)` — requires Preview Ready and unchanged file/mapping; returns resumable import operation. Grants only when independent evidence passes validation.
- `contacts.consent_history(contact, start, page_length)` — Marketing User/Manager; returns bounded company-scoped event chronology for that contact, including recorded evidence references but never a public file URL.
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
- POST requires `application/json`, a declared content length and a body no larger than 1 MiB; missing length returns 411, an empty declared body returns 400 and oversize returns 413. Frappe v16.53.0 parses JSON during `frappe/app.py::init_request` before whitelisted-method dispatch, omits query arguments from JSON `form_dict`, and rejects malformed JSON as HTTP 417 before the webhook handler runs. The handler reads routing only from the URL and reuses cached original body bytes for HMAC verification. The reverse proxy or ingress must enforce the same 1 MiB limit specifically for this route before forwarding so Frappe does not parse an oversized body first.
- The handler verifies `X-Hub-Signature-256` using the selected connection's app secret over the exact cached request bytes before application-level payload interpretation. Reject invalid/unknown routing with 401/403. Validate WABA/number ownership after signature verification.
- Every `messages` change must identify a phone number owned by the selected connection. Commit WA Webhook Event and return 200 only after durable success. Persistence failure returns 503, allowing provider retry. Valid duplicate receipt returns 200. Unknown authenticated event types are stored as processed/unsupported diagnostics rather than crashing or discarding supported siblings in the same envelope.
- GET verification does not prove POST delivery, credentials, policy readiness or subscription permissions.

No browser login is required. The signed Guest POST is exercised through Frappe's WSGI app without cookies; no global CSRF setting is changed. Retain signature checks for every POST.

## Error catalogue

- 400: `INVALID_INPUT`, `INVALID_FILTER`, `INVALID_PHONE`, `INVALID_STEP`, `INVALID_MEDIA`.
- 401/403: framework auth failures, `SOURCE_ACCESS_DENIED`, `COMPANY_MISMATCH`, `INVALID_SIGNATURE`.
- 404: `NOT_FOUND` without leaking inaccessible identities.
- 409: `STALE_DOCUMENT`, `IDEMPOTENCY_CONFLICT`, `INVALID_STATE`, `APPROVAL_STALE`, `CLONE_REQUIRED`.
- 422: `CONSENT_REQUIRED`, `SUPPRESSED`, `TEMPLATE_NOT_APPROVED`, `WINDOW_CLOSED`, `READINESS_FAILED`, `AUDIENCE_TOO_LARGE`, `CAMPAIGN_EXPIRED`.
- 429: `LOCAL_RATE_LIMIT`; due work is deferred, not presented as provider delivery failure.
- 502/503: `PROVIDER_UNAVAILABLE`, `PERSISTENCE_UNAVAILABLE`; uncertain submissions become Unknown instead of automatic retries.

Provider-specific errors are mapped by versioned contract fixtures, not substring matching. Validate contracts through [acceptance tests](TESTING_AND_ACCEPTANCE.md).
