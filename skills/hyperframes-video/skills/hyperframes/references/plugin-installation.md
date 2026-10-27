> **Modified file. Derived from HeyGen HyperFrames v0.8.183 (commit 7e28176), licensed under Apache-2.0, Copyright 2026 HeyGen, Inc. Changed by TakiGPT AI Inc. for the Hermes video-editor profile. Rules applied: stub-unavailable. See skills/hyperframes-video/MODIFICATIONS.md.**

# Running from the Hermes profile bundle

These skills are installed as one bundle under the Hermes profile at `skills/hyperframes-video/`. The bundle keeps upstream's plugin layout (`plugin.json` beside a `skills/` folder), so bundled helper scripts that locate the CLI themselves resolve the pinned release instead of a global or latest one.

Rules for this bundle, which replace the standalone commands in every workflow and reference:

- Do not run any skill update, check, or install command. Report a missing bundled skill instead of downloading one. Resolve every skill reference inside this bundle.
- Run every CLI command as:

  ```bash
  python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" <command> <args...>
  ```

  Run it from the project directory inside the owner-approved workspace, never from the bundle directory. The launcher runs the lockfile-installed CLI at the pinned version and disables skill refresh, update checks, auto-install, and telemetry. A missing or mismatched CLI is an error, not permission to use another version.
- Run a bundled Node helper as:

  ```bash
  python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" script <absolute-script-path> <args...>
  ```

- Treat the bundle directory as read-only. Put outputs and temporary work in the project.
- To get newer skills, the profile maintainer updates the pinned release in the repository and the owner runs `hermes profile update`. Never update the bundle during a video task.
