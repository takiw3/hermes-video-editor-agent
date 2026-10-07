# HyperFrames integration

## Decision

**Option B: a derivative of the upstream skills, with recorded patches.** The unchanged upstream skills are not installed as the production integration, because they would:

- load in Hermes without the frontmatter fields this profile's skills carry,
- tell the agent to run a skill self-update before every workflow,
- write every command as a bare `npx hyperframes`, which resolves to whatever npm serves that day,
- document cloud render, Lambda, Cloud Run, publish, feedback, and sign-in as normal steps.

Option A (unchanged) fails on each of those. Option C (the Hermes optional `hyperframes` skill) was not needed and is not shipped: it is a single condensed skill, its setup installs the CLI globally with no upper pin, and it shares the name `hyperframes` with the upstream router. The install tests show that adding it beside the vendored router makes that name ambiguous on Hermes 0.21.4 and 0.21.5, so the profile's deny rules block the agent from installing it.

## Pin

| | |
| --- | --- |
| Upstream | https://github.com/heygen-com/hyperframes |
| Tag | `v0.8.138`, published 2026-10-06 |
| Commit | `0ca28db4f8671a2e2262594e03c566222d695920` |
| npm | `hyperframes@0.8.138` |
| License | Apache-2.0, Copyright 2026 HeyGen, Inc. No `NOTICE` file at the tag. |
| Exact upstream copy | `vendor/upstream/hyperframes/` (repository only) |
| Derivative | `skills/hyperframes-video/` (installed) |
| Lock file | `vendor/hyperframes.lock.yaml`: every file's SHA-256, every patch, every removed file, every asset license |

The baseline this work started from named `v0.8.137`. `v0.8.138` was published the same day and is what was tested. The baseline observations are kept as a regression fixture in `tests/fixtures/` and re-checked against the vendored copy by `scripts/check_upstream_contract.py`.

## What is bundled, what is not, and why

### Published skills, bundled (15)

`hyperframes`, `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`, `hyperframes-creative`, `hyperframes-cli`, `hyperframes-audio`, `hyperframes-registry`, `hyperframes-studio`, `media-use`, `talking-head-recut`, `embedded-captions`, `motion-graphics`, `general-video`, `faceless-explainer`.

### Published skills, not bundled

| Skill | Why |
| --- | --- |
| `music-to-video` | Failed the evidence test. It ships 66 PNG texture masks and one font with no license record in the skill or in upstream `CREDITS.md`. An asset with no identifiable license does not ship. |
| `product-launch-video` | Failed the evidence test. Its input is a live website capture, a network read the default mode does not perform, so no render of it could be tested. |
| `pr-to-video`, `remotion-to-hyperframes`, `slideshow`, `figma` | Not editing work. |

When the upstream router selects one of these, the agent says it is not bundled and offers the closest bundled workflow. It never downloads one.

### Internal upstream skills

Upstream keeps six skills under `.claude/skills`, marks each `metadata.internal: true`, and says they are not part of the distributed set. Four were evaluated against four conditions: covered by the Apache-2.0 license at the tag, loads standalone in an installed profile, every referenced file present without Git LFS pointers, and no instruction to act on the upstream repository.

| Skill | Result | Why |
| --- | --- | --- |
| `captions-overlay` | bundled | One text file, no assets, no LFS. Supplements `embedded-captions`, which is bundled. Loads in an installed profile on both tested Hermes releases. Marked as internal upstream material that may change without notice. |
| `motion-doctrine` | not bundled | It routes to `oversized-cursor`, which is out of scope. Its seam-gate script starts a detached preview server through an unpinned `npx --yes hyperframes` and prefers a repo-local CLI build. |
| `cut-the-curve` | not bundled | It tells the agent to read `motion-doctrine` first and defers to `seam-craft`. Neither is bundled, so it does not load standalone. |
| `seam-craft` | not bundled | Render doctrine for the `product-launch-video` injector, which is not bundled. |
| `changelog-video`, `oversized-cursor` | not bundled | Out of scope by instruction. |

### Registry

Not vendored. Catalog search runs locally in the pinned CLI. Installing an item fetches its files from the network, and the tagged source shows the fetch reads from the upstream `main` branch (`packages/cli/src/registry/remote.ts`), not from the pinned release. So a fetch is an owner-run setup step, per item, that records the hash of every file written. No fixed set of blocks was vendored: the overlay tests built their lower-third and callout by hand, and no test showed a block set was needed.

### Themes

Not vendored. `themes/` exists at the tag, and no bundled workflow reads it at runtime.

### Guides

`docs/guides` is not copied. Where the wrapper needs a fact from upstream, it is restated in `skills/integrations/editor-hyperframes/references/upstream-facts.md` with the upstream path and tag.

### Media sources

`media-use resolve` for music, images, logos, and voice reaches HeyGen and third-party services. Those routes are off: the launcher refuses `media-use` and `tts`, removes provider keys from the CLI's environment, and gives the CLI a home folder with no existing sign-in. Catalog terms for commercial social use were not established, so catalog assets are treated as unlicensed. The local operations stay on: captions, color and media treatment, and the audio engine, plus transcription once the owner installs the model. Background removal is unavailable in this release: it needs `onnxruntime-node`, which is not in the pinned lockfile, and a model that downloads on first run.

## Patches

`skills/hyperframes-video/MODIFICATIONS.md` lists every rule and every modified file. In short:

- Hermes frontmatter (`version`, `author`, `license`, `metadata.hermes`) added to each `SKILL.md`. `name` and `description` are unchanged, and no skill is renamed.
- A profile runtime-rules block under the frontmatter.
- Every `npx hyperframes` replaced with the pinned launcher form.
- Bundled helper scripts routed through the launcher.
- Every self-update and freshness step removed.
- Cloud, Lambda, Cloud Run, publish, feedback, upgrade, telemetry, capture, and skills instructions replaced or stubbed. Stubbed files are kept so links resolve.
- Two assets withheld: a font with conflicting license statements, and a vendored GSAP file.
- Nested `.gitignore` files and one loose test file withheld, so they cannot hide files from a git-URL install.

Every modified file carries a notice that it was changed. `hyperframes_vendor.py verify` rebuilds the derivative from the upstream copy and fails on any difference.

## Plugin mode and path resolution

Upstream's plugin mode was reproduced. `plugin.json` sits at `skills/hyperframes-video/`, two folders above each `SKILL.md`, so bundled helper scripts resolve the release from the manifest. Their own launcher calls `npx --yes hyperframes@<version>`. The profile's launcher puts shims ahead of `npx` on the child's `PATH`, so that call runs the lockfile-installed CLI when the version matches the pin and is refused when it does not.

Script paths use `$HERMES_HOME`, which Hermes sets for terminal commands in the profile. `${HERMES_SKILL_DIR}` substitution exists in the tested releases and is not relied on.

## What was proved, and where

| Requirement | Test |
| --- | --- |
| Every vendored skill loads in an installed profile | `tests/test_install.py`, on Hermes 0.21.4 and 0.21.5 |
| Cross-skill links resolve after installation | `hyperframes_vendor.py verify`, and a cross-skill `skill_view` in `tests/test_install.py` |
| No skill name collides | `tests/test_install.py` |
| No documented command resolves to an unpinned version | `hyperframes_vendor.py verify`, `scripts/validate.py`, `tests/test_gates.py` |
| The self-update path is unreachable | `tests/test_gates.py` (allowlist, shims), `tests/test_install.py` (deny rules) |
| `init` does not refresh skills or write outside the profile | `tests/test_renders.py` |
| A render path works after installation | `tests/test_renders.py`, from a profile installed by `hermes profile install` |
| Installation triggers no download | `tests/test_install.py`, with all network access denied |
| Cloud, upload, publish, sign-in, and fetch paths are refused | `tests/test_gates.py`, `tests/test_install.py` |
| No source file changes during an edit | `tests/test_renders.py`, by checksum |
| No vendored file differs from its checksum without a patch | `hyperframes_vendor.py verify` |
| No bundled asset ships without a license record | `hyperframes_vendor.py verify` |
