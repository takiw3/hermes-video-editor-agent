# Render performance and limits

Every figure on this page was measured. Nothing here is a promise about another machine.

## Test machine

<!-- machine:begin -->
Apple M2, 8 cores, 16 GB memory, macOS 26.6.2, Node.js v22.23.1, ffmpeg version 9.0.1

Hermes under test: Unavailable. HyperFrames `0.8.183`.
<!-- machine:end -->

## Long-form limit as tested

<!-- longform:begin -->
| | |
| --- | --- |
| Duration rendered | 120 seconds (2 minutes), 6 segments as sub-compositions |
| Resolution | 1280x720, 30 frames per second |
| Quality | draft |
| Render time | 64 seconds (0.53 times the video's length) |
| Workers | 4, planned from 4589 MB of free memory |
| Peak memory, whole render process tree | 1833 MB |
| Hardware | Apple M2, 8 cores, 16 GB memory, macOS 26.6.2, Node.js v22.23.1, ffmpeg version 9.0.1 |
| Checked | Picture and sound of every segment against synthetic ground truth, total duration, audio present |
<!-- longform:end -->

This is the longest render the release tests made. It is not a ceiling. A longer render was not tested, so nothing longer is claimed. Render time for this same test varied between runs on the same machine with how much memory and processor time other work left free, so treat the figure as one measurement, not a rate.

## What was measured across the test renders

<!-- renders:begin -->
| Test render | Render seconds | Workers | Peak memory (MB) |
| --- | --- | --- | --- |
| music bed with voice carve and clipping | 10.1 | 4 | 1593 |
| vertical captions lower third and callout | 8.1 | 4 | 1765 |
| grade changes the picture and contact sheets exist | 6.4 | 5 | 2076 |
| cut trim splice reorder then final | 8.0 | 4 | 1755 |
| keep ranges from transcript timings | 7.6 | 4 | 1749 |
| sound leads picture | 8.4 | 5 | 2099 |
| multi segment long form with measurements | 63.7 | 4 | 1833 |
| punch in and crossfade | 7.5 | 5 | 2138 |
| reframe v1-16x9 | 7.3 | 5 | 1974 |
| reframe v2-9x16 | 6.5 | 4 | 1571 |
| reframe v3-4x5 | 6.1 | 4 | 1615 |
| slow motion and held frame | 8.3 | 5 | 2136 |

Other measurements from the same run:

- Music carve under speech: 19.83 dB. Voice over music in speech windows: 11.73 dB.
- Cut detection on a render with 5 known cuts between solid colors, at scene threshold 0.3: 4 detected. Scene detection can miss a cut between similar frames.
- Retime at 0.5x: a 740 Hz source tone measured 740 Hz in the render.
- Transparent WebM: corner alpha 0, graphic alpha 255.
<!-- renders:end -->

## How the profile handles limits on your machine

- Every render records its duration, resolution, render time, worker count, and the peak memory of the whole render process tree in a receipt and in the workspace's measurement file.
- `hf.py limits` reports the longest render on record per resolution and stage. That is your machine's tested limit.
- `hf.py plan-workers` shows the worker plan: memory free right now, minus a reserve, divided by the largest per-worker peak measured on this machine at the same canvas size or larger. A small-canvas render is not used to size a larger one. With no such render on record it uses a planning figure of 512 MB per worker, twice what upstream states for one worker's Chrome process.
- For a long render, the agent renders one short segment first, estimates the full render from that measurement, tells you the estimate, and asks before starting.
- When a render would exceed the longest on record, the agent says so and proposes rendering in segments.
- A render that fails is reported once, with its memory figures. The agent lowers workers, says so, and tries once more. It never loops.

## Not claimed

- A maximum duration.
- Real-time or near-real-time rendering.
- A render time for any machine other than the one above.
- 4K, HDR, GIF, HLS, or PNG-sequence output. None was rendered in the tests.
- Final-quality long-form timing. The long-form test rendered at draft quality.
