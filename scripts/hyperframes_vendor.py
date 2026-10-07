#!/usr/bin/env python3
"""Vendor, derive, lock, and verify the HyperFrames skills.

    python3 scripts/hyperframes_vendor.py import --upstream <checkout>
    python3 scripts/hyperframes_vendor.py derive
    python3 scripts/hyperframes_vendor.py lock
    python3 scripts/hyperframes_vendor.py verify        # CI entry point

`import` copies the selected skills from a local checkout of the pinned
upstream commit into vendor/upstream/hyperframes/, byte for byte.

`derive` rebuilds skills/hyperframes-video/ from that copy by applying the
patch rules in this file. The derivative is a pure function of the upstream
copy plus these rules, so `verify` can rebuild it in a temp dir and require
a byte-identical match. That is what "every local change is recorded" means
here: an edit made by hand to a derived file fails the build.

Standard library plus PyYAML only. No network access.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hf_vendor_config as C  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
VENDOR = REPO / C.VENDOR_ROOT
DERIVED = REPO / C.DERIVED_ROOT
LOCK = REPO / "vendor" / "hyperframes.lock.yaml"

SHORT = C.UPSTREAM_COMMIT[:7]
PROHIBITED_RE = "|".join(re.escape(s) for s in C.PROHIBITED_SUBCOMMANDS)

NOTICE_LINE = (
    f"Modified file. Derived from HeyGen HyperFrames {C.UPSTREAM_TAG} "
    f"(commit {SHORT}), licensed under Apache-2.0, {C.UPSTREAM_COPYRIGHT} "
    "Changed by TakiGPT AI Inc. for the Hermes video-editor profile. "
    "Rules applied: {rules}. See skills/hyperframes-video/MODIFICATIONS.md."
)

RUNTIME_RULES = f"""> **Profile runtime rules. These override anything below.**
>
> 1. Load the `editor-hyperframes` skill first. It governs every HyperFrames call in this profile.
> 2. Run every HyperFrames command through the pinned launcher: `{C.LAUNCHER} <command>`. Never run the CLI through `npx`, as a bare `hyperframes` binary, or at any other version.
> 3. Run a bundled helper script as `{C.LAUNCHER} script <path-to-script> <args>`, never with `node` directly.
> 4. `/name` means the bundled skill `name`. Load it with `skill_view("name")`. A link such as `../media-use/references/x.md` means `skill_view("media-use", "references/x.md")`. `<SKILL_DIR>` is the `skill_dir` value `skill_view` returns for this skill.
> 5. These skills are release-managed. Never update, install, or download a skill. If a workflow is not bundled, say so and offer the closest bundled one.
> 6. Cloud render, Lambda, Cloud Run, publish, feedback, sign-in, website capture, and provider calls are unavailable in the default mode. A command shown as `[unavailable in this profile: ...]` must not be run in any form.
> 7. Any download (CLI, browser, speech model, font, media, registry block) needs one-time owner approval naming the item, source, size, and license.
"""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


LFS_MAGIC = b"version https://git-lfs.github.com/spec/"


def is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as fh:
        return fh.read(len(LFS_MAGIC)) == LFS_MAGIC


def derived_rel(rel: str) -> str | None:
    """Map a path in the upstream copy to its path in the derivative.

    Published skills keep their path. Internal upstream skills move from
    `.claude/skills/<name>/` to `skills/<name>/` so they sit beside the
    published skills and cross-skill links resolve."""
    if rel.startswith("skills/"):
        return rel
    prefix = C.INTERNAL_ROOT + "/"
    if rel.startswith(prefix):
        return "skills/" + rel[len(prefix):]
    return None


def is_text(data: bytes) -> bool:
    if b"\0" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


# --------------------------------------------------------------------------
# import
# --------------------------------------------------------------------------

def cmd_import(args) -> int:
    upstream = Path(args.upstream).resolve()
    head = subprocess.run(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if head != C.UPSTREAM_COMMIT:
        print(f"refusing: checkout is at {head}, pin is {C.UPSTREAM_COMMIT}")
        return 1
    dirty = subprocess.run(
        ["git", "-C", str(upstream), "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    if dirty:
        print("refusing: upstream checkout has local changes")
        return 1

    withheld_hashes = {}
    for rel in C.WITHHELD:
        src = upstream / rel
        if not src.is_file():
            print(f"refusing: withheld file is missing upstream: {rel}")
            return 1
        withheld_hashes[rel] = sha256_file(src)

    if VENDOR.exists():
        shutil.rmtree(VENDOR)
    VENDOR.mkdir(parents=True)
    for name in C.ROOT_FILES:
        shutil.copy2(upstream / name, VENDOR / name)
    for skill in C.SKILLS_INCLUDED:
        src_dir = upstream / "skills" / skill
        for src in sorted(src_dir.rglob("*")):
            if src.is_symlink():
                print(f"refusing: symlink in upstream skills tree: {src}")
                return 1
            if not src.is_file():
                continue
            rel = src.relative_to(upstream).as_posix()
            if rel in C.WITHHELD:
                continue
            if is_lfs_pointer(src):
                print(f"refusing: Git LFS pointer in upstream skills tree: {rel}")
                return 1
            dest = VENDOR / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    for skill in C.INTERNAL_INCLUDED:
        src_dir = upstream / C.INTERNAL_ROOT / skill
        if not (src_dir / "SKILL.md").is_file():
            print(f"refusing: internal skill missing upstream: {skill}")
            return 1
        for src in sorted(src_dir.rglob("*")):
            if src.is_symlink():
                print(f"refusing: symlink in upstream internal skill: {src}")
                return 1
            if not src.is_file():
                continue
            rel = src.relative_to(upstream).as_posix()
            if is_lfs_pointer(src):
                print(f"refusing: Git LFS pointer in upstream internal skill: {rel}")
                return 1
            dest = VENDOR / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)

    (VENDOR.parent / "hyperframes.withheld.yaml").write_text(
        "# Upstream sha256 of files deliberately not copied into this repository.\n"
        "# Written by `hyperframes_vendor.py import`. Reasons are in\n"
        "# scripts/hf_vendor_config.py and vendor/hyperframes.lock.yaml.\n"
        + yaml.safe_dump(withheld_hashes, sort_keys=True),
        encoding="utf-8",
    )
    n = sum(1 for p in VENDOR.rglob("*") if p.is_file())
    print(f"imported {n} files from {C.UPSTREAM_TAG} ({SHORT})")
    return 0


# --------------------------------------------------------------------------
# derive: patch rules
# --------------------------------------------------------------------------

class PatchError(Exception):
    pass


def replace_once(text: str, old: str, new: str, where: str) -> str:
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{where}: expected exactly 1 match, found {count}: {old[:70]!r}")
    return text.replace(old, new)


def replace_section(text: str, heading: str, body: str, where: str) -> str:
    """Replace the body under an exact heading line, up to the next heading of
    the same or a higher level. The heading line itself is kept."""
    lines = text.split("\n")
    idx = [i for i, line in enumerate(lines) if line == heading]
    if len(idx) != 1:
        raise PatchError(f"{where}: expected exactly 1 heading {heading!r}, found {len(idx)}")
    start = idx[0]
    level = len(heading) - len(heading.lstrip("#"))
    end = len(lines)
    in_fence = False
    for i in range(start + 1, len(lines)):
        if lines[i].lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6}) ", lines[i])
        if m and len(m.group(1)) <= level:
            end = i
            break
    new_lines = lines[: start + 1] + ["", body.rstrip("\n"), ""] + lines[end:]
    return "\n".join(new_lines)


UNAVAILABLE = "Not available in this profile."

BUNDLED_WORKFLOWS = (
    "`/talking-head-recut`, `/embedded-captions`, `/motion-graphics`, "
    "`/faceless-explainer`, and `/general-video`"
)
NOT_BUNDLED = (
    "`/remotion-to-hyperframes`, `/slideshow`, `/music-to-video`, `/pr-to-video`, "
    "`/product-launch-video`, and `/figma`"
)

# (relative path under the vendor root) -> list of (rule id, callable)
def _router(text: str, w: str) -> str:
    text = replace_once(
        text,
        "**Plugin installs:** Before setup or freshness commands, follow [plugin execution rules](references/plugin-installation.md) when this skill is inside a HyperFrames plugin. Standalone installs keep the update instructions below.",
        "**This bundle:** these skills are pinned and release-managed by the Hermes profile. There are no setup or freshness commands to run. See [bundle rules](references/plugin-installation.md).",
        w,
    )
    text = replace_section(
        text,
        "### Check remaining usage",
        "The pinned CLI's `usage --json` command reports harness usage only for Claude Code, Codex, and Grok. Under Hermes it returns `status: unknown`. Report usage as unknown and do not guess an allowance. Keep scope and workflow choices with the owner.\n\n"
        "HyperFrames **renders video from HTML** — a composition is an HTML file whose DOM declares timing with `data-*` attributes, whose animation runtime is seekable, and whose media playback is owned by the framework. The full authoring contract lives in `/hyperframes-core`; read it before writing composition HTML. Brief, storyboard, review, production, dispatch, and frame-worker contracts live in this skill's `references/`.",
        w,
    )
    text = replace_section(
        text,
        "### Keep the project's CLI current",
        "This profile pins one CLI version in a lock file and installs it from a lockfile with integrity hashes. Never run an upgrade probe, never run a different version, and never change a project's pinned version. If a project's `package.json` pins a version other than the profile's, stop and report both versions to the owner.",
        w,
    )
    text = replace_section(
        text,
        "## 4. Install and enter the workflow",
        f"Workflows are bundled with the profile and are never installed or refreshed at run time. Bundled: {BUNDLED_WORKFLOWS}.\n\n"
        f"Not bundled: {NOT_BUNDLED}. When routing selects one of these, tell the owner it is not bundled in this release, name the closest bundled workflow (usually `/general-video`), and ask whether to proceed with it. Do not download it and do not reconstruct it from memory.",
        w,
    )
    text = replace_section(
        text,
        "## 6. Studio, and the HyperFrames desktop app",
        "The Studio preview is a local editor served on localhost. Start and stop it only through the launcher's `preview-start` and `preview-stop` commands, and stop it when the task ends. The HyperFrames desktop app hand-off is not available in this profile: do not offer it, and do not relay CLI lines that advertise it.",
        w,
    )
    return text


def _freshness_banner(skill: str):
    def fn(text: str, w: str) -> str:
        pattern = re.compile(
            r"^> \*\*First, keep this skill fresh[^\n]*$", re.MULTILINE
        )
        if len(pattern.findall(text)) != 1:
            raise PatchError(f"{w}: freshness banner not found exactly once")
        return pattern.sub(
            "> **Release-managed skill.** This copy is pinned with the Hermes profile. Do not run a skill update before, during, or after this workflow.",
            text,
        )
    return fn


def _general_video(text: str, w: str) -> str:
    text = replace_once(
        text,
        "Before relying on this workflow, run:\n\n```bash\nnpx hyperframes skills update general-video\n```\n\nA successful no-op means the skill is current. Surface an update failure instead of continuing from memory.\n",
        "This workflow is bundled and pinned with the Hermes profile. Do not run a skill update.\n",
        w,
    )
    text = replace_once(
        text,
        "First run `npx hyperframes skills update <workflow-name>`. ",
        "Borrow only from workflows bundled in this profile; never download one. ",
        w,
    )
    return text


def _capability_menu(text: str, w: str) -> str:
    return replace_once(
        text,
        "and workflow skills install lazily. Before reaching across, run `npx hyperframes skills update <that-workflow>` with the bare name. ",
        "and only the workflows bundled with this profile are available. Never download one. ",
        w,
    )


def _cli_skill(text: str, w: str) -> str:
    for needle in (
        "| HeyGen-hosted zero-infrastructure render | `npx hyperframes cloud render`                                                |\n",
        "| Self-managed distributed AWS render      | `npx hyperframes lambda render <project> --width 1920 --height 1080 --wait`   |\n",
        "| Self-managed distributed GCP render      | `npx hyperframes cloudrun render <project> --width 1920 --height 1080 --wait` |\n",
    ):
        text = replace_once(text, needle, "", w)
    text = replace_once(
        text,
        "Use cloud rendering when the user wants hosted rendering without local Chrome, FFmpeg, or AWS. Use Lambda only when AWS ownership is a requirement. Use Cloud Run only when GCP ownership is a requirement. Read the matching reference before running any cloud path.",
        "Rendering in this profile is local only. HeyGen-hosted cloud, AWS Lambda, and Google Cloud Run rendering are not available.",
        w,
    )
    start = text.index("After verifying a successful render, send one feedback report")
    end = text.index("## Read the matching reference before running a command")
    text = (
        text[:start]
        + "Do not send a feedback report. `feedback` submits to a public channel, which is an external write, and it is not available in this profile.\n\n"
        + text[end:]
    )
    pattern = re.compile(r"^9\. \*\*Hand the project to the desktop app \(on offer\):\*\*[^\n]*$", re.MULTILINE)
    if len(pattern.findall(text)) != 1:
        raise PatchError(f"{w}: desktop-app step not found exactly once")
    text = pattern.sub(
        "9. **Desktop app hand-off:** not available in this profile. Skip this step.", text
    )
    return text


def _sections(mapping: dict[str, str]):
    def fn(text: str, w: str) -> str:
        for heading, body in mapping.items():
            text = replace_section(text, heading, body, w)
        return text
    return fn


def _thr_skill(text: str, w: str) -> str:
    text = replace_once(
        text,
        'ls "<SKILL_DIR>/assets/fonts" "<SKILL_DIR>/assets/vendor/gsap.min.js"',
        'ls "<SKILL_DIR>/assets/fonts"',
        w,
    )
    text = replace_once(
        text,
        "- `<SKILL_DIR>/assets/fonts/*.woff2`, `<SKILL_DIR>/assets/vendor/gsap.min.js` (bundled inside this skill, staged to work dir in Step 9)",
        "- `<SKILL_DIR>/assets/fonts/*.woff2` (bundled inside this skill, staged to work dir in Step 9)\n- GSAP 3.15.0 is not bundled in this profile. The composition loads it from the jsDelivr CDN at render time, so rendering this workflow needs network access to `cdn.jsdelivr.net`.",
        w,
    )
    text = replace_once(
        text,
        "`LXGW WenKai TC` (Chinese hand-script), `Inter` (modern sans), `Virgil`\n(geometric hand). Reference via `@font-face` or `font-family` directly.",
        "`LXGW WenKai TC` (Chinese hand-script), `Inter` (modern sans). The `Virgil`\nfont is not bundled in this profile; use `Caveat` where a style calls for it. Reference via `@font-face` or `font-family` directly.",
        w,
    )
    text = replace_once(
        text,
        'mkdir -p "$WORK_DIR/public/fonts" "$WORK_DIR/public/vendor" "$WORK_DIR/public/cards"',
        'mkdir -p "$WORK_DIR/public/fonts" "$WORK_DIR/public/cards"',
        w,
    )
    text = replace_once(
        text,
        'cp -n "$SKILL_DIR/assets/vendor/gsap.min.js" "$WORK_DIR/public/vendor/"\n',
        "",
        w,
    )
    text = replace_once(
        text,
        '      @font-face {\n        font-family: "Virgil";\n        src: url("fonts/Virgil.woff2") format("woff2");\n        font-display: block;\n      }\n',
        "",
        w,
    )
    text = replace_once(
        text,
        '<script src="vendor/gsap.min.js"></script>',
        '<script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>',
        w,
    )
    return text


def _thr_editorial(text: str, w: str) -> str:
    return replace_once(
        text,
        "this skill only ships Caveat / LXGW WenKai TC / Inter / Virgil.",
        "this skill only ships Caveat / LXGW WenKai TC / Inter (Virgil is not bundled in this profile).",
        w,
    )


def _thr_design_index(text: str, w: str) -> str:
    return replace_once(
        text,
        "skill provides Caveat / LXGW WenKai TC / Inter / Virgil locally",
        "skill provides Caveat / LXGW WenKai TC / Inter locally (Virgil is not bundled in this profile)",
        w,
    )


SURGICAL = {
    "skills/hyperframes/SKILL.md": [("router-profile-rules", _router)],
    "skills/hyperframes/references/capability-menu.md": [("no-lazy-install", _capability_menu)],
    "skills/talking-head-recut/SKILL.md": [
        ("no-freshness-step", _freshness_banner("talking-head-recut")),
        ("withheld-assets", _thr_skill),
    ],
    "skills/talking-head-recut/references/styles/editorial.html": [("withheld-assets", _thr_editorial)],
    "skills/talking-head-recut/references/DESIGN_INDEX.md": [("withheld-assets", _thr_design_index)],
    "skills/embedded-captions/SKILL.md": [("no-freshness-step", _freshness_banner("embedded-captions"))],
    "skills/motion-graphics/SKILL.md": [("no-freshness-step", _freshness_banner("motion-graphics"))],
    "skills/faceless-explainer/SKILL.md": [("no-freshness-step", _freshness_banner("faceless-explainer"))],
    "skills/general-video/SKILL.md": [("no-freshness-step", _general_video)],
    "skills/hyperframes-cli/SKILL.md": [("local-render-only", _cli_skill)],
    "skills/hyperframes-cli/references/preview-render.md": [
        ("local-render-only", _sections({
            "### feedback (report after rendering)": f"{UNAVAILABLE} `feedback` submits to a public channel, which is an external write.",
            "## publish": f"{UNAVAILABLE} `publish` uploads the project to a hosted service.",
        })),
    ],
    "skills/hyperframes-cli/references/upgrade-info-misc.md": [
        ("local-render-only", _sections({
            "## upgrade": f"{UNAVAILABLE} The CLI version is pinned by the profile's lock file and is changed only through a reviewed repository update.",
            "## telemetry": "Telemetry is disabled by the launcher, which sets `HYPERFRAMES_NO_TELEMETRY=1` and `DO_NOT_TRACK=1` on every call. Do not enable it and do not run the `telemetry` command.",
        })),
    ],
    "skills/hyperframes-cli/references/init-and-scaffold.md": [
        ("local-render-only", _sections({
            "## capture": f"{UNAVAILABLE} Website capture is a network read the default mode does not perform.",
            "## skills": f"{UNAVAILABLE} Skills are bundled and release-managed by the Hermes profile.",
        })),
    ],
}

STUB_BODIES = {
    "skills/hyperframes/references/skill-lifecycle.md": """# Skill installation and freshness

The HyperFrames skills in this Hermes profile are bundled with the profile, pinned to one upstream release, and release-managed. They are updated only through a reviewed, versioned change to the profile repository, followed by `hermes profile update`.

- Never run a skill update, check, or install command, in any form.
- Never refresh skills during `init`. The launcher sets `HYPERFRAMES_SKIP_SKILLS=1` on every call, which is the opt-out the pinned CLI honors.
- A workflow that is not bundled is reported as not bundled. It is never downloaded.
- If a bundled skill looks stale or broken, stop and report it to the owner. Do not continue from a remembered workflow contract.
""",
    "skills/hyperframes/references/plugin-installation.md": f"""# Running from the Hermes profile bundle

These skills are installed as one bundle under the Hermes profile at `skills/hyperframes-video/`. The bundle keeps upstream's plugin layout (`plugin.json` beside a `skills/` folder), so bundled helper scripts that locate the CLI themselves resolve the pinned release instead of a global or latest one.

Rules for this bundle, which replace the standalone commands in every workflow and reference:

- Do not run any skill update, check, or install command. Report a missing bundled skill instead of downloading one. Resolve every skill reference inside this bundle.
- Run every CLI command as:

  ```bash
  {C.LAUNCHER} <command> <args...>
  ```

  Run it from the project directory inside the owner-approved workspace, never from the bundle directory. The launcher runs the lockfile-installed CLI at the pinned version and disables skill refresh, update checks, auto-install, and telemetry. A missing or mismatched CLI is an error, not permission to use another version.
- Run a bundled Node helper as:

  ```bash
  {C.LAUNCHER} script <absolute-script-path> <args...>
  ```

- Treat the bundle directory as read-only. Put outputs and temporary work in the project.
- To get newer skills, the profile maintainer updates the pinned release in the repository and the owner runs `hermes profile update`. Never update the bundle during a video task.
""",
}
for _rel, _what in C.STUBBED.items():
    if _rel not in STUB_BODIES:
        title = _what
        STUB_BODIES[_rel] = (
            f"# {title}\n\n{UNAVAILABLE}\n\n"
            f"{title} reaches an external service. The default `edit_and_render` mode of this Hermes profile renders locally only, and this release ships no approved publishing or cloud mode. The launcher refuses these commands and the profile configuration denies them.\n\n"
            "If the owner asks for this, say it is not available in this release and offer a local render.\n"
        )


# Global text rules, applied to every .md file in the derivative.
PIN_RE = re.compile(r"npx(?: --yes| -y)? hyperframes(?:@[0-9A-Za-z.\-]+)?(?![\w-])")
PROHIBITED_CMD_RE = re.compile(
    r"npx(?: --yes| -y)? hyperframes(?:@[0-9A-Za-z.\-]+)? (" + PROHIBITED_RE + r")\b[^`\n|]*"
)
PROHIBITED_BARE_RE = re.compile(
    r"`hyperframes (" + PROHIBITED_RE + r")\b([^`\n]*)`"
)
SKILLS_ADD_RE = re.compile(r"npx skills add[^`\n|]*")
NODE_SCRIPT_RE = re.compile(
    r"(?<![\w/.-])node (?=(?:\"?<SKILL_DIR>|\"?<MEDIA_DIR>|\"?<PLUGIN_ROOT>|\"?\$SKILL_DIR|scripts/|skills/|grounding/))"
)


def apply_global_md_rules(text: str) -> tuple[str, list[str]]:
    rules: list[str] = []

    def mark(m: re.Match) -> str:
        tail = m.group(0).split("hyperframes", 1)[1].strip()
        tail = re.sub(r"^@[0-9A-Za-z.\-]+\s*", "", tail)
        return f"[unavailable in this profile: hyperframes {tail.rstrip()}]"

    new = PROHIBITED_CMD_RE.sub(mark, text)
    new = PROHIBITED_BARE_RE.sub(
        lambda m: f"`[unavailable in this profile: hyperframes {m.group(1)}{m.group(2).rstrip()}]`",
        new,
    )
    new = SKILLS_ADD_RE.sub(
        lambda m: f"[unavailable in this profile: {m.group(0).rstrip()}]", new
    )
    if new != text:
        rules.append("neutralize-external-commands")
        text = new

    new = PIN_RE.sub(lambda m: C.LAUNCHER, text)
    if new != text:
        rules.append("pin-cli")
        text = new

    new = NODE_SCRIPT_RE.sub(lambda m: C.LAUNCHER + " script ", text)
    if new != text:
        rules.append("launcher-scripts")
        text = new
    return text, rules


INTERNAL_NOTICE = (
    "> **Internal upstream material.** Upstream keeps this skill under `.claude/skills/`, marks it "
    "`metadata.internal: true`, and does not distribute it with the published set. It may change or "
    "disappear without notice in a later release. Where it names a skill that is not bundled in this "
    "profile, that skill is unavailable: say so and continue with the bundled ones.\n"
)


def add_frontmatter(text: str, skill: str, where: str, internal: bool = False) -> str:
    if not text.startswith("---\n"):
        raise PatchError(f"{where}: no frontmatter at byte zero")
    end = text.index("\n---\n", 4)
    front = text[4:end]
    parsed = yaml.safe_load(front)
    keys = set(parsed.keys())
    if internal:
        if keys != {"name", "description", "metadata"} or parsed["metadata"] != {"internal": True}:
            raise PatchError(f"{where}: upstream internal frontmatter changed: {sorted(keys)}")
        front = replace_once(front, "\nmetadata:\n  internal: true", "", where)
        tags = "[hyperframes, video, vendored, upstream-internal]"
        meta = "metadata:\n  internal: true\n  hermes:\n"
    else:
        if keys != {"name", "description"}:
            raise PatchError(f"{where}: upstream frontmatter keys changed: {sorted(keys)}")
        tags = "[hyperframes, video, vendored]"
        meta = "metadata:\n  hermes:\n"
    extra = (
        f"version: {C.NPM_VERSION}\n"
        "author: HeyGen, Inc. (modified by TakiGPT AI Inc.)\n"
        "license: Apache-2.0\n"
        f"{meta}"
        f"    tags: {tags}\n"
        "    related_skills: [editor-hyperframes]"
    )
    body = text[end + 5:]
    banner = RUNTIME_RULES + ("\n" + INTERNAL_NOTICE if internal else "")
    return f"---\n{front}\n{extra}\n---\n\n{{NOTICE}}\n{banner}\n{body.lstrip(chr(10))}"


def with_notice(text: str, rel: str, rules: list[str]) -> str:
    notice = NOTICE_LINE.format(rules=", ".join(rules))
    suffix = Path(rel).suffix
    if "{NOTICE}" in text and rel.endswith("/SKILL.md"):
        return text.replace("{NOTICE}", f"> **{notice}**\n", 1)
    if suffix == ".md":
        return f"> **{notice}**\n\n{text}"
    if suffix == ".html":
        comment = f"<!-- {notice} -->\n"
        first, _, rest = text.partition("\n")
        if first.lower().startswith("<!doctype"):
            return f"{first}\n{comment}{rest}"
        return comment + text
    if suffix in {".mjs", ".cjs", ".js"}:
        comment = f"// {notice}\n"
        if text.startswith("#!"):
            first, _, rest = text.partition("\n")
            return f"{first}\n{comment}{rest}"
        return comment + text
    raise PatchError(f"{rel}: no notice format for modified {suffix} file")


def build_derived(out: Path) -> dict:
    """Write the derivative into *out* and return its inventory."""
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    inventory: dict[str, dict] = {}

    def record(rel_out: str, status: str, rules: list[str], upstream_rel: str | None):
        inventory[rel_out] = {
            "sha256": sha256_file(out / rel_out),
            "status": status,
            **({"rules": rules} if rules else {}),
            **({"upstream": upstream_rel} if upstream_rel else {}),
        }

    for name in ("LICENSE", "CREDITS.md", "plugin.json"):
        shutil.copy2(VENDOR / name, out / name)
        record(name, "unmodified", [], name)

    for src in sorted(VENDOR.rglob("*")):
        if not src.is_file():
            continue
        up_rel = src.relative_to(VENDOR).as_posix()
        rel = derived_rel(up_rel)
        if rel is None:
            continue
        internal = up_rel != rel
        dest = out / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = src.read_bytes()
        rules: list[str] = []

        if up_rel in STUB_BODIES:
            text = STUB_BODIES[up_rel]
            rules = ["stub-unavailable"]
            dest.write_text(with_notice(text, rel, rules), encoding="utf-8")
            record(rel, "stubbed", rules, up_rel)
            continue

        if not is_text(data):
            shutil.copy2(src, dest)
            record(rel, "unmodified", [], up_rel)
            continue

        text = data.decode("utf-8")
        original = text
        for rule_id, fn in SURGICAL.get(up_rel, []):
            text = fn(text, rel)
            if rule_id not in rules:
                rules.append(rule_id)
        if rel.endswith(".md"):
            text, global_rules = apply_global_md_rules(text)
            rules.extend(r for r in global_rules if r not in rules)
        parts = rel.split("/")
        if len(parts) == 3 and parts[2] == "SKILL.md":
            text = add_frontmatter(text, parts[1], rel, internal)
            rules.insert(0, "hermes-frontmatter")
            rules.insert(1, "runtime-rules-banner")
            if internal:
                rules.insert(2, "internal-upstream-notice")

        if text == original:
            shutil.copy2(src, dest)
            record(rel, "unmodified", [], up_rel)
        else:
            dest.write_text(with_notice(text, rel, rules), encoding="utf-8")
            record(rel, "modified", rules, up_rel)

    write_added_files(out, inventory, record)
    return inventory


RULE_DESCRIPTIONS = {
    "hermes-frontmatter": "Added `version`, `author`, `license`, and `metadata.hermes` frontmatter fields accepted by the tested Hermes skill schema. `name` and `description` are unchanged.",
    "runtime-rules-banner": "Inserted the profile runtime rules block directly under the frontmatter.",
    "internal-upstream-notice": "Internal upstream skill only: moved from `.claude/skills/<name>/` to `skills/<name>/` so it sits beside the published skills, and marked as internal upstream material that may change without notice.",
    "pin-cli": "Replaced every unpinned `npx` invocation of the CLI (including the `@latest` form) with the pinned launcher.",
    "launcher-scripts": "Routed `node <bundled script>` command forms through the launcher's `script` command.",
    "neutralize-external-commands": "Rewrote every command-form mention of a prohibited subcommand (" + ", ".join(C.PROHIBITED_SUBCOMMANDS) + ") and of the third-party `skills add` installer to an inert `[unavailable in this profile: ...]` marker.",
    "router-profile-rules": "Router: replaced the plugin/freshness line, the usage check, the CLI-upgrade section, the install-and-enter section, and the desktop-app section with profile rules; listed bundled and not-bundled workflows.",
    "no-lazy-install": "Removed the instruction to install a workflow before borrowing from it.",
    "no-freshness-step": "Removed the skill self-update step that ran before the workflow.",
    "local-render-only": "Removed or replaced cloud render, Lambda, Cloud Run, publish, feedback, upgrade, telemetry, website capture, skills, and desktop-app instructions.",
    "withheld-assets": "Removed references to the withheld Virgil font and the withheld vendored GSAP file; GSAP 3.15.0 now loads from the jsDelivr CDN.",
    "stub-unavailable": "Replaced the whole file with a short statement of what this profile does instead. The file is kept so links to it resolve.",
}


def write_added_files(out: Path, inventory: dict, record) -> None:
    lic_dir = out / "licenses"
    lic_dir.mkdir()

    ofl_src = (VENDOR / "skills/hyperframes-creative/frame-presets/code-editorial/fonts/OFL-inter.txt").read_text(encoding="utf-8")
    marker = "This Font Software is licensed under the SIL Open Font License, Version 1.1."
    if marker not in ofl_src:
        raise PatchError("OFL text marker not found in upstream OFL-inter.txt")
    ofl_body = ofl_src[ofl_src.index(marker):]
    (lic_dir / "OFL-1.1.txt").write_text(
        "The fonts listed in FONT-COPYRIGHTS.md as OFL-1.1 are each licensed by\n"
        "their own copyright holders under the SIL Open Font License, Version 1.1,\n"
        "reproduced below. The copyright line for every font file is in\n"
        "FONT-COPYRIGHTS.md.\n\n" + ofl_body,
        encoding="utf-8",
    )
    record("licenses/OFL-1.1.txt", "added", [], None)

    shutil.copy2(VENDOR / "LICENSE", lic_dir / "Apache-2.0.txt")
    record("licenses/Apache-2.0.txt", "added", [], None)

    (lic_dir / "FONT-COPYRIGHTS.md").write_text(font_copyrights(), encoding="utf-8")
    record("licenses/FONT-COPYRIGHTS.md", "added", [], None)

    (out / "ASSET-LICENSES.md").write_text(asset_licenses_md(), encoding="utf-8")
    record("ASSET-LICENSES.md", "added", [], None)

    modified = sorted(
        (rel, e) for rel, e in inventory.items() if e["status"] in {"modified", "stubbed"}
    )
    lines = [
        "# Modifications to HeyGen HyperFrames skills",
        "",
        f"The files under `skills/` in this folder are derived from HeyGen HyperFrames {C.UPSTREAM_TAG} (commit `{C.UPSTREAM_COMMIT}`), {C.UPSTREAM_REPOSITORY}, licensed under the Apache License 2.0, {C.UPSTREAM_COPYRIGHT} The license text is in `LICENSE`.",
        "",
        "TakiGPT AI Inc. changed the files listed below so the skills run safely inside a Hermes profile. Every other file under `skills/` is byte-identical to upstream. This derivative is not affiliated with or endorsed by HeyGen. HyperFrames and HeyGen are names of their respective owner and are used here only to identify the upstream work.",
        "",
        "The derivative is generated by `scripts/hyperframes_vendor.py derive` in the profile repository from an exact upstream copy, and CI rebuilds it to prove no unrecorded change exists.",
        "",
        "## Rules",
        "",
    ]
    for rule_id, desc in RULE_DESCRIPTIONS.items():
        lines.append(f"- `{rule_id}`: {desc}")
    lines += ["", "## Files not shipped", ""]
    for rel, reason in C.WITHHELD.items():
        lines.append(f"- `{rel}`: {reason}")
    lines += ["", "## Files added", ""]
    lines += [
        "- `ASSET-LICENSES.md`, `licenses/OFL-1.1.txt`, `licenses/Apache-2.0.txt`, `licenses/FONT-COPYRIGHTS.md`: license records for bundled fonts and audio that upstream ships without a license file beside them.",
        "- `MODIFICATIONS.md`: this file.",
        "",
        f"## Modified files ({len(modified)})",
        "",
    ]
    for rel, entry in modified:
        lines.append(f"- `{rel}`: {', '.join(entry['rules'])}")
    (out / "MODIFICATIONS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    record("MODIFICATIONS.md", "added", [], None)


def font_copyrights() -> str:
    """Per-file copyright and license strings read from each font's name table.

    Committed output is checked by `verify`; fontTools is needed only to
    regenerate it, so CI can verify without the dependency."""
    cached = DERIVED / "licenses" / "FONT-COPYRIGHTS.md"
    try:
        from fontTools.ttLib import TTFont  # type: ignore
    except Exception:
        if cached.is_file():
            return cached.read_text(encoding="utf-8")
        raise PatchError("fontTools (with brotli) is required to generate FONT-COPYRIGHTS.md")

    rows = []
    for font in sorted(VENDOR.rglob("*.woff2")):
        rel = font.relative_to(VENDOR).as_posix()
        name = TTFont(str(font))["name"]
        copyright_line = (name.getDebugName(0) or "").strip().replace("|", "/")
        license_url = (name.getDebugName(14) or "").strip() or "not recorded in the font file"
        group = asset_group_for(rel)
        rows.append(f"| `{rel}` | {group['license']} | {copyright_line} | {license_url} |")
    return (
        "# Font copyright notices\n\n"
        "Read from the `name` table of each bundled font file (name ID 0, copyright; name ID 14, license URL). The license column is the record in `ASSET-LICENSES.md`.\n\n"
        "| File | License | Copyright notice in the font | License URL in the font |\n"
        "| --- | --- | --- | --- |\n" + "\n".join(rows) + "\n"
    )


def asset_group_for(rel: str) -> dict | None:
    for group in C.ASSET_LICENSES:
        if not fnmatch.fnmatch(rel, group["glob"]):
            continue
        base = rel.rsplit("/", 1)[-1]
        if "only" in group and base not in group["only"]:
            continue
        if "exclude" in group and base in group["exclude"]:
            continue
        return group
    return None


def asset_licenses_md() -> str:
    lines = [
        "# Licenses of bundled assets",
        "",
        f"The HyperFrames skills are Apache-2.0 ({C.UPSTREAM_COPYRIGHT}). The binary and media assets inside them carry their own licenses, recorded here. An asset with no record does not ship: see `MODIFICATIONS.md` for the two files withheld for that reason.",
        "",
    ]
    for group in C.ASSET_LICENSES:
        lines += [
            f"## {group['id']}",
            "",
            f"- Files: `{group['glob']}` ({group['count']})",
            f"- License: {group['license']} ({group['license_url']})",
            f"- Source: {group['source']}",
            f"- Proof: {group['proof']}",
            f"- Restrictions: {group['restrictions']}",
            "",
        ]
    lines += [
        "## Not bundled, loaded at render time",
        "",
        "- GSAP is not distributed in this repository. Upstream compositions load it from the jsDelivr CDN (3.14.2 in most workflows, 3.15.0 in `talking-head-recut`). In this profile the owner-run toolchain setup installs GSAP 3.14.2 from npm, from the pinned lockfile, and the launcher copies that build into each project so a render needs no CDN. A composition that pins another GSAP version still loads it from the CDN, which needs an owner-approved host. GSAP is licensed by Webflow under the GSAP Standard License (https://gsap.com/standard-license), which is not an OSI open-source license. It grants a license to use, reproduce, display, and implement GSAP on any website, web application, or digital interface at no charge, including commercial projects, and prohibits use in tools that let users build visual animations without code in competition with Webflow.",
        "- Some compositions reference Google Fonts or other CDN-hosted libraries. Those are fetched by the renderer at render time and are not distributed here.",
        "",
    ]
    return "\n".join(lines)


def cmd_derive(args) -> int:
    try:
        inventory = build_derived(DERIVED)
    except PatchError as exc:
        print(f"derive failed: {exc}")
        return 1
    counts: dict[str, int] = {}
    for entry in inventory.values():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    print("derived:", ", ".join(f"{v} {k}" for k, v in sorted(counts.items())))
    return 0


# --------------------------------------------------------------------------
# lock
# --------------------------------------------------------------------------

def vendor_inventory() -> dict[str, str]:
    return {
        p.relative_to(VENDOR).as_posix(): sha256_file(p)
        for p in sorted(VENDOR.rglob("*")) if p.is_file()
    }


def derived_inventory_from_disk() -> dict[str, str]:
    return {
        p.relative_to(DERIVED).as_posix(): sha256_file(p)
        for p in sorted(DERIVED.rglob("*")) if p.is_file()
    }


def cmd_lock(args) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        inventory = build_derived(Path(tmp) / "derived")
    withheld = yaml.safe_load((VENDOR.parent / "hyperframes.withheld.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((VENDOR / "skills-manifest.json").read_text(encoding="utf-8"))
    manifest_hashes = {
        name: manifest["skills"][name] for name in C.SKILLS_INCLUDED
    }
    patches = [
        {
            "file": rel, "status": e["status"], "rules": e["rules"],
            "upstream_sha256": sha256_file(VENDOR / e["upstream"]),
            "derived_sha256": e["sha256"],
        }
        for rel, e in sorted(inventory.items()) if e["status"] in {"modified", "stubbed"}
    ]
    lock = {
        "upstream_repository": C.UPSTREAM_REPOSITORY,
        "upstream_tag": C.UPSTREAM_TAG,
        "upstream_commit": C.UPSTREAM_COMMIT,
        "upstream_published_at": C.UPSTREAM_PUBLISHED_AT,
        "upstream_paths": C.UPSTREAM_PATHS,
        "npm_package": C.NPM_PACKAGE,
        "npm_version": C.NPM_VERSION,
        "npm_integrity": C.NPM_INTEGRITY,
        "node_minimum_major": C.NODE_MINIMUM_MAJOR,
        "skills_manifest_hashes": manifest_hashes,
        "retrieved_at": C.RETRIEVED_AT,
        "integration_option": "B (derived from upstream with recorded patches)",
        "vendor_path": C.VENDOR_ROOT,
        "installed_path": C.INSTALLED_PATH,
        "published_skills_included": C.SKILLS_INCLUDED,
        "published_skills_excluded": C.SKILLS_EXCLUDED,
        "internal_skills_included": C.INTERNAL_INCLUDED,
        "internal_skills_excluded": C.INTERNAL_EXCLUDED,
        "registry_items_included": C.REGISTRY_ITEMS_INCLUDED,
        "themes_included": C.THEMES_INCLUDED,
        "license": {
            "spdx": C.UPSTREAM_LICENSE,
            "copyright": C.UPSTREAM_COPYRIGHT,
            "license_file": f"{C.INSTALLED_PATH}/LICENSE",
            "notice_file_upstream": "none at the pinned tag",
            "credits_file": f"{C.INSTALLED_PATH}/CREDITS.md",
        },
        "patch_rules": RULE_DESCRIPTIONS,
        "local_patches": patches,
        "removed_files": [
            {"file": rel, "reason": reason, "upstream_sha256": withheld[rel]}
            for rel, reason in C.WITHHELD.items()
        ],
        "added_files": sorted(rel for rel, e in inventory.items() if e["status"] == "added"),
        "asset_licenses": [
            {k: v for k, v in g.items()} for g in C.ASSET_LICENSES
        ],
        "sha256": {
            "vendor_tree": tree_digest(vendor_inventory()),
            "derived_tree": tree_digest({rel: e["sha256"] for rel, e in inventory.items()}),
        },
        "file_inventory": {
            "vendor": vendor_inventory(),
            "derived": {rel: e["sha256"] for rel, e in sorted(inventory.items())},
        },
    }
    write_pin()
    lock["toolchain"] = {
        "package_json": f"{TOOLCHAIN_REL}/package.json",
        "package_lock": f"{TOOLCHAIN_REL}/package-lock.json",
        "package_lock_sha256": sha256_file(REPO / TOOLCHAIN_REL / "package-lock.json"),
        "pin_file": f"{TOOLCHAIN_REL}/pin.json",
        "locked_packages": len(load_package_lock()["packages"]) - 1,
        "install_command": "npm ci --ignore-scripts --no-audit --no-fund",
    }
    header = (
        "# HyperFrames vendoring lock file.\n"
        "# Generated by `python3 scripts/hyperframes_vendor.py lock`. Do not edit by hand.\n"
        "# Pins, scope, reasons, and asset licenses come from scripts/hf_vendor_config.py.\n"
    )
    LOCK.write_text(header + yaml.safe_dump(lock, sort_keys=False, width=100), encoding="utf-8")
    print(f"wrote {LOCK.relative_to(REPO)}: {len(lock['file_inventory']['vendor'])} vendor files, "
          f"{len(lock['file_inventory']['derived'])} derived files, {len(patches)} patches")
    return 0


TOOLCHAIN_REL = "skills/integrations/editor-hyperframes/toolchain"


def load_package_lock() -> dict:
    import json
    return json.loads((REPO / TOOLCHAIN_REL / "package-lock.json").read_text(encoding="utf-8"))


def pin_payload() -> dict:
    return {
        "npm_package": C.NPM_PACKAGE,
        "npm_version": C.NPM_VERSION,
        "npm_integrity": C.NPM_INTEGRITY,
        "node_minimum_major": C.NODE_MINIMUM_MAJOR,
        "upstream_repository": C.UPSTREAM_REPOSITORY,
        "upstream_tag": C.UPSTREAM_TAG,
        "upstream_commit": C.UPSTREAM_COMMIT,
        "package_lock_sha256": sha256_file(REPO / TOOLCHAIN_REL / "package-lock.json"),
    }


def write_pin() -> None:
    import json
    (REPO / TOOLCHAIN_REL / "pin.json").write_text(
        json.dumps(pin_payload(), indent=2) + "\n", encoding="utf-8")


def verify_toolchain(check) -> None:
    import json
    pin_path = REPO / TOOLCHAIN_REL / "pin.json"
    check(pin_path.is_file() and json.loads(pin_path.read_text(encoding="utf-8")) == pin_payload(),
          "toolchain pin.json matches the vendor config and the shipped lockfile")
    lock = load_package_lock()
    pkgs = lock["packages"]
    root = pkgs[""]["dependencies"]
    check(root.get(C.NPM_PACKAGE) == C.NPM_VERSION,
          "toolchain package.json pins the CLI to an exact version", str(root.get(C.NPM_PACKAGE)))
    check(all(re.fullmatch(r"\d+\.\d+\.\d+", v) for v in root.values()),
          "toolchain package.json has no version ranges", str(root))
    entry = pkgs.get(f"node_modules/{C.NPM_PACKAGE}", {})
    check(entry.get("version") == C.NPM_VERSION and entry.get("integrity") == C.NPM_INTEGRITY,
          "lockfile CLI entry matches the pinned version and npm integrity")
    no_integrity = [k for k, v in pkgs.items() if k and not v.get("link") and not v.get("integrity")]
    check(not no_integrity, "every locked package has an integrity hash", ", ".join(no_integrity[:3]))
    off_registry = [k for k, v in pkgs.items()
                    if v.get("resolved") and not v["resolved"].startswith("https://registry.npmjs.org/")]
    check(not off_registry, "every locked package resolves from registry.npmjs.org", ", ".join(off_registry[:3]))


def tree_digest(inventory: dict[str, str]) -> str:
    h = hashlib.sha256()
    for rel in sorted(inventory):
        h.update(f"{inventory[rel]}  {rel}\n".encode())
    return h.hexdigest()


# --------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------

def cmd_verify(args) -> int:
    errors: list[str] = []
    ok: list[str] = []

    def check(cond: bool, label: str, detail: str = "") -> None:
        (ok if cond else errors).append(label + (f": {detail}" if detail and not cond else ""))

    if not LOCK.is_file():
        print("FAIL lock file missing")
        return 1
    lock = yaml.safe_load(LOCK.read_text(encoding="utf-8"))

    check(lock["upstream_commit"] == C.UPSTREAM_COMMIT and lock["npm_version"] == C.NPM_VERSION,
          "lock pin matches config")
    check(lock["upstream_tag"] == f"v{lock['npm_version']}", "tag and npm version agree")
    plugin = yaml.safe_load((VENDOR / "plugin.json").read_text(encoding="utf-8"))
    check(plugin.get("name") == "hyperframes" and plugin.get("version") == C.NPM_VERSION,
          "upstream plugin.json names the pinned release", str(plugin.get("version")))

    verify_toolchain(check)
    check(lock.get("toolchain", {}).get("package_lock_sha256") == pin_payload()["package_lock_sha256"],
          "lock file records the shipped lockfile checksum")

    # 1. vendor copy matches recorded checksums exactly
    on_disk = vendor_inventory()
    recorded = lock["file_inventory"]["vendor"]
    missing = sorted(set(recorded) - set(on_disk))
    extra = sorted(set(on_disk) - set(recorded))
    changed = sorted(r for r in recorded if r in on_disk and recorded[r] != on_disk[r])
    check(not missing, "no vendored file missing", ", ".join(missing[:5]))
    check(not extra, "no unrecorded vendored file", ", ".join(extra[:5]))
    check(not changed, "vendored files match recorded sha256", ", ".join(changed[:5]))
    check(tree_digest(on_disk) == lock["sha256"]["vendor_tree"], "vendor tree digest matches")

    # 2. upstream skills manifest still describes the vendored skills
    manifest = yaml.safe_load((VENDOR / "skills-manifest.json").read_text(encoding="utf-8"))
    for skill in C.SKILLS_INCLUDED:
        check(skill in manifest["skills"], f"upstream manifest lists {skill}")
        check((VENDOR / "skills" / skill / "SKILL.md").is_file(), f"vendored {skill}/SKILL.md present")
    for skill in C.SKILLS_EXCLUDED:
        check(not (VENDOR / "skills" / skill).exists(), f"excluded skill absent from vendor: {skill}")
        check(not (DERIVED / "skills" / skill).exists(), f"excluded skill absent from derivative: {skill}")
    for skill in C.INTERNAL_INCLUDED:
        check((VENDOR / C.INTERNAL_ROOT / skill / "SKILL.md").is_file(), f"vendored internal {skill}/SKILL.md present")
    for skill in C.INTERNAL_EXCLUDED:
        check(not (VENDOR / C.INTERNAL_ROOT / skill).exists(), f"excluded internal skill absent from vendor: {skill}")
        check(not (DERIVED / "skills" / skill).exists(), f"excluded internal skill absent from derivative: {skill}")
    check(not any(is_lfs_pointer(p) for p in list(VENDOR.rglob("*")) + list(DERIVED.rglob("*")) if p.is_file()),
          "no Git LFS pointer files in vendor or derivative")
    check(lock.get("registry_items_included") == [] and not (REPO / "skills" / "hyperframes-video" / "registry").exists(),
          "no registry item is vendored")
    check(lock.get("themes_included") == [] and not (DERIVED / "themes").exists(), "no theme is vendored")
    for rel in C.WITHHELD:
        check(not (VENDOR / rel).exists(), f"withheld file absent from vendor: {rel}")
        check(not (DERIVED / rel).exists(), f"withheld file absent from derivative: {rel}")

    # 3. derivative is exactly upstream + recorded rules
    with tempfile.TemporaryDirectory() as tmp:
        try:
            rebuilt = build_derived(Path(tmp) / "derived")
        except PatchError as exc:
            errors.append(f"derive failed: {exc}")
            rebuilt = {}
    rebuilt_hashes = {rel: e["sha256"] for rel, e in rebuilt.items()}
    disk = derived_inventory_from_disk()
    d_missing = sorted(set(rebuilt_hashes) - set(disk))
    d_extra = sorted(set(disk) - set(rebuilt_hashes))
    d_changed = sorted(r for r in rebuilt_hashes if r in disk and rebuilt_hashes[r] != disk[r])
    check(not d_missing, "no derived file missing", ", ".join(d_missing[:5]))
    check(not d_extra, "no unrecorded derived file", ", ".join(d_extra[:5]))
    check(not d_changed, "derived files equal upstream plus recorded patches", ", ".join(d_changed[:5]))
    check(disk == lock["file_inventory"]["derived"], "derived inventory matches lock")

    # 4. every modified file carries a change notice; unmodified files are identical
    for rel, entry in rebuilt.items():
        path = DERIVED / rel
        if not path.is_file():
            continue
        if entry["status"] in {"modified", "stubbed"}:
            head = path.read_text(encoding="utf-8")[:6000]
            check("Modified file. Derived from HeyGen HyperFrames" in head,
                  f"change notice present: {rel}")
        elif entry["status"] == "unmodified":
            check(sha256_file(path) == sha256_file(VENDOR / entry["upstream"]),
                  f"unmodified file identical to upstream: {rel}")

    # 5. license texts travel with the derivative
    lic = DERIVED / "LICENSE"
    lic_text = lic.read_text(encoding="utf-8") if lic.is_file() else ""
    check("Apache License" in lic_text and "Version 2.0, January 2004" in lic_text,
          "Apache-2.0 text beside derived files")
    check(C.UPSTREAM_COPYRIGHT in lic_text, "upstream copyright preserved in LICENSE")
    check(sha256_file(lic) == sha256_file(VENDOR / "LICENSE") if lic.is_file() else False,
          "derived LICENSE identical to upstream LICENSE")
    check(not any((VENDOR / n).exists() for n in ("NOTICE", "NOTICE.md", "NOTICE.txt")),
          "upstream ships no NOTICE file at the pinned tag (nothing to reproduce)")
    for name in ("CREDITS.md", "MODIFICATIONS.md", "ASSET-LICENSES.md", "licenses/OFL-1.1.txt",
                 "licenses/Apache-2.0.txt", "licenses/FONT-COPYRIGHTS.md"):
        check((DERIVED / name).is_file(), f"present: {C.DERIVED_ROOT}/{name}")
    check((DERIVED / "skills/talking-head-recut/NOTICE.md").is_file(),
          "talking-head-recut MIT attribution preserved")

    # 6. every asset has a license record, and group counts are exact
    counts = {g["id"]: 0 for g in C.ASSET_LICENSES}
    for rel in sorted(disk):
        path = DERIVED / rel
        is_asset = path.suffix.lower() in C.ASSET_EXTENSIONS or rel in C.ASSET_EXTRA_FILES
        if not is_asset and rel.startswith("skills/") and not is_text(path.read_bytes()):
            is_asset = True
        if not is_asset:
            continue
        group = asset_group_for(rel)
        if group is None:
            errors.append(f"asset without a license record: {rel}")
        else:
            counts[group["id"]] += 1
    for group in C.ASSET_LICENSES:
        check(counts[group["id"]] == group["count"],
              f"asset group {group['id']} has {group['count']} files",
              f"found {counts[group['id']]}")

    # 7. no unpinned or external command form survives in derived instructions
    bad_patterns = {
        "unpinned npx hyperframes": re.compile(r"npx(?: --yes| -y)? hyperframes"),
        "npx skills add outside a marker": re.compile(r"(?<!this profile: )npx skills add"),
        "@latest": re.compile(r"hyperframes@latest"),
        "direct node on a bundled script": NODE_SCRIPT_RE,
    }
    for rel in sorted(disk):
        if not rel.endswith(".md"):
            continue
        text = (DERIVED / rel).read_text(encoding="utf-8")
        for label, pattern in bad_patterns.items():
            if pattern.search(text):
                errors.append(f"{label} in {rel}")
        for m in re.finditer(r'hf\.py" (' + PROHIBITED_RE + r")\b", text):
            errors.append(f"launcher called with prohibited subcommand {m.group(1)} in {rel}")
    ok.append("derived instructions scanned for unpinned and external command forms")

    # 8. cross-skill links resolve; no nested skills; no symlinks; names unique
    link_re = re.compile(r"\]\((\.\./[^)#\s]+)")
    broken = []
    for rel in sorted(disk):
        if not rel.endswith(".md"):
            continue
        base = (DERIVED / rel).parent
        for m in link_re.finditer((DERIVED / rel).read_text(encoding="utf-8")):
            target = (base / m.group(1)).resolve()
            try:
                target.relative_to((DERIVED / "skills").resolve())
            except ValueError:
                continue
            first = target.relative_to((DERIVED / "skills").resolve()).parts[0]
            if first in C.SKILLS_EXCLUDED or first in C.INTERNAL_EXCLUDED:
                continue
            if not target.exists():
                broken.append(f"{rel} -> {m.group(1)}")
    check(not broken, "cross-skill relative links resolve", "; ".join(broken[:5]))
    names = []
    for skill_md in sorted(DERIVED.rglob("SKILL.md")):
        rel = skill_md.relative_to(DERIVED).as_posix()
        check(len(rel.split("/")) == 3, f"skill sits at bundle depth: {rel}")
        front = yaml.safe_load(skill_md.read_text(encoding="utf-8").split("\n---\n", 1)[0][4:])
        check(front["name"] == skill_md.parent.name, f"skill name equals folder: {rel}")
        names.append(front["name"])
    check(sorted(names) == sorted(C.SKILLS_INCLUDED + C.INTERNAL_INCLUDED), "derived skills equal the included lists")
    check(not any(p.is_symlink() for p in list(VENDOR.rglob("*")) + list(DERIVED.rglob("*"))),
          "no symlinks in vendor or derivative")
    check(not any(p.name == ".gitignore" for p in list(VENDOR.rglob("*")) + list(DERIVED.rglob("*"))),
          "no nested .gitignore in vendor or derivative")

    for label in ok:
        if args.verbose:
            print(f"  ok    {label}")
    for label in errors:
        print(f"  FAIL  {label}")
    print(f"vendor verify: {len(ok)} checks passed, {len(errors)} failed")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import")
    p.add_argument("--upstream", required=True)
    p.set_defaults(fn=cmd_import)
    sub.add_parser("derive").set_defaults(fn=cmd_derive)
    sub.add_parser("lock").set_defaults(fn=cmd_lock)
    p = sub.add_parser("verify")
    p.add_argument("--verbose", "-v", action="store_true")
    p.set_defaults(fn=cmd_verify)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
