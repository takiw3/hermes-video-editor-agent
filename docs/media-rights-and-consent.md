# Media rights and consent

This page describes the editor's rules. It is not legal advice. Where a question is legal, the editor flags it, cites the official source, and escalates.

## The register

Every project has an `asset-rights-register.yaml`: asset, source, license, proof, restrictions, what it is cleared for, and who appears in it. The field names match the `social-media` profile's register.

- An asset with no recorded license is unusable.
- `hf.py rights-check` lists every asset in the project with no entry and every entry with a blank source, license, or proof.
- A final render is refused while either list is non-empty.
- The editor records what you tell it. It never fills a blank itself.

## Rules by asset type

| Asset | Rule |
| --- | --- |
| Music | A license you hold, with proof. Platform music libraries license use inside that platform. A sound is not assumed cleared for a rendered file, a business account, or a sponsored post. |
| Sound effects | The 19 bundled effects are from Pixabay under the Pixabay Content License, as recorded upstream. Each one used is entered in the register. |
| Fonts | A license that covers video, recorded. |
| Logos | A logo belongs to its owner. Used only with your confirmation that the use is permitted. |
| B-roll and images | From libraries you own or have licensed. Nothing is fetched. |
| Catalog media reached through `media-use` | Off. Treated as unlicensed until its terms are read and recorded. |
| Registry items | Fetched only by you. Recorded with file hashes, and entered in the register before use. |
| GSAP | Installed from npm by your setup step, under the GSAP Standard License. Recorded in each project's register by the launcher. |

## Reference videos

A reference video is studied for technique. Nothing from it enters a deliverable: no frame, no clip, no audio, no graphic, no text. Credit is not a license. The launcher keeps the reference folder out of every render path.

## People

- Recorded consent is required for any identifiable person on camera, any client named, and any minor.
- Footage involving a minor always escalates.
- A request for a voice clone, an avatar, or a deepfake of a real person is refused and escalated.
- A request to cut or reorder speech so it says something the person did not mean is refused and escalated.

## Disclosure and labels

- A sponsorship disclosure in the script or brief is never removed or obscured.
- Where a deliverable contains generated voice, generated imagery, or altered footage of a real person, the editor flags the platform's AI-label guidance to `social-media`, which owns packaging. What was verified about each platform's labeling rules, with dates, is in `research-sources-and-platform-terms.md`.

## Claims on screen

Words the speaker did not say need your recorded approval. A claim, a result, or a testimonial that is not in the approved script goes to `marketing`. Health, financial, legal, and earnings claims on screen escalate.

## When something goes wrong

Copyright claims, takedown notices, and platform strikes about a past edit escalate to the Executive profile with that edit's rights register. The editor may draft a holding note. It promises no legal, platform, or commercial outcome.
