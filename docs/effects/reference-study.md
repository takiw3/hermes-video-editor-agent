# Reference study: picture effects in a studied open-source editor

## Header

- Purpose: a behavioral study for a clean-room implementation. It records what each effect looks like on screen and what its controls do, in plain words, so a separate implementer can build our own effects without opening the studied project's files.
- Studied repository: https://github.com/jub0t/concat (Concat, AGPL-3.0-or-later)
- Pinned commit: 2756209a92766a4e4726999a51648349a272c159 (main on 2026-10-21; latest release at that time was v0.2.8)
- Date read: 2026-10-21
- Rule: this file contains no code, no shader text, no numbers, defaults or ranges taken from the studied project, no copied description text, and no distinctive coined look or preset names. Every sentence below was written fresh. The `reference_id` field is there for traceability only and must never appear in our effect ids, file names or user-facing text.
- `study_key` (RS-001 to RS-102) is the only identifier our catalog uses to point back at an entry here (`reference_id` in `catalog.yaml`). It carries no name from the studied project.
- Fingerprints of the studied shaders, manifests and images (salted hashes only, no text) are in `tests/fixtures/concat-fingerprints.json`. `scripts/copy_check.py check` uses them.

### Files read

- Repository documents, read in full: `README.md`, `TRADEMARK.md`, `CLA.md`, `CODE_SIGNING.md`, `SECURITY.md`, `THIRD_PARTY_NOTICES.md`, and the opening lines of `LICENSE` (enough to confirm GNU AGPL version 3).
- Audit reports, read in full: `audit/AUDIT-2026-10-15-QUICK.md`, `audit/AUDIT-2026-10-20-QUICK.md`, `audit/AUDIT-2026-10-20.md`, `audit/2026-10-20/project-effects-ml-phones-ci.md`, `audit/2026-10-20/product-distribution.md`. The other audit files were keyword-searched only.
- Effect manifests, read in full: all 127 `src/crates/concat-effects/packages/*/effect.toml`.
- Never opened: any `.wgsl`, `.rs` or `fixtures.toml` file.

### Counts by kind (from the manifests)

| Kind | Count |
| --- | --- |
| filter (preset looks) | 57 |
| effect (adjustable picture effects) | 23 |
| transition | 22 |
| audio filter | 25 |
| total | 127 |
| picture packages (filter + effect + transition) | 102 |

### How the studied package model behaves (observations, in our words)

- Each package is one GPU shader plus a manifest. Some effects run several passes, for example a blur drawn across and then down at reduced resolution before the final composite.
- Controls come in a handful of types: a plain slider, a whole-number slider, a choice list, an on/off switch, a colour picker, a three-way colour wheel (hue plus level), and a drawn curve. Some sliders are marked as animatable over time.
- Most packages name one control as the master strength, so a single "intensity" knob can scale the whole look.
- A flag says whether the effect works on display-encoded values or in linear light. Exposure, contrast, white balance and the light-based effects work in linear light; most preset looks work on display values.
- Every transition degrades to a plain crossfade when its shader is unavailable, and most name a simpler standard transition as a rough equivalent.
- A package can declare that it replaces an older package and map the old controls onto its own, so saved projects keep working.
- Packages cannot read extra images, masks, earlier frames or audio. That limits them to single-frame picture maths, which is why there are no particle sprites, logo overlays or beat-synced effects in the set.

## Transitions

```yaml
study_key: RS-001
reference_id: concat.dissolve
kind: transition
category: basic
visible_behavior: The outgoing shot fades away while the incoming shot fades in over the same stretch, so both are briefly visible at once.
control_roles: none
our_family: transitions
our_effect_id: cross-dissolve
already_in_hyperframes: partly (not one of the listed shader transitions, but an opacity crossfade between two layers is trivial in a composition)
notes: The plain crossfade is also the fallback every other transition drops to.
```

```yaml
study_key: RS-002
reference_id: concat.blur-dissolve
kind: transition
category: dissolve
visible_behavior: A crossfade in which both pictures go soft as the cut approaches and come back into focus after it.
control_roles:
  strength: how blurred the pictures get at the middle of the transition
our_family: transitions
our_effect_id: blur-dissolve
already_in_hyperframes: partly (the Blur media effect keyframed over a crossfade gets close; no single transition does it)
notes: Blur is strongest at the midpoint and falls off symmetrically on both sides.
```

```yaml
study_key: RS-003
reference_id: concat.clock-wipe
kind: transition
category: wipe
visible_behavior: A line pivoting on the centre of the frame sweeps round like a clock hand, and the incoming shot fills in behind it.
control_roles: none
our_family: transitions
our_effect_id: clock-wipe
already_in_hyperframes: no
notes: A radial wipe is the simple equivalent.
```

```yaml
study_key: RS-004
reference_id: concat.cube
kind: transition
category: dimensional
visible_behavior: The two shots sit on neighbouring faces of a box that turns, carrying the outgoing shot away and bringing the incoming one round into view.
control_roles: none
our_family: transitions
our_effect_id: cube-rotate
already_in_hyperframes: no
notes: Needs a perspective projection of two textured faces.
```

```yaml
study_key: RS-005
reference_id: concat.fade-black
kind: transition
category: basic
visible_behavior: The picture dims all the way to black, then the next shot rises out of the black.
control_roles: none
our_family: transitions
our_effect_id: fade-through-black
already_in_hyperframes: partly (not a listed shader transition; a black layer with opacity keys does it)
notes: Two halves, out then in, rather than a crossfade with a dark middle.
```

```yaml
study_key: RS-006
reference_id: concat.fade-white
kind: transition
category: basic
visible_behavior: The outgoing shot brightens until the frame is pure white, then the incoming shot settles back out of the white.
control_roles: none
our_family: transitions
our_effect_id: fade-through-white
already_in_hyperframes: yes (flash through white)
notes: Same two-half shape as the fade through black.
```

```yaml
study_key: RS-007
reference_id: concat.film-burn
kind: transition
category: burn
visible_behavior: A hot, warm, overexposed flare washes through the frame around the cut and hides the switch.
control_roles:
  heat: how strong and how orange the burn gets
our_family: transitions
our_effect_id: film-burn-flash
already_in_hyperframes: partly (ridged burn and light leak cover similar ground)
notes: The frame is almost white well before the midpoint, so a preview thumbnail should be taken early in the transition.
```

```yaml
study_key: RS-008
reference_id: concat.light-leak-transition
kind: transition
category: light
visible_behavior: A warm band of light travels across the frame and the shots swap underneath it.
control_roles:
  warmth: how orange the light is, from neutral to warm
our_family: transitions
our_effect_id: light-leak-sweep
already_in_hyperframes: yes (light leak)
notes: Directional streak rather than a full-frame flash.
```

```yaml
study_key: RS-009
reference_id: concat.light-leak-flash
kind: transition
category: light
visible_behavior: An irregular, organic patch of overexposure blooms over the frame and burns out, leaving the new shot behind it.
control_roles:
  strength: how much of the frame the flash covers and how bright it gets
our_family: transitions
our_effect_id: overexposure-burn-flash
already_in_hyperframes: partly (light leak, flash through white)
notes: The studied project's own audit flagged a power function there that can receive a negative input; guard any such call in our version. Take the preview thumbnail early.
```

```yaml
study_key: RS-010
reference_id: concat.glitch-transition
kind: transition
category: glitch
visible_behavior: The image tears into horizontal bands and the colour channels slip out of line for a moment while the shots swap.
control_roles:
  amount: how violent the tearing and channel slip are
our_family: transitions
our_effect_id: glitch-cut
already_in_hyperframes: yes (glitch)
notes: none
```

```yaml
study_key: RS-011
reference_id: concat.glitch-warp
kind: transition
category: glitch
visible_behavior: Slices of the frame shove sideways with colour fringes and blocky pixel displacement as the shots change over.
control_roles:
  amount: how far slices shift and how blocky the displacement gets
our_family: transitions
our_effect_id: slice-tear-displace
already_in_hyperframes: partly (glitch, chromatic split)
notes: Its simple equivalent is a crossfade that pixelates through the middle.
```

```yaml
study_key: RS-012
reference_id: concat.iris
kind: transition
category: wipe
visible_behavior: A circle grows from the centre with the incoming shot inside it until it fills the frame.
control_roles:
  softness: how feathered the circle's edge is
our_family: transitions
our_effect_id: circle-iris
already_in_hyperframes: yes (SDF iris)
notes: none
```

```yaml
study_key: RS-013
reference_id: concat.linear-wipe
kind: transition
category: wipe
visible_behavior: A straight edge travels across the frame, replacing the outgoing shot with the incoming one as it goes.
control_roles:
  direction: which edge the wipe starts from, either horizontal or either vertical way
  softness: how feathered the moving edge is
our_family: transitions
our_effect_id: linear-wipe
already_in_hyperframes: no
notes: none
```

```yaml
study_key: RS-014
reference_id: concat.push
kind: transition
category: slide
visible_behavior: The incoming shot enters from one side and shoves the outgoing shot out the other side, both moving together.
control_roles:
  direction: which way the pair moves
our_family: transitions
our_effect_id: push-slide
already_in_hyperframes: no
notes: Differs from the slide below because both pictures move.
```

```yaml
study_key: RS-015
reference_id: concat.rgb-split-wipe
kind: transition
category: glitch
visible_behavior: Red, green and blue pull apart during the cut and lock back together on the new shot.
control_roles:
  spread: how far the channels separate at the peak
our_family: transitions
our_effect_id: channel-split-cut
already_in_hyperframes: yes (chromatic split)
notes: none
```

```yaml
study_key: RS-016
reference_id: concat.shape-wipe
kind: transition
category: wipe
visible_behavior: The incoming shot grows outward from the centre inside a shape mask, a circle, a heart or a star, until it covers the frame.
control_roles:
  shape: which mask shape is used
  softness: how feathered the shape's edge is
our_family: transitions
our_effect_id: shape-mask-wipe
already_in_hyperframes: partly (SDF iris covers the circle case)
notes: The shape is still small at the midpoint, so the preview thumbnail should be taken late.
```

```yaml
study_key: RS-017
reference_id: concat.slide
kind: transition
category: slide
visible_behavior: The incoming shot slides in over the outgoing one, which stays still underneath.
control_roles:
  direction: which side the new shot enters from
our_family: transitions
our_effect_id: slide-over
already_in_hyperframes: no
notes: none
```

```yaml
study_key: RS-018
reference_id: concat.swirl
kind: transition
category: spin
visible_behavior: Both pictures twist around the centre of the frame, the twist peaks at the cut, then unwinds onto the new shot.
control_roles:
  twist: how tightly the picture winds at the peak
our_family: transitions
our_effect_id: swirl-twist
already_in_hyperframes: yes (swirl vortex)
notes: Also shelved with the distortion effects in the studied UI.
```

```yaml
study_key: RS-019
reference_id: concat.spin
kind: transition
category: spin
visible_behavior: The outgoing shot rotates away as a flat card while the incoming one rotates into place.
control_roles:
  turns: how far the pictures rotate over the transition
our_family: transitions
our_effect_id: spin-rotate
already_in_hyperframes: no
notes: none
```

```yaml
study_key: RS-020
reference_id: concat.whip-pan
kind: transition
category: motion
visible_behavior: A fast sideways camera whip with heavy streak blur carries the old shot out of frame and the new one in.
control_roles:
  speed: how fast the whip feels and how long the streaks are
our_family: transitions
our_effect_id: whip-pan
already_in_hyperframes: yes (whip pan)
notes: Drops to a plain horizontal slide where shaders are unavailable.
```

```yaml
study_key: RS-021
reference_id: concat.zoom-blur-transition
kind: transition
category: zoom
visible_behavior: The camera rushes inward or outward with radial streaks and lands on the new shot.
control_roles:
  strength: how long the radial streaks get
our_family: transitions
our_effect_id: zoom-blur-rush
already_in_hyperframes: yes (cinematic zoom)
notes: none
```

```yaml
study_key: RS-022
reference_id: concat.zoom-transition
kind: transition
category: zoom
visible_behavior: A quick zoom through the outgoing shot that lands on the incoming one, pushing in or pulling out.
control_roles:
  direction: zoom in or zoom out
our_family: transitions
our_effect_id: zoom-through
already_in_hyperframes: partly (cinematic zoom)
notes: Scale change without the heavy streaks of the zoom blur rush.
```

## Adjustable effects

```yaml
study_key: RS-023
reference_id: concat.bloom-pulse
kind: effect
category: light
visible_behavior: Bright areas glow softly, and the glow swells and fades in a steady rhythm.
control_roles:
  amount: how strong the glow is (master strength)
  speed: how fast the glow breathes in and out
our_family: image-effects
our_effect_id: pulsing-bloom
already_in_hyperframes: partly (Bloom, with the pulse added by keyframes)
notes: Glow comes from a separable blur of the bright areas drawn at reduced resolution.
```

```yaml
study_key: RS-024
reference_id: concat.color-wheels
kind: effect
category: color
visible_behavior: Shadows, midtones and bright areas can each be pushed toward a chosen hue and made brighter or darker on their own.
control_roles:
  lift: hue and level for the shadows
  gamma: hue and level for the midtones
  gain: hue and level for the bright areas
our_family: looks-and-grades
our_effect_id: lift-gamma-gain
already_in_hyperframes: partly (color grading correction)
notes: Neutral at rest. All three wheels can be animated. Works on display-encoded values.
```

```yaml
study_key: RS-025
reference_id: concat.corona
kind: effect
category: glow
visible_behavior: A cool blue-white halo gathers around the brightest, blown-out parts of the picture.
control_roles:
  threshold: how bright an area must be before it glows
  radius: how far the halo spreads
  amount: how strong the halo is (master strength)
  coolness: how blue the halo is
our_family: image-effects
our_effect_id: cool-highlight-halo
already_in_hyperframes: partly (Bloom)
notes: A cold counterpart to film halation. One reduced-resolution blur of the extracted bright areas, added back over the picture.
```

```yaml
study_key: RS-026
reference_id: concat.chromatic-aberration
kind: effect
category: distort
visible_behavior: Red and blue fringes appear around edges and grow stronger toward the frame border, like a cheap lens.
control_roles:
  shift: how far the colour channels separate
our_family: image-effects
our_effect_id: chromatic-aberration
already_in_hyperframes: yes (Channel Separation)
notes: Separation increases with distance from the centre.
```

```yaml
study_key: RS-027
reference_id: concat.chroma-key
kind: effect
category: keying
visible_behavior: Removes a chosen backdrop colour so the layer below shows through, and neutralises the coloured fringe left on the subject's edges.
control_roles:
  key_colour: the backdrop colour to remove
  similarity: how close a colour must be to the key to be removed (master strength)
  softness: how gradual the edge between kept and removed is
  spill: how much of the backdrop's tint is cleaned off the subject
our_family: keying-and-subject
our_effect_id: chroma-key
already_in_hyperframes: no
notes: One package replaces older separate green and blue screen presets. Starts on a standard studio green. Works on display-encoded values.
```

```yaml
study_key: RS-028
reference_id: concat.curves
kind: effect
category: color
visible_behavior: Tones are remapped along curves the user draws, one for overall brightness and one for each of red, green and blue.
control_roles:
  luma: brightness-only curve
  red: red channel curve
  green: green channel curve
  blue: blue channel curve
our_family: looks-and-grades
our_effect_id: rgb-curves
already_in_hyperframes: yes (curves)
notes: Neutral at rest.
```

```yaml
study_key: RS-029
reference_id: concat.film-grain
kind: effect
category: stylize
visible_behavior: A layer of moving grain sits over the picture and changes every frame, like film stock.
control_roles:
  amount: how heavy the grain is
our_family: looks-and-grades
our_effect_id: film-grain
already_in_hyperframes: yes (grain)
notes: Grain must be animated, not a fixed texture.
```

```yaml
study_key: RS-030
reference_id: concat.gaussian-blur
kind: effect
category: blur
visible_behavior: The whole picture goes evenly soft.
control_roles:
  radius: how wide the blur is
our_family: image-effects
our_effect_id: gaussian-blur
already_in_hyperframes: yes (Blur)
notes: Separable two-pass blur, drawn at reduced resolution for large radii. Replaces an older box blur by matching its spread.
```

```yaml
study_key: RS-031
reference_id: concat.glow
kind: effect
category: stylize
visible_behavior: A soft halo forms around the bright parts of the picture.
control_roles:
  amount: how strong and wide the glow is
our_family: image-effects
our_effect_id: soft-glow
already_in_hyperframes: yes (Bloom)
notes: Same separable reduced-resolution blur shape as the pulsing bloom, without the pulse.
```

```yaml
study_key: RS-032
reference_id: concat.exposure
kind: effect
category: color
visible_behavior: The picture gets brighter or darker by photographic stops, as if the aperture changed, with bright areas rolling off rather than clipping.
control_roles:
  exposure: stops of light up or down (animatable)
our_family: looks-and-grades
our_effect_id: exposure-stops
already_in_hyperframes: partly (color grading correction)
notes: Works in linear light.
```

```yaml
study_key: RS-033
reference_id: concat.contrast
kind: effect
category: color
visible_behavior: Contrast goes up or down around middle grey, without crushing black or losing detail above white.
control_roles:
  amount: signed contrast change (animatable)
our_family: looks-and-grades
our_effect_id: contrast-pivot
already_in_hyperframes: partly (color grading correction)
notes: Works in linear light, pivoting on middle grey.
```

```yaml
study_key: RS-034
reference_id: concat.fisheye
kind: effect
category: distort
visible_behavior: The picture bulges outward from the centre like a very wide lens.
control_roles:
  strength: how strong the bulge is
our_family: camera-and-motion
our_effect_id: fisheye-lens
already_in_hyperframes: partly (CRT Curvature, displacement map in the VFX chain)
notes: none
```

```yaml
study_key: RS-035
reference_id: concat.luma-key
kind: effect
category: keying
visible_behavior: Removes the dark parts of the picture so elements shot on black (fire, smoke, sparks) sit over the layer below; inverted, it removes the bright parts instead.
control_roles:
  threshold: how dark a pixel must be to be removed (master strength)
  softness: how gradual the cut-off is
  invert: remove bright areas instead of dark ones
our_family: keying-and-subject
our_effect_id: luma-key
already_in_hyperframes: no
notes: Works on display-encoded values.
```

```yaml
study_key: RS-036
reference_id: concat.halftone
kind: effect
category: retro
visible_behavior: The picture becomes a grid of black and white dots whose size follows the brightness.
control_roles:
  dot_size: spacing and size of the dots
our_family: image-effects
our_effect_id: halftone-dots
already_in_hyperframes: yes (Halftone)
notes: none
```

```yaml
study_key: RS-037
reference_id: concat.motion-blur
kind: effect
category: blur
visible_behavior: The picture streaks along one direction, as if the camera panned during the exposure.
control_roles:
  length: how long the streak is
  angle: which direction the streak runs
our_family: camera-and-motion
our_effect_id: directional-blur
already_in_hyperframes: partly (Blur)
notes: A coarse blur along the line, then smoothing between its samples.
```

```yaml
study_key: RS-038
reference_id: concat.saturation
kind: effect
category: color
visible_behavior: Colours get richer or greyer, measured against each pixel's own brightness so the tone stays put.
control_roles:
  amount: signed saturation change (animatable)
our_family: looks-and-grades
our_effect_id: saturation
already_in_hyperframes: partly (color grading correction)
notes: Works on display-encoded values.
```

```yaml
study_key: RS-039
reference_id: concat.sharpen
kind: effect
category: basic
visible_behavior: Edges and fine detail look crisper.
control_roles:
  amount: how much sharpening is applied
our_family: image-effects
our_effect_id: unsharp-sharpen
already_in_hyperframes: no
notes: Works on display-encoded values.
```

```yaml
study_key: RS-040
reference_id: concat.halation
kind: effect
category: film
visible_behavior: A red-orange halo appears around blown-out bright areas, the way light scatters back through film.
control_roles:
  threshold: how bright an area must be before it glows
  radius: how far the halo spreads
  amount: how strong the halo is (master strength)
  tint: halo colour, from a deep red one way to a print orange the other
our_family: image-effects
our_effect_id: film-halation
already_in_hyperframes: partly (Bloom)
notes: Separable reduced-resolution blur of the bright areas, tinted and added back.
```

```yaml
study_key: RS-041
reference_id: concat.vignette
kind: effect
category: stylize
visible_behavior: The corners darken so the eye goes to the middle of the frame.
control_roles:
  strength: how dark and how far in the corners close
our_family: looks-and-grades
our_effect_id: vignette
already_in_hyperframes: yes (vignette)
notes: none
```

```yaml
study_key: RS-042
reference_id: concat.white-balance
kind: effect
category: color
visible_behavior: The picture looks as if lit by warmer or cooler light, and can lean toward magenta or green.
control_roles:
  temperature: colour temperature of the light (animatable)
  tint: green to magenta balance (animatable)
our_family: looks-and-grades
our_effect_id: white-balance
already_in_hyperframes: partly (color grading correction)
notes: Works in linear light and models how the eye adapts to the light colour.
```

```yaml
study_key: RS-043
reference_id: concat.zoom-blur
kind: effect
category: blur
visible_behavior: The picture streaks outward from a chosen point, as if the lens zoomed during the exposure.
control_roles:
  amount: how long the streaks are (animatable)
  centre_x: horizontal position of the zoom point
  centre_y: vertical position of the zoom point
our_family: camera-and-motion
our_effect_id: radial-zoom-blur
already_in_hyperframes: partly (Blur; the cinematic zoom transition has a similar look)
notes: Several passes, each filling in between the previous pass's samples, to get long smooth streaks.
```

```yaml
study_key: RS-044
reference_id: concat.pixelate
kind: effect
category: distort
visible_behavior: The picture breaks into large square blocks of flat colour.
control_roles:
  size: block size
our_family: image-effects
our_effect_id: pixelate
already_in_hyperframes: yes (Pixelate)
notes: none
```

```yaml
study_key: RS-045
reference_id: concat.posterize
kind: effect
category: stylize
visible_behavior: Smooth gradients collapse into a few flat bands of colour, like a screen print.
control_roles:
  levels: how many bands each channel keeps
our_family: image-effects
our_effect_id: posterize
already_in_hyperframes: partly (Ordered Dither and Two-Ink Print quantise colour; no plain posterize)
notes: Works on display-encoded values.
```

## Preset looks (filters)

```yaml
study_key: RS-046
reference_id: concat.adjust
kind: filter
category: adjust
visible_behavior: The manual correction panel every picture clip carries. At rest it changes nothing; it can fix exposure, tone, balance, sharpness and edge darkening in one place.
control_roles:
  temperature: warmer or cooler light
  tint: green to magenta balance
  saturation: signed colour strength
  exposure: stops of light up or down (master strength)
  brightness: overall lift or drop
  contrast: signed contrast
  highlights: lifts or pulls the broad upper half of the tones
  shadows: lifts or pulls the broad lower half of the tones
  whites: moves the very top end only
  blacks: moves the very bottom end only
  sharpen: adds edge crispness
  fade: lifts blacks toward a matte
  vignette: darkens the corners
  wheels: lift, gamma and gain colour wheels (animatable)
  curves: luma, red, green and blue curves
our_family: looks-and-grades
our_effect_id: basic-correction-panel
already_in_hyperframes: partly (color grading correction, curves, vignette)
notes: Works in linear light; exposure is in true stops. Controls are grouped colour, lightness, effects, wheels, curves.
```

```yaml
study_key: RS-047
reference_id: concat.autumn
kind: filter
category: seasonal
visible_behavior: Greens turn toward amber and the whole picture takes on warm, fall-coloured light.
control_roles: none
our_family: looks-and-grades
our_effect_id: warm-foliage-shift
already_in_hyperframes: partly (selective color plus a LUT)
notes: Fixed look with no knobs.
```

```yaml
study_key: RS-048
reference_id: concat.bleach-bypass
kind: filter
category: cinematic
visible_behavior: Colour is washed out and contrast pushed hard, giving the silvery, gritty look of skipping the bleach step in film processing.
control_roles: none
our_family: looks-and-grades
our_effect_id: bleach-bypass
already_in_hyperframes: partly (correction or a LUT)
notes: none
```

```yaml
study_key: RS-049
reference_id: concat.bronze
kind: filter
category: retro
visible_behavior: A sepia tone that keeps strong contrast and clean whites, so it reads as old film rather than a flat brown wash.
control_roles:
  tone: how much sepia is applied (master strength)
  contrast: how much contrast is kept or added
our_family: looks-and-grades
our_effect_id: contrast-sepia
already_in_hyperframes: partly (correction plus a LUT)
notes: none
```

```yaml
study_key: RS-050
reference_id: concat.classic-chrome
kind: filter
category: film
visible_behavior: Bright areas are muted while shadows stay deep but open, giving a restrained, slightly cool colour-negative look.
control_roles: none
our_family: looks-and-grades
our_effect_id: muted-negative-film
already_in_hyperframes: partly (LUT)
notes: The studied name echoes a camera maker's film simulation; ours must use a generic name.
```

```yaml
study_key: RS-051
reference_id: concat.clean
kind: filter
category: natural-look
visible_behavior: A barely visible polish for talking heads, with neutral balance, a gentle tone curve, slightly richer colour and reds calmed so skin looks even.
control_roles:
  amount: how far the polish is applied
our_family: looks-and-grades
our_effect_id: subtle-skin-even-grade
already_in_hyperframes: partly (correction, curves, selective color)
notes: Directly relevant to talking-head reels.
```

```yaml
study_key: RS-052
reference_id: concat.cloudless-sky
kind: filter
category: travel
visible_behavior: Skies go deeper and bluer and foliage cooler and calmer, while faces and every other colour stay as shot.
control_roles:
  sky: how much the blues deepen (master strength)
  greens: how much foliage is cooled and calmed
our_family: looks-and-grades
our_effect_id: sky-deepen
already_in_hyperframes: partly (selective color)
notes: Hue-targeted; needs a hue mask so skin is untouched.
```

```yaml
study_key: RS-053
reference_id: concat.contrast-pop
kind: filter
category: color
visible_behavior: Shadows go deeper and bright areas brighter for a punchier picture.
control_roles:
  contrast: how strong the push is
our_family: looks-and-grades
our_effect_id: s-curve-contrast
already_in_hyperframes: partly (curves)
notes: none
```

```yaml
study_key: RS-054
reference_id: concat.cool
kind: filter
category: color
visible_behavior: The whole picture shifts toward the blue of daylight in shade.
control_roles:
  temperature: how cool the shift is
our_family: looks-and-grades
our_effect_id: cool-shift
already_in_hyperframes: partly (correction)
notes: One-knob temperature shift.
```

```yaml
study_key: RS-055
reference_id: concat.cool-blue
kind: filter
category: cinematic
visible_behavior: Shadows and midtones turn blue while bright areas and skin stay neutral, with contrast raised; it reads like a city at dusk.
control_roles:
  chill: how much blue goes into shadows and midtones (master strength)
  contrast: how much contrast is added
our_family: looks-and-grades
our_effect_id: blue-shadow-grade
already_in_hyperframes: partly (correction, selective color)
notes: Needs skin protection.
```

```yaml
study_key: RS-056
reference_id: concat.cyberpunk
kind: filter
category: cinematic
visible_behavior: Magenta floods the shadows and cyan the bright areas, pushed hard for a neon look.
control_roles: none
our_family: looks-and-grades
our_effect_id: magenta-cyan-split-tone
already_in_hyperframes: partly (LUT)
notes: Fixed look. See the neon glow look below for an adjustable, blooming version.
```

```yaml
study_key: RS-057
reference_id: concat.daydream
kind: filter
category: cinematic
visible_behavior: Soft cinema look with lifted blacks, warm glowing light, slightly cool shadows and skin kept natural.
control_roles:
  haze: how lifted and soft the picture gets (master strength)
  warmth: how warm the glow is
our_family: looks-and-grades
our_effect_id: hazy-warm-bloom-grade
already_in_hyperframes: partly (correction plus Bloom)
notes: Combines a grade with a light bloom.
```

```yaml
study_key: RS-058
reference_id: concat.delicious
kind: filter
category: food
visible_behavior: Warm and saturated, the push that makes food look appetising.
control_roles: none
our_family: looks-and-grades
our_effect_id: warm-saturated-food
already_in_hyperframes: partly (correction)
notes: none
```

```yaml
study_key: RS-059
reference_id: concat.digicam
kind: filter
category: retro
visible_behavior: The look of an early digital compact camera, with harsh flash, blown whites, boosted colour, a cool cyan cast, over-sharpened edges and sensor noise.
control_roles:
  flash: how harsh the flash and blown whites are (master strength)
  noise: how much sensor noise is added
our_family: looks-and-grades
our_effect_id: compact-camera-flash
already_in_hyperframes: partly (correction plus grain)
notes: Popular on short-form platforms.
```

```yaml
study_key: RS-060
reference_id: concat.dreamy
kind: filter
category: soft
visible_behavior: A soft, hazy glow over pastel, lifted blacks.
control_roles: none
our_family: looks-and-grades
our_effect_id: pastel-haze-bloom
already_in_hyperframes: partly (Bloom plus correction)
notes: none
```

```yaml
study_key: RS-061
reference_id: concat.fair
kind: filter
category: portrait
visible_behavior: Faces get brighter and more even, with reds calmed and the balance neutral, while the rest of the frame stays as it was.
control_roles:
  brighten: how much skin is lifted (master strength)
  even: how much redness and blotchiness is reduced
our_family: looks-and-grades
our_effect_id: skin-brighten-even
already_in_hyperframes: partly (selective color on skin hues)
notes: Skin-targeted by hue, not by face detection.
```

```yaml
study_key: RS-062
reference_id: concat.falling-dust
kind: filter
category: retro
visible_behavior: A warm faded look with specks of dust drifting down through the frame and a light leak glowing in one corner.
control_roles:
  dust: how much dust falls (master strength)
  leak: how strong the corner light leak is
our_family: overlays-and-generators
our_effect_id: drifting-dust-overlay
already_in_hyperframes: partly (Film Artifacts plus a light leak)
notes: Dust is generated procedurally in the shader, not from sprites. Where the shader is unavailable it shows only the fade and faint noise.
```

```yaml
study_key: RS-063
reference_id: concat.film
kind: filter
category: cinematic
visible_behavior: A print-film look with a proper toe and shoulder in the tone curve, warm halation around lights and grain that moves.
control_roles:
  grain: how heavy the moving grain is (master strength)
  warmth: how warm the halation and overall tone are
our_family: looks-and-grades
our_effect_id: film-print-emulation
already_in_hyperframes: partly (curves, grain, Bloom)
notes: Combines a tone curve, a highlight glow and animated grain.
```

```yaml
study_key: RS-064
reference_id: concat.fresh
kind: filter
category: natural-look
visible_behavior: Daylight footage made to pop, with midtones lifted, muted colours raised, a hint of mint in the brightest whites and skin left alone.
control_roles:
  pop: how much colour and midtone lift is added (master strength)
  brightness: how much overall lift
our_family: looks-and-grades
our_effect_id: daylight-pop
already_in_hyperframes: partly (correction, selective color)
notes: Vibrance-style boost that spares skin.
```

```yaml
study_key: RS-065
reference_id: concat.golden-hour
kind: filter
category: natural-look
visible_behavior: Late-afternoon light with a warm balance that keeps its brightness, orange in the bright areas, a trace of magenta in the shadows and slightly lifted blacks.
control_roles:
  glow: how strongly the look is applied (master strength)
  warmth: colour temperature of the light
our_family: looks-and-grades
our_effect_id: golden-hour-grade
already_in_hyperframes: partly (correction, LUT)
notes: Warming without darkening.
```

```yaml
study_key: RS-066
reference_id: concat.high-contrast-mono
kind: filter
category: black-and-white
visible_behavior: Black and white pushed hard, with deep blacks, bright whites and little in between.
control_roles: none
our_family: looks-and-grades
our_effect_id: high-contrast-bw
already_in_hyperframes: partly (correction plus curves; Mono Screen is a different, display-style look)
notes: none
```

```yaml
study_key: RS-067
reference_id: concat.ivory
kind: filter
category: natural-look
visible_behavior: A soft matte with cream in the whites and a little gold through the middle; suits interiors and morning light.
control_roles:
  matte: how far blacks lift and whites soften (master strength)
  warmth: how much cream and gold is added
our_family: looks-and-grades
our_effect_id: warm-cream-matte
already_in_hyperframes: partly (correction, curves)
notes: Warm sibling of the bright cool matte below.
```

```yaml
study_key: RS-068
reference_id: concat.lagoon
kind: filter
category: travel
visible_behavior: Water and sky turn aquamarine and brighter while sand and skin stay warm and clean.
control_roles:
  water: how strongly blues and cyans shift to aqua (master strength)
  brightness: how much those areas are lifted
our_family: looks-and-grades
our_effect_id: aqua-water-shift
already_in_hyperframes: partly (selective color)
notes: Hue-targeted beach look.
```

```yaml
study_key: RS-069
reference_id: concat.landscape-pop
kind: filter
category: outdoor
visible_behavior: Greens and blues get richer, the extra punch a travel shot wants.
control_roles: none
our_family: looks-and-grades
our_effect_id: nature-saturation-boost
already_in_hyperframes: partly (selective color)
notes: none
```

```yaml
study_key: RS-070
reference_id: concat.marquee
kind: filter
category: stylized
visible_behavior: Night city look, with lights and signs made vivid and glowing, blacks kept deep and cool and faces left clean.
control_roles:
  lights: how much the light sources glow and saturate (master strength)
  depth: how deep and cool the blacks go
our_family: looks-and-grades
our_effect_id: night-signage-glow
already_in_hyperframes: partly (Bloom plus correction)
notes: Needs a bright-area mask for the glow and skin protection.
```

```yaml
study_key: RS-071
reference_id: concat.matcha
kind: filter
category: stylized
visible_behavior: Soft green through the midtones and whites, muted colour and a light matte, gentle enough for faces.
control_roles:
  amount: how far the look is applied
our_family: looks-and-grades
our_effect_id: soft-green-matte
already_in_hyperframes: partly (correction, LUT)
notes: none
```

```yaml
study_key: RS-072
reference_id: concat.midnight
kind: filter
category: cinematic
visible_behavior: Deep blacks, a cool cast over everything except warm lamps, low colour and a little grain; suits late-night desk footage.
control_roles:
  depth: how dark and cool the picture goes (master strength)
  grain: how much grain is added
our_family: looks-and-grades
our_effect_id: late-night-cool-grade
already_in_hyperframes: partly (correction, selective color, grain)
notes: Keeps warm light sources warm while cooling the rest.
```

```yaml
study_key: RS-073
reference_id: concat.milk
kind: filter
category: natural-look
visible_behavior: Bright and matte, with soft cool whites, blacks lifted well off the floor and quiet colour, like a clean white room.
control_roles:
  matte: how far blacks lift and whites soften (master strength)
  cool: how cool the whites are
our_family: looks-and-grades
our_effect_id: bright-cool-matte
already_in_hyperframes: partly (curves, correction)
notes: none
```

```yaml
study_key: RS-074
reference_id: concat.mono
kind: filter
category: retro
visible_behavior: Black and white as if shot through a coloured filter, where one setting darkens skies and lightens skin and the other does the reverse; grain is optional.
control_roles:
  colour_filter: which colour filter is simulated, from red-like to green-like
  contrast: how much contrast (master strength)
  grain: how much grain is added
our_family: looks-and-grades
our_effect_id: filtered-monochrome
already_in_hyperframes: partly (correction plus grain)
notes: Weighted channel mix before desaturation.
```

```yaml
study_key: RS-075
reference_id: concat.moody
kind: filter
category: cinematic
visible_behavior: Blacks crushed by a film-style toe, colour drained, bronze through the middle, cool shadows and the corners closing in.
control_roles:
  depth: how dark and drained the picture gets (master strength)
  warmth: how much bronze goes into the midtones
our_family: looks-and-grades
our_effect_id: dark-bronze-grade
already_in_hyperframes: partly (curves, correction, vignette)
notes: none
```

```yaml
study_key: RS-076
reference_id: concat.natural
kind: filter
category: portrait
visible_behavior: A gentle, true-to-life lift with barely any warmth and skin left alone.
control_roles: none
our_family: looks-and-grades
our_effect_id: gentle-natural-lift
already_in_hyperframes: partly (correction)
notes: none
```

```yaml
study_key: RS-077
reference_id: concat.neon
kind: filter
category: stylized
visible_behavior: Magenta in the shadows, cyan in the bright areas, hard contrast, strong colour and the light sources themselves blooming; suits night streets and signs.
control_roles:
  glow: how much the lights bloom (master strength)
  punch: how hard the contrast and colour are pushed
our_family: looks-and-grades
our_effect_id: neon-split-tone-glow
already_in_hyperframes: partly (LUT plus Bloom)
notes: Adjustable, blooming version of the fixed magenta-cyan split tone.
```

```yaml
study_key: RS-078
reference_id: concat.night
kind: filter
category: cinematic
visible_behavior: Low-light footage opened up, with shadows lifted, their noise smoothed before lifting, whites held and the blue of night kept.
control_roles:
  lift: how far the shadows are raised (master strength)
  clarity: how much local contrast and noise smoothing
our_family: looks-and-grades
our_effect_id: low-light-lift
already_in_hyperframes: partly (correction; no noise smoothing in the list)
notes: Denoising before lifting is the part that matters.
```

```yaml
study_key: RS-079
reference_id: concat.noir
kind: filter
category: cinematic
visible_behavior: Desaturated and heavy, with a cold cast in the shadows and dimmed corners.
control_roles: none
our_family: looks-and-grades
our_effect_id: cold-noir
already_in_hyperframes: partly (correction plus vignette)
notes: none
```

```yaml
study_key: RS-080
reference_id: concat.peach
kind: filter
category: portrait
visible_behavior: Skin warmed toward peach and softened, shadows lifted so lines ease and contrast lowered; meant for portraits at moderate strength.
control_roles:
  glow: how warm and luminous skin becomes (master strength)
  softness: how much skin is softened
our_family: looks-and-grades
our_effect_id: peach-skin-soften
already_in_hyperframes: partly (selective color plus Blur)
notes: Combines a skin-hue grade with soft-focus.
```

```yaml
study_key: RS-081
reference_id: concat.pink-fuzz
kind: filter
category: stylized
visible_behavior: Low contrast, pink and lavender in the light and a soft glow over everything.
control_roles:
  haze: how soft and low-contrast the picture gets (master strength)
  blush: how much pink and lavender is added
our_family: looks-and-grades
our_effect_id: pink-haze-bloom
already_in_hyperframes: partly (Bloom plus correction)
notes: none
```

```yaml
study_key: RS-082
reference_id: concat.polaroid
kind: filter
category: retro
visible_behavior: Instant-print look with a cream matte, warm bright areas, cyan creeping into the shadows and slight softness toward the corners.
control_roles:
  fade: how matte the print looks (master strength)
  warmth: how warm the bright areas are
our_family: looks-and-grades
our_effect_id: instant-print-look
already_in_hyperframes: partly (curves, correction, Blur)
notes: The studied name is a brand; ours must stay generic.
```

```yaml
study_key: RS-083
reference_id: concat.rain
kind: filter
category: cinematic
visible_behavior: Cool, hazy and drained, with wet reflections lifted and glowing; suits street walks at dusk.
control_roles:
  haze: how hazy and soft the picture gets (master strength)
  chill: how cool the cast is
our_family: looks-and-grades
our_effect_id: wet-street-grade
already_in_hyperframes: partly (correction plus Bloom)
notes: none
```

```yaml
study_key: RS-084
reference_id: concat.retro-70s
kind: filter
category: film
visible_behavior: A heavy warm fade with a yellowed, sun-bleached cast.
control_roles: none
our_family: looks-and-grades
our_effect_id: sun-bleached-fade
already_in_hyperframes: partly (curves plus a LUT)
notes: none
```

```yaml
study_key: RS-085
reference_id: concat.retro-cartoon
kind: filter
category: stylized
visible_behavior: Flat bands of colour with dark inked outlines, like a printed comic.
control_roles:
  levels: how many colour bands remain
  ink: how heavy the outlines are (master strength)
our_family: image-effects
our_effect_id: comic-ink-posterize
already_in_hyperframes: partly (Kuwahara Paint; posterize is not in the list)
notes: Posterize plus edge detection drawn in black.
```

```yaml
study_key: RS-086
reference_id: concat.rosy
kind: filter
category: portrait
visible_behavior: A soft pink lift in the bright areas, warm and flattering.
control_roles: none
our_family: looks-and-grades
our_effect_id: pink-highlight-lift
already_in_hyperframes: partly (correction)
notes: none
```

```yaml
study_key: RS-087
reference_id: concat.sage
kind: filter
category: cinematic
visible_behavior: Muted green-teal through the midtones, a gentle film curve and warmth only where a face is; the quiet look of an independent film.
control_roles:
  amount: how far the look is applied
our_family: looks-and-grades
our_effect_id: muted-teal-indie-grade
already_in_hyperframes: partly (curves, selective color)
notes: Skin-hue protection keeps faces warm.
```

```yaml
study_key: RS-088
reference_id: concat.sci-fi
kind: filter
category: cinematic
visible_behavior: A cool, sterile steel-and-teal look with saturation held back.
control_roles: none
our_family: looks-and-grades
our_effect_id: steel-teal-grade
already_in_hyperframes: partly (LUT)
notes: none
```

```yaml
study_key: RS-089
reference_id: concat.silver
kind: filter
category: black-and-white
visible_behavior: A cool, soft black and white with lifted shadows, like a silver gelatin print.
control_roles: none
our_family: looks-and-grades
our_effect_id: soft-cool-bw
already_in_hyperframes: partly (correction plus curves)
notes: none
```

```yaml
study_key: RS-090
reference_id: concat.soft-light
kind: filter
category: natural-look
visible_behavior: A matte with lifted blacks, eased-down whites, low contrast and a soft creamy glow in the light; airy and flattering.
control_roles:
  lift: how far blacks are lifted (master strength)
  warmth: how much cream is in the glow
our_family: looks-and-grades
our_effect_id: airy-matte-bloom
already_in_hyperframes: partly (curves plus Bloom)
notes: Not the soft-light blend mode, despite the studied name.
```

```yaml
study_key: RS-091
reference_id: concat.spooky
kind: filter
category: stylized
visible_behavior: Drained colour, a green-cyan cast, crushed shadows and a heavy vignette, for horror and Halloween clips.
control_roles:
  dread: how far the look is pushed
our_family: looks-and-grades
our_effect_id: eerie-green-grade
already_in_hyperframes: partly (correction plus vignette)
notes: none
```

```yaml
study_key: RS-092
reference_id: concat.super-8
kind: filter
category: film
visible_behavior: Faded, warm and grainy, like an old home movie run through a projector.
control_roles: none
our_family: looks-and-grades
our_effect_id: home-movie-film
already_in_hyperframes: partly (grain, Film Artifacts)
notes: The studied name is a film format name; ours stays generic.
```

```yaml
study_key: RS-093
reference_id: concat.teal-orange
kind: filter
category: cinematic
visible_behavior: Teal in the shadows, orange in the bright areas, skin kept as skin and a film curve over it all; the blockbuster look.
control_roles:
  amount: how strong the split tone is (master strength)
  contrast: how much film-curve contrast is added
  protect_skin: how much skin hues are held back from the shift
our_family: looks-and-grades
our_effect_id: teal-orange
already_in_hyperframes: partly (LUT, selective color)
notes: Skin protection is a user control here, not hidden.
```

```yaml
study_key: RS-094
reference_id: concat.tropical
kind: filter
category: outdoor
visible_behavior: Saturated and bright, with water pushed toward teal.
control_roles: none
our_family: looks-and-grades
our_effect_id: tropical-teal-boost
already_in_hyperframes: partly (selective color)
notes: none
```

```yaml
study_key: RS-095
reference_id: concat.umber
kind: filter
category: natural-look
visible_behavior: Café look with warm brown through the middle, greens muted to olive and contrast eased; kind to wood and skin.
control_roles:
  warmth: how much brown warmth is added (master strength)
  soften: how much contrast is eased
our_family: looks-and-grades
our_effect_id: warm-brown-cafe-grade
already_in_hyperframes: partly (correction, selective color)
notes: none
```

```yaml
study_key: RS-096
reference_id: concat.vhs
kind: filter
category: retro
visible_behavior: Colour smears sideways, scan lines show, the picture softens, tape noise crawls and saturation runs too high, with a slight vertical smear from a worn head.
control_roles:
  bleed: how far colour smears sideways (master strength)
  lines: how visible the scan lines are
our_family: image-effects
our_effect_id: vhs-tape
already_in_hyperframes: partly (Tape Damage, Scanlines, Chroma Softening)
notes: One package bundles what HyperFrames splits into several media effects.
```

```yaml
study_key: RS-097
reference_id: concat.vaporwave
kind: filter
category: mood
visible_behavior: Magenta and cyan pushed hard into a saturated retro-synth cast.
control_roles: none
our_family: looks-and-grades
our_effect_id: pastel-magenta-cyan-cast
already_in_hyperframes: partly (LUT)
notes: none
```

```yaml
study_key: RS-098
reference_id: concat.vibrance
kind: filter
category: color
visible_behavior: Muted colours get richer while colours that are already strong are left mostly alone.
control_roles:
  amount: how much the muted colours are boosted
our_family: looks-and-grades
our_effect_id: vibrance
already_in_hyperframes: partly (correction, selective color)
notes: none
```

```yaml
study_key: RS-099
reference_id: concat.vivid
kind: filter
category: natural-look
visible_behavior: Strong colour, biting contrast and a little edge sharpening, so footage looks shot on a better camera, with skin held back from the boost.
control_roles:
  colour: how much colour is added (master strength)
  punch: how much contrast and edge is added
our_family: looks-and-grades
our_effect_id: vivid-punch
already_in_hyperframes: partly (correction, selective color)
notes: none
```

```yaml
study_key: RS-100
reference_id: concat.vintage
kind: filter
category: retro
visible_behavior: An old print look with matte blacks and whites, faded colour, greens drifting to yellow and a soft vignette.
control_roles:
  age: how faded and matte the print is (master strength)
  tint: how much the colours drift warm and yellow
our_family: looks-and-grades
our_effect_id: faded-print-matte
already_in_hyperframes: partly (curves, LUT, vignette)
notes: none
```

```yaml
study_key: RS-101
reference_id: concat.warm
kind: filter
category: color
visible_behavior: The whole picture shifts toward warm candlelight.
control_roles:
  temperature: how warm the shift is
our_family: looks-and-grades
our_effect_id: warm-shift
already_in_hyperframes: partly (correction)
notes: One-knob temperature shift.
```

```yaml
study_key: RS-102
reference_id: concat.winter-cool
kind: filter
category: outdoor
visible_behavior: Desaturated and blue, with blacks lifted into a matte wintry haze.
control_roles: none
our_family: looks-and-grades
our_effect_id: wintry-blue-matte
already_in_hyperframes: partly (curves plus correction)
notes: none
```

## Audio filters (not studied in depth)

Listed for completeness. These are sound effects, not picture effects, and none were assigned our ids.

- concat.bass: boosts the low end.
- concat.bright: lifts the top end for air and presence.
- concat.cathedral: a large stone-space reverb whose reflections arrive late.
- concat.chipmunk: raises the pitch for a small, squeaky voice.
- concat.deep: lowers the pitch and adds body.
- concat.denoise: removes steady hum and hiss from under speech.
- concat.distorted: overdrives and clips the signal.
- concat.echo: a single delayed repeat that fades.
- concat.enhance-voice: a cleanup chain for rumble, hiss, harsh sibilants and uneven level.
- concat.hall: a long, even concert-hall reverb.
- concat.lofi: a tiny old speaker with the top end cut and gritty bit reduction.
- concat.loudness: brings the whole clip to one target loudness.
- concat.megaphone: a harsh, mid-heavy, driven voice.
- concat.pitch: shifts pitch by semitones without changing length.
- concat.plate: a dense, bright, short plate reverb.
- concat.radio: a narrow band with light crunch and noise.
- concat.robot: a metallic, modulated voice.
- concat.room: the early reflections of a small room.
- concat.stadium: a very large arena reverb.
- concat.sweet: a lighter, closer, brighter voice whose pitch follows the amount unless set.
- concat.telephone: the narrow band of a phone line with some drive.
- concat.treble: boosts the high end.
- concat.underwater: heavy low-pass muffling.
- concat.vinyl: warm, band-limited turntable character.
- concat.whisper: a breathy voice with thin low end and more presence.
