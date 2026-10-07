# Third-party notices

The original work in this repository is licensed under the MIT License, Copyright (c) 2026 TakiGPT AI Inc. See `LICENSE`.

The material below is not original to this repository and is not relicensed.

## HeyGen HyperFrames skills

- Location: `skills/hyperframes-video/` (derived, installed with the profile) and `vendor/upstream/hyperframes/` (exact upstream copy, repository only).
- Source: https://github.com/heygen-com/hyperframes
- Release: `v0.8.138`, commit `0ca28db4f8671a2e2262594e03c566222d695920`, published 2026-10-06.
- License: Apache License, Version 2.0. Copyright 2026 HeyGen, Inc.
- License text: `skills/hyperframes-video/LICENSE` and `vendor/upstream/hyperframes/LICENSE`. Both are the upstream file, unchanged.
- NOTICE file: upstream ships none at the pinned tag. Upstream's `CREDITS.md` is reproduced unchanged at `skills/hyperframes-video/CREDITS.md`.

`skills/hyperframes-video/` is a derivative work. TakiGPT AI Inc. modified 88 of the 606 vendored skill files so the skills run safely inside a Hermes profile. Each modified file carries a prominent notice stating that it was changed. The rules applied and the full list of modified files are in `skills/hyperframes-video/MODIFICATIONS.md` and in `vendor/hyperframes.lock.yaml`. Every other file is byte-identical to upstream.

This project is not affiliated with, sponsored by, or endorsed by HeyGen. "HeyGen" and "HyperFrames" are used only to identify the upstream work.

### Internal upstream skill

`captions-overlay` comes from `.claude/skills/captions-overlay/` in the upstream repository, not from the published `skills/` set. Upstream marks it `metadata.internal: true` and describes that folder as repo-native. It is covered by the repository's Apache-2.0 license at the pinned tag. It is a single text file with no assets, it is not tracked with Git LFS, and it is installed at `skills/hyperframes-video/skills/captions-overlay/` with a notice saying it is internal upstream material that may change or disappear without notice.

### Attribution carried inside the skills

`talking-head-recut` is adapted by upstream from the vtake-skills project (https://github.com/notedit/vtake-skills), MIT License, Copyright (c) 2026 leeoxiang. Upstream's notice and the MIT text are preserved unchanged at `skills/hyperframes-video/skills/talking-head-recut/NOTICE.md`.

## Assets bundled inside the HyperFrames skills

Recorded per group in `skills/hyperframes-video/ASSET-LICENSES.md` and in the lock file's `asset_licenses`. The build fails if any binary or media file in the derivative matches no group.

| Assets | Count | License | Where the terms are |
| --- | --- | --- | --- |
| Sound effects, `media-use/audio/assets/sfx/*.mp3` | 19 | Pixabay Content License | `media-use/audio/assets/sfx/CREDITS.md` (upstream) and https://pixabay.com/service/license-summary/ |
| Fonts, `hyperframes-creative/frame-presets/code-editorial/fonts/` (Inter, EB Garamond, JetBrains Mono) | 6 | OFL-1.1 | `OFL-*.txt` beside the fonts (upstream) |
| Fonts, `embedded-captions/modes/standard/fonts/files/` (22 families) | 42 | OFL-1.1 | `skills/hyperframes-video/licenses/OFL-1.1.txt` and `licenses/FONT-COPYRIGHTS.md` |
| Fonts, same folder (Permanent Marker, Special Elite) | 2 | Apache-2.0 | `skills/hyperframes-video/licenses/Apache-2.0.txt` |
| `embedded-captions/modes/standard/fonts/fonts.css` (the 44 fonts above, base64-inlined by upstream) | 1 | OFL-1.1 AND Apache-2.0 | as above |
| Fonts, `talking-head-recut/assets/fonts/` (Caveat, Inter, LXGW WenKai TC) | 5 | OFL-1.1 | `licenses/OFL-1.1.txt` and `licenses/FONT-COPYRIGHTS.md` |
| Stroke fonts, `embedded-captions/assets/strokefonts/*.svg` (Hershey) | 2 | Hershey Fonts license | the license text inside each SVG file |

Upstream ships the 44 caption fonts and the five talking-head fonts with no license file beside them. Each family's license was recorded on 2026-10-06 from its `@fontsource` package metadata on npm and from the license URL embedded in the font file, and the license texts were added to the derivative. One family, Monoton, has a copyright line and no license URL in its font file; its OFL-1.1 status rests on the fontsource record.

The Pixabay Content License permits commercial use without attribution and does not permit selling or redistributing the files on a standalone basis. Upstream does not record a per-file Pixabay URL, so the original uploader of each sound is not identified here.

### Not shipped

Two upstream files are withheld from both the derivative and the audit copy, because their license could not be confirmed as permitting redistribution here:

- `talking-head-recut/assets/fonts/Virgil.woff2`. The font's embedded metadata reads "Freeware for personal use! For commercial license ...", while https://github.com/excalidraw/virgil publishes Virgil under OFL-1.1. The two statements conflict.
- `talking-head-recut/assets/vendor/gsap.min.js` (GSAP 3.15.0). See GSAP below.

Their upstream checksums are in `vendor/hyperframes.lock.yaml` under `removed_files`.

Two published skills are left out because of their assets or inputs, not their code. `music-to-video` ships 66 PNG texture masks and one font with no license record in the skill or in upstream `CREDITS.md`. `product-launch-video` starts from a live website capture. The reasons for every excluded skill are in `vendor/hyperframes.lock.yaml`.

No registry item and no theme from the upstream repository is vendored.

## GSAP

No GSAP file is distributed in this repository.

GSAP is licensed by Webflow under the GSAP Standard License (titled Standard "No Charge" GSAP License), https://gsap.com/standard-license, effective April 30, 2025, last modified May 30, 2025, read on 2026-10-06. It is not an OSI open-source license. In summary:

- It grants a non-exclusive, worldwide license to use, reproduce, display, and implement GSAP products solely for Permitted Uses: implementation or use on any website, web application, or digital interface, by any person or entity, including commercial projects, at no charge.
- It prohibits use in tools that let users build visual animations without code in a way that competes with Webflow's visual animation building, reverse engineering to create competitive products, and removing or altering proprietary notices or branding.
- Webflow retains all intellectual property rights and may terminate the license for non-compliance.

The license does not expressly grant redistribution of the library file inside another project, so the upstream copy is withheld and nothing here bundles one. Instead:

- The owner-run toolchain setup installs `gsap@3.14.2` from the npm registry, from the pinned lockfile. The owner receives it from npm under the license above.
- The launcher copies that installed build into each of the owner's own projects, so a render needs no CDN. That is the owner's use of GSAP in the owner's project, recorded in the project's rights register.
- A composition that pins another GSAP version (for example 3.15.0 in `talking-head-recut`) loads it from the jsDelivr CDN at render time, from a host the owner approves.

Rendering a video with GSAP is a use of the library in a digital interface. The owner should read the license themselves.

## Fonts and other CDN libraries

Some upstream compositions reference Google Fonts or other CDN-hosted libraries. The renderer fetches them at render time only from hosts the owner has approved. They are not distributed here.

## Installed by the owner during setup, not distributed here

- **HyperFrames CLI** (`hyperframes@0.8.138`, Apache-2.0, HeyGen, Inc.) and its dependency tree: 172 packages, including GSAP, pinned with integrity hashes in `skills/integrations/editor-hyperframes/toolchain/package-lock.json`. Each package is under its own license, readable in the lockfile and in `node_modules` after install. The tree includes `sharp` (Apache-2.0) with platform builds of `libvips` (LGPL-3.0-or-later), `puppeteer-core` (Apache-2.0), and `esbuild` (MIT).
- **Headless Chrome** (`chrome-headless-shell`, build 152.0.7977.30 for the pinned CLI), from Chrome for Testing, under the Chromium project's open-source licenses.
- **Parakeet TDT 0.6B v3** speech model by NVIDIA, optional, CC-BY-4.0, in the int8 ONNX export from `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8`, run with sherpa-onnx (Apache-2.0).
- **FFmpeg** and **Node.js**, installed by the owner independently, under their own licenses.

A registry item, when the owner fetches one, comes from the upstream repository's `main` branch under that repository's license. Upstream `CREDITS.md` lists items that vendor or load third-party code (three.js, GSAP, opentype.js, Clipper, d3-delaunay) and a few assets whose origin upstream has not confirmed. The fetch records file hashes, and the item needs an entry in the project's rights register before use.

## Development and CI

GitHub Actions `actions/checkout`, `actions/setup-python`, and `actions/setup-node` (MIT), each pinned to a full commit SHA. PyYAML (MIT) for validation scripts. fontTools (MIT) is used only when regenerating `FONT-COPYRIGHTS.md`.
