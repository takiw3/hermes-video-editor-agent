# Example: a paper edit, then a decision list

Synthetic. The owner, transcript, and timecodes below are invented.

**Owner:** Leo, who owns a roofing company. **Request:** "Tighten this cut. Remove dead air and retakes, and show me the paper edit first."

## Paper edit as sent

A paper edit is not a cut. Nothing was rendered.

Project `SYN-PROJ-044` · v1 · Short-form vertical · Target 45 seconds · Style decision: `house_style`

| # | Source in | Source out | Spoken (verbatim) | Why this take |
| --- | --- | --- | --- | --- |
| 1 | 00:02.1 | 00:07.8 | "Most roof leaks start at the flashing, not the shingles." | The hook as `social-media` wrote it. Take 2 is cleaner. |
| 2 | 00:14.0 | 00:26.3 | "Here's the thirty-second check you can do from the ground." | Only take |
| 3 | 00:31.5 | 00:52.9 | "We do not cover damage from a prior repair under this warranty." | Kept whole. See the meaning check. |

Removed:

| Source in | Source out | What | Meaning check |
| --- | --- | --- | --- |
| 00:07.8 | 00:14.0 | Retake of line 1 | None needed |
| 00:26.3 | 00:31.5 | Dead air, from transcript word timings | None needed |

**Meaning check on line 3.** The dead-air proposal would have dropped a pause that sits just before "not". The cut is moved so the whole sentence stays intact. Removing "not" would reverse the warranty statement.

**What the footage cannot support.** The hook promises a check "from the ground". There is no shot of the roof from the ground. That is listed as a b-roll gap for Leo, not filled with something invented.

Timeline: 39.6 seconds. Removed: 11.4 seconds.

## After Leo approved

The editor wrote the decision list. Timing uses only attributes the pinned release documents.

```yaml
project_id: SYN-PROJ-044
version: v1
duration_seconds: 39.6
style_decision: style-decision.yaml
paper_edit_approved_by: Leo (owner)
clips:
  - id: line-1
    element: video
    src: assets/take.wc.mp4
    data-start: 0
    data-duration: 5.7
    data-media-start: 2.1
    data-track-index: 0
    data-has-audio: true
    recipe: trim
    reason: the hook
    meaning_check: sentence complete
  - id: line-2
    element: video
    src: assets/take.wc.mp4
    data-start: 5.7
    data-duration: 12.3
    data-media-start: 14.0
    data-track-index: 0
    data-has-audio: true
    recipe: split and splice
    reason: removes the retake of line 1
    meaning_check: sentence complete
```

Edit state after approval: `paper_edit_approved`.
