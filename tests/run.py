#!/usr/bin/env python3
"""Run a unittest module and record every test as pass, fail, or not run.

    python3 tests/run.py tests.test_tools --json docs/test-results/tools.json
    python3 tests/run.py tests.test_gates --json docs/test-results/gates.json
    VE_TEST_TOOLCHAIN=1 VE_TEST_BROWSER=... VE_TEST_USE_HERMES=1 \\
        python3 tests/run.py tests.test_renders --json docs/test-results/renders.json

A skipped test is recorded as `not run` with its reason. It is never counted
as passed. Measurements a suite collects (render seconds, peak memory) are
written beside the results, with the machine they were taken on.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def describe(test: unittest.TestCase) -> str:
    cls = type(test).__name__
    name = getattr(test, "_testMethodName", str(test))
    return f"{cls}: {name.removeprefix('test_').replace('_', ' ')}"


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows: list[dict] = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append({"name": describe(test), "status": "pass", "detail": ""})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.rows.append({"name": describe(test), "status": "fail", "detail": str(err[1])[:400]})

    def addError(self, test, err):
        super().addError(test, err)
        self.rows.append({"name": describe(test), "status": "fail", "detail": f"{err[0].__name__}: {err[1]}"[:400]})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.rows.append({"name": describe(test), "status": "not run", "detail": reason})


def out(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:
        return "Unavailable"


def machine() -> dict:
    info = {"os": f"{platform.system()} {platform.release()}", "machine": platform.machine(),
            "cpu_count": os.cpu_count(), "python": platform.python_version(),
            "node": out(["node", "--version"]) if shutil.which("node") else "not installed",
            "ffmpeg": (out(["ffmpeg", "-version"]).splitlines() or ["not installed"])[0].split(" Copyright")[0]
            if shutil.which("ffmpeg") else "not installed"}
    if sys.platform == "darwin":
        info["os"] = f"macOS {out(['sw_vers', '-productVersion'])}"
        info["cpu"] = out(["sysctl", "-n", "machdep.cpu.brand_string"])
        mem = out(["sysctl", "-n", "hw.memsize"])
        info["memory_gb"] = round(int(mem) / (1 << 30)) if mem.isdigit() else "Unavailable"
    return info


def main() -> int:
    args = sys.argv[1:]
    json_out = args[args.index("--json") + 1] if "--json" in args else None
    modules = [a for a in args if a.startswith("tests.")]
    if not modules:
        print(__doc__)
        return 2
    rows: list[dict] = []
    measurements: dict = {}
    failed = False
    for name in modules:
        module = importlib.import_module(name)
        suite = unittest.defaultTestLoader.loadTestsFromModule(module)
        try:
            result = unittest.TextTestRunner(resultclass=Recorder, verbosity=2).run(suite)
        except unittest.SkipTest as exc:  # raised from setUpModule on old interpreters
            rows.append({"name": f"{name} (whole suite)", "status": "not run", "detail": str(exc)})
            continue
        rows.extend(result.rows)
        for test, reason in result.skipped:
            if not any(r["name"] == describe(test) for r in rows):
                rows.append({"name": f"{name} (whole suite)" if "setUpModule" in str(test) else describe(test),
                             "status": "not run", "detail": reason})
        failed = failed or not result.wasSuccessful()
        measurements.update(getattr(module, "RESULTS", {}))
    counts = {s: sum(1 for r in rows if r["status"] == s) for s in ("pass", "fail", "not run")}
    print(f"\n{', '.join(modules)}: {counts['pass']} pass, {counts['fail']} fail, {counts['not run']} not run")
    if json_out:
        payload = {"suite": ", ".join(modules), "counts": counts, "machine": machine(), "tests": rows}
        if measurements:
            payload["measurements"] = measurements
        if os.environ.get("VE_TEST_HERMES_LABEL"):
            payload["hermes"] = os.environ["VE_TEST_HERMES_LABEL"]
        Path(json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(json_out).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 1 if failed or counts["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
