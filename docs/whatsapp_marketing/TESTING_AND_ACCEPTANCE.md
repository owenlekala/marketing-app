# Testing and acceptance

Owner: WA-R17. Application tests have not run. This file defines required evidence; [progress](PROGRESS.md) records results. Use a disposable site, synthetic identities, a fake clock and a provider fake for automated tests. Real sends require an explicitly authorised test/pilot recipient.

## Test layers and commands

- Pure unit tests: eligibility, state transitions, canonical hashing, step validation, schedule/timezone decisions, provider classification and reconciliation.
- Frappe integration tests: DocType validation, database constraints, permissions, hooks, migrations, transaction rollback, outbox and scheduler recovery.
- Provider contract tests: checked-in synthetic fixtures for the explicitly supported API version, including success, throttling, rejection, status, template, signature and media shapes. Never record real tokens/personal payloads.
- Browser tests: native forms/lists/Page controls, both themes, keyboard, smaller viewports and two-user access. Use the app's selected supported Playwright harness established in P0, not unverified browser mocks.
- Operational qualification: queue outages, worker termination, backup restore, load, retention and a limited authorised live pilot.

Future command examples, inside `<bench-root>` on `<test-site>`:

```sh
bench --site <test-site> set-config allow_tests true
bench --site <test-site> migrate
bench --site <test-site> run-tests --app tag_marketing
bench build --app tag_marketing
```

Run the app's declared lint/type/browser scripts after bootstrap creates them. Document their exact commands then; do not claim an npm/pytest command exists before configuring it. Keep outbound networking disabled in the automated suite and fail on unexpected provider traffic.

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
