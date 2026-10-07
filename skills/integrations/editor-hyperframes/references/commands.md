# Launcher and tool commands

The launcher is `skills/integrations/editor-hyperframes/scripts/hf.py` in the installed profile. The measurement tools are `editor_tools.py` beside it. Both are standard-library Python.

## Agent commands

Run from a version folder inside the approved workspace.

| Command | What it does |
| --- | --- |
| `hf.py status` | Reports the video engine (`not configured` or `toolchain verified`), research (`owner-supplied only`), and each missing piece. No network. |
| `hf.py doctor --deep` | Also runs the pinned CLI's own doctor and checks the version that runs is the pinned one. |
| `hf.py pin` | Prints the pinned release. |
| `hf.py init <version>` | Scaffolds a version folder under `projects/<video-id>/`, strips npm scripts, and vendors the local GSAP build. |
| `hf.py lint`, `hf.py check`, `hf.py validate`, `hf.py inspect`, `hf.py layout` | The pinned CLI's checks. Refused when reference material is in the project. |
| `hf.py timeline --json` | The project's tracks and clips. |
| `hf.py snapshot --at <t1,t2>` | PNG frames for inspection. The external vision option is turned off. |
| `hf.py compare <a> <b> --at <t> --labels x,y --out <file.png>` | One labeled sheet from two or more versions at the same instant. |
| `hf.py grade-compare`, `hf.py media-treatment`, `hf.py normalize-audio` | Local color and audio commands, as documented in the bundled `hyperframes-cli` and `media-use` skills. |
| `hf.py catalog` | Local registry search. It installs nothing. |
| `hf.py transcribe <file>` | Local transcription, only after the owner installed the speech model. |
| `hf.py render --stage draft` | Draft render and receipt. Add `--comparison house_style` (or `outlier_matched`, `hybrid`) when no style decision is recorded. |
| `hf.py render --stage final` | Final render and receipt, after the gates pass. |
| `hf.py receipt --stage draft <file>` | A receipt for an existing render. |
| `hf.py preview-start`, `hf.py preview-status`, `hf.py preview-stop` | The local preview on 127.0.0.1, and its teardown. |
| `hf.py footage-add <file>`, `hf.py footage-verify` | Register originals, and prove none changed. |
| `hf.py rights-check`, `hf.py hosts-check`, `hf.py references-check`, `hf.py style-check`, `hf.py ids-check` | Each gate on its own. |
| `hf.py plan-workers`, `hf.py limits` | The worker plan from measured memory, and the longest render on record per resolution. |
| `hf.py handoff <rendered-file>` | Copy a receipt-backed render to the approved handoff folder. |
| `hf.py vendor-gsap` | Point a composition at the lockfile-installed GSAP build. |
| `hf.py script <bundled-script>` | Run a bundled HyperFrames helper script, pinned. |
| `hf.py history`, `hf.py clean`, `hf.py docs`, `hf.py usage`, `hf.py info`, `hf.py compositions`, `hf.py keyframes`, `hf.py beats` | Pass-through to the pinned CLI. |

Refused always: `skills`, `upgrade`, `publish`, `cloud`, `lambda`, `cloudrun`, `auth`, `feedback`, `events`, `telemetry`, `open`, `catch-up`, `figma`, `capture`, `media-use`, `tts`, `remove-background`, `add`, `models`, `browser`, `play`, `present`, `preview`, `benchmark`.

## Measurement tools

| Tool | What it measures |
| --- | --- |
| `editor_tools.py probe <file>` | Container, codecs, frame rate and mode, rotation, color transfer, audio, SHA-256, and risk flags. |
| `editor_tools.py working-copy <file>` | Writes a constant-frame-rate SDR copy under `working-copies/` and proves the original is unchanged. |
| `editor_tools.py cuts <file> --threshold 0.30 --min-shot 0.20` | Cut times, time to first cut, and shot-length distribution. |
| `editor_tools.py audio-profile <file>` | Integrated loudness, true peak, clipping, and silence gaps. |
| `editor_tools.py duck-check <file> --speech <intervals.json>` | Level in speech windows against the gaps. |
| `editor_tools.py frames <file> --schedule short-form` | Session-only frames on a recorded schedule. |
| `editor_tools.py contact-sheet <file> --out <sheet.jpg>` | One tiled image. Refused for reference videos. |
| `editor_tools.py session-clean` | Deletes sampled frames. |
| `editor_tools.py outlier-score <dataset.json>` | Views over the account's baseline median, ranked, with no cutoff. |
| `editor_tools.py dead-air <words.json>` | Keep-ranges from word timings, as a proposal. |
| `editor_tools.py safe-zone <overlay-plan.yaml>` | Overlay boxes against a sourced safe zone. |
| `editor_tools.py check-study`, `check-blueprint`, `check-proposal` | The evidence rules for studies, blueprints, and proposals. |

## Owner commands

The owner runs these in their own terminal. The profile's configuration denies them to the agent. Each download shows its item, source, size, and license and asks for confirmation.

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" setup --plan
```

| Command | What it does |
| --- | --- |
| `hf.py setup --plan` | Lists every step and download. Changes nothing. |
| `hf.py setup --workspace <folder>` | Approves the video workspace and creates its folders. |
| `hf.py setup --install-cli` | Installs the pinned CLI and GSAP from the shipped lockfile with `npm ci`. |
| `hf.py setup --download-browser` | Downloads the headless Chrome build the pinned CLI expects. |
| `hf.py setup --use-browser <path>` | Records a headless Chrome already on the machine. No download. |
| `hf.py setup --install-model parakeet` | Optional. Installs the local speech model. |
| `hf.py setup --allow-host <host>` | Approves a render-time host a composition loads from. `--deny-host <host>` removes it. |
| `hf.py setup --handoff <folder>` | Optional. Approves a folder for delivering renders to teammates. |
| `hf.py setup --add-registry-item <name> --project <version-folder>` | Optional. Fetches one registry item from the upstream main branch and records its file hashes. |
| `hf.py setup --remove cli` | Removes the toolchain. Also `browser`, `model`, or `all`. |
