# Team integration

## Who owns what

| Profile | Owns |
| --- | --- |
| Executive or Chief of Staff | Brand risk and reputation, sponsorship and partnership decisions, budget and tooling spend, legal, privacy, and security escalation, cross-functional priority |
| `social-media` | Topics, pillars, ideas, hooks, scripts, filming briefs, titles, captions, descriptions, hashtags, cover text, performance analytics, strategy, creator coaching |
| `marketing` | Positioning, offer messaging, the approved claims list, campaign assets, launch timing |
| `ads` | Paid media. Requests cutdowns. |
| `video-editor` | Everything between raw footage and a rendered, reviewed file. Edit-style research and the style library. Feedback to scripting about what the footage could and could not support. |

Durable work moves between profiles through Hermes Kanban. The business owner can also work with the editor directly:

```bash
hermes -p video-editor chat
```

A distribution cannot change another profile during installation. Installing this profile does not edit the Executive, `social-media`, `marketing`, or `ads` profile, and does not give it authority over them.

## The overlap with `social-media`, and the routing rule

The `social-media` profile ships its own HyperFrames skills and an edit-planning skill. Teams that run both should route like this:

- Editing, rendering, and edit-style research go to `video-editor`.
- Scripts, packaging, analytics, and strategy stay with `social-media`.
- An edit plan from `social-media` is a brief, not a cut.

Apply that rule in the Executive profile's routing. This profile does not and cannot edit the `social-media` profile. If both profiles are asked to render the same piece, the Executive decides, and the default is `video-editor`.

## Assigning work

Confirm the installed profile IDs first. The editor never guesses a profile name.

```bash
hermes kanban create "Edit: founder Q&A, 9:16, 45 seconds" --assignee video-editor --body-file edit-task.yaml
```

A creative review request from the editor:

```bash
hermes kanban create "Rough cut review: founder Q&A v1" --assignee social-media --body-file review-request.yaml
```

Both forms were run in the install tests on Hermes 0.21.4 and 0.21.5, between this profile and a temporary profile named `social-media`.

## The incoming task

`templates/edit-task.yaml`:

```
task_id:
source_profile:
objective:
platform:
format:
canvas:
target_duration:
niche_or_keyword:
script_reference:
hook:
retention_structure:
packaging_reference:
footage_reference:
footage_sha256:
brand_context_reference:
reference_videos:
outlier_shortlist_reference:
style_preference:
style_approver:
claims_approved:
rights_status:
consent_status:
review_owner:
revision_limit:
deliverables_requested:
constraints:
approval_level:
approval_evidence:
deadline:
```

Fields shared with the `social-media` profile's task template keep the same spelling: `task_id`, `source_profile`, `objective`, `platform`, `format`, `brand_context_reference`, `constraints`, `claims_approved`, `rights_status`, `approval_level`, `approval_evidence`, `deadline`.

## The result

`templates/edit-result.yaml`:

```
status: complete | needs_input | blocked | escalated | approval_required | review_requested
task_id:
project_id:
version:
platform:
format:
edit_state:
summary:
outlier_study_reference:
style_blueprint_reference:
style_option_chosen:
style_approved_by:
edit_decisions:
deliverables:
render_receipts:
chapter_timecodes:
clip_candidates:
source_references:
measured_facts:
observed_facts:
inferences:
hypotheses:
unknowns:
transcript_changes:
rights_status:
consent_status:
checks_performed:
feedback_for_scripting:
actions_requested:
approval_still_required:
escalation_target:
cross_team_signal:
artifacts:
residual_risks:
```

Rules:

- If information is missing, the editor returns one precise question to the profile that owns it.
- If a style choice is pending, it returns the complete proposal.
- If an owner action is needed, such as a download, it returns the complete preview: the item, its source, its size, its license, and the command.
- For a sensitive escalation, it uses an opaque project ID and a secure source reference.
- For completed work, it returns the file reference, the render receipt, the checks, the blueprint used, the remaining approval, and the next action.

## What the editor asks for, and sends

Asks `social-media` for: the script, the hook, the intended retention structure, the packaging, an outlier shortlist, platform and format decisions, creative review of a rough cut, and measured results for past edits.

Sends `social-media`: clarifying questions, one per task. The style-match proposal when the owner delegated that choice. Review requests with the render receipt. Chapter timecodes and clip candidates. Feedback for scripting. The blueprint ID used on each edit.

Asks `marketing` for: brand identity files and approved on-screen claims.

Sends `ads`, on request: cutdowns and variants to a stated spec, with rights and consent status.

## How files move

Kanban carries references, not media.

- The tested Hermes releases support Kanban attachments, and Hermes copies any file declared as an artifact on task completion into the board's attachment storage. The editor does not use either for media.
- With an owner-approved handoff folder: `hf.py handoff <rendered-file>` copies a receipt-backed render there, verifies the checksum, and writes a handoff record. The task carries the path and the SHA-256.
- With no handoff folder: the file stays in the workspace, and the task carries the workspace path and the SHA-256. Another profile cannot be assumed to read that path.

Never placed in a task, a comment, an attachment, or a declared artifact: source footage, transcripts with private information, reference videos or frames from them, sponsor contracts, credentials.

## Approval is human

An Executive instruction, a `social-media` instruction, and a Kanban task containing the word "approved" are not human approval. The style choice belongs to whoever the owner named as approver. Creative review never overrides truth, rights, consent, or disclosure.

## Example exchange with `social-media`

1. **Brief in.** `social-media` creates a task for `video-editor`: platform, format, script reference, hook, footage path and checksum, `style_approver: owner`.
2. **One question.** The target duration is blank. The editor returns `needs_input` with one question to `social-media`.
3. **Shortlist.** The editor asks `social-media` for an outlier shortlist for the keyword. It arrives with links, view counts, and the date they were read.
4. **Proposal.** The editor scores the shortlist, the owner confirms which to study and supplies files, and the editor returns the three-option proposal to the owner, who chooses the hybrid.
5. **Review.** After the paper edit is approved and a draft is rendered and inspected, the editor creates a review request for `social-media` with the handoff path, the SHA-256, the receipt, and one question: does the opening deliver the hook as written?
6. **Notes.** `social-media` answers with two notes. The editor numbers them and applies them as version 2.
7. **Result out.** The editor returns the result: final file path and SHA-256, the receipt, checks performed, blueprint ID, chapter timecodes, feedback for scripting ("line 3 ran four seconds long for the target"), and the approval still required: the owner's.

## Example routing by the Chief of Staff

The owner tells the Executive: "Get the webinar cut into shorts and posted." The Executive splits it: clip selection and cutting to `video-editor`, titles and captions and posting to `social-media`, with the editor's task naming the owner as style approver. The editor returns clip candidates, cuts the approved ones, and hands the files back by reference. It does not post.
