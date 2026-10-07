# Render performance and limits

Every figure on this page was measured. Nothing here is a promise about another machine.

## Test machine

<!-- machine:begin -->
Apple M2, 8 cores, 16 GB memory, macOS 26.6.2, Node.js v22.23.1, ffmpeg version 8.1

Hermes under test: Hermes Agent v0.21.5 (2026.9.24), commit f97608f178d1ffeca59860195ab7da295f7c8e5f. HyperFrames `0.8.138`.
<!-- machine:end -->

## Long-form limit as tested

<!-- longform:begin -->
| | |
| --- | --- |
| Duration rendered | 600 seconds (10 minutes), 30 segments as sub-compositions |
| Resolution | 1920x1080, 30 frames per second |
| Quality | draft |
| Render time | 895 seconds (1.49 times the video's length) |
| Workers | 2, planned from 3561 MB of free memory |
| Peak memory, whole render process tree | 779 MB |
| Hardware | Apple M2, 8 cores, 16 GB memory, macOS 26.6.2, Node.js v22.23.1, ffmpeg version 8.1 |
| Checked | Picture and sound of every segment against synthetic ground truth, total duration, audio present |
<!-- longform:end -->

This is the longest render the release tests made. It is not a ceiling. A longer render was not tested, so nothing longer is claimed. Render time for this same test varied between runs on the same machine with how much memory and processor time other work left free, so treat the figure as one measurement, not a rate.

## What was measured across the test renders

<!-- renders:begin -->
| Test render | Render seconds | Workers | Peak memory (MB) |
| --- | --- | --- | --- |
| music bed with voice carve and clipping | 6.2 | 2 | 642 |
| vertical captions lower third and callout | 5.0 | 3 | 781 |
| grade changes the picture and contact sheets exist | 3.8 | 6 | 1081 |
| cut trim splice reorder then final | 4.2 | 6 | 1121 |
| keep ranges from transcript timings | 5.0 | 6 | 1133 |
| sound leads picture | 5.3 | 6 | 1125 |
| multi segment long form with measurements | 895.4 | 2 | 779 |
| punch in and crossfade | 4.7 | 4 | 914 |
| reframe v1-16x9 | 2.8 | 4 | 876 |
| reframe v2-9x16 | 2.8 | 4 | 877 |
| reframe v3-4x5 | 2.9 | 4 | 877 |
| slow motion and held frame | 4.5 | 4 | 892 |

Other measurements from the same run:

- Music carve under speech: 19.84 dB. Voice over music in speech windows: 11.72 dB.
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
