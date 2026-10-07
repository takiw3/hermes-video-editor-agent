# Example: a full exchange with the social-media profile

Synthetic. The profiles, task IDs, paths, and checksums below are invented.

## 1. Brief in

`social-media` creates a Kanban task assigned to `video-editor`:

```yaml
task_id: SYN-TASK-077
source_profile: social-media
objective: Cut the founder Q&A into one short-form video
platform: synthetic-platform
format: short-form vertical
canvas: 9:16
target_duration:
script_reference: handoff/scripts/founder-qa-v3.md
hook: "The question every new client asks us first"
footage_reference: footage/founder-qa.mp4
footage_sha256: 9f2c0000000000000000000000000000000000000000000000000000000000aa
brand_context_reference: local/brand-and-visual-identity.md
style_approver: owner
review_owner: social-media
revision_limit: 3
```

## 2. One question

`target_duration` is blank. The editor returns:

```yaml
status: needs_input
task_id: SYN-TASK-077
edit_state: brief_received
actions_requested:
  - to: social-media
    question: What is the target duration for this cut?
```

## 3. Study and decision

`social-media` answers "45 seconds" and hands over an outlier shortlist. The owner confirms three references, supplies files, and chooses the hybrid from the proposal.

## 4. Review request

After the paper edit is approved and a draft is rendered and inspected, the editor runs `hf.py handoff` on the draft and creates a task for `social-media`:

```yaml
status: review_requested
task_id: SYN-TASK-077
project_id: SYN-PROJ-077
version: v1
edit_state: review_requested
review_owner: social-media
file_reference: handoff/SYN-PROJ-077/v1/SYN-PROJ-077-v1-draft.mp4
file_sha256: 41d7000000000000000000000000000000000000000000000000000000000b2c
render_receipt: handoff/SYN-PROJ-077/v1/SYN-PROJ-077-v1-draft.receipt.yaml
stage: draft
style_option_used: hybrid
style_blueprint_reference: SB-SYN-014 v1
questions:
  - Does the opening deliver the hook as written?
revision_round: 0
revision_limit: 3
```

The task holds a path, a checksum, and a receipt reference. It holds no media.

## 5. Notes back

`social-media` replies: "Hook lands. Trim the pause at 00:04. The lower-third covers the logo on her shirt."

The editor numbers the notes, finds no conflict with the approved paper edit, and applies both as version 2.

## 6. Result out

```yaml
status: complete
task_id: SYN-TASK-077
project_id: SYN-PROJ-077
version: v2
edit_state: final_rendered
summary: Final rendered at 9:16. Two review notes applied in v2. Awaiting the owner's approval.
style_blueprint_reference: SB-SYN-014 v1
style_option_chosen: hybrid
style_approved_by: owner
deliverables:
  - path: handoff/SYN-PROJ-077/v2/SYN-PROJ-077-v2-final.mp4
    sha256: 7be1000000000000000000000000000000000000000000000000000000000c3d
render_receipts: [handoff/SYN-PROJ-077/v2/SYN-PROJ-077-v2-final.receipt.yaml]
checks_performed: [hash, spec, cuts, captions against transcript, safe zone, audio measured, rights, footage unchanged]
feedback_for_scripting:
  - Line 3 ran four seconds long for a 45-second target.
  - No b-roll exists for the second example. Listed as a shot request.
approval_still_required: [owner approval of the final]
actions_requested:
  - to: social-media
    request: Measured results for edit SYN-PROJ-077 against blueprint SB-SYN-014, at 14 days
residual_risks: [A re-read of the platform spec is due if this ships after the fact file's 90-day window]
```

The editor does not post the video. Posting belongs to `social-media` and the owner.
