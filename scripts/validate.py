#!/usr/bin/env python3
"""Repository validation. Run before every commit and in CI.

    python3 scripts/validate.py              # working tree
    python3 scripts/validate.py --history    # also scan Git history for secrets
    python3 scripts/validate.py --history --only-history

Standard library plus PyYAML. No network access. Exit 1 on any failure.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
SELF = {"scripts/validate.py", "scripts/run_evals.py"}
GITHUB = "github.com/takiw3/hermes-video-editor-agent"
PROFILE = "video-editor"
WRAPPER = "skills/integrations/editor-hyperframes"

CORE_SKILLS = """edit-intake-and-routing editor-and-brand-onboarding footage-ingest-and-inventory transcript-and-selects
outlier-video-research edit-style-analysis style-match-proposal style-library-maintenance paper-edit-and-decision-list
short-form-editing long-form-editing long-to-short-clipping caption-design-and-timing motion-graphics-and-overlays
b-roll-and-visual-coverage audio-cleanup-and-mix color-and-media-treatment reframe-and-multi-format-export
render-and-export edit-quality-review revision-and-version-management asset-rights-and-consent-check
edit-performance-feedback cross-team-edit-handoffs weekly-edit-review""".split()
EFFECT_SKILLS = """effects-catalog-and-selection effect-preview-and-contact-sheets effect-application-and-animation
effect-stacking-and-recipes looks-and-grades image-effects transitions camera-and-motion-effects keying-and-subject-effects
overlays-and-generators text-and-title-effects creator-composite-effects audio-effects effect-performance-budget
photosensitivity-and-accessibility-check effect-authoring-and-verification reference-editor-study""".split()
EFFECTS = "skills/video-effects-core"
VENDORED_SKILLS = """hyperframes hyperframes-core hyperframes-animation hyperframes-keyframes hyperframes-creative
hyperframes-cli hyperframes-audio hyperframes-registry hyperframes-studio media-use talking-head-recut
embedded-captions motion-graphics faceless-explainer general-video captions-overlay""".split()
NOT_BUNDLED = ["music-to-video", "product-launch-video", "pr-to-video", "remotion-to-hyperframes", "slideshow", "figma",
               "motion-doctrine", "cut-the-curve", "seam-craft", "changelog-video", "oversized-cursor"]
TEMPLATES = """editor-profile.md brand-and-visual-identity.md footage-inventory.yaml transcript-selects.yaml
outlier-study.yaml style-blueprint.yaml style-match-proposal.md style-decision.yaml paper-edit.md
edit-decision-list.yaml caption-style.yaml overlay-plan.yaml audio-plan.yaml export-preset.yaml render-receipt.yaml
quality-checklist.md revision-request.yaml asset-rights-register.yaml approval-request.yaml edit-task.yaml
edit-result.yaml review-request.yaml report-template.md reference-style-notes.yaml effect-plan.yaml effect-recipe.yaml
effect-verification-record.yaml""".split()
DOCS = """architecture.md hyperframes-setup.md hyperframes-integration.md outlier-research-and-style-matching.md
research-sources-and-platform-terms.md permissions-and-security.md editor-onboarding.md
short-form-and-long-form-workflows.md render-performance-and-limits.md media-rights-and-consent.md
team-integration.md privacy-and-retention.md updating-vendored-code.md evaluations.md effects/catalog.md
effects/reference-study.md effects/clean-room-process.md effects/verification.md effects/performance.md
concat-safety-review.md photosensitivity-and-accessibility.md""".split()
FACTS = f"{WRAPPER}/references/platform-facts.yaml"
REQUIRED_FILES = [
    "distribution.yaml", "SOUL.md", "config.yaml", "profile.yaml", "README.md", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", ".gitignore",
    ".github/workflows/ci.yml", "vendor/hyperframes.lock.yaml", "vendor/upstream/hyperframes/LICENSE",
    "skills/hyperframes-video/LICENSE", "skills/hyperframes-video/plugin.json",
    f"{WRAPPER}/SKILL.md", f"{WRAPPER}/scripts/hf.py", f"{WRAPPER}/scripts/editor_tools.py",
    f"{WRAPPER}/toolchain/package-lock.json", f"{WRAPPER}/toolchain/pin.json",
    f"{WRAPPER}/references/capabilities.md", f"{WRAPPER}/references/commands.md",
    f"{WRAPPER}/references/workspace-and-gates.md", f"{WRAPPER}/references/upstream-facts.md", FACTS,
    "tests/fixtures/compat-baseline-2026-10-06.yaml",
    "docs/test-results/tools.json", "docs/test-results/gates.json", "docs/test-results/renders.json",
    "docs/test-results/install-hermes-0.21.4.json", "docs/test-results/install-hermes-0.22.5.json", "docs/test-results/effects.json", "docs/test-results/effects.tests.json",
    f"{EFFECTS}/effects-library/catalog.yaml", f"{EFFECTS}/effects-library/runtime/fx-runtime.js",
    f"{EFFECTS}/effects-library/scripts/fx.py", "scripts/copy_check.py", "scripts/build_catalog.py",
    "scripts/verify_effects.py", "tests/fixtures/concat-fingerprints.json", "tests/test_effects.py",
] + [f"templates/{t}" for t in TEMPLATES] + [f"docs/{d}" for d in DOCS]
SKILL_SECTIONS = ["## When to use", "## When not to use", "## Inputs", "## Missing information",
                  "## Source handling", "## Procedure", "## Output contract", "## Checks before completion",
                  "## Permission boundaries", "## Blocked and failure behavior", "## Templates", "## Example"]
GITIGNORE_REQUIRED = [".env", "auth.json", "node_modules/", "memories/", "sessions/", "logs/", "local/",
                      "*.db", "renders/", "footage/", "references/", "working-copies/", "*.mp4", "*.mov", "*.onnx"]

SECRET_PATTERNS = {
    "private key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"),
    "AWS access key id": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    "GitHub token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "Slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "Anthropic or OpenAI key": re.compile(r"\bsk-(?:ant-|proj-)?[A-Za-z0-9_\-]{32,}\b"),
    "ElevenLabs or generic sk_ key": re.compile(r"\bsk_[a-f0-9]{40,}\b"),
    "Meta access token": re.compile(r"\bEAA[A-Za-z0-9]{40,}\b"),
    "JWT": re.compile(r"\beyJ[A-Za-z0-9_-]{15,}\.eyJ[A-Za-z0-9_-]{15,}\.[A-Za-z0-9_-]{10,}\b"),
    "assigned secret": re.compile(
        r"(?i)\b(?:api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|password)\b\s*[:=]\s*"
        r"[\"'][A-Za-z0-9_\-/+=]{24,}[\"']"),
}
# Upstream ships one public analytics client key. It is not a credential, and
# the launcher disables the telemetry that would use it.
SECRET_ALLOW = [("media-use/scripts/lib/telemetry.mjs", "phc_")]
FORBIDDEN_NAMES = {".env", "auth.json", "state.db", "kanban.db", "engine.json", "footage-manifest.json",
                   "reference-hashes.json", "render-measurements.json", "google_token.json", "mcp_tokens.json",
                   "credentials", "style-decision.yaml"}
FORBIDDEN_SUFFIXES = {".db", ".db-wal", ".db-shm", ".pem", ".p12", ".key", ".mp4", ".mov", ".mkv", ".webm",
                      ".wav", ".m4a", ".onnx", ".gguf", ".safetensors", ".sqlite", ".csv", ".xlsx", ".srt", ".vtt"}
FORBIDDEN_DIRS = {"node_modules", "memories", "sessions", "logs", "local", "renders", "receipts", "snapshots", "footage",
                  "working-copies", "style-library", "checkpoints", "cache", ".cache", "chrome", "browser_screenshots",
                  ".video-editor"}
MP3_ALLOWED_UNDER = ("skills/hyperframes-video/skills/media-use/audio/assets/sfx/",
                     "vendor/upstream/hyperframes/skills/media-use/audio/assets/sfx/")
COMMUNITY = [re.compile(r"skool\.com", re.I), re.compile(r"agentic ai academy", re.I), re.compile(r"\$97\b")]
KNOWN_HF_ENV = {"HYPERFRAMES_SKIP_SKILLS", "HYPERFRAMES_NO_UPDATE_CHECK", "HYPERFRAMES_NO_AUTO_INSTALL",
                "HYPERFRAMES_NO_TELEMETRY", "HYPERFRAMES_PREVIEW_HOST", "HYPERFRAMES_SKILL_PKG_VERSION",
                "HYPERFRAMES_PLUGIN_VERSION", "HYPERFRAMES_BROWSER_PATH", "HYPERFRAMES_API_KEY",
                "HYPERFRAMES_SKILL_NODE_MODULES"}
# Composition attributes the pinned release documents in the bundled skills.
# A custom skill or template may name these and no others.
KNOWN_DATA_ATTRS = {"data-start", "data-duration", "data-media-start", "data-track-index", "data-playback-rate",
                    "data-has-audio", "data-automation", "data-composition-id", "data-composition-src",
                    "data-composition-variables", "data-variable-values", "data-color-grading", "data-width",
                    "data-height", "data-var-src", "data-var-text", "data-volume", "data-vfx-chain", "data-fx-chain",
                    "data-no-capture"}
# Statements this profile must never make. Each is checked in runtime files,
# examples, and docs, and skipped where the sentence is a negation or a rule
# quoting the forbidden request.
PROMISES = {
    "result promised from a style match": re.compile(
        r"(?i)\b(?:will|is going to|guaranteed to) (?:get|drive|deliver|produce|generate|boost|double|triple|increase|lift|improve|outperform)\b[^.\n]{0,60}\b(?:views|reach|followers|revenue|engagement|retention|performance)\b"),
    "virality claim": re.compile(r"(?i)\b(?:will|guaranteed to|sure to|proven to) go viral\b"),
    "guarantee": re.compile(r"(?i)\bwe guarantee\b|\bguaranteed (?:views|results|growth|reach)\b"),
    "cause stated as fact": re.compile(r"(?i)\b(?:went viral|performed|blew up) because (?:of )?(?:the|its|their) (?:edit|cut|cuts|captions|pacing|hook)\b"),
    "ranking claim stated as fact": re.compile(r"(?i)\balgorithm (?:prefers|rewards|favou?rs|loves|prioriti[sz]es|pushes)\b"),
}
NEGATION = re.compile(r"(?i)\b(?:no|not|never|cannot|can't|won't|don't|doesn't|decline[sd]?|refus\w+|without|nothing|whether|asked|asks|request\w*|promise[sd]? (?:or|nothing)|fail[s]?|must not|if)\b")
FIXED_THRESHOLD = re.compile(
    r"(?i)\ban outlier is (?:any|a) video (?:with|over|above)\b|\boutliers? (?:are|is) (?:videos? )?(?:with |over |above )?(?:more than |at least )?[\d,.]+ ?(?:k|m|million|thousand|x)?\b(?! account)")
SPEC_NUMBER = re.compile(
    r"(?i)\b\d+(?:\.\d+)?\s?(?:GB|MB|KB|Mbps|Kbps|fps|frames per second|minutes?|seconds?|pixels|px|LUFS)\b|\b\d{3,4}\s?(?:x|by)\s?\d{3,4}\b")
PLATFORM_WORD = re.compile(r"(?i)\b(instagram|reels?|tiktok|youtube|shorts|linkedin|facebook)\b")
VIDEO_DOWNLOADERS = ["yt-dlp", "youtube-dl", "gallery-dl", "instaloader", "you-get", "streamlink"]

errors: list[str] = []
passed = 0


def check(cond: bool, label: str, detail: str = "") -> bool:
    global passed
    if cond:
        passed += 1
    else:
        errors.append(label + (f": {detail}" if detail else ""))
    return bool(cond)


def tracked_files() -> list[Path]:
    """Files Git would commit: tracked plus untracked-but-not-ignored."""
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files", "-co", "--exclude-standard", "-z"],
                             capture_output=True, check=True).stdout.decode()
        files = [REPO / p for p in out.split("\0") if p]
        if files:
            return [f for f in files if f.is_file() or f.is_symlink()]
    except Exception:
        pass
    return [p for p in REPO.rglob("*") if (p.is_file() or p.is_symlink()) and ".git" not in p.parts]


def rel(path: Path) -> str:
    return path.relative_to(REPO).as_posix()


def read(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def is_vendored(r: str) -> bool:
    return r.startswith(("vendor/upstream/", "skills/hyperframes-video/")) or r == "vendor/hyperframes.lock.yaml"


def frontmatter(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    try:
        return yaml.safe_load(text[4:text.index("\n---\n", 4)])
    except Exception:
        return None


BASE64_BLOB = re.compile(r"base64,[A-Za-z0-9+/=]{200,}")


def scan_secrets(text: str, where: str) -> list[str]:
    hits = []
    text = BASE64_BLOB.sub("base64,", text)
    for label, pattern in SECRET_PATTERNS.items():
        for m in pattern.finditer(text):
            if any(where.endswith(f) and m.group(0).startswith(p) for f, p in SECRET_ALLOW):
                continue
            hits.append(f"{label} in {where}")
            break
    return hits


def claim_lines(text: str):
    """Lines outside fenced code, with the two lines above for negation context."""
    lines, fenced = text.splitlines(), False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            yield line, " ".join(lines[max(0, i - 1):i + 1])


def validate_tree() -> None:
    files = tracked_files()
    rels = {rel(f) for f in files}

    for name in REQUIRED_FILES:
        check(name in rels, f"required file present: {name}")

    for f in files:
        r = rel(f)
        if f.suffix in {".yaml", ".yml"}:
            try:
                yaml.safe_load(f.read_text(encoding="utf-8"))
                check(True, "")
            except Exception as exc:
                check(False, f"invalid YAML: {r}", str(exc)[:120])
        elif f.suffix == ".json" and not is_vendored(r):
            try:
                json.loads(f.read_text(encoding="utf-8"))
                check(True, "")
            except Exception as exc:
                check(False, f"invalid JSON: {r}", str(exc)[:120])

    # symlinks, LFS pointers, forbidden files
    for f in files:
        r = rel(f)
        check(not f.is_symlink(), f"no symlink: {r}")
        if f.is_file() and f.stat().st_size < 400:
            check(not f.read_bytes().startswith(b"version https://git-lfs.github.com/spec/"), f"no Git LFS pointer: {r}")
        parts = Path(r).parts
        if not r.startswith("docs/test-results/"):
            check(not (set(parts[:-1]) & FORBIDDEN_DIRS),
                  f"no runtime, user-state, footage, reference, or render directory committed: {r}")
        check(f.name not in FORBIDDEN_NAMES or r == "templates/style-decision.yaml",
              f"no credential, state, or owner decision file committed: {r}")
        if f.suffix.lower() in FORBIDDEN_SUFFIXES:
            check(False, f"no database, key, footage, reference video, render, transcript, model, or export committed: {r}")
        if f.suffix.lower() == ".mp3":
            check(r.startswith(MP3_ALLOWED_UNDER), f"audio outside the licensed upstream sfx set: {r}")
        if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
            still = r.startswith(f"{EFFECTS}/effects-library/") and f.name in {"reference.jpg", "contact-sheet.jpg"}
            check(is_vendored(r) or still, f"image outside the vendored material and the effect stills (a sampled frame or render?): {r}")
    check(not (REPO / "references").exists() and not (REPO / "footage").exists(), "no footage or reference folder at the repository root")

    for f in files:
        r = rel(f)
        if r in SELF:
            continue
        text = read(f)
        if text is None:
            continue
        for hit in scan_secrets(text, r):
            check(False, hit)
    check(True, "secret scan complete")

    gi = (REPO / ".gitignore").read_text(encoding="utf-8") if (REPO / ".gitignore").is_file() else ""
    for entry in GITIGNORE_REQUIRED:
        check(any(line.strip() == entry for line in gi.splitlines()), f".gitignore lists {entry}")

    # manifest
    m = yaml.safe_load((REPO / "distribution.yaml").read_text(encoding="utf-8"))
    check(m.get("name") == PROFILE and str(m.get("version")) == "1.1.0" and m.get("license") == "MIT",
          "manifest name, version, license")
    check(not m.get("env_requires"), "manifest requires no environment variable")
    check("skills" not in m["distribution_owned"], "manifest never owns the whole skills directory")
    for owned in m["distribution_owned"]:
        check((REPO / owned).exists(), f"owned path exists: {owned}")
    check(not (REPO / "cron").exists(), "no cron jobs ship")
    check(not (REPO / "mcp.json").exists(), "no MCP server configuration ships")

    # skills
    names: dict[str, str] = {}
    for skill_md in sorted((REPO / "skills").rglob("SKILL.md")):
        r = rel(skill_md)
        fm = frontmatter(skill_md)
        if not check(fm is not None, f"frontmatter starts at byte zero and parses: {r}"):
            continue
        name = fm.get("name", "")
        check(bool(re.fullmatch(r"[a-z0-9][a-z0-9-]{1,62}", name)), f"skill name is lowercase: {r}")
        check(name == skill_md.parent.name, f"skill name equals folder: {r}")
        check(name not in names, f"duplicate skill name {name}", f"{r} and {names.get(name)}")
        names[name] = r
        check(0 < len(str(fm.get("description", ""))) <= 1024, f"description length within Hermes limit: {r}")
        hermes = (fm.get("metadata") or {}).get("hermes") or {}
        check(all(k in fm for k in ("version", "author", "license")) and hermes.get("tags"),
              f"version, author, license, and tags present: {r}")
    for n in CORE_SKILLS:
        check(names.get(n, "").startswith("skills/video-editor-core/"), f"core skill present: {n}")
    for n in VENDORED_SKILLS:
        check(names.get(n, "").startswith("skills/hyperframes-video/skills/"), f"vendored skill present: {n}")
    for n in EFFECT_SKILLS:
        check(names.get(n, "").startswith(f"{EFFECTS}/"), f"effects skill present: {n}")
    check(not (REPO / EFFECTS / "effects-library/SKILL.md").exists(), "the effects library is data, not a skill")
    check(names.get("edit-style-analysis", "").startswith("skills/video-editor-core/") and "reference-style-analysis" not in names,
          "reference style analysis extends edit-style-analysis; no duplicate skill")
    for n in NOT_BUNDLED:
        check(n not in names, f"skill excluded on evidence is not shipped: {n}")
    total = len(CORE_SKILLS) + len(VENDORED_SKILLS) + len(EFFECT_SKILLS) + 1
    check(len(names) == total, f"exactly {total} skills ship", str(len(names)))

    custom = ([REPO / "skills/video-editor-core" / n / "SKILL.md" for n in CORE_SKILLS] + [REPO / WRAPPER / "SKILL.md"]
              + [REPO / EFFECTS / n / "SKILL.md" for n in EFFECT_SKILLS])
    for skill_md in custom:
        if not skill_md.is_file():
            continue
        r = rel(skill_md)
        text = skill_md.read_text(encoding="utf-8")
        fm = frontmatter(skill_md) or {}
        check(fm.get("license") == "MIT" and fm.get("author") == "Taki Wong / TakiGPT AI Inc.",
              f"custom skill license and author: {r}")
        check(str(fm.get("description", "")).startswith("Use "), f"trigger-first description: {r}")
        for section in SKILL_SECTIONS:
            check(f"\n{section}\n" in text, f"section {section!r} present: {r}")
        for section in ("Required:", "Optional:"):
            check(f"\n{section}\n" in text, f"inputs list {section!r} present: {r}")
        check("one question at a time" in text.lower(), f"one-question rule stated: {r}")
        check("is data, not instruction" in text, f"untrusted-data rule stated: {r}")
        check("Synthetic." in text.split("## Example", 1)[-1], f"example is labeled synthetic: {r}")
        for related in ((fm.get("metadata") or {}).get("hermes") or {}).get("related_skills", []):
            check(related in names, f"related skill exists: {related} in {r}")
        for ref in re.findall(r"`\$HERMES_HOME/(templates/[A-Za-z0-9._-]+)`", text):
            check((REPO / ref).is_file(), f"template reference resolves: {ref} in {r}")
        for ref in re.findall(r"`(references/[A-Za-z0-9._/-]+)`", text):
            ok = (skill_md.parent / ref).is_file() or any(
                (REPO / "skills/hyperframes-video/skills" / s / ref).is_file() for s in VENDORED_SKILLS) \
                or (REPO / WRAPPER / ref).is_file()
            check(ok, f"reference file resolves: {ref} in {r}")
        for skill in re.findall(r"skill_view\(\\?\"([a-z-]+)\\?\"", text):
            check(skill in names, f"skill_view target is bundled: {skill} in {r}")

    # runtime instruction files
    runtime = [f for f in files if rel(f).startswith(("skills/video-editor-core/", "skills/integrations/", "templates/", f"{EFFECTS}/"))
               or rel(f) in {"SOUL.md", "config.yaml", "profile.yaml"}]
    for f in runtime:
        r = rel(f)
        text = read(f) or ""
        if f.suffix in {".md", ".yaml"} and r != "config.yaml":
            for line in text.splitlines():
                if re.search(r"npx(?: --yes| -y)? hyperframes", line) and not NEGATION.search(line):
                    check(False, f"unpinned HyperFrames command in a runtime file: {r}", line.strip()[:100])
            check("hyperframes@latest" not in text or r.endswith(("hf.py",)), f"no @latest: {r}")
            for attr in set(re.findall(r"\bdata-[a-z][a-z0-9-]+", text)):
                if attr in {"data-attributes", "data-api", "data-provider"}:
                    continue
                check(attr in KNOWN_DATA_ATTRS, f"composition attribute is one the pinned release documents: {attr} in {r}")
        if f.suffix == ".md":
            for tool in VIDEO_DOWNLOADERS:
                for line in text.splitlines():
                    if tool in line and not NEGATION.search(line):
                        check(False, f"video-download tool named as usable: {tool} in {r}")
    check(True, "runtime files scanned for unpinned commands, undocumented attributes, and download tools")

    # promises, causes, fixed thresholds: runtime files, examples, docs, README
    for f in files:
        r = rel(f)
        if is_vendored(r) or r in SELF or r.startswith(("tests/", "evals/", "scripts/")) or f.suffix not in {".md", ".yaml"}:
            continue
        text = read(f) or ""
        for line, context in claim_lines(text):
            for label, pattern in PROMISES.items():
                m = pattern.search(line)
                if m and not NEGATION.search(context):
                    check(False, f"{label}: {r}", line.strip()[:110])
            if FIXED_THRESHOLD.search(line) and not NEGATION.search(context):
                check(False, f"fixed outlier threshold stated as fact: {r}", line.strip()[:110])
    check(True, "no promised result, stated cause, or fixed outlier threshold")

    # markdown links in original docs
    for f in files:
        r = rel(f)
        if f.suffix != ".md" or is_vendored(r):
            continue
        text = f.read_text(encoding="utf-8")
        for target in re.findall(r"\]\((?!https?://|#|mailto:)([^)#\s]+)", text):
            check((f.parent / target).exists(), f"internal link resolves: {target} in {r}")

    # placeholders and leftover markers in original files
    for f in files:
        r = rel(f)
        if is_vendored(r) or r in SELF or r.startswith("tests/") or f.suffix == ".json":
            continue
        text = read(f)
        if text is None:
            continue
        for token in ("<GITHUB_OWNER>", "<REPOSITORY_NAME>", "GITHUB_OWNER", "REPOSITORY_NAME", "lorem ipsum"):
            check(token.lower() not in text.lower(), f"unresolved placeholder {token}: {r}")
        check(not re.search(r"\b(?:TODO|FIXME|XXX|TBC)\b", text), f"leftover work marker: {r}")

    # examples
    examples = [f for f in files if rel(f).startswith("examples/")]
    check(len(examples) >= 6, "examples are present", str(len(examples)))
    for f in examples:
        text = read(f) or ""
        check(len(text.strip()) > 300, f"example is not empty: {rel(f)}")
        check("synthetic" in text.lower(), f"example is labeled synthetic: {rel(f)}")
        # A view count in an example must be visibly invented test data.
        for line in text.splitlines():
            if re.search(r"(?i)\b[\d,.]+ ?(?:k|m|million)? views\b", line):
                check("synthetic" in line.lower() or "| synthetic" in text.lower(),
                      f"reference figure in an example is labeled synthetic: {rel(f)}", line.strip()[:90])

    # community promotion: README only, one section, link once
    readme = (REPO / "README.md").read_text(encoding="utf-8") if (REPO / "README.md").is_file() else ""
    check(readme.count("https://www.skool.com/agenticaiacademy/about") == 1, "community link appears exactly once in README")
    check(len(re.findall(r"(?i)agentic ai academy", readme)) <= 2, "community named in one README section only")
    check(readme.count("$97") == 1, "community price appears once in README")
    for f in files:
        r = rel(f)
        if r == "README.md" or r in SELF or r.startswith("tests/") or r == "scripts/run_evals.py":
            continue
        text = read(f)
        if text is None:
            continue
        check(not any(p.search(text) for p in COMMUNITY), f"community promotion outside the README: {r}")

    # README commands, flags, and environment variables
    check(f"hermes profile install {GITHUB} --alias\n" in readme, "README primary install command")
    check(f"hermes profile install {GITHUB} --alias --yes" in readme, "README documents the --yes form separately")
    first_plain = readme.find(f"hermes profile install {GITHUB} --alias\n")
    first_yes = readme.find(f"hermes profile install {GITHUB} --alias --yes")
    check(0 <= first_plain < first_yes, "confirmation-enabled command comes first")
    for cmd in ("hermes -p video-editor chat", "hermes profile update video-editor",
                "hermes profile delete video-editor", "--assignee video-editor", "--assignee social-media"):
        check(cmd in readme, f"README documents: {cmd}")
    launcher = (REPO / WRAPPER / "scripts/hf.py").read_text(encoding="utf-8")
    tools_src = (REPO / WRAPPER / "scripts/editor_tools.py").read_text(encoding="utf-8")
    known_cmds = set(re.findall(r'"([a-z][a-z-]+)"', launcher.split("ALLOWED = {", 1)[1].split("}", 1)[0]))
    known_cmds |= set(re.findall(r'cmd == "([a-z-]+)"', launcher)) | {"status", "doctor", "preview-start", "preview-status", "preview-stop"}
    prohibited = set(re.findall(r'^    "([a-z-]+)":', launcher.split("PROHIBITED = {", 1)[1].split("\n}", 1)[0], re.M))
    setup_flags = set(re.findall(r'flag == "(--[a-z-]+)"', launcher)) | {"--plan", "--yes"}
    render_flags = {"--stage", "--comparison", "--fps", "--format", "--resolution", "--variables", "--variables-file",
                    "--batch", "--batch-concurrency", "--strict-variables", "--workers", "--quality", "--output",
                    "--hdr", "--sdr", "--crf", "--video-bitrate", "--strict"}
    known_tools = set(re.findall(r'^    "([a-z-]+)": cmd_', tools_src, re.M)) | set(re.findall(r'"([a-z-]+)": cmd_', tools_src))
    docs_text = {rel(f): f.read_text(encoding="utf-8") for f in files
                 if f.suffix == ".md" and not is_vendored(rel(f)) and not rel(f).startswith("evals/")}
    filler = {"is", "in", "and", "or", "the", "a", "to", "itself", "refuses", "writes", "runs", "then", "from", "with",
              "command", "launcher", "never", "does", "for", "on", "by"}
    for r, text in docs_text.items():
        for m in re.finditer(r"(?:hf\.py\"?|(?m:^)hf|`hf) ([a-z][a-z-]+)((?: --?[a-z-]+(?:[ =][^\s`|\\]+)?)*)", text):
            cmd = m.group(1)
            check(cmd in known_cmds or cmd in prohibited or cmd in filler,
                  f"documented launcher command exists: `{cmd}` in {r}")
            flags = re.findall(r"(--[a-z-]+)", m.group(2))
            if cmd == "setup":
                for flag in flags:
                    check(flag in setup_flags, f"documented setup flag exists: {flag} in {r}")
            if cmd == "render":
                for flag in flags:
                    check(flag in render_flags, f"documented render flag is one the tagged CLI or launcher accepts: {flag} in {r}")
        for m in re.finditer(r"editor_tools\.py\"? ([a-z][a-z-]+)", text):
            check(m.group(1) in known_tools or m.group(1) in filler, f"documented tool exists: `{m.group(1)}` in {r}")
        for var in set(re.findall(r"\bHYPERFRAMES_[A-Z_]+\b", text)):
            check(var in KNOWN_HF_ENV, f"documented environment variable is one the tagged CLI or launcher uses: {var} in {r}")

    # capability claims are backed by recorded, passing, pixel-checked renders
    results_dir = REPO / "docs/test-results"
    recorded: dict[str, str] = {}
    for name in ("tools.json", "gates.json", "renders.json", "install-hermes-0.22.5.json", "install-hermes-0.21.4.json", "effects.tests.json"):
        path = results_dir / name
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            for t in data["tests"]:
                recorded[t["name"]] = t["status"]
            check(data["counts"]["fail"] == 0, f"recorded results contain no failure: {name}", str(data["counts"]))
    caps = (REPO / WRAPPER / "references/capabilities.md").read_text(encoding="utf-8")
    claims = {
        "Hard cut at a known timecode": "CutsAndFinalPipeline: cut trim splice reorder then final",
        "Trim in and out": "CutsAndFinalPipeline: cut trim splice reorder then final",
        "Split and splice": "CutsAndFinalPipeline: cut trim splice reorder then final",
        "Reorder": "CutsAndFinalPipeline: cut trim splice reorder then final",
        "Retime at a constant rate": "RetimeAndFreeze: slow motion and held frame",
        "Freeze on a still": "RetimeAndFreeze: slow motion and held frame",
        "Punch-in on the inner wrapper": "PunchInAndCrossfade: punch in and crossfade",
        "Crossfade": "PunchInAndCrossfade: punch in and crossfade",
        "J cut with independent audio": "JCut: sound leads picture",
        "Dead-air removal from transcript timings": "DeadAirRemoval: keep ranges from transcript timings",
        "Captions on a vertical clip, timed to a transcript": "CaptionsAndOverlays: vertical captions lower third and callout",
        "Lower-third and data callout": "CaptionsAndOverlays: vertical captions lower third and callout",
        "Motion graphic with transparency (WebM)": "TransparentMotionGraphic: webm with alpha",
        "Music bed with voice carve": "AudioMix: music bed with voice carve and clipping",
        "Color treatment with before and after sheets": "ColorTreatment: grade changes the picture and contact sheets exist",
        "16:9 render": "ReframeAndBatch: reframes are separate reviewed renders",
        "Reframe to 9:16 and 4:5 as separate renders": "ReframeAndBatch: reframes are separate reviewed renders",
        "Batch render from variable rows": "ReframeAndBatch: batch render one output per row",
        "Multi-segment long-form with sub-compositions": "LongForm: multi segment long form with measurements",
        "Draft and final quality settings": "CutsAndFinalPipeline: cut trim splice reorder then final",
        "Version compare sheet": "ReframeAndBatch: reframes are separate reviewed renders",
        "Preview start and teardown": "PreviewLifecycle: preview starts on localhost and tears down",
    }
    cap_rows = {ln.split("|")[1].strip(): ln.split("|")[2].strip() for ln in caps.splitlines()
                if ln.startswith("| ") and ln.count("|") >= 4}
    for claim, test in claims.items():
        check(cap_rows.get(claim) == "rendered and verified", f"capability row present and marked: {claim}", str(cap_rows.get(claim)))
        check(recorded.get(test) == "pass", f"claimed capability has a passing recorded render: {claim}", str(recorded.get(test)))
    for claim, status in cap_rows.items():
        if status == "rendered and verified":
            check(claim in claims, f"`rendered and verified` row is tied to a recorded test: {claim}")
    # the README's operations table agrees with the capability reference, row for row
    readme_rows = {ln.split("|")[1].strip(): ln.split("|")[2].strip() for ln in readme.splitlines()
                   if ln.startswith("| ") and ln.count("|") >= 3}
    for claim, status in cap_rows.items():
        if claim in readme_rows and status in {"rendered and verified", "tested", "not tested", "not available", "loaded only"}:
            check(readme_rows[claim] == status, f"README status matches the capability reference: {claim}",
                  f"{readme_rows[claim]} vs {status}")
    check(sum(1 for c in claims if c in readme_rows) >= 18, "README lists the tested editing operations")

    # measured long-form limits: every figure in the README comes from the recorded run
    renders = json.loads((results_dir / "renders.json").read_text()) if (results_dir / "renders.json").is_file() else {}
    lf = (renders.get("measurements") or {}).get("longform")
    if check(bool(lf), "a long-form render measurement is recorded"):
        perf = (REPO / "docs/render-performance-and-limits.md").read_text(encoding="utf-8")
        for value in (str(lf["duration_seconds"]), lf["resolution"], str(round(lf["render_seconds"])), str(lf["peak_tree_rss_mb"])):
            check(value in perf, f"long-form figure in docs matches the recorded run: {value}")
            check(value.replace("x", "×") in readme or value in readme, f"long-form figure in README matches the recorded run: {value}")

    # platform facts carry a source and a date
    facts = yaml.safe_load((REPO / FACTS).read_text(encoding="utf-8")) if (REPO / FACTS).is_file() else {"facts": [], "research_routes": []}
    for fact in facts["facts"]:
        tag = f"{fact.get('platform')}/{fact.get('topic')}"
        check(str(fact.get("source_url", "")).startswith("https://"), f"platform fact has an official URL: {tag}")
        check(bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(fact.get("accessed", "")))), f"platform fact has an access date: {tag}")
        check(fact.get("status") in {"verified", "not_verified"}, f"platform fact has a status: {tag}")
    for route in facts.get("research_routes", []):
        tag = f"{route.get('platform')}/{route.get('route')}"
        check(route.get("status") in {"enabled", "opt-in", "not permitted by terms", "not built"}, f"research route has a status: {tag}")
        check(str(route.get("source_url", "")).startswith("https://") and bool(route.get("accessed")),
              f"research route records its terms source and access date: {tag}")
        if route.get("status") == "enabled":
            check(route.get("route") in {"social_media_shortlist", "owner_supplied"},
                  f"only owner-supplied routes are enabled by default: {tag}")
    check(len(facts.get("research_routes", [])) >= 8, "research routes are recorded per platform")
    for f in files:
        r = rel(f)
        if f.suffix != ".md" or is_vendored(r) or r.startswith(("tests/", "evals/")):
            continue
        in_example = False
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                in_example = line.strip() == "## Example"
            if in_example or not (PLATFORM_WORD.search(line) and SPEC_NUMBER.search(line)):
                continue
            sourced = ("http" in line or "verified" in line.lower() or "synthetic" in line.lower()
                       or "accessed" in line.lower() or "platform-facts" in line.lower())
            check(sourced, f"platform spec stated without a source or status: {r}", line.strip()[:110])

    # self-update, cloud, publish, sign-in, download unreachable
    allowed = set(re.findall(r'"([a-z][a-z-]+)"', launcher.split("ALLOWED = {", 1)[1].split("}", 1)[0]))
    need = {"skills", "upgrade", "publish", "cloud", "lambda", "cloudrun", "auth", "feedback", "telemetry",
            "events", "capture", "media-use", "tts", "models", "browser", "add", "remove-background"}
    check(need <= prohibited, "launcher refuses every external, self-update, and fetch subcommand", str(need - prohibited))
    check(not (allowed & prohibited), "no subcommand is both allowed and prohibited", str(allowed & prohibited))
    for switch in ("HYPERFRAMES_SKIP_SKILLS", "HYPERFRAMES_NO_UPDATE_CHECK", "HYPERFRAMES_NO_AUTO_INSTALL",
                   "HYPERFRAMES_NO_TELEMETRY", "DO_NOT_TRACK"):
        check(f'"{switch}": "1"' in launcher, f"launcher sets {switch}=1")
    for needle in ("def style_report", "def references_report", "def media_id_report", "def plan_workers"):
        check(needle in launcher, f"launcher implements: {needle[4:]}")
    for src, label in ((launcher, "launcher"), (tools_src, "tools")):
        check(not re.search(r"\b(?:urllib|requests|http\.client|socket|ftplib)\b", src), f"{label} imports no network library")
        check(not any(tool in src for tool in VIDEO_DOWNLOADERS), f"{label} names no video-download tool")
    cfg = yaml.safe_load((REPO / "config.yaml").read_text(encoding="utf-8"))
    deny = cfg["approvals"]["deny"]
    for needle in ("*npx*hyperframes*", "*hyperframes.mjs*", "*hf.py publish*", "*hf.py cloud*", "*hf.py lambda*",
                   "*hf.py auth*", "*hf.py skills*", "*hf.py upgrade*", "*hf.py setup*", "*hf.py add*", "*npm run*",
                   "*skills install*hyperframes*", "*yt-dlp*", "*youtube-dl*", "*rm *footage/*", "*cp *references/*"):
        check(needle in deny, f"config deny rule present: {needle}")
    check(cfg["approvals"]["mode"] == "manual" and cfg["approvals"]["cron_mode"] == "deny", "approvals fail closed")
    check(cfg["terminal"]["home_mode"] == "profile", "terminal.home_mode is profile")
    check(cfg["memory"]["write_approval"] is True and cfg["skills"]["write_approval"] is True, "memory and skill writes staged")
    for key in ("model", "provider", "mcp_servers", "cron", "toolsets"):
        check(key not in cfg, f"config hardcodes no {key}")
    check(not re.search(r"(?m)^\s*[^#\n]*(/Users/|/home/|C:\\\\)", (REPO / "config.yaml").read_text()), "config has no absolute user path")

    # licenses
    lic = (REPO / "LICENSE").read_text(encoding="utf-8")
    check("MIT License" in lic and "Copyright (c) 2026 TakiGPT AI Inc." in lic, "MIT license and copyright line")
    tpn = (REPO / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
    for needle in ("Apache License", "Copyright 2026 HeyGen, Inc.", "GSAP Standard License", "OFL-1.1",
                   "Pixabay", "CC-BY-4.0", "vtake", "captions-overlay", "7e2817619f340f9302eeaef185e73be39a19858d",
                   "@hyperframes/shader-transitions", "html2canvas", "2756209a92766a4e4726999a51648349a272c159"):
        check(needle in tpn, f"THIRD_PARTY_NOTICES covers: {needle}")
    check("MIT" not in (REPO / "skills/hyperframes-video/LICENSE").read_text()[:400], "vendored material is not relicensed as MIT")
    check("retain the community link" not in readme.lower() and "must keep the community" not in readme.lower(),
          "README does not claim the license forces forks to keep the community link")

    # CI actions pinned to a full commit
    ci = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    for uses in re.findall(r"uses:\s*(\S+)", ci):
        check(bool(re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", uses)), f"CI action pinned to a commit: {uses}")
    check("auto-merge" not in ci.lower() and "git push" not in ci.lower(), "CI never merges or pushes")

    # vendor verification, upstream contract, evals
    for script, label in (("hyperframes_vendor.py", "vendor checksums and derivative"),
                          ("check_upstream_contract.py", "upstream contract"), ("run_evals.py", "eval fixtures")):
        args = [sys.executable, str(REPO / "scripts" / script)] + (["verify"] if script == "hyperframes_vendor.py" else [])
        proc = subprocess.run(args, capture_output=True, text=True)
        check(proc.returncode == 0, label, proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else proc.stderr[-200:])


def validate_effects() -> None:
    """Effects library: catalog current, verified claims backed by records,
    README count equal to the verified count, copy check, sync conflicts."""
    lib = REPO / EFFECTS / "effects-library"
    specs = sorted(lib.glob("*/*/effect.json"))
    ids = [json.loads(p.read_text(encoding="utf-8"))["effect_id"] for p in specs]
    check(len(ids) == len(set(ids)), "effect ids are unique", str(len(ids)))
    for p in specs:
        s = json.loads(p.read_text(encoding="utf-8"))
        r = rel(p)
        check(s["effect_id"] == p.parent.name and s["family"] == p.parent.parent.name, f"effect folder matches id and family: {r}")
        for key in ("effect_id", "display_name", "family", "kind", "description", "implementation_route", "parameters",
                    "applies_to", "needs_model", "needs_key_footage", "hdr_behavior", "deterministic", "seek_safe",
                    "photosensitivity", "face_safe", "provenance", "license", "status"):
            check(key in s and s[key] not in (None, ""), f"catalog field {key} present: {r}")
        check(s.get("needs_model") is False, f"no effect needs a model: {r}")
        for prm in s.get("parameters", []):
            check(prm["min"] <= prm["default"] <= prm["max"], f"parameter range holds its default: {r} {prm['key']}")
        if s.get("provenance") == "clean-room":
            check(bool(re.fullmatch(r"RS-\d{3}", s.get("reference_id") or "")), f"clean-room effect names its study entry: {r}")
        rec = p.parent / "verification.json"
        if rec.is_file():
            data = json.loads(rec.read_text(encoding="utf-8"))
            if data.get("result") == "pass":
                nums = {c["n"] for c in data.get("checks", [])}
                check(set(range(1, 13)) <= nums and all(c["result"] in {"pass", "not-applicable"} for c in data["checks"]),
                      f"a passing record has all 12 checks passed or not applicable: {r}")
                check((p.parent / "reference.jpg").is_file() or s["family"] == "audio", f"verified picture effect has its reference still: {r}")
    for js in lib.glob("*/*/update.js"):
        text = js.read_text(encoding="utf-8")
        if re.search(r"perspective\(|rotate[XY]\(|rotate3d\(|preserve-3d", text):
            spec = json.loads((js.parent / "effect.json").read_text(encoding="utf-8"))
            check(spec.get("needs_screenshot_capture") is True,
                  f"a 3D-transform effect routes renders to screenshot capture (fast capture freezes video in 3D layers): {rel(js)}")
        for banned in ("Math.random", "Date.now", "new Date", "performance.now", "fetch(", "XMLHttpRequest", "import("):
            check(banned not in text, f"effect script is deterministic and offline ({banned}): {rel(js)}")
    proc = subprocess.run([sys.executable, str(REPO / "scripts/build_catalog.py"), "--check"], capture_output=True, text=True)
    check(proc.returncode == 0, "catalog, catalog doc and README counts are current", proc.stdout.strip()[-200:])
    cat = json.loads("\n".join(l for l in (lib / "catalog.yaml").read_text(encoding="utf-8").splitlines() if not l.startswith("#")))
    counts = cat["counts"]
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    check(f"| **Picture effects** | **{counts['visual_verified']}** |" in readme, "README verified count equals the catalog's verified count")
    status = "full release" if counts["visual_verified"] >= 101 else "limited release"
    check(status in readme and (status == "full release" or str(counts["visual_verified"]) in readme),
          "README states full or limited release with the exact count")
    proc = subprocess.run([sys.executable, str(REPO / "scripts/copy_check.py"), "check"], capture_output=True, text=True)
    check(proc.returncode == 0, "copy check against the studied project's fingerprints", proc.stdout.strip()[-200:])
    # sync-conflict duplicates from a cloud-synced folder: "name 2", "name 2.ext"
    dupes = []
    for path in REPO.rglob("*"):
        if ".git" in path.parts or "node_modules" in path.parts:
            continue
        if re.search(r" \d+(\.[^/]*)?$", path.name):
            empty_dir = path.is_dir() and not any(path.iterdir())
            dupes.append((rel(path), empty_dir))
    for r, empty_dir in dupes:
        if empty_dir:
            print(f"  WARN  empty sync-conflict folder (not tracked by Git; delete it with the owner's OK): {r}")
        else:
            check(False, f"sync-conflict duplicate in the tree: {r}")
    check(True, "sync-conflict duplicate scan complete")


def validate_history() -> None:
    try:
        log = subprocess.run(["git", "-C", str(REPO), "log", "--all", "-p", "--no-color", "--format=commit %H"],
                             capture_output=True, check=True).stdout.decode("utf-8", errors="replace")
    except Exception as exc:
        check(False, "git history readable", str(exc)[:100])
        return
    commit, path = "?", "?"
    for line in log.splitlines():
        if line.startswith("commit "):
            commit = line[7:15]
        elif line.startswith("+++ b/"):
            path = line[6:]
            name = Path(path).name
            allowed_name = path == "templates/style-decision.yaml"
            check((name not in FORBIDDEN_NAMES or allowed_name)
                  and Path(path).suffix.lower() not in (FORBIDDEN_SUFFIXES - {".csv"}),
                  f"history contains a forbidden file: {path} ({commit})")
        elif line.startswith("+") and path not in SELF:
            for hit in scan_secrets(line, f"{path} ({commit})"):
                check(False, f"history: {hit}")
    check(True, "git history secret scan complete")


def main() -> int:
    if "--only-history" not in sys.argv:
        validate_tree()
        validate_effects()
    if "--history" in sys.argv:
        validate_history()
    for e in errors:
        print(f"  FAIL  {e}")
    print(f"validate: {passed} checks passed, {len(errors)} failed")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
