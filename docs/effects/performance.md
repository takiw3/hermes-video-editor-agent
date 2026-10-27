# Effect performance

Each verified effect carries a `render_cost_multiplier`: capture seconds with the effect, divided by capture seconds for the same composition without it. The per-effect figures are in the [catalog](catalog.md).

## How it is measured

- The composition is 320x180, 30 fps, 2 seconds (60 frames).
- Capture seconds come from the render summary the pinned CLI prints (`capture 5.4s`). That excludes browser start-up, frame extraction and encoding.
- The effect's figure is the lower of two runs; the baseline is one run. The multiplier is never reported below 1.0.
- Several effects were verified at once (`--jobs 4` on an Apple M2, 16 GB), so the machine was busy. Treat a figure as a rough ranking, not a benchmark. Re-measure on your machine with one job when it matters.

## What it does not tell you

- **Resolution.** A 1080p or 4K render costs more, and per-pixel effects (blur, bloom, painterly, warps, SVG convolutions) scale with pixel count.
- **Capture mode.** Some effects switch HyperFrames from its fast DOM capture to screenshot capture: anything WebGL, a vfx chain, or shader transitions. The record notes which mode each render used.
- **Workers.** `wave-warp` and `self-displace` read their own layer, so HyperFrames pins the whole render to one worker.
- **Stacking.** Multipliers on one composition roughly multiply. `fx.py stack-check` multiplies them, warns over a budget of 4, and names every effect at 2 or more.

## Practical budget

- Long-form: one look, one transition style, and light overlays. Keep heavy effects to short windows (`--at`, `--duration`).
- Before a long render, run `fx.py stack-check` and `hf.py plan-workers`, then render a 10-second draft and compare its time with the estimate.
