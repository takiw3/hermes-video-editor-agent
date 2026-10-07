> **Modified file. Derived from HeyGen HyperFrames v0.8.138 (commit 0ca28db), licensed under Apache-2.0, Copyright 2026 HeyGen, Inc. Changed by TakiGPT AI Inc. for the Hermes video-editor profile. Rules applied: pin-cli. See skills/hyperframes-video/MODIFICATIONS.md.**

# Generate a project beat grid

Use `hyperframes beats` when an existing HyperFrames project needs the Studio-compatible beat file for its music track. This is a CLI utility, not a complete video workflow.

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" beats
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" beats ./my-video
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" beats ./my-video --json
```

The project must contain a local music `<audio>` source. Mark it with `data-timeline-role="music"`; an id containing `music`, `bgm`, or `soundtrack` is also recognized. The command analyzes that file in headless Chrome and writes `beats/<audio-relative-path>.json`.

If no beats are detected, the command fails and writes nothing. If Chrome is unavailable, run:

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" browser ensure
```

For a complete beat-synced video, route through `/music-to-video`. That workflow owns a different audio-driven pipeline and its `audiomap.json`; do not replace its analyzer with this Studio utility.
