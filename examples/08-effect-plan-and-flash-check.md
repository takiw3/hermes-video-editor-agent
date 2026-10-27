# Example: an effect plan, applied and checked

Synthetic. The owner, the footage, and every value below are invented test data.

**Owner:** Priya, who runs a two-chair dental clinic. **Request:** "Make the clinic tour feel calm and premium. Put my name on screen when I first appear."

## What the editor did first

No effect plan existed, so it applied nothing. It listed the verified looks and transitions and picked for the brief: calm, not flashy.

```bash
python3 "$HERMES_HOME/skills/video-effects-core/effects-library/scripts/fx.py" list --family looks-and-grades --status verified
python3 "$HERMES_HOME/skills/video-effects-core/effects-library/scripts/fx.py" show clean-studio
```

It wrote `effect-plan.yaml`:

```yaml
plan_id: EP-0001
project_id: clinic-tour
version: v2
effect_approver: owner
photosensitivity_budget: pass
hdr_sources: false
render_cost_budget: 4
effects:
  - effect_id: clean-studio
    target: "#tour-clip"
    params: {intensity: 0.8}
    why: neutral, slightly brighter rooms without a visible style
  - effect_id: crossfade
    from: "#scene-reception"
    to: "#scene-room-1"
    at: 12.4
    duration: 0.5
    why: a quiet room change
  - effect_id: lower-third
    target: "#tour-wrap"
    at: 2.0
    duration: 4.0
    why: Priya's name and role when she first appears
```

`fx.py check-plan effect-plan.yaml` returned `pass`. Priya approved the plan, and the edit state became `effect_plan_approved`.

## Applying it

```bash
FX='python3 "$HERMES_HOME/skills/video-effects-core/effects-library/scripts/fx.py"'
$FX apply . --effect clean-studio --target '#tour-clip' --param intensity=0.8
$FX apply . --effect crossfade --from '#scene-reception' --to '#scene-room-1' --at 12.4 --duration 0.5
$FX apply . --effect lower-third --target '#tour-wrap' --at 2 --duration 4
$FX stack-check .
```

The lower third shipped with placeholder text, so the editor replaced "Name here" and "Role here" inside the `fx:overlay` block with the wording Priya supplied, before the draft render.

## Checks on the draft

```bash
$FX flash-check renders/clinic-tour-v2-draft.mp4
```

Result: `pass`. No concurrent flash anywhere, and no small-area flicker. `hf.py check` reported no contrast finding on the lower third.

## Result returned

```yaml
status: approval_required
effect_plan_reference: projects/clinic-tour/effect-plan.yaml
effects_used:
  - {iid: cleanstudi1, effect_id: clean-studio, target: "#tour-clip", params: {intensity: 0.8}}
  - {iid: crossfade1, effect_id: crossfade, target: "#scene-reception -> #scene-room-1", window: [12.4, 12.9]}
  - {iid: lowerthird1, effect_id: lower-third, target: "#tour-wrap", window: [2.0, 6.0]}
effect_versions: {clean-studio: "<verified_at from the catalog>", crossfade: "<...>", lower-third: "<...>"}
photosensitivity_result: pass
```

The editor did not say the effects would improve results. It said the draft is ready for Priya's review.
