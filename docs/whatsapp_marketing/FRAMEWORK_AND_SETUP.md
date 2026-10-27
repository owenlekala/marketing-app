# Framework and development setup

Owner: WA-R01, WA-R02, WA-R15. Execution: [P0 tasks](tasks/P0-ENVIRONMENT-AND-BOOTSTRAP.md). Baseline references: [source register](REFERENCES.md).

## Inspected facts and unverified state

Frappe is 16.53.0 at `e8d41dd006`; ERPNext is 16.52.1 at `ade850bbd6`. Frappe requires Python `>=3.14,<3.15`; Node is `>=24`. ERPNext requires Frappe `>=16.50.0,<17.0.0`. Use Python 3.14 and Node 24 for the initial development image and record exact patch versions/digests in bootstrap evidence.

The source folders are separate repositories, with inspected fork origins recorded in [references](REFERENCES.md#local-baseline). WA-P0-001 found a source-only workspace. WA-P0-002 subsequently established and verified the disposable Bench/site in an owned Docker volume; the workspace root itself is not a Bench. Current runtime evidence is recorded in [WA-P0-002](PROGRESS.md#wa-p0-002--disposable-development-runtime). WA-P0-003 adds the separate application scaffold; its UI and provider callbacks remain later tasks.

## Framework mental model

- **Bench** owns the Python environment, application checkouts, site directories, asset build and process configuration. Run `bench` commands from its root.
- **Site** owns a database, site configuration and files. Use explicit `--site` selectors; a site is an isolation boundary.
- **App** is an installed Python package and repository. A **module** groups owned DocTypes and Desk content inside that app.
- **DocType** metadata defines fields, permissions and document behaviour. A Python **controller** validates lifecycle operations; form scripts provide client interactions.
- **Hooks** contribute event handlers, assets, install/migrate steps and scheduler jobs without core edits.
- **Migrations** synchronise metadata and execute patches. They must be repeatable and preserve customer customisations.
- **Assets** are built by Frappe's bundler and served from `/assets`; do not reference arbitrary development source paths in deployed pages.
- **Redis/RQ queues** transport background execution; **scheduler** discovers due work. Durable business work remains in the database.
- **Realtime** distributes updates through permission-checked document/user subscriptions. Inspect this checkout's realtime process before configuring it; do not assume an older Node-only service layout.
- **Private files** require authorised retrieval and `File` ownership checks; a private URL alone is not an access design.

See official [Apps](https://docs.frappe.io/framework/user/en/basics/apps), [Bench](https://docs.frappe.io/framework/user/en/bench) and [installation](https://docs.frappe.io/framework/user/en/installation).

## Docker development procedure

### Workspace runtime controller

WA-P0-002 implements the isolated development project in [development/whatsapp_marketing](../../development/whatsapp_marketing/compose.yaml). Use [runtime.py](../../development/whatsapp_marketing/runtime.py) from the `tag_marketing` repository root; [runtime.lock.json](../../development/whatsapp_marketing/runtime.lock.json) owns image digests, source revisions, site identity and ports. The following commands use that lock rather than maintaining another environment file:

```sh
python3 development/whatsapp_marketing/runtime.py config
python3 development/whatsapp_marketing/runtime.py up
python3 development/whatsapp_marketing/runtime.py status
python3 development/whatsapp_marketing/runtime.py verify
python3 development/whatsapp_marketing/runtime.py stop
```

The workspace root also needs sibling source checkouts for HRMS (`hrms/`, `version-16`), ZA Localisation Core (`frappe_za_core/`) and South African Payroll (`frappe_za_payroll/`). `runtime.lock.json` is authoritative for their exact commits; the bootstrap refuses a different revision or a dirty source checkout. Payroll requires ERPNext, HRMS and `za_local_core`, so the runtime installs those in order. These remain development-runtime apps; TAG Marketing itself still declares only ERPNext as a required app.

The host controller supports Python 3.9 because application execution occurs inside the checked Python 3.14 container. Docker access is required for lifecycle commands. `up` starts only the owned Compose project, prepares its volume, bootstraps the pinned Frappe/ERPNext/HRMS and South African localisation sources, and starts the native web/realtime/scheduler and dedicated workers. Bench clones the locked HRMS/localisation sources into its writable volume for dependency installation and asset builds; TAG Marketing stays soft-linked to its editable host checkout. The bootstrap installs HRMS, `za_local_core`, `za_local_payroll` and TAG Marketing on the disposable site in dependency order. The runtime lock pins each source commit and the payroll PDF dependency. `stop` retains data volumes; no command silently resets a failed Bench/site.

After successful bootstrap, the local site is reachable at `http://wa-marketing.localhost:18080` (also verified through `http://localhost:18080`). Administrator login uses the generated local `site_admin` secret. The Bench root inside its containers is `/home/frappe/dev/frappe-bench`; the site identifier and exposed ports are owned by the lock file.

Generated database/admin credentials stay under the ignored `.local/secrets` directory (host directories mode 0700), never in the image lock or documentation. Secret files are read-only and container-readable for Compose file-secret mounts. Only bootstrap/database services receive them. The remaining services receive no root/admin secret mounts. Credentials are neither logged nor included in browser/probe responses.

Frappe, ERPNext, HRMS, `za_local_core` and `za_local_payroll` source repositories are mounted read-only and cloned at their locked commits into writable Bench storage so Bench can install JavaScript dependencies and build assets. TAG Marketing is mounted writable at `/source/tag_marketing`, with `apps/tag_marketing` soft-linked to its canonical host checkout. A read-only, mode-000 tmpfs masks the TAG Marketing `.local` subtree in every Bench service so its live source mount cannot expose host credentials. The bootstrap service receives its explicit `/run/secrets` mounts separately. Published ports bind only to host loopback. Database/Redis have no host-published ports. The bootstrap checks every pinned source commit before installation, refuses incomplete Bench resets, uses the fork's Python realtime entrypoint and migrates the disposable site twice. The verifier checks installed app dependencies, database/Redis, built assets, web/realtime, actual marketing-queue consumption and a synthetic scheduled execution. Consult current task evidence before claiming any of these runtime checks passed.

### Bootstrap ownership

The executable [bootstrap](../../development/whatsapp_marketing/bootstrap.py) owns runtime checks, local-source installation, site creation, development settings, repeated migration and asset builds. Update that implementation and its evidence together rather than copying a second manual bootstrap recipe into this guide. The [official references](REFERENCES.md) explain Bench semantics; this workspace's fork manifests and lock determine the actual environment.

## Application verification after app bootstrap

The runtime controller verification above belongs to WA-P0-002. The commands below additionally require the scaffold from WA-P0-003 and, for feature checks, later services; they are not prerequisites for claiming that the framework-only runtime is established. Run inside the Bench container from `<bench-root>` with the confirmed `<dev-site>`:

```sh
bench version
bench --site <dev-site> list-apps
bench --site <dev-site> doctor
bench --site <dev-site> run-tests --app tag_marketing
```

From the same Bench root, open `bench --site <dev-site> console` and run the read-only Python expressions below, then exit. `frappe.db` is a database object, so do not treat its methods as importable dotted CLI execute functions.

```python
frappe.db.sql("select 1")
frappe.db.get_database_size()
frappe.cache.ping()
```

Verify a scheduled/queued synthetic diagnostic operation from the application; do not print site configuration or secrets. Record the exact supported Bench/CLI diagnostics if this installation differs.

- Confirm installed revisions match the baseline and the marketing queue consumes a synthetic job.
- Run migrate twice; confirm unique records and retained customisations.
- Open Desk; confirm assets return successfully and capture ERPNext reference screenshots in both themes.
- Confirm realtime authentication and assignment changes using two users with different permissions.
- Publish only the webhook callback over approved public HTTPS; verify GET challenge and signed POST receipt. A successful HTTP handshake alone is not readiness.
- Record worker/scheduler heartbeat, database, asset, webhook and UI results in [progress](PROGRESS.md).

## Production boundary

Use a custom immutable image containing compatible apps and built assets, dedicated workers, correct realtime entrypoints, private storage, TLS and external secret management. Never use `bench start`, developer mode or a test site as production deployment. Follow [operations/release](OPERATIONS_AND_RELEASE.md).
