# Progress and evidence

Last baseline review: 27 October 2026. Implementation: **WA-P0-001 through WA-P0-003 verified; application scaffold installed**. Production readiness: **Not qualified**. Live sending: **Not enabled by this work**.

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

- Next: WA-P0-004 configures the test harness and deterministic adapters before feature implementation.
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
