# Example: outlier scoring

Synthetic. Every account, video, and figure below is invented test data. None describes a real creator or a real video.

**Owner:** Dana, who runs a 14-person bookkeeping firm. **Request:** "Study the top outliers for 'small business bookkeeping' on short-form and show me what their edits have in common."

## What the editor did first

It had no research route of its own, so it asked `social-media` for a shortlist. The shortlist arrived through Kanban with links, view counts, and the date they were read. The editor put the figures in a dataset file and ran:

```bash
python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" outlier-score dataset.json
```

## Result returned to Dana

Study bounds: synthetic platform, short-form, keyword "small business bookkeeping", window 2026-09-01 to 2026-09-30, figures read 2026-10-06 12:00 UTC, route `social_media_shortlist`.

| Rank | Video | Account | Views (synthetic) | Account baseline median (synthetic) | Baseline size | Outlier score |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | a-hit | ledger-lane | 3,000 | 300 | 5 | 10.0 |
| 2 | c-hit | tidy-books | 300 | 60 | 5 | 5.0 |
| 3 | b-hit | big-finance-channel | 60,000 | 30,000 | 5 | 2.0 |

Set aside, not ranked:

| Video | Why |
| --- | --- |
| d-boosted | Marked as a boosted post in the shortlist |
| e-missing | Views `Unavailable` in the shortlist |

What this shows: the small account's video ranks first, with one twentieth of the large account's raw views (synthetic), because the score is relative to each account's own baseline.

What it does not show:

- Evidence depth is `metadata_only`. It supports findings about length, title, and packaging. It supports no finding about cuts, captions, or pacing.
- Nothing here says why any video performed.
- No cutoff was applied. Dana decides how many to study.

## The one question

"Which of these do you want studied, and can you supply them as files you have the right to hold? Without files I can report length and packaging only."

## What it did not do

It did not open a platform, log in, or download a video.
