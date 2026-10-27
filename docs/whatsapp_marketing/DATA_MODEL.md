# Data model and lifecycle contract

Owner: WA-R01, WA-R04–WA-R14. Proposed application schema, not existing records. See [architecture](ARCHITECTURE.md), [API commands](API_CONTRACTS.md) and [permissions](PERMISSIONS_AND_PRIVACY.md).

## Shared conventions

All normal DocTypes use Frappe standard `name`, `owner`, `creation`, `modified`, `modified_by`, `docstatus` and `_user_tags` metadata where supported; custom ownership rules below do not bypass Frappe permissions. Business records are non-submittable (`docstatus=0`); managed `status` is an independent workflow, not Frappe submission. Do not expose Submit/Cancel document actions as campaign launch controls.

Unless a naming series is specified, normal records use generated hash names; label fields are user-facing names. All normal records are module-owned. Child records are explicitly listed below. Single settings have no company collection.

Fields below are stored unless marked derived. Required references must match company; server code validates all Link/Dynamic Link inputs. UTC is storage convention for instants; IANA zones govern display/scheduling. JSON is schema-validated, bounded and versioned. Use native JSON support from the inspected framework, not arbitrary `eval`. Optional unique provider IDs store NULL, never repeated empty-string values. Add composite unique constraints through idempotent schema helpers/patches and prove them under concurrent writes. Do not enable Frappe rename on delivery/evidence identities.

Profiles/configuration are editable by permitted users. Every field described as managed, derived, snapshot or evidence is protected in controllers and command services, including generic REST, Data Import and bulk updates. Audit privileged changes. Sensitive content must not be globally searchable, returned by list projections, or included in ordinary logs.

## Records

### WA Settings

- `marketing_company` — **Link → Company**; required; one company per site; immutable after live business data exists.
- `timezone` — **Data**; required IANA zone; initial Africa/Johannesburg.
- `marketing_start` — **Time**; required; default 09:00.
- `marketing_end` — **Time**; required; default 17:00; later than start.
- `marketing_cap` — **Int**; required; default 1; positive.
- `cap_window_hours` — **Int**; required; default 24; positive.
- `sending_enabled` — **Check**; default 0; emergency global switch; readiness gated.
- `sending_scope` — **Select**; Pilot or Live; default Pilot; Live requires verified pilot evidence.
- `pilot_contacts` — **Table → WA Pilot Contact**; explicit opted-in allowlist; 1..20 contacts for Pilot scope.
- `pilot_verified_at` — **Datetime**; service-managed UTC after manager evidence review.
- `pilot_verified_by` — **Link → User**; service-managed reviewing Manager.
- `pilot_evidence_reference` — **Small Text**; service-managed reviewed campaign/message/STOP/handover evidence reference.
- `suppression_hmac_key` — **Password**; generated server-only immutable identity-digest secret; rotation requires migration.
- `max_campaign_recipients` — **Int**; read-only 10000 for v1.
- `company_rate_per_second` — **Float**; required positive configured value before live enablement.
- `raw_event_retention_days` — **Int**; explicit positive policy value required.
- `message_retention_days` — **Int**; explicit positive policy value required.
- `media_retention_days` — **Int**; explicit positive policy value required.
- `consent_retention_days` — **Int**; explicit positive policy value; enforce documented legal hold.
- `privacy_notice_url` — **Data**; required HTTPS URL before live enablement.
- `retention_policy_reference` — **Small Text**; required policy owner/reference before enablement.
- `enabled_source_types` — **Table → WA Source Type**; allowlist Lead, Customer, Contact, Sales Order.

**Lifecycle:** Single; no business status.

**Write ownership:** System Manager writes. A live switch action is audited.

**Constraints/indexes:** Single record; no custom unique constraint.

### WA Connection

- `company` — **Link → Company**; required; selected settings company.
- `connection_name` — **Data**; required user label.
- `public_id` — **Data**; required generated random routing identifier; immutable.
- `meta_app_id` — **Data**; required; not a secret.
- `waba_id` — **Data**; required provider business account identifier.
- `api_version` — **Data**; required explicit supported version; no unversioned requests.
- `access_token` — **Password**; required secret; never returned.
- `app_secret` — **Password**; required webhook-signing secret.
- `verify_token` — **Password**; required generated subscription secret.
- `status` — **Select**; service-managed readiness.
- `last_validated_at` — **Datetime**; UTC; service-managed.
- `last_webhook_at` — **Datetime**; UTC; service-managed.
- `last_error_code` — **Data**; redacted diagnostic code.
- `last_error_summary` — **Small Text**; safe diagnostic only.

**Lifecycle:** Draft → Verifying → Ready; Ready ↔ Degraded; any → Disabled; Disabled → Verifying after explicit reconnect.

**Write ownership:** Create/update credentials: System Manager only. Secret changes clear validation and invalidate readiness.

**Constraints/indexes:** Unique public_id; unique (company, meta_app_id, waba_id); index (company, status).

### WA Sending Number

- `company` — **Link → Company**; required; matches connection.
- `connection` — **Link → WA Connection**; required.
- `provider_phone_id` — **Data**; required immutable provider identifier.
- `display_phone` — **Data**; provider display; not used as API identity.
- `display_name` — **Data**; provider business name.
- `status` — **Select**; service-managed.
- `quality_rating` — **Data**; provider value if available; unknown remains unknown.
- `provider_limits_json` — **JSON**; versioned provider capabilities/limits with fetched timestamp; no invented entitlement.
- `rate_per_second` — **Float**; configured positive sender limit before live sends.
- `last_sync_at` — **Datetime**; UTC.
- `default_team` — **Link → User Group**; optional agent team.

**Lifecycle:** Unverified → Ready; Ready ↔ Restricted; any → Disabled; Disabled → Unverified on explicit enable.

**Write ownership:** Provider fields sync-owned; administrators configure rates/team. Never silently switch approved sender.

**Constraints/indexes:** Unique provider_phone_id within site; index (company, status).

### WA Contact

- `company` — **Link → Company**; required; immutable.
- `phone_e164` — **Data**; required validated E.164; changing identity creates a new contact.
- `display_name` — **Data**; required nonblank display label.
- `language` — **Link → Language**; optional; explicit campaign language wins.
- `timezone` — **Data**; optional valid IANA zone.
- `tags` — **Table → WA Contact Tag**; company-scoped tag references.
- `source_links` — **Table → WA Source Link**; verified allowlisted ERPNext references.
- `consent_status` — **Select**; derived Unknown, Granted, Withdrawn; marketing purpose only.
- `suppressed` — **Check**; derived effective suppression.
- `last_inbound_at` — **Datetime**; service-derived maximum trusted event time.
- `archived` — **Check**; exclude from new audiences.

**Lifecycle:** Editable profile, derived consent fields; archived contacts remain auditable.

**Write ownership:** Marketing User/Manager profile edits. Consent/suppression fields cannot be set by CRUD or ordinary import.

**Constraints/indexes:** Unique (company, phone_e164); indexes (company, archived), (company, modified).

### WA Consent Event

- `company` — **Link → Company**; required.
- `contact` — **Link → WA Contact**; required same company.
- `purpose` — **Select**; Marketing in v1; do not infer support permission.
- `event_type` — **Select**; Granted or Withdrawn.
- `occurred_at` — **Datetime**; required evidence timestamp UTC.
- `recorded_at` — **Datetime**; required server receipt timestamp UTC.
- `source` — **Select**; Web Form, CSV Evidence, Agent Recorded, Inbound Keyword, Unsubscribe Button.
- `notice_version` — **Data**; required for grants.
- `evidence_file` — **Link → File**; optional private evidence.
- `evidence_reference` — **Small Text**; required evidence description/reference; grants require file or verifiable reference.
- `source_event_key` — **Data**; required deterministic idempotency key.
- `recorded_by` — **Link → User**; required actor/service identity.

**Lifecycle:** Append-only; correction is a new evidence event, never editing history.

**Write ownership:** Grant recording checks source and evidence. Withdrawal immediate. Backdated grants cannot override a later withdrawal; regrant needs newer evidence; timestamp ties resolve to Withdrawn.

**Constraints/indexes:** Unique source_event_key; index (company, contact, purpose, occurred_at).

### WA Suppression

- `company` — **Link → Company**; required.
- `contact` — **Link → WA Contact**; required.
- `purpose` — **Select**; Marketing.
- `reason` — **Select**; Opt Out, Manual Block, Invalid Address.
- `active` — **Check**; required; only services change.
- `consent_event` — **Link → WA Consent Event**; optional source of restriction.
- `identity_digest` — **Data**; keyed digest of company/normalised identity for lawful minimised suppression after content deletion.
- `changed_at` — **Datetime**; required UTC.
- `changed_by` — **Link → User**; required.

**Lifecycle:** Active ↔ inactive through audited services; opt-out deactivation requires qualifying newer consent.

**Write ownership:** No bulk deletion. Retention of a minimised suppression identity follows configured policy and legal holds.

**Constraints/indexes:** Unique (company, contact, purpose); index identity_digest.

### WA Tag

- `company` — **Link → Company**; required.
- `label` — **Data**; required.
- `disabled` — **Check**; default 0.

**Lifecycle:** Enabled/disabled configuration.

**Write ownership:** Marketing User/Manager manage; referenced disabled tags remain visible in history.

**Constraints/indexes:** Unique (company, label).

### WA Import Batch

- `company` — **Link → Company**; required.
- `source_file` — **Link → File**; required private CSV.
- `mapping_json` — **JSON**; explicit allowlisted column mapping and phone-country default.
- `status` — **Select**; service-managed.
- `row_count` — **Int**; read-only.
- `valid_count` — **Int**; read-only.
- `rejected_count` — **Int**; read-only.
- `result_file` — **Link → File**; optional private per-row diagnostics.
- `operation` — **Link → WA Operation**; background progress.
- `requested_by` — **Link → User**; required initiating user.
- `input_hash` — **Data**; file+mapping hash preventing stale confirmation.

**Lifecycle:** Validating → Preview Ready → Importing → Completed; processing states → Failed; Preview Ready → Validating on remap.

**Write ownership:** Confirm exact preview hash; read/revalidate source permissions and evidence. Row-scoped idempotency allows resume without regranting consent.

**Constraints/indexes:** Index (company, status); unique row keys belong to standalone WA Import Row records, never a giant child grid.

### WA Audience Segment

- `company` — **Link → Company**; required.
- `segment_name` — **Data**; required.
- `filters_json` — **JSON**; required versioned allowlisted filter AST; no arbitrary SQL/code.
- `disabled` — **Check**; default 0.
- `last_preview_count` — **Int**; advisory cache, never the approved audience.

**Lifecycle:** Editable; campaigns freeze evaluated membership rather than live definitions.

**Write ownership:** Filter fields: tags, language, source type, selected source attributes, contact creation date and archived state; eligibility is always applied.

**Constraints/indexes:** Unique (company, segment_name); index (company, disabled).

### WA Template

- `company` — **Link → Company**; required.
- `connection` — **Link → WA Connection**; required.
- `provider_template_id` — **Data**; set after provider creation.
- `template_name` — **Data**; required provider-compatible name.
- `language_code` — **Data**; required explicit provider locale.
- `category` — **Select**; Marketing, Utility, Authentication; Authentication sync-only in v1.
- `components_json` — **JSON**; required validated header/body/footer/button schema.
- `status` — **Select**; service-managed provider state.
- `content_hash` — **Data**; required canonical content hash.
- `provider_reason` — **Small Text**; redacted rejection/pause reason.
- `last_sync_at` — **Datetime**; UTC.

**Lifecycle:** Draft → Pending → Approved / Rejected; Approved → Paused / Disabled; provider states are authoritative.

**Write ownership:** User edits only Draft/Rejected local drafts, then resubmits. Campaigns require Approved; edits/reclassification invalidate stale approval snapshots.

**Constraints/indexes:** Unique (connection, template_name, language_code); unique provider_template_id when populated (use nullable unique column).

### WA Campaign

- `company` — **Link → Company**; required.
- `campaign_name` — **Data**; required.
- `purpose` — **Select**; Marketing for v1 bulk campaigns.
- `sending_number` — **Link → WA Sending Number**; required same company.
- `segment` — **Link → WA Audience Segment**; required.
- `exclusions_json` — **JSON**; contact/tag exclusions frozen with snapshot.
- `template` — **Link → WA Template**; required matching connection.
- `variable_mapping_json` — **JSON**; allowlisted expressions/constant values; no code.
- `media_file` — **Link → File**; optional private approved header media.
- `scheduled_at` — **Datetime**; required for Schedule; UTC.
- `start_mode` — **Select**; Now or Scheduled; required, default Now; Scheduled requires scheduled_at. Now approval has no future start and can launch until expiry.
- `expires_at` — **Datetime**; required at approval; after start.
- `schedule_timezone` — **Data**; required IANA display zone.
- `status` — **Select**; service-managed.
- `current_snapshot` — **Link → WA Campaign Snapshot**; service-managed.
- `approved_by` — **Link → User**; service-managed.
- `approved_at` — **Datetime**; UTC.
- `approval_hash` — **Data**; service-managed hash of immutable snapshot.
- `test_message` — **Link → WA Message**; test tied to snapshot hash.
- `erpnext_campaign` — **Link → Campaign**; optional authorised CRM master.
- `estimated_budget` — **Currency**; optional estimate guard, not invoice cap guarantee.
- `currency` — **Link → Currency**; company default currency.

**Lifecycle:** Draft → Pending Approval → Approved → Scheduled / Running → Completed; Scheduled/Running → Paused; Paused → Scheduled/Running; Scheduled/Paused → Completed on expiry with recorded skipped reasons; nonterminal → Cancelled; execution states → Failed. Rejection or material edits before dispatch return Draft. After first submission, clone to change material content.

**Write ownership:** User drafts/requests approval; Manager approves/launches/actions. Read-only workflow fields only service-writable. Completed means dispatch drained, not every message delivered.

**Constraints/indexes:** Index (company, status, scheduled_at); naming series WA-CAM-.YYYY.-.#####.

### WA Campaign Snapshot

- `company` — **Link → Company**; required.
- `campaign` — **Link → WA Campaign**; required.
- `version` — **Int**; required incrementing.
- `status` — **Select**; Building, Ready, Superseded.
- `configuration_json` — **JSON**; frozen sender/template hash/components/mapping/media digest/schedule/exclusions.
- `snapshot_hash` — **Data**; configuration + canonical ordered recipient/variable hashes.
- `recipient_count` — **Int**; required <=10000 eligible unique recipients.
- `excluded_summary_json` — **JSON**; reason counts without inaccessible source data.
- `selected_by` — **Link → User**; required selection actor.
- `created_at` — **Datetime**; UTC.

**Lifecycle:** Building → Ready; Ready → Superseded when material configuration changes; immutable when Ready.

**Write ownership:** Chunk generation writes under Building. Approval requires Ready/hash verified/current document revision; user edits blocked.

**Constraints/indexes:** Unique (campaign, version); index (campaign, status).

### WA Campaign Recipient

- `company` — **Link → Company**; required.
- `campaign` — **Link → WA Campaign**; required.
- `snapshot` — **Link → WA Campaign Snapshot**; required.
- `contact` — **Link → WA Contact**; required.
- `phone_e164` — **Data**; frozen address.
- `variables_json` — **JSON**; frozen resolved values.
- `source_references_json` — **JSON**; minimal selected source IDs for permission/relevance checks.
- `eligibility_reason` — **Data**; last inclusion/exclusion result code.
- `dispatch_status` — **Select**; service-managed.
- `message` — **Link → WA Message**; logical outbound message.
- `finished_at` — **Datetime**; UTC.

**Lifecycle:** Pending → Queued → Accepted / Unknown / Failed / Skipped / Cancelled. Delivered/Read are message evidence, not recipient dispatch states.

**Write ownership:** Frozen membership and variables. Live gating may exclude a member but never add one after approval.

**Constraints/indexes:** Unique (snapshot, contact); index (campaign, dispatch_status); technical rows are standalone, not child-table rows.

### WA Conversation

- `company` — **Link → Company**; required.
- `contact` — **Link → WA Contact**; required.
- `sending_number` — **Link → WA Sending Number**; required.
- `assigned_to` — **Link → User**; optional authorised WhatsApp Agent.
- `team` — **Link → User Group**; optional authorised team.
- `status` — **Select**; Open or Resolved.
- `automation_mode` — **Select**; Automatic or Human.
- `last_inbound_at` — **Datetime**; trusted maximum inbound timestamp.
- `last_message_at` — **Datetime**; activity sort key.
- `unread_count` — **Int**; derived per conversation summary; per-user read cursor handled separately.
- `assignment_version` — **Int**; optimistic concurrency for assignment.

**Lifecycle:** Open ↔ Resolved; Automatic → Human by handover/reply; Human → Automatic by explicit Resume Automation.

**Write ownership:** Agents act only within assignment/team scope. New inbound reopens Resolved. Service window derives from last_inbound_at + 24h.

**Constraints/indexes:** Unique (company, contact, sending_number); index (company, assigned_to, status, last_message_at).

### WA Conversation Read

- `company` — **Link → Company**; required.
- `conversation` — **Link → WA Conversation**; required.
- `user` — **Link → User**; required.
- `last_read_message` — **Link → WA Message**; optional cursor.
- `read_at` — **Datetime**; UTC.

**Lifecycle:** User-specific read cursor.

**Write ownership:** Only the current authorised user advances their cursor; unread list queries never expose other users.

**Constraints/indexes:** Unique (conversation, user).

### WA Conversation Note

- `company` — **Link → Company**; required.
- `conversation` — **Link → WA Conversation**; required.
- `note` — **Small Text**; required plain text; never sent to Meta.
- `author` — **Link → User**; required.
- `recorded_at` — **Datetime**; UTC.

**Lifecycle:** Append-only internal note; redaction via privacy service.

**Write ownership:** Assigned/team agents and Manager read/write through note command.

**Constraints/indexes:** Index (conversation, recorded_at).

### WA Message

- `company` — **Link → Company**; required.
- `conversation` — **Link → WA Conversation**; required.
- `direction` — **Select**; Inbound or Outbound.
- `purpose` — **Select**; Marketing, Utility, Support, Test.
- `body_text` — **Long Text**; plain text; sensitive.
- `media_file` — **Link → File**; optional private linked attachment.
- `template` — **Link → WA Template**; required for template sends.
- `template_payload_json` — **JSON**; frozen send payload without credentials.
- `provider_message_id` — **Data**; nullable until known; unique when populated.
- `logical_key` — **Data**; required deterministic delivery key.
- `status` — **Select**; service-managed.
- `campaign_recipient` — **Link → WA Campaign Recipient**; optional origin.
- `automation_run` — **Link → WA Automation Run**; optional origin.
- `reply_to_provider_id` — **Data**; optional reply context.
- `replacement_for` — **Link → WA Message**; optional immutable reference to a prior unresolved send; normal campaign approval or agent reply authorisation still applies.
- `initiated_by` — **Link → User**; actor/service identity.
- `submitted_at` — **Datetime**; UTC.
- `sent_at` — **Datetime**; UTC.
- `delivered_at` — **Datetime**; UTC.
- `read_at` — **Datetime**; UTC.
- `received_at` — **Datetime**; inbound UTC.
- `error_code` — **Data**; safe classified error.

**Lifecycle:** Outbound: Queued → Submitting → Accepted → Sent → Delivered → Read; Submitting → Unknown / Failed; Queued → Suppressed / Cancelled; definitive provider rejection may mark Failed. Inbound: Received. All historical events retained; current status uses reconciliation policy.

**Write ownership:** Service-created immutable content once queued. Outbound permission/cap reservation checked per origin. No generic edit/delete.

**Constraints/indexes:** Unique logical_key; unique provider_message_id when populated; index (conversation, creation, name).

### WA Message Attempt

- `company` — **Link → Company**; required.
- `message` — **Link → WA Message**; required.
- `attempt_no` — **Int**; required.
- `started_at` — **Datetime**; UTC.
- `finished_at` — **Datetime**; UTC.
- `result` — **Select**; Started, Accepted, Rejected, Unknown.
- `provider_message_id` — **Data**; nullable.
- `http_status` — **Int**; nullable.
- `error_code` — **Data**; redacted classification.
- `provider_trace_id` — **Data**; optional safe support reference.

**Lifecycle:** Append then finalise once; stale Started after submission becomes Unknown.

**Write ownership:** Worker-only; retain without tokens/body duplication.

**Constraints/indexes:** Unique (message, attempt_no); index (result, started_at).

### WA Message Event

- `company` — **Link → Company**; required.
- `message` — **Link → WA Message**; nullable until correlated.
- `provider_message_id` — **Data**; required for provider status.
- `event_type` — **Data**; provider status or reconciliation observation.
- `occurred_at` — **Datetime**; provider timestamp UTC.
- `received_at` — **Datetime**; server timestamp UTC.
- `event_key` — **Data**; required canonical deduplication key.
- `details_json` — **JSON**; minimal redacted details.

**Lifecycle:** Append-only; uncorrelated events retry correlation before retention cleanup.

**Write ownership:** Webhook processor/service-only. Late events do not overwrite stronger evidence.

**Constraints/indexes:** Unique event_key; index (provider_message_id, occurred_at).

### WA Outbox Item

- `company` — **Link → Company**; required.
- `message` — **Link → WA Message**; required.
- `logical_key` — **Data**; required equals message delivery identity.
- `status` — **Select**; service-managed.
- `due_at` — **Datetime**; UTC.
- `lease_owner` — **Data**; nullable worker claim token.
- `lease_until` — **Datetime**; nullable UTC.
- `submission_started_at` — **Datetime**; set before provider HTTP boundary.
- `attempt_count` — **Int**; default 0.
- `next_retry_at` — **Datetime**; nullable UTC.
- `last_error_code` — **Data**; redacted.

**Lifecycle:** Pending/Retry → Claimed → Submitting → Done / Retry / Unknown / Failed; pre-submission → Cancelled; uncertain post-submission → Unknown. Waiting for hours/cap stays Pending with future due_at.

**Write ownership:** Worker/scheduler services only. Done means accepted by provider or resolved, not delivered.

**Constraints/indexes:** Unique logical_key; index (status, due_at); index lease_until.

### WA Send Reservation

- `company` — **Link → Company**; required.
- `contact` — **Link → WA Contact**; required.
- `message` — **Link → WA Message**; required.
- `reserved_at` — **Datetime**; UTC.
- `state` — **Select**; Reserved, Retained, Released.
- `purpose` — **Select**; Marketing or Test.
- `estimate_amount` — **Currency**; optional budget reservation.
- `currency` — **Link → Currency**; required for amount.

**Lifecycle:** Reserved → Retained after Accepted/Unknown; Reserved → Released after explicit rejection/no submission.

**Write ownership:** Lock company/contact coordination row before counting active rolling-window reservations and inserting. Do not represent a rolling window as a calendar-day unique key.

**Constraints/indexes:** Unique message; index (company, contact, reserved_at, state); locking strategy tested under contention.

### WA Automation

- `company` — **Link → Company**; required.
- `automation_name` — **Data**; required.
- `status` — **Select**; Draft, Active, Paused, Archived.
- `draft_definition_json` — **JSON**; versioned trigger/conditions/ordered steps/forward targets.
- `published_version` — **Link → WA Automation Version**; nullable.
- `run_as_user` — **Link → User**; required for publication; permissions rechecked.
- `sending_number` — **Link → WA Sending Number**; required for outbound actions.
- `purpose` — **Select**; Marketing, Utility, Support.

**Lifecycle:** Draft → Active; Active ↔ Paused; Draft/Paused → Archived. Draft changes do not mutate published versions.

**Write ownership:** Manager publishes, pauses and resumes. Active definition editing edits draft only. Published runs pin a version.

**Constraints/indexes:** Unique (company, automation_name); index (company, status).

### WA Automation Version

- `company` — **Link → Company**; required.
- `automation` — **Link → WA Automation**; required.
- `version` — **Int**; required monotonic.
- `definition_json` — **JSON**; validated immutable trigger/steps.
- `definition_hash` — **Data**; required.
- `published_by` — **Link → User**; required manager.
- `published_at` — **Datetime**; UTC.

**Lifecycle:** Immutable published snapshot.

**Write ownership:** Application service creates after cycle/target/purpose/permission validation.

**Constraints/indexes:** Unique (automation, version).

### WA Automation Run

- `company` — **Link → Company**; required.
- `automation` — **Link → WA Automation**; required.
- `version` — **Link → WA Automation Version**; required.
- `trigger_key` — **Data**; required source identity.
- `contact` — **Link → WA Contact**; required.
- `conversation` — **Link → WA Conversation**; nullable until messaging.
- `source_event` — **Link → WA Source Event**; optional CRM event.
- `status` — **Select**; service-managed.
- `current_step_id` — **Data**; required stable step identifier.
- `completed_steps_json` — **JSON**; bounded step result ledger keyed by stable ID.
- `due_at` — **Datetime**; UTC for waits.
- `lease_owner` — **Data**; nullable.
- `lease_until` — **Datetime**; nullable UTC.
- `last_error_code` — **Data**; redacted.

**Lifecycle:** Ready → Running → Waiting / Waiting Human / Completed / Failed / Cancelled; due Waiting → Ready; explicit human resume → Ready. Paused definitions block new claims without mutating completed history.

**Write ownership:** Workers execute at most one effective action per (run, step_id); send logical key is run+step. No sleeps for waits.

**Constraints/indexes:** Unique (automation, trigger_key, contact); index (status, due_at); index lease_until.

### WA Source Event

- `company` — **Link → Company**; required.
- `event_type` — **Select**; Lead Created, Customer Created, Sales Order Submitted, Sales Order Cancelled.
- `source_doctype` — **Link → DocType**; allowlist only.
- `source_name` — **Dynamic Link → source_doctype**; required.
- `source_revision` — **Data**; required modified/version identity.
- `event_key` — **Data**; required deterministic logical key.
- `actor` — **Link → User**; required.
- `status` — **Select**; Ready, Processing, Processed, Failed.
- `recorded_at` — **Datetime**; UTC.
- `error_code` — **Data**; redacted.

**Lifecycle:** Ready → Processing → Processed; failed processing → Failed with explicit reprocess.

**Write ownership:** Source transaction creates; after-commit event worker processes. No remote traffic inside source hooks.

**Constraints/indexes:** Unique event_key; index (status, recorded_at).

### WA Webhook Event

- `company` — **Link → Company**; required after authenticated routing.
- `connection` — **Link → WA Connection**; required.
- `receipt_key` — **Data**; canonical receipt digest.
- `raw_payload` — **Long Text**; bounded sensitive JSON; only after valid signature.
- `status` — **Select**; Ready, Processing, Processed, Failed.
- `received_at` — **Datetime**; UTC.
- `processed_at` — **Datetime**; nullable UTC.
- `error_code` — **Data**; redacted.
- `attempt_count` — **Int**; default 0.

**Lifecycle:** Ready → Processing → Processed; failure → Failed; recovery may reprocess idempotently.

**Write ownership:** Guest cannot list/read. Signature validation precedes persistence. Element keys also deduplicate statuses/messages across different envelopes.

**Constraints/indexes:** Unique receipt_key; index (status, received_at).

### WA Operation

- `company` — **Link → Company**; required.
- `operation_type` — **Data**; allowlisted job kind.
- `requested_by` — **Link → User**; required.
- `request_id` — **Data**; required client/service idempotency key.
- `request_hash` — **Data**; required canonical command arguments hash.
- `status` — **Select**; Pending, Running, Succeeded, Failed, Cancelled.
- `progress_percent` — **Percent**; 0..100.
- `target_doctype` — **Link → DocType**; allowlisted.
- `target_name` — **Dynamic Link → target_doctype**; nullable.
- `result_json` — **JSON**; bounded IDs/counts/diagnostic result; no credentials.
- `result_file` — **Link → File**; optional private output.
- `error_code` — **Data**; redacted.
- `heartbeat_at` — **Datetime**; UTC.

**Lifecycle:** Pending → Running → Succeeded / Failed / Cancelled.

**Write ownership:** Read by requester/authorised Manager and current target scope. Permissions rechecked by worker. Idempotent repeat with different arguments returns conflict.

**Constraints/indexes:** Unique (requested_by, operation_type, request_id); index (company, status, heartbeat_at).

### WA Audit Event

- `company` — **Link → Company**; required.
- `action` — **Data**; required allowlisted audit action.
- `actor` — **Link → User**; required initiating principal.
- `target_doctype` — **Link → DocType**; allowlisted.
- `target_name` — **Dynamic Link → target_doctype**; required.
- `occurred_at` — **Datetime**; server UTC.
- `before_hash` — **Data**; optional.
- `after_hash` — **Data**; optional.
- `details_json` — **JSON**; redacted reason, operation ID and safe changed fields.

**Lifecycle:** Append-only; privacy redaction retains integrity metadata.

**Write ownership:** Services write; Managers/System Managers read within company; Analyst only aggregate outcomes.

**Constraints/indexes:** Index (company, target_doctype, target_name, occurred_at).

### WA Import Row

- `company` — **Link → Company**; required.
- `batch` — **Link → WA Import Batch**; required.
- `row_number` — **Int**; required positive CSV row ordinal.
- `input_hash` — **Data**; required batch file+mapping hash.
- `row_hash` — **Data**; canonical row content hash.
- `status` — **Select**; Valid, Invalid, Imported.
- `contact` — **Link → WA Contact**; nullable until matched/imported.
- `error_code` — **Data**; safe row diagnostic.
- `projection_json` — **JSON**; bounded validated allowlisted fields/evidence references; sensitive; no executable expressions.

**Lifecycle:** Valid → Imported; invalid rows remain Invalid until a new validated input batch/version.

**Write ownership:** Importer owns writes; rows are standalone and paginated. Repeat confirmation resumes only unchanged input. Cleanup follows configured raw/import retention.

**Constraints/indexes:** Unique (batch, row_number, input_hash); index (batch, status).

### WA Privacy Hold

- `company` — **Link → Company**; required configured company.
- `scope` — **Select**; Company, Contact or Category.
- `contact` — **Link → WA Contact**; required only for Contact scope, same company.
- `categories_json` — **JSON**; allowlisted raw events, messages, media, consent, imports or exports; required for Category scope.
- `reason` — **Small Text**; required legal/policy reason without unnecessary personal content.
- `authority_reference` — **Small Text**; required approving authority/case reference.
- `active` — **Check**; default 1; audited service changes only.
- `expires_at` — **Datetime**; optional reviewed expiry; expiry alone does not delete content.
- `reviewed_by` — **Link → User**; required System Manager.

**Lifecycle:** Active → released through audited privacy service after authority review. Cleanup checks holds at preview and again per deletion batch.

**Write ownership:** System Manager through restricted native form/service; read permission limited to authorised privacy administrators. Record release in WA Audit Event. No ordinary Marketing User edit or export.

**Constraints/indexes:** Generated hash name; index (company, active, scope, contact). Reject irrelevant contact/category values for the chosen scope.

### WA Rate Card

- `company` — **Link → Company**; required.
- `rate_card_name` — **Data**; required.
- `currency` — **Link → Currency**; required; no silent foreign exchange conversion.
- `effective_from` — **Date**; required.
- `effective_until` — **Date**; optional exclusive end later than start.
- `rates` — **Table → WA Rate Card Row**; required market/category unit estimates.
- `source_url` — **Data**; required official rate source/reference.
- `reviewed_by` — **Link → User**; required approving Manager.
- `status` — **Select**; Draft, Active, Retired.

**Lifecycle:** Draft → Active → Retired; active rows are immutable; replacement uses a new dated card.

**Write ownership:** Manager administers. Reject overlapping Active effective periods for the same company/currency/market/category. Estimation chooses by intended delivery market/category/date; missing exact currency/rate returns unavailable.

**Constraints/indexes:** Unique (company, rate_card_name); index (company, status, effective_from).

## Small child records

- **WA Pilot Contact:** `contact` (Link → WA Contact, required, same company, currently opted in). Parent: WA Settings; unique contact, maximum 20; only System Manager changes while sending is disabled.
- **WA Rate Card Row:** `country` (Link → Country, required destination market), `category` (Select Marketing/Utility/Authentication, required), `unit_price` (Currency, required nonnegative, parent currency). Parent: WA Rate Card; unique country/category per card.
- **WA Source Type:** `source_doctype` (Link → DocType, required, allowlisted), `enabled` (Check). Parent: WA Settings; unique source type within parent.
- **WA Source Link:** `source_doctype` (Link → DocType), `source_name` (Dynamic Link), `selected_phone` (Data), `selected_by` (Link → User), `selected_at` (Datetime). Parent: WA Contact; required company/source permission validation; no arbitrary Dynamic Links.
- **WA Contact Tag:** `tag` (Link → WA Tag, required, same company). Parent: WA Contact; unique tag per parent.

Automation steps live in the validated definition JSON and are edited through native controls rather than storing both a child grid and competing JSON truth. Each step has `step_id`, `action`, `parameters`, `next_step_id`, optional forward `otherwise_step_id`; trigger, purpose and condition schema are defined in [automation flow](flows/AUTOMATION_EXECUTION.md).

CSV row diagnostics and massive snapshots are never attached as one large editable child table. Use standalone WA Import Row records with unique `(batch, row_number, input_hash)` for resumable row processing.

## Relationship and permission invariants

A connection owns numbers/templates. A company/contact owns consent and marketing suppression across numbers. Each company/contact/number tuple has one conversation. Campaign snapshots own recipient membership; recipients point to one logical message. Messages own attempts/events/outbox/reservations. Automation versions own immutable definitions; runs pin a version and unique trigger/contact pair across published versions. Operation references expose only authorised target records.

Every sender/template pairing uses the same connection. Company mismatches fail validation regardless of a user's roles. Read cursors and internal notes stay separate from provider messages. Media is a private File linked to its authorised owner; messages retain only permitted references after retention cleanup.

## Approval hash and statuses

Canonical snapshot hashing uses sorted keys and ordered recipient identities/variable hashes. Include sender, template content hash/category/language, media content digest, purpose, exclusions, resolved variables, start mode/schedule/expiry/timezone and sending policy values. Exclude operational counters, late delivery updates and connection-secret material. Record the policy version. Changing any hashed value before dispatch returns the campaign to Draft; after submission begins require a cloned campaign.

Pausing/resuming, retry scheduling, counters, provider callbacks and stricter live suppression do not rewrite the approved snapshot. Reconnection never authorises a different sender. Completion and cancellation are recorded, not inferred from UI button state.

## Schema verification

Use [WA-A01, WA-A04, WA-A06, WA-A07 and WA-A10](TESTING_AND_ACCEPTANCE.md). Test nullable unique IDs, composite constraints, source/company mismatches, immutable fields via REST, stale snapshots, rolling-cap races and repeated migrations on MariaDB 11.8 before considering other databases supported.
