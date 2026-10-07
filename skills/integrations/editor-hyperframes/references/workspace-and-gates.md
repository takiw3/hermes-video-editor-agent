# Workspace layout and gates

## Layout

The owner approves one workspace folder. The launcher creates this inside it:

```
<workspace>/
  footage/            originals. Read-only by rule. Checksums registered.
  working-copies/     conversions written by editor_tools.py, each with its command
  references/         reference videos for study. Never an asset. Outside every render path.
  projects/
    <video-id>/       one folder per video
      style-decision.yaml
      v1/             one subfolder per version: a HyperFrames project
        index.html
        assets/       copies and working copies used by this version
        compositions/ sub-compositions, for long-form segments
        renders/      rendered files
        receipts/     one receipt per render, written by the launcher
        snapshots/    frames and contact sheets
        asset-rights-register.yaml
      v2/
  .video-editor/      checksums, render measurements, session frames
```

A HyperFrames project reads media from inside its own folder, so a version works from a copy or a working copy in `assets/`. The original in `footage/` is never the file on the timeline and is never written to.

## Gates on a draft render

1. The toolchain is verified and the pinned version is installed from the lockfile.
2. The working directory and every path are inside the workspace, and the project is under `projects/`.
3. Nothing from `references/` is in the project: no path into it, no symlink into it, no byte-identical copy of a file in it.
4. Every `<audio>` and `<video>` element has an `id`.
5. Every external host the composition loads from is owner-approved.
6. A style decision is recorded, or the draft carries a `--comparison` tag.

## Extra gates on a final render

7. `style-decision.yaml` is valid: an option with its study and blueprint, a named approver and a time, and a blueprint that is not stale, or a one-edit waiver with its reason.
8. Every asset in the project has a complete rights record.
9. Every registered original still matches its checksum.
10. A draft receipt exists for this version.
11. The output path does not already exist.

## What the reference exclusion cannot see

It compares checksums and paths. A re-encoded, cropped, or trimmed copy of a reference has a different checksum and is not detected. The rule holds regardless: nothing from a reference enters a deliverable.

## What is not a gate

These are your rules, not code: who actually made the style choice, whether a cut changes meaning, whether a caption is accurate, whether consent exists, and whether the render looks and sounds right.
