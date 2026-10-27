# Photosensitivity and accessibility

Every render with effects gets a flash check before it goes to the owner. A failing render is never delivered.

## The criteria, and where they come from

Read on 2026-10-21 from the W3C:

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) (W3C Recommendation, 12 December 2024): Success Criterion 2.3.1 *Three Flashes or Below Threshold*, and the definitions of *general flash and red flash thresholds* and *relative luminance*.
- [Understanding SC 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html), including the WCAG 2.2 working definition of a saturated red transition.

What the check uses, quoted from those pages, with no threshold of our own:

- No more than three general flashes and no more than three red flashes in any one-second period, unless the flashing area is small enough.
- A general flash is a pair of opposing changes in relative luminance of 10% or more of the maximum, where the darker state is below 0.80.
- The area limit is 25% of any 10-degree visual field, given as 341 x 256 CSS pixels.
- Relative luminance is the sRGB formula with the 0.04045 linearization knee.
- A red transition goes to or from a state with R/(R+G+B) of 0.8 or more, and its CIE 1976 u'v' chromaticity changes by more than 0.2.

The constants live in one place, `WCAG` in `fx.py`, with the URLs and the access date.

## How `fx.py flash-check` applies them

1. The video is mapped onto a display whose short side is 768 CSS px by default, the WCAG reference screen height. Pass `--display-short-side` for bigger viewing; a bigger display makes the same flash cover more of the field.
2. The frame is split into cells one eighth of the 341 x 256 field across, and each cell's relative luminance is followed frame by frame.
3. A cell transition is one monotonic run of at least 10% of maximum relative luminance with its darker end below 0.80. It counts once, however far it goes.
4. **Our reading, not WCAG text.** A field transition happens when the cells changing one way outnumber the cells changing the other way by at least 25% of a 341 x 256 field, in the same frame or the next. This is how we read "the combined area of flashes occurring concurrently". Stripes sliding through a field brighten one part while another part darkens, so the field as a whole does not flash.
5. A flash is a pair of opposing field transitions. More than three in any one-second window fails.
6. **Warn** means two or more concurrent flashes in a second somewhere, or a small area flickering faster than three flashes a second. It is under the limit, but a person should look.

Known inputs used to check the checker:

| Input | Result |
| --- | --- |
| 5 Hz full-frame strobe | fail |
| 5 Hz red strobe | fail (general and red) |
| 2 Hz full-frame strobe | warn |
| 5 Hz strobe over 9% of a field | warn (small-area flicker), not fail |
| 5 Hz strobe over a whole field | fail |
| The calm fixture clip | pass |

These cases are in the test suite.

This is a screening check, not a certification. It does not replace a professional tool such as the Harding test for broadcast.

## What the catalog rating means

Each effect's rating comes from its default and max renders on calm synthetic media:

- **pass:** no flash at either setting.
- **warn:** something worth a look.
- **fail:** it flashed. If only max flashed, the effect is listed as **limited**, with that limit in its record.

An effect that flashes at default is not verified. Your footage, timing and stacking can still create flashes the catalog could not see, so the check always runs on the real render.

## HDR

Effects run on HyperFrames' SDR pipeline; a native HDR layer keeps its pixels on a separate path and shows no effect. For HDR the Understanding page cites a different industry definition (20 cd/m² where the darker state is below 160 cd/m²). This profile does not check HDR renders. An HDR source gets an SDR working copy the owner approves.

## Other accessibility checks

- **Text contrast:** `hf.py check` reports text that fails WCAG AA contrast against what is behind it. Effects that move or recolour the background can cause this, so fix it with a darker band or a heavier stroke.
- **Motion:** shakes, warps and fast pushes can make some viewers ill. Keep them short and purposeful.
