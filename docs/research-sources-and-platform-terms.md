# Research sources and platform terms

Every row below was read from the official page on the access date shown. The machine-readable copy the agent uses is `skills/integrations/editor-hyperframes/references/platform-facts.yaml`. Platforms change these pages often: a fact older than 90 days is re-read before it is relied on.

This page summarizes published specifications and terms for reference. It is not legal advice.

## Research routes

| Route | Status in this release | Basis |
| --- | --- | --- |
| A shortlist handed over by `social-media` through Kanban | enabled | No platform access by this profile |
| Reference links, figures, and files the owner supplies | enabled | No platform access by this profile |
| An official platform API with an owner credential (`connected_research`) | not built | No platform passed every condition. See below. |
| Automated viewing of public pages | not permitted by terms | Every platform read prohibits it without written permission |

A new profile reports research as `owner-supplied only`.

### What each platform's terms say about automated access (accessed 2026-10-06)

| Platform | What the terms say | Source |
| --- | --- | --- |
| YouTube | No access to the Service using any automated means (such as robots, botnets or scrapers), except public search engines under robots.txt or with prior written permission. No downloading except as expressly authorized. | https://www.youtube.com/t/terms |
| Instagram | You can't access or collect information in an automated way without express permission, whether or not logged in. | https://help.instagram.com/581066165581870 |
| Facebook and Instagram (Meta) | No Automated Data Collection without Meta's express written permission. | https://www.facebook.com/apps/site_scraping_tos_terms.php |
| TikTok | You must not scrape, crawl, export or otherwise extract any data or content using any automated system or software, except as approved in writing. | https://www.tiktok.com/legal/page/us/terms-of-service/en |
| LinkedIn | Prohibited conduct includes developing, supporting, or using software, scripts, robots, or crawlers to scrape the Services. | https://www.linkedin.com/legal/user-agreement |
| X | Crawling or scraping the Services in any form, for any purpose, without prior written consent is expressly prohibited. Access only through published interfaces. | https://x.com/en/tos |

### Official data APIs (accessed 2026-10-06)

| Platform | What the route exposes | Authentication | Status | Why |
| --- | --- | --- | --- | --- |
| YouTube Data API | `videos.list` returns a `statistics` part at 1 quota unit per call. `search.list` can order by view count, returns at most 50 items per page, and has its own bucket of 100 calls per day. Other endpoints share a default 10,000 units per day. | A credential from the owner's own Google Cloud project | not built | The Developer Policies say not to aggregate API Data or use it to gain insights into YouTube's usage, and require each API client to publish a privacy policy and follow stored-data rules. Whether a per-account baseline study fits is the owner's call to make with counsel. Sources: https://developers.google.com/youtube/terms/developer-policies, https://developers.google.com/youtube/v3/docs/videos/list, https://developers.google.com/youtube/v3/docs/search/list, https://developers.google.com/youtube/v3/determine_quota_cost |
| Instagram Platform APIs | Management of professional accounts that connect to the app: messaging, publishing, comments, mentions, hashtag search, insights. | A Meta app and an account that grants it access | not built | Built around accounts that authorize the app. No route to other accounts' per-video view counts was confirmed, and none was tested. Sources: https://developers.facebook.com/docs/instagram-platform, https://developers.facebook.com/terms |
| TikTok Research API | Public video fields including `view_count`, `like_count`, `create_time`, and `video_duration`. | An approved research application | not permitted by terms | For qualified researchers at academic or not-for-profit institutions, independent of commercial interests. Sources: https://developers.tiktok.com/products/research-api/, https://developers.tiktok.com/doc/research-api-specs-query-videos |
| X API | Not inspected in detail | An X developer account | not permitted by terms | The X Developer Policy says you may not use the X API to measure the usage of X for benchmarking, competitive, or commercial purposes. Source: https://developer.x.com/en/developer-terms/agreement-and-policy |
| LinkedIn, Facebook | No public-video data route was read | | not built | |

No `connected_research` mode ships. The profile is complete with owner-supplied references and `social-media` shortlists.

## Video specifications (accessed 2026-10-06)

| Platform | Verified | Source |
| --- | --- | --- |
| YouTube | Recommended upload: MP4 with the moov atom at the front, H.264, progressive scan, AAC-LC or Opus audio. Upload at the recorded frame rate; common rates include 24, 25, 30, 48, 50, and 60 frames per second. | https://support.google.com/youtube/answer/1722171 |
| YouTube Shorts | A square or vertical video up to three minutes, uploaded on or after October 15, 2024, is categorized as a Short. A wider aspect ratio such as 16:9 keeps a video long-form. | https://support.google.com/youtube/answer/15424877 |
| Instagram Reels | Aspect ratio between 1.91:1 and 9:16. Minimum 30 frames per second. Minimum resolution 720 pixels. Recommended cover 420 by 654 pixels. | https://help.instagram.com/1038071743007909 |
| Facebook Reels | All videos are shared as reels and can be any length or orientation. Recommended: MP4, 1080p, H.264 or H.265, 24 to 60 frames per second, stereo AAC-LC at 44.1 or 48 kHz. | https://www.facebook.com/business/help/1197310377458196 |
| TikTok | Recorded videos up to 10 minutes; uploaded videos up to 60 minutes. | https://support.tiktok.com/en/using-tiktok/creating-videos/camera-tools |
| LinkedIn | Maximum 5 GB and 15 minutes. Resolution 256x144 to 4096x2304. Aspect ratio 1:2.4 to 2.4:1. 10 to 60 frames per second. 192 Kbps to 30 Mbps. The page showed "Last updated: 2 years ago". | https://www.linkedin.com/help/linkedin/answer/a548372 |
| X | Not verified. The help page returned HTTP 403 to an automated read. | https://help.x.com/en/using-x/x-videos |

## Not verified on any platform

- **Numeric safe zones.** No official page read gives pixel margins. LinkedIn says to keep the edges free of text and logos and gives no number. Safe zones come from you, recorded as yours.
- **Caption reading-speed rules.** None ships. Use your own or cite a current source.
- **Loudness targets.** None ships.
- **TikTok upload resolution, aspect ratio, file size, and codec for organic posts.**
- **Instagram maximum reel duration and file size.**

## AI-generated content labeling (accessed 2026-10-06)

| Platform | Verified | Source |
| --- | --- | --- |
| YouTube | Creators must disclose, with the AI use setting in YouTube Studio, AI that meaningfully alters or generates photorealistic content. Non-realistic content and minor edits do not need disclosure. | https://support.google.com/youtube/answer/14328491 |
| TikTok | Creators apply the "creator labeled as AI-generated" label to content completely generated or significantly edited by AI. TikTok also applies automatic labels. | https://www.tiktok.com/support/faq_detail?id=7636670084747893268 |
| Instagram | The help article exists. Its conditions were not readable. Not verified. | https://help.instagram.com/761121959519495 |
| Facebook, LinkedIn, X | Not verified. | |

The editor flags a deliverable that contains generated voice, generated imagery, or altered footage of a real person to `social-media`, which owns packaging and applies the label.

## Hermes and HyperFrames sources (accessed 2026-10-06)

| Source | Used for |
| --- | --- |
| https://hermes-agent.nousresearch.com/docs/user-guide/profile-distributions | Install and update commands, manifest |
| https://hermes-agent.nousresearch.com/docs/user-guide/profiles | Profile isolation |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban | Cross-profile tasks |
| https://hermes-agent.nousresearch.com/docs/user-guide/features/skills, https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills | Skill format |
| https://hermes-agent.nousresearch.com/docs/reference/optional-skills-catalog, https://hermes-agent.nousresearch.com/docs/user-guide/skills/optional/creative/creative-hyperframes | The Hermes optional `hyperframes` skill: its setup installs `hyperframes@>=0.4.2` globally and locates itself with `find ~/.hermes/skills` |
| https://github.com/NousResearch/hermes-agent/releases/latest | Latest stable: v0.21.5, tag `v2026.9.24`, commit `f97608f178d1ffeca59860195ab7da295f7c8e5f` |
| Tagged Hermes source: `hermes_cli/profile_distribution.py`, `hermes_cli/profiles.py`, `hermes_cli/config_defaults.py`, `tools/approval_floors.py`, `tools/terminal_scope.py`, `agent/skill_utils.py`, `tools/skills_tool.py`, `hermes_cli/kanban.py` | Manifest parsing, copy rules, skill discovery, deny rules, `terminal.home_mode`, Kanban commands and attachments |
| https://github.com/heygen-com/hyperframes/releases/latest | Latest stable: v0.8.138, commit `0ca28db4f8671a2e2262594e03c566222d695920` |
| Tagged HyperFrames source: `skills/`, `.claude/skills/`, `plugin.json`, `skills-manifest.json`, `LICENSE`, `CREDITS.md`, `packages/cli/src/` | Vendoring, patches, CLI switches, render flags, registry fetch path, model and browser sources |
| https://gsap.com/standard-license | GSAP license terms |

The Hermes and HyperFrames facts were read from the tagged source checkouts, which are the source of truth where a web page and the code differ. `https://hyperframes.heygen.com` returned no readable text to an automated read and is not relied on.
