"""Render tests. Every editing operation the README claims is rendered here
from an installed temporary profile and checked against synthetic ground truth.

Needs the pinned toolchain, so it runs only when asked:

    VE_TEST_TOOLCHAIN=1 VE_TEST_BROWSER=/path/to/chrome-headless-shell \
    VE_TEST_USE_HERMES=1 python3 -m unittest tests.test_renders -v

Without VE_TEST_TOOLCHAIN=1 every test here is skipped, which the release
notes report as `not run`, never as passed.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import unittest
from pathlib import Path

from tests import harness as H

LONGFORM_SECONDS = int(os.environ.get("VE_TEST_LONGFORM_SECONDS", "120"))
LONGFORM_SIZE = os.environ.get("VE_TEST_LONGFORM_SIZE", "1280x720")
RESULTS: dict[str, dict] = {}

_state: dict = {}


def setUpModule() -> None:
    if not H.toolchain_requested():
        raise unittest.SkipTest("VE_TEST_TOOLCHAIN is not 1: render tests not run")
    keep = os.environ.get("VE_TEST_KEEP")
    base = Path(keep) if keep else Path(tempfile.mkdtemp(prefix="ve-render-"))
    if keep and base.exists():
        shutil.rmtree(base)
    base.mkdir(parents=True, exist_ok=True)
    profile = H.install_profile(base)
    ws = base / "ws"
    H.setup_toolchain(profile, ws)
    status = H.hf(profile, "status", "--json")
    assert json.loads(status.stdout)["video_engine"] == "toolchain verified", status.stdout
    take = H.make_timecode_clip(ws / "footage" / "take.mp4", seconds=14)
    proc = H.hf(profile, "footage-add", take, cwd=ws)
    assert proc.returncode == 0, proc.stderr
    _state.update(base=base, profile=profile, ws=ws, take=take, take_sha=H.sha256(take), keep=bool(keep))


def tearDownModule() -> None:
    if not _state:
        return
    report = os.environ.get("VE_TEST_REPORT")
    if report:
        Path(report).write_text(json.dumps(RESULTS, indent=2) + "\n", encoding="utf-8")
    H.hf(_state["profile"], "preview-stop", cwd=_state["ws"] / "projects")
    if not _state["keep"]:
        shutil.rmtree(_state["base"], ignore_errors=True)


class RenderCase(unittest.TestCase):
    maxDiff = None

    @property
    def profile(self) -> Path:
        return _state["profile"]

    @property
    def ws(self) -> Path:
        return _state["ws"]

    def project(self, name: str, version: str = "v1", media: dict[str, Path] | None = None) -> Path:
        project = H.new_project(self.profile, self.ws, name, version)
        for rel, src in (media or {"assets/take.mp4": _state["take"]}).items():
            (project / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, project / rel)
        return project

    def draft(self, project: Path, *extra) -> Path:
        result = H.render(self.profile, project, "draft", "--comparison", "house_style", *extra)
        RESULTS[self.id().split(".")[-1]] = {k: result.get(k) for k in ("render_seconds", "peak_tree_rss_mb", "workers")}
        return Path(result["outputs"][0])

    def assertPicture(self, out: Path, expected: dict[float, int | None]) -> None:
        got = {t: H.source_second_at(out, t) for t in expected}
        self.assertEqual(got, expected, "picture does not match the edit")

    def assertSound(self, out: Path, expected: dict[float, int | None], window: float = 0.5) -> None:
        got = {t: H.audio_second_at(out, t, t + window) for t in expected}
        self.assertEqual(got, expected, "sound does not match the edit")


class CutsAndFinalPipeline(RenderCase):
    """Hard cut, trim in and out, split and splice, reorder, then the full
    draft -> style decision -> rights -> final path with receipts."""

    def test_cut_trim_splice_reorder_then_final(self) -> None:
        project = self.project("cuts")
        body = "\n".join([
            H.video_clip("a1", "assets/take.mp4", 0, 1, 4),    # trim: in=4 out=5
            H.video_clip("a2", "assets/take.mp4", 1, 1, 6),    # split and splice: source second 5 removed
            H.video_clip("b", "assets/take.mp4", 2, 3, 10),    # hard cut at 2.0 to source 10-13
            H.video_clip("c", "assets/take.mp4", 5, 1, 1),     # reorder: earlier source placed last
        ])
        (project / "index.html").write_text(H.html_document(640, 360, 6, body), encoding="utf-8")
        self.assertEqual(H.hf(self.profile, "lint", cwd=project).returncode, 0)
        check = H.hf(self.profile, "check", cwd=project)
        self.assertEqual(check.returncode, 0, check.stdout[-800:])

        out = self.draft(project)
        picture = {0.5: 4, 1.5: 6, 2.5: 10, 3.5: 11, 4.5: 12, 5.5: 1}
        self.assertPicture(out, picture)
        self.assertSound(out, {0.25: 4, 1.25: 6, 2.25: 10, 3.25: 11, 4.25: 12, 5.25: 1})
        # the hard cut lands on its timecode: one frame either side of 2.0
        self.assertPicture(out, {2.0 - 2 / 30: 6, 2.0 + 1 / 30: 10})
        self.assertAlmostEqual(float(H.probe(out)["format"]["duration"]), 6.0, delta=0.1)

        # final is refused until a style decision and licence records exist
        refused = H.hf(self.profile, "render", "--stage", "final", "--fps", "30", cwd=project)
        self.assertEqual(refused.returncode, 5)
        self.assertEqual(json.loads(refused.stderr)["status"], "approval required")
        H.record_style_decision(project)
        refused = H.hf(self.profile, "render", "--stage", "final", "--fps", "30", cwd=project)
        self.assertIn("no complete license record", refused.stderr)
        H.register_assets(project, ["assets/take.mp4"])

        final = H.render(self.profile, project, "final")
        final_path = Path(final["outputs"][0])
        self.assertEqual(final["status"], "final rendered with file path")
        self.assertEqual(final["style_decision"], "hybrid")
        self.assertPicture(final_path, picture)

        receipt = Path(final["receipts"][0]).read_text(encoding="utf-8")
        fields = dict(line.split(": ", 1) for line in receipt.splitlines())
        self.assertEqual(json.loads(fields["sha256"]), H.sha256(final_path))
        self.assertEqual(int(fields["size_bytes"]), final_path.stat().st_size)
        self.assertEqual((fields["width"], fields["height"], fields["frame_rate"]), ("640", "360", "30.0"))
        self.assertEqual(json.loads(fields["video_codec"]), "h264")
        self.assertEqual(json.loads(fields["quality"]), "delivery")
        self.assertEqual(fields["audio_silent"], "false")
        self.assertEqual(fields["inspected"], "false")
        self.assertGreater(int(fields["peak_tree_rss_mb"]), 0)
        self.assertIn("planned from measured memory", fields["workers_basis"])
        draft_receipt = next(p for p in (project / "receipts").glob("*draft*.yaml"))
        self.assertIn('quality: "draft"', draft_receipt.read_text(encoding="utf-8"))
        self.assertNotEqual(H.sha256(out), H.sha256(final_path))
        RESULTS["draft_vs_final"] = {"draft_bytes": out.stat().st_size, "final_bytes": final_path.stat().st_size}

        # the original is byte-identical after the whole edit
        verify = H.hf(self.profile, "footage-verify", cwd=project)
        self.assertEqual(verify.returncode, 0, verify.stdout)
        self.assertEqual(H.sha256(_state["take"]), _state["take_sha"])

        # Cut detection on the render, at the recorded threshold: every cut it
        # reports is a real one. It is allowed to miss a cut between two
        # similar colours, which is the documented limit of scene detection;
        # the count it found is recorded, not assumed.
        cuts = json.loads(H.tools(self.profile, "cuts", final_path, "--threshold", "0.30").stdout)
        found = cuts["cut_times_seconds"]
        self.assertTrue(all(abs(c - round(c)) < 0.1 and 1 <= round(c) <= 5 for c in found), found)
        self.assertGreaterEqual(len(found), 4)
        RESULTS["cut_detection_on_render"] = {"true_cuts": 5, "detected": len(found), "threshold": 0.30}

        # a second final to the same explicit path is refused, never overwritten
        again = H.hf(self.profile, "render", "--stage", "final", "--fps", "30", "--output", final_path, cwd=project)
        self.assertEqual(again.returncode, 4)
        self.assertIn("will not be overwritten", again.stderr)


class RetimeAndFreeze(RenderCase):
    def test_slow_motion_and_held_frame(self) -> None:
        project = self.project("retime")
        H.ffmpeg("-ss", "8.5", "-i", _state["take"], "-frames:v", "1", project / "assets" / "held.png")
        body = "\n".join([
            H.video_clip("slow", "assets/take.mp4", 0, 4, 4, extra=' data-playback-rate="0.5"'),
            '      <img id="hold" class="clip fill" src="assets/held.png" data-start="4" data-duration="2" data-track-index="0" />',
        ])
        (project / "index.html").write_text(H.html_document(640, 360, 6, body), encoding="utf-8")
        out = self.draft(project)
        # 0.5x: each source second lasts two timeline seconds
        self.assertPicture(out, {0.5: 4, 1.5: 4, 2.5: 5, 3.5: 5})
        # freeze: the held frame (source second 8) for the full hold, with no sound
        self.assertPicture(out, {4.3: 8, 5.0: 8, 5.7: 8})
        self.assertIsNone(H.tone_at(out, 4.3, 5.7))
        RESULTS["retime_tone_hz"] = {"source_hz": H.tone_hz(4), "rendered_hz": round(H.tone_at(out, 0.3, 1.7) or 0)}


class PunchInAndCrossfade(RenderCase):
    def test_punch_in_and_crossfade(self) -> None:
        project = self.project("punch")
        body = "\n".join([
            '      <div id="p-visual" class="inner">',
            H.video_clip("p", "assets/take.mp4", 0, 3.5, 2.2, track=0,
                         extra=''' data-automation='{"version":1,"lanes":[{"target":"volume","points":[{"t":0,"v":1},{"t":3,"v":1},{"t":3.5,"v":0}]}]}' '''),
            "      </div>",
            '      <div id="q-visual" class="inner">',
            H.video_clip("q", "assets/take.mp4", 3, 3, 7.2, track=1,
                         extra=''' data-automation='{"version":1,"lanes":[{"target":"volume","points":[{"t":0,"v":0},{"t":0.5,"v":1},{"t":3,"v":1}]}]}' '''),
            "      </div>",
        ])
        script = "\n".join([
            '      tl.set("#q-visual", { opacity: 0 }, 0);',
            '      tl.to("#p-visual", { scale: 2, duration: 0.2 }, 0.3);',          # punch-in on the wrapper
            '      tl.to("#p-visual", { opacity: 0, duration: 0.5 }, 3);',          # crossfade out
            '      tl.to("#q-visual", { opacity: 1, duration: 0.5 }, 3);',          # crossfade in
        ])
        (project / "index.html").write_text(H.html_document(640, 360, 6, body, script), encoding="utf-8")
        self.assertEqual(H.hf(self.profile, "lint", cwd=project).returncode, 0)
        out = self.draft(project)
        # The white box is 80px. A point 70px right of centre is background
        # before the punch-in and white after a 2x scale.
        probe_point = "8:8:386:176"
        before = H.frame_rgb(out, 0.1, probe_point)
        after = H.frame_rgb(out, 0.7, probe_point)
        self.assertLess(H.colour_distance(before, H.PALETTE[2]), 60, before)
        self.assertLess(H.colour_distance(after, (255, 255, 255)), 40, after)
        # crossfade: source second 5 (clip p at 3.0 is 2.2+3.0) into source second 7
        a, b = H.PALETTE[5], H.PALETTE[7]
        mid = H.frame_rgb(out, 3.25)
        blend = tuple((x + y) / 2 for x, y in zip(a, b))
        self.assertLess(H.colour_distance(mid, blend), 60, f"mid-fade {mid} is not a blend of {a} and {b}")
        self.assertGreater(H.colour_distance(mid, a), 40)
        self.assertGreater(H.colour_distance(mid, b), 40)
        self.assertPicture(out, {3.9: 8, 5.5: 9})


class JCut(RenderCase):
    def test_sound_leads_picture(self) -> None:
        project = self.project("jcut")
        for name, start in (("a", 3), ("b", 9)):
            H.ffmpeg("-ss", str(start), "-t", "3", "-i", _state["take"], "-vn", "-c:a", "pcm_s16le",
                     project / "assets" / f"{name}.wav")
        body = "\n".join([
            H.video_clip("va", "assets/take.mp4", 0, 3, 3, track=0, audio=False),
            H.video_clip("vb", "assets/take.mp4", 3, 3, 9, track=0, audio=False),
            '      <audio id="sa" src="assets/a.wav" data-start="0" data-duration="2" data-media-start="0" data-track-index="10"></audio>',
            # B's sound starts one second before B's picture
            '      <audio id="sb" src="assets/b.wav" data-start="2" data-duration="3" data-media-start="0" data-track-index="11"></audio>',
        ])
        (project / "index.html").write_text(H.html_document(640, 360, 6, body), encoding="utf-8")
        self.assertEqual(H.hf(self.profile, "lint", cwd=project).returncode, 0)
        out = self.draft(project)
        self.assertPicture(out, {0.5: 3, 2.5: 5, 3.5: 9, 4.5: 10})
        self.assertSound(out, {0.25: 3, 1.25: 4, 2.25: 9, 3.25: 10, 4.25: 11})
        # at 2.5s the picture is still A while the sound is already B
        self.assertEqual((H.source_second_at(out, 2.5), H.audio_second_at(out, 2.25, 2.75)), (5, 9))


class DeadAirRemoval(RenderCase):
    def test_keep_ranges_from_transcript_timings(self) -> None:
        src = H.make_timecode_clip(self.ws / "footage" / "pauses.mp4", seconds=9, silent_seconds=(2, 3, 6))
        H.hf(self.profile, "footage-add", src, cwd=self.ws)
        project = self.project("deadair", media={"assets/pauses.mp4": src})
        words = [{"text": f"w{i}", "start": float(i), "end": i + 1.0} for i in (0, 1, 4, 5, 7, 8)]
        (project / "words.json").write_text(json.dumps({"words": words}), encoding="utf-8")
        proposal = json.loads(H.tools(self.profile, "dead-air", project / "words.json", "--min-gap", "0.6",
                                      "--pad", "0", "--source", "assets/pauses.mp4").stdout)
        self.assertEqual(proposal["status"], "proposal")
        self.assertEqual([(c["data-media-start"], c["data-duration"]) for c in proposal["clips"]],
                         [(0.0, 2.0), (4.0, 2.0), (7.0, 2.0)])
        self.assertEqual(proposal["seconds_removed"], 3.0)
        body = "\n".join(H.video_clip(c["id"], c["src"], c["data-start"], c["data-duration"], c["data-media-start"])
                         for c in proposal["clips"])
        (project / "index.html").write_text(H.html_document(640, 360, proposal["timeline_duration_seconds"], body),
                                            encoding="utf-8")
        out = self.draft(project)
        self.assertPicture(out, {0.5: 0, 1.5: 1, 2.5: 4, 3.5: 5, 4.5: 7, 5.5: 8})
        before = json.loads(H.tools(self.profile, "audio-profile", src).stdout)
        after = json.loads(H.tools(self.profile, "audio-profile", out).stdout)
        self.assertEqual([round(g["seconds"]) for g in before["silence_gaps"]], [2, 1])
        self.assertEqual(after["silence_gaps"], [])
        self.assertEqual(H.sha256(src), json.loads(H.tools(self.profile, "probe", src).stdout)["files"][0]["sha256"])


TRANSCRIPT = [
    {"id": "cap-1", "text": "AI saves time", "start": 0.1, "end": 1.6},
    {"id": "cap-2", "text": "every single day", "start": 3.0, "end": 4.6},
]
CAPTION_CSS = """
      .caption { position: absolute; left: 30px; width: 300px; top: 430px; height: 60px; background: #000; color: #fff;
                 font: 700 26px/60px Arial, Helvetica, sans-serif; text-align: center; }
      #lower-third { position: absolute; left: 20px; top: 330px; width: 200px; height: 50px; background: #fff;
                     color: #000; font: 600 20px/50px Arial, Helvetica, sans-serif; padding-left: 10px; }
      #callout { position: absolute; left: 220px; top: 60px; width: 120px; height: 40px; background: #ffe119;
                 color: #000; font: 600 18px/40px Arial, Helvetica, sans-serif; text-align: center; }
"""


class CaptionsAndOverlays(RenderCase):
    def test_vertical_captions_lower_third_and_callout(self) -> None:
        head = H.make_timecode_clip(self.ws / "footage" / "head.mp4", seconds=6, size="360x640",
                                    silent_seconds=(2, 5), start_index=3)
        H.ffmpeg("-i", head, "-vf", "drawbox=x=0:y=0:w=360:h=640:color=0x0082c8:t=fill", "-c:a", "copy",
                 self.ws / "footage" / "head-flat.mp4")
        flat = self.ws / "footage" / "head-flat.mp4"
        H.hf(self.profile, "footage-add", flat, cwd=self.ws)
        project = self.project("captions", media={"assets/head.mp4": flat})
        caps = "\n".join(
            f'      <div id="{c["id"]}" class="clip caption" data-start="{c["start"]}" '
            f'data-duration="{round(c["end"] - c["start"], 3)}" data-track-index="5">{c["text"]}</div>'
            for c in TRANSCRIPT)
        body = "\n".join([
            H.video_clip("head", "assets/head.mp4", 0, 6, 0),
            caps,
            '      <div id="lower-third" class="clip" data-start="1" data-duration="2" data-track-index="6">Synthetic Speaker</div>',
            '      <div id="callout" class="clip" data-start="3" data-duration="2" data-track-index="7">+42%</div>',
        ])
        html = H.html_document(360, 640, 6, body, css=CAPTION_CSS)
        (project / "index.html").write_text(html, encoding="utf-8")
        lint = H.hf(self.profile, "lint", cwd=project)
        self.assertEqual(lint.returncode, 0, lint.stdout[-600:])

        # caption text in the composition is the transcript, word for word
        on_screen = re.findall(r'class="clip caption"[^>]*>([^<]+)</div>', html)
        self.assertEqual(on_screen, [c["text"] for c in TRANSCRIPT])

        out = self.draft(project)
        stream = H.video_stream(out)
        self.assertEqual((stream["width"], stream["height"]), (360, 640))
        video_blue = (0, 130, 200)

        def region(t: float, crop: str):
            return H.frame_rgb(out, t, crop)

        cap_box, lt_box, call_box = "300:60:30:430", "180:40:30:335", "100:30:230:65"
        for t in (0.8, 3.8):       # a caption is up: black card with white text
            rgb = region(t, cap_box)
            self.assertGreater(H.colour_distance(rgb, video_blue), 120, f"no caption card at {t}s: {rgb}")
            self.assertGreater(sum(rgb) / 3, 6, f"caption card at {t}s has no text pixels: {rgb}")
            self.assertLess(sum(rgb) / 3, 140)
        for t in (2.3, 5.3):       # between captions the footage shows through
            self.assertLess(H.colour_distance(region(t, cap_box), video_blue), 50)
        self.assertGreater(sum(region(2.0, lt_box)) / 3, 150, "lower-third missing at 2.0s")
        self.assertLess(H.colour_distance(region(0.5, lt_box), video_blue), 50, "lower-third up too early")
        self.assertLess(H.colour_distance(region(4.0, call_box), (255, 225, 25)), 90, "callout missing at 4.0s")
        self.assertLess(H.colour_distance(region(1.5, call_box), video_blue), 50, "callout up too early")

        # safe zone: the same boxes against an owner-confirmed fixture zone
        plan = {"canvas": {"width": 360, "height": 640},
                "safe_zone": {"source": "owner", "top": 50, "bottom": 140, "left": 20, "right": 20},
                "elements": [{"id": "caption", "x": 30, "y": 430, "width": 300, "height": 60},
                             {"id": "lower-third", "x": 20, "y": 330, "width": 200, "height": 50},
                             {"id": "callout", "x": 220, "y": 60, "width": 120, "height": 40}]}
        (project / "overlay-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        ok = H.tools(self.profile, "safe-zone", project / "overlay-plan.json")
        self.assertEqual((ok.returncode, json.loads(ok.stdout)["status"]), (0, "pass"))
        plan["elements"].append({"id": "too-low", "x": 30, "y": 560, "width": 300, "height": 60})
        (project / "overlay-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        bad = H.tools(self.profile, "safe-zone", project / "overlay-plan.json")
        self.assertEqual(bad.returncode, 5)
        self.assertEqual(json.loads(bad.stdout)["elements"][-1]["overflow_px"], {"bottom": 120})
        del plan["safe_zone"]["source"]
        (project / "overlay-plan.json").write_text(json.dumps(plan), encoding="utf-8")
        unsourced = H.tools(self.profile, "safe-zone", project / "overlay-plan.json")
        self.assertIn("no recorded source", unsourced.stderr)


class TransparentMotionGraphic(RenderCase):
    def test_webm_with_alpha(self) -> None:
        project = self.project("alpha", media={})
        css = """
      html, body, #root { background: transparent !important; }
      #badge { position: absolute; left: 220px; top: 130px; width: 200px; height: 100px; background: #f032e6; }
"""
        body = '      <div id="badge" class="clip" data-start="0" data-duration="2" data-track-index="0"></div>'
        script = '      tl.fromTo("#badge", { x: -40 }, { x: 40, duration: 2, ease: "none" }, 0);'
        (project / "index.html").write_text(H.html_document(640, 360, 2, body, script, css), encoding="utf-8")
        result = H.render(self.profile, project, "draft", "--comparison", "house_style", "--format", "webm")
        out = Path(result["outputs"][0])
        self.assertEqual(out.suffix, ".webm")
        corner = H.frame_rgba(out, 1.0, "16:16:8:8", decoder="libvpx-vp9")
        centre = H.frame_rgba(out, 1.0, "16:16:312:172", decoder="libvpx-vp9")
        self.assertLess(corner[3], 16, f"corner is not transparent: {corner}")
        self.assertGreater(centre[3], 240, f"graphic is not opaque: {centre}")
        self.assertLess(H.colour_distance(centre, (240, 50, 230)), 60)
        RESULTS["alpha"] = {"corner_rgba": corner, "centre_rgba": centre}


class ReframeAndBatch(RenderCase):
    def test_reframes_are_separate_reviewed_renders(self) -> None:
        sizes = {"v1-16x9": (640, 360), "v2-9x16": (360, 640), "v3-4x5": (480, 600)}
        outputs = {}
        for version, (w, h) in sizes.items():
            project = self.project("reframe", version)
            body = '      <div id="shot" class="inner">\n' + H.video_clip("take", "assets/take.mp4", 0, 2, 4) + "\n      </div>"
            (project / "index.html").write_text(H.html_document(w, h, 2, body), encoding="utf-8")
            outputs[version] = self.draft(project)
            RESULTS[f"reframe_{version}"] = RESULTS.pop("test_reframes_are_separate_reviewed_renders")
        for version, (w, h) in sizes.items():
            stream = H.video_stream(outputs[version])
            self.assertEqual((stream["width"], stream["height"]), (w, h), version)
            # object-fit: cover keeps the centred subject (the white box) in frame
            centre = H.frame_rgb(outputs[version], 1.0, f"16:16:{w // 2 - 8}:{h // 2 - 8}")
            self.assertLess(H.colour_distance(centre, (255, 255, 255)), 40, f"{version}: subject lost in reframe")
            self.assertEqual(H.source_second_at(outputs[version], 1.5), 5)
            self.assertEqual(len(list((outputs[version].parent.parent / "receipts").glob("*.receipt.yaml"))), 1)
        # version compare: one labelled sheet from two versions at the same instant
        video_dir = self.ws / "projects" / "reframe"
        sheet = video_dir / "compare-16x9-vs-9x16.png"
        proc = H.hf(self.profile, "compare", "v1-16x9", "v2-9x16", "--at", "1", "--labels", "wide,vertical",
                    "--out", sheet, cwd=video_dir)
        self.assertEqual(proc.returncode, 0, proc.stdout[-600:] + proc.stderr[-600:])
        self.assertGreater(sheet.stat().st_size, 1000)

    def test_batch_render_one_output_per_row(self) -> None:
        project = self.project("batch", media={})
        html = H.html_document(320, 180, 1, '      <div id="card" class="clip" data-start="0" data-duration="1" data-track-index="0"></div>',
                               css="#card { position: absolute; inset: 0; background: var(--accent); }")
        html = html.replace('<html lang="en">', """<html lang="en" data-composition-variables='[
  {"id":"name","type":"string","label":"Name","default":"default"},
  {"id":"accent","type":"color","label":"Accent","default":"#000080"}
]'>""")
        (project / "index.html").write_text(html, encoding="utf-8")
        rows = {"rows": [{"name": "red", "accent": "#e6194b"}, {"name": "green", "accent": "#3cb44b"}]}
        (project / "rows.json").write_text(json.dumps(rows), encoding="utf-8")
        result = H.render(self.profile, project, "draft", "--comparison", "house_style", "--batch", "rows.json",
                          "--output", "renders/batch-{name}.mp4", "--strict-variables")
        outputs = sorted(Path(p) for p in result["outputs"])
        self.assertEqual([p.name for p in outputs], ["batch-green.mp4", "batch-red.mp4"])
        self.assertEqual(len(result["receipts"]), 2)
        self.assertEqual(H.palette_index(H.frame_rgb(outputs[0], 0.5)), 1)
        self.assertEqual(H.palette_index(H.frame_rgb(outputs[1], 0.5)), 0)


class ColorTreatment(RenderCase):
    def test_grade_changes_the_picture_and_contact_sheets_exist(self) -> None:
        project = self.project("grade")
        body = '      <div id="shot" class="inner">\n' + H.video_clip("take", "assets/take.mp4", 0, 2, 4) + "\n      </div>"
        (project / "index.html").write_text(H.html_document(640, 360, 2, body), encoding="utf-8")
        before = self.draft(project)
        proc = H.hf(self.profile, "media-treatment", "--project", ".", "--file", "index.html", "--selector", "#take",
                    "--grading", '{"preset":"warm-daylight","intensity":1}', "--apply", "--json", cwd=project)
        self.assertEqual(proc.returncode, 0, proc.stdout[-800:] + proc.stderr[-800:])
        self.assertIn("data-color-grading", (project / "index.html").read_text(encoding="utf-8"))
        after = self.draft(project)
        shift = H.colour_distance(H.frame_rgb(before, 1.0), H.frame_rgb(after, 1.0))
        self.assertGreater(shift, 3.0, "the grade did not change the picture")
        RESULTS["grade_shift_rgb_distance"] = round(shift, 1)
        for label, clip in (("before", before), ("after", after)):
            sheet = project / "snapshots" / f"contact-{label}.jpg"
            made = H.tools(self.profile, "contact-sheet", clip, "--out", sheet, "--count", "4", "--columns", "2")
            self.assertEqual(made.returncode, 0, made.stderr)
            self.assertGreater(sheet.stat().st_size, 500)


class AudioMix(RenderCase):
    def test_music_bed_with_voice_carve_and_clipping(self) -> None:
        project = self.project("mix", media={})
        assets = project / "assets"
        # voice: 1 kHz bursts in seconds 1-2 and 4-5; music: a steady 150 Hz bed
        H.ffmpeg("-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000:duration=6",
                 "-af", "volume='if(between(t,1,3)+between(t,4,5.5),1,0)':eval=frame", assets / "voice.wav")
        H.ffmpeg("-f", "lavfi", "-i", "sine=frequency=150:sample_rate=48000:duration=6", "-af", "volume=2", assets / "music.wav")
        duck = '{"version":1,"lanes":[{"target":"volume","points":[{"t":0,"v":1},{"t":0.9,"v":1},{"t":1,"v":0.1},{"t":3,"v":0.1},{"t":3.1,"v":1},{"t":3.9,"v":1},{"t":4,"v":0.1},{"t":5.5,"v":0.1},{"t":5.6,"v":1},{"t":6,"v":1}]}]}'
        body = "\n".join([
            '      <div id="plate" class="clip" data-start="0" data-duration="6" data-track-index="0" style="position:absolute;inset:0;background:#0082c8"></div>',
            '      <audio id="voice" src="assets/voice.wav" data-start="0" data-duration="6" data-track-index="10"></audio>',
            f"      <audio id=\"music\" src=\"assets/music.wav\" data-start=\"0\" data-duration=\"6\" data-track-index=\"11\" data-automation='{duck}'></audio>",
        ])
        (project / "index.html").write_text(H.html_document(320, 180, 6, body), encoding="utf-8")
        self.assertEqual(H.hf(self.profile, "lint", cwd=project).returncode, 0)
        out = self.draft(project)
        speech = project / "speech.json"
        speech.write_text(json.dumps([{"start": 1.0, "end": 3.0}, {"start": 4.0, "end": 5.5}]), encoding="utf-8")
        result = json.loads(H.tools(self.profile, "duck-check", out, "--speech", speech, "--voice-band", "700-1400",
                                    "--music-band", "80-260", "--min-margin-db", "6").stdout)
        RESULTS["duck_check"] = {k: result.get(k) for k in ("voice_over_music_margin_db", "music_carve_depth_db")}
        self.assertEqual(result["status"], "pass", result)
        self.assertGreater(result["music_carve_depth_db"], 10, "the music was not carved under the voice")
        profile = json.loads(H.tools(self.profile, "audio-profile", out).stdout)
        self.assertFalse(profile["silent"])
        self.assertIsInstance(profile["integrated_lufs"], float)
        self.assertEqual(profile["music_present"], "Unavailable")

        # clipping detection on a deliberately overdriven file
        hot = project / "renders" / "hot.wav"
        H.ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=2", "-af", "volume=30dB", "-c:a", "pcm_s16le", hot)
        clipped = json.loads(H.tools(self.profile, "audio-profile", hot).stdout)
        self.assertTrue(clipping := clipped["clipping"], clipped)
        self.assertFalse(profile["clipping"])


class LongForm(RenderCase):
    def test_multi_segment_long_form_with_measurements(self) -> None:
        w, h = (int(x) for x in LONGFORM_SIZE.split("x"))
        seg = 20
        count = max(2, LONGFORM_SECONDS // seg)
        total = count * seg
        loop = H.make_long_timecode_clip(self.ws / "footage" / "long.mp4", total, LONGFORM_SIZE)
        # the fixture itself is checked first, so a failure below is the edit's, not the source's
        for t in (5.5, total / 2 + 0.5, total - 2.5):
            self.assertEqual(H.source_second_at(loop, t), int(t) % 16, f"fixture picture at {t}s")
            self.assertEqual(H.audio_second_at(loop, t - 0.25, t + 0.25), int(t) % 16, f"fixture sound at {t}s")
        H.hf(self.profile, "footage-add", loop, cwd=self.ws)
        project = self.project("longform", media={"assets/long.mp4": loop})
        (project / "compositions").mkdir(exist_ok=True)
        hosts = []
        for i in range(count):
            cid = f"seg-{i:02d}"
            (project / "compositions" / f"{cid}.html").write_text(f"""<!doctype html>
<html>
  <head><meta charset="UTF-8" /></head>
  <body>
    <template>
      <style>
        #root {{ position: absolute; inset: 0; overflow: hidden; background: #000; }}
        #{cid}-title {{ position: absolute; left: 40px; top: 40px; padding: 8px 16px; background: #000; color: #fff;
                       font: 700 32px/1.2 Arial, Helvetica, sans-serif; }}
      </style>
      <div id="root" data-composition-id="{cid}" data-width="{w}" data-height="{h}">
        <video id="{cid}-take" src="assets/long.mp4" data-start="0" data-duration="{seg}" data-media-start="{i * seg}"
               data-track-index="0" playsinline data-has-audio="true"
               style="position:absolute;inset:0;width:100%;height:100%;object-fit:cover"></video>
        <div id="{cid}-title" class="clip" data-start="0" data-duration="3" data-track-index="1">Chapter {i + 1}</div>
      </div>
      <script>
        (() => {{
          const tl = gsap.timeline({{ paused: true }});
          tl.fromTo("#{cid}-title", {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4 }}, 0);
          window.__timelines["{cid}"] = tl;
        }})();
      </script>
    </template>
  </body>
</html>
""", encoding="utf-8")
            hosts.append(f'      <div id="host-{cid}" data-composition-id="{cid}" data-composition-src="compositions/{cid}.html" '
                         f'data-start="{i * seg}" data-duration="{seg}" data-track-index="0" data-width="{w}" data-height="{h}"></div>')
        (project / "index.html").write_text(H.html_document(w, h, total, "\n".join(hosts)), encoding="utf-8")
        lint = H.hf(self.profile, "lint", cwd=project)
        self.assertEqual(lint.returncode, 0, lint.stdout[-1500:])
        plan = json.loads(H.hf(self.profile, "plan-workers", cwd=project).stdout)
        started = time.time()
        out = self.draft(project)
        wall = time.time() - started
        self.assertAlmostEqual(float(H.probe(out)["format"]["duration"]), total, delta=0.5)
        self.assertTrue(H.has_audio(out))
        # each segment shows and sounds the source second its media-start selects
        for i in range(count):
            t = i * seg + 5.5
            expect = (i * seg + 5) % 16
            self.assertEqual(H.source_second_at(out, t), expect, f"segment {i} picture")
            self.assertEqual(H.audio_second_at(out, t - 0.25, t + 0.25), expect, f"segment {i} sound")
        limits = json.loads(H.hf(self.profile, "limits", cwd=project).stdout)
        self.assertEqual(limits["status"], "measured")
        key = f"{w}x{h} draft"
        self.assertEqual(round(limits["longest_render_per_resolution_and_stage"][key]["duration_seconds"]), total)
        RESULTS["longform"] = {"duration_seconds": total, "segments": count, "resolution": LONGFORM_SIZE, "stage": "draft",
                               "wall_seconds": round(wall, 1), "planned_workers": plan["workers"],
                               "available_memory_mb_before": plan["available_mb"], "total_memory_mb": plan["total_mb"],
                               **RESULTS.get("test_multi_segment_long_form_with_measurements", {})}


class PreviewLifecycle(RenderCase):
    def test_preview_starts_on_localhost_and_tears_down(self) -> None:
        project = self.project("preview", media={})
        start = H.hf(self.profile, "preview-start", cwd=project, timeout=180)
        self.assertEqual(start.returncode, 0, start.stdout[-800:] + start.stderr[-800:])
        self.assertIn('"bind": "127.0.0.1"', start.stdout)
        status = H.hf(self.profile, "preview-status", cwd=project)
        self.assertNotIn("0.0.0.0", status.stdout)
        stop = H.hf(self.profile, "preview-stop", cwd=project, timeout=120)
        self.assertEqual(stop.returncode, 0, stop.stdout)
        report = H.parse_json(stop.stdout)
        self.assertEqual(report["status"], "preview stopped")
        self.assertEqual(report["remaining"], [])


class InstalledToolchainFacts(RenderCase):
    def test_pinned_version_runs_and_usage_is_unknown(self) -> None:
        deep = json.loads(H.hf(self.profile, "doctor", "--json", "--deep").stdout)
        self.assertEqual(deep["video_engine"], "toolchain verified")
        self.assertEqual(deep["upstream_doctor"]["version"], "0.8.138")
        self.assertEqual(deep["research"], "owner-supplied only")
        usage = H.hf(self.profile, "usage", "--json", cwd=self.ws / "projects")
        self.assertIn('"status":"unknown"', usage.stdout.replace(" ", ""))

    def test_init_does_not_touch_skill_folders_or_the_network_cache(self) -> None:
        home = self.profile.parents[2]
        self.project("noskills", media={})
        for leak in (".claude/skills", ".agents/skills", ".codex/skills"):
            self.assertFalse((home / leak).exists(), f"init wrote skills into {leak}")
            self.assertFalse((self.profile / "local" / "video-editor" / "video-engine" / "home" / leak).exists(),
                             f"init wrote skills into the engine home: {leak}")
        installed = {p.relative_to(self.profile / "skills").parts[0] for p in (self.profile / "skills").iterdir()}
        self.assertEqual(installed - {".DS_Store"}, {"video-editor-core", "integrations", "hyperframes-video"})

    def test_missing_id_is_caught_by_upstream_lint_and_by_the_launcher(self) -> None:
        project = self.project("noid")
        body = ('      <video src="assets/take.mp4" data-start="0" data-duration="2" data-media-start="0" '
                'data-track-index="0" playsinline data-has-audio="true"></video>\n'
                '      <audio src="assets/take.mp4" data-start="0" data-duration="2" data-track-index="5"></audio>')
        (project / "index.html").write_text(H.html_document(640, 360, 2, body), encoding="utf-8")
        lint = H.hf(self.profile, "lint", cwd=project)
        self.assertNotEqual(lint.returncode, 0)
        self.assertIn("media_missing_id", lint.stdout + lint.stderr)
        refused = H.hf(self.profile, "render", "--stage", "draft", "--comparison", "house_style", cwd=project)
        self.assertEqual(refused.returncode, 5)
        report = json.loads(refused.stderr)
        self.assertEqual(sorted(m["element"] for m in report["missing_id"]), ["audio", "video"])
        self.assertEqual(list((project / "renders").iterdir()), [])

    def test_reference_file_cannot_reach_a_timeline(self) -> None:
        ref = H.make_timecode_clip(self.ws / "references" / "outlier-01.mp4", seconds=3, start_index=9)
        project = self.project("refleak", media={})
        # 1. by path
        body = H.video_clip("r", "../../../references/outlier-01.mp4", 0, 2, 0)
        (project / "index.html").write_text(H.html_document(640, 360, 2, body), encoding="utf-8")
        for cmd in (["render", "--stage", "draft", "--comparison", "house_style"], ["lint"], ["snapshot"]):
            proc = H.hf(self.profile, *cmd, cwd=project)
            self.assertEqual(proc.returncode, 5, cmd)
            self.assertIn("path into the reference folder", proc.stderr)
        # 2. by copying the bytes into the project
        shutil.copy2(ref, project / "assets" / "borrowed.mp4")
        (project / "index.html").write_text(
            H.html_document(640, 360, 2, H.video_clip("r", "assets/borrowed.mp4", 0, 2, 0)), encoding="utf-8")
        proc = H.hf(self.profile, "render", "--stage", "draft", "--comparison", "house_style", cwd=project)
        self.assertEqual(proc.returncode, 5)
        self.assertIn("byte-identical copy of a reference file", proc.stderr)
        # 3. as a command-line path
        proc = H.hf(self.profile, "snapshot", "--against", ref, cwd=project)
        self.assertEqual(proc.returncode, 4)
        self.assertIn("inside the reference folder", proc.stderr)
        self.assertEqual(list((project / "renders").iterdir()), [])
        # analysis of a reference is allowed, and its frames are session-only
        cuts = json.loads(H.tools(self.profile, "cuts", ref).stdout)
        self.assertEqual([round(c) for c in cuts["cut_times_seconds"]], [1, 2])
        frames = json.loads(H.tools(self.profile, "frames", ref).stdout)
        self.assertTrue(frames["is_reference_material"] and frames["session_only"])
        self.assertTrue(all(".video-editor/session/" in f["path"] for f in frames["frames"]))
        sheet = H.tools(self.profile, "contact-sheet", ref, "--out", project / "snapshots" / "ref.jpg")
        self.assertEqual(sheet.returncode, 4)
        cleaned = json.loads(H.tools(self.profile, "session-clean").stdout)
        self.assertEqual(cleaned["files_removed"], frames["frame_count"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
