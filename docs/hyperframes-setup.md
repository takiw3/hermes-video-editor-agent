# Video toolchain setup

Installing the profile installs the profile and its skills. It does not install or download anything else. This page is the separate, owner-driven setup step that makes editing and rendering work.

You run these commands yourself, in your own terminal. The profile's configuration denies them to the agent, and each download asks you to confirm after showing the item, its source, its size, and its license.

## What you install yourself first

| Requirement | Notes |
| --- | --- |
| Node.js 22 or newer, with npm | The profile never installs or upgrades it. |
| FFmpeg (provides `ffmpeg` and `ffprobe`) | The profile never installs it. |
| Free disk | About 240 MB for the CLI and its packages, about 190 MB for the browser, about 670 MB if you install the speech model, plus your footage and renders. |
| Memory | Each render worker runs its own headless Chrome. The launcher plans workers from the memory free at render time. |

## The commands

Define a shortcut so the commands are readable. It works in bash and zsh, and lasts for the current terminal session:

```bash
hf() { python3 "$HOME/.hermes/profiles/video-editor/skills/integrations/editor-hyperframes/scripts/hf.py" "$@"; }
```

See the whole plan first. This changes nothing:

```bash
hf setup --plan
```

1. Approve a video workspace. Pick a dedicated folder. The launcher refuses your home folder, the disk root, and the profile itself.

   ```bash
   hf setup --workspace ~/Videos/editor-workspace
   ```

2. Install the pinned CLI.

   ```bash
   hf setup --install-cli
   ```

3. Get the headless browser. Download the build the pinned CLI expects:

   ```bash
   hf setup --download-browser
   ```

   Or record one you already have, with no download:

   ```bash
   hf setup --use-browser /path/to/chrome-headless-shell
   ```

4. Check the result:

   ```bash
   hf status
   ```

   It should read `video engine: toolchain verified`.

## What the release tests did and did not exercise

The release tests ran `--workspace`, `--install-cli`, `--use-browser`, `--allow-host`, and `--handoff`. They did not run `--download-browser`, `--install-model`, or `--add-registry-item` to completion, because each downloads something. Those three were tested only up to the confirmation prompt, which refuses without you at a terminal.

## Every download, named

| Item | Source | Size | License |
| --- | --- | --- | --- |
| HyperFrames CLI `hyperframes@0.8.138`, GSAP 3.14.2, and their dependencies (172 locked packages) | registry.npmjs.org, with `npm ci` from the shipped lockfile, integrity-checked, install scripts off | about 240 MB on disk | Apache-2.0 for HyperFrames (Copyright 2026 HeyGen, Inc.). GSAP Standard License for GSAP, which is not an OSI license. Every other package under its own license, listed in the lockfile. |
| Headless Chrome (`chrome-headless-shell`, build 152.0.7977.30) | Chrome for Testing, fetched by the pinned CLI | about 190 MB on disk | Chromium open-source licenses |
| Optional: Parakeet TDT 0.6B v3 speech model and the sherpa-onnx runtime | Hugging Face, `csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8`, fetched by the pinned CLI | about 670 MB of model files, plus the runtime | CC-BY-4.0 for the model (NVIDIA). Apache-2.0 for sherpa-onnx. |

The CLI and browser sizes were measured on the release test machine (236 MB and 193 MB on macOS, Apple silicon). The model size is the sum of the file sizes pinned in the CLI source at the tag (`packages/cli/src/whisper/sherpa.ts`); the model was not downloaded for the release tests.

## Optional steps

```bash
hf setup --install-model parakeet        # local transcription
hf setup --handoff ~/Videos/handoff      # a folder teammates' profiles can read
hf setup --allow-host cdn.jsdelivr.net   # a host a composition loads from at render time
```

A new project uses the GSAP build installed in step 2, so a normal render needs no network and no approved host. You only need `--allow-host` for a composition that loads something from a CDN, such as a web font or another GSAP version.

Fetching a registry item is also an owner step, per item:

```bash
hf setup --add-registry-item <name> --project <version-folder>
```

The registry is fetched from the upstream `main` branch, not from the pinned release, so its contents can change between fetches. The command records the hash of every file it writes in `registry-items.lock.json` in the project. This path was not exercised with a live fetch in the release tests.

## What the profile sets on every call

The launcher sets `HYPERFRAMES_SKIP_SKILLS=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, `HYPERFRAMES_NO_AUTO_INSTALL=1`, `HYPERFRAMES_NO_TELEMETRY=1`, and `DO_NOT_TRACK=1` for the CLI, removes provider keys from its environment, points its home at a folder inside the profile, and binds the preview to `127.0.0.1`. Each switch was read in the tagged CLI source.

## Removing the toolchain

```bash
hf setup --remove cli
hf setup --remove browser
hf setup --remove model
hf setup --remove all
```

`--remove browser` deletes a browser this setup downloaded. A browser you recorded with `--use-browser` is left where it was. Node.js and FFmpeg are yours and are never touched.

## Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| `video engine: not configured` | Run `hf status` and follow the `fix:` line for each missing piece. |
| `installed lockfile does not match the shipped lockfile` after a profile update | The pin changed. Run `hf setup --install-cli` again. |
| Slow renders | Normal on modest hardware. Check `hf plan-workers`: low free memory means one worker. Close other apps, or render in segments. |
| Silent render | An `<audio>` element has no `id`, or a clip is missing `data-has-audio`. The launcher refuses the first case before rendering. The receipt's `audio_silent` field catches the rest. |
| `render failed` with `memory_pressure_likely: true` | Lower `--workers`, or render in segments. The launcher never retries on its own. |
| Preview still running | `hf preview-stop` stops it and reports any process left. |
| `the composition loads from hosts the owner has not approved` | Remove the reference, or approve the host with `--allow-host`. |
