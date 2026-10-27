# Architecture

## What this repository is

A native Hermes Profile Distribution. Installing it creates one persistent, named Hermes profile, `video-editor`, with its own identity, configuration, skills, and state. It is not an ephemeral child agent spawned for a task.

## Three layers

1. **Identity and rules.** `SOUL.md`, `profile.yaml`, and `config.yaml`. The profile owns post-production and nothing else, studies outliers before it cuts, and never posts, uploads, or downloads a platform video.
2. **Editor skills.** 25 focused skills under `skills/video-editor-core/`, each with one job, one output contract, and its own failure behavior.
3. **The video engine.** HeyGen HyperFrames, pinned to one release and reached only through a launcher.
   - `skills/hyperframes-video/` holds 16 upstream skills, derived from the pinned release with recorded patches.
   - `skills/integrations/editor-hyperframes/` holds the wrapper skill, the launcher (`hf.py`), the measurement tools (`editor_tools.py`), and the pinned toolchain lockfile.

## Why a launcher

Upstream HyperFrames instructions are written for a coding agent on a developer's machine: every command is a bare `npx hyperframes`, skills update themselves, and the CLI can publish, cloud render, and sign in. None of that fits an agent editing a business owner's footage.

The launcher puts one process between the agent and the CLI. Everything the profile promises about the engine is checked there, in code:

| Promise | Where it is enforced |
| --- | --- |
| One pinned CLI version, from a lockfile | `hf.py`: runs the lockfile-installed CLI, refuses a version or lockfile mismatch |
| No skill self-update, update check, auto-install, or telemetry | `hf.py`: sets the switches the tagged CLI reads on every child process |
| No cloud render, publish, sign-in, capture, or provider call | `hf.py` allowlist, and `config.yaml` deny rules |
| Writes stay in the workspace | `hf.py` path checks on the working directory and every path argument |
| Nothing from a reference video in a project | `hf.py` reference exclusion, on every render, lint, check, snapshot, and preview |
| No final render without a style decision | `hf.py` style-decision preflight |
| No silent render from a missing `id` | `hf.py` timed-media check, and upstream lint |
| Source footage unchanged | `hf.py` checksum manifest, re-checked before every final |
| Workers sized to the machine | `hf.py` plans from measured memory and records the peak |

`config.yaml` then denies the plain command forms that go around the launcher, at the Hermes approval floor. `docs/permissions-and-security.md` says exactly what that does and does not cover.

## Tree changes from the usual layout

The vendored skills sit at `skills/hyperframes-video/skills/<name>/`, one folder deeper than a flat category. Upstream helper scripts find the CLI by looking for `plugin.json` two folders above each `SKILL.md` (`skills/embedded-captions/scripts/hf-cli.cjs` at the pinned tag). Keeping upstream's plugin layout makes those scripts resolve the pinned release. Hermes discovers skills recursively, and the install tests confirm all 16 load at that depth.

## The effects layer (1.1.0)

`skills/video-effects-core/` adds 17 skills and an effects library beside them. The library is data, not a skill: one folder per effect with `effect.json` (the catalog entry), the templates it writes into a composition (`style.css`, `defs.svg`, `markup.html`, `update.js`), its `verification.json`, and its reference stills. `catalog.yaml` is generated from those folders by `scripts/build_catalog.py`.

`fx.py` applies an effect by writing marked blocks into `index.html` from `fx-instances.json`, which lists what is applied. `fx-runtime.js` drives every original effect from one GSAP clock, as a pure function of composition time, so a frame seeked alone matches the same frame in sequence. Effects that wrap HyperFrames features write HyperFrames' own attributes instead: `data-color-grading`, `data-vfx-chain`, `data-fx-chain`, or a `HyperShader.init` call. Removing an effect restores the composition byte for byte.

An effect counts only after the 12-check gate passes in an installed temporary profile. See [effects/verification.md](effects/verification.md).

## State and where it lives

| State | Location | Owned by the distribution |
| --- | --- | --- |
| Identity, config, skills, templates, notices | the profile root | yes, replaced on update |
| Editor profile, brand identity, style library | `local/` in the profile | no, preserved |
| Toolchain, approvals, browser record | `local/video-editor/video-engine/` | no, preserved |
| Owner effects and effect recipes | `local/effects/`, `local/effect-recipes/` | no, preserved |
| Applied effects for one project version | `fx-instances.json` beside its `index.html`, in the workspace | no, preserved |
| Footage, working copies, references, projects, renders | the owner-approved workspace | no, outside the profile |
| Credentials, memory, sessions | Hermes user paths | no, preserved |

## Modes

Two modes ship. `offline` when the toolchain is not verified, and `edit_and_render` once it is. No research mode with a platform credential ships, and no external-services mode ships, because neither met its bar: see `docs/research-sources-and-platform-terms.md` and `docs/permissions-and-security.md`.

## What is tested, and how

- `tests/test_tools.py`: measurement tools and evidence rules against synthetic ground truth.
- `tests/test_gates.py`: every launcher gate, against a stand-in CLI, with no render.
- `tests/test_install.py`: install, payload, update, deny rules, and a Kanban exchange, against real Hermes releases.
- `tests/test_renders.py`: every editing operation the README claims, rendered from an installed temporary profile and checked by pixel and by audio measurement.

Recorded results are in `docs/test-results/`.
