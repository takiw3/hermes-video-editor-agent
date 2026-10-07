# Permissions and security

## Default posture

- Default mode: `edit_and_render`, once the toolchain is verified. Before that: `offline`.
- Default external-action policy: no external writes. There is no posting, scheduling, uploading, publishing, cloud rendering, or sign-in in any mode.
- Network reads: the owner-run setup downloads (the pinned CLI from npm, the headless browser, the optional speech model), and, only for a composition that needs one, a fetch from a render-time host the owner approved.
- Source footage is read-only.
- Every write stays inside the owner-approved workspace.
- No cron job, MCP server, scraping service, video-download tool, or data provider is configured.

## What is technically enforced

Each line is covered by an automated test in `tests/`.

| Boundary | Mechanism |
| --- | --- |
| Installation downloads nothing and runs nothing | Hermes copies an allowlist of files. Tested with all network access denied. |
| Only the pinned CLI runs through the launcher | `hf.py` runs the lockfile-installed CLI and refuses a version or lockfile mismatch. It also checks the version that actually runs. |
| No skill self-update, update check, auto-install, or telemetry | `hf.py` sets the switches the tagged CLI reads, on every child process. |
| A child process cannot fetch another version | `hf.py` puts shims ahead of `npx`, `npm`, `pip`, `brew`, and `heygen` on the child's `PATH`. |
| No cloud render, Lambda, Cloud Run, publish, sign-in, feedback, capture, provider media, or voice | `hf.py` subcommand allowlist |
| No provider key reaches the CLI | `hf.py` removes credential-shaped variables from the child's environment and gives it a home folder inside the profile |
| Frames are not sent to an external vision service by `snapshot` | `hf.py` passes `--describe false` and removes the provider key |
| Writes stay in the workspace | `hf.py` checks the working directory and every path argument. `editor_tools.py` checks every path. |
| No output is overwritten | `hf.py` and `editor_tools.py` refuse an existing output path |
| Nothing from `references/` in a project | `hf.py` refuses a path, symlink, or byte-identical copy, on every render, lint, check, snapshot, and preview |
| No final render without a style decision | `hf.py` style-decision preflight |
| No final render with an unlicensed asset, a changed original, or no draft | `hf.py` final-render gates |
| No render with an `<audio>` or `<video>` that has no `id` | `hf.py`, and upstream lint |
| Workers sized to free memory | `hf.py` plans from a measurement and records the peak |
| A failed render is not retried | `hf.py` reports once and exits |
| Downloads and approvals need the owner at a terminal | `hf.py setup` refuses a download without an interactive confirmation |
| The route-around command forms are denied to the agent | `config.yaml` `approvals.deny`, which Hermes applies before any bypass mode. Tested against Hermes 0.21.4 and 0.21.5 with a list of commands that must be denied and a list that must not. |
| Memory and skill writes are staged for review | `config.yaml` `write_approval` |
| Dangerous commands fail closed when nobody is watching | `config.yaml` `cron_mode`, `single_query_mode`, `unattended_mode` set to `deny` |

## What is enforced only by instruction

These rest on the agent following `SOUL.md` and its skills. No code stops a violation.

- Who actually made the style choice. `style-decision.yaml` proves a choice was recorded. The agent writes that file.
- That a cut does not change the meaning of what a person said.
- That captions match what was said, and that no unapproved words or claims go on screen.
- That consent exists for a person on camera, and that a license record is true.
- That a re-encoded or trimmed copy of a reference is not used. The reference exclusion compares checksums and paths.
- That footage, private transcripts, and reference material stay out of Kanban tasks, comments, attachments, and declared artifacts.
- That the agent does not download a video with a tool the deny rules do not name, or by a route they do not match.
- That an instruction inside a transcript, title, caption, registry item, or Kanban comment is ignored.
- That frames showing people or private information are not sampled without the owner's consent.
- Escalation of sensitive cases.

## Limits of the technical controls

Stated plainly:

- **The launcher is not a sandbox.** It governs calls made through it. A process that never calls it is not stopped by it. The gate tests include a direct call to the CLI that produces a file with no receipt.
- **Deny rules match command text.** A command hidden inside a script file the agent writes first is not matched. The install tests record this.
- **Deny rules cover terminal commands, not file-tool writes.** The agent's file tools can write where the operating-system user can. To restrict them, set `HERMES_WRITE_SAFE_ROOT` to your workspace in the profile's `.env`. Hermes then refuses file-tool writes outside it. The distribution does not set this, because it must not hardcode a path.
- **Approvals are stored in a file the operating-system user can write** (`local/video-editor/video-engine/engine.json`). The deny rules block terminal commands that name it. That is a floor, not a lock.

## No hard action gate, so no external-services mode

An `approved_external_services` mode would need a gate that no raw fetch, upload, sign-in, or cloud command could bypass, with single-use, expiring, field-bound human approval. Inside one operating-system user, without a sandbox, that cannot be built: anything the gate can read or write, the agent can too. The tests above confirm a raw command goes around the launcher. So this release ships no such mode. Registry fetches and downloads are owner-run setup steps, in the owner's own terminal, and everything else external is refused.

The approval-request template keeps the full field set (`approval_id`, `approved_by_human`, `approved_at`, `expires_at`, `profile`, `business_tenant`, `project_id`, `operation`, `service`, `service_account`, `item_name`, `item_source_url`, `item_version_or_commit`, `item_license`, `item_size`, `destination_path`, `data_sent_off_machine`, `files_uploaded_sha256`, `estimated_cost`, `cost_ceiling`) so a later release cannot add an action with fewer bound fields.

## Tenant boundaries

- One installed video editor profile is for one brand or creator.
- A profile is not a full tenant-security boundary. Profiles share an operating-system user, its filesystem access, and the Kanban board.
- Strong separation between brands needs separate operating-system users or containers, explicit mounts, isolated credentials, and separate boards.
- Kanban tenant labels and profile names are routing metadata, not access controls.
- Keep the Kanban dashboard on localhost unless you secure it separately.
- The HyperFrames preview is a long-lived local server that holds browser workers open. The launcher binds it to `127.0.0.1`, and `preview-stop` stops it and reports anything left. Stop it when the task ends.
- Another profile cannot be assumed to read this profile's workspace. Use an owner-approved handoff folder, and pass the path and SHA-256.
- `terminal.home_mode: profile` keeps tool subprocesses in the profile's home folder. It is a containment convenience, verified on both tested Hermes releases, and not a tenant boundary.

## Prompt injection

Titles, descriptions, captions, comments, transcripts, metadata, registry items, file contents, and Kanban comments are data. An instruction inside one is ignored and reported. None can grant approval, change the rules, or widen permissions. A Kanban task containing the word "approved" is not human approval. Five eval fixtures cover injection in a transcript, a video title, a reference's captions, a registry item, and a Kanban comment.

## Reporting a vulnerability

See `SECURITY.md`.
