# Upstream facts this wrapper relies on

Each fact was read from HeyGen HyperFrames at tag `v0.8.183` (commit `7e2817619f340f9302eeaef185e73be39a19858d`) on 2026-10-21. The first reading was at `v0.8.138` on 2026-10-06; every row was re-read at the new tag. The path names the upstream file. HyperFrames changes often, so a fact here is true for the pinned release only.

| Fact | Upstream source |
| --- | --- |
| A composition is HTML. Timing lives in `data-start`, `data-duration`, `data-media-start`, `data-track-index`, `data-playback-rate`, and `data-has-audio`. Consumed source equals timeline duration times rate. | `skills/hyperframes-core/references/creator-editing-recipes.md` |
| Timed media without an `id` fails lint with `media_missing_id`. An `<audio>` with no `id` is not picked up by the mixer, so the render is silent. | `skills/hyperframes-core/references/creator-editing-recipes.md` |
| Zoom, pan, crop, and mask target an inner wrapper, not the timed clip element. Reframing is authored geometry, not face tracking. | `skills/hyperframes-core/references/creator-editing-recipes.md` |
| A freeze uses a still image. An arbitrary mid-source freeze needs a still extracted first. | `skills/hyperframes-core/references/creator-editing-recipes.md` |
| Volume over time uses a `data-automation` volume lane. A lane and a volume tween on one track conflict, and the lane wins. | `skills/hyperframes-core/references/creator-editing-recipes.md` |
| A sub-composition is a separate file loaded with `data-composition-src`. Only the contents of its `<template>` reach the render. | `skills/hyperframes-core/references/sub-compositions.md` |
| Variables are declared on `<html>` with `data-composition-variables`. `render --batch` takes a JSON array of rows and an output template. | `skills/hyperframes-core/references/variables-and-media.md`, `skills/hyperframes-cli/references/compare-and-batch.md` |
| Color treatment is a `data-color-grading` attribute, written by the `media-treatment` command. | `skills/media-use/references/grading.md` |
| `HYPERFRAMES_SKIP_SKILLS=1` stops `init` and the CLI from refreshing skills. `HYPERFRAMES_NO_UPDATE_CHECK` and `HYPERFRAMES_NO_AUTO_INSTALL` stop update checks and auto-install. `HYPERFRAMES_NO_TELEMETRY` and `DO_NOT_TRACK` stop telemetry. | `packages/cli/src/utils/skillsUpdateCheck.ts`, `packages/cli/src/utils/autoUpdate.ts`, `packages/cli/src/commands/init.ts`, `packages/cli/src/telemetry/policy.ts` |
| Bundled helper scripts find the CLI through a `plugin.json` two folders above each `SKILL.md`, which is why the bundle keeps a `skills/` folder under `skills/hyperframes-video/`. | `skills/embedded-captions/scripts/hf-cli.cjs`, `skills/hyperframes/references/plugin-installation.md` |
| The registry is fetched from the upstream `main` branch, not from the pinned release. | `packages/cli/src/registry/remote.ts` |
| The pinned CLI expects the `chrome-headless-shell` build `152.0.7977.30`. | `packages/cli/src/browser/manager.ts` |
| `snapshot --describe` sends frames to a vision provider and runs by default when a provider key is set. The launcher removes provider keys and passes `--describe false`. | `packages/cli/src/commands/snapshot.ts` |
| `usage --json` detects only some coding harnesses. Under Hermes it returns `status: unknown`. | `packages/cli/src/commands/usage.ts` |
| Background removal needs the optional `onnxruntime-node` package (a dev dependency of the CLI, pinned at 1.21.1 upstream) and downloads a `u2net_human_seg` model on first run. Neither is in this profile's lockfile, so it is unavailable. | `packages/cli/src/background-removal/manager.ts`, `packages/cli/src/background-removal/inference.ts` |
| The speech model `parakeet` is CC-BY-4.0 and runs on `sherpa-onnx`, Apache-2.0. | `CREDITS.md` |
| Upstream states each render worker starts a Chrome process of roughly 256 MB. On the release test machine the measured peak for the whole render process tree was about 600 to 1,060 MB with one to three workers. | `packages/cli/src/commands/render.ts`, `skills/hyperframes-cli/references/preview-render.md`; the measured figures are from this profile's release tests |
| Media effects and color looks are one `data-color-grading` JSON value with the sections `adjust`, `wheels`, `curves`, `hueCurves`, `secondaries`, `details`, `effects`, `palette`, and `lut`. It has 18 named presets (13 grades and 5 effect looks), 15 palettes, and 18 media effects. Unknown keys fail validation. | `packages/parsers/src/colorGradingContract.ts`, `packages/core/src/colorGrading.ts`, `docs/guides/media-effects.mdx` |
| Media effects run on the SDR pipeline. A native HDR layer keeps its HDR pixels on a separate path, so effects do not appear on it. | `docs/guides/media-effects.mdx` |
| Shader transitions are a closed set of 14 named shaders in `@hyperframes/shader-transitions`, loaded by the composition's own script and started with `HyperShader.init`. A transition with no `shader` is a CSS crossfade. Custom fragment shaders are not supported. | `skills/hyperframes-animation/transitions/overview.md`, `packages/shader-transitions/src/` |
| `data-vfx-chain` accepts three kernels: `fractal-noise`, `wave-warp`, and `displacement-map`. An unknown kernel throws. | `packages/core/src/vfx.ts` |
