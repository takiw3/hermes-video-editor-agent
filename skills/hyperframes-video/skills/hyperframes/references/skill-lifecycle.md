> **Modified file. Derived from HeyGen HyperFrames v0.8.183 (commit 7e28176), licensed under Apache-2.0, Copyright 2026 HeyGen, Inc. Changed by TakiGPT AI Inc. for the Hermes video-editor profile. Rules applied: stub-unavailable. See skills/hyperframes-video/MODIFICATIONS.md.**

# Skill installation and freshness

The HyperFrames skills in this Hermes profile are bundled with the profile, pinned to one upstream release, and release-managed. They are updated only through a reviewed, versioned change to the profile repository, followed by `hermes profile update`.

- Never run a skill update, check, or install command, in any form.
- Never refresh skills during `init`. The launcher sets `HYPERFRAMES_SKIP_SKILLS=1` on every call, which is the opt-out the pinned CLI honors.
- A workflow that is not bundled is reported as not bundled. It is never downloaded.
- If a bundled skill looks stale or broken, stop and report it to the owner. Do not continue from a remembered workflow contract.
