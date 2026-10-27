# Clean-room process

This profile's effects come from three routes, tried in this order:

1. **Effects HyperFrames already ships.** Media effects, color presets, the color grading engine, the 14 shader transitions and the crossfade, the `data-vfx-chain` kernels, and the audio effects. We wrap them, give them a catalog entry and verify them. We do not copy their code; it stays in the pinned HyperFrames packages.
2. **Original effects in the composition.** CSS filters, SVG filters, GSAP timelines and canvas drawing, written for this profile under MIT.
3. **Behavior studied clean-room** from another editor, Concat (`https://github.com/jub0t/concat`, AGPL-3.0-or-later). We learned what its effects look like on screen. We never used its code.

## Why clean-room

Concat is AGPL-3.0-or-later. Copying any of its code, shader text, manifest text, preset numbers, images or coined names into this MIT repository would put AGPL obligations on the combined work. Its name and logo are also reserved under its trademark policy. So two separate roles did the work, and nothing crossed between them except plain-language descriptions.

## The two roles

**Study (one agent, once, then deleted).**
- Fetched the pinned commit `2756209a92766a4e4726999a51648349a272c159` as text only, into a scratch folder outside this repository and outside any profile home. Git hooks were pointed at `/dev/null`, and Git LFS smudge and filters were off.
- Never built, ran, installed or tested Concat. No `cargo`, no release binary, no model download, no MCP or JSON-RPC connection, no voice-cloning code.
- Read the effect manifests and the project's own docs and audits. Opened no shader (`.wgsl`), Rust (`.rs`) or fixture file.
- Wrote [reference-study.md](reference-study.md): what each effect looks like and what its controls do, in fresh words, with no numbers, defaults, ranges, code or coined names.
- Fingerprinted the shaders, manifests and images into `tests/fixtures/concat-fingerprints.json`, which holds salted hashes only, then deleted the scratch copy (2026-10-21T14:40:01Z).
- Wrote the [safety review](../concat-safety-review.md), including one agent skill in the repository that tells coding agents to build and launch the app. It was recorded and ignored.

**Implementation (a different session).**
- Read only `reference-study.md`. Never opened a Concat file.
- Designed every effect from the behavior description and its own judgment: its own parameter names, ranges, defaults and code.
- Each clean-room effect's `reference_id` (`RS-001` to `RS-102`) points at its study entry. It carries no name from the studied project.

## How copying would be caught

`scripts/copy_check.py check` runs in CI and in `scripts/validate.py`:

- **Shingles.** Every shader, script, style, markup, manifest and catalog file here is cut into 8-token shingles after comments are stripped and tokens lowercased. Each shingle is hashed with the stored salt and compared with the studied project's hashes. A file fails when it shares more than 3 shingles.
- **Syntax-only shingles don't count.** A shingle made only of punctuation, keywords, one- or two-letter names, single-digit numbers and position words (`left`, `top`, `width`) carries no expression. A WGSL loop header reads exactly like a JavaScript one. Without this rule every `for (var i = 0; i < n; i++)` would match.
- **Images.** Any image whose SHA-256 matches a studied image fails. That includes the photograph the studied editor uses for its preview cards.
- **The name.** The project's name may appear only in the documents allowed to name it, for attribution. The vendored HyperFrames tree is exempt from the name check only: upstream uses the word for FFmpeg's concat step, and those files are verified byte for byte against their upstream tag. The shingle check still runs on them.

Each effect's verification gate runs the same shingle check on its own source files (check 12).

## If the owner asks for the real code

Stop. This profile does not copy another project's code, whatever its license, and does not build or run another editor.
