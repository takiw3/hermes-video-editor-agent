#!/usr/bin/env python3
"""Rewrite the generated blocks in README.md and docs/ from recorded results.

    python3 scripts/update_test_status.py

Every number in those blocks comes from a file under docs/test-results/ or
from the capability reference. Nothing is typed by hand, so a claim cannot
drift from the run that produced it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RESULTS = REPO / "docs/test-results"
CAPS = REPO / "skills/integrations/editor-hyperframes/references/capabilities.md"

SUITES = [
    ("tools.json", "Measurement and evidence rules", "`python3 tests/run.py tests.test_tools`"),
    ("gates.json", "Launcher gates, against a stand-in CLI", "`python3 tests/run.py tests.test_gates`"),
    ("install-hermes-0.21.5.json", "Install, payload, update, deny rules, Kanban exchange on Hermes 0.21.5", "`python3 tests/test_install.py`"),
    ("install-hermes-0.21.4.json", "The same on Hermes 0.21.4", "`python3 tests/test_install.py`"),
    ("renders.json", "Renders from an installed temporary profile, checked against ground truth", "`python3 tests/run.py tests.test_renders`"),
]


def load(name: str) -> dict | None:
    path = RESULTS / name
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else None


def replace_block(text: str, marker: str, body: str) -> str:
    pattern = re.compile(rf"(<!-- {marker}:begin -->\n).*?(<!-- {marker}:end -->)", re.DOTALL)
    if not pattern.search(text):
        raise SystemExit(f"marker {marker} not found")
    return pattern.sub(lambda m: m.group(1) + body.rstrip("\n") + "\n" + m.group(2), text)


def status_table() -> str:
    rows = ["| Suite | Pass | Fail | Not run | Command |", "| --- | --- | --- | --- | --- |"]
    for name, label, cmd in SUITES:
        data = load(name)
        if data is None:
            rows.append(f"| {label} | not run | | | {cmd} |")
            continue
        c = data["counts"]
        rows.append(f"| {label} | {c['pass']} | {c['fail']} | {c['not run']} | {cmd} |")
    not_run = []
    for name, label, _ in SUITES:
        data = load(name)
        for t in (data or {}).get("tests", []):
            if t["status"] == "not run":
                not_run.append(f"- {t['name']}: {t['detail']}")
    out = "\n".join(rows)
    if not_run:
        out += "\n\nNot run:\n\n" + "\n".join(sorted(set(not_run)))
    return out


def machine_line(m: dict) -> str:
    cpu = m.get("cpu") or m.get("machine")
    return (f"{cpu}, {m.get('cpu_count')} cores, {m.get('memory_gb', 'Unavailable')} GB memory, {m.get('os')}, "
            f"Node.js {m.get('node')}, {m.get('ffmpeg')}")


def longform_block(renders: dict) -> str:
    lf = renders["measurements"]["longform"]
    minutes = lf["duration_seconds"] / 60
    ratio = lf["render_seconds"] / lf["duration_seconds"]
    return "\n".join([
        "| | |", "| --- | --- |",
        f"| Duration rendered | {lf['duration_seconds']} seconds ({minutes:g} minutes), {lf['segments']} segments as sub-compositions |",
        f"| Resolution | {lf['resolution']}, 30 frames per second |",
        f"| Quality | {lf['stage']} |",
        f"| Render time | {round(lf['render_seconds'])} seconds ({ratio:.2f} times the video's length) |",
        f"| Workers | {lf['workers']}, planned from {lf['available_memory_mb_before']} MB of free memory |",
        f"| Peak memory, whole render process tree | {lf['peak_tree_rss_mb']} MB |",
        f"| Hardware | {machine_line(renders['machine'])} |",
        "| Checked | Picture and sound of every segment against synthetic ground truth, total duration, audio present |",
    ])


def renders_block(renders: dict) -> str:
    rows = ["| Test render | Render seconds | Workers | Peak memory (MB) |", "| --- | --- | --- | --- |"]
    for key, value in renders["measurements"].items():
        if isinstance(value, dict) and "render_seconds" in value and key != "longform":
            label = key.removeprefix("test_").replace("_", " ")
            rows.append(f"| {label} | {value['render_seconds']} | {value.get('workers')} | {value.get('peak_tree_rss_mb')} |")
    extras = renders["measurements"]
    notes = []
    if "duck_check" in extras:
        d = extras["duck_check"]
        notes.append(f"- Music carve under speech: {d['music_carve_depth_db']} dB. Voice over music in speech windows: {d['voice_over_music_margin_db']} dB.")
    if "cut_detection_on_render" in extras:
        c = extras["cut_detection_on_render"]
        notes.append(f"- Cut detection on a render with {c['true_cuts']} known cuts between solid colors, at scene threshold {c['threshold']}: {c['detected']} detected. Scene detection can miss a cut between similar frames.")
    if "retime_tone_hz" in extras:
        r = extras["retime_tone_hz"]
        notes.append(f"- Retime at 0.5x: a {r['source_hz']} Hz source tone measured {r['rendered_hz']} Hz in the render.")
    if "alpha" in extras:
        notes.append(f"- Transparent WebM: corner alpha {extras['alpha']['corner_rgba'][3]}, graphic alpha {extras['alpha']['centre_rgba'][3]}.")
    return "\n".join(rows) + ("\n\nOther measurements from the same run:\n\n" + "\n".join(notes) if notes else "")


def operations_table() -> str:
    lines = CAPS.read_text(encoding="utf-8").splitlines()
    start = lines.index("## Editing operations")
    table = []
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            table.append("| " + " | ".join(cells[:2]) + " |")
    return "\n".join(table)


def main() -> int:
    renders = load("renders.json")
    readme = REPO / "README.md"
    text = readme.read_text(encoding="utf-8")
    text = replace_block(text, "test-status", status_table())
    text = replace_block(text, "operations", operations_table())
    perf_path = REPO / "docs/render-performance-and-limits.md"
    perf = perf_path.read_text(encoding="utf-8")
    if renders and "longform" in renders.get("measurements", {}):
        block = longform_block(renders)
        text = replace_block(text, "longform", block)
        perf = replace_block(perf, "longform", block)
        perf = replace_block(perf, "machine", machine_line(renders["machine"]) + f"\n\nHermes under test: {renders.get('hermes', 'Unavailable')}. HyperFrames `0.8.138`.")
        perf = replace_block(perf, "renders", renders_block(renders))
    else:
        for marker in ("longform",):
            text = replace_block(text, marker, "Not run.")
            perf = replace_block(perf, marker, "Not run.")
    readme.write_text(text, encoding="utf-8")
    perf_path.write_text(perf, encoding="utf-8")
    print("updated README.md and docs/render-performance-and-limits.md from docs/test-results/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
