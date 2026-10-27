#!/usr/bin/env python3
"""Run the effect verification gate from an installed temporary profile.

    python3 scripts/verify_effects.py [effect_id ...] [--family F] [--jobs N] [--only-unverified]

1. Installs this repository into a throwaway HOME with `hermes profile install`
   (VE_TEST_HERMES or `hermes` on PATH). Without Hermes it refuses: the gate
   is defined as running inside an installed profile.
2. Runs the owner-only toolchain setup there: approve a workspace, `npm ci`
   from the shipped lockfile, record an existing headless Chrome
   (VE_TEST_BROWSER). Nothing is downloaded except npm packages pinned by
   integrity hash.
3. Calls the installed `fx.py verify <id>` for each effect, N at a time. Every
   render inside it runs with outbound network denied by the OS.
4. Copies each effect's verification.json, reference.jpg and contact-sheet.jpg
   back into skills/video-effects-core/effects-library/, and writes
   docs/test-results/effects.json.

Renders use FFmpeg from PATH; put a working FFmpeg first on PATH.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIB_REL = Path("skills/video-effects-core/effects-library")
LIB = REPO / LIB_REL
FINGERPRINTS = REPO / "tests/fixtures/concat-fingerprints.json"
RESULTS = REPO / "docs/test-results/effects.json"
COPY_BACK = ("verification.json", "reference.jpg", "contact-sheet.jpg")


def effect_ids() -> dict[str, Path]:
    found = {}
    for p in sorted(LIB.glob("*/*/effect.json")):
        spec = json.loads(p.read_text(encoding="utf-8"))
        found[spec["effect_id"]] = p.parent.relative_to(LIB)
    return found


def run(cmd, env, timeout=3600):
    return subprocess.run([str(c) for c in cmd], env=env, capture_output=True, text=True, timeout=timeout)


def hermes_version(binary: str) -> str:
    out = run([binary, "--version"], os.environ.copy(), 60).stdout.strip().splitlines()
    return out[0] if out else "unknown"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ids", nargs="*")
    ap.add_argument("--family")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--only-unverified", action="store_true")
    ap.add_argument("--keep-home", help="reuse or keep this temporary HOME (for reruns)")
    args = ap.parse_args()

    binary = os.environ.get("VE_TEST_HERMES") or shutil.which("hermes")
    browser = os.environ.get("VE_TEST_BROWSER")
    if not binary:
        print("refusing: no hermes binary; the gate runs inside an installed profile")
        return 4
    if not browser or not Path(browser).is_file():
        print("refusing: set VE_TEST_BROWSER to an existing chrome-headless-shell")
        return 4

    all_ids = effect_ids()
    ids = args.ids or [i for i, rel in all_ids.items() if not args.family or rel.parts[0] == args.family]
    if args.only_unverified:
        def passed(i):
            rec = LIB / all_ids[i] / "verification.json"
            return rec.is_file() and json.loads(rec.read_text()).get("result") == "pass"
        ids = [i for i in ids if not passed(i)]
    unknown = [i for i in ids if i not in all_ids]
    if unknown:
        print(f"unknown effects: {unknown}")
        return 2

    home = Path(args.keep_home or tempfile.mkdtemp(prefix="ve-fx-home-"))
    hermes_home = home / ".hermes"
    profile = hermes_home / "profiles" / "video-editor"
    env = {**os.environ, "HOME": str(home), "HERMES_HOME": str(hermes_home), "FX_FINGERPRINTS": str(FINGERPRINTS),
           "FX_VERIFY_TEMP": "1"}
    if profile.is_dir():
        proc = run([binary, "profile", "update", "video-editor", "--yes"], env)
        if proc.returncode != 0:
            shutil.rmtree(profile)
    if not profile.is_dir():
        proc = run([binary, "profile", "install", str(REPO), "--alias", "--yes"], env)
        if proc.returncode != 0 or not profile.is_dir():
            print(f"hermes profile install failed:\n{proc.stdout[-2000:]}\n{proc.stderr[-2000:]}")
            return 5
    penv = {**env, "HERMES_HOME": str(profile)}
    hf = [sys.executable, profile / "skills/integrations/editor-hyperframes/scripts/hf.py"]
    if not (profile / "local/video-editor/video-engine/engine.json").is_file():
        for step in (["setup", "--workspace", home / "video-work"], ["setup", "--install-cli", "--yes"], ["setup", "--use-browser", browser]):
            proc = run(hf + step, penv)
            if proc.returncode != 0:
                print(f"setup {step[1]} failed:\n{proc.stdout[-1500:]}\n{proc.stderr[-1500:]}")
                return 5
    fx = profile / LIB_REL / "scripts/fx.py"

    def one(eid: str) -> dict:
        t0 = time.time()
        proc = run([sys.executable, fx, "verify", eid], penv, 3600)
        try:
            res = json.loads(proc.stdout[proc.stdout.find("{"):])
        except ValueError:
            res = {"effect_id": eid, "result": "crash", "errors": [(proc.stdout + proc.stderr)[-2000:]]}
        src = profile / LIB_REL / all_ids[eid]
        dest = LIB / all_ids[eid]
        for name in COPY_BACK:
            if (src / name).is_file():
                shutil.copy2(src / name, dest / name)
        res["seconds"] = round(time.time() - t0, 1)
        fails = [k for k, v in res.get("checks", {}).items() if v == "fail"]
        print(f"{eid:30s} {res.get('result'):6s} {res['seconds']:6.0f}s fails={fails} {(res.get('errors') or [''])[0][-200:]}", flush=True)
        return res

    with ThreadPoolExecutor(max(1, args.jobs)) as pool:
        results = list(pool.map(one, ids))

    summary = {}
    for eid, rel in all_ids.items():
        rec = LIB / rel / "verification.json"
        if rec.is_file():
            data = json.loads(rec.read_text(encoding="utf-8"))
            summary[eid] = {"family": rel.parts[0], "result": data.get("result"), "limited": bool(data.get("limited")),
                            "verified_at": data.get("verified_at"), "photosensitivity": (data.get("photosensitivity") or {}).get("result"),
                            "render_cost_multiplier": data.get("render_cost_multiplier")}
    payload = {
        "recorded_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hermes": hermes_version(binary),
        "machine": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "jobs": args.jobs,
        "this_run": {r["effect_id"]: r.get("result") for r in results},
        "effects": summary,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if not args.keep_home:
        shutil.rmtree(home, ignore_errors=True)
    bad = [r["effect_id"] for r in results if r.get("result") != "pass"]
    print(f"\n{len(results) - len(bad)}/{len(results)} passed this run" + (f"; failed: {bad}" if bad else ""))
    return 0 if not bad else 5


if __name__ == "__main__":
    sys.exit(main())
