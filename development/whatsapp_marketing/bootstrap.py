"""Bootstrap only a disposable ERPNext site, preserving pinned source checkouts."""

import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path("/runtime")
LOCK = json.loads((ROOT / "runtime.lock.json").read_text())
BENCH = Path("/home/frappe/dev/frappe-bench")
SITE = LOCK["site"]
ENV = dict(os.environ)
ENV.update({
    "GIT_CONFIG_COUNT": "3",
    "GIT_CONFIG_KEY_0": "safe.directory",
    "GIT_CONFIG_VALUE_0": "/source/frappe",
    "GIT_CONFIG_KEY_1": "safe.directory",
    "GIT_CONFIG_VALUE_1": "/source/erpnext",
    "GIT_CONFIG_KEY_2": "safe.directory",
    "GIT_CONFIG_VALUE_2": "/source/tag_marketing",
})
SENSITIVE = []


def run(label, args, cwd=BENCH):
    print(label, flush=True)
    process = subprocess.Popen(args, cwd=cwd, env=ENV, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = ""
    for line in process.stdout:
        for secret in SENSITIVE:
            line = line.replace(secret, "[REDACTED]")
        print(line, end="", flush=True)
        # Command queries are tiny; cap retained install logs while streaming them.
        output = (output + line)[-1_000_000:]
    if process.wait():
        raise RuntimeError("%s failed (exit %s)" % (label, process.returncode))
    return output.strip()


def check_revision(path, expected):
    actual = run("Verify %s source revision" % path.name, ["git", "-C", str(path), "rev-parse", "HEAD"], cwd=path)
    if actual != expected:
        raise RuntimeError("Source revision mismatch for %s; no implicit update permitted" % path.name)
    if run("Check %s source changes" % path.name, ["git", "-C", str(path), "status", "--porcelain"], cwd=path):
        raise RuntimeError("Source checkout has changes: %s" % path.name)


def main():
    if os.getuid() == 0:
        raise RuntimeError("Run bootstrap as the image's unprivileged frappe user")
    if sys.version_info[:2] != (3, 14):
        raise RuntimeError("The locked framework requires Python 3.14")
    if not os.access(BENCH.parent, os.W_OK):
        raise RuntimeError("Bench parent is not writable; run the volume-init service and check nocopy mounts")
    node = run("Verify Node runtime", ["node", "--version"], cwd=ROOT)
    if int(node.lstrip("v").split(".")[0]) != LOCK["runtime"]["node_major"]:
        raise RuntimeError("Node runtime does not match lock")
    run("Verify Yarn", ["yarn", "--version"], cwd=ROOT)
    run("Verify Bench", ["bench", "--version"], cwd=ROOT)
    for name, revision in LOCK["sources"].items():
        check_revision(Path("/source") / name, revision)
    if not BENCH.exists():
        run("Initialise pinned Frappe Bench", [
            "bench", "init", "--python", sys.executable,
            "--frappe-path", "/source/frappe", "--frappe-branch", "version-16",
            "--skip-redis-config-generation", "--skip-assets", str(BENCH),
        ], cwd=BENCH.parent)
    if not (BENCH / "env/bin/python").exists():
        raise RuntimeError("Incomplete Bench exists; inspect it before retrying, do not reset volumes")
    check_revision(BENCH / "apps/frappe", LOCK["sources"]["frappe"])
    if not (BENCH / "apps/erpnext").exists():
        run("Install pinned ERPNext source", ["bench", "get-app", "--skip-assets", "erpnext", "/source/erpnext"])
    check_revision(BENCH / "apps/erpnext", LOCK["sources"]["erpnext"])
    app = BENCH / "apps/tag_marketing"
    source = Path("/source/tag_marketing")
    if not (source / "tag_marketing/hooks.py").is_file():
        raise RuntimeError("Marketing source mount is missing; check the application checkout")
    if not app.exists():
        run("Register the single marketing source checkout", [
            "bench", "get-app", "--soft-link", "--skip-assets", "tag_marketing", str(source),
        ])
    if not app.is_symlink() or app.resolve() != source:
        raise RuntimeError("Marketing app must link to the canonical host source, not a duplicate checkout")
    run("Refresh editable marketing package", [
        "uv", "pip", "install", "--quiet", "--no-deps", "-e", str(app),
        "--python", str(BENCH / "env/bin/python"),
    ])
    common = BENCH / "sites/common_site_config.json"
    config = json.loads(common.read_text()) if common.exists() else {}
    config.update({
        "db_host": "mariadb", "db_port": 3306,
        "redis_cache": "redis://redis-cache:6379", "redis_queue": "redis://redis-queue:6379",
        "redis_socketio": "redis://redis-queue:6379", "webserver_host": "web",
        "webserver_port": 8000, "socketio_port": LOCK["ports"]["realtime"],
        "default_site": SITE, "serve_default_site": True,
        "scheduler_tick_interval": 5,
        "workers": {"marketing": {"timeout": 300, "background_workers": 1}},
    })
    temporary = common.with_suffix(".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n")
    temporary.chmod(0o600)
    temporary.replace(common)
    if not (BENCH / "sites" / SITE / "site_config.json").exists():
        db_password = Path("/run/secrets/db_root").read_text().strip()
        admin_password = Path("/run/secrets/site_admin").read_text().strip()
        SENSITIVE.extend([db_password, admin_password])
        run("Create disposable development site", [
            "bench", "new-site", SITE, "--db-root-username", "root",
            "--db-root-password", db_password, "--admin-password", admin_password,
            "--mariadb-user-host-login-scope", "%",
        ])
    installed = run("Check installed site apps", ["bench", "--site", SITE, "list-apps", "--format", "json"])
    if "erpnext" not in installed:
        run("Install ERPNext on disposable site", ["bench", "--site", SITE, "install-app", "erpnext"])
    if "tag_marketing" not in installed:
        run("Install marketing scaffold on disposable site", ["bench", "--site", SITE, "install-app", "tag_marketing"])
    for key, value in [("developer_mode", "1"), ("allow_tests", "true")]:
        run("Configure development %s" % key, ["bench", "--site", SITE, "set-config", key, value])
    for iteration in range(2):
        run("Migrate disposable site (%s/2)" % (iteration + 1), ["bench", "--site", SITE, "migrate"])
    run("Build installed application assets", ["bench", "build"])
    run("Enable disposable-site scheduler", ["bench", "--site", SITE, "enable-scheduler"])
    print("Bootstrap complete. Marketing scaffold installed; no outbound integration configured.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Never include a subprocess argument list containing credentials.
        text = str(exc)
        for secret in SENSITIVE:
            text = text.replace(secret, "[REDACTED]")
        print(text, file=sys.stderr)
        sys.exit(1)
