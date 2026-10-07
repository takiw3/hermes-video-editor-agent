#!/usr/bin/env python3
"""Re-check the upstream facts this integration depends on.

Reads the exact upstream copy under vendor/upstream/hyperframes/ and the
regression fixture in tests/fixtures/. Fails when an observation the patches
rely on no longer holds, so an upstream change is noticed during an update
instead of after it. No network access.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
UP = REPO / "vendor/upstream/hyperframes"
FIXTURE = REPO / "tests/fixtures/compat-baseline-2026-10-06.yaml"


def text(rel: str) -> str:
    return (UP / rel).read_text(encoding="utf-8")


def all_md() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted((UP / "skills").rglob("*.md")))


def main() -> int:
    fixture = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    docs = all_md()
    router = text("skills/hyperframes/SKILL.md")
    plugin_doc = text("skills/hyperframes/references/plugin-installation.md")
    lifecycle = text("skills/hyperframes/references/skill-lifecycle.md")
    recipes = text("skills/hyperframes-core/references/creator-editing-recipes.md")
    render_ref = text("skills/hyperframes-cli/references/preview-render.md")
    credits = text("CREDITS.md")

    def frontmatter_keys() -> set:
        keys = set()
        for skill_md in (UP / "skills").glob("*/SKILL.md"):
            keys |= set(yaml.safe_load(skill_md.read_text(encoding="utf-8").split("\n---\n", 1)[0][4:]).keys())
        return keys

    def internal_marked() -> bool:
        found = list((UP / ".claude/skills").glob("*/SKILL.md"))
        return bool(found) and all(
            (yaml.safe_load(p.read_text(encoding="utf-8").split("\n---\n", 1)[0][4:]).get("metadata") or {}).get("internal") is True
            for p in found)

    checks = {
        1: frontmatter_keys() == {"name", "description"},
        2: bool(re.search(r"\]\(\.\./[a-z-]+/", docs)),
        3: "`/hyperframes-core`" in router and "`/media-use`" in router,
        4: "skills update <workflow-name>" in router
           and "keep this skill fresh" in text("skills/talking-head-recut/SKILL.md"),
        6: "HYPERFRAMES_SKIP_SKILLS=1" in lifecycle and "temporarily ignored" in lifecycle,
        7: "two levels above the loaded `SKILL.md`" in plugin_doc and "plugin-cli.mjs" in plugin_doc,
        9: len(re.findall(r"npx hyperframes", docs)) >= 400,
        11: "GSAP Standard License" in credits and len(list((UP / "skills").rglob("*.mp3"))) == 19,
        12: internal_marked(),
        15: all(a in recipes for a in ("data-start", "data-duration", "data-media-start", "data-track-index", "data-has-audio")),
        16: "media_missing_id" in recipes and "silent" in recipes,
        17: all(flag in render_ref for flag in ("--fps", "--quality", "--format", "--resolution", "--workers",
                                                "--variables", "--strict"))
            and "--batch" in text("skills/hyperframes-cli/references/compare-and-batch.md"),
        18: bool(re.search(r"~?256\s?MB", render_ref)),
        20: "parakeet" in credits.lower() and "CC-BY-4.0" in credits,
        22: bool(re.search(r"(?i)single[- ]subject|one (?:speaker|subject)|talking[- ]head", text("skills/embedded-captions/SKILL.md"))),
        23: all(k in docs for k in ("HEYGEN_API_KEY", "GEMINI_API_KEY", "ELEVENLABS_API_KEY")),
        25: all(f"hyperframes {c}" in docs for c in ("publish", "cloud", "lambda", "cloudrun")),
        26: "history end" in docs,
    }
    failed = 0
    for obs in fixture["observations"]:
        if not obs.get("checkable"):
            continue
        ok = checks.get(obs["id"])
        if ok is None:
            print(f"  FAIL  observation {obs['id']} is marked checkable but has no check")
            failed += 1
        elif ok != obs["held_at_pin"]:
            print(f"  FAIL  observation {obs['id']} changed: {obs['claim']}")
            failed += 1
    plugin = yaml.safe_load(text("plugin.json"))
    if plugin["version"] != fixture["tested"]["hyperframes"]["version"]:
        print("  FAIL  fixture `tested` version does not match the vendored plugin.json; update the fixture with the pin")
        failed += 1
    checked = sum(1 for o in fixture["observations"] if o.get("checkable"))
    print(f"upstream contract: {checked} observations re-checked, {failed} changed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
