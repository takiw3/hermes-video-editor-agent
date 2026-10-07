# Capabilities and their test status

Each line is marked with what this release actually did with it:

- `rendered and verified`: rendered from an installed temporary profile with the pinned release, and checked against synthetic ground truth by pixel and by audio measurement.
- `tested`: exercised by an automated test that does not need a render.
- `loaded only`: the bundled skill loads in an installed profile, and nothing was rendered through its full workflow.
- `not tested`: no test covers it. Say so before attempting it.
- `not available`: refused by the launcher in this release.

The test names are in `tests/` in the repository, and the recorded results are in `docs/test-results/`. Synthetic media means generated color fields and tones, never real people.

## Editing operations

| Operation | Status | How it was checked |
| --- | --- | --- |
| Hard cut at a known timecode | rendered and verified | Frame color one frame either side of the cut, and the tone under it |
| Trim in and out | rendered and verified | Source second on screen and in the audio |
| Split and splice | rendered and verified | A removed source second is absent from picture and sound |
| Reorder | rendered and verified | An earlier source second plays last |
| Retime at a constant rate | rendered and verified | At 0.5x each source second holds for two timeline seconds |
| Freeze on a still | rendered and verified | The held frame's color for the full hold, with silence |
| Punch-in on the inner wrapper | rendered and verified | A point outside the subject before the zoom is inside it after |
| Crossfade | rendered and verified | The mid-fade frame is a blend of both clips |
| J cut with independent audio | rendered and verified | Picture from clip A while the sound is already clip B |
| L cut | not tested | Same mechanism as the J cut; not rendered separately |
| Dead-air removal from transcript timings | rendered and verified | Expected keep-ranges, and no silence gap left in the render |
| Speed ramp, masks, split-screen, pan | not tested | Documented upstream; not rendered here |
| Captions on a vertical clip, timed to a transcript | rendered and verified | Caption text equals the transcript; caption cards present and absent at the right times by pixel |
| Lower-third and data callout | rendered and verified | Each overlay present and absent at the right times by pixel |
| Safe-zone check | tested | Pass, overflow, and unsourced-zone cases |
| Motion graphic with transparency (WebM) | rendered and verified | Alpha 0 in the corner, alpha 255 on the graphic |
| Motion graphic with transparency (MOV) | not tested | |
| Music bed with voice carve | rendered and verified | Music level under speech against the gaps, by band |
| Clipping and silence detection | tested | An overdriven file is flagged; a silent track is flagged on the receipt |
| Color treatment with before and after sheets | rendered and verified | A measurable color shift, and both contact sheets written |
| 16:9 render | rendered and verified | Output dimensions and content |
| Reframe to 9:16 and 4:5 as separate renders | rendered and verified | Dimensions, subject still centered, one receipt each |
| Square (1:1) canvas | not tested | |
| Batch render from variable rows | rendered and verified | One output and one receipt per row, each with its row's color |
| Multi-segment long-form with sub-compositions | rendered and verified | Each segment's picture and sound, duration, and recorded time and peak memory |
| Draft and final quality settings | rendered and verified | Both render; each receipt records its quality |
| Version compare sheet | rendered and verified | One labeled sheet from two versions |
| Preview start and teardown | rendered and verified | Bound to 127.0.0.1; no process left after stop |
| Local transcription | not tested | The speech model was not downloaded for the release tests; the unavailable path is tested |
| Background removal | not available | Its runtime package and model are not in the pinned lockfile |
| Caption embedding behind the subject | not tested | Needs background removal |
| Multi-shot caption embedding | not tested | |
| HDR output, 4K output, GIF, HLS, PNG sequence | not tested | |
| Registry item fetch | not tested | Owner-run; the refusal path is tested, no live fetch was made |

## Bundled workflows

| Skill | Status |
| --- | --- |
| `hyperframes` (router), `hyperframes-core`, `hyperframes-animation`, `hyperframes-keyframes`, `hyperframes-creative`, `hyperframes-cli`, `hyperframes-audio`, `hyperframes-registry`, `hyperframes-studio`, `media-use` | loaded only. The recipes, attributes, and commands used in the rendered tests above come from these skills. |
| `talking-head-recut` | loaded only. Its composition pins GSAP 3.15.0 from a CDN, which needs an owner-approved host and a network connection at render time. |
| `embedded-captions` | loaded only. Its matting step needs background removal, which is not available. |
| `motion-graphics`, `general-video`, `faceless-explainer` | loaded only |
| `captions-overlay` | loaded only. Internal upstream material that may change without notice. |

A workflow marked `loaded only` may be used, with this said up front: its own end-to-end pipeline was not rendered in this release's tests. The draft render and the quality review are what establish that a given edit worked.

## Not supported

Multi-camera sync. Automatic "best moments" detection. Noise reduction, de-reverb, or voice isolation. Stabilization, object tracking, or rotoscoping. Editing inside CapCut, Premiere, DaVinci Resolve, or Final Cut, or exporting their project files. Downloading a video from any platform. Posting, scheduling, or uploading. Voice cloning or avatar generation. Generative video. Cloud, Lambda, or Cloud Run rendering. Real-time rendering.

## Long-form limits

There is no built-in maximum. The limit is what this machine has rendered, which `hf.py limits` reports from recorded measurements. The release test machine's figures are in the repository's `docs/render-performance-and-limits.md`. They describe that machine only.
