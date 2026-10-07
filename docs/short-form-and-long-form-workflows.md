# Short-form and long-form workflows

Short-form and long-form are different crafts. The editor does not apply one rhythm to both.

## Shared path

Every edit runs the same first half:

1. Intake: `edit-intake-and-routing`. Edit state `brief_received`.
2. Footage: `footage-ingest-and-inventory`. Probe, checksum, flag, working copies. `footage_ingested`.
3. Transcript: `transcript-and-selects`. Transcribe, verify, mark takes, propose selects. `transcribed`.
4. Study: `outlier-video-research`. `outlier_study_ready`, or `outlier_study_waived`.
5. Blueprint: `edit-style-analysis`.
6. Proposal and decision: `style-match-proposal`. `style_chosen`.
7. Paper edit: `paper-edit-and-decision-list`. `paper_edit_approved`.

Nothing is rendered before step 7 is approved.

## Short-form

`short-form-editing`:

- Build the opening first and review it alone. It must deliver the hook `social-media` wrote. If the footage cannot, that goes back before any cutting around it.
- One idea per video.
- Cuts follow the documented recipes: hard cut, trim, split and splice, reorder, retime, freeze, crossfade.
- Captions through `caption-design-and-timing`, overlays through `motion-graphics-and-overlays`, sound through `audio-cleanup-and-mix`, treatment through `color-and-media-treatment`.
- Lint and check, then a draft render, then `edit-quality-review`.
- Every requested aspect ratio is its own reviewed render, through `reframe-and-multi-format-export`. A reframe is never assumed safe.

For a three-way comparison (house style, outlier-matched, hybrid), each option is its own version folder and its own draft, tagged with its option. No final is rendered until a choice is recorded.

## Long-form

`long-form-editing`:

- Build a structure map before cutting: cold open, intro, segments, ending.
- Edit in segments as sub-compositions, so one failure does not cost the whole render.
- Render one short segment as a draft, read its time and peak memory from the receipt, estimate the full render from that, and tell the owner before starting.
- Workers come from measured memory.
- A render longer than anything on record at that resolution is named as such, and segmenting is proposed.
- Chapter timecodes go to `social-media` for packaging.
- Clip candidates are marked with timecodes and a reason each. They are candidates.

## Long to short

`long-to-short-clipping` finds candidates in the verified transcript: passages that state one complete idea in the target duration. It does not detect "best moments", and no candidate is ranked by predicted performance. You or `social-media` choose. Each approved clip becomes its own short-form edit.

## Render, review, revise

- `render-and-export`: draft first, every time. The launcher writes the receipt.
- `edit-quality-review`: frames across the timeline, denser at the opening and at every cut near speech. Audio measured. Pass or fail per check with a timecode.
- `revision-and-version-management`: notes become numbered, conflicts go to the approver, and a revision is a new version folder. Earlier versions stay intact.
- `cross-team-edit-handoffs`: review requests and deliveries carry a path, a SHA-256, and the receipt.

Edit states from here: `rough_cut_rendered`, `review_requested`, `revision_requested`, `fine_cut_rendered`, `final_rendered`, `approved`, `delivered`.

## Statuses

`not configured`, `toolchain verified`, `footage probed`, `transcript verified`, `style decision recorded`, `composition written`, `lint passed`, `check passed`, `draft rendered`, `final rendered with file path`, `render failed`, `approval required`, `outcome unknown`.

A zero exit code proves the process finished. It does not prove the cut works, the captions are accurate, or the audio is clean. Only inspection proves that.

## What the tools cannot do

Multi-camera sync, automatic best-moment detection, noise reduction or voice isolation, stabilization, object tracking, rotoscoping, background removal in this release, project files for other editors, downloading, posting, voice cloning, avatars, and generative video. The editor says so, names what a human editor would need to do, and offers the nearest supported result.
