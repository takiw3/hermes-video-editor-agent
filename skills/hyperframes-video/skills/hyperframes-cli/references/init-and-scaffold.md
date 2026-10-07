> **Modified file. Derived from HeyGen HyperFrames v0.8.138 (commit 0ca28db), licensed under Apache-2.0, Copyright 2026 HeyGen, Inc. Changed by TakiGPT AI Inc. for the Hermes video-editor profile. Rules applied: local-render-only, pin-cli. See skills/hyperframes-video/MODIFICATIONS.md.**

# init, capture, skills

<!-- registry-items: allow=blank,landscape-4k,portrait-4k,square-4k,product-launch-video,hyperframes-core,media-use -->

Scaffolding commands. Use these instead of creating files by hand — they set up the right file structure, copy media, run transcription, and install AI coding skills.

## init

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video                                    # centered blank (TTY: wizard)
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video --example warm-grain               # pick an example
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video --resolution portrait
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video --video clip.mp4                   # with video file
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video --audio track.mp3                  # with audio file
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video --tailwind                         # Tailwind v4 browser runtime
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" init my-video --non-interactive                  # CI — flag-only, same blank
```

**Default depends on TTY**: in a terminal, the CLI prompts for example/options (default: centered blank). Outside a TTY (CI, agents, piped output) it auto-switches to non-interactive and scaffolds that blank. Pass `--example` only to start from a named example. Pass `--non-interactive` to force flag-only mode on a TTY.

Templates: `blank`, `warm-grain`, `play-mode`, `swiss-grid`, `vignelli`, `decision-tree`, `kinetic-type`, `product-promo`, `nyt-graph`. (The closed set of `hyperframes:example` items in `registry/registry.json` plus the bundled `blank` template. `hyperframes catalog` does not list examples — its `--type` takes only `block` or `component` — so this list has no live equivalent and is checked by `bun run lint:skills`.)

Other useful flags:

- `--resolution` — preset: `landscape` (1920×1080), `portrait` (1080×1920), `landscape-4k`, `portrait-4k`, `square` (1080×1080), `square-4k`. Aliases: `1080p`, `4k`, `uhd`, `1080p-square`, `4k-square`.
- `--skill=<slug>` — record the owning authoring workflow (e.g. `product-launch-video`) in `hyperframes.json`, so every later render of this project — re-renders, `npm run render`, `--batch` — is attributed to it on anonymous telemetry without re-passing the flag. Creation workflows set this automatically; you rarely pass it by hand.
- `--skip-skills` — **temporarily ignored**: `init` always checks AI coding skills against GitHub while the skills.sh registry catches up. To opt out (CI/tests), set the `HYPERFRAMES_SKIP_SKILLS=1` env var instead.
- `--skip-transcribe` — don't auto-transcribe `--audio` / `--video` with Whisper.
- `--model`, `--language` — Whisper model / language for the auto-transcription.

When using `--tailwind`, invoke the `hyperframes-core` (Tailwind reference) skill before editing classes or theme tokens. The scaffold uses Tailwind v4 browser runtime patterns, not Studio's Tailwind v3 setup.

When `--audio` or `--video` is supplied, `init` transcribes the file with Whisper. For voice/model selection see the `media-use` skill.

## capture

Not available in this profile. Website capture is a network read the default mode does not perform.

## skills

Not available in this profile. Skills are bundled and release-managed by the Hermes profile.
