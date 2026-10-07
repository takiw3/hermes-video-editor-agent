# Security

## Reporting a vulnerability

Report privately through GitHub's private vulnerability reporting on this repository (Security, then Report a vulnerability). Do not open a public issue for a security problem.

Include what you found, how to reproduce it, and what it lets an attacker or a misbehaving agent do. Do not include real credentials, real footage, or anyone's private data in a report.

## What counts

- A way for the agent to run HyperFrames without the pinned launcher that the deny rules do not block as a plain command.
- A way to reach a cloud render, publish, upload, sign-in, registry fetch, or provider call through the launcher.
- A way to write outside the approved workspace through the launcher or the measurement tools.
- A way to get reference material into a render through the launcher.
- A way to render a final with no style decision through the launcher.
- A way for installation or update to download, execute, or overwrite user-owned state.
- A secret, footage, or user data committed to the repository or included in the installed payload.
- A license or attribution error in the vendored material.

## Known limits, not vulnerabilities

These are documented in `docs/permissions-and-security.md`:

- The launcher is not an operating-system sandbox. A process that never calls it is not stopped by it.
- Deny rules match command text. A command hidden inside a script file is not matched.
- A profile is not a tenant boundary.
- The style-decision file proves a choice was recorded, not who made it.

## Supported versions

The latest released version of this profile, on the Hermes releases named in the README.

## Upstream

Report a vulnerability in HyperFrames to HeyGen through the upstream repository, and in Hermes to Nous Research through theirs.
