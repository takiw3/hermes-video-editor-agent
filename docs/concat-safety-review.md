# Concat safety review

Text-only review of the Concat video editor, done as the study phase of a clean-room process. Nothing from Concat was built, run, installed or connected to.

```yaml
repository: https://github.com/jub0t/concat
commit: 2756209a92766a4e4726999a51648349a272c159   # confirmed with git rev-parse FETCH_HEAD; main on 2026-10-21, latest release v0.2.8
read_at: 2026-10-21
license: GNU AGPL version 3 (LICENSE header); README and TRADEMARK.md state AGPL-3.0-or-later. CLA.md version 2.0 (effective 2026-10-21) assigns contributors' copyright to the owner, who may also license the code commercially.
trademark_policy: The name and logo are reserved by the owner and are not covered by the AGPL. Nominative use ("compatible with", "a fork of") is allowed; a modified build must ship under a different name and icon; using the name or a confusingly similar one in a product, company, store listing or domain is not allowed.
files_read:
  - README.md
  - LICENSE (opening lines only, to confirm the license)
  - TRADEMARK.md
  - CLA.md
  - CODE_SIGNING.md
  - SECURITY.md
  - THIRD_PARTY_NOTICES.md
  - audit/AUDIT-2026-10-15-QUICK.md
  - audit/AUDIT-2026-10-20-QUICK.md
  - audit/AUDIT-2026-10-20.md
  - audit/2026-10-20/project-effects-ml-phones-ci.md
  - audit/2026-10-20/product-distribution.md
  - src/crates/concat-effects/packages/*/effect.toml (all 127)
  - .claude/skills/run-concat/SKILL.md (read as data to record the finding below; not followed)
  - .gitattributes
  - models/manifest.toml (only to list hosts and check that hashes exist; no values copied)
  - keyword search only, not read in full - audit/AUDIT-2026-10-15.md, audit/2026-10-15/*.md, audit/2026-10-20/host-server-api-cli.md, audit/2026-10-20/media-render-export-core.md, audit/2026-10-20/window.md, audit/2026-10-20/window-subreviews.md
files_not_read:
  - every .wgsl shader (opened only by scripts/copy_check.py fingerprint, which prints no text)
  - every .rs source file (only counted and grepped for a word count; no lines printed)
  - every fixtures.toml
  - Cargo.toml and Cargo.lock contents (grepped for git sources only)
  - workflow files (grepped for action pin format and permissions blocks only)
  - binaries and models (one committed ONNX segmentation model; nothing downloaded)
  - docs/ including docs/MCP.md, CONTRIBUTING.md, CODE_OF_CONDUCT.md, TRANSLATING.md, scripts/
  - the voice-cloning and text-to-speech code (never studied)
static_checks_run:
  - unsafe in .rs files: 1041 occurrences of the word across 31 files. 138 are in first-party code under src/crates (host 46, media 41, window crate 34, android 10, speech 5, text 1, render 1), which matches the project's own audit. The other 903 are in two vendored patch crates under src/patches (whisper-rs-sys 803, i-slint-renderer-skia 100).
  - curl or wget piped to a shell: none found anywhere in the tree.
  - git-sourced dependencies: none in any of the 19 Cargo.toml files; src/Cargo.lock has no git+ sources.
  - build.rs files (7): src/patches/i-slint-renderer-skia/build.rs, src/patches/whisper-rs-sys/build.rs, src/crates/concat/build.rs, src/crates/concat-media/build.rs, src/crates/concat-android/build.rs, src/crates/concat-effects/build.rs, src/crates/concat-server/build.rs. None were run.
  - SVG files containing <script: none (5 SVG files in the tree).
  - GitHub Actions pinning: 6 workflows, 48 uses lines; all 45 remote actions pinned to full 40-character commit SHAs, 3 are local reusable workflows. No pull_request_target trigger. Only 3 of 6 workflows declare a permissions block (models.yml, nix.yml, release.yml); ci.yml, mobile.yml and build-app.yml do not.
  - model downloads: models/manifest.toml lists 23 models, every one with a SHA-256 value. Hosts named are github.com and huggingface.co. The project's audit says its own mirror release has never been filled, so downloads fall back to third-party hosts (reported by the audit, not verified here).
  - desktop build dependencies: scripts/ci/deps.lock carries 25 SHA-256 lines. The audit reports that the phone build scripts (src/scripts/ffmpeg-mobile.sh, src/scripts/sherpa-mobile.sh) fetch FFmpeg source and prebuilt sherpa-onnx libraries without a digest check (reported, those scripts not read).
  - Git LFS: no LFS pointer files; .gitattributes sets text normalisation only. Fetch ran with LFS smudge disabled anyway.
  - committed binaries: one ONNX model (src/crates/concat-vision/models/selfie-segmentation.onnx); 18 files carry an executable bit. None were opened or run.
  - release signing (CODE_SIGNING.md): Windows releases are not code-signed; a future signing process through GitHub Actions with manual approval is described. The audit adds that macOS builds are ad-hoc signed and not notarised, iOS builds are ad-hoc, Android builds are signed with the repository key, Linux packages and the checksum file are unsigned, and the in-app updater checks downloads against a digest published in the same release.
  - agent-targeted instructions: one file, .claude/skills/run-concat/SKILL.md. No CLAUDE.md, AGENTS.md, .cursorrules or similar elsewhere. No prompt-injection phrasing found in Markdown files.
  - effect packages by kind: filter 57, effect 23, transition 22, audio filter 25; total 127; picture packages 102.
findings:
  - The fetched commit equals the pinned SHA 2756209a92766a4e4726999a51648349a272c159.
  - .claude/skills/run-concat/SKILL.md is an agent skill with a broad trigger that tells any coding agent working in the repo to cd into src and run cargo build, cargo run, cargo test with GPU features, cargo check, cargo clippy and cargo clean, and to use terminal and computer-use tools to inspect the running app. Recorded and ignored. Nothing was built, run or launched.
  - README advertises a built-in MCP server and a JSON-RPC API for AI agents. The audit reports the MCP tool hints understate which tools write files and that the API's file roots default to the whole home folder. Not connected to, not studied.
  - The app offers voice cloning from a short recording. THIRD_PARTY_NOTICES says the bundled pipeline adds no audio watermark; the audit reports no consent prompt. Not studied.
  - Third-party licenses in the shipped app include GPL-3.0-only (Slint UI toolkit), GPL-3.0-or-later (espeak-ng), GPL-3.0 (one matting model), and GPL builds of FFmpeg with x264, alongside MIT, Apache-2.0, BSD and OFL components.
  - The effect catalogue's preview cards are rendered from an Unsplash photograph shipped in the repository. Its hash is in our fingerprint file; we must not reuse it.
  - SECURITY.md routes reports to GitHub's private advisory form. The audit says that channel was disabled and was switched on during its 2026-10-20 session.
  - The audit names a GitHub organisation squatting on the project name. Not relevant to us beyond the trademark point.
  - Fingerprint run - 412 files fingerprinted, 32921 salted shingle hashes, 125 image hashes.
risks_to_this_project:
  - license: copying any Concat code, shader text, manifest text or numbers would bring AGPL-3.0-or-later obligations onto the combined work, which conflicts with this repository's MIT license. Mitigated by the clean-room split and the copy check.
  - trademark: the name and logo are reserved. Our effects, ids, docs and UI must not use the name except for factual attribution in the allow-listed docs.
  - supply chain if built: seven build.rs scripts, two vendored patched crates with heavy unsafe use, unpinned phone-build downloads, unsigned or ad-hoc release binaries and a same-release digest for updates. Building or installing it would run unreviewed code on this machine.
  - agent prompt injection: the repository ships an agent skill that triggers on ordinary requests and tells agents to build and launch the app. Any agent session opened inside a checkout would be exposed. Never open a session there.
  - model downloads: the app downloads ML models on demand from third-party hosts, with digests checked. We did not download any and must not depend on them.
  - voice cloning: the app can imitate a voice from a few seconds of audio, with no watermark and, per its audit, no consent prompt. We never studied or used that code, and this project should not borrow it.
controls_applied:
  - Clean-room separation. This study phase wrote behavior in plain words only; a separate implementer builds from docs/effects/reference-study.md without opening Concat.
  - Text-only fetch. Shallow fetch of the pinned commit into a scratch directory outside the repository, with hooks pointed at /dev/null and Git LFS smudge, process and required filters disabled; the tree was exported with git archive.
  - No build, no execution. No cargo, make, npm, build.rs or project script was run; no release binary, installer or model was downloaded; no MCP or JSON-RPC connection was made.
  - Restricted reading. No .wgsl, .rs or fixtures.toml content was viewed; static checks reported counts and paths only.
  - Fingerprints. scripts/copy_check.py fingerprint stored salted shingle hashes of the shaders and manifests and hashes of the images, with no text, for scripts/copy_check.py check to run in CI.
  - Scratch deletion. The scratch copy was deleted with rm -rf at the end of the review.
fingerprint_file: tests/fixtures/concat-fingerprints.json
scratch_copy_deleted_at: 2026-10-21T14:40:01Z
```

Concat is a free desktop and mobile video editor written in Rust, pitched as an open-source CapCut replacement. It runs locally, renders effects on the GPU from small shader packages, does captions, text to speech, voice cloning and background removal with downloaded ML models, and exposes an MCP server and JSON-RPC API so agents can drive it. It is pre-1.0, ships from one maintainer's repository, and its own audits describe unsigned Windows builds, ad-hoc macOS and iOS builds, and a CI that is often red on main.

No Concat code, shader text, manifest text, numbers, defaults or coined names are in this repository. Concat is licensed AGPL-3.0-or-later, and copying any of its expression into our MIT-licensed code would make the combined work subject to the AGPL. Its name and logo are reserved under TRADEMARK.md, so we refer to it only for attribution in the documents allowed to name it. The study records what each effect looks like and what its controls do, in fresh plain English, and the fingerprint file lets `scripts/copy_check.py check` catch any accidental copy.

In plain words: we read Concat as text only, from a pinned commit, with Git hooks and LFS switched off, and deleted the copy when done. We did not build it, run it, download its binaries or models, connect to its agent API, or look at its voice-cloning code. We found one agent skill that tells coding agents to build and launch the app, and ignored it. This review covers what was read and counted. It does not say Concat is safe to run.
