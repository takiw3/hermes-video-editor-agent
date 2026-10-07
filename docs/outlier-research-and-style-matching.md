# Outlier research and style matching

## The rule

No composition is written until the project holds a fresh outlier study with a chosen style option, or a recorded owner waiver for that one edit.

## The workflow, in plain steps

1. **Bound the study.** One platform, one format, one niche or keyword, one time window, and a result count.
2. **Gather candidates on a permitted route.** A shortlist from the `social-media` profile, or links, figures, and files you supply. The profile does not log in, scrape, or download.
3. **Score them.** A video's outlier score is its views divided by the median views of the same account's recent videos in the same format. A small account's breakout can outrank a large account's average video. Missing figures stay `Unavailable`.
4. **Rank, without a cutoff.** You decide how many to study. No view count makes a video an outlier.
5. **Set aside what is not comparable.** Paid, boosted, reposted, compilation, and news-event videos are flagged or excluded where that can be determined.
6. **Build a contrast set.** Ordinary videos from the same accounts.
7. **You confirm the shortlist** before any deep analysis.
8. **Measure and observe.** Cuts, shot lengths, time to first cut, loudness, and silence are measured with FFmpeg at recorded thresholds. Captions, punch-ins, b-roll, overlays, transitions, color, and framing are observed in frames sampled on a recorded schedule.
9. **Compare against the contrast set.** A feature in both sets is that creator's habit. Only a feature that separates the outliers is worth testing.
10. **Write the blueprint.** Each feature tagged `measured`, `observed`, or `inferred`, mapped to something the bundled tools can do, with a do-not-copy list, a confidence level, and a valid-until date.
11. **Get the proposal.** Three options: house style, outlier-matched, and hybrid, each with what changes, what it costs, and the risk to your brand.
12. **You choose, or waive for one edit.** The choice is recorded in `style-decision.yaml` with who decided and when.
13. **The edit records its blueprint**, so `social-media` can compare measured results later.

## What a style match is

A test of a hypothesis. The offer reads: the outliers studied share these features, the contrast set does not, here is an edit in that style, and here is how the result will be compared.

## What it is not

- Not a forecast. No option comes with expected views, reach, followers, or revenue.
- Not an explanation. The study cannot show why a video performed. Topic, creator, timing, title, thumbnail, and distribution all move with the edit.
- Not a copy.

## Technique and expression

| May be matched (technique) | Must not be copied (expression) |
| --- | --- |
| Pacing and cut rhythm | Another creator's script |
| Shot length | On-screen wording |
| Opening structure | Graphics files, logos, characters |
| Caption placement and density | Branded templates and thumbnails |
| Zoom frequency | Signature catchphrases |
| B-roll and overlay density | Music tracks and sound files |
| Transition type | Footage |
| Music energy and sound-design density | A distinctive brand identity |
| Pacing curve and ending structure | |

A reference video is evidence about technique. It is not an asset. Nothing from one enters a deliverable: no frame, no clip, no audio, no graphic, no text. Credit is not a license. A request to recreate a specific video shot for shot is refused, and the technique-level match is offered.

## Evidence depth

| Depth | What you have | What it supports |
| --- | --- | --- |
| `metadata_only` | Figures and titles | Length, title, and packaging. No finding about cuts, captions, or pacing. |
| `owner_supplied_reference` | Files you have the right to hold | Measured and observed edit features |
| `observed_playback` | Videos watched on a permitted route | Observed edit features |

`editor_tools.py check-blueprint` fails a `metadata_only` blueprint that describes cuts or captions.

## How the rule is enforced

Stated plainly, because it matters:

- **In code, through the launcher.** A final render is refused while the project has no valid `style-decision.yaml`. A draft with no decision is refused unless it carries a `--comparison` tag naming which option it shows. A stale blueprint blocks the final until the approver accepts reuse. A waiver must name a reason and must be scoped to one edit.
- **In configuration.** The profile's deny rules block the plain command forms that would run the CLI without the launcher.
- **By instruction only.** The decision file proves a choice was recorded. It cannot prove who made it, and the agent writes the file. "The owner chose" rests on the agent following its rules. A command hidden inside a script file is also not matched by a deny rule.

So the gate is technical for every sanctioned path and instructional at the edges. The gate tests record this, including a direct call to the CLI that goes around the launcher and produces a file with no receipt, which the handoff command then refuses.

## Reference material

- Reference files live in the workspace's `references/` folder, outside every project.
- The launcher refuses any project that points into that folder, links into it, or holds a byte-identical copy of a file in it, on every render, lint, check, snapshot, and preview. A re-encoded or trimmed copy has a different checksum and is not detected, so the rule also stands as an instruction.
- Sampled frames are written to a session folder, never to a project, and deleted when the task ends.
- A contact sheet of a reference is refused, because it would be a saved copy of its frames.
- Looking at a frame sends it to your configured model provider.

## Performance feedback

The editor does not own analytics. It asks `social-media` for measured results by edit ID and blueprint ID, compares like with like, states the sample size, and treats every link between an edit choice and a result as a hypothesis. A blueprint's confidence changes only from measured results, and a blueprint the data contradicts is retired.
