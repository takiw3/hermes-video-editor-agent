# Editor onboarding

Installing the profile does not start onboarding. Onboarding begins on your first direct chat, or the first time a delegated task is missing context only you can give. If `social-media` or the Executive sends a complete brief with valid source references, the editor does the task without it.

## How it runs

1. The editor checks what it already has: approved memory, and `local/editor-profile.md`.
2. It explains the short setup.
3. It asks one question at a time, and never repeats one you answered.
4. You can skip, correct, pause, resume, or hand over documents instead of answering.
5. It asks for consent before reading footage, transcripts, reference videos, or performance data.
6. It summarizes the finished setup and asks you to confirm.
7. Only then does it save: compact preferences through the memory approval gate, and the full context in `local/`, which updates never touch.

## What it collects

- Business name, website, market, and what the content is meant to achieve
- Platforms, formats, and their priority order
- Niches and keywords that define your category on each platform
- Reference creators and videos you admire, and what you like about each
- Creators and styles you do not want to resemble
- Your house style, with past edits you are proud of
- Brand identity: colors, fonts with license status, logo files, lower-third style, cover style, intro and outro rules
- Caption style: font, size, position, color, active-word emphasis, words per card, casing
- Safe-zone preferences beyond platform minimums
- On-screen text rules, and words you never put on screen
- Music and sound-effect sources you are licensed to use
- B-roll and screen-recording libraries you own
- Consent status for people who appear on camera
- Camera, microphone, and typical recording format, including phone footage quirks
- Typical raw footage length, and target durations per platform and format
- Delivery specs beyond platform minimums
- Who reviews an edit, how many revision rounds are normal, who gives final approval, and who approves the style choice
- The video workspace and the handoff folder, which you approve with the setup command
- Hardware, which the editor measures where it can
- Acceptable render time for a draft and for a final
- Which downloads you approve: browser, transcription model
- Which research routes you approve
- How long an outlier study stays fresh, and how many outliers and contrast videos per blueprint
- Whether you want a study before every edit, or reuse of a fresh blueprint
- Retention rules for footage, working copies, transcripts, reference material, and renders
- Read, edit, render, and action levels
- The installed profile IDs for the Executive, `social-media`, `marketing`, and `ads`

It also shows you the edit-state model and asks you to confirm or change it.

## How answers are stored

Each saved line is tagged with where it came from: owner-confirmed, measured (with tool and date), official (with URL and access date), observed, inferred, hypothesis, or unknown. Permission boundaries are recorded separately. A blank stays blank. Nothing is invented: no brand color, font, license status, or consent status.

Never stored in memory: credentials, raw transcripts, reference videos.

## What you do yourself

The workspace, the handoff folder, and every download are approved with the setup command in your own terminal. The editor shows you the exact command and what it names. It never runs setup. See `hyperframes-setup.md`.

## Templates

`templates/editor-profile.md` and `templates/brand-and-visual-identity.md`. The brand template uses the same section names as the `social-media` profile's, so one file can serve both.
