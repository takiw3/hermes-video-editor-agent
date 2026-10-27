"""Launcher gate tests. No real HyperFrames toolchain and no render.

A stand-in CLI is placed where the pinned CLI would be installed. It records
how the launcher called it and can be told to fail, so the launcher's own
behavior is what gets tested: pinning, environment switches, the allowlist,
the workspace boundary, the style decision, failure reporting, and approvals.

    python3 -m unittest tests.test_gates -v
"""

from __future__ import annotations

import datetime as dt
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path

from tests import harness as H

# The pinned HyperFrames version, read from the shipped pin, so a re-pin needs no test edits.
PIN = json.loads((H.REPO / "skills/integrations/editor-hyperframes/toolchain/pin.json").read_text())["npm_version"]

FAKE_CLI = r"""
import fs from "node:fs";
const args = process.argv.slice(2);
const log = process.env.FAKE_HF_LOG;
if (log) {
  const env = {};
  for (const k of Object.keys(process.env)) {
    if (k.startsWith("HYPERFRAMES_") || k.startsWith("npm_config_") || ["DO_NOT_TRACK", "HOME", "TMPDIR"].includes(k)) env[k] = process.env[k];
  }
  env.SECRETS_VISIBLE = Object.keys(process.env).filter((k) => /API_KEY|TOKEN|SECRET/.test(k));
  env.PATH0 = (process.env.PATH || "").split(":")[0];
  fs.appendFileSync(log, JSON.stringify({ args, cwd: process.cwd(), env }) + "\n");
}
if (args[0] === "doctor") { console.log(JSON.stringify({ ok: true, checks: [], _meta: { version: process.env.FAKE_HF_VERSION || "__PIN__" } })); process.exit(0); }
if (args[0] === "usage") { console.log('{"status":"unknown","reason":"no_subscription_login"}'); process.exit(0); }
if (args[0] === "init") { const dir = args[1]; fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(dir + "/index.html", '<!doctype html><html><head><script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script></head><body><div id="root" data-composition-id="main"></div></body></html>');
  fs.writeFileSync(dir + "/hyperframes.json", "{}");
  fs.writeFileSync(dir + "/package.json", JSON.stringify({ name: dir, scripts: { render: "npx hyperframes render", publish: "npx hyperframes publish" } }));
  fs.writeFileSync(dir + "/AGENTS.md", "Run npx hyperframes skills update first.");
  process.exit(0); }
if (args[0] === "render") {
  const mode = process.env.FAKE_HF_RENDER || "ok";
  if (mode === "oom") { console.error("FATAL: out of memory"); process.exit(137); }
  if (mode === "error") { console.error("Error: composition failed"); process.exit(1); }
  if (mode === "nofile") process.exit(0);
  fs.copyFileSync(process.env.FAKE_HF_MEDIA, args[args.indexOf("--output") + 1]);
  process.exit(0);
}
process.exit(0);
""".replace("__PIN__", PIN)

_state: dict = {}


def setUpModule() -> None:
    if not H.have("node"):
        raise unittest.SkipTest("Node.js not available: launcher gate tests not run")
    _state["base"] = Path(tempfile.mkdtemp(prefix="ve-gates-")).resolve()
    if H.have("ffmpeg"):
        _state["media"] = H.make_timecode_clip(_state["base"] / "fixture.mp4", seconds=2)
        _state["silent"] = H.make_timecode_clip(_state["base"] / "fixture-silent.mp4", seconds=2, silent_seconds=(0, 1))


def tearDownModule() -> None:
    shutil.rmtree(_state.get("base", ""), ignore_errors=True)


def fresh_profile(name: str) -> Path:
    return H.install_profile(_state["base"] / name, use_hermes=False)


def fake_toolchain(profile: Path, version: str = PIN, lock_ok: bool = True) -> Path:
    """Put the stand-in CLI where `setup --install-cli` would install the real one."""
    pin = json.loads((profile / "skills/integrations/editor-hyperframes/toolchain/pin.json").read_text())
    tc = profile / "local" / "video-editor" / "video-engine" / f"toolchain-{pin['npm_version']}"
    pkg = tc / "node_modules" / "hyperframes"
    (pkg / "bin").mkdir(parents=True)
    (pkg / "package.json").write_text(json.dumps({"name": "hyperframes", "version": version}))
    (pkg / "bin" / "hyperframes.mjs").write_text(FAKE_CLI)
    gsap = tc / "node_modules" / "gsap"
    (gsap / "dist").mkdir(parents=True)
    (gsap / "package.json").write_text(json.dumps({"name": "gsap", "version": "3.14.2"}))
    (gsap / "dist" / "gsap.min.js").write_text("/*! GSAP stand-in for tests */ window.gsap = {};\n")
    lock = profile / "skills/integrations/editor-hyperframes/toolchain/package-lock.json"
    (tc / "package-lock.json").write_text(lock.read_text() if lock_ok else "{}")
    browser = profile / "local" / "video-editor" / "video-engine" / "fake-browser"
    browser.write_text("#!/bin/sh\nexit 0\n")
    browser.chmod(browser.stat().st_mode | stat.S_IXUSR)
    H.write_engine(profile, browser_path=str(browser))
    return tc


def ready(name: str) -> tuple[Path, Path, Path]:
    """A profile with the stand-in toolchain, a workspace, and one version folder."""
    profile = fresh_profile(name)
    ws = H.make_workspace(profile, _state["base"] / name / "ws")
    fake_toolchain(profile)
    video = ws / "projects" / "demo"
    video.mkdir(parents=True)
    proc = H.hf(profile, "init", "v1", cwd=video)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return profile, ws, video / "v1"


def err(proc) -> dict:
    """The launcher's JSON report, which follows anything the CLI itself printed."""
    return H.parse_json(proc.stderr)


def calls(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []


def render_env(log: Path, **extra) -> dict:
    return {"FAKE_HF_LOG": str(log), "FAKE_HF_MEDIA": str(_state.get("media", "")), **extra}


class NewProfile(unittest.TestCase):
    def test_a_new_profile_reports_not_configured_and_owner_supplied_research(self) -> None:
        profile = fresh_profile("new")
        proc = H.hf(profile, "status", "--json")
        self.assertEqual(proc.returncode, 3)
        report = json.loads(proc.stdout)
        self.assertEqual(report["video_engine"], "not configured")
        self.assertEqual(report["mode"], "offline")
        self.assertEqual(report["research"], "owner-supplied only")
        self.assertEqual(report["result_status"], "needs_setup")
        self.assertTrue({"cli", "browser", "workspace"} <= set(report["missing"]))
        self.assertEqual(report["pinned"]["npm_version"], PIN)
        self.assertFalse((profile / "local").exists(), "status must not create engine state")

    def test_every_command_but_status_needs_setup_first(self) -> None:
        profile = fresh_profile("needs-setup")
        for cmd in (["lint"], ["render", "--stage", "draft"], ["init", "v1"], ["footage-add", "x.mp4"], ["plan-workers"]):
            proc = H.hf(profile, *cmd)
            self.assertEqual(proc.returncode, 3, cmd)
            self.assertEqual(err(proc)["status"], "needs_setup")
            self.assertEqual(err(proc)["video_engine"], "not configured")

    def test_node_missing_node_too_old_and_ffmpeg_missing_are_named(self) -> None:
        profile = fresh_profile("toolchain-missing")
        bindir = _state["base"] / "toolchain-missing" / "bin"
        bindir.mkdir()
        python_dir = str(Path(shutil.which("python3")).parent)

        def status(path: str) -> dict:
            proc = H.run([shutil.which("python3"), profile / H.LAUNCHER_REL, "status", "--json"],
                         env={**H.profile_env(profile), "PATH": path})
            return {c["name"]: c for c in json.loads(proc.stdout)["checks"]}

        # an empty PATH: no node, no ffmpeg
        checks = status(str(bindir))
        self.assertFalse(checks["node"]["ok"])
        self.assertIn("Node.js not found", checks["node"]["detail"])
        self.assertIn("never installs it", checks["node"]["fix"])
        self.assertFalse(checks["ffmpeg"]["ok"] or checks["ffprobe"]["ok"])
        self.assertIn("Install FFmpeg yourself", checks["ffmpeg"]["fix"])
        # an old node
        old = bindir / "node"
        old.write_text("#!/bin/sh\necho v18.20.4\n")
        old.chmod(0o755)
        checks = status(str(bindir))
        self.assertFalse(checks["node"]["ok"])
        self.assertIn("v18.20.4 found, 22 or newer required", checks["node"]["detail"])
        self.assertIn("Nothing was changed", checks["node"]["fix"])
        self.assertFalse(python_dir == "")

    def test_setup_downloads_need_the_owner_at_a_terminal(self) -> None:
        profile = fresh_profile("setup")
        plan = H.hf(profile, "setup", "--plan")
        self.assertEqual(plan.returncode, 0)
        for word in ("source:", "size:", "license:"):
            self.assertGreaterEqual(plan.stdout.count(word), 3)
        self.assertIn(str(profile), plan.stdout)
        self.assertFalse((profile / "local").exists(), "--plan must change nothing")
        proc = H.hf(profile, "setup", "--install-cli")          # no TTY, no --yes
        self.assertEqual(proc.returncode, 4)
        self.assertEqual(err(proc)["status"], "approval required")
        self.assertIn("registry.npmjs.org", err(proc)["source"])
        self.assertFalse(any((profile / "local").rglob("node_modules")))

    def test_browser_and_model_downloads_stop_at_the_confirmation_prompt(self) -> None:
        profile, ws, project = ready("downloads")
        log = ws / "calls.jsonl"
        for args, needle in ((["--download-browser"], "Chrome for Testing"),
                             (["--install-model", "parakeet"], "Hugging Face")):
            proc = H.hf(profile, "setup", *args, env={"FAKE_HF_LOG": str(log)})       # no TTY, no --yes
            self.assertEqual(proc.returncode, 4, args)
            report = err(proc)
            self.assertEqual(report["status"], "approval required")
            self.assertIn(needle, report["source"])
            for field in ("item", "size", "license"):
                self.assertTrue(report[field], field)
        self.assertEqual(calls(log), [], "a download started without the owner's confirmation")
        other = H.hf(profile, "setup", "--install-model", "whisper-large")
        self.assertEqual(other.returncode, 2)
        engine = json.loads(H.engine_file(profile).read_text())
        self.assertNotIn("transcription_model", engine)

    def test_over_broad_workspaces_are_refused(self) -> None:
        profile = fresh_profile("broad")
        for folder in ("/", str(profile.parents[2]), str(profile), str(profile / "skills" / "x")):
            proc = H.hf(profile, "setup", "--workspace", folder)
            self.assertEqual(proc.returncode, 4, folder)


class Pinning(unittest.TestCase):
    def test_a_wrong_version_or_a_changed_lockfile_is_not_configured(self) -> None:
        profile = fresh_profile("wrong-version")
        H.make_workspace(profile, _state["base"] / "wrong-version" / "ws")
        fake_toolchain(profile, version="0.8.999")
        report = json.loads(H.hf(profile, "status", "--json").stdout)
        self.assertEqual(report["video_engine"], "not configured")
        cli = next(c for c in report["checks"] if c["name"] == "cli")
        self.assertIn(f"installed CLI is 0.8.999, pin is {PIN}", cli["detail"])

        profile = fresh_profile("wrong-lock")
        H.make_workspace(profile, _state["base"] / "wrong-lock" / "ws")
        fake_toolchain(profile, lock_ok=False)
        cli = next(c for c in json.loads(H.hf(profile, "status", "--json").stdout)["checks"] if c["name"] == "cli")
        self.assertIn("does not match the shipped lockfile", cli["detail"])

    def test_the_version_that_runs_is_checked_not_assumed(self) -> None:
        profile, ws, project = ready("deep")
        good = json.loads(H.hf(profile, "doctor", "--json", "--deep", cwd=project).stdout)
        self.assertEqual(good["upstream_doctor"]["version"], PIN)
        bad = H.hf(profile, "doctor", "--json", "--deep", cwd=project, env={"FAKE_HF_VERSION": "0.9.0"})
        report = json.loads(bad.stdout)
        self.assertEqual((report["video_engine"], report["result_status"]), ("not configured", "blocked"))

    def test_child_processes_get_the_switches_and_no_credentials(self) -> None:
        profile, ws, project = ready("env")
        log = ws / "calls.jsonl"
        proc = H.hf(profile, "lint", cwd=project, env={
            "FAKE_HF_LOG": str(log), "HEYGEN_API_KEY": "synthetic-not-a-key", "GEMINI_API_KEY": "synthetic-not-a-key",
            "ELEVENLABS_API_KEY": "synthetic-not-a-key", "HYPERFRAMES_API_KEY": "synthetic-not-a-key",
            "OPENAI_API_KEY": "synthetic-not-a-key", "GH_TOKEN": "synthetic-not-a-token"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        env = calls(log)[-1]["env"]
        for switch in ("HYPERFRAMES_SKIP_SKILLS", "HYPERFRAMES_NO_UPDATE_CHECK", "HYPERFRAMES_NO_AUTO_INSTALL",
                       "HYPERFRAMES_NO_TELEMETRY", "DO_NOT_TRACK"):
            self.assertEqual(env.get(switch), "1", switch)
        self.assertEqual(env["HYPERFRAMES_PREVIEW_HOST"], "127.0.0.1")
        self.assertEqual(env["npm_config_offline"], "true")
        self.assertEqual(env["SECRETS_VISIBLE"], [], "a provider key reached the CLI")
        self.assertNotIn("HYPERFRAMES_API_KEY", env)
        self.assertTrue(env["HOME"].startswith(str(profile / "local")), "the CLI saw the real HOME")
        self.assertTrue(env["PATH0"].endswith("shims"))
        self.assertTrue(env["TMPDIR"].startswith(str(ws)))

    def test_package_runners_reached_from_a_child_process_cannot_fetch_another_version(self) -> None:
        profile, ws, project = ready("shims")
        H.hf(profile, "lint", cwd=project)          # creates the shims
        shims = profile / "local" / "video-editor" / "video-engine" / "shims"
        env = H.profile_env(profile, {"EDITOR_HF_LAUNCHER": "1"})
        log = ws / "calls.jsonl"

        def shim(name: str, *args):
            return H.run([shims / name, *args], cwd=project, env={**env, "FAKE_HF_LOG": str(log)})

        latest = shim("npx", "--yes", "hyperframes@latest", "lint")
        self.assertEqual(latest.returncode, 4)
        self.assertIn(f"only hyperframes@{PIN} runs", latest.stderr)
        pinned = shim("npx", f"hyperframes@{PIN}", "lint")
        self.assertEqual(pinned.returncode, 0, pinned.stderr)
        self.assertEqual(calls(log)[-1]["args"], ["lint"])
        bare = shim("npx", "hyperframes", "skills", "update", "general-video")
        self.assertEqual(bare.returncode, 4)
        self.assertIn("release-managed", bare.stderr)
        for name, args in (("npm", ["install", "hyperframes"]), ("pip", ["install", "x"]), ("brew", ["install", "ffmpeg"]),
                           ("heygen", ["auth", "login"]), ("npx", ["skills", "add", "heygen-com/hyperframes"])):
            proc = shim(name, *args)
            self.assertEqual(proc.returncode, 4, (name, args))
        self.assertEqual(len(calls(log)), 1, "a refused shim call still reached the CLI")


class Allowlist(unittest.TestCase):
    def test_external_update_and_provider_subcommands_are_refused(self) -> None:
        profile, ws, project = ready("allowlist")
        log = ws / "calls.jsonl"
        refused = ["skills", "upgrade", "publish", "cloud", "lambda", "cloudrun", "auth", "feedback", "events",
                   "telemetry", "open", "catch-up", "figma", "capture", "media-use", "tts", "remove-background",
                   "models", "browser", "play", "present", "preview", "benchmark", "not-a-command"]
        for sub in refused:
            proc = H.hf(profile, sub, "render", cwd=project, env={"FAKE_HF_LOG": str(log)})
            self.assertEqual(proc.returncode, 4, sub)
            self.assertEqual(err(proc)["status"], "blocked", sub)
        self.assertEqual(calls(log), [], "a refused subcommand reached the CLI")

    def test_a_registry_fetch_is_an_owner_step_and_a_workflow_is_never_downloaded(self) -> None:
        profile, ws, project = ready("registry")
        log = ws / "calls.jsonl"
        proc = H.hf(profile, "add", "lower-third", cwd=project, env={"FAKE_HF_LOG": str(log)})
        self.assertEqual(proc.returncode, 4)
        self.assertEqual(err(proc)["status"], "approval required")
        self.assertIn("upstream main branch", err(proc)["message"])
        self.assertIn("setup --add-registry-item", err(proc)["fix"])
        owner = H.hf(profile, "setup", "--add-registry-item", "lower-third", "--project", project,
                     env={"FAKE_HF_LOG": str(log)})        # no TTY: cannot be approved
        self.assertEqual(owner.returncode, 4)
        self.assertEqual(err(owner)["status"], "approval required")
        self.assertIn("NOT the pinned release", err(owner)["source"])
        self.assertEqual(calls(log), [])
        self.assertFalse((project / "registry-items.lock.json").exists())

    def test_transcription_and_background_removal_report_unavailable_without_their_models(self) -> None:
        profile, ws, project = ready("models")
        proc = H.hf(profile, "transcribe", "assets/a.mp4", cwd=project)
        self.assertEqual(proc.returncode, 3)
        self.assertEqual(err(proc)["status"], "needs_setup")
        self.assertIn("no speech model is installed", err(proc)["message"])
        self.assertIn("owner-provided captions", err(proc)["fix"])
        proc = H.hf(profile, "remove-background", "assets/a.mp4", cwd=project)
        self.assertEqual(proc.returncode, 4)
        self.assertIn("background removal is unavailable", err(proc)["message"])

    def test_snapshot_never_sends_frames_to_a_vision_provider(self) -> None:
        profile, ws, project = ready("snapshot")
        log = ws / "calls.jsonl"
        refused = H.hf(profile, "snapshot", "--describe", "what is on screen", cwd=project)
        self.assertEqual(refused.returncode, 4)
        ok = H.hf(profile, "snapshot", "--at", "1", cwd=project, env={"FAKE_HF_LOG": str(log), "GEMINI_API_KEY": "synthetic"})
        self.assertEqual(ok.returncode, 0)
        self.assertEqual(calls(log)[-1]["args"], ["snapshot", "--at", "1", "--describe", "false"])
        self.assertEqual(calls(log)[-1]["env"]["SECRETS_VISIBLE"], [])


class WorkspaceBoundary(unittest.TestCase):
    def test_init_strips_the_routes_around_the_launcher(self) -> None:
        profile, ws, project = ready("init")
        pkg = json.loads((project / "package.json").read_text())
        self.assertEqual(pkg["scripts"], {})
        self.assertEqual(sorted(pkg["hermesVideoEditor"]["removed_scripts"]), ["publish", "render"])
        self.assertNotIn("npx", (project / "AGENTS.md").read_text())
        self.assertIn("editor-hyperframes", (project / "AGENTS.md").read_text())
        html = (project / "index.html").read_text()
        self.assertNotIn("cdn.jsdelivr.net", html)
        self.assertIn("assets/vendor/gsap.min.js", html)
        self.assertIn("GSAP Standard License", (project / "asset-rights-register.yaml").read_text())
        for folder in ("renders", "receipts", "assets"):
            self.assertTrue((project / folder).is_dir())

    def test_writes_and_working_directories_outside_the_workspace_are_refused(self) -> None:
        profile, ws, project = ready("boundary")
        outside = _state["base"] / "boundary" / "elsewhere"
        outside.mkdir()
        log = ws / "calls.jsonl"
        env = render_env(log)
        cases = [
            (["render", "--stage", "draft", "--comparison", "hybrid", "--output", str(outside / "x.mp4")], project),
            (["render", "--stage", "draft", "--comparison", "hybrid", "--output", "../../../../x.mp4"], project),
            (["snapshot", "--output", str(outside)], project),
            (["lint", str(outside)], project),
            (["lint"], outside),
            (["init", "v9"], ws / "footage"),
        ]
        for args, cwd in cases:
            proc = H.hf(profile, *args, cwd=cwd, env=env)
            self.assertEqual(proc.returncode, 4, args)
            self.assertEqual(err(proc)["status"], "blocked")
        self.assertEqual(calls(log), [])
        self.assertEqual(list(outside.iterdir()), [])
        home_proc = H.hf(profile, "lint", "~/Desktop", cwd=project, env=env)
        self.assertEqual(home_proc.returncode, 4)


@unittest.skipUnless(H.have("ffmpeg"), "FFmpeg not available: render gate tests not run")
class RenderGates(unittest.TestCase):
    def setUp(self) -> None:
        self.profile, self.ws, self.project = ready(f"render-{self._testMethodName[:40]}")
        self.log = self.ws / "calls.jsonl"

    def render(self, *args, **env):
        return H.hf(self.profile, "render", *args, cwd=self.project, env=render_env(self.log, **env))

    def renders_started(self) -> int:
        return sum(1 for c in calls(self.log) if c["args"][0] == "render")

    def decide(self, **over) -> Path:
        path = H.record_style_decision(self.project)
        if over:
            text = path.read_text()
            for key, value in over.items():
                lines = [f"{key}: {value}" if line.startswith(f"{key}:") else line for line in text.splitlines()]
                text = "\n".join(lines) + "\n"
            path.write_text(text)
        return path

    def test_a_draft_needs_a_decision_or_a_comparison_tag(self) -> None:
        proc = self.render("--stage", "draft")
        self.assertEqual(proc.returncode, 5)
        self.assertEqual(err(proc)["status"], "approval required")
        self.assertEqual(err(proc)["style_decision"], "missing")
        self.assertEqual(self.renders_started(), 0)
        self.assertEqual(self.render("--stage", "draft", "--comparison", "viral").returncode, 5)
        tagged = self.render("--stage", "draft", "--comparison", "outlier_matched")
        self.assertEqual(tagged.returncode, 0, tagged.stderr)
        result = H.parse_json(tagged.stdout)
        self.assertEqual((result["status"], result["style_decision"]), ("draft rendered", "pending"))
        receipt = Path(result["receipts"][0]).read_text()
        self.assertIn('comparison_option: "outlier_matched"', receipt)
        self.assertIn("inspected: false", receipt)
        self.assertIn('edit_state: "rough_cut_rendered"', receipt)

    def test_the_stage_is_required_and_draft_quality_is_never_final(self) -> None:
        self.assertEqual(self.render().returncode, 2)
        self.assertEqual(self.render("--stage", "final", "--quality", "draft").returncode, 4)
        self.assertEqual(self.render("--stage", "draft", "--quality", "high", "--comparison", "hybrid").returncode, 4)
        for flag in ("--docker", "--gpu"):
            self.assertEqual(self.render("--stage", "draft", "--comparison", "hybrid", flag).returncode, 4)
        self.assertEqual(self.renders_started(), 0)

    def test_a_final_render_is_refused_without_a_style_decision(self) -> None:
        H.register_assets(self.project, [])
        self.assertEqual(self.render("--stage", "draft", "--comparison", "hybrid").returncode, 0)
        proc = self.render("--stage", "final")
        self.assertEqual(proc.returncode, 5)
        self.assertEqual(err(proc)["status"], "approval required")
        self.assertIn("no style-decision.yaml", err(proc)["problems"][0])
        self.assertEqual(self.renders_started(), 1)
        self.decide()
        ok = self.render("--stage", "final")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        result = H.parse_json(ok.stdout)
        self.assertEqual((result["status"], result["style_decision"]), ("final rendered with file path", "hybrid"))
        self.assertTrue(Path(result["outputs"][0]).is_file())
        check = H.hf(self.profile, "style-check", cwd=self.project)
        self.assertEqual(json.loads(check.stdout)["status"], "style decision recorded")

    def test_silence_an_invalid_option_or_an_unnamed_approver_is_not_a_decision(self) -> None:
        self.assertEqual(self.render("--stage", "draft", "--comparison", "hybrid").returncode, 0)
        for over, needle in (({"decision": ""}, "Silence is not a choice"), ({"decision": "whatever_performs"}, "must be one of"),
                             ({"decided_by": ""}, "decided_by is empty"), ({"decided_at": ""}, "decided_at is empty"),
                             ({"blueprint_id": ""}, "blueprint_id is empty"), ({"study_id": "unknown"}, "study_id is empty")):
            self.decide(**over)
            proc = self.render("--stage", "final")
            self.assertEqual(proc.returncode, 5, over)
            self.assertTrue(any(needle in p for p in err(proc)["problems"]), (over, err(proc)["problems"]))
        self.assertEqual(self.renders_started(), 1)

    def test_a_waiver_covers_one_edit_and_needs_a_reason(self) -> None:
        self.assertEqual(self.render("--stage", "draft", "--comparison", "hybrid").returncode, 0)
        self.decide(decision="waived", study_id="", blueprint_id="", blueprint_valid_until="")
        self.assertTrue(any("waiver_reason is empty" in p for p in err(self.render("--stage", "final"))["problems"]))
        self.decide(decision="waived", waiver_reason="owner needs this cut today", waiver_scope="all_edits")
        self.assertTrue(any("never every edit" in p for p in err(self.render("--stage", "final"))["problems"]))
        self.decide(decision="waived", waiver_reason="owner needs this cut today", waiver_scope="this_edit")
        ok = self.render("--stage", "final")
        self.assertEqual(ok.returncode, 0, ok.stderr)
        self.assertEqual(H.parse_json(ok.stdout)["style_decision"], "waived")

    def test_a_stale_blueprint_is_flagged_until_the_approver_accepts_it(self) -> None:
        first = self.render("--stage", "draft", "--comparison", "hybrid")
        self.assertEqual(first.returncode, 0, first.stderr[-600:])
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        self.decide(blueprint_valid_until=yesterday)
        proc = self.render("--stage", "final")
        self.assertEqual(proc.returncode, 5)
        self.assertTrue(any("went stale" in p for p in err(proc)["problems"]))
        self.decide(blueprint_valid_until=yesterday, stale_blueprint_accepted_by="owner (synthetic)")
        accepted = self.render("--stage", "final")
        self.assertEqual(accepted.returncode, 0, accepted.stderr[-600:])

    def test_a_final_needs_a_draft_receipt_first(self) -> None:
        self.decide()
        proc = self.render("--stage", "final")
        self.assertEqual(proc.returncode, 5)
        self.assertIn("no draft render receipt", err(proc)["message"])
        self.assertEqual(self.renders_started(), 0)

    def test_an_asset_with_no_license_record_blocks_the_final(self) -> None:
        self.decide()
        self.assertEqual(self.render("--stage", "draft").returncode, 0)
        shutil.copy2(_state["media"], self.project / "assets" / "song.mp3")
        (self.project / "assets" / "brand.woff2").write_bytes(b"synthetic font bytes")
        proc = self.render("--stage", "final")
        self.assertEqual(proc.returncode, 5)
        self.assertEqual(sorted(err(proc)["unrecorded"]), ["assets/brand.woff2", "assets/song.mp3"])
        register = self.project / "asset-rights-register.yaml"
        register.write_text(register.read_text() + "  - asset: assets/song.mp3\n    source: unknown\n    license: tbd\n    proof:\n"
                            "  - asset: assets/brand.woff2\n    source: owner brand kit\n    license: OFL-1.1\n    proof: licenses/OFL.txt\n")
        proc = self.render("--stage", "final")
        self.assertEqual(err(proc)["incomplete"], [{"asset": "assets/song.mp3", "missing": ["source", "license", "proof"]}])
        self.assertEqual(self.renders_started(), 1)

    def test_changed_or_missing_source_footage_blocks_the_final(self) -> None:
        self.decide()
        original = self.ws / "footage" / "take.mp4"
        shutil.copy2(_state["media"], original)
        self.assertEqual(H.hf(self.profile, "footage-add", original, cwd=self.ws).returncode, 0)
        self.assertEqual(self.render("--stage", "draft").returncode, 0)
        with original.open("ab") as fh:
            fh.write(b"\0")
        proc = self.render("--stage", "final")
        self.assertEqual(proc.returncode, 5)
        self.assertEqual(err(proc)["changed"], ["footage/take.mp4"])
        again = H.hf(self.profile, "footage-add", original, cwd=self.ws)
        self.assertEqual(again.returncode, 5)
        self.assertIn("An original changed", again.stderr)
        self.assertEqual(self.renders_started(), 1)

    def test_an_unapproved_external_host_needs_the_owner(self) -> None:
        html = self.project / "index.html"
        html.write_text(html.read_text().replace("</head>", '<link href="https://fonts.googleapis.com/css2?family=Inter" rel="stylesheet"></head>'))
        proc = self.render("--stage", "draft", "--comparison", "hybrid")
        self.assertEqual(proc.returncode, 5)
        self.assertEqual(err(proc)["status"], "approval required")
        self.assertEqual(list(err(proc)["unapproved"]), ["fonts.googleapis.com"])
        self.assertEqual(self.renders_started(), 0)
        H.hf(self.profile, "setup", "--allow-host", "fonts.googleapis.com")
        self.assertEqual(self.render("--stage", "draft", "--comparison", "hybrid").returncode, 0)

    def test_a_render_that_fails_on_memory_is_reported_once_and_never_retried(self) -> None:
        proc = self.render("--stage", "draft", "--comparison", "hybrid", FAKE_HF_RENDER="oom")
        self.assertEqual(proc.returncode, 137)
        report = err(proc)
        self.assertEqual(report["status"], "render failed")
        self.assertTrue(report["memory_pressure_likely"])
        self.assertFalse(report["output_exists"])
        self.assertIn("Do not retry blindly", report["message"])
        self.assertIn("lower --workers", report["fix"])
        self.assertIsInstance(report["workers"], int)
        self.assertEqual(self.renders_started(), 1, "the launcher retried a failed render")
        self.assertEqual(list((self.project / "receipts").iterdir()), [])
        self.assertEqual(list((self.project / "renders").iterdir()), [])

    def test_a_failed_render_and_a_zero_exit_with_no_file_are_both_render_failed(self) -> None:
        proc = self.render("--stage", "draft", "--comparison", "hybrid", FAKE_HF_RENDER="error")
        self.assertEqual((proc.returncode, err(proc)["status"], err(proc)["memory_pressure_likely"]), (1, "render failed", False))
        proc = self.render("--stage", "draft", "--comparison", "hybrid", FAKE_HF_RENDER="nofile")
        self.assertEqual(proc.returncode, 5)
        self.assertEqual(err(proc)["status"], "render failed")
        self.assertEqual(err(proc)["exit_code"], 0)
        self.assertEqual(list((self.project / "receipts").iterdir()), [])

    def test_a_zero_exit_with_a_silent_track_is_recorded_as_silent(self) -> None:
        proc = self.render("--stage", "draft", "--comparison", "hybrid", FAKE_HF_MEDIA=str(_state["silent"]))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        receipt = Path(H.parse_json(proc.stdout)["receipts"][0]).read_text()
        self.assertIn("audio_silent: true", receipt)
        self.assertIn("inspected: false", receipt)

    def test_workers_come_from_measured_memory_unless_the_caller_sets_them(self) -> None:
        plan = json.loads(H.hf(self.profile, "plan-workers", cwd=self.project).stdout)
        self.assertGreaterEqual(plan["workers"], 1)
        self.assertLessEqual(plan["workers"], max(1, (os.cpu_count() or 2) - 1))
        self.assertIn("MB available", plan["reason"])
        self.assertIn("no measured render on record", plan["per_worker_basis"])
        # a small-canvas measurement is not used to size a larger canvas
        measurements = self.ws / ".video-editor" / "render-measurements.json"
        measurements.parent.mkdir(exist_ok=True)
        measurements.write_text(json.dumps([{"width": 640, "height": 360, "workers": 2, "peak_tree_rss_mb": 300, "stage": "draft"}]))
        html = self.project / "index.html"
        html.write_text(html.read_text().replace('data-composition-id="main"', 'data-composition-id="main" data-width="1920" data-height="1080"'))
        large = json.loads(H.hf(self.profile, "plan-workers", cwd=self.project).stdout)
        self.assertEqual((large["per_worker_mb"], large["canvas_pixels"]), (512, 1920 * 1080))
        measurements.write_text(json.dumps([{"width": 1920, "height": 1080, "workers": 2, "peak_tree_rss_mb": 1400, "stage": "draft"}]))
        measured = json.loads(H.hf(self.profile, "plan-workers", cwd=self.project).stdout)
        self.assertEqual(measured["per_worker_mb"], 700)
        self.assertIn("largest measured peak per worker", measured["per_worker_basis"])
        measurements.unlink()
        first = self.render("--stage", "draft", "--comparison", "hybrid")
        self.assertEqual(first.returncode, 0, first.stderr[-600:])
        args = calls(self.log)[-1]["args"]
        self.assertEqual(args[args.index("--workers") + 1], str(args[args.index("--workers") + 1]))
        self.assertIn("--workers", args)
        self.assertEqual(args[args.index("--quality") + 1], "draft")
        receipt = next((self.project / "receipts").glob("*.yaml")).read_text()
        self.assertIn("planned from measured memory", receipt)
        again = self.render("--stage", "draft", "--comparison", "house_style", "--workers", "1")
        self.assertEqual(again.returncode, 0, again.stderr[-600:])
        self.assertEqual(calls(self.log)[-1]["args"].count("--workers"), 1)
        newest = sorted((self.project / "receipts").glob("*.yaml"), key=lambda p: p.stat().st_mtime)[-1].read_text()
        self.assertIn("set by the caller", newest)

    def test_handoff_copies_only_receipt_backed_renders(self) -> None:
        proc = self.render("--stage", "draft", "--comparison", "hybrid")
        out = Path(H.parse_json(proc.stdout)["outputs"][0])
        none = json.loads(H.hf(self.profile, "handoff", out, cwd=self.project).stdout)
        self.assertEqual(none["status"], "handoff route unavailable")
        self.assertEqual((none["file"], none["sha256"]), (str(out), H.sha256(out)))
        folder = _state["base"] / "handoff" / self._testMethodName
        self.assertEqual(H.hf(self.profile, "setup", "--handoff", folder).returncode, 0)
        done = json.loads(H.hf(self.profile, "handoff", out, cwd=self.project).stdout)
        self.assertEqual(done["status"], "handed off")
        self.assertEqual(H.sha256(Path(done["handoff_file"])), H.sha256(out))
        self.assertIn("not an approved file", Path(done["handoff_record"]).read_text())
        footage = self.ws / "footage" / "raw.mp4"
        shutil.copy2(_state["media"], footage)
        refused = H.hf(self.profile, "handoff", footage, cwd=self.project)
        self.assertEqual(refused.returncode, 4)
        self.assertIn("never leave the workspace", refused.stderr)
        loose = self.project / "renders" / "no-receipt.mp4"
        shutil.copy2(_state["silent"], loose)
        self.assertEqual(H.hf(self.profile, "handoff", loose, cwd=self.project).returncode, 5)

    def test_a_raw_call_to_the_cli_goes_around_the_launcher_which_is_why_deny_rules_exist(self) -> None:
        """Observed and documented, not prevented here: the launcher cannot stop
        a process that never calls it. The profile's config.yaml deny rules
        block this command form at the Hermes approval floor; tests/test_install.py
        checks those rules against the tested Hermes release."""
        pin_dir = next((self.profile / "local/video-editor/video-engine").glob("toolchain-*"))
        raw = H.run(["node", pin_dir / "node_modules/hyperframes/bin/hyperframes.mjs", "render", "--output",
                     self.project / "renders" / "bypass.mp4"], cwd=self.project,
                    env={**os.environ, "FAKE_HF_MEDIA": str(_state["media"])})
        self.assertEqual(raw.returncode, 0)
        self.assertTrue((self.project / "renders" / "bypass.mp4").is_file(), "the bypass produced a file")
        self.assertEqual(list((self.project / "receipts").iterdir()), [], "a bypass render has no receipt")
        refused = H.hf(self.profile, "handoff", self.project / "renders" / "bypass.mp4", cwd=self.project)
        self.assertEqual(refused.returncode, 5, "a render with no receipt cannot be handed off")


if __name__ == "__main__":
    unittest.main(verbosity=2)
