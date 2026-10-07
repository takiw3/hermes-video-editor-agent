#!/usr/bin/env python3
"""Pinned HyperFrames launcher for the Hermes video-editor profile.

Every HyperFrames call the agent makes goes through this file:

    python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" <command>

What it enforces, in code:

  * One CLI version. The CLI runs from a lockfile install (npm ci) made by the
    owner-run setup step. A missing or mismatched install is an error. There
    is no fallback to npx, to a global binary, or to "latest".
  * No self-update. HYPERFRAMES_SKIP_SKILLS, HYPERFRAMES_NO_UPDATE_CHECK,
    HYPERFRAMES_NO_AUTO_INSTALL, HYPERFRAMES_NO_TELEMETRY and DO_NOT_TRACK are
    set on every child process. Each switch was verified against the tagged
    CLI source.
  * A subcommand allowlist. Cloud render, Lambda, Cloud Run, publish, sign-in,
    feedback, upgrade, skills, website capture and provider commands are
    refused.
  * A workspace boundary. The working directory and every path argument must
    resolve inside the owner-approved workspace.
  * No provider credentials. Secret-looking environment variables are removed
    from the child environment, and HOME points at a profile-local folder so
    no existing sign-in is visible to the CLI.
  * PATH shims. A child process that shells out to npx, npm, pip and similar
    gets the pinned CLI or a refusal, never an unpinned download.
  * Draft before final, asset rights, external hosts, and source-footage
    checksums are checked before a final render.
  * A style decision. A final render is refused while the project has no
    style-decision.yaml recording a chosen option or a one-edit waiver. A
    draft with no decision must be tagged as a comparison option.
  * The reference-folder exclusion. Nothing under the workspace's references/
    folder, and no byte-identical copy of a file in it, may sit in a project
    or on a command line. Reference videos are for study, not for renders.
  * Timed media needs an id. An <audio> or <video> element with no id is
    refused before render, because the mixer skips it and the render is silent.
  * Workers come from measured memory, and every render records its peak
    process-tree memory.

These gates hold for every call made through this launcher. They are not an
operating-system sandbox: see docs/permissions-and-security.md for what a raw
command can and cannot get around.

Setup (`hf.py setup ...`) downloads software and is for the owner to run in
their own terminal. The profile's config.yaml denies it to the agent.

Standard library only. Exit codes: 0 ok, 2 usage, 3 needs_setup, 4 refused,
5 check failed, otherwise the child's exit code.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve()
SKILL_DIR = SCRIPT.parent.parent
PROFILE_HOME = SCRIPT.parents[4]
TOOLCHAIN_SRC = SKILL_DIR / "toolchain"
PIN_FILE = TOOLCHAIN_SRC / "pin.json"
BUNDLE_DIR = PROFILE_HOME / "skills" / "hyperframes-video"
ENGINE_DIR = PROFILE_HOME / "local" / "video-editor" / "video-engine"
ENGINE_FILE = ENGINE_DIR / "engine.json"
ENGINE_HOME = ENGINE_DIR / "home"
SHIM_DIR = ENGINE_DIR / "shims"

EXIT_USAGE, EXIT_SETUP, EXIT_REFUSED, EXIT_CHECK = 2, 3, 4, 5

# Subcommands of the pinned CLI the agent may run. Everything else is refused.
ALLOWED = {
    "init", "lint", "check", "validate", "inspect", "layout", "snapshot",
    "render", "info", "compositions", "timeline", "keyframes", "beats",
    "catalog", "compare", "grade-compare", "normalize-audio", "history",
    "clean", "docs", "usage", "doctor", "transcribe", "media-treatment",
}
# Refused always, with the reason shown to the agent.
PROHIBITED = {
    "skills": "skills are bundled and release-managed; nothing is updated at run time",
    "upgrade": "the CLI version is pinned by the profile lock file",
    "publish": "uploading a project is an external write",
    "cloud": "cloud rendering is not available in this release",
    "lambda": "AWS Lambda rendering is not available in this release",
    "cloudrun": "Google Cloud Run rendering is not available in this release",
    "auth": "the agent never signs in to a provider",
    "feedback": "feedback is submitted to a public channel, which is an external write",
    "events": "telemetry is disabled in this profile",
    "telemetry": "telemetry is disabled in this profile",
    "open": "the desktop-app hand-off is not available in this profile",
    "catch-up": "the desktop-app hand-off is not available in this profile",
    "figma": "the Figma workflow is not bundled",
    "capture": "website capture is a network read the default mode does not perform",
    "media-use": "provider-backed media sourcing is off by default",
    "tts": "voice generation is off by default",
    "remove-background": "background removal is unavailable: its runtime package and model are not installed, and this release does not install them",
    "add": "a registry item is fetched from the upstream main branch, not from the pinned release; it is an owner-run setup step",
    "models": "model downloads are an owner-run setup step",
    "browser": "browser downloads are an owner-run setup step",
    "play": "use preview-start and preview-stop",
    "present": "the presentation server is not part of the editing workflows",
    "preview": "use preview-start, preview-status and preview-stop",
    "benchmark": "not part of the editing workflows",
}

OUTPUT_FLAGS = {"-o", "--output", "--out", "--dir", "--output-dir", "--project"}
SECRET_NAME = re.compile(
    r"(_API_KEY|_APIKEY|_TOKEN|_SECRET|_PASSWORD|_CREDENTIALS)$|^(AWS_|HEYGEN_|GEMINI_|ELEVENLABS_|OPENAI_|ANTHROPIC_|OPENROUTER_|GROQ_|FIGMA_|GOOGLE_API|GOOGLE_APPLICATION|GH_|GITHUB_)",
)
ASSET_EXT = {
    ".woff2", ".woff", ".ttf", ".otf", ".mp3", ".wav", ".ogg", ".m4a", ".aac",
    ".flac", ".mp4", ".mov", ".webm", ".mkv", ".png", ".jpg", ".jpeg", ".webp",
    ".gif", ".svg", ".cube", ".lut",
}
URL_RE = re.compile(r"""https?://([A-Za-z0-9.-]+)(?::\d+)?[^\s"'<>)]*""")
SKIP_DIRS = {"node_modules", ".git", "renders", "receipts", "snapshots", ".hyperframes", ".cache", "tmp"}
WS_META = ".video-editor"
WS_DIRS = ("footage", "working-copies", "references", "projects", WS_META)
STYLE_OPTIONS = {"house_style", "outlier_matched", "hybrid"}
STYLE_FILE = "style-decision.yaml"
RESEARCH_DEFAULT = "owner-supplied only"
# Planning figure used until this machine has a measured render on record.
# Upstream states each render worker starts a Chrome process of roughly 256 MB
# (packages/cli/src/commands/render.ts, tag v0.8.138); the plan doubles it.
WORKER_MB_ASSUMED = 512


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def out(msg: str = "") -> None:
    print(msg, flush=True)


def fail(code: int, status: str, msg: str, **extra) -> "NoReturn":  # type: ignore[name-defined]
    payload = {"status": status, "message": msg, **extra}
    print(json.dumps(payload, indent=2), file=sys.stderr, flush=True)
    sys.exit(code)


def load_pin() -> dict:
    try:
        return json.loads(PIN_FILE.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - broken install
        fail(EXIT_SETUP, "needs_setup", f"pin file unreadable: {exc}")


def load_engine() -> dict:
    if ENGINE_FILE.is_file():
        try:
            return json.loads(ENGINE_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(EXIT_CHECK, "blocked", f"engine.json is unreadable: {exc}")
    return {}


def save_engine(engine: dict) -> None:
    ENGINE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = ENGINE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(engine, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, ENGINE_FILE)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def toolchain_dir(pin: dict) -> Path:
    return ENGINE_DIR / f"toolchain-{pin['npm_version']}"


def cli_entry(pin: dict) -> Path:
    return toolchain_dir(pin) / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def which(name: str, path: str | None = None) -> str | None:
    return shutil.which(name, path=path if path is not None else clean_path())


def clean_path() -> str:
    """PATH without our own shim dir, so tool discovery never finds a shim."""
    shim = str(SHIM_DIR)
    return os.pathsep.join(p for p in os.environ.get("PATH", "").split(os.pathsep) if p and p != shim)


def node_version(node: str) -> tuple[int, str] | None:
    try:
        raw = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=15).stdout.strip()
        m = re.match(r"v?(\d+)\.", raw)
        return (int(m.group(1)), raw) if m else None
    except Exception:
        return None


# --------------------------------------------------------------------------
# doctor
# --------------------------------------------------------------------------

def collect_checks(pin: dict, engine: dict) -> list[dict]:
    checks: list[dict] = []

    def add(name, ok, detail, fix=None, required=True):
        checks.append({"name": name, "ok": bool(ok), "required": required, "detail": detail,
                       **({"fix": fix} if fix and not ok else {})})

    node = which("node")
    ver = node_version(node) if node else None
    need = int(pin["node_minimum_major"])
    if not node:
        add("node", False, "Node.js not found on PATH",
            f"Install Node.js {need} or newer yourself. This profile never installs it.")
    elif not ver:
        add("node", False, f"could not read the version of {node}", f"Install Node.js {need} or newer.")
    elif ver[0] < need:
        add("node", False, f"{ver[1]} found, {need} or newer required",
            f"Upgrade Node.js to {need} or newer yourself. Nothing was changed.")
    else:
        add("node", True, f"{ver[1]} at {node}")

    for tool in ("ffmpeg", "ffprobe"):
        found = which(tool)
        add(tool, found, found or f"{tool} not found on PATH",
            "Install FFmpeg yourself (it provides ffmpeg and ffprobe). This profile never installs it.")

    tc = toolchain_dir(pin)
    pkg = tc / "node_modules" / "hyperframes" / "package.json"
    lock = tc / "package-lock.json"
    if not pkg.is_file():
        add("cli", False, f"pinned CLI {pin['npm_package']}@{pin['npm_version']} is not installed",
            "Owner runs: hf.py setup --install-cli")
    else:
        installed = json.loads(pkg.read_text(encoding="utf-8")).get("version")
        lock_ok = lock.is_file() and sha256_file(lock) == pin["package_lock_sha256"]
        if installed != pin["npm_version"]:
            add("cli", False, f"installed CLI is {installed}, pin is {pin['npm_version']}",
                "Owner runs: hf.py setup --install-cli")
        elif not lock_ok:
            add("cli", False, "installed lockfile does not match the shipped lockfile",
                "Owner runs: hf.py setup --install-cli")
        else:
            add("cli", True, f"{pin['npm_package']}@{installed} from lockfile at {tc}")

    browser = engine.get("browser_path")
    if not browser:
        add("browser", False, "no headless browser recorded",
            "Owner runs: hf.py setup --download-browser, or --use-browser <path>")
    elif not (Path(browser).is_file() and os.access(browser, os.X_OK)):
        add("browser", False, f"recorded browser is missing or not executable: {browser}",
            "Owner runs: hf.py setup --download-browser, or --use-browser <path>")
    else:
        add("browser", True, browser)

    ws = engine.get("workspace")
    if not ws:
        add("workspace", False, "no video workspace approved",
            "Owner runs: hf.py setup --workspace <folder>")
    elif not Path(ws).is_dir():
        add("workspace", False, f"approved workspace does not exist: {ws}",
            "Owner runs: hf.py setup --workspace <folder>")
    else:
        add("workspace", True, ws)

    model = engine.get("transcription_model")
    add("transcription", bool(model),
        f"model approved and installed: {model}" if model else
        "no speech model installed; transcription is unavailable, owner-provided captions still work",
        "Optional. Owner runs: hf.py setup --install-model parakeet", required=False)
    handoff = engine.get("handoff")
    add("handoff", True,
        f"approved handoff folder: {handoff}" if handoff else
        "no handoff folder approved; deliveries stay in the workspace and are reported by path and SHA-256",
        required=False)
    hosts = engine.get("external_hosts") or []
    add("external_hosts", True,
        ("approved render-time hosts: " + ", ".join(hosts)) if hosts else
        "no render-time host approved; compositions that load GSAP or fonts from a CDN will be refused",
        required=False)
    return checks


def engine_status(checks: list[dict]) -> str:
    return "toolchain verified" if all(c["ok"] for c in checks if c["required"]) else "not configured"


def cmd_doctor(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    as_json = "--json" in argv
    deep = "--deep" in argv
    checks = collect_checks(pin, engine)
    status = engine_status(checks)
    missing = [c["name"] for c in checks if c["required"] and not c["ok"]]
    report = {
        "video_engine": status,
        "result_status": "ok" if status == "toolchain verified" else "needs_setup",
        "missing": missing,
        "pinned": {k: pin[k] for k in ("npm_package", "npm_version", "upstream_tag", "upstream_commit")},
        "mode": "edit_and_render" if status == "toolchain verified" else "offline",
        "research": engine.get("research") or RESEARCH_DEFAULT,
        "profile_home": str(PROFILE_HOME),
        "checks": checks,
    }
    if deep and status == "toolchain verified":
        proc = run_cli(pin, engine, ["doctor", "--json"], capture=True, cwd=engine["workspace"])
        try:
            upstream = json.loads(proc.stdout[proc.stdout.index("{"):])
            report["upstream_doctor"] = {
                "ok": upstream.get("ok"),
                "failed": [c["name"] for c in upstream.get("checks", []) if not c.get("ok")],
                "version": (upstream.get("_meta") or {}).get("version"),
            }
            if (upstream.get("_meta") or {}).get("version") != pin["npm_version"]:
                report["video_engine"] = "not configured"
                report["result_status"] = "blocked"
                report["missing"].append("cli version mismatch at run time")
        except Exception:
            report["upstream_doctor"] = {"ok": None, "error": "could not parse the pinned CLI's doctor output"}
    if as_json:
        out(json.dumps(report, indent=2))
    else:
        out(f"video engine: {report['video_engine']}")
        out(f"research:     {report['research']}")
        out(f"pinned CLI:   {pin['npm_package']}@{pin['npm_version']} ({pin['upstream_tag']}, {pin['upstream_commit'][:7]})")
        for c in checks:
            mark = "ok  " if c["ok"] else ("MISS" if c["required"] else "info")
            out(f"  {mark} {c['name']:<14} {c['detail']}")
            if c.get("fix"):
                out(f"       fix: {c['fix']}")
        if missing:
            out("needs_setup: " + ", ".join(missing))
    return 0 if report["video_engine"] == "toolchain verified" else EXIT_SETUP


# --------------------------------------------------------------------------
# environment and child processes
# --------------------------------------------------------------------------

def child_env(pin: dict, engine: dict) -> dict:
    env = {k: v for k, v in os.environ.items() if not SECRET_NAME.search(k)}
    ver = pin["npm_version"]
    tc = toolchain_dir(pin)
    ENGINE_HOME.mkdir(parents=True, exist_ok=True)
    env.update({
        "HYPERFRAMES_SKIP_SKILLS": "1",
        "HYPERFRAMES_NO_UPDATE_CHECK": "1",
        "HYPERFRAMES_NO_AUTO_INSTALL": "1",
        "HYPERFRAMES_NO_TELEMETRY": "1",
        "DO_NOT_TRACK": "1",
        "HYPERFRAMES_SKILL_PKG_VERSION": ver,
        "HYPERFRAMES_PLUGIN_VERSION": ver,
        "HYPERFRAMES_SKILL_NODE_MODULES": str(tc / "node_modules"),
        "HYPERFRAMES_PREVIEW_HOST": "127.0.0.1",
        "HOME": str(ENGINE_HOME),
        "npm_config_offline": "true",
        "npm_config_update_notifier": "false",
        "npm_config_fund": "false",
        "npm_config_audit": "false",
        "EDITOR_HF_LAUNCHER": "1",
        "EDITOR_HF_REAL_PATH": clean_path(),
    })
    env.pop("HYPERFRAMES_PREVIEW_HOST_OVERRIDE", None)
    if engine.get("browser_path"):
        env["HYPERFRAMES_BROWSER_PATH"] = engine["browser_path"]
    ws = engine.get("workspace")
    if ws:
        tmp = Path(ws) / ".video-editor" / "tmp"
        tmp.mkdir(parents=True, exist_ok=True)
        env["TMPDIR"] = str(tmp)
    ensure_shims()
    env["PATH"] = os.pathsep.join([str(SHIM_DIR), clean_path()])
    return env


SHIM_NAMES = ["npx", "npm", "pnpm", "yarn", "bun", "bunx", "pip", "pip3", "uvx", "brew", "heygen", "hyperframes"]


def ensure_shims() -> None:
    SHIM_DIR.mkdir(parents=True, exist_ok=True)
    body = '#!/bin/sh\nexec python3 "{script}" _shim "{name}" "$@"\n'
    for name in SHIM_NAMES:
        target = SHIM_DIR / name
        want = body.format(script=str(SCRIPT), name=name)
        if not target.is_file() or target.read_text(encoding="utf-8") != want:
            target.write_text(want, encoding="utf-8")
            target.chmod(0o755)


def require_ready(pin: dict, engine: dict) -> None:
    checks = collect_checks(pin, engine)
    missing = [c for c in checks if c["required"] and not c["ok"]]
    if missing:
        fail(EXIT_SETUP, "needs_setup", "video engine: not configured",
             video_engine="not configured",
             missing=[{"name": c["name"], "detail": c["detail"], "fix": c.get("fix")} for c in missing])


def run_cli(pin: dict, engine: dict, args: list[str], capture: bool = False, cwd: str | None = None):
    node = which("node")
    cmd = [node, str(cli_entry(pin)), *args]
    return subprocess.run(
        cmd, env=child_env(pin, engine), cwd=cwd,
        capture_output=capture, text=True if capture else None,
    )


# --------------------------------------------------------------------------
# workspace boundary
# --------------------------------------------------------------------------

def workspace_root(engine: dict) -> Path:
    return Path(engine["workspace"]).resolve()


def looks_like_path(arg: str) -> bool:
    if arg.startswith("-") or URL_RE.match(arg):
        return False
    return arg.startswith((".", "/", "~")) or "/" in arg or os.sep in arg


def check_paths(engine: dict, args: list[str], extra_roots: tuple[Path, ...] = ()) -> None:
    root = workspace_root(engine)
    cwd = Path.cwd()
    if not inside(cwd, root):
        fail(EXIT_REFUSED, "blocked",
             f"working directory is outside the approved workspace: {cwd}",
             workspace=str(root),
             fix="cd into a project folder inside the workspace and run the command again")
    expect_path = False
    for arg in args:
        value = None
        if expect_path:
            value, expect_path = arg, False
        elif arg in OUTPUT_FLAGS:
            expect_path = True
            continue
        elif "=" in arg and arg.split("=", 1)[0] in OUTPUT_FLAGS:
            value = arg.split("=", 1)[1]
        elif looks_like_path(arg):
            value = arg
        if value is None:
            continue
        target = Path(os.path.expanduser(value))
        target = target if target.is_absolute() else cwd / target
        if not (inside(target, root) or any(inside(target, r) for r in extra_roots)):
            fail(EXIT_REFUSED, "blocked",
                 f"path is outside the approved workspace: {value}",
                 workspace=str(root),
                 fix="keep every project, source file and output inside the workspace")
        if inside(target, references_root(engine)):
            fail(EXIT_REFUSED, "blocked",
                 f"path is inside the reference folder: {value}",
                 reference_folder=str(references_root(engine)),
                 fix="reference videos are for study only; they never enter a project, a timeline, or a render")


def references_root(engine: dict) -> Path:
    return workspace_root(engine) / "references"


def find_project(start: Path, root: Path) -> Path:
    cur = start.resolve()
    while inside(cur, root):
        if (cur / "hyperframes.json").is_file() or (cur / "index.html").is_file():
            return cur
        if cur == root.resolve():
            break
        cur = cur.parent
    return start.resolve()


# --------------------------------------------------------------------------
# project checks: rights, external hosts, footage
# --------------------------------------------------------------------------

def iter_project_files(project: Path):
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            yield Path(dirpath) / name


def parse_register(path: Path) -> dict[str, dict]:
    """Minimal reader for templates/asset-rights-register.yaml.

    Reads `- asset:` list items with flat `key: value` fields. PyYAML is not
    assumed on the owner's machine, so the launcher stays standard-library."""
    entries: dict[str, dict] = {}
    current: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        m = re.match(r"^\s*-\s+asset:\s*(.*)$", line)
        if m:
            current = {"asset": m.group(1).strip().strip("\"'")}
            entries[current["asset"]] = current
            continue
        m = re.match(r"^\s+([a-z_]+):\s*(.*)$", line)
        if m and current is not None:
            current[m.group(1)] = m.group(2).strip().strip("\"'")
    return entries


EMPTY_VALUES = {"", "unknown", "tbd", "none", "null", "~", "unavailable", "needs source"}


def rights_report(project: Path) -> dict:
    register_path = project / "asset-rights-register.yaml"
    if not register_path.is_file() and (project.parent / "asset-rights-register.yaml").is_file():
        register_path = project.parent / "asset-rights-register.yaml"
    entries = parse_register(register_path) if register_path.is_file() else {}
    assets, unrecorded, incomplete = [], [], []
    for path in iter_project_files(project):
        if path.suffix.lower() not in ASSET_EXT:
            continue
        rel = path.relative_to(project).as_posix()
        assets.append(rel)
        entry = entries.get(rel)
        if entry is None:
            unrecorded.append(rel)
            continue
        gaps = [k for k in ("source", "license", "proof") if entry.get(k, "").lower() in EMPTY_VALUES]
        if gaps:
            incomplete.append({"asset": rel, "missing": gaps})
    return {
        "check": "asset rights",
        "register": str(register_path) if register_path.is_file() else None,
        "assets": len(assets),
        "unrecorded": unrecorded,
        "incomplete": incomplete,
        "ok": not unrecorded and not incomplete,
    }


def hosts_report(project: Path, engine: dict) -> dict:
    approved = set(engine.get("external_hosts") or [])
    found: dict[str, list[str]] = {}
    pinned_gsap = gsap_source(load_pin())
    pinned_gsap_sha = sha256_file(pinned_gsap[0]) if pinned_gsap else None
    for path in iter_project_files(project):
        if path.suffix.lower() not in {".html", ".htm", ".css", ".js", ".mjs"}:
            continue
        if path.name == "gsap.min.js" and pinned_gsap_sha and sha256_file(path) == pinned_gsap_sha:
            continue  # byte-identical to the lockfile-installed build; its only URLs are in messages
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # A URL inside a comment is not loaded (a library's license header,
        # for example). Everything else that looks like a URL counts.
        text = re.sub(r"/\*.*?\*/|<!--.*?-->", " ", text, flags=re.DOTALL)
        text = re.sub(r"(?m)^\s*//[^\n]*$", " ", text)
        for m in URL_RE.finditer(text):
            host = m.group(1).lower()
            if host in {"www.w3.org", "localhost", "127.0.0.1"} or host.endswith(".w3.org"):
                continue
            found.setdefault(host, [])
            rel = path.relative_to(project).as_posix()
            if rel not in found[host]:
                found[host].append(rel)
    unapproved = {h: f for h, f in sorted(found.items()) if h not in approved}
    return {
        "check": "external hosts",
        "approved": sorted(approved),
        "found": {h: f for h, f in sorted(found.items())},
        "unapproved": unapproved,
        "ok": not unapproved,
    }


def footage_manifest_path(engine: dict) -> Path:
    return workspace_root(engine) / ".video-editor" / "footage-manifest.json"


def load_footage(engine: dict) -> dict:
    path = footage_manifest_path(engine)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"files": {}}


def footage_report(engine: dict) -> dict:
    manifest = load_footage(engine)
    changed, missing = [], []
    for rel, rec in manifest["files"].items():
        path = workspace_root(engine) / rel
        if not path.is_file():
            missing.append(rel)
        elif sha256_file(path) != rec["sha256"]:
            changed.append(rel)
    return {"check": "source footage", "registered": len(manifest["files"]),
            "changed": changed, "missing": missing, "ok": not changed and not missing}


def cmd_footage_add(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    if not argv:
        fail(EXIT_USAGE, "blocked", "usage: hf.py footage-add <file> [<file> ...]")
    check_paths(engine, argv)
    manifest = load_footage(engine)
    root = workspace_root(engine)
    added = []
    for arg in argv:
        path = Path(os.path.expanduser(arg))
        path = path if path.is_absolute() else Path.cwd() / path
        if not path.is_file():
            fail(EXIT_CHECK, "blocked", f"not a file: {arg}")
        rel = path.resolve().relative_to(root).as_posix()
        rec = {"sha256": sha256_file(path), "bytes": path.stat().st_size, "registered_at": now_iso()}
        existing = manifest["files"].get(rel)
        if existing and existing["sha256"] != rec["sha256"]:
            fail(EXIT_CHECK, "blocked",
                 f"{rel} is already registered with a different checksum. An original changed.",
                 registered=existing["sha256"], current=rec["sha256"])
        manifest["files"].setdefault(rel, rec)
        added.append({"file": rel, "sha256": manifest["files"][rel]["sha256"]})
    mpath = footage_manifest_path(engine)
    mpath.parent.mkdir(parents=True, exist_ok=True)
    mpath.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out(json.dumps({"status": "registered", "read_only": True, "files": added}, indent=2))
    return 0


def cmd_simple_report(kind: str, argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    check_paths(engine, argv)
    project = find_project(Path(argv[0]) if argv else Path.cwd(), workspace_root(engine))
    if kind == "rights":
        report = rights_report(project)
    elif kind == "hosts":
        report = hosts_report(project, engine)
    elif kind == "references":
        report = references_report(project, engine)
    elif kind == "style":
        report = style_report(project, engine)
    elif kind == "ids":
        report = media_id_report(project)
    else:
        report = footage_report(engine)
    report["project"] = str(project)
    report["status"] = "pass" if report["ok"] else ("approval required" if kind == "style" else "blocked")
    if kind == "style" and report["ok"]:
        report["status"] = "style decision recorded"
    out(json.dumps(report, indent=2))
    return 0 if report["ok"] else EXIT_CHECK


# --------------------------------------------------------------------------
# editor gates: reference exclusion, style decision, timed-media ids
# --------------------------------------------------------------------------

PATH_TOKEN_RE = re.compile(
    r"""(?:src|href|poster|data-[a-z0-9-]+)\s*=\s*["']([^"']+)["']|url\(\s*["']?([^"')]+)["']?\s*\)""",
    re.IGNORECASE,
)
TEXT_EXT = {".html", ".htm", ".css", ".js", ".mjs", ".cjs", ".json", ".svg", ".md", ".txt", ".yaml", ".yml"}


def reference_hashes(engine: dict) -> dict[str, str]:
    """sha256 -> relative path for every file under references/. Cached by
    size and mtime so a long-form reference is hashed once."""
    root = references_root(engine)
    cache_path = workspace_root(engine) / WS_META / "reference-hashes.json"
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        cache = {}
    fresh: dict[str, dict] = {}
    result: dict[str, str] = {}
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(root).as_posix()
            st = path.stat()
            old = cache.get(rel)
            if old and old.get("size") == st.st_size and old.get("mtime") == int(st.st_mtime):
                digest = old["sha256"]
            else:
                digest = sha256_file(path)
            fresh[rel] = {"size": st.st_size, "mtime": int(st.st_mtime), "sha256": digest}
            result[digest] = rel
    if fresh != cache:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(fresh, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def references_report(project: Path, engine: dict) -> dict:
    """Prove no reference material sits in, or is pointed at by, a project."""
    refs = references_root(engine)
    hashes = reference_hashes(engine)
    violations: list[dict] = []
    if inside(project, refs):
        violations.append({"kind": "project inside the reference folder", "file": str(project)})
    for dirpath, dirnames, filenames in os.walk(project):
        dirnames[:] = [d for d in dirnames if d not in {"node_modules", ".git"}]
        for name in list(dirnames) + filenames:
            path = Path(dirpath) / name
            rel = path.relative_to(project).as_posix()
            if path.is_symlink():
                if inside(path, refs):
                    violations.append({"kind": "symlink into the reference folder", "file": rel})
                continue
            if not path.is_file():
                continue
            ext = path.suffix.lower()
            if ext in ASSET_EXT and hashes:
                if sha256_file(path) in hashes:
                    violations.append({"kind": "byte-identical copy of a reference file", "file": rel,
                                       "reference": hashes[sha256_file(path)]})
            if ext in TEXT_EXT and path.stat().st_size < 8_000_000:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if str(refs) in text:
                    violations.append({"kind": "absolute path into the reference folder", "file": rel})
                for m in PATH_TOKEN_RE.finditer(text):
                    token = (m.group(1) or m.group(2) or "").strip()
                    if not token or token.startswith(("#", "data:", "http:", "https:", "blob:", "mailto:")):
                        continue
                    token = token.split("?", 1)[0].split("#", 1)[0]
                    target = Path(os.path.expanduser(token))
                    target = target if target.is_absolute() else path.parent / target
                    if inside(target, refs):
                        violations.append({"kind": "path into the reference folder", "file": rel, "path": token})
    return {"check": "reference exclusion", "reference_folder": str(refs),
            "reference_files": len(hashes), "violations": violations, "ok": not violations,
            "limit": "A re-encoded, cropped or trimmed copy of a reference has a different checksum and is not detected here. "
                     "The rule still applies: nothing from a reference enters a deliverable."}


def parse_flat_yaml(path: Path) -> dict[str, str]:
    """Top-level `key: value` scalars only. Enough for the decision file, and
    keeps the launcher on the standard library."""
    data: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw or raw[0] in " \t#-":
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", raw)
        if not m:
            continue
        value = m.group(2).split(" #", 1)[0].strip().strip("\"'")
        data[m.group(1)] = value
    return data


def find_style_file(project: Path, root: Path) -> Path | None:
    for candidate in (project, project.parent):
        if inside(candidate, root) and (candidate / STYLE_FILE).is_file():
            return candidate / STYLE_FILE
    return None


def style_report(project: Path, engine: dict) -> dict:
    root = workspace_root(engine)
    path = find_style_file(project, root)
    report: dict = {"check": "style decision", "file": str(path) if path else None, "problems": [], "warnings": []}
    if path is None:
        report.update(ok=False, state="missing")
        report["problems"].append(
            f"no {STYLE_FILE} in the project. Study outliers and record the owner's choice, or record a one-edit waiver.")
        return report
    d = parse_flat_yaml(path)

    def empty(key: str) -> bool:
        return d.get(key, "").lower() in EMPTY_VALUES

    decision = d.get("decision", "")
    report["decision"] = decision or None
    for key in ("decided_by", "decided_at"):
        if empty(key):
            report["problems"].append(f"{key} is empty: a style choice is recorded with who made it and when")
    if decision == "waived":
        report["state"] = "outlier_study_waived"
        if empty("waiver_reason"):
            report["problems"].append("waiver_reason is empty")
        if d.get("waiver_scope") != "this_edit":
            report["problems"].append("waiver_scope must be this_edit: a waiver covers one edit, never every edit")
    elif decision in STYLE_OPTIONS:
        report["state"] = "style_chosen"
        for key in ("study_id", "blueprint_id"):
            if empty(key):
                report["problems"].append(f"{key} is empty: a chosen option names the study and blueprint it came from")
        valid = d.get("blueprint_valid_until", "")
        report["blueprint_valid_until"] = valid or None
        try:
            stale = _dt.date.fromisoformat(valid[:10]) < _dt.date.today()
        except ValueError:
            stale = None
            report["problems"].append("blueprint_valid_until is missing or not an ISO date")
        if stale:
            if empty("stale_blueprint_accepted_by"):
                report["problems"].append(
                    f"the blueprint went stale on {valid[:10]}. Refresh the study, or have the approver record "
                    "stale_blueprint_accepted_by to reuse it for this edit.")
            else:
                report["warnings"].append(f"stale blueprint reused, accepted by {d['stale_blueprint_accepted_by']}")
    else:
        report["state"] = "invalid"
        report["problems"].append(
            "decision must be one of: house_style, outlier_matched, hybrid, waived. Silence is not a choice.")
    report["ok"] = not report["problems"]
    return report


MEDIA_TAG_RE = re.compile(r"<(audio|video)\b([^>]*)>", re.IGNORECASE)


def media_id_report(project: Path) -> dict:
    """Timed media needs an id. Upstream documents that an <audio> element
    with no id is not picked up by the mixer, which renders silence."""
    missing = []
    for path in iter_project_files(project):
        if path.suffix.lower() not in {".html", ".htm"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
        for m in MEDIA_TAG_RE.finditer(text):
            if not re.search(r"""\bid\s*=\s*["'][^"']+["']""", m.group(2)):
                line = text.count("\n", 0, m.start()) + 1
                missing.append({"file": path.relative_to(project).as_posix(), "line": line,
                                "element": m.group(1).lower(), "tag": m.group(0)[:120]})
    return {"check": "timed media ids", "missing_id": missing, "ok": not missing}


# --------------------------------------------------------------------------
# memory: plan workers from a measurement, record the peak
# --------------------------------------------------------------------------

def measure_memory() -> dict:
    """Total and currently available physical memory, in MB, with the method."""
    total = avail = None
    method = "unavailable"
    try:
        if sys.platform == "darwin":
            total = int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True,
                                       timeout=10).stdout.strip()) // (1 << 20)
            vm = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=10).stdout
            page = int(re.search(r"page size of (\d+) bytes", vm).group(1))
            pages = sum(int(re.search(rf"{name}:\s+(\d+)\.", vm).group(1))
                        for name in ("Pages free", "Pages inactive", "Pages speculative"))
            avail = pages * page // (1 << 20)
            method = "sysctl hw.memsize; vm_stat free + inactive + speculative"
        else:
            info = Path("/proc/meminfo").read_text(encoding="utf-8")
            total = int(re.search(r"MemTotal:\s+(\d+) kB", info).group(1)) // 1024
            avail = int(re.search(r"MemAvailable:\s+(\d+) kB", info).group(1)) // 1024
            method = "/proc/meminfo MemTotal, MemAvailable"
    except Exception as exc:  # measurement failed: say so, plan one worker
        method = f"unavailable ({type(exc).__name__})"
    return {"total_mb": total, "available_mb": avail, "method": method, "cpu_count": os.cpu_count() or 1}


def measurements_path(engine: dict) -> Path:
    return workspace_root(engine) / WS_META / "render-measurements.json"


def load_measurements(engine: dict) -> list[dict]:
    try:
        return json.loads(measurements_path(engine).read_text(encoding="utf-8"))
    except Exception:
        return []


def canvas_pixels(project: Path) -> int | None:
    """Width times height of the project's root composition, when it states one."""
    try:
        text = (project / "index.html").read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None
    w, h = re.search(r'data-width="(\d+)"', text), re.search(r'data-height="(\d+)"', text)
    return int(w.group(1)) * int(h.group(1)) if w and h else None


def plan_workers(engine: dict, pixels: int | None = None) -> dict:
    """Workers from free memory and a per-worker figure measured on this
    machine at this canvas size or larger. A small-canvas render says little
    about the memory a 1080p worker needs, so smaller renders are not used."""
    mem = measure_memory()
    history = [m for m in load_measurements(engine) if m.get("peak_tree_rss_mb") and m.get("workers")]
    if pixels:
        history = [m for m in history if (m.get("width") or 0) * (m.get("height") or 0) >= pixels]
    size = f" at {pixels} pixels or larger" if pixels else ""
    if history:
        per_worker = max(int(m["peak_tree_rss_mb"] / m["workers"]) for m in history)
        basis = f"largest measured peak per worker on this machine{size}, from {len(history)} recorded render(s)"
    else:
        per_worker = WORKER_MB_ASSUMED
        basis = (f"planning figure, no measured render on record{size} yet "
                 "(upstream states about 256 MB per worker; doubled)")
    if mem["available_mb"] is None:
        workers, reason = 1, "memory could not be measured, so one worker"
    else:
        reserve = max(1024, int(mem["total_mb"] * 0.15))
        by_mem = (mem["available_mb"] - reserve) // per_worker
        workers = int(max(1, min(by_mem, max(1, mem["cpu_count"] - 1))))
        reason = (f"({mem['available_mb']} MB available - {reserve} MB reserve) / {per_worker} MB per worker, "
                  f"capped at {max(1, mem['cpu_count'] - 1)} by CPU count")
    return {"workers": workers, "reason": reason, "per_worker_mb": per_worker, "per_worker_basis": basis, **mem}


def tree_rss_mb(root_pid: int) -> int:
    try:
        ps = subprocess.run(["ps", "-axo", "pid=,ppid=,rss="], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return 0
    children: dict[int, list[int]] = {}
    rss: dict[int, int] = {}
    for line in ps.splitlines():
        parts = line.split()
        if len(parts) != 3 or not all(x.isdigit() for x in parts):
            continue
        pid, ppid, kb = (int(x) for x in parts)
        children.setdefault(ppid, []).append(pid)
        rss[pid] = kb
    total, stack, seen = 0, [root_pid], set()
    while stack:
        pid = stack.pop()
        if pid in seen:
            continue
        seen.add(pid)
        total += rss.get(pid, 0)
        stack.extend(children.get(pid, []))
    return total // 1024


def run_cli_measured(pin: dict, engine: dict, args: list[str], cwd: str | None = None) -> tuple[int, int]:
    """Run the pinned CLI and sample the peak memory of its process tree."""
    import threading
    proc = subprocess.Popen([which("node"), str(cli_entry(pin)), *args], env=child_env(pin, engine), cwd=cwd)
    peak = [0]
    stop = threading.Event()

    def sample() -> None:
        while not stop.is_set():
            peak[0] = max(peak[0], tree_rss_mb(proc.pid))
            stop.wait(1.0)

    thread = threading.Thread(target=sample, daemon=True)
    thread.start()
    try:
        code = proc.wait()
    finally:
        stop.set()
        thread.join(timeout=5)
    return code, peak[0]


def measure_audio(path: Path) -> dict:
    """Peak and mean level of the first audio stream, from ffmpeg volumedetect."""
    ffmpeg = which("ffmpeg")
    if not ffmpeg:
        return {"audio_measured": False}
    proc = subprocess.run([ffmpeg, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0?", "-af", "volumedetect",
                           "-f", "null", "-"], capture_output=True, text=True, timeout=1800)
    peak = re.search(r"max_volume:\s*(-?[\d.]+|-inf) dB", proc.stderr)
    mean = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", proc.stderr)
    if not peak:
        return {"audio_measured": False}

    def num(m):
        return None if m is None or m.group(1) == "-inf" else float(m.group(1))

    peak_db, mean_db = num(peak), num(mean)
    return {"audio_measured": True, "audio_peak_db": peak_db, "audio_mean_db": mean_db,
            "audio_silent": peak_db is None or peak_db <= -80.0,
            "audio_at_full_scale": peak_db is not None and peak_db >= 0.0}


# --------------------------------------------------------------------------
# render and receipts
# --------------------------------------------------------------------------

def take_option(args: list[str], *names: str) -> tuple[str | None, list[str]]:
    rest, value, i = [], None, 0
    while i < len(args):
        a = args[i]
        if a in names and i + 1 < len(args):
            value = args[i + 1]
            i += 2
            continue
        if any(a.startswith(n + "=") for n in names):
            value = a.split("=", 1)[1]
            i += 1
            continue
        rest.append(a)
        i += 1
    return value, rest


def probe(path: Path) -> dict:
    ffprobe = which("ffprobe")
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return {"error": proc.stderr.strip()[:400]}
    data = json.loads(proc.stdout)
    video = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    audio = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
    num, _, den = (video.get("avg_frame_rate") or "0/1").partition("/")
    fps = round(float(num) / float(den), 3) if den and float(den) else None
    return {
        "container": (data.get("format") or {}).get("format_name"),
        "duration_seconds": round(float((data.get("format") or {}).get("duration", 0) or 0), 3),
        "width": video.get("width"),
        "height": video.get("height"),
        "frame_rate": fps,
        "video_codec": video.get("codec_name"),
        "pixel_format": video.get("pix_fmt"),
        "audio_codec": audio.get("codec_name") if audio else None,
        "has_audio": audio is not None,
    }


def yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value))


def write_receipt(project: Path, output: Path, stage: str, pin: dict, elapsed: float,
                  quality: str, cli_args: list[str], extra: dict | None = None) -> Path:
    info = probe(output)
    audio = measure_audio(output) if info.get("has_audio") else {"audio_measured": False}
    status = "draft rendered" if stage == "draft" else "final rendered with file path"
    extra = extra or {}
    fields = [
        ("receipt_version", 1),
        ("status", status),
        ("stage", stage),
        ("edit_state", "rough_cut_rendered" if stage == "draft" else "final_rendered"),
        ("inspected", False),
        ("inspection_note", "A zero exit code proves the process finished. It does not prove the cut works, the captions are accurate, or the audio is clean. Run edit-quality-review on snapshots before reporting this render."),
        ("output_path", str(output)),
        ("output_relative", output.relative_to(project).as_posix() if inside(output, project) else str(output)),
        ("sha256", sha256_file(output)),
        ("size_bytes", output.stat().st_size),
        ("duration_seconds", info.get("duration_seconds")),
        ("width", info.get("width")),
        ("height", info.get("height")),
        ("frame_rate", info.get("frame_rate")),
        ("container", info.get("container")),
        ("video_codec", info.get("video_codec")),
        ("pixel_format", info.get("pixel_format")),
        ("audio_codec", info.get("audio_codec")),
        ("has_audio", info.get("has_audio")),
        ("audio_measured", audio.get("audio_measured")),
        ("audio_peak_db", audio.get("audio_peak_db")),
        ("audio_mean_db", audio.get("audio_mean_db")),
        ("audio_silent", audio.get("audio_silent")),
        ("audio_at_full_scale", audio.get("audio_at_full_scale")),
        ("quality", quality),
        ("render_seconds", round(elapsed, 1)),
        ("workers", extra.get("workers")),
        ("workers_basis", extra.get("workers_basis")),
        ("available_memory_mb_before", extra.get("available_mb")),
        ("total_memory_mb", extra.get("total_mb")),
        ("peak_tree_rss_mb", extra.get("peak_tree_rss_mb")),
        ("style_decision", extra.get("style_decision")),
        ("style_decision_file", extra.get("style_decision_file")),
        ("comparison_option", extra.get("comparison_option")),
        ("batch_row", extra.get("batch_row")),
        ("rendered_at", now_iso()),
        ("engine", f"{pin['npm_package']}@{pin['npm_version']}"),
        ("upstream_commit", pin["upstream_commit"]),
        ("cli_arguments", " ".join(cli_args)),
        ("project", str(project)),
        ("probe_error", info.get("error")),
    ]
    receipts = project / "receipts"
    receipts.mkdir(exist_ok=True)
    path = receipts / f"{output.stem}.receipt.yaml"
    path.write_text("".join(f"{k}: {yaml_scalar(v)}\n" for k, v in fields), encoding="utf-8")
    return path


def record_measurement(engine: dict, output: Path, stage: str, quality: str, elapsed: float, extra: dict) -> None:
    info = probe(output)
    rows = load_measurements(engine)
    rows.append({
        "rendered_at": now_iso(), "stage": stage, "quality": quality,
        "duration_seconds": info.get("duration_seconds"), "width": info.get("width"), "height": info.get("height"),
        "frame_rate": info.get("frame_rate"), "render_seconds": round(elapsed, 1),
        "workers": extra.get("workers"), "peak_tree_rss_mb": extra.get("peak_tree_rss_mb"),
        "total_memory_mb": extra.get("total_mb"), "cpu_count": extra.get("cpu_count"),
    })
    path = measurements_path(engine)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows[-500:], indent=2) + "\n", encoding="utf-8")


def cmd_render(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    stage, args = take_option(argv, "--stage")
    if stage not in {"draft", "final"}:
        fail(EXIT_USAGE, "blocked", "render needs --stage draft or --stage final",
             fix="render a draft first, inspect it, then render final")
    comparison, args = take_option(args, "--comparison")
    for flag in ("--docker", "--gpu"):
        if flag in args:
            fail(EXIT_REFUSED, "blocked", f"{flag} is not available through this launcher")
    check_paths(engine, args)
    root = workspace_root(engine)
    positional = [a for a in args if not a.startswith("-") and looks_like_path(a) and Path(a).is_dir()]
    project = find_project(Path(positional[0]) if positional else Path.cwd(), root)
    if not inside(project, root / "projects"):
        fail(EXIT_REFUSED, "blocked", f"render from a project under {root / 'projects'}, not {project}",
             fix="one project folder per video, one subfolder per version")

    quality, args = take_option(args, "--quality")
    if stage == "draft":
        quality = quality or "draft"
        if quality != "draft":
            fail(EXIT_REFUSED, "blocked", "a draft render uses --quality draft")
    else:
        quality = quality or "delivery"
        if quality == "draft":
            fail(EXIT_REFUSED, "blocked",
                 "a draft-quality file cannot be a final render",
                 fix="use --stage draft, or pick looks, delivery, standard or high for final")

    refs = references_report(project, engine)
    if not refs["ok"]:
        fail(EXIT_CHECK, "blocked", "reference material is in or pointed at by this project",
             violations=refs["violations"],
             fix="remove it. Reference videos are studied for technique; nothing from one enters a deliverable.")
    ids = media_id_report(project)
    if not ids["ok"]:
        fail(EXIT_CHECK, "blocked", "timed media without an id: an <audio> element with no id renders silent",
             missing_id=ids["missing_id"], fix="give every <audio> and <video> element a unique id")
    hosts = hosts_report(project, engine)
    if not hosts["ok"]:
        fail(EXIT_CHECK, "approval required",
             "the composition loads from hosts the owner has not approved",
             unapproved=hosts["unapproved"],
             fix="owner approves a host with: hf.py setup --allow-host <host>, or remove the reference")

    style = style_report(project, engine)
    if stage == "final":
        if not style["ok"]:
            fail(EXIT_CHECK, "approval required", "no valid style decision is recorded for this project",
                 style_decision=style.get("state"), problems=style["problems"],
                 fix=f"present the style-match proposal, then record the approver's choice or a one-edit waiver in {STYLE_FILE}")
        if comparison:
            fail(EXIT_REFUSED, "blocked", "--comparison is for draft renders made before a style is chosen")
        rights = rights_report(project)
        if not rights["ok"]:
            fail(EXIT_CHECK, "blocked", "an asset has no complete license record",
                 unrecorded=rights["unrecorded"], incomplete=rights["incomplete"],
                 fix="record source, license and proof for each asset in asset-rights-register.yaml, or remove it")
        footage = footage_report(engine)
        if not footage["ok"]:
            fail(EXIT_CHECK, "blocked", "registered source footage changed or is missing",
                 changed=footage["changed"], missing=footage["missing"])
        drafts = sorted((project / "receipts").glob("*.receipt.yaml")) if (project / "receipts").is_dir() else []
        if not any('stage: "draft"' in p.read_text(encoding="utf-8") for p in drafts):
            fail(EXIT_CHECK, "blocked", "no draft render receipt exists for this project version",
                 fix="render with --stage draft, inspect snapshots, then render final")
    elif not style["ok"]:
        if comparison not in STYLE_OPTIONS:
            fail(EXIT_CHECK, "approval required",
                 "no style decision is recorded, and this draft is not tagged as a comparison option",
                 style_decision=style.get("state"), problems=style["problems"],
                 fix="record the choice or waiver, or tag the draft: --comparison house_style|outlier_matched|hybrid")

    batch, _ = take_option(list(args), "--batch")
    output, args = take_option(args, "-o", "--output")
    fmt, _ = take_option(list(args), "--format")
    ext = {"webm": "webm", "mov": "mov", "gif": "gif"}.get(fmt or "", "mp4")
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    if output is None:
        tag = f"{stage}-{comparison}" if comparison else stage
        name = f"{project.parent.name}-{project.name}-{tag}-{stamp}"
        # A batch render takes an output template; {index} keeps rows unique.
        output = str(project / "renders" / (f"{name}-{{index}}.{ext}" if batch else f"{name}.{ext}"))
    out_path = Path(os.path.expanduser(output))
    out_path = out_path if out_path.is_absolute() else Path.cwd() / out_path
    if not inside(out_path, root):
        fail(EXIT_REFUSED, "blocked", f"output is outside the approved workspace: {output}")
    if not batch and out_path.exists():
        fail(EXIT_REFUSED, "blocked", f"output already exists and will not be overwritten: {out_path}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    media_ext = {".mp4", ".webm", ".mov", ".gif"}

    plan = plan_workers(engine, canvas_pixels(project))
    workers, _ = take_option(list(args), "--workers", "-w")
    if workers is None:
        args += ["--workers", str(plan["workers"])]
        workers_used, basis = plan["workers"], f"planned from measured memory: {plan['reason']}"
    else:
        workers_used = int(workers) if workers.isdigit() else None
        basis = f"set by the caller; the memory plan was {plan['workers']}"
    extra = {"workers": workers_used, "workers_basis": basis, "available_mb": plan["available_mb"],
             "total_mb": plan["total_mb"], "cpu_count": plan["cpu_count"],
             "style_decision": style.get("decision") if style["ok"] else "pending",
             "style_decision_file": style.get("file"), "comparison_option": comparison}

    before = {p for p in out_path.parent.iterdir() if p.suffix.lower() in media_ext} if batch else set()
    cli_args = ["render", *args, "--quality", quality, "--output", str(out_path)]
    started = time.time()
    code, peak = run_cli_measured(pin, engine, cli_args)
    elapsed = time.time() - started
    extra["peak_tree_rss_mb"] = peak
    if batch:
        produced = sorted(p for p in out_path.parent.iterdir()
                          if p.is_file() and p not in before and p.suffix.lower() in media_ext and p.stat().st_size > 0)
    else:
        produced = [out_path] if out_path.is_file() and out_path.stat().st_size > 0 else []
    if code != 0 or not produced:
        after = measure_memory()
        fail(code or EXIT_CHECK, "render failed",
             "the render did not produce a file. Read the error above, fix the cause, and report what changed. Do not retry blindly.",
             exit_code=code, output_exists=bool(produced), render_seconds=round(elapsed, 1),
             workers=workers_used, peak_tree_rss_mb=peak, available_memory_mb_before=plan["available_mb"],
             available_memory_mb_after=after["available_mb"],
             memory_pressure_likely=bool(code in {137, 134, -9} or (plan["available_mb"] and peak > plan["available_mb"])),
             fix="if memory is the cause, lower --workers, report it to the owner, and render again once; otherwise fix the composition")
    receipts = []
    for i, produced_path in enumerate(produced):
        row_extra = {**extra, "batch_row": i if batch else None}
        receipts.append(str(write_receipt(project, produced_path, stage, pin, elapsed, quality, cli_args, row_extra)))
    record_measurement(engine, produced[0], stage, quality, elapsed, extra)
    out(json.dumps({
        "status": "draft rendered" if stage == "draft" else "final rendered with file path",
        "outputs": [str(p) for p in produced], "receipts": receipts, "render_seconds": round(elapsed, 1),
        "workers": workers_used, "peak_tree_rss_mb": peak, "style_decision": extra["style_decision"],
        "next": "inspect snapshots across the timeline, denser at the opening and at every cut near speech, before reporting this render",
    }, indent=2))
    return 0


def cmd_receipt(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    stage, args = take_option(argv, "--stage")
    if stage not in {"draft", "final"} or len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: hf.py receipt --stage draft|final <rendered-file>")
    check_paths(engine, args)
    path = Path(os.path.expanduser(args[0]))
    path = path if path.is_absolute() else Path.cwd() / path
    if not path.is_file():
        fail(EXIT_CHECK, "render failed", f"no file at {path}. Do not report a render that does not exist.")
    project = find_project(path.parent, workspace_root(engine))
    receipt = write_receipt(project, path.resolve(), stage, pin, 0.0, "unknown", ["receipt-only"])
    out(json.dumps({"status": "receipt written", "receipt": str(receipt)}, indent=2))
    return 0


# --------------------------------------------------------------------------
# preview lifecycle
# --------------------------------------------------------------------------

def engine_processes() -> list[dict]:
    """Processes that belong to this profile's video engine, and only those.

    Matched by this profile's own paths (its toolchain folder, its engine home,
    and its workspace temp folder), plus every descendant of a match. The
    browser binary is deliberately not a match: an owner who recorded an
    existing headless Chrome with --use-browser may be running it for other
    work, and stopping a preview here must never touch that."""
    pin, engine = load_pin(), load_engine()
    needles = [str(toolchain_dir(pin)), str(ENGINE_HOME)]
    if engine.get("workspace"):
        needles.append(str(Path(engine["workspace"]) / WS_META / "tmp"))
    try:
        ps = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return []
    rows: dict[int, tuple[int, str]] = {}
    for line in ps.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows[int(parts[0])] = (int(parts[1]), parts[2])
    mine = {pid for pid, (_, command) in rows.items()
            if any(n in command for n in needles) and "hf.py" not in command and pid != os.getpid()}
    grew = True
    while grew:                      # add descendants of anything already matched
        grew = False
        for pid, (ppid, command) in rows.items():
            if pid not in mine and ppid in mine and "hf.py" not in command and pid != os.getpid():
                mine.add(pid)
                grew = True
    return [{"pid": pid, "command": rows[pid][1][:160]} for pid in sorted(mine)]


def cmd_preview(action: str, argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    check_paths(engine, argv)
    if action == "start":
        refs = references_report(find_project(Path.cwd(), workspace_root(engine)), engine)
        if not refs["ok"]:
            fail(EXIT_CHECK, "blocked", "reference material is in or pointed at by this project",
                 violations=refs["violations"])
        port, rest = take_option(argv, "--port")
        args = ["preview", "--background", "--no-open", "--json", *rest]
        if port:
            args += ["--port", port]
        proc = run_cli(pin, engine, args, capture=True)
        out(proc.stdout.strip() or proc.stderr.strip())
        out(json.dumps({"status": "preview running" if proc.returncode == 0 else "preview failed",
                        "bind": "127.0.0.1", "stop_with": "hf.py preview-stop"}, indent=2))
        return proc.returncode
    if action == "status":
        proc = run_cli(pin, engine, ["preview", "--list", "--json"], capture=True)
        out(proc.stdout.strip() or proc.stderr.strip())
        out(json.dumps({"engine_processes": engine_processes()}, indent=2))
        return proc.returncode
    # stop: stop this project's preview, then every preview, then sweep.
    run_cli(pin, engine, ["preview", "--stop", *argv], capture=True)
    run_cli(pin, engine, ["preview", "--kill-all"], capture=True)
    deadline = time.time() + 15
    left = engine_processes()
    while left and time.time() < deadline:
        time.sleep(0.5)
        left = engine_processes()
    killed = []
    for proc in left:
        try:
            os.kill(proc["pid"], signal.SIGTERM)
            killed.append(proc)
        except OSError:
            pass
    if killed:
        time.sleep(2)
        for proc in engine_processes():
            try:
                os.kill(proc["pid"], signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.5)
    remaining = engine_processes()
    out(json.dumps({
        "status": "preview stopped" if not remaining else "orphaned processes remain",
        "terminated_orphans": killed, "remaining": remaining,
    }, indent=2))
    return 0 if not remaining else EXIT_CHECK


# --------------------------------------------------------------------------
# passthrough, scripts, shims
# --------------------------------------------------------------------------

RENDERING_SUBCOMMANDS = {"lint", "check", "validate", "inspect", "layout", "snapshot", "compare", "grade-compare"}


def refuse_subcommand(sub: str) -> "NoReturn":  # type: ignore[name-defined]
    reason = PROHIBITED.get(sub, "it is not on this profile's allowlist")
    status = "approval required" if sub == "add" else "blocked"
    extra = {"fix": "the owner runs, in their own terminal: hf.py setup --add-registry-item <name> --project <version-folder>"} if sub == "add" else {}
    fail(EXIT_REFUSED, status, f"`hyperframes {sub}` is not available in this profile: {reason}",
         subcommand=sub, mode="edit_and_render", **extra)


def cmd_passthrough(sub: str, argv: list[str]) -> int:
    if sub not in ALLOWED:
        refuse_subcommand(sub)
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    if sub == "render":
        return cmd_render(argv)
    if sub == "doctor":
        return cmd_doctor(["--deep", *argv])
    if sub == "transcribe" and not engine.get("transcription_model"):
        fail(EXIT_SETUP, "needs_setup",
             "transcription is unavailable: no speech model is installed",
             video_engine="toolchain verified",
             fix="use owner-provided captions, or the owner runs: hf.py setup --install-model parakeet")
    check_paths(engine, argv)
    if sub == "init":
        if not inside(Path.cwd(), workspace_root(engine) / "projects"):
            fail(EXIT_REFUSED, "blocked", "create projects under the workspace's projects/ folder",
                 fix="cd into projects/<video-id>/ and init the version folder there, for example v1")
        return cmd_init(pin, engine, argv)
    if sub in RENDERING_SUBCOMMANDS:
        dirs = [a for a in argv if not a.startswith("-") and looks_like_path(a) and Path(a).is_dir()]
        for start in ([Path(d) for d in dirs] or [Path.cwd()]):
            refs = references_report(find_project(start, workspace_root(engine)), engine)
            if not refs["ok"]:
                fail(EXIT_CHECK, "blocked", "reference material is in or pointed at by this project",
                     violations=refs["violations"],
                     fix="remove it. Reference videos are studied for technique; nothing from one enters a deliverable.")
    if sub == "snapshot":
        # `--describe` sends frames to a vision provider and runs by default
        # when a provider key is set. The launcher removes provider keys from
        # the environment and turns the option off explicitly as well.
        describe, rest = take_option(argv, "--describe")
        if describe not in (None, "false"):
            fail(EXIT_REFUSED, "blocked", "`snapshot --describe` sends frames to an external vision provider",
                 fix="inspect the snapshots with this profile's own configured model instead")
        argv = [*rest, "--describe", "false"]
    if sub == "transcribe":
        _, rest = take_option(argv, "--engine")
        argv = [*rest, "--engine", engine["transcription_model"]]
    return run_cli(pin, engine, [sub, *argv]).returncode


PROJECT_NOTE = """# HyperFrames project (Hermes video-editor profile)

This project belongs to the Hermes `video-editor` profile. The HyperFrames CLI
writes generic agent instructions into new projects; this profile replaces
them with this note because those instructions name commands that are not
available here.

- Load the `editor-hyperframes` skill before doing anything in this folder.
- Run every HyperFrames command through the profile's pinned launcher
  (`hf.py`), from inside this folder.
- There are no npm scripts. Do not add any.
- Rendering is local only. Nothing here is uploaded, published, or posted.
- Source footage is read-only. Outputs go to `renders/`, receipts to
  `receipts/`, and asset licenses to `asset-rights-register.yaml`.
- A final render needs `style-decision.yaml` in this folder or the video
  folder above it. Nothing from the workspace's `references/` folder may be
  copied or linked here.
"""

GSAP_CDN_RE = re.compile(r"https://cdn\.jsdelivr\.net/npm/gsap@([0-9.]+)/dist/gsap\.min\.js")
GSAP_LOCAL = "assets/vendor/gsap.min.js"


def gsap_source(pin: dict) -> tuple[Path, str] | None:
    pkg = toolchain_dir(pin) / "node_modules" / "gsap"
    try:
        version = json.loads((pkg / "package.json").read_text(encoding="utf-8"))["version"]
    except Exception:
        return None
    src = pkg / "dist" / "gsap.min.js"
    return (src, version) if src.is_file() else None


def vendor_gsap(pin: dict, project: Path) -> dict:
    """Copy the lockfile-installed GSAP build into the project and point the
    composition at it, so a render needs no CDN and works offline."""
    found = gsap_source(pin)
    if found is None:
        return {"status": "unavailable", "message": "the pinned toolchain has no GSAP build; the owner reruns setup --install-cli"}
    src, version = found
    dest = project / GSAP_LOCAL
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file() or sha256_file(dest) != sha256_file(src):
        shutil.copy2(src, dest)
    rewritten, other_versions = [], []
    for html in sorted(project.rglob("*.html")):
        if any(part in SKIP_DIRS for part in html.relative_to(project).parts):
            continue
        text = html.read_text(encoding="utf-8")
        rel = os.path.relpath(dest, html.parent).replace(os.sep, "/")

        def swap(m: re.Match) -> str:
            if m.group(1) != version:
                other_versions.append({"file": html.relative_to(project).as_posix(), "version": m.group(1)})
                return m.group(0)
            return rel

        new = GSAP_CDN_RE.sub(swap, text)
        if new != text:
            html.write_text(new, encoding="utf-8")
            rewritten.append(html.relative_to(project).as_posix())
    register = project / "asset-rights-register.yaml"
    entry = (f"  - asset: {GSAP_LOCAL}\n"
             f"    source: npm package gsap@{version}, installed by the owner-run toolchain setup from the pinned lockfile\n"
             "    license: GSAP Standard License (https://gsap.com/standard-license), not an OSI open-source license\n"
             "    proof: package.json license field of the installed gsap package\n"
             "    restrictions: no charge for use including commercial use; not for tools that let users build visual animations without code in competition with Webflow\n")
    if register.is_file():
        text = register.read_text(encoding="utf-8")
        if GSAP_LOCAL not in text:
            text = text.replace("assets: []", "assets:") if "assets: []" in text else text.rstrip("\n") + "\n"
            register.write_text(text.rstrip("\n") + "\n" + entry, encoding="utf-8")
    return {"status": "gsap vendored", "version": version, "file": str(dest), "sha256": sha256_file(dest),
            "rewritten": rewritten, "left_on_cdn": other_versions,
            "note": "A composition that pins a different GSAP version still loads it from the CDN, which needs an owner-approved host and a network connection at render time."}


def cmd_vendor_gsap(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    check_paths(engine, argv)
    project = find_project(Path(argv[0]) if argv else Path.cwd(), workspace_root(engine))
    result = vendor_gsap(pin, project)
    out(json.dumps(result, indent=2))
    return 0 if result["status"] == "gsap vendored" else EXIT_SETUP


REGISTER_STUB = """# Asset rights register for this project.
# Every font, sound, image, video, or registry block used in the composition
# needs one entry with a real source, license, and proof. `hf.py rights-check`
# and every final render fail while an asset in this folder has no complete
# entry. An asset with no recorded license is unusable.
assets: []
"""


def cmd_init(pin: dict, engine: dict, argv: list[str]) -> int:
    """Scaffold a project, then remove the routes around the launcher that the
    CLI scaffolds into it (npm scripts that call npx, generic agent files)."""
    argv = [a for a in argv if a != "--skip-skills"]
    has_media = any(a in {"-v", "--video", "-a", "--audio"} or a.startswith(("--video=", "--audio="))
                    for a in argv)
    if has_media and not engine.get("transcription_model") and "--skip-transcribe" not in argv:
        argv.append("--skip-transcribe")
    if "--non-interactive" not in argv:
        argv.append("--non-interactive")
    before = {p for p in Path.cwd().iterdir() if p.is_dir()}
    code = run_cli(pin, engine, ["init", *argv]).returncode
    if code != 0:
        return code
    created = [p for p in Path.cwd().iterdir() if p.is_dir() and p not in before]
    if (Path.cwd() / "hyperframes.json").is_file() and not created:
        created = [Path.cwd()]
    for project in created:
        pkg = project / "package.json"
        if pkg.is_file():
            data = json.loads(pkg.read_text(encoding="utf-8"))
            removed = sorted((data.get("scripts") or {}).keys())
            data["scripts"] = {}
            data["hermesVideoEditor"] = {
                "engine": f"{pin['npm_package']}@{pin['npm_version']}",
                "note": "npm scripts removed; run commands through the profile launcher",
                "removed_scripts": removed,
            }
            pkg.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        for name in ("AGENTS.md", "CLAUDE.md", "GEMINI.md"):
            if (project / name).is_file():
                (project / name).write_text(PROJECT_NOTE, encoding="utf-8")
        for sub_dir in ("renders", "receipts", "assets"):
            (project / sub_dir).mkdir(exist_ok=True)
        register = project / "asset-rights-register.yaml"
        if not register.exists():
            register.write_text(REGISTER_STUB, encoding="utf-8")
        vendor_gsap(pin, project)
    out(json.dumps({"status": "project created",
                    "projects": [str(p) for p in created],
                    "next": "confirm the brand identity and record the style decision before writing composition HTML"}, indent=2))
    return 0


def cmd_script(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    if not argv:
        fail(EXIT_USAGE, "blocked", "usage: hf.py script <bundled-script> [args]")
    script = Path(os.path.expanduser(argv[0]))
    candidates = [script] if script.is_absolute() else [Path.cwd() / script, BUNDLE_DIR / script,
                                                         BUNDLE_DIR / "skills" / script]
    found = next((c for c in candidates if c.is_file()), None)
    if found is None or not inside(found, BUNDLE_DIR):
        fail(EXIT_REFUSED, "blocked",
             f"not a bundled HyperFrames script: {argv[0]}",
             fix=f"pass an absolute path under {BUNDLE_DIR}")
    if found.suffix not in {".mjs", ".cjs", ".js"}:
        fail(EXIT_REFUSED, "blocked", f"only bundled Node scripts run through the launcher: {found.name}")
    check_paths(engine, argv[1:], extra_roots=(BUNDLE_DIR,))
    env = child_env(pin, engine)
    return subprocess.run([which("node"), str(found), *argv[1:]], env=env).returncode


def cmd_plan_workers(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    project = find_project(Path.cwd(), workspace_root(engine)) if inside(Path.cwd(), workspace_root(engine)) else None
    pixels = canvas_pixels(project) if project else None
    out(json.dumps({**plan_workers(engine, pixels), "canvas_pixels": pixels}, indent=2))
    return 0


def cmd_limits(argv: list[str]) -> int:
    """What this machine has actually rendered, from recorded measurements."""
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    rows = [r for r in load_measurements(engine) if r.get("duration_seconds") and r.get("height")]
    tested: dict[str, dict] = {}
    for r in rows:
        key = f"{r['width']}x{r['height']} {r['stage']}"
        if key not in tested or r["duration_seconds"] > tested[key]["duration_seconds"]:
            tested[key] = r
    out(json.dumps({
        "status": "measured" if tested else "no render measured on this machine yet",
        "longest_render_per_resolution_and_stage": tested,
        "renders_on_record": len(rows),
        "rule": "Do not exceed the longest measured duration at a resolution without telling the owner first. "
                "Estimate a long render from a measured short segment, and say it is an estimate.",
    }, indent=2))
    return 0


def cmd_handoff(argv: list[str]) -> int:
    """Copy a receipt-backed render to the owner-approved handoff folder."""
    pin, engine = load_pin(), load_engine()
    require_ready(pin, engine)
    if len(argv) != 1:
        fail(EXIT_USAGE, "blocked", "usage: hf.py handoff <rendered-file>")
    check_paths(engine, argv)
    root = workspace_root(engine)
    src = Path(os.path.expanduser(argv[0]))
    src = (src if src.is_absolute() else Path.cwd() / src).resolve()
    if not src.is_file():
        fail(EXIT_CHECK, "render failed", f"no file at {src}. Do not report a render that does not exist.")
    if not inside(src, root / "projects") or src.parent.name != "renders":
        fail(EXIT_REFUSED, "blocked", "only a rendered file in a project's renders/ folder can be handed off",
             fix="footage, working copies, transcripts and reference material never leave the workspace through a handoff")
    project = src.parent.parent
    receipt = project / "receipts" / f"{src.stem}.receipt.yaml"
    digest = sha256_file(src)
    if not receipt.is_file() or f'sha256: "{digest}"' not in receipt.read_text(encoding="utf-8"):
        fail(EXIT_CHECK, "blocked", "no render receipt matches this file's checksum",
             fix="write one with: hf.py receipt --stage draft|final <file>")
    base = {"file": str(src), "sha256": digest, "size_bytes": src.stat().st_size, "receipt": str(receipt)}
    handoff = engine.get("handoff")
    if not handoff or not Path(handoff).is_dir():
        out(json.dumps({"status": "handoff route unavailable", **base,
                        "message": "No handoff folder is approved. The file stays in the workspace. Report this path and SHA-256.",
                        "fix": "owner runs: hf.py setup --handoff <folder>"}, indent=2))
        return 0
    dest_dir = Path(handoff) / project.parent.name / project.name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if dest.exists() and sha256_file(dest) != digest:
        fail(EXIT_REFUSED, "blocked", f"a different file already exists at {dest}; it will not be overwritten")
    shutil.copy2(src, dest)
    shutil.copy2(receipt, dest_dir / receipt.name)
    if sha256_file(dest) != digest:
        fail(EXIT_CHECK, "outcome unknown", "the copy does not match the source checksum", **base, copied_to=str(dest))
    record = dest_dir / f"{src.stem}.handoff.yaml"
    record.write_text("".join(f"{k}: {yaml_scalar(v)}\n" for k, v in [
        ("handoff_version", 1), ("file", str(dest)), ("sha256", digest), ("size_bytes", src.stat().st_size),
        ("source", str(src)), ("receipt", str(dest_dir / receipt.name)), ("copied_at", now_iso()),
        ("note", "A handed-off file is not an approved file and not a posted file."),
    ]), encoding="utf-8")
    out(json.dumps({"status": "handed off", **base, "handoff_file": str(dest), "handoff_record": str(record)}, indent=2))
    return 0


def cmd_shim(argv: list[str]) -> int:
    """Entry point for the PATH shims a child process may hit."""
    name, args = argv[0], argv[1:]
    pin = load_pin()
    if name == "hyperframes":
        return dispatch(args)
    if name in {"npx", "bunx", "uvx"}:
        rest = [a for a in args if a not in {"--yes", "-y", "--no-install", "--quiet", "-q"}]
        if rest and re.fullmatch(r"hyperframes(@[0-9A-Za-z.\-]+)?", rest[0]):
            spec = rest[0]
            if "@" in spec and spec.split("@", 1)[1] != pin["npm_version"]:
                fail(EXIT_REFUSED, "blocked",
                     f"only {pin['npm_package']}@{pin['npm_version']} runs in this profile, not {spec}")
            return dispatch(rest[1:])
        fail(EXIT_REFUSED, "blocked",
             f"`{name} {' '.join(args[:2])}` would download and run an unpinned package",
             fix="report the missing dependency to the owner; nothing is installed during a video task")
    fail(EXIT_REFUSED, "blocked",
         f"`{name}` is not available during a video task: installs and sign-ins are owner-run setup steps",
         attempted=f"{name} {' '.join(args[:3])}".strip())


# --------------------------------------------------------------------------
# setup (owner-run)
# --------------------------------------------------------------------------

DOWNLOADS = {
    "cli": {
        "item": "HyperFrames CLI and its dependencies ({pkg}@{ver}), plus GSAP 3.14.2: 172 locked packages",
        "source": "https://registry.npmjs.org (npm ci from the shipped package-lock.json, integrity-checked)",
        "size": "about 235 MB on disk",
        "license": "Apache-2.0 for HyperFrames (Copyright 2026 HeyGen, Inc.); GSAP under the GSAP Standard License (not an OSI license); each other dependency under its own license, listed in the lockfile",
    },
    "browser": {
        "item": "Headless Chrome (chrome-headless-shell, the build pinned by the CLI)",
        "source": "Chrome for Testing, downloaded by the pinned CLI through @puppeteer/browsers",
        "size": "about 190 MB on disk",
        "license": "Chromium open-source licenses (BSD-3-Clause and others); read the terms at the source before approving",
    },
    "parakeet": {
        "item": "Parakeet TDT 0.6B v3 speech model (int8 ONNX export) and its sherpa-onnx runtime",
        "source": "Hugging Face, csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8, downloaded by the pinned CLI",
        "size": "about 670 MB of model files, plus the sherpa-onnx runtime",
        "license": "CC-BY-4.0 for the model (NVIDIA); sherpa-onnx is Apache-2.0",
    },
}


def confirm(key: str, pin: dict, yes: bool) -> dict:
    d = {k: v.format(pkg=pin["npm_package"], ver=pin["npm_version"]) for k, v in DOWNLOADS[key].items()}
    out("")
    out(f"Download:  {d['item']}")
    out(f"Source:    {d['source']}")
    out(f"Size:      {d['size']}")
    out(f"License:   {d['license']}")
    if not yes:
        if not sys.stdin.isatty():
            fail(EXIT_REFUSED, "approval required",
                 "this download needs the owner's approval at an interactive terminal",
                 **d, fix="the owner runs this setup command in their own terminal")
        if input("Approve this download? [y/N] ").strip().lower() not in {"y", "yes"}:
            fail(EXIT_REFUSED, "blocked", "download declined by the owner; nothing was changed")
    return d


def record_approval(engine: dict, key: str, d: dict) -> None:
    engine.setdefault("approvals", []).append(
        {"key": key, **d, "approved_at": now_iso(), "approved_by_os_user": os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"}
    )


def cmd_setup(argv: list[str]) -> int:
    pin, engine = load_pin(), load_engine()
    yes = "--yes" in argv
    argv = [a for a in argv if a != "--yes"]
    if not argv or argv == ["--plan"]:
        out("Video toolchain setup for the video-editor profile. Nothing below runs until the owner asks for it.")
        out(f"Profile home: {PROFILE_HOME}")
        out(f"Engine folder: {ENGINE_DIR}")
        out("")
        out("You install these yourself (the profile never does): Node.js "
            f"{pin['node_minimum_major']} or newer, FFmpeg.")
        for key in ("cli", "browser", "parakeet"):
            d = {k: v.format(pkg=pin["npm_package"], ver=pin["npm_version"]) for k, v in DOWNLOADS[key].items()}
            out("")
            out(f"[{key}] {d['item']}")
            out(f"    source:  {d['source']}")
            out(f"    size:    {d['size']}")
            out(f"    license: {d['license']}")
        out("")
        out("Commands, each run by the owner:")
        out("  hf.py setup --workspace <folder>      approve the video workspace")
        out("  hf.py setup --install-cli             install the pinned CLI from the lockfile")
        out("  hf.py setup --download-browser        download the pinned headless Chrome")
        out("  hf.py setup --use-browser <path>      or record a headless Chrome you already have")
        out("  hf.py setup --install-model parakeet  optional: local transcription")
        out("  hf.py setup --allow-host <host>       approve a render-time host, for example cdn.jsdelivr.net for GSAP")
        out("  hf.py setup --handoff <folder>        optional: approve a folder for delivering renders to teammates")
        out("  hf.py setup --add-registry-item <name> --project <version-folder>")
        out("                                        optional: fetch one registry item (from upstream main, not the pinned release)")
        out("  hf.py setup --remove cli|browser|model|all")
        return 0

    i = 0
    while i < len(argv):
        flag = argv[i]
        value = argv[i + 1] if i + 1 < len(argv) and not argv[i + 1].startswith("--") else None
        i += 2 if value is not None else 1

        if flag == "--workspace":
            if not value:
                fail(EXIT_USAGE, "blocked", "--workspace needs a folder")
            ws = Path(os.path.expanduser(value)).resolve()
            too_broad = (
                ws == Path(ws.anchor) or ws == Path.home().resolve()
                or inside(PROFILE_HOME, ws)            # the profile home or any ancestor of it
                or inside(ws, PROFILE_HOME / "skills")  # inside the installed skills
            )
            if too_broad:
                fail(EXIT_REFUSED, "blocked", f"refusing an over-broad workspace: {ws}",
                     fix="choose a dedicated folder for video projects")
            for sub in WS_DIRS:
                (ws / sub).mkdir(parents=True, exist_ok=True)
            engine["workspace"] = str(ws)
            out(f"workspace approved: {ws}")

        elif flag == "--install-cli":
            node, npm = which("node"), which("npm")
            ver = node_version(node) if node else None
            if not node or not npm or not ver or ver[0] < int(pin["node_minimum_major"]):
                fail(EXIT_SETUP, "needs_setup",
                     f"Node.js {pin['node_minimum_major']} or newer with npm is required first",
                     found=ver[1] if ver else None)
            d = confirm("cli", pin, yes)
            tc = toolchain_dir(pin)
            tc.mkdir(parents=True, exist_ok=True)
            for name in ("package.json", "package-lock.json"):
                shutil.copy2(TOOLCHAIN_SRC / name, tc / name)
            if sha256_file(tc / "package-lock.json") != pin["package_lock_sha256"]:
                fail(EXIT_CHECK, "blocked", "shipped lockfile does not match the recorded checksum")
            proc = subprocess.run(
                [npm, "ci", "--ignore-scripts", "--no-audit", "--no-fund"], cwd=str(tc),
                env={k: v for k, v in os.environ.items() if not SECRET_NAME.search(k)},
            )
            if proc.returncode != 0:
                fail(proc.returncode, "blocked", "npm ci failed; the pinned CLI is not installed. Nothing falls back to another version.")
            installed = json.loads((tc / "node_modules/hyperframes/package.json").read_text(encoding="utf-8"))["version"]
            if installed != pin["npm_version"]:
                fail(EXIT_CHECK, "blocked", f"installed {installed}, expected {pin['npm_version']}")
            record_approval(engine, "cli", d)
            out(f"installed {pin['npm_package']}@{installed} into {tc}")

        elif flag == "--download-browser":
            if not cli_entry(pin).is_file():
                fail(EXIT_SETUP, "needs_setup", "install the CLI first: hf.py setup --install-cli")
            d = confirm("browser", pin, yes)
            env = child_env(pin, engine)
            env.pop("HYPERFRAMES_BROWSER_PATH", None)
            env.pop("npm_config_offline", None)
            subprocess.run([which("node"), str(cli_entry(pin)), "browser", "ensure"], env=env)
            proc = subprocess.run([which("node"), str(cli_entry(pin)), "browser", "path"],
                                  env=env, capture_output=True, text=True)
            path = (proc.stdout.strip().splitlines() or [""])[-1].strip()
            if not path or not Path(path).is_file():
                fail(EXIT_CHECK, "blocked", "the browser download did not produce an executable")
            engine["browser_path"] = path
            record_approval(engine, "browser", d)
            out(f"browser recorded: {path}")

        elif flag == "--use-browser":
            if not value or not Path(os.path.expanduser(value)).is_file():
                fail(EXIT_USAGE, "blocked", "--use-browser needs the path of an existing headless Chrome executable")
            engine["browser_path"] = str(Path(os.path.expanduser(value)).resolve())
            engine.setdefault("approvals", []).append(
                {"key": "browser-existing", "item": engine["browser_path"], "source": "already on this machine",
                 "size": "no download", "license": "owner's existing install", "approved_at": now_iso()})
            out(f"browser recorded (no download): {engine['browser_path']}")

        elif flag == "--install-model":
            if value != "parakeet":
                fail(EXIT_USAGE, "blocked", "the only model this release can install is: parakeet")
            if not cli_entry(pin).is_file():
                fail(EXIT_SETUP, "needs_setup", "install the CLI first: hf.py setup --install-cli")
            d = confirm("parakeet", pin, yes)
            env = child_env(pin, engine)
            env.pop("npm_config_offline", None)
            env["PATH"] = clean_path()
            proc = subprocess.run([which("node"), str(cli_entry(pin)), "models", "install", "parakeet"], env=env)
            if proc.returncode != 0:
                fail(proc.returncode, "blocked", "model install failed; transcription stays unavailable")
            engine["transcription_model"] = "parakeet"
            record_approval(engine, "parakeet", d)
            out("transcription model installed: parakeet")

        elif flag == "--allow-host":
            if not value or not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", value):
                fail(EXIT_USAGE, "blocked", "--allow-host needs a bare host name, for example cdn.jsdelivr.net")
            hosts = set(engine.get("external_hosts") or [])
            hosts.add(value)
            engine["external_hosts"] = sorted(hosts)
            engine.setdefault("approvals", []).append({"key": "host", "item": value, "approved_at": now_iso()})
            out(f"render-time host approved: {value}")

        elif flag == "--deny-host":
            engine["external_hosts"] = sorted(set(engine.get("external_hosts") or []) - {value})
            out(f"render-time host removed: {value}")

        elif flag == "--handoff":
            if not value:
                fail(EXIT_USAGE, "blocked", "--handoff needs a folder")
            folder = Path(os.path.expanduser(value)).resolve()
            if folder == Path(folder.anchor) or folder == Path.home().resolve() or inside(PROFILE_HOME, folder):
                fail(EXIT_REFUSED, "blocked", f"refusing an over-broad handoff folder: {folder}")
            folder.mkdir(parents=True, exist_ok=True)
            engine["handoff"] = str(folder)
            engine.setdefault("approvals", []).append({"key": "handoff", "item": str(folder), "approved_at": now_iso()})
            out(f"handoff folder approved: {folder}")

        elif flag == "--project":
            pass  # consumed by --add-registry-item

        elif flag == "--add-registry-item":
            proj_value = argv[argv.index("--project") + 1] if "--project" in argv and argv.index("--project") + 1 < len(argv) else None
            if not value or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value) or not proj_value:
                fail(EXIT_USAGE, "blocked", "usage: hf.py setup --add-registry-item <name> --project <version-folder>")
            if not engine.get("workspace") or not cli_entry(pin).is_file():
                fail(EXIT_SETUP, "needs_setup", "approve a workspace and install the CLI first")
            project = Path(os.path.expanduser(proj_value)).resolve()
            if not inside(project, workspace_root(engine) / "projects") or not project.is_dir():
                fail(EXIT_REFUSED, "blocked", f"--project must be a version folder under the workspace's projects/: {project}")
            DOWNLOADS["registry"] = {
                "item": f"HyperFrames registry item `{value}`",
                "source": "https://raw.githubusercontent.com/heygen-com/hyperframes/main/registry (the upstream main branch, NOT the pinned release; contents can change between fetches)",
                "size": "not known before the fetch; the file list and hashes are recorded after it",
                "license": "Apache-2.0 for HeyGen-authored items; some items vendor or load third-party code and assets listed in upstream CREDITS.md, and a few assets have an unconfirmed origin. Read the fetched files before using the item in a deliverable.",
            }
            d = confirm("registry", pin, yes)
            before = {q.relative_to(project).as_posix(): sha256_file(q) for q in project.rglob("*") if q.is_file() and "node_modules" not in q.parts}
            env = child_env(pin, engine)
            env.pop("npm_config_offline", None)
            proc = subprocess.run([which("node"), str(cli_entry(pin)), "add", value], env=env, cwd=str(project))
            if proc.returncode != 0:
                fail(proc.returncode, "outcome unknown", "the registry fetch did not finish cleanly. Inspect the project before trying again; nothing is retried automatically.")
            after = {q.relative_to(project).as_posix(): sha256_file(q) for q in project.rglob("*") if q.is_file() and "node_modules" not in q.parts}
            changed = {rel: h for rel, h in sorted(after.items()) if before.get(rel) != h}
            lock_path = project / "registry-items.lock.json"
            try:
                lock = json.loads(lock_path.read_text(encoding="utf-8"))
            except Exception:
                lock = {"items": []}
            lock["items"].append({"item_name": value, "item_source_url": d["source"], "source_ref": "main (unpinned)",
                                  "fetched_at": now_iso(), "fetched_with": f"{pin['npm_package']}@{pin['npm_version']}",
                                  "files_sha256": changed, "license": "record in asset-rights-register.yaml before use"})
            lock_path.write_text(json.dumps(lock, indent=2) + "\n", encoding="utf-8")
            record_approval(engine, "registry", d)
            out(f"fetched registry item {value}: {len(changed)} file(s) written, hashes recorded in {lock_path}")

        elif flag == "--remove":
            targets = {"cli", "browser", "model"} if value == "all" else {value}
            if "cli" in targets:
                for d_ in ENGINE_DIR.glob("toolchain-*"):
                    shutil.rmtree(d_, ignore_errors=True)
                shutil.rmtree(SHIM_DIR, ignore_errors=True)
                out("removed: CLI toolchain")
            if "browser" in targets:
                shutil.rmtree(ENGINE_HOME / ".cache" / "hyperframes" / "chrome", ignore_errors=True)
                shutil.rmtree(ENGINE_HOME / ".cache" / "puppeteer", ignore_errors=True)
                engine.pop("browser_path", None)
                out("removed: downloaded browser (a browser recorded with --use-browser is left in place)")
            if "model" in targets:
                for name in ("parakeet", "whisper", "models"):
                    shutil.rmtree(ENGINE_HOME / ".cache" / "hyperframes" / name, ignore_errors=True)
                engine.pop("transcription_model", None)
                out("removed: speech models")
        else:
            fail(EXIT_USAGE, "blocked", f"unknown setup option: {flag}", fix="run: hf.py setup --plan")
        save_engine(engine)
    return 0


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------

HELP = """hf.py: pinned HyperFrames launcher for the video-editor profile

Statuses: not configured | toolchain verified | style decision recorded |
draft rendered | final rendered with file path | render failed |
approval required | outcome unknown

  status | doctor [--json] [--deep]   report the video engine state (no network)
  pin                                 print the pinned release
  setup --plan | setup <options>      OWNER ONLY: downloads and approvals
  init | lint | check | validate | inspect | layout | snapshot | info
  compositions | timeline | keyframes | beats | catalog | compare
  grade-compare | normalize-audio | history | clean | docs | usage
                                      run the pinned CLI inside the workspace
  render --stage draft|final [...]    render, then write a receipt
         [--comparison house_style|outlier_matched|hybrid]   tag a draft made before a style is chosen
  receipt --stage draft|final <file>  write a receipt for an existing render
  preview-start | preview-status | preview-stop
  footage-add <file...>               register originals and their checksums
  footage-verify                      prove no original changed
  rights-check [project]              every asset has a license record
  hosts-check [project]               every external host is owner-approved
  references-check [project]          nothing from references/ is in or linked from the project
  style-check [project]               a style decision or one-edit waiver is recorded
  ids-check [project]                 every <audio> and <video> element has an id
  plan-workers                        worker count from measured memory
  limits                              longest render this machine has on record, per resolution
  handoff <rendered-file>             copy a receipt-backed render to the approved handoff folder
  vendor-gsap [project]               use the lockfile-installed GSAP build instead of the CDN
  script <bundled-script> [args]      run a bundled Node helper, pinned
"""


def dispatch(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        out(HELP)
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in {"status", "doctor"} and os.environ.get("EDITOR_HF_LAUNCHER") != "1":
        return cmd_doctor(rest)
    if cmd == "pin":
        out(json.dumps(load_pin(), indent=2))
        return 0
    if cmd == "setup":
        return cmd_setup(rest)
    if cmd == "_shim":
        return cmd_shim(rest)
    if cmd == "script":
        return cmd_script(rest)
    if cmd == "receipt":
        return cmd_receipt(rest)
    if cmd == "footage-add":
        return cmd_footage_add(rest)
    if cmd == "footage-verify":
        return cmd_simple_report("footage", rest)
    if cmd == "rights-check":
        return cmd_simple_report("rights", rest)
    if cmd == "hosts-check":
        return cmd_simple_report("hosts", rest)
    if cmd == "references-check":
        return cmd_simple_report("references", rest)
    if cmd == "style-check":
        return cmd_simple_report("style", rest)
    if cmd == "ids-check":
        return cmd_simple_report("ids", rest)
    if cmd == "plan-workers":
        return cmd_plan_workers(rest)
    if cmd == "limits":
        return cmd_limits(rest)
    if cmd == "handoff":
        return cmd_handoff(rest)
    if cmd == "vendor-gsap":
        return cmd_vendor_gsap(rest)
    if cmd in {"preview-start", "preview-status", "preview-stop"}:
        return cmd_preview(cmd.split("-", 1)[1], rest)
    if cmd.startswith("-"):
        fail(EXIT_USAGE, "blocked", f"unknown option: {cmd}")
    return cmd_passthrough(cmd, rest)


if __name__ == "__main__":
    try:
        sys.exit(dispatch(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
