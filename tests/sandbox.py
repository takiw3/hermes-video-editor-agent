"""Install-test sandbox: throwaway HOME and HERMES_HOME, Hermes runner, results.

Nothing here touches the developer's real profiles, accounts, or footage.
Every test runs under a temporary directory that is removed at exit.

Environment:
  HERMES_SRC      path to a Hermes checkout; run as `python -m hermes_cli.main`
  HERMES_PYTHON   interpreter with Hermes' dependencies (default: python3)
  HERMES_BIN      a `hermes` executable to use instead (default: `hermes` on PATH)
    VE_TEST_KEEP=1  keep the sandbox for inspection
"""

from __future__ import annotations

import atexit
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PROFILE = "video-editor"


class Results:
    def __init__(self, title: str):
        self.title = title
        self.rows: list[tuple[str, str, str]] = []

    def record(self, name: str, status: str, detail: str = "") -> None:
        assert status in {"pass", "fail", "not run"}
        self.rows.append((name, status, detail))
        mark = {"pass": "ok     ", "fail": "FAIL   ", "not run": "notrun "}[status]
        print(f"  {mark} {name}" + (f" -- {detail}" if detail else ""), flush=True)

    def check(self, name: str, cond: bool, detail: str = "") -> bool:
        self.record(name, "pass" if cond else "fail", "" if cond else detail)
        return bool(cond)

    def notrun(self, name: str, why: str) -> None:
        self.record(name, "not run", why)

    def finish(self, json_out: str | None = None) -> int:
        counts = {s: sum(1 for r in self.rows if r[1] == s) for s in ("pass", "fail", "not run")}
        print(f"\n{self.title}: {counts['pass']} pass, {counts['fail']} fail, {counts['not run']} not run")
        for name, status, detail in self.rows:
            if status == "fail":
                print(f"  FAILED: {name} -- {detail}")
        if json_out:
            Path(json_out).write_text(json.dumps(
                {"suite": self.title, "counts": counts,
                 "tests": [{"name": n, "status": s, "detail": d} for n, s, d in self.rows]},
                indent=2) + "\n", encoding="utf-8")
        return 1 if counts["fail"] else 0


class Sandbox:
    """A temporary HOME and HERMES_HOME."""

    def __init__(self):
        self.root = Path(tempfile.mkdtemp(prefix="video-editor-test-")).resolve()
        self.home = self.root / "home"
        self.hermes_home = self.root / "hermes"
        self.home.mkdir()
        self.hermes_home.mkdir()
        self.real_home = Path.home()
        atexit.register(self.cleanup)

    def cleanup(self) -> None:
        if os.environ.get("VE_TEST_KEEP") == "1":
            print(f"(kept sandbox: {self.root})")
            return
        shutil.rmtree(self.root, ignore_errors=True)

    @property
    def profile_dir(self) -> Path:
        return self.hermes_home / "profiles" / PROFILE

    def env(self, **extra) -> dict:
        env = dict(os.environ)
        env.update({"HOME": str(self.home), "HERMES_HOME": str(self.hermes_home)})
        env.pop("PYTHONPATH", None)
        env.update(extra)
        return env


def hermes_command() -> tuple[list[str], str | None] | None:
    """Return (argv prefix, cwd) for running Hermes, or None when unavailable."""
    src = os.environ.get("HERMES_SRC")
    if src and Path(src, "hermes_cli").is_dir():
        py = os.environ.get("HERMES_PYTHON") or sys.executable
        return [py, "-m", "hermes_cli.main"], src
    exe = os.environ.get("HERMES_BIN") or shutil.which("hermes")
    if exe:
        return [exe], None
    return None


def run_hermes(sb: Sandbox, args: list[str], timeout: int = 300, wrap: list[str] | None = None,
               env_extra: dict | None = None) -> subprocess.CompletedProcess:
    cmd, cwd = hermes_command()  # type: ignore[misc]
    full = (wrap or []) + cmd + args
    return subprocess.run(full, cwd=cwd, env=sb.env(**(env_extra or {})), capture_output=True,
                          text=True, timeout=timeout, stdin=subprocess.DEVNULL)


def hermes_python(sb: Sandbox, code: str, profile_scoped: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    """Run Python against the Hermes source with the profile as HERMES_HOME."""
    src = os.environ.get("HERMES_SRC")
    py = os.environ.get("HERMES_PYTHON") or sys.executable
    env = sb.env(HERMES_HOME=str(sb.profile_dir if profile_scoped else sb.hermes_home))
    return subprocess.run([py, "-c", code], cwd=src, env=env, capture_output=True, text=True, timeout=timeout)


def hermes_version() -> str | None:
    found = hermes_command()
    if not found:
        return None
    cmd, cwd = found
    try:
        out = subprocess.run(cmd + ["--version"], cwd=cwd, capture_output=True, text=True, timeout=120,
                             env={**os.environ, "HOME": tempfile.gettempdir(),
                                  "HERMES_HOME": tempfile.mkdtemp(prefix="hv-")}).stdout
    except Exception:
        return None
    return out.strip().splitlines()[0] if out.strip() else None


def no_network_wrapper() -> list[str] | None:
    """A command prefix that denies all network access to the child, or None."""
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return ["sandbox-exec", "-p", "(version 1)(allow default)(deny network*)"]
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        probe = subprocess.run(["unshare", "-rn", "true"], capture_output=True)
        if probe.returncode == 0:
            return ["unshare", "-rn"]
    return None


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): sha256_file(p)
            for p in sorted(root.rglob("*")) if p.is_file() and not p.is_symlink()}


def manifest() -> dict:
    import yaml
    return yaml.safe_load((REPO / "distribution.yaml").read_text(encoding="utf-8"))


def expected_payload() -> dict[str, str]:
    """Every file the distribution allowlist should install, with its sha256."""
    out: dict[str, str] = {}
    for rel in manifest()["distribution_owned"]:
        src = REPO / rel
        if src.is_file():
            out[rel] = sha256_file(src)
        elif src.is_dir():
            for p in sorted(src.rglob("*")):
                if p.is_file():
                    out[p.relative_to(REPO).as_posix()] = sha256_file(p)
    return out


def install_profile(sb: Sandbox, wrap: list[str] | None = None) -> subprocess.CompletedProcess:
    return run_hermes(sb, ["profile", "install", str(REPO), "--alias", "--yes"], wrap=wrap)
