# Privacy and retention

## What the profile reads

Only what you approve: footage, audio, transcripts, reference videos, brand files, and performance figures you or `social-media` supply. It asks before reading footage, transcripts, reference videos, or performance data.

## What leaves the machine

| Data | Where it goes |
| --- | --- |
| Your prompts, the text the agent reads, and its tool results | Your configured model provider |
| Frames the agent looks at, from your renders, your footage, or a reference | Your configured model provider. Frame inspection needs a vision-capable model. |
| Footage, audio, and rendered files | Nowhere. Rendering, probing, transcription, and measurement run locally. |
| Telemetry from HyperFrames | Nothing. The launcher turns it off on every call. |
| Anything to HeyGen or another media, voice, image, or data provider | Nothing. Those routes are refused and their keys are removed from the CLI's environment. |

The editor says so before sampling frames from footage that shows people or private information. If that is not acceptable for a piece of footage, tell it, and it will report the visual checks as not checked.

During setup, your machine contacts the npm registry, the browser download host, and, if you install it, the speech model host. During a render, it contacts a host only if a composition loads from one you approved.

## What is stored, and where

| Data | Location | Default retention |
| --- | --- | --- |
| Editor profile, brand identity | `local/` in the profile | Until you change it |
| Style library (blueprints) | `local/style-library/` | Until retired. Retired blueprints are kept, marked. |
| Source footage | The workspace `footage/` folder | Yours. The editor never deletes it. |
| Working copies | The workspace `working-copies/` folder | Your rule |
| Transcripts, paper edits, decision lists | The project folder | Your rule |
| Reference videos | The workspace `references/` folder | Your rule |
| Frames sampled from a reference or a render | A session folder in the workspace | Deleted when the task ends |
| Renders, receipts, snapshots | The project folder | Your rule. Prior versions are never deleted without your instruction. |
| Compact preferences | Hermes memory, through the approval gate | Until you remove them |

You choose retention rules during onboarding.

## Never saved to memory

Credentials. Raw transcripts. Private information visible or audible in footage. Reference videos or frames. Sponsor contracts. Personal data about creators studied.

## Never in the repository or the distribution

`.env`, `auth.json`, API keys and tokens, memories, sessions, logs, databases, caches, downloaded browsers and models, `node_modules`, footage, working copies, reference videos and frames, renders, transcripts, studies, blueprints, decision lists, fetched registry items, and sponsor contracts. `.gitignore`, the validation script, and the install tests each check this.

## Outlier research

The editor studies videos, not people. It collects no personal data about private individuals, and records about creators only what a study needs: an account name, links, and public figures with the date they were read.

## Cross-team handoffs

Kanban tasks hold references and checksums. Footage of identifiable people, private transcripts, and reference material are not placed in a task, a comment, an attachment, or a declared artifact. Sensitive escalations use an opaque project ID.

## Updates and removal

`hermes profile update video-editor` replaces only distribution-owned files. It preserves credentials, memory, sessions, `local/` including the style library and the toolchain, configuration overrides, the workspace, and your own skills. The install tests place a sentinel file in each and check it after an update.

`hermes profile delete video-editor` removes the profile, including `local/`. Your workspace is outside the profile and is not touched. Remove the toolchain first if you want it gone separately: see `hyperframes-setup.md`.
