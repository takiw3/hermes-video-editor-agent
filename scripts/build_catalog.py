#!/usr/bin/env python3
"""Build the effects catalog from the effect sources and their verification records.

    python3 scripts/build_catalog.py           # write catalog.yaml, docs/effects/catalog.md, README counts
    python3 scripts/build_catalog.py --check   # fail when any generated file is out of date

An effect is `verified` only when its verification.json says pass; `limited`
when it passed with a written limit. Everything else stays `implemented`.
The README count is the verified count, by family, with the date of the
newest record. Audio effects are counted separately.

The featured set (effects-library/featured.json) is hand-curated after a
full-size review. It must name exactly FEATURED_COUNT effects, each verified
and not limited; the build refuses anything else.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LIB = REPO / "skills/video-effects-core/effects-library"
CATALOG = LIB / "catalog.yaml"
DOC = REPO / "docs/effects/catalog.md"
FEATURED = LIB / "featured.json"
FEATURED_DOC = REPO / "docs/effects/featured.md"
FEATURED_COUNT = 50
README = REPO / "README.md"
VISUAL = ["looks-and-grades", "image-effects", "transitions", "camera-and-motion", "keying-and-subject",
          "overlays-and-generators", "text-and-title", "creator-composites"]
TARGETS = {"looks-and-grades": 25, "image-effects": 25, "transitions": 20, "camera-and-motion": 12,
           "keying-and-subject": 6, "overlays-and-generators": 10, "text-and-title": 8, "creator-composites": 10}
TITLES = {"looks-and-grades": "Looks and grades", "image-effects": "Image effects", "transitions": "Transitions",
          "camera-and-motion": "Camera and motion", "keying-and-subject": "Keying and subject",
          "overlays-and-generators": "Overlays and generators", "text-and-title": "Text and titles",
          "creator-composites": "Creator composites", "audio": "Audio"}
RELEASE_MIN = 101
FIELDS = ["effect_id", "display_name", "family", "kind", "description", "implementation_route", "hyperframes_feature",
          "source_files", "parameters", "applies_to", "needs_model", "needs_key_footage", "hdr_behavior", "deterministic",
          "seek_safe", "photosensitivity", "face_safe", "render_cost_multiplier", "reference_still", "verification_record",
          "provenance", "reference_id", "license", "status"]


def featured() -> dict:
    return json.loads(FEATURED.read_text(encoding="utf-8"))


def entries() -> list[dict]:
    picks = {f["effect_id"]: f["use_for"] for f in featured()["effects"]}
    rows = []
    for spec_path in sorted(LIB.glob("*/*/effect.json")):
        d = spec_path.parent
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        rec_path = d / "verification.json"
        rec = json.loads(rec_path.read_text(encoding="utf-8")) if rec_path.is_file() else None
        status = spec.get("status", "implemented")
        if status not in {"retired", "planned"}:
            status = "implemented"
            if rec and rec.get("result") == "pass":
                status = "limited" if rec.get("limited") or spec.get("status") == "limited" else "verified"
        rel = d.relative_to(REPO).as_posix()
        entry = {k: spec.get(k) for k in FIELDS}
        entry["source_files"] = sorted(f"{rel}/{p.name}" for p in d.iterdir()
                                       if p.name not in {"verification.json", "reference.jpg", "contact-sheet.jpg"})
        entry["status"] = status
        entry["verification_record"] = f"{rel}/verification.json" if rec else None
        entry["reference_still"] = f"{rel}/reference.jpg" if (d / "reference.jpg").is_file() else None
        if rec:
            entry["render_cost_multiplier"] = rec.get("render_cost_multiplier")
            entry["photosensitivity"] = (rec.get("photosensitivity") or {}).get("result") or entry["photosensitivity"]
            entry["verified_at"] = rec.get("verified_at")
            entry["limits"] = rec.get("limited") or []
        entry["featured"] = entry["effect_id"] in picks
        entry["featured_use"] = picks.get(entry["effect_id"])
        rows.append(entry)
    return rows


def counts(rows: list[dict]) -> dict:
    by = {f: 0 for f in VISUAL}
    limited = {f: 0 for f in VISUAL}
    audio = 0
    for r in rows:
        if r["family"] == "audio":
            audio += r["status"] == "verified"
        elif r["status"] == "verified":
            by[r["family"]] += 1
        elif r["status"] == "limited":
            limited[r["family"]] += 1
    dates = sorted(r.get("verified_at") or "" for r in rows if r["status"] in {"verified", "limited"})
    return {"by_family": by, "limited_by_family": limited, "visual_verified": sum(by.values()),
            "visual_limited": sum(limited.values()), "audio_verified": audio, "latest": (dates[-1][:10] if dates else None),
            "featured": sum(1 for r in rows if r["featured"]), "total_entries": len(rows)}


def featured_problems(rows: list[dict]) -> list[str]:
    ids = [f["effect_id"] for f in featured()["effects"]]
    by_id = {r["effect_id"]: r for r in rows}
    problems = []
    if len(ids) != FEATURED_COUNT:
        problems.append(f"featured.json names {len(ids)} effects, not {FEATURED_COUNT}")
    if len(set(ids)) != len(ids):
        problems.append("featured.json names an effect twice")
    for eid in ids:
        r = by_id.get(eid)
        if r is None:
            problems.append(f"featured effect {eid} does not exist")
        elif r["status"] != "verified":
            problems.append(f"featured effect {eid} is {r['status']}, not verified")
        elif r["family"] == "audio":
            problems.append(f"featured effect {eid} is audio; the featured set is picture effects")
    return problems


def catalog_text(rows: list[dict], c: dict) -> str:
    head = ("# Generated by scripts/build_catalog.py from each effect's effect.json and verification.json.\n"
            "# Do not edit by hand. The body is JSON, which is valid YAML.\n")
    return head + json.dumps({"version": 1, "counts": c, "effects": rows}, indent=1) + "\n"


def doc_text(rows: list[dict], c: dict) -> str:
    out = ["# Effects catalog", "",
           "Generated by `scripts/build_catalog.py`. Every number here comes from a verification record. An effect is "
           "**verified** when it passed all 12 checks of the gate in an installed profile; **limited** when it passed "
           "with a written limit; **implemented** when it has no passing record yet. See [verification.md](verification.md).", "",
           f"Verified picture effects: **{c['visual_verified']}** (plus {c['visual_limited']} limited). Verified audio effects: "
           f"**{c['audio_verified']}**, counted separately. Newest record: {c['latest'] or 'none'}.", ""]
    out += [f"Featured: **{c['featured']}**, reviewed at full size. See [featured.md](featured.md).", ""]
    for fam in VISUAL + ["audio"]:
        fam_rows = [r for r in rows if r["family"] == fam]
        if not fam_rows:
            continue
        out += [f"## {TITLES[fam]}", "", "| Effect | Route | Status | Featured | Cost | Flash check | Provenance |",
                "| --- | --- | --- | --- | --- | --- | --- |"]
        for r in fam_rows:
            cost = r.get("render_cost_multiplier")
            out.append(f"| `{r['effect_id']}` {r['display_name']} | {r['implementation_route']} | {r['status']} | "
                       f"{'yes' if r['featured'] else ''} | {cost if cost is not None else 'n/a'} | {r.get('photosensitivity') or 'n/a'} | "
                       f"{r['provenance']}{' ' + r['reference_id'] if r.get('reference_id') else ''} |")
        out.append("")
    return "\n".join(out)


def featured_text(rows: list[dict]) -> str:
    meta = featured()
    out = ["# Featured effects", "",
           "Generated by `scripts/build_catalog.py` from `skills/video-effects-core/effects-library/featured.json`, which is "
           "edited by hand. The editor reaches for these first: `fx.py list --featured`.", "",
           f"Reviewed {meta['reviewed_at']}. {meta['method']}", "",
           "Every featured effect is verified (all 12 checks) and not limited. The build fails otherwise. A `warn` in the "
           "flash check column means fast motion flipped high-contrast edges in a small area, with no flash at the default "
           "setting; the flash check still runs on every real render.", ""]
    for fam in VISUAL:
        fam_rows = [r for r in rows if r["family"] == fam and r["featured"]]
        if not fam_rows:
            continue
        out += [f"## {TITLES[fam]} ({len(fam_rows)})", "", "| Effect | Use it for | Flash check |", "| --- | --- | --- |"]
        out += [f"| `{r['effect_id']}` {r['display_name']} | {r['featured_use']} | {r.get('photosensitivity') or 'n/a'} |"
                for r in fam_rows]
        out.append("")
    return "\n".join(out)


def readme_block(c: dict) -> str:
    rows = ["| Family | Verified | Limited | Target |", "| --- | --- | --- | --- |"]
    for fam in VISUAL:
        rows.append(f"| {TITLES[fam]} | {c['by_family'][fam]} | {c['limited_by_family'][fam]} | {TARGETS[fam]} or more |")
    rows.append(f"| **Picture effects** | **{c['visual_verified']}** | {c['visual_limited']} | more than 100 |")
    rows.append(f"| Audio (separate) | {c['audio_verified']} | 0 | none set |")
    status = ("full release" if c["visual_verified"] >= RELEASE_MIN
              else f"limited release: {c['visual_verified']} verified picture effects, fewer than {RELEASE_MIN}")
    return (f"Verified on {c['latest'] or 'no date'}. Release status: **{status}**.\n\n" + "\n".join(rows)
            + f"\n\nFeatured: **{c['featured']}** of these were reviewed at 1080x1920 on real vertical talking-head footage "
              "and are the editor's first picks. See [docs/effects/featured.md](docs/effects/featured.md).")


def replace_marker(text: str, name: str, body: str) -> str:
    # The block may be empty (begin and end on adjacent lines) before the first build.
    pattern = re.compile(rf"(<!-- {name}:begin -->\n)(?:.*?\n)?(<!-- {name}:end -->)", re.S)
    if not pattern.search(text):
        raise SystemExit(f"README has no <!-- {name}:begin --> block")
    return pattern.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)


def main() -> int:
    check = "--check" in sys.argv
    rows = entries()
    problems = featured_problems(rows)
    for problem in problems:
        print(f"  FAIL  {problem}")
    if problems:
        return 1
    c = counts(rows)
    outputs = {CATALOG: catalog_text(rows, c), DOC: doc_text(rows, c), FEATURED_DOC: featured_text(rows)}
    readme = README.read_text(encoding="utf-8")
    outputs[README] = replace_marker(readme, "effect-counts", readme_block(c))
    stale = [p for p, text in outputs.items() if not p.is_file() or p.read_text(encoding="utf-8") != text]
    if check:
        for p in stale:
            print(f"  FAIL  out of date: {p.relative_to(REPO)} (run scripts/build_catalog.py)")
        print(f"catalog: {c['visual_verified']} verified picture effects, {c['visual_limited']} limited, "
              f"{c['audio_verified']} audio, {len(stale)} stale files")
        return 1 if stale else 0
    for p, text in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(json.dumps(c, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
