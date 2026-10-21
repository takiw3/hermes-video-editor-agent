# Changelog

This project follows semantic versioning. Changes to distributed files, vendored code, permissions, or escalation rules are made here, visibly, and never by the agent editing itself.

## Unreleased

### Fixed

- The install tests now import Hermes only from `HERMES_SRC`. Before, a module missing from the release under test could load from an editable Hermes install in the same venv. A new check fails if anything else is imported. Results on 0.21.4 and 0.21.5 are unchanged.

## 1.0.0 - 2026-10-06

Release status: edit-and-render release.

### Added

- The `video-editor` Hermes Profile Distribution: identity, provider-neutral configuration, routing description, and a narrow `distribution_owned` allowlist.
- 25 post-production skills under `skills/video-editor-core/`, from intake to weekly review.
- The outlier-first workflow: outlier scoring relative to each account's own baseline, contrast sets, style blueprints with evidence tags, three-option style-match proposals, and a recorded style decision or one-edit waiver.
- `editor-hyperframes`, the wrapper skill, with a pinned launcher (`hf.py`) and deterministic measurement tools (`editor_tools.py`).
- HeyGen HyperFrames `v0.8.138` (commit `0ca28db4f8671a2e2262594e03c566222d695920`) as a derivative with recorded patches: 15 published skills and the internal `captions-overlay` skill, with a lock file of every checksum, patch, removed file, and asset license.
- Launcher gates: pinned CLI from a lockfile, self-update and telemetry switches, subcommand allowlist, workspace boundary, reference-folder exclusion, style-decision preflight, timed-media id check, rights and footage checks before a final render, worker planning from measured memory, and render receipts.
- 23 templates, with field names shared with the `social-media` profile where the two exchange work.
- Tests: measurement tools against synthetic ground truth, launcher gates against a stand-in CLI, installation and update on Hermes 0.21.4 and 0.21.5, a Kanban exchange with a temporary `social-media` profile, and renders of every claimed editing operation checked by pixel and by audio measurement.
- 82 synthetic behavior evaluation fixtures.
- Platform specifications and terms of service, each recorded with its URL and access date.

### Not shipped, on evidence

- `connected_research` mode. No platform passed every condition.
- `approved_external_services` mode. No hard action gate can be built inside one operating-system user.
- `music-to-video` and `product-launch-video`, and the internal skills `motion-doctrine`, `cut-the-curve`, and `seam-craft`.
- Background removal. Its runtime package and model are not in the pinned lockfile.

### Known limits

- The bundled upstream workflows were loaded in an installed profile and not rendered end to end.
- Long-form was tested at draft quality on one machine.
- Renders and installs were tested on macOS with Apple silicon only. CI runs the measurement and launcher-gate suites on Ubuntu.
