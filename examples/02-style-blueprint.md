# Example: a style blueprint

Synthetic. The references, accounts, and measurements below are invented test data.

**Owner:** Aisha, who runs a bookkeeping practice. She confirmed three outliers and three ordinary videos from the same three accounts and supplied all six as local files.

## How it was measured

Same thresholds for all six files:

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" cuts references/ref-01.mp4 --threshold 0.30 --min-shot 0.20
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" frames references/ref-01.mp4 --schedule short-form
```

## Blueprint (excerpt)

```yaml
blueprint_id: SB-SYN-014
blueprint_version: 1
study_id: OS-SYN-014
platform: synthetic-platform
format: short-form
evidence_depth: owner_supplied_reference
reference_count: 3
duration_range: 21 to 34 seconds across the three outliers
opening_structure: >-
  First cut between 0.6 and 0.9 seconds in all three outliers. In the contrast
  set the first cut falls between 2.4 and 4.1 seconds.
cut_rhythm: 18 to 26 cuts per minute in the outliers; 9 to 14 in the contrast set
shot_length_distribution: median shot 2.1 to 3.0 seconds in the outliers
caption_treatment: large centered captions, two to four words per card, in all six videos
features_shared_with_contrast_set: [caption_treatment]
features_distinct_to_outliers: [opening_structure, cut_rhythm]
feature_evidence_tags:
  duration_range: measured
  opening_structure: measured
  cut_rhythm: measured
  shot_length_distribution: measured
  caption_treatment: observed
analysis_tools_and_thresholds:
  cut_detection: editor_tools.py cuts 1.0.0, FFmpeg scene threshold 0.30, minimum shot 0.20 seconds
  frame_sampling: short-form schedule, every 0.25 s to 3 s, 0.5 s to 10 s, 1 s to 30 s
hyperframes_mapping:
  - feature: opening_structure
    maps_to: hard cut and trim recipes
    tested: true
not_reproducible_with_bundled_tools: []
do_not_copy:
  - reference: ref-01
    items: [script, on-screen wording, the arrow graphic, the music track]
confidence: "low: three references from three accounts, one platform, one month"
valid_until: "2026-11-05"
```

## What the editor said about it

- The early first cut and the faster cut rhythm separate the outliers from the same accounts' ordinary videos. Those two are worth testing.
- The caption style is in both sets. It is those creators' habit, so it is not offered as a test.
- Scene detection finds hard visual changes. It can miss a cut between similar frames, and a different threshold gives a different count.
- The blueprint describes technique. It says nothing about why these videos performed.

Sampled frames were deleted with `session-clean` when the task ended.
