---
name: captions-overlay
description: Overlay doctrine for the embedded-captions workflow — the caption MODEL (drop / rail / embed) and the rule that captions are an OVERLAY composited on top of the film, never a reserved bottom band you shift content up to avoid. Load when adding captions/subtitles to a talking-head or launch video, when deciding whether a phrase should be dropped, ride the verbatim rail, or be promoted to a scarce embedded climax, when laying out a composition that will carry captions (do NOT reserve a keep-out band), or when centering a composition on the true frame center under captions. Quotes the rail+embed model from embedded-captions and constraint #13 (captions overlay, keep-out band retired) from the product-launch-video scene agent. Applies ON TOP of embedded-captions.
version: 0.8.138
author: HeyGen, Inc. (modified by TakiGPT AI Inc.)
license: Apache-2.0
metadata:
  internal: true
  hermes:
    tags: [hyperframes, video, vendored, upstream-internal]
    related_skills: [editor-hyperframes]
---

> **Modified file. Derived from HeyGen HyperFrames v0.8.138 (commit 0ca28db), licensed under Apache-2.0, Copyright 2026 HeyGen, Inc. Changed by TakiGPT AI Inc. for the Hermes video-editor profile. Rules applied: hermes-frontmatter, runtime-rules-banner, internal-upstream-notice. See skills/hyperframes-video/MODIFICATIONS.md.**

> **Profile runtime rules. These override anything below.**
>
> 1. Load the `editor-hyperframes` skill first. It governs every HyperFrames call in this profile.
> 2. Run every HyperFrames command through the pinned launcher: `python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" <command>`. Never run the CLI through `npx`, as a bare `hyperframes` binary, or at any other version.
> 3. Run a bundled helper script as `python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py" script <path-to-script> <args>`, never with `node` directly.
> 4. `/name` means the bundled skill `name`. Load it with `skill_view("name")`. A link such as `../media-use/references/x.md` means `skill_view("media-use", "references/x.md")`. `<SKILL_DIR>` is the `skill_dir` value `skill_view` returns for this skill.
> 5. These skills are release-managed. Never update, install, or download a skill. If a workflow is not bundled, say so and offer the closest bundled one.
> 6. Cloud render, Lambda, Cloud Run, publish, feedback, sign-in, website capture, and provider calls are unavailable in the default mode. A command shown as `[unavailable in this profile: ...]` must not be run in any form.
> 7. Any download (CLI, browser, speech model, font, media, registry block) needs one-time owner approval naming the item, source, size, and license.

> **Internal upstream material.** Upstream keeps this skill under `.claude/skills/`, marks it `metadata.internal: true`, and does not distribute it with the published set. It may change or disappear without notice in a later release. Where it names a skill that is not bundled in this profile, that skill is unavailable: say so and continue with the bundled ones.

# Captions Overlay Doctrine

> **Overlay doctrine — supplements the upstream `embedded-captions` skill. Applies ON TOP of it; do not expect it folded into the upstream skill.**

Two ideas combine here. First, the **caption model** — every spoken phrase is `drop`,
`rail`, or `embed`, and embed is the scarce earned peak, not the default. Second, the
**overlay law** — a caption line is composited ON TOP of the film as an overlay; it is
NOT a reserved zone, so you never shift content up or leave a dead band to "make room"
for it. The two reinforce each other: because captions ride as an overlay (the verbatim
rail in front, the occasional embed behind the subject), the composition keeps its full
frame and centers on the true vertical center.

## The caption model — drop / rail / embed

Every spoken phrase is one of three things (verbatim from `embedded-captions`):

|           | What                                             | How it's shown                                                                                                                                                    |
| --------- | ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **drop**  | filler — um/uh, stutters, self-corrections       | not shown                                                                                                                                                         |
| **rail**  | the default — ordinary spoken content (verbatim) | clean lower-third subtitle, **in front**, readable. A punch word can get an inline `emphasis` highlight (accent colour / active-word pop) — it stays on the rail. |
| **embed** | a promoted peak — the headline beat              | one big word composited **behind the subject** (matte occlusion), designed entrance + exit                                                                        |

**The rail carries most of the text; embed is the scarce, earned peak** — ≤1 per beat,
never two adjacent/co-visible, spaced ≥ a beat apart. A short clip → usually one embed;
a long explainer → ~one per section. Embedding every word is the common mistake.

This is the **Standard** mode shape (rail = the verbatim lower-third; embed = the climax
composited behind the subject). **Cinematic** mode drops the rail and makes everything
embed-style — use it only for pure-cinematic asks, never for explainer / voiceover where
the words must read.

### Rail-first, embed-scarce (the load-bearing rules)

Quoted from the `embedded-captions` non-negotiables:

- **Rail-first for talking-head / explainer.** Don't embed the whole transcript — most
  text is the rail; embed only peaks. Embedding everything is the default mistake.
- **Embed is scarce + spaced.** ≤1 embed per sentence/beat, never two adjacent or
  co-visible, ≥ a beat apart, at most one `apex`. climax = per-beat peak, **not** "the
  single payoff of the entire clip."

## The overlay law — captions are NOT a reserved band

In a generated launch composition, when captions are enabled, finalize composites a
**small, minimal word-by-word caption line** as an overlay layer ON TOP of the whole
film (a single text line, bottom-centered, roughly the bottom ~5-8% of canvas height).
It is an overlay, not a reserved zone (verbatim from constraint #13 of the
product-launch-video scene agent):

- **Center the composition on the TRUE vertical center — y = H / 2** (landscape 540,
  portrait 960). Do not shift content up to "make room" for captions; a composition
  centered at 0.42 × H with a dead lower band is the bug, not the fix.
- Content may extend to the canvas bottom. Full-bleed subjects, rails, and backgrounds
  all welcome.
- **One soft courtesy rule:** avoid parking _critical small readable text_ (a URL line,
  a legal line, a sub-caption) exactly in the bottom ~80px center span where the caption
  line sits — the overlay would fight it. Large imagery / cards / ambient content under
  the captions is fine; the caption skin is designed to read over content.
- There is no machine keep-out gate (the old `captions.mjs keepout` check is retired).
  Finalize snapshot QA judges caption-over-content legibility visually.

**When captions are disabled:** identical positioning freedom — the overlay simply
doesn't exist.

## Why these two rules are one doctrine

The model says the rail rides **in front** and an embed is a rare word composited
**behind the subject** — both are layers added to footage that ships untouched. The
overlay law says the caption line is a layer composited **on top** of the whole film,
not a band carved out of the layout. So in both the captioning pipeline and the
launch-video pipeline, captions are an overlay you add, not a zone you reserve:

- Keep the full frame; center on true center; let content run to the edges.
- Make the rail (or the small overlay caption line) carry the verbatim words.
- Promote a word to an embed only at a genuine peak — scarce, spaced, never two at once.
- Reserve nothing; judge legibility of captions-over-content visually, not by a keep-out gate.
