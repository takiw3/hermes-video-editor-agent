# Example: a render that exits zero and fails review

Synthetic. The project, file names, and measurements below are invented.

**Owner:** Yara, who owns a bakery chain. A 45-second vertical draft was rendered.

## The launcher's result

```json
{
  "status": "draft rendered",
  "outputs": ["projects/SYN-PROJ-052/v1/renders/SYN-PROJ-052-v1-draft.mp4"],
  "receipts": ["projects/SYN-PROJ-052/v1/receipts/SYN-PROJ-052-v1-draft.receipt.yaml"],
  "workers": 2,
  "style_decision": "hybrid"
}
```

## The receipt (excerpt)

```yaml
status: "draft rendered"
stage: "draft"
edit_state: "rough_cut_rendered"
inspected: false
duration_seconds: 45.0
width: 1080
height: 1920
has_audio: true
audio_silent: true
quality: "draft"
style_decision: "hybrid"
```

## What the editor reported

Not "done". The exit code was zero, and the receipt says the audio track is silent.

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| 1 | File exists and its SHA-256 matches the receipt | pass | recomputed |
| 2 | Duration, resolution, frame rate | pass | probe |
| 6 | Captions match the verified transcript | pass | frames at 00:01, 00:07, 00:19, 00:33 |
| 10 | Audio is present, not silent, and does not clip | **fail** | `audio_silent: true`; `audio-profile` reports no signal |
| 20 | Status is stated exactly | pass | reported as `draft rendered` |

Cause found: the music element in the composition had no `id`, and the speech clip was missing `data-has-audio`. An `<audio>` element with no `id` is skipped by the mixer.

What changed: both attributes were added, lint passed, and a new draft was rendered. The second receipt reads `audio_silent: false`.

Status reported to Yara: `draft rendered`, failed review at check 10, fixed, second draft ready for her to look at. Not final. Not approved.
