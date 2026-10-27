# Progress and evidence

Last baseline review: 27 October 2026. Implementation: **WA-P0-001 through WA-P0-004 and WA-P1-001 through WA-P1-002 verified; WA-P1-003 is next**. Production readiness: **Not qualified**. Live sending: **Not enabled by this work**.

## Inspected evidence

- Frappe source: 16.53.0, `e8d41dd006`; ERPNext: 16.52.1, `ade850bbd6`.
- Local manifests require Python 3.14 and Node >=24.
- Local native navigation/theme/DocType examples were inspected; see [references](REFERENCES.md).
- Current task evidence below qualifies the disposable framework/site runtime. The app scaffold is installed and verified in WA-P0-003; visual parity, business features and provider callbacks remain unimplemented/unqualified.
- The canonical handbook and runtime now live inside the standalone `tag_marketing` Git repository; see WA-P0-003 evidence below.

## Completion ownership

Track completion only in the [phase task definitions](tasks/README.md). Derive phase readiness from those tasks and the [phase gates](IMPLEMENTATION_PLAN.md#phase-sequence-and-gates); do not maintain another set of task or phase checkboxes here. This file records implementation evidence and validation history.

## Documentation validation

Initial pack validation on 27 October 2026, before this redundancy review, used the repeatable structural checker in [testing and acceptance](TESTING_AND_ACCEPTANCE.md#repeatable-documentation-structural-check):

- PASS: exact inventory of 48 requested Markdown documents.
- PASS: 728 relative links/anchors and 43 distinct referenced local source paths resolve.
- PASS: 18 stable requirements, 32 uniquely identified unchecked implementation tasks and 18 acceptance scenarios are connected through traceability.
- PASS: all task prerequisites resolve and dependency graph has no cycles.
- PASS: all 10 Sidebar destinations have specifications; all six flow files include Mermaid, with seven diagram blocks overall including architecture.
- PASS: fenced-code structure and absence of unresolved prose placeholders.
- Reviewed: campaign transitions, Test/Pilot/Live gates, source mappings, template/API actions, unknown-outcome handling and frozen/live-policy precedence agree across owning specs and related pages/tasks.
- Limit: Mermaid diagrams were inspected as source and structurally checked; graphical rendering was not exercised. Runtime commands and application acceptance scenarios were not executed because no app/runtime implementation is part of this documentation change.

This qualifies documentation structure only and does not check any application phase above. The embedded read-only checker is retained for future documentation edits.

## Redundancy review

Reviewed 27 October 2026 after the handbook directory was renamed:

- Canonical workspace handbook is `docs/whatsapp_marketing/`; corrected stale kickoff, bootstrap and structural-check paths.
- Centralised task completion guidance in tasks/README.md and page-wide guidance in pages/README.md/the design system. Preserved feature-specific implementation, failure and acceptance details.
- Removed copied task-index and phase-progress checkboxes. Each of the 32 task definitions owns one completion checkbox; this file owns evidence only.
- Retained all 48 documents, 18 requirements, 18 acceptance scenarios and seven diagrams. Structural validation reports no duplicate files or repeated shared paragraphs, broken references, missing task prerequisites or dependency cycles.
- Exercised the checker with in-memory duplicate-paragraph, stale-path and copied-checklist examples: all rejected. A legitimately completed task checkbox remains valid. No application task was changed to complete.
- Removed instructions permitting synchronised editable handbook copies; a future repository move leaves only a pointer at the previous location.

## Implementation evidence format

Append one entry per task: task ID; status (Not started/In progress/Blocked/Verified); app commit; runtime/site type; exact commands and results; acceptance IDs; screenshot/artifact paths; outstanding checks and next action. Use synthetic data and redact secrets. Never replace a failing result with an unsupported success claim.

## Known implementation prerequisites

- Begin WA-P1-003 shared native UI and error/progress foundations using the qualified navigation; keep sending disabled.
- Verify current official Meta API version/permissions/payloads; some developer pages were rate-limited during planning.
- Obtain business-owned credentials, approved templates and explicitly authorised test recipients during the relevant task.
- Configure retention policy, rate controls and operational ownership before live enablement.

## WA-P0-001 — Source and deployment baseline

Status: **Verified** on 27 October 2026. This closes source/environment discovery only. The runtime is not provisioned and no app commit exists. Task completion is maintained only in the phase task file.

### Source and instruction verification

- Read the handbook, documentation AGENTS.md, implementation rules, kickoff, product requirements, setup guide, reference register and task contract before execution. No other workspace AGENTS.md was found by `rg --files -g 'AGENTS.md' -g '!**/node_modules/**'`.
- `git -C <repository> rev-parse HEAD`, `git -C <repository> branch --show-current` and `git -C <repository> status --short` were executed for each existing source repository. All four working trees were clean before changes.
- Frappe `version-16`: `e8d41dd0061a32ee781caefe5d0b0d2bb7c15362`, version 16.53.0.
- ERPNext `version-16`: `ade850bbd6a7412e9994a9637d2c5c713771632a`, version 16.52.1.
- Payroll `main`: `dc958457b062a76a04014957dba3e4c1cc02fa19`, version 2.1.0. Docker source `main`: `2e6c8573a2af9882df705ce4247a26eb69c4f597`.
- Read version assignments and manifests without importing application code. Requirements match the accepted baseline: Frappe Python `>=3.14,<3.15`, Node `>=24`; ERPNext Python `>=3.14` and Frappe `>=16.50.0,<17.0.0`. Confirmed fork origins in the reference register without exposing URL credentials.

### Host and runtime inventory

- `uname -m`: `x86_64`.
- `python3 --version`: Python 3.9.6 at `/usr/bin/python3`; `python3.14` is absent from PATH. Host Python cannot run the selected framework. Discovery used text/JSON parsing rather than importing or compiling its newer Python syntax.
- `node --version`: v24.15.0, compatible with the declared Node minimum. Executable: `/Users/owen/.nvm/versions/node/v24.15.0/bin/node`.
- Executable lookup found no `bench`, `yarn`, `uv`, `redis-cli` or `mariadb` on PATH. This does not claim those tools are absent inside an uninspected container.
- Docker CLI exists at `/usr/local/bin/docker`; Docker Desktop application exists. `docker compose version` returned v5.1.3.
- `docker context show` returned `desktop-linux`; `docker context inspect desktop-linux --format '{{.Endpoints.docker.Host}}'` returned `unix:///Users/owen/.docker/run/docker.sock`.
- `docker ps --format '{{.Names}}\t{{.Image}}\t{{.Status}}'` failed with socket permission denial in the sandbox. The same read-only inventory outside the sandbox failed with **Cannot connect to the Docker daemon**. No container inventory was obtained. This establishes an unreachable configured daemon, not proof that all containers or other contexts are stopped.
- A workspace marker check found no `sites`, `env`, `apps`, `Procfile` or `tag_marketing` at the root. Bounded discovery found no Bench/site configuration; `frappe_docker/images/bench` is an image-source directory, not an installed Bench. No secret-bearing site configuration was printed.

### Acceptance, changes and handoff

- WA-A01: source/runtime compatibility prerequisites inspected; installation and repeat-migration portions belong to later tasks and were not claimed as passed.
- WA-A18: executed the retained read-only structural checker using `python3` after updating the evidence and the authoritative task checkbox. Passed: 48 documents, 640 relative links, 43 source paths, 18 requirements, 32 tasks and 18 acceptance scenarios; zero duplicate file/paragraph groups, dependency cycles or validation errors. Exactly one task is checked complete. Final Git status checks confirm all four existing source repositories remain clean.
- Changed only the baseline task checkbox, current evidence and the owning setup/reference descriptions. No framework/payroll/Docker source, service, image or database was modified; no messages were sent.
- Next task: **WA-P0-002**. Restore access to the intended local Docker daemon, verify its context, and establish the documented pinned Python 3.14/Node 24 development runtime and disposable site. Do not scaffold the app until that task's prerequisites and verification pass.

## WA-P0-002 — Disposable development runtime

Status: **Verified** on 27 October 2026. All runtime checks below passed; only this task's authoritative checkbox was closed. No marketing application repository/commit exists yet.

- Started the installed Docker Desktop application using `open -a Docker`. `docker desktop status` subsequently reported running; daemon access was verified outside the sandbox. Engine version: 29.4.1; allocation: 4 CPUs and 8,325,570,560 bytes RAM.
- Implemented one runtime controller, Compose definition, image/source lock, bootstrap and verifier under `development/whatsapp_marketing`. The setup guide links the implementation; there is no copied handbook or second image/environment lock.
- Resolved Bench, MariaDB and Redis image references to full SHA-256 digests. Exact identifiers are owned by runtime.lock.json. Local secrets are generated once under ignored private directories and redacted from bootstrap errors.
- `python3 development/whatsapp_marketing/runtime.py config` passed Compose validation. Host-Python AST parsing of all three scripts, digest-format checks and private-directory permission checks passed.
- The owned `tag-wa-dev` MariaDB and both Redis containers are healthy. No pre-existing containers or source repositories were reconfigured. The pinned Bench image was verified as Python 3.14.8, Node v24.22.0, Yarn 1.22.22 and Bench 5.31.0; supported `bench init` options were checked using the image's CLI help.
- An initial launch encountered missing port variables after configuration was consolidated into the lock; the controller now supplies both ports from that single source. Revalidation passed and the idempotent project launch was restarted without deleting volumes.
- Bootstrap initially encountered a root-owned empty Bench volume. Runtime inspection confirmed UID/GID 1000 for the image user; the initializer now resolves that identity from the image, and `nocopy` mounts prevent empty-volume copy-up from replacing ownership. The corrected run completed both pinned source installs, site creation, ERPNext installation, two migration passes and the asset build without resetting volumes or modifying the host source repositories.
- Only individual non-secret runtime files are mounted into ordinary services. Root/admin secret file mounts are limited to database/bootstrap as appropriate. Bootstrap logs stream with known credentials redacted; captured output is bounded.

### Verification results and next task

- `python3 development/whatsapp_marketing/runtime.py up`: exited 0 after complete bootstrap and startup of all eight owned services. Site: `wa-marketing.localhost`; Bench root inside its volume: `/home/frappe/dev/frappe-bench`. No marketing app, business data import or outbound integration was created.
- `python3 development/whatsapp_marketing/runtime.py verify`: exited 0. Actual output: Python 3.14.8; installed apps `frappe`, `erpnext`; database `11.8.9-MariaDB-ubu2404`; Redis cache/queue pings true; web ping and built assets true; realtime Engine.IO handshake true; two workers registered; dedicated marketing queue consumed its harmless job; temporary scheduled probe executed and was removed.
- `python3 development/whatsapp_marketing/runtime.py status`: database/Redis healthy; web, Python realtime, scheduler, normal worker and marketing worker running. Published web/realtime ports bind only to loopback; database/Redis ports are not host-published.
- Host HTTP requests to both local site hostnames at port 18080 returned HTTP 200 and `{"message":"pong"}`. Login-page asset checks were performed by the verifier; authenticated marketing UI/role checks remain later acceptance work.
- An ephemeral-container subprocess probe using a synthetic credential passed log-redaction verification. Runtime AST, digest formatting, Compose interpolation and private credential-directory checks passed. Both cloned application working trees were clean after installation/build; all four host repositories remained clean.
- Acceptance scope: WA-A01 framework installation/repeated migrations and WA-A13 baseline services/actual queue and scheduler execution verified. App-specific permissions, emergency switch, outage recovery and production gates remain for their later tasks; this is not blanket acceptance of the future marketing module.
- Final documentation check passed: 48 files, 646 relative references, 47 local source paths, all 32 task dependencies/18 requirements/18 acceptance scenarios, zero duplicate file/paragraph groups or errors. Runtime syntax and Compose validation passed; mount inspection confirms ordinary web receives no root/admin secret files and host source mounts are read-only. Exactly WA-P0-001 and WA-P0-002 are checked complete.
- Next: **WA-P0-003**. Create the separate application repository and app-level instruction bridge; move the single handbook/runtime implementation into that repository, updating links/mounts while preserving this project, site, volumes and secrets. Do not recreate a parallel environment or handbook.

## WA-P0-003 — Application repository and instruction bridge

Status: **Verified** on 27 October 2026. Initial application commit: `971e7b5966a975e97ac1007a94db578e921126cb` on local branch `main`. That commit intentionally records verification as in progress; this subsequent evidence update closes the task after execution.

- Generated the app using the pinned runtime's `bench new-app --no-git tag_marketing`, with title TAG Marketing, publisher TAG Projects, MIT license and no generated GitHub workflow. The contact email uses the configured local Git identity. Exported the scaffold with `docker cp`; verified every exported file by SHA-256 before replacing only the generated volume copy with a link to `/source/tag_marketing`.
- Initialised the independent repository with `git -C tag_marketing init -b main`. No remote or push was created. Declared Python `>=3.14,<3.15`, Frappe `>=16.53.0,<17.0.0` and ERPNext `>=16.52.1,<17.0.0` through supported Bench dependency metadata. `required_apps` declares ERPNext; no payroll/HRMS dependencies or framework changes.
- Renamed the generated module to `WhatsApp Marketing` and its package to `whatsapp_marketing`, preserving the separate app identity. No UI, business DocTypes, provider integration or empty service abstractions were added.
- Moved the canonical handbook to `tag_marketing/docs/whatsapp_marketing/` and runtime to `tag_marketing/development/whatsapp_marketing/` in the parent workspace. Both previous locations contain only a README pointer. Corrected all sibling source links and development working-directory instructions.
- Added repository-wide AGENTS.md linking the handbook rules and tasks. The nested documentation instructions retain subtree scope; there is no copied parallel rule set or second editable handbook.
- Preserved the existing `tag-wa-dev` project, named volumes, site and generated credentials. Bench soft-links the single host app checkout; pinned Frappe/ERPNext mounts remain read-only. A read-only mode-000 tmpfs masks host `.local` credentials underneath the live app mount. Bootstrap explicitly receives its existing secrets separately.
- The first post-move start exposed an existing database container still referencing the previous secret-file path. Recreated only that owned container with `compose up -d --force-recreate --wait mariadb`, retaining its data volume and unchanged credentials; health checks passed. No volume deletion or site reset occurred.
- Preliminary verification: runtime script syntax, bridge/pointer links, private-directory/file modes and Compose configuration pass. The canonical structural check passes 48 documents, 649 relative references, 48 local sources, 32 tasks, 18 requirements and 18 acceptance scenarios, with zero duplicate files/paragraphs, missing dependencies or link errors.

### Final verification and handoff

- From the parent workspace, `python3 tag_marketing/development/whatsapp_marketing/runtime.py up` exited 0: editable package refresh, installation on the retained site, two migrations, complete asset build, scheduler enablement and service startup succeeded. Future runs use the repository-root commands in the setup guide. `bench get-app --help` confirms this pinned Bench supports the fresh-runtime `--soft-link` registration path.
- `docker exec tag-wa-dev-web-1 bench --site wa-marketing.localhost install-app tag_marketing` exited 0 with ERPNext and TAG Marketing already installed. Module inspection confirms the owned `WhatsApp Marketing` Module Def belongs to `tag_marketing`; Bench resolves the app to `/source/tag_marketing`. No default `Tag Marketing` module was installed.
- `python3 tag_marketing/development/whatsapp_marketing/runtime.py verify` exited 0: Python 3.14.8; installed apps Frappe, ERPNext and TAG Marketing; database 11.8.9; dependency bounds, module registration and credential isolation true; database/Redis, web/assets, realtime, marketing queue and actual scheduled execution probes all passed. RQ reported three registrations during restart recovery; the project runs its two intended worker containers and the dedicated queue consumed the probe successfully.
- Inspected mount metadata for web, realtime, scheduler and both workers: each uses the single writable app source, read-only framework source mounts and the host-credential mask, with no `/run/secrets` mounts. Existing `tag-wa-dev_bench-data`, `tag-wa-dev_db-data` and `tag-wa-dev_queue-data` remain owned by the same project. The web verifier confirms host credentials are inaccessible.
- Parsed compatibility bounds with the runtime's `tomllib`/`packaging`: Python 3.14 accepted, 3.13 and 3.15 rejected; below-minimum framework/app versions and v17 rejected. Both Bench framework working trees and all four host source repositories remain clean. No remote is configured for the new repository.
- Staged-content verification reads generated credentials locally and checks they occur in no staged blob, without printing them. No `.local`, Python cache or credential files are tracked. Removed the redundant runtime `.gitignore`; the repository-level ignore file owns those rules.
- Final canonical structural validation passes with zero link/dependency/duplicate errors. Instruction and old-location pointer links resolve; both old locations contain only their README pointer. Exactly the first three P0 task definitions are complete. Acceptance scope: WA-A01 scaffold installation/repeated migrations and WA-A18 instruction/versioned-documentation governance; app-specific permission, UI and business acceptance remain later work.
- A concurrent local copyright edit to `license.txt` appeared during verification. Preserved it without staging it into the task evidence commit.
- No new marketing UI is introduced in this task, so visual comparison belongs to P1. No live-provider traffic, production deployment, remote repository or payroll/framework modifications occurred. Next task: **WA-P0-004**, supported tests, deterministic provider/clock boundaries and browser harness. Production qualification remains outstanding.

## WA-P0-004 — Test harness and deterministic adapters

Status: **Verified** on 27 October 2026 after the review and combined gate below. Harness implementation commits: `431c8b2e2c1879c296bd124c3a5ee1b45bd48d40` and `9d50ae11f2adb88d202ed9bd12437e50c315b7fc`. Acceptance scope: WA-A01 scaffold checks and WA-A18 executable governance. Production and feature-specific acceptance remain unqualified.

- Added framework-independent clock/byte-transport protocols and scripted test adapters. Pure tests cover UTC advancement, rejected naive/backward time, scripted throttling/timeouts, exhausted/unused provider outcomes and stable captured requests. These are transport harness fixtures, not verified Meta payloads.
- Added process-local socket/DNS/direct-IP/UDP guards and app test bases. A nested leaking-test probe proves that catching an unexpected-network exception still leaves a failing test. App integration tests allow only the owned DB/cache endpoints and restore user/transaction state after every test.
- Inspected the pinned v16 runner and IntegrationTestCase rather than copying deprecated testing examples. The checkout rolls back at class cleanup; the app supplies per-test rollback. Initial executed suites passed four pure tests and four native integration tests, including a cross-test rollback probe and two-user native permission distinction. Additional site-gate/IP-family checks are being rerun.
- Added a single quality controller for dependency setup, Ruff/mypy, pure unittest, Frappe runner and real Playwright. Python dependencies are hash locked; browser packages use npm lockfile integrity. The optional Chromium-only browser image is generated from the locked Bench base and exact Playwright package version, currently 1.58.2; no second editable version pin is maintained. Dependency installation is allowed network access separately from guarded test execution.
- Browser setup uses fresh synthetic agent/manager credentials only, suppresses welcome email and captures credentials without printing. The hardened run ownership and recovery lifecycle is defined in [testing and acceptance](TESTING_AND_ACCEPTANCE.md#synthetic-users-data-and-cleanup). A host lock prevents overlapping quality runs. Normal Bench services retain the host-private mask; browser mounts only synthetic test credentials and its artifact directory.
- Configured native login/Desk smoke coverage for light/dark 1440px, 1024px and 390px Chromium, keyboard focus, distinct sessions and native permission checks. External browser HTTP/WebSocket/API traffic fails the test; a separate negative probe must fail for the guard assertion. The Chromium-only build and locked tool installation are complete; native-browser execution is in progress.
- Preliminary checks: Python lint/format and mypy pass across 23 source files. Documentation validation passes 48 files, 658 relative links, 56 distinct local sources, all requirement/task/acceptance IDs and dependencies, with zero duplicate groups or errors. Existing local license edit is preserved outside this task's changes.

The standard multi-browser image download was too slow to qualify the harness promptly. Stopped only this task's superseded download processes and selected a smaller Chromium-only image on the already locked Python 3.14/Node 24 Bench base; the generator is owned by quality.py.

### Executed harness evidence

- `python3 development/whatsapp_marketing/quality.py setup` exited 0: generated Chromium-only image build, hash-locked Python tools and integrity-locked npm dependencies installed. Tested local image ID: `sha256:a151d1d08a58914d0569b5c1651239c114e40c0024cd772484d70e1d546da63a`. Base runtime remains Python 3.14.8 / Node v24.22.0; Playwright 1.58.2 installed Chromium Headless Shell 145.0.7632.6, revision 1208. The test network reports `Internal=true`.
- Python lint/format and mypy passed across 23 app/runtime files before concurrent runtime edits. After those edits, focused checks of only the owned application/test/quality-controller files passed (13 source files), without formatting the other work. TypeScript `tsc --noEmit` passed in the browser service.
- Pure unittest: **4 passed**. Native `bench --site wa-marketing.localhost run-tests --app tag_marketing`: **5 integration tests passed**, plus the same four pure classes discovered under Frappe's unspecified category. This proves per-test database rollback, module registration, required-app bounds, two-user native permissions and rejection of the wrong site/disabled tests.
- `python3 development/whatsapp_marketing/quality.py browser` exited 0 after the readiness fix: **8 real Chromium cases passed** across two users, desktop light/dark, tablet and mobile. The separate deliberate external HTTP probe failed for the expected guard assertion, and its controller reported PASS. No retries or fabricated application responses were used.
- Early browser runs exposed a five-second cold-navigation assumption and testing before UI startup. A later combined run exposed the same root issue while the theme API was still undefined. The final harness waits for actual native sidebar/theme availability before interacting, activates native Search from the keyboard and verifies dialog input focus. Server-injected boot data alone is not readiness.
- Saved eight synthetic-user screenshots under `development/whatsapp_marketing/.local/test-results/browser/*/native-desk.png`; visually inspected dark desktop and 390px mobile images against the native ERPNext Desk. These qualify the harness shell, not the future marketing pages.
- Verified no Role rollback probe or synthetic users remained; temporary browser credentials were removed. Three standalone fixture create/delete cycles and three ordered integration-to-fixture cycles passed. A combined invocation had an intermittent fixture CLI failure; Bench's fallback exposed NameError and hid its original cause. The controller now reports the safe exception-class chain without captured credentials. No automatic retry masks fixture failures.
- `python3 development/whatsapp_marketing/runtime.py verify` passed before the concurrent runtime expansion: Frappe/ERPNext/TAG Marketing installed, DB/Redis, module/dependency checks, credential isolation, web/assets, realtime, two registered workers, actual marketing-queue and scheduler probes true. This is historical evidence for that baseline, not qualification of subsequent runtime changes.

### Runtime expansion follow-up

The environment blocker recorded above was resolved after the user requested HRMS, ZA Core and SA Payroll in the Desk. The three apps are now installed from pinned sources; runtime checks confirm their imports, dependency bounds, Desk tile/Dock records and assets. The earlier note is retained as history, not current runtime state.

Runtime expansion and additional-app business qualification are separate from the final WhatsApp harness gate recorded below. The later combined-gate evidence supersedes the earlier pending verification status.

### Payroll runtime installation evidence

- Installed the requested `tagprojectsza/hrms` `version-16` checkout at `5c72c067c0a3bcc969a49c708b7bec545a046fe9`, existing `frappe_za_core` at `a6128f1661c5ad9cda4eabff86168fe5bf9818b9`, and existing `frappe_za_payroll` at `dc958457b062a76a04014957dba3e4c1cc02fa19`. Pinned `reportlab==5.1.0` for payroll's PDF support.
- Extended Compose mounts, runtime lock, bootstrap and verifier. Framework/localisation source checkouts are mounted read-only and cloned at their pinned commits into Bench storage for dependency installation and asset builds; TAG Marketing remains soft-linked to its editable checkout.
- `python3 tag_marketing/development/whatsapp_marketing/runtime.py config`: passed. `python3 tag_marketing/development/whatsapp_marketing/runtime.py up`: exited 0 after dependency-ordered installs, two migrations, complete asset build and service restart. No site or database volume was reset.
- `docker exec tag-wa-dev-web-1 bench --site wa-marketing.localhost list-apps`: Frappe, ERPNext, TAG Marketing, HRMS, `za_local_core` and `za_local_payroll`.
- `python3 tag_marketing/development/whatsapp_marketing/runtime.py verify`: exited 0. Verified app compatibility, the ZA Localisation Apps-screen tile, the Payroll Dock, database/Redis, built assets, web/realtime, marketing queue, scheduler and credential isolation.
- Installation registers the apps and their default setup records; it does not configure a real company or approve statutory rate packs. Payroll remains unqualified for real pay processing until its setup and acceptance requirements are met.


### Review corrections and final combined gate

Verified on 27 October 2026; implementation commit `eb3d9df`. This follow-up closes WA-P0-004 only.

- Review found cleanup could run after unsuccessful fixture setup using shared account names, and the negative browser check could accept an unrelated failure containing a matching string. Replaced these with run-owned identities/recovery manifests and a structured three-probe report oracle; see the [owning lifecycle and commands](TESTING_AND_ACCEPTANCE.md#synthetic-users-data-and-cleanup).
- Added integration checks that cleanup preserves other runs/legacy accounts and validates all ownership markers before deleting any record. Added pure report checks rejecting missing/duplicate probes, unrelated/additional errors, retries, skips and expected-failure annotations. CLI fixture setup/cleanup now enforce the same local-infrastructure-only guard.
- The shared bootstrap completed and recreated its services; imports for configured apps were available. This removed the historical blocker. The WhatsApp app still requires only ERPNext; extra app functionality remains outside this qualification.
- `python3 development/whatsapp_marketing/quality.py all` exited **0**: structural documentation checks; Ruff lint/format; mypy across **25 sources**; **6 pure tests**; **7 Frappe integration tests** (plus rediscovery of the same six pure tests); strict TypeScript; **8 real Chromium cases**; and **3 deliberate HTTP/WebSocket/API probes** rejected only by their guard assertions. No retries masked failures.
- The first repository-wide lint attempts correctly failed on import ordering/formatting in concurrently edited bootstrap/verifier files. Applied only mechanical corrections there, preserving their runtime changes; reran the full gate successfully. Kept those mixed runtime files outside the harness commit.
- Browser cases passed for both synthetic users in desktop light/dark, tablet and mobile; eight fresh screenshots are under `development/whatsapp_marketing/.local/test-results/browser/*/native-desk.png`. Inspected dark desktop and mobile screenshots: native Desk shell remains intact. These images qualify the harness baseline only; marketing navigation and screens are later tasks.
- Successful cleanup removed both private recovery files. The final read-only database check found no harness users or rollback Role. Added an ignore entry for Bench's generated public node_modules symlink; no generated assets or credentials are versioned.
- `quality.py docs` and `git diff --check` are rerun after recording this evidence. Production remains unqualified and live sending disabled. Next dependency-ready task: **WA-P1-001**, the complete documented schema, role matrix, settings guards and idempotent constraints; its checkbox remains unchecked.


## WA-P1-001 — Owned schema, roles and settings guards

Status: **Verified** on 27 October 2026. Implementation commit: `e93e0a1`. Scope: WA-A01 schema/install/migration and the foundation company/role portions of WA-A03. Source selection, feature workflows and production qualification remain later tasks. No navigation task has begun.

- Added all 31 documented parent DocTypes and five child DocTypes as native metadata, thin lifecycle adapters, server-side settings policy, company/assignment read restrictions and idempotent setup. Feature writes remain closed; [foundation boundaries](DATA_MODEL.md#foundation-implementation-boundary) and [staged permissions](PERMISSIONS_AND_PRIVACY.md#foundation-access-and-staged-availability) own the current availability rules.
- Single-field unique indexes are native metadata; compound constraints/indexes have one owned manifest. Corrected reserved identifier quoting after the first migration failed on row_number. Main-site migration subsequently passed. A concurrent dashboard write in another installed app caused a separate migration deadlock; pausing and restoring only the owned workers/scheduler allowed it to complete without modifying sibling code.
- Reviewed the pinned unique-key helper and found its lookup is not database-scoped. Added the local SHOW INDEX adapter and verified a missing unique key with a reserved field on a connection-local temporary table. Fresh qualification now explicitly checks every declared compound index on its own database.
- Focused checks passed: eight offline pure tests, 25 real Frappe integration tests, and mypy across 110 sources. Integration checks include every documented parent field, every compound/scalar unique constraint, nullable provider IDs, a real two-connection race, company and team restrictions, generic/bulk/ignore_validate write denial, sharing denial, settings auditing/forgery and preservation of custom settings/roles/encryption identity.
- Real-browser qualification passed 16 cases (native settings access/hidden credential checks and ordinary-agent API denial alongside the Desk checks) plus all three network probes. A broad checkbox locator initially matched a native display control as well as the actual input; corrected its target. The final gate also captures the lower privacy section.
- Preliminary fresh ERPNext/TAG install and two migrations passed before tightening the local-index checks. Later fresh runs exposed an installation PermissionError and disposed only their own temporary sites. Inspection found Frappe post_install.init_singles saves before after_sync and requests ignore_validate. Seeding safe defaults/key during the owned settings DocType sync avoids that early save while preserving before_validate guards. The corrected fresh install and both migrations exited 0, verified only Frappe/ERPNext/TAG installed, all declared indexes present, customised setting/role preserved and the encrypted key unchanged. The qualification site was disposed successfully.

- The authorised System Manager save test additionally found that sparse Single defaults lacked the canonical name. Seeding that identity fixed ordinary saves after field-level filtering without granting creation rights or exposing the secret. Missing existing encryption material stops migration for recovery; it is never silently replaced.
- Final `python3 development/whatsapp_marketing/quality.py all` exited **0**: documentation structure, Ruff lint/format, mypy over **110 sources**, **8 offline tests**, **27 real integration tests**, strict TypeScript, **16 Chromium cases** and **3 intended network-guard failures**. No retries were used. Frappe emits a native v17 deprecation notice for its limit_page_length adapter; it does not fail the pinned v16 suite.
- Ran `bench --site wa-marketing.localhost migrate` twice more, both exit 0, with the owned scheduler/workers restored in finally. This verifies the main installed environment as well as the isolated fresh-install path. The additional apps remain outside marketing business qualification.
- Screenshots are under `development/whatsapp_marketing/.local/test-results/browser/foundation-*/native-settings*.png` alongside Desk references. Visually inspected the dark desktop/privacy section and 390px mobile form: native controls, spacing, theme and responsive layout are intact. No custom UI framework or global CSS was added. The default generated module sidebar is not the final P1-002 navigation.
- Final cleanup checks found zero harness/foundation users, synthetic companies or race rows, no qualification site and no private browser manifest/credential file. Sending remains **0** and all eight owned runtime services are running. Documentation validation and whitespace checks are repeated after this evidence update.
- Only WA-P1-001 is completed. Next: **WA-P1-002** owned Dock/Sidebar/Workspace and safe destinations. Features remain gated according to their own tasks; this schema task does not qualify live messaging or production release.


## WA-P1-002 — Native grouped navigation and Desk icon

Status: **Verified** on 27 October 2026 after the qualification follow-up below. App commit: **working tree, not committed**. Scope: WA-A02 owned navigation/widget foundation and WA-A03 role/company boundaries. Production and feature queries remain unqualified; this entry does not close later report/inbox tasks.

### Initial implementation and earlier qualification attempts

- Added the TAG Marketing Apps-screen logo, owned Dock, native Sidebar and Workspace. The [navigation index](pages/README.md#native-sidebar-hierarchy) owns the HRMS/ERPNext-style dropdown layout. No framework, HRMS, ERPNext or localisation metadata was edited. Shared-navigation mounting is unnecessary for this independent app tile.
- Added all sidebar targets: native lists/forms, the authorised Inbox availability Page, seven Script Report availability boundaries, five native Number Cards and two Dashboard Charts. No campaign totals, message records, reply controls or provider activity are fabricated. The [foundation interface contract](API_CONTRACTS.md#foundation-navigation-interfaces) owns the current responses.
- Native Apps permission and resolved landing checks cover Marketing User, Marketing Manager, Marketing Analyst, WhatsApp Agent and System Manager. Agent-only users land in Inbox; Analyst sees Overview/reports without raw contact access. Unrelated/Guest users cannot access the app or its availability queries. Every destination resolves, icons exist in the shipped sprite and no destination is duplicated.
- Navigation tests verify company restrictions on every metric entry point, filter/chart rejection, collision refusal without overwrite, and preservation of site Sidebar/Dock/Workspace layers through two forced native base imports. Optional legacy Desktop Icons seeding is owned, idempotent and has an actual shell route; the normal Apps screen uses its supported hook.
- The initial browser inspection exposed mismatched native Workspace block/child labels. Corrected the references and now assert all five N/A cards and both unavailable chart messages render. The Agent test also accounts for the native active-route group opening automatically. A customization test initially compared in-memory timestamp strings with database datetimes; it now compares persisted records before and after import.
- Ordinary migration initially retained the previous JSON revision. Inspected the native importer's timestamp rule, advanced the changed Sidebar/Workspace revisions and documented [revision handling](FRAMEWORK_AND_SETUP.md#native-navigation-metadata-revisions). A direct read-only inspection now confirms both persisted records match the shipped content after an ordinary migration.
- `python3 development/whatsapp_marketing/qualify_foundation.py` exited **0**: fresh Frappe/ERPNext/TAG-only install, all owned navigation identities present, two migrations, encrypted key/settings/role preservation and successful disposal of the owned temporary site. Extra installed apps on the main site are outside business qualification.
- `python3 development/whatsapp_marketing/quality.py all` passed documentation structure, Ruff/format, mypy over **131 sources**, **8 offline tests** and **35 real integration tests**, including all eight navigation tests. Its browser stage exposed the mobile test's use of a rail-only open operation. The corrected test waits for widget readiness and uses the native mobile menu button, which also sets drawer height. Native N/A/chart requests have a bounded 30-second readiness wait; navigation cases have a 120-second total bound, without retries.
- `python3 development/whatsapp_marketing/quality.py browser --browser-project mobile` exited **0**: **5 positive phone cases passed**, three role/theme combinations intentionally excluded, strict TypeScript and all **3 deliberate HTTP/WebSocket/API egress probes** passed their rejection oracle. The focused option retains the normal fixture/cleanup lifecycle; it is not a substitute for the complete matrix.
- A subsequent full `quality.py browser` run passed **all four marketing-role navigation cases**, then failed the existing System Manager harness login's 30-second URL bound while native Desk navigation was still loading. Earlier runs exercised dark/tablet navigation and the corrected focused phone run passed. At that point, there was **no complete green browser matrix**; the follow-up below supersedes this qualification state. Host `uptime` reported load averages **146.30 / 163.09 / 124.63**, consistent with the observed native-login and host-command delays; no unrelated processes or services were stopped to address this.
- Visually inspected expanded navigation and widgets in light/dark desktop and the 390px native phone drawer. Latest retained screenshots are `development/whatsapp_marketing/.local/test-results/browser/navigation-*/marketing-desk-icon.png`, `marketing-sidebar.png` and `marketing-sidebar-expanded.png` for the desktop roles. Playwright replaces its output directory on a later run; the earlier dark/phone images were inspected but need recapture with the successful complete matrix. Do not cite replaced artifacts as retained evidence.
- After the focused-runner change, `quality.py lint` exited **0** (Ruff, format and mypy over 131 sources). Read-only cleanup inspection found **zero** harness/foundation users, synthetic navigation companies or synthetic Sidebar overrides; both private browser manifest/credential files are absent. Sending is **0**. The fresh qualification site was disposed. Documentation structure and whitespace checks are repeated after this entry.
- The next action at that point was complete browser qualification before closing the task. The follow-up below resolves that gate. Initial Docker access was blocked by an automatic approval-review usage limit; later approved execution succeeded, so no approval blocker remains.


### Qualification follow-up — verified

- Rechecked the pinned host source revisions: Frappe `e8d41dd006`, ERPNext `ade850bbd6`. Preserved the unrelated bootstrap, Compose and license edits. No sibling app or framework source was changed.
- Fixed the harness login boundary: wait for navigation **commit**, then actual native Sidebar/theme initialization, each bounded at 60 seconds. Cases have a finite 120-second total budget; there are no retries or mocked responses. This addresses cold Desk loading without treating a partially loaded URL as readiness. Screenshots now use a separate run directory, preserving evidence across later diagnostics.
- `python3 development/whatsapp_marketing/quality.py browser` exited **0**: strict TypeScript, **23 positive real Chromium cases passed**, **9 explicitly excluded duplicate role/visual combinations**, and **all 3 intentional HTTP/WebSocket/API guard failures** accepted by the strict report oracle. Every marketing role ran at desktop light; Manager also ran at desktop dark, 1024px tablet and 390px phone. Existing native settings/session permission checks passed in every project. This is the complete browser gate that was previously pending.
- Retained evidence root: `development/whatsapp_marketing/.local/test-results/browser/62fe185273cb4f3894f85a5dafe4063c/`. Each `navigation-*` case contains `marketing-desk-icon.png` and `marketing-sidebar.png`; Manager and Analyst report expansion cases also contain `marketing-sidebar-expanded.png`. Visually reviewed the dark desktop workspace, native Apps tile and expanded phone drawer. Native controls, heading icons, indented links, theme and responsive layout remain intact.
- Extended the navigation integration checks to preserve **both site and personal** Sidebar/Dock layers plus the site Workspace delta through two forced native base imports; the personal Sidebar label still takes precedence. Also verified that an Agent outside the configured company cannot query Inbox readiness. `docker exec tag-wa-dev-web-1 bench --site wa-marketing.localhost run-tests --app tag_marketing --module tag_marketing.tests.test_navigation` exited **0**, **8 tests passed**. The earlier full **35-test integration** and **8-test offline** results remain applicable; only these coverage assertions and the browser harness changed afterward.
- `python3 development/whatsapp_marketing/quality.py lint` exited **0**: Ruff lint/format and mypy across **131 sources**. Final documentation structure and `git diff --check` run after recording this evidence.
- Read-only cleanup found **0** harness users, foundation users, synthetic navigation companies, synthetic Sidebar layers and synthetic Dock layers. Browser manifest/credentials are absent; sending remains **0**. The earlier fresh Frappe/ERPNext/TAG-only install and two migrations remain passed, and that temporary site was disposed.
- Only WA-P1-002 closes here. Next dependency-ready task: **WA-P1-003**. Full ERPNext visual comparison is WA-P1-004; actual messaging, Inbox, reporting and operation services retain their own gates. Production is **not qualified** and live sending is **not enabled**.
