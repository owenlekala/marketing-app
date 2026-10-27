# Messaging and reliability

Owner: WA-R07–WA-R11, WA-R15, WA-R16. [Data model](DATA_MODEL.md) owns state names; [API contracts](API_CONTRACTS.md) owns public commands.

## Readiness and eligibility

Pilot enablement requires configured privacy/retention policy, validated credentials/API version, verified webhook receipt, selected company, ready sender, approved compatible template, configured rates, healthy queue/scheduler and offline qualification. Pilot scope restricts every campaign/automation submission to the settings allowlist of 1–20 opted-in contacts. Live enablement additionally requires manager-reviewed pilot evidence. Administrators may conduct explicit authorised tests before enabling either scope; those commands never enable ordinary campaign/automation sending.

Before each outbound submission verify emergency switch, campaign/run state, approved snapshot/version, current actor/source scope, sender/connection, template current approval/content, expiry, consent/suppression, service window when relevant, frequency cap, budget estimate reservation and current rate controls. A failed check records a safe reason without leaking inaccessible data.

Explicit Test messages use their command's recorded test authorisation instead of a campaign/live-scope gate, so administrators can qualify an initially disabled installation. They still require authorised consent, sender/connection readiness, appropriate template/window, media validation and rate/cap controls. A Disabled connection/number blocks tests too. Disabling ordinary sending does not implicitly authorise a test; each requires the separate explicit command and confirmation.

Marketing outside configured hours or frequency/rate availability defers to the next eligible time, bounded by expiry. Apply the stricter of approved and current limits; loosening global configuration cannot override frozen approval. On DST gaps advance to the next valid eligible local instant; for ambiguous local times use the later UTC instant. Hard suppression, invalid address, lost source permission or invalidated template prevents submission. Expired free-form replies fail `WINDOW_CLOSED`; never invent replacement template content.

## Snapshot, approval and scheduling

Generate recipients in bounded chunks under a Building snapshot. Canonicalise configuration/membership/resolved variable hashes, verify totals, then mark Ready. A partial snapshot is never approvable. Manager approval compares current document revision and snapshot hash in one transaction.

Campaign tests are explicit, sent to an authorised opted-in contact and tied to the exact snapshot hash; accepted test evidence is required to request approval. Preview data is clearly sampled. Material edits require a new snapshot/test/approval. Once any recipient reaches Submitting, require a clone for material changes.

Scheduler discovers due Scheduled campaigns every minute using indexed queries and claim protection. It invokes the same launch service as the manager. Expired campaigns stop new work and finish with skipped/expired reasons; delivery events remain processable. Dispatch completion aggregates recipient outcomes, including Unknown, and marks Completed only when no dispatchable items remain; show an unresolved-outcome count prominently.

## Outbox and submission boundary

1. Persist logical message/outbox with a unique origin key: campaign snapshot/contact; automation run/step; inbox command request ID. Commit before enqueueing.
2. Claim due work atomically using a lease token and short transaction. Default lease 120 seconds; provider HTTP total timeout 30 seconds. Batch claims stay bounded at 100 items and never lock an entire campaign.
3. Recheck live eligibility. Acquire company/contact coordination lock, inspect rolling reservations, reserve cap/budget and persist attempt + Submitting marker. Commit before HTTP.
4. Call Meta through the pinned adapter. Persist provider ID, Accepted result, retained reservation and outbox Done atomically on success.
5. An explicit retryable rejection may schedule Retry. An explicit permanent rejection marks Failed and releases the reservation. An ambiguous timeout/disconnect/crash after Submitting marks Unknown and retains the reservation.

Use a company/contact row lock for cap reservation. Do not hold that lock over HTTP. Withdrawal and submission eligibility share coordination so new work cannot pass an already-recorded withdrawal. A provider request already in flight when withdrawal occurs cannot be recalled; record timing accurately.

## Retry and recovery policy

Known retryable provider throttling/unavailability is classified from verified versioned responses. Default maximum is five total attempts with delays of 1, 5, 15 and 60 minutes, jittered ±20%; honour a longer supported Retry-After but never exceed campaign expiry. Authentication, policy, invalid-recipient and template failures do not retry automatically; degrade/pause affected sending and alert operators.

Do not infer safe rejection merely from a 5xx status: retry only where the provider contract confirms no acceptance or no submission occurred. A transport failure after the boundary is Unknown. Stale Claimed items without a Submitting marker may be reclaimed; stale Submitting/Started items become Unknown. Leases are renewed only by the owning token, and completion uses conditional updates to prevent stale workers overwriting newer results.

Recovery scans every minute: pending outbox, due retries, stale leases, webhook/source events, due automation waits and stale operations. Database records survive enqueue/Redis outages. Persisted events allow replay without duplicate actions. Do not retry a poisoned item forever; show Failed diagnostics after bounded processing attempts.

Unknown reconciliation uses available provider ID, correlation metadata verified in the current contract and late webhooks. Do not correlate merely because phone/text/timestamp look similar. If unresolved, Manager records evidence and a decision. A separately confirmed replacement is a new logical send with explicit duplicate-risk acknowledgement; never reset Unknown to Pending invisibly. No exactly-once delivery guarantee across Meta.

## Inbound events and status ordering

Verify signature, WABA and number before trusting content. Commit raw receipt before 200; enqueue after commit. Deduplicate envelope receipts and individual message/status elements separately. Iterate every envelope entry; one unsupported element must not drop valid siblings.

Create/correlate the conversation and inbound message once. Use the maximum trusted inbound event timestamp, not processing time, for the 24-hour reply window. A delayed old message must not extend the window. Detect unreasonable future timestamps and retain for diagnosis.

Process opt-outs first, then receipt/reply association, human routing and eligible automation triggers. Unknown identities are retained for supported resolution; do not guess E.164 identities or send to an unresolved identifier.

Append Message Events. Current successful evidence progresses Accepted → Sent → Delivered → Read; late Sent cannot downgrade Delivered. Failed evidence is retained separately; if actual delivery exists, do not replace that fact with a contradictory late failure. Unmatched provider IDs remain correlation candidates. Missing read receipts are unknown, not proof of unread status.

## Automation execution

Runs pin a published version and trigger identity. Execute steps with stable `(run, step_id)` action keys. Waits persist `due_at`; workers return immediately instead of sleeping. Pausing a definition prevents new claims, and handover prevents automated sends in that conversation. Explicit resume rechecks consent, window, expiry and permissions; old free-form steps do not become eligible just because the run resumed.

Cap per run at 100 steps and one active run per automation/contact/trigger identity; reject backward targets/cycles. Errors produce visible Failed runs. Execution decisions and results remain in the run ledger; provider messages link back to the originating step.

## Capacity and reconciliation

Use paginated audience queries and chunked snapshots; avoid one job per entire 10,000-recipient campaign with an in-memory array. Queue defaults: dedicated `marketing`, one worker initially, bounded batches; scale based on measured queue age and provider entitlement. Inbox queries use indexed keyset pagination and never load all messages.

Metrics distinguish dispatch and provider outcomes. Reply attribution uses provider reply context first; an optional latest-message heuristic is labelled inferred and excluded from exact reply counts by default. Cost estimates use dated configurable rates and reserved estimates; they cannot guarantee the provider invoice amount. Rate/pricing reference: [Meta pricing](https://whatsappbusiness.com/products/platform-pricing/).

See [webhook flow](flows/WEBHOOKS_AND_DELIVERY.md), [campaign flow](flows/CAMPAIGN_APPROVAL_AND_DISPATCH.md), and [failure tests](TESTING_AND_ACCEPTANCE.md).
