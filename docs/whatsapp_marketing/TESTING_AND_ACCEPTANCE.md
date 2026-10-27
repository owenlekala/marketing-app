# Testing and acceptance

Owner: WA-R17. Harness checks are implemented in WA-P0-004; feature acceptance remains required as its code is added. This file defines required evidence; [progress](PROGRESS.md) records results. Use a disposable site, synthetic identities, a fake clock and a provider fake for automated tests. Real sends require an explicitly authorised test/pilot recipient.

## Test layers and commands

- Pure unit tests: eligibility, state transitions, canonical hashing, step validation, schedule/timezone decisions, provider classification and reconciliation.
- Frappe integration tests: DocType validation, database constraints, permissions, hooks, migrations, transaction rollback, outbox and scheduler recovery.
- Provider contract tests: checked-in synthetic fixtures for the explicitly supported API version, including success, throttling, rejection, status, template, signature and media shapes. Never record real tokens/personal payloads.
- Browser tests: native forms/lists/Page controls, both themes, keyboard, smaller viewports and two-user access. Use the app's selected supported Playwright harness established in P0, not unverified browser mocks.
- Operational qualification: queue outages, worker termination, backup restore, load, retention and a limited authorised live pilot.

### Executable harness (WA-P0-004)

Run from the `tag_marketing` repository root, with the pinned disposable environment running. The [quality controller](../../development/whatsapp_marketing/quality.py) owns commands; it uses the site/project in the [runtime lock](../../development/whatsapp_marketing/runtime.lock.json), never an implicit production site:

```sh
python3 development/whatsapp_marketing/runtime.py up
python3 development/whatsapp_marketing/quality.py setup
python3 development/whatsapp_marketing/quality.py all
```

For focused work, replace `all` with `docs`, `lint`, `unit`, `integration`, `browser` or `egress`. `setup` installs hash-locked Python tools and `npm ci --ignore-scripts` from package-lock.json into the browser service's node_modules volume. The `browser-setup` service has installation network access; test containers attach only to an internal Docker network with the real web/realtime services. Dependency installation requires network access; test execution permits only explicit local infrastructure. Run setup again when a lock changes. Setup generates its Dockerfile from the pinned Bench base in the runtime lock and the exact Playwright version in package.json, then builds a Chromium-only local image. The generated file is ignored build output, not a second editable configuration. Tested image IDs belong to progress; rebuilding may resolve newer OS packages and requires requalification. No optional browser service starts during ordinary application startup.

- `docs`: executes the read-only canonical structural checker retained below, with no copied implementation.
- `lint`: Ruff lint/format checks across app/runtime Python and mypy across the same sources. Ports, deterministic fakes, network helpers and pure unit tests require typed definitions; framework-facing code uses checked bodies with dynamic third-party imports. Browser execution also runs `npm run typecheck` (strict TypeScript). These checks do not imply complete static typing of Frappe.
- `unit`: standard-library unittest discovery under `tag_marketing/tests/unit`, importing no Frappe/site code. Reuse [OfflineTestCase](../../tag_marketing/tests/support/cases.py). It denies socket/DNS/direct-IP/UDP egress and fails in cleanup even if the attempted-network exception was caught. Deliberate guard tests use an inner isolated guard; they prove a normal leaking test fails. Never catch or disable guards in ordinary tests.
- `integration`: supported `bench --site <locked-site> run-tests --app tag_marketing` from the Bench root. Reuse [AppIntegrationTestCase](../../tag_marketing/tests/support/integration.py), not deprecated FrappeTestCase. It validates the disposable site, retains native Frappe setup and adds per-test rollback/user restoration and explicit MariaDB/Redis host-and-port allowances. This checkout rolls back at class cleanup; the app adds per-test isolation. The rollback probe inserts a synthetic Role, then the following test proves it is absent. The default Bench command also discovers the pure unittest classes under its unspecified category; use `unit` for site-independent runs.
- `browser --browser-project mobile` (or desktop-light, desktop-dark, tablet) limits a diagnostic run to one configured project while retaining the same fresh fixtures, strict TypeScript, cleanup and three egress probes. Omit the option for the full matrix. It does not replace the other project evidence.
- `browser --browser-grep '<Playwright test expression>'` narrows a diagnostic run to matching cases while retaining fixture setup/cleanup and the egress probes; combine it with `--browser-project` to qualify one viewport. Use this for focused iteration, then run the complete browser matrix before closing a task.
- `browser`: real Chromium and native login/Desk against the live disposable site, with independent agent/manager contexts, keyboard focus, light/dark mode and 1440/1024/390px viewports. [Playwright configuration](../../playwright.config.ts) owns project details. Same-site requests/realtime are allowed; external HTTP, WebSocket and Playwright API calls are rejected. Service workers are blocked. The `egress` action runs three deliberate HTTP, WebSocket and API probes without login or database fixtures. The controller validates their structured JSON report: all three must fail only for their guard assertions, with no retries, skipped tests or unrelated errors. Browser runs include the same probes. Their output directory is separate from passing screenshots.

Navigation tests cover every marketing role at desktop light; Marketing Manager additionally covers dark, tablet and phone. Other role/project combinations are explicitly skipped to avoid duplicating permission checks across visual variants. Those skips are not counted as passing cases. The three negative egress probes must still all execute and fail only for the intended guard assertions.

The [application ports](../../tag_marketing/application/ports.py) expose an aware-UTC clock and byte HTTP transport. [Test fakes](../../tag_marketing/tests/support/fakes.py) advance explicit instants without sleeping and consume scripted responses/exceptions; extra or unused calls fail. This transport fake does not assert a Meta Graph API contract. Add versioned provider fixtures in P2/P3 when those payloads are verified; business-state and dispatch tests belong to their feature tasks.

### Synthetic users, data and cleanup

[Fixture helpers](../../tag_marketing/tests/support/site.py) own synthetic identities: an ERPNext Sales User and a System Manager plus Marketing User, Marketing Manager, Marketing Analyst and WhatsApp Agent, with welcome email disabled. The first two retain the harness permission baseline; marketing identities qualify role-specific navigation and feature access. Integration fixtures roll back. Browser credentials are newly generated, captured without printing, placed in a mode-0600 ignored file, and mounted only into the browser service. Normal Bench services cannot read host `.local` credentials. Browser traces/video are off to avoid retaining login secrets; screenshots contain synthetic users only.

Each browser run persists a mode-0600 `browser-run.json` recovery manifest before setup, then creates unique accounts carrying its run identifier in both email and ownership metadata. Setup and cleanup use the same infrastructure-only network guard as integration tests. Cleanup validates every candidate before deleting any user and targets only that run. A nonblocking host lock prevents overlapping quality runs. The controller attempts cleanup in `finally` and removes the manifest/credentials only after successful database cleanup; failures retain recovery state and block another run. After an interrupted run, inspect the ignored artifacts and run `python3 development/whatsapp_marketing/quality.py cleanup` from the app root once the owned site is available. Do not delete the manifest to bypass a failed cleanup. If a legacy credential file exists without a manifest, inspect its origin and reconcile only confirmed harness-owned records before removing the orphan file; never guess an account owner. Never run fixture helpers on a production site. Screenshots are under `development/whatsapp_marketing/.local/test-results/browser/<run_id>/`; each run keeps a separate directory so later diagnostics do not replace earlier evidence. Native login waits for navigation commit and then actual Sidebar/theme readiness (60 seconds per boundary, 120 seconds per case); this accommodates cold development assets without retries or fabricated responses. These images are local evidence, not proof of future marketing page parity.

The Python guard is process-local, not a firewall. Automated app tests must use these bases and fakes. Run synchronous worker logic under the guard; future subprocess/worker tests must install a guard in that process or isolate network at container level. Do not send work to unguarded live workers to qualify provider behaviour. Browser containers additionally have no external Docker route. Installation, browser-driver control and database/cache traffic are infrastructure boundaries, not provider traffic.

### Schema foundation qualification (WA-P1-001)

Run `python3 development/whatsapp_marketing/qualify_foundation.py` from the app root after the owned runtime is available. The [qualification controller](../../development/whatsapp_marketing/qualify_foundation.py) uses only the bootstrap service's existing secret mounts, refuses an existing qualification site, creates `wa-foundation-qualification.localhost`, installs only ERPNext and TAG Marketing, checks all 36 records/declared indexes, customises one setting/role, migrates twice and verifies preservation of those values and the encrypted HMAC identity. It drops only its newly created site in finally; no production or main disposable site is reset. Captured subprocess output is suppressed on failure because it may contain credentials. If site creation itself fails, inspect any partial qualification site before rerunning; never remove an unrelated site to bypass the refusal.

The [foundation integration suite](../../tag_marketing/tests/test_foundation.py) checks every documented parent field/type/link, exact database indexes, all compound unique keys, optional provider IDs, a real two-connection uniqueness race, generic write/share bypasses, company restrictions, inbox assignment/team/cursors, settings forgery, secret preservation and role isolation. Fixtures use synthetic trusted SQL solely to test boundaries before feature services exist. Normal feature tests must use their actual commands once implemented. Retained settings policy tests run without Frappe under the offline unit base.

## Acceptance scenarios

### WA-A01 — Foundation and migrations

Install on a fresh compatible ERPNext site; confirm required-app errors are actionable. Migrate twice, rerun seeds, change an administrator-owned navigation preference and migrate again. Assert no duplicate owned records, no erased customisation, no payroll dependency and no unrelated source changes.

### WA-A02 — Native UI

Compare every sidebar destination against the same-version ERPNext reference UI. Capture 1440px light/dark screenshots, 1024px and 390px layouts, keyboard/focus and loading/empty/error cases. Confirm no leaked global CSS, duplicate shell or placeholder metrics.

### WA-A03 — Audience and source permissions

Use a Marketing User with and without Sales permissions, shared Customer with two Contacts, Contact with multiple phones, missing Lead company and mismatched Sales Order company. Check lists, direct IDs, previews, snapshots, report drill-downs and source links. Denied data must never appear in counts or templates.

### WA-A04 — Consent, imports and suppression

Import valid/invalid/duplicate rows, unknown evidence and CSV formula-like labels; confirm profile creation is separate from marketing eligibility. Repeat confirmation/crash-resume. Withdraw after snapshot approval, replay an older grant, and explicitly regrant with newer evidence. Assert one effective identity, no duplicate grants and suppression across numbers. Race withdrawal against submission reservation; a recorded withdrawal must block subsequent submissions.

### WA-A05 — Connections and templates

Validate wrong token/WABA/version, discover multiple numbers, rotate secrets, disable/reconnect and verify actual signed POST delivery. Test approved/rejected/paused templates, language and variable errors, private header media and repeated submission commands. An HTTP credential success alone cannot mark full readiness.

### WA-A06 — Webhook authentication and replay

Exercise GET token challenge and POST raw-body HMAC separately. Reject changed bytes, unknown routing and wrong WABA/number. Simulate database failure before acknowledgement; require non-200. Replay envelopes and individual elements, mixed supported/unsupported types, delayed/future timestamps and status-before-acceptance. Assert exactly one logical business effect for each unique element, without claiming provider exactly-once delivery.

### WA-A07 — Campaign approval and state

Approve a completed snapshot/test hash; attempt stale revision approval and material edits. Manager self-approval is allowed; ordinary User launch is denied. Future start/expiry and zero/oversize audiences block appropriately. After first submission require Clone for material edits. Pause/resume/cancel preserve historical outcomes; late delivery updates continue after Completed.

### WA-A08 — Dispatch failure recovery

Inject crashes before commit, after commit/before enqueue, after claim, after Submitting/before HTTP, after provider acceptance/before persistence and during outcome persistence. Confirm safe pre-submission reclaim, post-boundary Unknown, bounded explicitly safe retries and retained frequency reservations. Concurrent workers cannot double-claim or overwrite newer leases. Late evidence correlates only with verified identities; unknowns have no blind Retry All.

### WA-A09 — Inbox scope and realtime

Use two agents, distinct teams and a manager. Verify assignment filters, paginated messages, private notes/files and current-user read cursors. Reassign during viewing/download and deny subsequent access. Realtime carries no body content to site-wide rooms; reconnect/refetch does not expose a former assignment.

### WA-A10 — Reply window and human ownership

Check just before, exactly at and after 24-hour expiry using trusted inbound time. Delay an old webhook; it must not reopen a window. Expire a queued free-form reply before worker submission. Race an agent reply/handover against automatic sending; committed Human mode blocks new automated submissions. Explicit resume rechecks readiness rather than renewing the window.

### WA-A11 — Automations and CRM events

Validate every supported trigger/action, forward branching, invalid targets/cycles and 100-step bound. Simulation has no business/provider mutations. Publish during an active wait and preserve the old version. Restart workers during wait/tag/send, replay source hooks and roll back source transactions. Assert one effective step, no event from rolled-back sources, no reprocessing historical events on new publication and correct run-as permissions.

### WA-A12 — Reports and estimates

Seed known message/event fixtures, including duplicate/late statuses, tests, missing reads, inferred/exact replies and unknown attempts. Reconcile counts/denominators to authorised raw records. Validate estimate rate date/category/market/currency and missing-rate behaviour; never label estimates actual invoice totals. Analyst cannot retrieve raw bodies/manager exports.

### WA-A13 — Operational controls

Stop workers/Redis/scheduler; verify queue-age and heartbeat alerts. Disable sending while work is queued: inbound processing continues, no new submission passes the live switch. Pilot scope rejects every recipient outside its explicit allowlist; Live scope rejects missing pilot evidence. Recover from database records after enqueue failure. Authentication failure degrades affected connection and alerts operators.

### WA-A14 — Security and media

Try direct managed-field edits via REST/import, cross-company IDs, arbitrary source/SQL/step parameters, XSS in messages/variables, unsupported MIME, oversized files, hostile media redirects, unauthorised evidence and CSV export formulas. Assert rejection/redaction and private file ownership. Check logs/responses for secrets and excessive personal content.

### WA-A15 — Upgrade and restore

Back up a populated disposable site including files and encryption-key recovery material; migrate twice and restore to an isolated environment. Keep sending disabled on restore. Reconcile accepted/unknown outbox against provider evidence before re-enable; restoring a database must not automatically resend old pending/submitting work.

### WA-A16 — Capacity and responsiveness

Seed 50,000 contacts, multiple campaigns and enough conversation history to require pagination. Snapshot 10,000 recipients with bounded batches; reject 10,001 eligible recipients clearly. Under one marketing worker and controlled fake-provider throughput, measure memory, query counts, queue age and inbox p95 query latency. Initial gate: inbox query p95 below 2 seconds and individual webhook persistence p95 below 1 second on a recorded 4-vCPU/8-GB staging allocation, excluding external provider latency. No full recipient/message load into browser or one unbounded worker array. Record dataset, database, Redis/worker configuration and results; adjust design rather than silently lowering the target.

### WA-A17 — Retention and subject requests

Missing policy blocks live enablement. Preview and execute cleanup on expired raw/media/content records; enforce legal hold and private outputs. Erasure preserves required audit/suppression integrity under configured policy, and reimport cannot reactivate marketing. Access/erasure commands verify requester/actor authority.

### WA-A18 — Documentation consistency

Check required file inventory, relative links/anchors/local source paths, unique IDs, task prerequisites/cycles, all sidebar pages, requirement→task→acceptance coverage, Mermaid fences, and agreement on statuses/defaults. Keep progress truthful. This check completes only documentation readiness, never application release qualification.

## Evidence policy

Record task results using the [progress evidence format](PROGRESS.md#implementation-evidence-format) and [shared completion rules](tasks/README.md#shared-completion-rules). Screenshots use synthetic data. Production release requires all applicable scenarios and [release gates](OPERATIONS_AND_RELEASE.md), not a percentage of checked tasks.

## Repeatable documentation structural check

Run the following from the `tag_marketing` repository root. It reads files only and exits nonzero on inventory, link/anchor, source path, dependency, ID or coverage errors. Keep the expected inventory updated for intentional future additions. It also rejects duplicate files, repeated shared paragraphs, stale handbook paths, a second marketing handbook and copied status checklists. Task completion checkboxes belong only to their definitions. It validates Mermaid fence structure, not visual rendering; inspect/render diagrams separately before changing their syntax. Semantic state/default agreement still requires review.

```sh
python3 - <<'PY'
from pathlib import Path
import re, collections, hashlib, json, sys
root=Path('docs/whatsapp_marketing').resolve()
expected_root='README AGENTS IMPLEMENTATION_RULES PRODUCT_REQUIREMENTS IMPLEMENTATION_PLAN FRAMEWORK_AND_SETUP REFERENCES ARCHITECTURE DATA_MODEL API_CONTRACTS ERPNext_INTEGRATION UI_DESIGN_SYSTEM PERMISSIONS_AND_PRIVACY MESSAGING_AND_RELIABILITY TESTING_AND_ACCEPTANCE OPERATIONS_AND_RELEASE TRACEABILITY PROGRESS IMPLEMENTATION_KICKOFF'.split()
expected=set(x+'.md' for x in expected_root)
expected|={'decisions/'+x+'.md' for x in ['README','ADR-001-APP-AND-DESIGN-BASELINE']}
expected|={'pages/'+x+'.md' for x in ['README','OVERVIEW','CONNECTIONS','CONTACTS_AND_IMPORTS','AUDIENCE_SEGMENTS','TEMPLATES','CAMPAIGNS','INBOX','AUTOMATIONS','REPORTS','SETTINGS']}
expected|={'flows/'+x+'.md' for x in ['README','CONNECTION_AND_ONBOARDING','AUDIENCE_AND_CONSENT','CAMPAIGN_APPROVAL_AND_DISPATCH','WEBHOOKS_AND_DELIVERY','INBOX_AND_HANDOVER','AUTOMATION_EXECUTION']}
expected|={'tasks/'+x+'.md' for x in ['README','P0-ENVIRONMENT-AND-BOOTSTRAP','P1-APP-AND-NATIVE-UI','P2-CONNECTIONS-AND-WEBHOOKS','P3-AUDIENCES-AND-TEMPLATES','P4-CAMPAIGNS-AND-DISPATCH','P5-INBOX','P6-AUTOMATIONS','P7-REPORTING-AND-RELEASE']}
files={p.relative_to(root).as_posix():p for p in root.rglob('*.md')}
errors=[]
if set(files)!=expected: errors.append(f'Inventory mismatch missing={expected-set(files)}, extra={set(files)-expected}')
contents={p:p.read_text() for p in files.values()}
def plain(s):return re.sub(r'^```[^\n]*\n.*?^```\s*$', '',s,flags=re.M|re.S)
def headings(s):
 counts=collections.Counter(); anchors=set()
 for h in re.findall(r'^#{1,6}\s+(.+)$',plain(s),re.M):
  slug=re.sub(r'[^\w\- ]','',h.lower()).replace(' ','-')
  n=counts[slug];counts[slug]+=1;anchors.add(slug+(f'-{n}' if n else ''))
 return anchors
links=0;source_paths=set();mermaid=0
for path,s in contents.items():
 if len(s.split())<70:errors.append(f'Too short: {path.name}')
 if len(re.findall(r'^```',s,re.M))%2:errors.append(f'Unbalanced code fences: {path}')
 mermaid+=len(re.findall(r'^```mermaid\s*$',s,re.M))
 for href in re.findall(r'(?<!!)\[[^\]]*\]\(([^)]+)\)',plain(s)):
  if re.match(r'^[a-z]+:',href):continue
  href=href.strip('<>'); target,_,fragment=href.partition('#'); dest=(path.parent/target).resolve() if target else path
  links+=1
  if not dest.exists():errors.append(f'Broken link {path.relative_to(root)} -> {href}');continue
  if not dest.is_relative_to(root):source_paths.add(str(dest))
  if fragment and dest.suffix=='.md' and fragment not in headings(dest.read_text()):errors.append(f'Broken anchor {path.relative_to(root)} -> {href}')
reqs=set(re.findall(r'\*\*(WA-R\d{2})\s+—',contents[root/'PRODUCT_REQUIREMENTS.md']))
acceptance=set(re.findall(r'^### (WA-A\d{2})',contents[root/'TESTING_AND_ACCEPTANCE.md'],re.M))
tasks={};req_tasks=collections.defaultdict(set);acc_tasks=collections.defaultdict(set)
for path,s in contents.items():
 if path.parent.name!='tasks' or path.name=='README.md':continue
 parts=re.split(r'^## (WA-P\d-\d{3})\s*$',s,flags=re.M)
 for i in range(1,len(parts),2):
  tid,body=parts[i:i+2]
  if tid in tasks:errors.append(f'Duplicate task {tid}')
  dep=re.search(r'\*\*Depends on:\*\* (.+)',body)
  deps=re.findall(r'WA-P\d-\d{3}',dep.group(1)) if dep else []
  tasks[tid]=deps
  if not dep:errors.append(f'Missing dependencies section {tid}')
  for label in ['Requirements','Acceptance','Read first','Implementation and boundaries','Failure cases and verification','Completion evidence']:
   if f'**{label}:**' not in body:errors.append(f'Missing task contract {tid} {label}')
  for req in re.findall(r'WA-R\d{2}',body):
   if req not in reqs:errors.append(f'Unknown requirement {req} in {tid}')
   req_tasks[req].add(tid)
  for a in re.findall(r'WA-A\d{2}',body):
   if a not in acceptance:errors.append(f'Unknown acceptance {a} in {tid}')
   acc_tasks[a].add(tid)
  if len(re.findall(r'^- \[[ xX]\] ',body,re.M))!=1:errors.append(f'Task must own exactly one completion checkbox: {tid}')
visiting=set();visited=set()
def visit(t):
 if t in visiting:errors.append('Dependency cycle '+t);return
 if t in visited:return
 visiting.add(t)
 for d in tasks[t]:
  if d not in tasks:errors.append(f'Unknown dependency {t}->{d}')
  else:visit(d)
 visiting.remove(t);visited.add(t)
for t in tasks:visit(t)
if len(tasks)!=32:errors.append(f'Expected 32 tasks, got {len(tasks)}')
if len(reqs)!=18:errors.append(f'Expected 18 requirements, got {len(reqs)}')
if len(acceptance)!=18:errors.append(f'Expected 18 acceptance scenarios, got {len(acceptance)}')
for r in reqs:
 if not req_tasks[r]:errors.append(f'Uncovered requirement {r}')
 if r not in contents[root/'TRACEABILITY.md']:errors.append(f'Requirement missing traceability {r}')
for a in acceptance:
 if not acc_tasks[a]:errors.append(f'Untasked acceptance {a}')
for path,s in contents.items():
 for task in re.findall(r'WA-P\d-\d{3}',s):
  if task not in tasks:errors.append(f'Unknown task reference {task} in {path.name}')
 for req in re.findall(r'WA-R\d{2}',s):
  if req not in reqs:errors.append(f'Unknown requirement ref {req} in {path.name}')
 for a in re.findall(r'WA-A\d{2}',s):
  if a not in acceptance:errors.append(f'Unknown acceptance ref {a} in {path.name}')
 if re.search(r'\b(TODO|TBD|FIXME|lorem ipsum)\b',plain(s),re.I):errors.append(f'Unresolved placeholder in {path.name}')
# Reject copies and duplicated ownership, while preserving links and feature-specific detail.
file_hashes=collections.defaultdict(list)
paragraphs=collections.defaultdict(list)
legacy_path='docs/'+'TAG_'+'WAmarketing'
for path,s in contents.items():
 file_hashes[hashlib.sha256(s.encode()).hexdigest()].append(str(path.relative_to(root)))
 if legacy_path in s:errors.append(f'Stale handbook path in {path.name}')
 for block in re.split(r'\n\s*\n',plain(s)):
  block=' '.join(block.split())
  if len(block)>180 and not block.startswith('#'):paragraphs[block].append(str(path.relative_to(root)))
for matches in file_hashes.values():
 if len(matches)>1:errors.append(f'Duplicate files: {matches}')
for matches in paragraphs.values():
 if len(matches)>1:errors.append(f'Duplicated shared paragraph: {matches}')
for rel in ['tasks/README.md','PROGRESS.md']:
 if re.search(r'^- \[[ xX]\] ',plain(contents[root/rel]),re.M):errors.append(f'Duplicate task/phase status tracking in {rel}')
for sibling in root.parent.iterdir():
 candidate=sibling/'PRODUCT_REQUIREMENTS.md'
 if sibling!=root and candidate.is_file():
  other=candidate.read_text()
  if 'WA-R01' in other and 'tag_marketing' in other:errors.append(f'Second marketing handbook: {sibling}')
print(json.dumps({'files':len(files),'words':sum(len(s.split()) for s in contents.values()),'relative_links':links,'distinct_local_sources':len(source_paths),'mermaid_diagrams':mermaid,'requirements':len(reqs),'tasks':len(tasks),'acceptance':len(acceptance),'duplicate_file_groups':sum(len(v)>1 for v in file_hashes.values()),'duplicate_paragraph_groups':sum(len(v)>1 for v in paragraphs.values()),'errors':errors},indent=2))
sys.exit(bool(errors))
PY
```

### Persisted progress browser fixtures

The CLI fixture helper additionally prepares five run-owned WA Operation states linked to one synthetic WA Connection. There is no whitelisted fixture writer. If no marketing company is configured, it temporarily supplies a raw synthetic Company; existing configured companies/settings are preserved. A mode-0600 site-private `wa-progress-<run_id>.json` recovery file records only run ownership and the prior company reference, never credentials.

Cleanup validates user markers first, then operation hashes/requesters/targets and connection markers before deleting any record. It locks and compares the marketing-company setting before restoring a temporary value, refuses a changed setting, checks native linked/dynamic-linked records before removing fixture targets, and commits all cleanup atomically. Unexpected links or ownership changes retain both recovery layers for inspection. The site-private recovery file is removed only after successful commit. Tests use the same exact disposable-site and network gates as the existing harness; synthetic direct persistence is shared in the test-only persistence helper and never imported by product code.

Browser feedback checks use persisted statuses, real operation GETs, actual offline/recovery transitions and native Dialog controls. A renderer-input test supplies malicious text and a stale code directly to the public component API; it does not fabricate a server response. No live sending or feature jobs are enabled by these fixtures.
