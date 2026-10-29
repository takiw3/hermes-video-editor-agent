"""Effects library tests: catalog integrity, apply and remove, stacking and plan
checks, the WCAG flash check against known inputs, and the copy check.

No Hermes and no HyperFrames toolchain needed. The flash tests need FFmpeg and
are recorded `not run` without it. The renders of every effect are the
verification gate (scripts/verify_effects.py), not this suite.

    python3 -m unittest tests.test_effects -v
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests import harness as H

REPO = H.REPO
LIB = REPO / "skills/video-effects-core/effects-library"
FX_REL = "skills/video-effects-core/effects-library/scripts/fx.py"
REQUIRED = ["effect_id", "display_name", "family", "kind", "description", "implementation_route", "hyperframes_feature",
            "parameters", "applies_to", "needs_model", "needs_key_footage", "hdr_behavior", "deterministic", "seek_safe",
            "photosensitivity", "face_safe", "render_cost_multiplier", "provenance", "reference_id", "license", "status"]
ROUTES = {"hf-media-treatment", "hf-color-grade", "hf-shader-transition", "hf-vfx-chain", "hf-registry", "css-filter",
          "svg-filter", "gsap-composite", "original-webgl", "hf-audio-fx"}
FAMILIES = {"looks-and-grades", "image-effects", "transitions", "camera-and-motion", "keying-and-subject",
            "overlays-and-generators", "text-and-title", "creator-composites", "audio"}

_state: dict = {}


def setUpModule() -> None:
    base = Path(tempfile.mkdtemp(prefix="ve-effects-")).resolve()
    profile = H.install_profile(base, use_hermes=False)
    ws = H.make_workspace(profile, base / "ws")
    _state.update(base=base, profile=profile, ws=ws)


def tearDownModule() -> None:
    shutil.rmtree(_state["base"], ignore_errors=True)


def fx(*args, cwd=None):
    return H.run([sys.executable, _state["profile"] / FX_REL, *args], cwd=cwd or _state["ws"],
                 env=H.profile_env(_state["profile"]), timeout=600)


def specs() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(LIB.glob("*/*/effect.json"))]


COMPOSITION = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <script src="assets/vendor/gsap.min.js"></script>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="4" data-width="320" data-height="180">
      <div id="w1" class="layer"><video id="va" src="assets/a.mp4" data-start="0" data-duration="4" data-media-start="0" data-track-index="0" data-has-audio="true"></video></div>
      <div id="w2" class="layer" style="opacity:0"><video id="vb" src="assets/b.mp4" data-start="0" data-duration="4" data-media-start="0" data-track-index="1" muted></video></div>
      <div id="s1" class="scene" style="background-color:#000000"></div>
      <div id="s2" class="scene" style="background-color:#000000"></div>
      <div id="t1" class="title">Fresh cut ready</div>
    </div>
    <script>
      const tl = gsap.timeline({ paused: true });
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def project(name: str) -> Path:
    p = _state["ws"] / "projects" / "fx-test" / name
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    (p / "index.html").write_text(COMPOSITION, encoding="utf-8")
    (p / "asset-rights-register.yaml").write_text("assets: []\n", encoding="utf-8")
    return p


class Catalog(unittest.TestCase):
    def test_every_effect_has_the_catalog_fields(self):
        for s in specs():
            missing = [k for k in REQUIRED if k not in s]
            self.assertEqual(missing, [], s["effect_id"])

    def test_effect_ids_are_unique_and_match_their_folder(self):
        ids = [p.parent.name for p in LIB.glob("*/*/effect.json")]
        self.assertEqual(len(ids), len(set(ids)))
        for p in LIB.glob("*/*/effect.json"):
            s = json.loads(p.read_text())
            self.assertEqual(s["effect_id"], p.parent.name)
            self.assertEqual(s["family"], p.parent.parent.name)

    def test_routes_families_and_parameter_ranges_are_valid(self):
        for s in specs():
            self.assertIn(s["implementation_route"], ROUTES, s["effect_id"])
            self.assertIn(s["family"], FAMILIES, s["effect_id"])
            for p in s["parameters"]:
                self.assertTrue(p["min"] <= p["default"] <= p["max"], f"{s['effect_id']}.{p['key']}")

    def test_clean_room_effects_carry_a_study_key_and_no_studied_name(self):
        study = (REPO / "docs/effects/reference-study.md").read_text(encoding="utf-8")
        for s in specs():
            if s["provenance"] == "clean-room":
                self.assertRegex(s["reference_id"] or "", r"^RS-\d{3}$", s["effect_id"])
                self.assertIn(f"study_key: {s['reference_id']}", study)
            self.assertNotRegex(json.dumps(s), r"(?i)concat\.", s["effect_id"])

    def test_generated_catalog_is_current(self):
        proc = H.run([sys.executable, REPO / "scripts/build_catalog.py", "--check"])
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_a_verified_status_needs_a_passing_twelve_check_record(self):
        cat = json.loads("\n".join(l for l in (LIB / "catalog.yaml").read_text().splitlines() if not l.startswith("#")))
        for e in cat["effects"]:
            if e["status"] not in {"verified", "limited"}:
                continue
            rec = json.loads((REPO / e["verification_record"]).read_text())
            self.assertEqual(rec["result"], "pass", e["effect_id"])
            numbers = {c["n"] for c in rec["checks"]}
            self.assertTrue(set(range(1, 13)) <= numbers, e["effect_id"])
            self.assertTrue(all(c["result"] in {"pass", "not-applicable"} for c in rec["checks"]), e["effect_id"])

    def test_every_effect_script_defines_its_own_id_and_reads_no_clock(self):
        for p in LIB.glob("*/*/update.js"):
            text = p.read_text(encoding="utf-8")
            self.assertIn(f'HFX.define("{p.parent.name}"', text)
            for banned in ("Math.random", "Date.now", "new Date", "performance.now", "requestAnimationFrame", "setTimeout", "fetch("):
                self.assertNotIn(banned, text, f"{p.parent.name} uses {banned}")


class Featured(unittest.TestCase):
    """The hand-curated first picks: exactly 50, each a verified picture effect."""

    @staticmethod
    def build_catalog():
        import importlib.util
        spec = importlib.util.spec_from_file_location("build_catalog", REPO / "scripts/build_catalog.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_the_featured_set_is_fifty_verified_picture_effects(self):
        cat = json.loads("\n".join(l for l in (LIB / "catalog.yaml").read_text().splitlines() if not l.startswith("#")))
        picks = [e for e in cat["effects"] if e["featured"]]
        self.assertEqual(len(picks), 50)
        for e in picks:
            self.assertEqual(e["status"], "verified", e["effect_id"])
            self.assertNotEqual(e["family"], "audio", e["effect_id"])
            self.assertTrue(e["featured_use"].strip(), e["effect_id"])

    def test_list_featured_returns_the_fifty_with_their_use(self):
        proc = fx("list", "--featured")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["count"], 50)
        self.assertTrue(all(e["featured"] and e["featured_use"] for e in data["effects"]))

    def test_the_build_refuses_an_unverified_or_unknown_featured_effect(self):
        mod = self.build_catalog()
        rows = mod.entries()
        real = mod.featured()
        unverified = next(r["effect_id"] for r in rows if r["status"] == "implemented")
        for swap in (unverified, "no-such-effect"):
            effects = [{"effect_id": swap, "use_for": "x"}] + real["effects"][1:]
            mod.featured = lambda effects=effects: {**real, "effects": effects}
            problems = mod.featured_problems(rows)
            self.assertTrue(any(swap in p for p in problems), problems)
        mod.featured = lambda: {**real, "effects": real["effects"][:49]}
        self.assertTrue(any("not 50" in p for p in mod.featured_problems(rows)))


class ApplyAndRemove(unittest.TestCase):
    CASES = [
        ("posterize", ["--target", "#w1"]),
        ("hue-shift", ["--target", "#w1"]),
        ("teal-orange", ["--target", "#va"]),
        ("pixelate", ["--target", "#va", "--animate", "amount=0.5:0.2,2:0.9"]),
        ("snowfall", ["--target", "#w1"]),
        ("linear-wipe", ["--from", "#s1", "--to", "#s2", "--at", "1", "--duration", "0.6"]),
        ("word-pop", ["--target", "#t1"]),
        ("picture-in-picture", ["--target", "#w1", "--to", "#w2"]),
        ("wave-warp", ["--target", "#w1"]),
        ("high-pass", ["--target", "#va"]),
        ("fractal-noise", []),
    ]

    def test_apply_then_remove_restores_the_composition_exactly(self):
        for effect, args in self.CASES:
            with self.subTest(effect=effect):
                p = project(f"rt-{effect}")
                before = (p / "index.html").read_text()
                proc = fx("apply", p, "--effect", effect, "--allow-unverified", "--iid", "fx1", *args)
                self.assertEqual(proc.returncode, 0, proc.stderr)
                after = (p / "index.html").read_text()
                self.assertNotEqual(before, after)
                proc = fx("remove", p, "--iid", "fx1")
                self.assertEqual(proc.returncode, 0, proc.stderr)
                self.assertEqual((p / "index.html").read_text(), before)

    def test_static_hyperframes_attribute_needs_no_runtime(self):
        p = project("grade")
        self.assertEqual(fx("apply", p, "--effect", "teal-orange", "--allow-unverified", "--target", "#va").returncode, 0)
        html = (p / "index.html").read_text()
        self.assertIn("data-color-grading=", html)
        self.assertNotIn("fx-runtime.js", html)

    def test_two_grades_on_one_clip_merge_into_one_attribute(self):
        p = project("two-grades")
        fx("apply", p, "--effect", "white-balance", "--allow-unverified", "--target", "#va", "--param", "amount=0.4")
        fx("apply", p, "--effect", "vignette", "--allow-unverified", "--target", "#va")
        attr = re.search(r"data-color-grading='([^']*)'|data-color-grading=\"([^\"]*)\"", (p / "index.html").read_text())
        value = json.loads(attr.group(1) or attr.group(2).replace("&quot;", '"'))
        self.assertEqual(value["adjust"]["temperature"], 0.4)
        self.assertIn("vignette", value["details"])

    def test_two_filter_effects_on_one_layer_share_one_filter_chain(self):
        p = project("chain")
        fx("apply", p, "--effect", "posterize", "--allow-unverified", "--target", "#w1", "--iid", "a1")
        fx("apply", p, "--effect", "hue-shift", "--allow-unverified", "--target", "#w1", "--iid", "b1")
        rules = re.findall(r"#w1 \{ filter: ([^;]+); \}", (p / "index.html").read_text())
        self.assertEqual(len(rules), 1)
        self.assertTrue(rules[0].startswith("url(#fx-a1-filter)") and "hue-rotate" in rules[0])

    def test_out_of_range_values_unverified_effects_and_missing_elements_are_refused(self):
        p = project("refuse")
        self.assertEqual(fx("apply", p, "--effect", "posterize", "--allow-unverified", "--target", "#w1", "--param", "levels=40").returncode, 4)
        self.assertEqual(fx("apply", p, "--effect", "posterize", "--allow-unverified", "--target", "#nope").returncode, 4)
        self.assertEqual(fx("apply", p, "--effect", "no-such-effect", "--target", "#w1").returncode, 2)
        spec = json.loads((LIB / "image-effects/posterize/effect.json").read_text())
        if not (LIB / "image-effects/posterize/verification.json").is_file():
            self.assertEqual(fx("apply", p, "--effect", "posterize", "--target", "#w1").returncode, 4)
        del spec

    def test_a_project_outside_the_workspace_is_refused(self):
        outside = _state["base"] / "elsewhere"
        outside.mkdir(exist_ok=True)
        (outside / "index.html").write_text(COMPOSITION)
        self.assertEqual(fx("apply", outside, "--effect", "posterize", "--allow-unverified", "--target", "#w1").returncode, 4)


class StackAndPlan(unittest.TestCase):
    def test_two_camera_moves_on_one_layer_are_a_conflict(self):
        p = project("stack")
        fx("apply", p, "--effect", "punch-in", "--allow-unverified", "--target", "#w1", "--iid", "a1")
        fx("apply", p, "--effect", "camera-shake", "--allow-unverified", "--target", "#w1", "--iid", "b1")
        proc = fx("stack-check", p)
        report = json.loads(proc.stdout)
        self.assertTrue(any("a1, b1 all set transform" in x for x in report["problems"]), report)

    def test_check_plan_rejects_out_of_range_values_and_unknown_effects(self):
        plan = _state["ws"] / "plan.yaml"
        plan.write_text("plan_id: P1\nproject_id: X\neffect_approver: owner\nphotosensitivity_budget: pass\n"
                        "effects:\n  - effect_id: posterize\n    params: {levels: 99}\n  - effect_id: not-real\n")
        report = json.loads(fx("check-plan", plan).stdout)
        self.assertEqual(report["result"], "fail")
        self.assertTrue(any("outside the verified range" in x for x in report["problems"]))
        self.assertTrue(any("not in the library" in x for x in report["problems"]))

    def test_check_plan_requires_sdr_approval_for_hdr_sources(self):
        plan = _state["ws"] / "plan-hdr.yaml"
        plan.write_text("plan_id: P2\nproject_id: X\neffect_approver: owner\nphotosensitivity_budget: pass\n"
                        "hdr_sources: yes\neffects:\n  - effect_id: posterize\n")
        report = json.loads(fx("check-plan", plan).stdout)
        self.assertTrue(any("SDR working copy" in x for x in report["problems"]))


@unittest.skipUnless(H.have("ffmpeg") and H.have("ffprobe"), "FFmpeg not installed")
class FlashCheck(unittest.TestCase):
    """WCAG 2.3.1 against inputs whose answer is known."""

    def clip(self, name: str, expr: str) -> Path:
        dest = _state["base"] / f"{name}.mp4"
        H.ffmpeg("-f", "lavfi", "-i", f"color=c=black:s=320x180:r=30:d=2,{expr}", "-c:v", "libx264", "-crf", "10",
                 "-pix_fmt", "yuv420p", dest)
        return dest

    def verdict(self, path: Path) -> dict:
        proc = fx("flash-check", path)
        return json.loads(proc.stdout or proc.stderr)

    def test_five_hertz_full_frame_strobe_fails(self):
        r = self.verdict(self.clip("s5", "geq=lum='if(lt(mod(N\\,6)\\,3)\\,235\\,16)':cb=128:cr=128"))
        self.assertEqual(r["result"], "fail")
        self.assertEqual(r["general"]["flashes"], 5.0)

    def test_red_strobe_fails_the_red_rule(self):
        r = self.verdict(self.clip("red", "geq=r='if(lt(mod(N\\,6)\\,3)\\,230\\,10)':g=10:b=10"))
        self.assertEqual(r["result"], "fail")
        self.assertGreater(r["red"]["flashes"], 3)

    def test_two_hertz_strobe_warns_but_passes_the_limit(self):
        r = self.verdict(self.clip("s2", "geq=lum='if(lt(mod(N\\,15)\\,8)\\,235\\,16)':cb=128:cr=128"))
        self.assertEqual(r["result"], "warn")

    def test_small_area_strobe_is_under_the_area_limit(self):
        r = self.verdict(self.clip("small", "geq=lum='if(between(X\\,150\\,170)*between(Y\\,80\\,95)*lt(mod(N\\,6)\\,3)\\,235\\,60)':cb=128:cr=128"))
        self.assertNotEqual(r["result"], "fail")
        self.assertTrue(r["small_area_flicker"])

    def test_still_picture_passes(self):
        r = self.verdict(self.clip("still", "geq=lum='60+X/3':cb=128:cr=128"))
        self.assertEqual(r["result"], "pass")

    def test_criteria_cite_wcag_with_an_access_date(self):
        r = self.verdict(self.clip("still2", "geq=lum='60+X/3':cb=128:cr=128"))
        self.assertIn("https://www.w3.org/TR/WCAG22/", r["criteria"]["urls"])
        self.assertEqual(r["criteria"]["accessed"], "2026-10-21")
        self.assertEqual(r["criteria"]["general_flash_min_change"], 0.10)


class CopyCheck(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(REPO / "scripts"))
        import copy_check
        self.cc = copy_check

    def test_repository_passes_the_copy_check(self):
        proc = H.run([sys.executable, REPO / "scripts/copy_check.py", "check"])
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_a_copied_shader_is_caught(self):
        base = _state["base"] / "cc"
        studied, repo = base / "studied", base / "repo"
        (studied / "pkg").mkdir(parents=True)
        (repo / "skills").mkdir(parents=True)
        # Invented words only: real shader idioms would match the real fingerprints.
        shader = ("fn zorblat(quax: f32, wimble: f32) -> f32 { let snorf = quax * wimble + quax; let plimp = snorf - wimble * 3.75; "
                  "return glomp(plimp, snorf, quax) + frabble(wimble); }")
        (studied / "pkg/effect.wgsl").write_text(shader)
        out = base / "fp.json"
        H.run([sys.executable, REPO / "scripts/copy_check.py", "fingerprint", "--source", studied, "--commit", "0" * 40,
               "--date", "2026-10-27", "--out", out])
        (repo / "skills/copied.wgsl").write_text(shader)
        (repo / "skills/original.js").write_text("export const look = (amount) => ({ warmth: amount * 0.5, contrast: 1 + amount });\n")
        problems = self.cc.check(repo, out)
        self.assertTrue(any("copied.wgsl" in p for p in problems), problems)
        self.assertFalse(any("original.js" in p for p in problems), problems)

    def test_syntax_only_shingles_do_not_count(self):
        self.assertTrue(self.cc.trivial(tuple("for ( var i = 0 ; i <".split())))
        self.assertFalse(self.cc.trivial(tuple("var halation = mix ( glow , 0.37 )".split())))

    def test_the_profile_and_the_repository_use_the_same_trivial_rule(self):
        spec = __import__("importlib.util").util.spec_from_file_location("fxmod", LIB / "scripts/fx.py")
        mod = __import__("importlib.util").util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertEqual(mod.COPY_KEYWORDS, self.cc.KEYWORDS)
        self.assertEqual(mod.COPY_TRIVIAL_NUMBERS, self.cc.TRIVIAL_NUMBERS)
        self.assertEqual(mod.COPY_KEYWORDS_POSITION, self.cc.KEYWORDS_POSITION)

    def test_the_studied_projects_name_is_caught_outside_the_allowed_files(self):
        base = _state["base"] / "cc-name"
        (base / "skills").mkdir(parents=True)
        (base / "skills/note.md").write_text("Ported from Concat.\n")
        fp = base / "fp.json"
        fp.write_text(json.dumps({"salt": "x", "shingle_hashes": [], "image_sha256": [], "commit": "0" * 40,
                                  "files_fingerprinted": 0}))
        problems = self.cc.check(base, fp)
        self.assertTrue(any("named outside the allowed files" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
