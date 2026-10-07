"""Measurement and evidence-rule tests against synthetic ground truth.

No Hermes and no HyperFrames toolchain needed. The media tests need FFmpeg
and are skipped (reported `not run`) without it.

    python3 -m unittest tests.test_tools -v
"""

from __future__ import annotations

import datetime as dt
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

from tests import harness as H

_state: dict = {}


def setUpModule() -> None:
    base = Path(tempfile.mkdtemp(prefix="ve-tools-")).resolve()
    profile = H.install_profile(base, use_hermes=False)
    ws = H.make_workspace(profile, base / "ws")
    _state.update(base=base, profile=profile, ws=ws)


def tearDownModule() -> None:
    shutil.rmtree(_state["base"], ignore_errors=True)


def tool(*args):
    return H.tools(_state["profile"], *args, cwd=_state["ws"])


def write(name: str, data, as_yaml: bool = True) -> Path:
    path = _state["ws"] / "projects" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False) if as_yaml else json.dumps(data), encoding="utf-8")
    return path


def dataset(videos, **over):
    return {"platform": "synthetic-platform", "format": "short-form", "niche_or_keyword": "synthetic keyword",
            "time_window": "2026-09-01/2026-09-30", "accessed_at": "2026-10-06T12:00:00Z",
            "source_route": "owner_supplied", "videos": videos, **over}


def account(name: str, baseline: list[int], candidates: dict[str, object]) -> list[dict]:
    rows = [{"video_id": f"{name}-base-{i}", "account": name, "views": v, "age_days": 20} for i, v in enumerate(baseline)]
    rows += [{"video_id": vid, "account": name, "views": views, "age_days": 10, "candidate_only": True}
             for vid, views in candidates.items()]
    return rows


class OutlierScoring(unittest.TestCase):
    def test_score_is_views_over_the_account_median_with_no_cutoff(self) -> None:
        videos = (account("acct-a", [100, 200, 300, 400, 500], {"a-hit": 3000})          # median 300 -> 10.0
                  + account("acct-b", [10_000, 20_000, 30_000, 40_000, 50_000], {"b-hit": 60_000})  # median 30000 -> 2.0
                  + account("acct-c", [50, 50, 60, 70, 70], {"c-hit": 300}))              # median 60 -> 5.0
        path = write("scores/dataset.json", dataset(videos), as_yaml=False)
        proc = tool("outlier-score", path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        out = json.loads(proc.stdout)
        self.assertEqual({a: r["baseline_median_views"] for a, r in out["accounts"].items()},
                         {"acct-a": 300, "acct-b": 30_000, "acct-c": 60})
        hits = {r["video_id"]: r for r in out["ranked"] if r["video_id"].endswith("-hit")}
        self.assertEqual({k: v["outlier_score"] for k, v in hits.items()}, {"a-hit": 10.0, "b-hit": 2.0, "c-hit": 5.0})
        # the small account's video outranks the large account's, despite 20x fewer raw views
        self.assertLess(hits["a-hit"]["rank"], hits["b-hit"]["rank"])
        self.assertTrue(out["threshold"].startswith("none"))
        self.assertNotIn("too_few_accounts", [w["flag"] for w in out["warnings"]])
        self.assertEqual(out["evidence_depth"], "metadata_only")

    def test_missing_values_stay_unavailable_and_flagged_videos_are_set_aside(self) -> None:
        videos = account("acct-a", [100, 200, 300, 400, 500], {"a-missing": None, "a-ok": 900})
        videos += account("acct-b", [10, 20, 30, 40, 50], {"b-boosted": 3000})
        videos[-1]["boosted"] = True
        videos.append({"video_id": "c-no-baseline", "account": "acct-c", "views": 5000, "candidate_only": True})
        out = json.loads(tool("outlier-score", write("scores/missing.json", dataset(videos), as_yaml=False)).stdout)
        unscored = {r["video_id"]: r for r in out["unscored"]}
        self.assertEqual(unscored["a-missing"]["views"], "Unavailable")
        self.assertEqual(unscored["a-missing"]["outlier_score"], "Unavailable")
        self.assertEqual(unscored["c-no-baseline"]["outlier_score"], "Unavailable")
        self.assertEqual(out["accounts"]["acct-c"]["baseline_median_views"], "Unavailable")
        self.assertEqual([r["video_id"] for r in out["excluded"]], ["b-boosted"])
        self.assertNotIn("b-boosted", [r["video_id"] for r in out["ranked"]])
        self.assertNotIn("a-missing", [r["video_id"] for r in out["ranked"]])

    def test_too_few_accounts_and_thin_baselines_are_flagged(self) -> None:
        videos = account("only-one", [100, 200, 300], {"hit": 5000})
        out = json.loads(tool("outlier-score", write("scores/few.json", dataset(videos), as_yaml=False)).stdout)
        flags = [w["flag"] for w in out["warnings"]]
        self.assertIn("too_few_accounts", flags)
        self.assertIn("thin_baseline", flags)

    def test_a_dataset_without_bounds_is_refused(self) -> None:
        data = dataset(account("a", [1, 2, 3, 4, 5], {"x": 9}))
        del data["accessed_at"]
        proc = tool("outlier-score", write("scores/unbounded.json", data, as_yaml=False))
        self.assertEqual(proc.returncode, 5)
        self.assertIn("accessed_at", proc.stderr)


def study(**over) -> dict:
    base = {
        "study_id": "OS-SYN-001", "platform": "synthetic-platform", "format": "short-form",
        "niche_or_keyword": "synthetic keyword", "query_terms": ["synthetic keyword"],
        "time_window": "2026-09-01/2026-09-30", "accessed_at": "2026-10-06T12:00:00Z",
        "source_route": "owner_supplied", "baseline_method": "median views of the same account's recent videos in the same format",
        "baseline_sample_size": 5, "candidates_reviewed": 12,
        "outliers_selected": [{"video_id": f"v{i}", "account": f"acct-{i}", "views": 1000 * i, "baseline_median_views": 100,
                               "outlier_score": 10.0 * i} for i in (1, 2, 3)],
        "contrast_set": [{"video_id": f"c{i}", "account": f"acct-{i}", "views": 100} for i in (1, 2, 3)],
        "ranking_method": "ranked by outlier score; the owner confirmed three to study", "exclusions": [],
        "min_accounts": 3, "too_few_accounts_note": None, "evidence_depth": "owner_supplied_reference",
        "limits": "Says nothing about why a video performed.", "valid_until": "2099-01-01",
    }
    base.update(over)
    return base


def blueprint(**over) -> dict:
    base = {
        "blueprint_id": "SB-SYN-001", "blueprint_version": 1, "study_id": "OS-SYN-001", "platform": "synthetic-platform",
        "format": "short-form", "evidence_depth": "owner_supplied_reference", "reference_count": 3,
        "duration_range": "21 to 34 seconds", "opening_structure": "first cut inside the first second in all three",
        "cut_rhythm": "18 to 26 cuts per minute", "shot_length_distribution": "median 2.1 to 3.0 seconds",
        "framing_and_reframes": None, "punch_ins_and_camera_moves": None,
        "caption_treatment": "large centred captions, two to four words per card", "on_screen_text": None,
        "b_roll_and_cutaways": None, "graphics_and_overlays": None, "transitions": None,
        "music_and_sound_design": None, "color_and_treatment": None, "pacing_curve": None,
        "pattern_interrupts": None, "ending_structure": None,
        "features_shared_with_contrast_set": ["caption_treatment"],
        "features_distinct_to_outliers": ["opening_structure"],
        "feature_evidence_tags": {"duration_range": "measured", "opening_structure": "observed", "cut_rhythm": "measured",
                                  "shot_length_distribution": "measured", "caption_treatment": "observed"},
        "analysis_tools_and_thresholds": {"cut_detection": "editor_tools.py cuts 1.0.0, scene 0.30, min shot 0.20"},
        "hyperframes_mapping": [{"feature": "opening_structure", "maps_to": "hard cut recipe", "tested": True}],
        "not_reproducible_with_bundled_tools": [], "do_not_copy": [{"reference": "v1", "items": ["on-screen wording", "music"]}],
        "confidence": "low: three references from three accounts", "valid_until": "2099-01-01",
    }
    base.update(over)
    return base


PROPOSAL = """# Style-match proposal

The outliers studied share these features, and the contrast set does not: an early first cut.

## What the evidence cannot show

It cannot show why these videos performed, and it cannot show that this style will produce any result.

## Options

### A. House style
### B. Outlier-matched
### C. Hybrid

## Recommendation

Recommend option C because the outlier caption look conflicts with the brand identity.

## How the result will be compared

Here is an edit in that style, and here is how the result will be compared after posting.
"""


class EvidenceRules(unittest.TestCase):
    def check(self, kind: str, name: str, data) -> tuple[int, dict]:
        path = write(f"rules/{name}", data) if not isinstance(data, str) else _state["ws"] / "projects" / "rules" / name
        if isinstance(data, str):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data, encoding="utf-8")
        proc = tool(f"check-{kind}", path)
        return proc.returncode, json.loads(proc.stdout)

    def test_a_sound_study_passes(self) -> None:
        code, out = self.check("study", "ok-study.yaml", study())
        self.assertEqual((code, out["problems"]), (0, []))

    def test_a_study_with_one_account_is_flagged(self) -> None:
        data = study()
        for o in data["outliers_selected"]:
            o["account"] = "acct-1"
        code, out = self.check("study", "one-account.yaml", data)
        self.assertEqual(code, 5)
        self.assertTrue(any("fewer than 3" in p for p in out["problems"]), out["problems"])
        data["too_few_accounts_note"] = "The niche has one active account. Confidence lowered."
        code, out = self.check("study", "one-account-noted.yaml", data)
        self.assertEqual(code, 0)
        self.assertTrue(any("too few accounts" in w for w in out["warnings"]))

    def test_a_raw_view_cutoff_no_contrast_set_and_blank_figures_fail(self) -> None:
        code, out = self.check("study", "cutoff.yaml", study(ranking_method="every video over 1,000,000 views"))
        self.assertTrue(any("raw view cutoff" in p for p in out["problems"]))
        code, out = self.check("study", "no-contrast.yaml", study(contrast_set=[]))
        self.assertTrue(any("contrast_set is empty" in p for p in out["problems"]))
        data = study()
        data["outliers_selected"][0]["views"] = None
        code, out = self.check("study", "blank.yaml", data)
        self.assertTrue(any("write Unavailable" in p for p in out["problems"]))

    def test_a_stale_study_and_a_stale_blueprint_are_flagged(self) -> None:
        yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
        code, out = self.check("study", "stale-study.yaml", study(valid_until=yesterday))
        self.assertTrue(out["stale"])
        code, out = self.check("blueprint", "stale-bp.yaml", blueprint(valid_until=yesterday))
        self.assertTrue(out["stale"])
        self.assertTrue(any("went stale" in w for w in out["warnings"]))

    def test_a_sound_blueprint_passes(self) -> None:
        code, out = self.check("blueprint", "ok-bp.yaml", blueprint())
        self.assertEqual((code, out["problems"]), (0, []))

    def test_a_metadata_only_study_cannot_produce_cut_or_caption_findings(self) -> None:
        code, out = self.check("blueprint", "meta-bp.yaml", blueprint(evidence_depth="metadata_only"))
        self.assertEqual(code, 5)
        for feature in ("cut_rhythm", "caption_treatment", "opening_structure", "shot_length_distribution"):
            self.assertTrue(any(p.startswith(f"{feature}: a metadata_only study") for p in out["problems"]), feature)
        honest = blueprint(evidence_depth="metadata_only", feature_evidence_tags={"duration_range": "measured"},
                           features_shared_with_contrast_set=[], features_distinct_to_outliers=[])
        for feature in ("opening_structure", "cut_rhythm", "shot_length_distribution", "caption_treatment"):
            honest[feature] = "not supported at this evidence depth"
        code, out = self.check("blueprint", "meta-honest.yaml", honest)
        self.assertEqual((code, out["problems"]), (0, []))

    def test_untagged_mistagged_and_promising_blueprints_fail(self) -> None:
        data = blueprint()
        del data["feature_evidence_tags"]["cut_rhythm"]
        code, out = self.check("blueprint", "untagged.yaml", data)
        self.assertTrue(any(p.startswith("cut_rhythm: no evidence tag") for p in out["problems"]))
        data = blueprint()
        data["feature_evidence_tags"]["caption_treatment"] = "measured"
        code, out = self.check("blueprint", "mistagged.yaml", data)
        self.assertTrue(any("no bundled tool measures it" in p for p in out["problems"]))
        code, out = self.check("blueprint", "no-dnc.yaml", blueprint(do_not_copy=[]))
        self.assertTrue(any("do_not_copy is empty" in p for p in out["problems"]))
        code, out = self.check("blueprint", "promise.yaml", blueprint(confidence="high: this style will go viral"))
        self.assertTrue(any("result or cause claim" in p for p in out["problems"]))

    def test_a_proposal_must_offer_three_options_and_promise_nothing(self) -> None:
        code, out = self.check("proposal", "ok.md", PROPOSAL)
        self.assertEqual((code, out["problems"]), (0, []))
        for bad in ("This style will get similar views.", "We guarantee more reach.", "Expect 3x more views.",
                    "The reason it went viral is the pacing."):
            code, out = self.check("proposal", "bad.md", PROPOSAL + "\n" + bad + "\n")
            self.assertEqual(code, 5, bad)
            self.assertTrue(any("result or cause claim" in p for p in out["problems"]), bad)
        code, out = self.check("proposal", "two-options.md", PROPOSAL.replace("### C. Hybrid", ""))
        self.assertEqual(code, 5)


class YamlSubset(unittest.TestCase):
    def test_the_standard_library_parser_reads_every_shipped_yaml_template_like_pyyaml(self) -> None:
        templates = sorted((H.REPO / "templates").glob("*.yaml"))
        self.assertGreaterEqual(len(templates), 15)
        for path in templates:
            subset = json.loads(tool("load", path, "--subset").stdout)
            self.assertEqual(subset, yaml.safe_load(path.read_text(encoding="utf-8")), path.name)

    def test_it_reads_nested_documents(self) -> None:
        data = blueprint()
        path = write("rules/nested.yaml", data)
        self.assertEqual(json.loads(tool("load", path, "--subset").stdout), data)


@unittest.skipUnless(H.have("ffmpeg") and H.have("ffprobe"), "FFmpeg not available: media tests not run")
class MediaMeasurement(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ws = _state["ws"]
        # A reference with known cut points: bars 0-2s, a red field 2-3.5s, a grid 3.5-7s, blue 7-8s.
        cls.ref = cls.ws / "references" / "known-cuts.mp4"
        H.ffmpeg("-f", "lavfi", "-i", "smptebars=s=640x360:r=30:d=2", "-f", "lavfi", "-i", "color=c=red:s=640x360:r=30:d=1.5",
                 "-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=3.5", "-f", "lavfi", "-i", "color=c=blue:s=640x360:r=30:d=1",
                 "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:duration=8",
                 "-filter_complex", "[0:v][1:v][2:v][3:v]concat=n=4:v=1:a=0[v]", "-map", "[v]", "-map", "4:a",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "14", "-pix_fmt", "yuv420p", "-c:a", "aac", cls.ref)
        cls.true_cuts = [2.0, 3.5, 7.0]

    def test_cut_detection_matches_known_cut_points_at_the_recorded_threshold(self) -> None:
        out = json.loads(tool("cuts", self.ref, "--threshold", "0.30", "--min-shot", "0.20").stdout)
        self.assertEqual(out["thresholds"], {"scene_threshold": 0.3, "min_shot_seconds": 0.2})
        self.assertEqual(out["evidence_tag"], "measured")
        self.assertEqual(out["cut_count"], 3)
        for got, want in zip(out["cut_times_seconds"], self.true_cuts):
            self.assertAlmostEqual(got, want, delta=0.05)
        self.assertAlmostEqual(out["time_to_first_cut_seconds"], 2.0, delta=0.05)
        self.assertIn("ffmpeg version", out["ffmpeg"])

    def test_shot_length_distribution_matches_ground_truth(self) -> None:
        out = json.loads(tool("cuts", self.ref).stdout)
        for got, want in zip(out["shot_lengths_seconds"], [2.0, 1.5, 3.5, 1.0]):
            self.assertAlmostEqual(got, want, delta=0.06)
        dist = out["shot_length_distribution"]
        self.assertEqual(dist["count"], 4)
        self.assertAlmostEqual(dist["mean"], 2.0, delta=0.03)
        self.assertAlmostEqual(dist["median"], 1.75, delta=0.06)
        self.assertAlmostEqual(dist["min"], 1.0, delta=0.06)
        self.assertAlmostEqual(dist["max"], 3.5, delta=0.06)

    def test_a_different_threshold_is_recorded_as_a_different_measurement(self) -> None:
        strict = json.loads(tool("cuts", self.ref, "--threshold", "0.99").stdout)
        self.assertEqual(strict["thresholds"]["scene_threshold"], 0.99)
        self.assertLess(strict["cut_count"], 3)

    def test_frame_sampling_schedule_is_recorded_and_repeatable(self) -> None:
        first = json.loads(tool("frames", self.ref, "--schedule", "short-form").stdout)
        second = json.loads(tool("frames", self.ref, "--schedule", "short-form").stdout)
        times = [f["time_seconds"] for f in first["frames"]]
        self.assertEqual(times, [f["time_seconds"] for f in second["frames"]])
        self.assertEqual(first["schedule_definition"], [[3.0, 0.25], [10.0, 0.5], [30.0, 1.0], [None, 2.0]])
        # denser in the opening seconds: 12 frames in the first 3 s, then every half second
        self.assertEqual(times[:13], [round(i * 0.25, 2) for i in range(12)] + [3.0])
        self.assertEqual(times[-1], 7.5)
        self.assertTrue(first["session_only"] and first["is_reference_material"])
        cleaned = json.loads(tool("session-clean").stdout)
        self.assertEqual(cleaned["files_removed"], len(times))

    def test_variable_frame_rate_is_flagged_and_handled_through_a_working_copy(self) -> None:
        src = self.ws / "footage" / "phone-vfr.mp4"
        H.ffmpeg("-f", "lavfi", "-i", "testsrc2=s=640x360:r=30:d=4", "-f", "lavfi", "-i", "sine=frequency=500:duration=4",
                 "-vf", "select='not(mod(n\\,3))+gt(n\\,60)',setpts=N/30/TB*(1+0.5*lt(N\\,20))", "-fps_mode", "vfr",
                 "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", src)
        before = H.sha256(src)
        info = json.loads(tool("probe", src).stdout)["files"][0]
        self.assertEqual(info["frame_rate_mode"], "variable", info)
        self.assertIn("variable_frame_rate", [f["flag"] for f in info["flags"]])
        self.assertTrue(info["needs_working_copy"])
        made = tool("working-copy", src, "--fps", "30")
        self.assertEqual(made.returncode, 0, made.stderr)
        record = json.loads(made.stdout)
        self.assertTrue(record["original_unchanged"])
        self.assertEqual(H.sha256(src), before)
        copy = Path(record["working_copy"])
        self.assertEqual(copy.parent.name, "working-copies")
        self.assertEqual(json.loads(tool("probe", copy).stdout)["files"][0]["frame_rate_mode"], "constant")
        self.assertIn("ffmpeg", record["command"][0])
        again = tool("working-copy", src, "--fps", "30")
        self.assertEqual(again.returncode, 4)       # never overwrites

    def test_a_rotated_phone_source_is_flagged_and_baked_into_a_working_copy(self) -> None:
        plain = self.ws / "footage" / "phone-plain.mp4"
        H.make_timecode_clip(plain, seconds=2)
        rotated = self.ws / "footage" / "phone-rotated.mp4"
        H.ffmpeg("-display_rotation", "90", "-i", plain, "-c", "copy", rotated)
        info = json.loads(tool("probe", rotated).stdout)["files"][0]
        self.assertIn("rotated", [f["flag"] for f in info["flags"]], info)
        self.assertEqual((info["width"], info["height"]), (640, 360))
        self.assertEqual((info["display_width"], info["display_height"]), (360, 640))
        record = json.loads(tool("working-copy", rotated).stdout)
        baked = record["working_copy_probe"]
        self.assertEqual((baked["width"], baked["height"], baked["rotation_degrees"]), (360, 640, 0))

    def test_a_source_with_no_audio_and_an_audio_only_source_are_flagged(self) -> None:
        silent = H.make_timecode_clip(self.ws / "footage" / "no-audio.mp4", seconds=2, audio=False)
        info = json.loads(tool("probe", silent).stdout)["files"][0]
        self.assertFalse(info["has_audio"])
        self.assertIn("no_audio", [f["flag"] for f in info["flags"]])
        profile = json.loads(tool("audio-profile", silent).stdout)
        self.assertEqual((profile["has_audio"], profile["integrated_lufs"]), (False, "Unavailable"))

    def test_a_source_whose_probe_fails_stops_the_edit(self) -> None:
        broken = self.ws / "footage" / "broken.mp4"
        broken.write_bytes(b"this is not a video file" * 40)
        proc = tool("probe", broken)
        self.assertEqual(proc.returncode, 5)
        out = json.loads(proc.stdout)
        self.assertEqual(out["status"], "probe failed")
        self.assertFalse(out["files"][0]["probe_ok"])
        self.assertIn("Never edit from a file whose probe failed", out["files"][0]["rule"])
        self.assertEqual(tool("working-copy", broken).returncode, 5)
        self.assertEqual(list((self.ws / "working-copies").glob("broken*")), [])

    def test_tools_refuse_paths_outside_the_workspace(self) -> None:
        outside = _state["base"] / "outside.mp4"
        H.make_timecode_clip(outside, seconds=1)
        for args in (("probe", outside), ("cuts", outside), ("frames", outside), ("working-copy", outside)):
            proc = tool(*args)
            self.assertEqual(proc.returncode, 4, args)
            self.assertIn("outside the approved workspace", proc.stderr)

    def test_a_reference_video_is_never_converted_or_sheeted(self) -> None:
        self.assertEqual(tool("working-copy", self.ref).returncode, 4)
        sheet = tool("contact-sheet", self.ref, "--out", self.ws / "projects" / "sheet.jpg")
        self.assertEqual(sheet.returncode, 4)
        self.assertFalse((self.ws / "projects" / "sheet.jpg").exists())

    def test_dead_air_ranges_come_from_word_timings(self) -> None:
        words = [{"text": "one", "start": 0.2, "end": 0.6}, {"text": "two", "start": 0.7, "end": 1.1},
                 {"text": "three", "start": 3.0, "end": 3.4}, {"text": "four", "start": 3.5, "end": 4.0}]
        path = write("deadair/words.json", {"words": words}, as_yaml=False)
        out = json.loads(tool("dead-air", path, "--min-gap", "0.6", "--pad", "0.1").stdout)
        self.assertEqual(out["status"], "proposal")
        self.assertEqual([(c["data-media-start"], c["data-duration"]) for c in out["clips"]], [(0.1, 1.1), (2.9, 1.2)])
        self.assertEqual(out["cuts"][0]["seconds_removed"], 1.7)
        self.assertEqual([c["data-start"] for c in out["clips"]], [0.0, 1.1])


if __name__ == "__main__":
    unittest.main(verbosity=2)
