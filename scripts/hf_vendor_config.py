"""Single source of truth for the HyperFrames pin, vendoring scope, and patches.

Everything in vendor/hyperframes.lock.yaml that is not a computed hash comes
from here. Change a value here, rerun `scripts/hyperframes_vendor.py`, and
review the resulting diff in a pull request. See docs/updating-vendored-code.md.
"""

UPSTREAM_REPOSITORY = "https://github.com/heygen-com/hyperframes"
UPSTREAM_TAG = "v0.8.138"
UPSTREAM_COMMIT = "0ca28db4f8671a2e2262594e03c566222d695920"
UPSTREAM_PATHS = ["skills/", ".claude/skills/captions-overlay/"]
UPSTREAM_PUBLISHED_AT = "2026-10-06T18:19:06Z"
RETRIEVED_AT = "2026-10-06"

NPM_PACKAGE = "hyperframes"
NPM_VERSION = "0.8.138"
NPM_INTEGRITY = (
    "sha512-1xeNRkGeCobo9wbNht4BH1Y3FdSswHuo5R8UgCB8ea5eGqdRyQ7GkK8B6MGAbrhu"
    "9o7+jV7qUa2kRxjQ9KSGmg=="
)
NODE_MINIMUM_MAJOR = 22

UPSTREAM_LICENSE = "Apache-2.0"
UPSTREAM_COPYRIGHT = "Copyright 2026 HeyGen, Inc."

# Where the exact upstream copy and the derived runtime copy live in this repo.
VENDOR_ROOT = "vendor/upstream/hyperframes"
DERIVED_ROOT = "skills/hyperframes-video"
INSTALLED_PATH = "skills/hyperframes-video"

# The launcher every derived instruction points at. `$HERMES_HOME` is bridged
# into terminal subprocesses by Hermes (tools/environments/local.py), so this
# string resolves inside an installed profile without any substitution.
LAUNCHER = 'python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py"'

SKILLS_INCLUDED = [
    "hyperframes",
    "hyperframes-core",
    "hyperframes-animation",
    "hyperframes-keyframes",
    "hyperframes-creative",
    "hyperframes-cli",
    "hyperframes-audio",
    "hyperframes-registry",
    "hyperframes-studio",
    "media-use",
    "talking-head-recut",
    "embedded-captions",
    "motion-graphics",
    "faceless-explainer",
    "general-video",
]

SKILLS_EXCLUDED = {
    "pr-to-video": "Not editing work. Its input is a GitHub pull request.",
    "remotion-to-hyperframes": "Not editing work. It ports another framework's project.",
    "slideshow": "Not editing work in v1.",
    "figma": "Not editing work in v1; needs a Figma token and network access.",
    "product-launch-video": (
        "Failed the evidence test. Its input is a live website capture, which "
        "is a network read the default mode does not perform, so no render of "
        "it could be tested in the default mode."
    ),
    "music-to-video": (
        "Failed the evidence test. It ships 66 PNG texture masks and one font "
        "with no license record in the skill or in upstream CREDITS.md at the "
        "pinned tag. An asset with no identifiable license does not ship, and "
        "removing them guts the templates that use them."
    ),
}

# Repo-internal upstream skills (`.claude/skills/`, `metadata.internal: true`).
# Upstream calls these repo-native and says they are not part of the
# distributed set, so they may change or disappear without notice.
INTERNAL_ROOT = ".claude/skills"
INTERNAL_INCLUDED = ["captions-overlay"]
INTERNAL_EXCLUDED = {
    "motion-doctrine": (
        "Fails standalone loading. It routes to `oversized-cursor`, which is "
        "out of scope, and its seam-gate script starts a detached preview "
        "server through an unpinned `npx --yes hyperframes` and prefers a "
        "repo-local CLI build, which is acting on the upstream repository."
    ),
    "cut-the-curve": (
        "Fails standalone loading. It tells the agent to read "
        "`motion-doctrine` first and defers to `seam-craft` for its token "
        "table; neither is bundled."
    ),
    "seam-craft": (
        "Fails standalone loading. It is render doctrine for the "
        "`product-launch-video` injector, which is not bundled."
    ),
    "changelog-video": "Out of scope by instruction. It runs only against the upstream repository.",
    "oversized-cursor": "Out of scope by instruction.",
}

# Registry and themes. Neither is vendored. Catalog search is local to the
# pinned CLI; `add` fetches from the network and needs owner approval.
REGISTRY_ITEMS_INCLUDED: list = []
THEMES_INCLUDED: list = []

ROOT_FILES = ["LICENSE", "CREDITS.md", "plugin.json", "skills-manifest.json"]

# Files that exist upstream at the pinned tag and are deliberately not copied
# into this repository at all (neither the audit copy nor the derivative).
# The lock file records each one's upstream sha256 so the audit is complete.
WITHHELD = {
    "skills/talking-head-recut/assets/fonts/Virgil.woff2": (
        "License conflict. The font's embedded metadata reads 'Copyright (c) "
        "2011 by Your Own Font Foundry. All rights reserved. Freeware for "
        "personal use! For commercial license ...', while github.com/"
        "excalidraw/virgil publishes Virgil under OFL-1.1. With two "
        "incompatible statements and no way to tell which governs this file, "
        "it is treated as having no identifiable license and is not shipped."
    ),
    "skills/talking-head-recut/assets/vendor/gsap.min.js": (
        "GSAP 3.15.0 under the GSAP Standard License (not an OSI license). "
        "The license grants a right to 'use, reproduce, display, and "
        "implement' GSAP for Permitted Uses and does not expressly grant "
        "redistribution of the library file inside another project. Because "
        "redistribution could not be confirmed as permitted, the file is not "
        "shipped. The derived workflow loads the same GSAP version from the "
        "jsDelivr CDN at render time, as every other bundled workflow does."
    ),
    "skills/media-use/.gitignore": (
        "Nested ignore file. It would hide files from this repository's Git "
        "index and so from a git-URL profile install."
    ),
    "skills/embedded-captions/.gitignore": (
        "Nested ignore file. It ignores *.mp4, *.log, transcript.json, "
        "plan.json and similar inside the skill, which would hide files from "
        "this repository's Git index and so from a git-URL profile install."
    ),
    "skills/python-encoding.test.mjs": (
        "Loose upstream test file at the skills root. Not part of any skill."
    ),
}

# Derived files whose whole body is replaced by a short profile-specific stub.
# The file is kept so cross-skill links to it still resolve.
STUBBED = {
    "skills/hyperframes-cli/references/cloud.md": (
        "HeyGen-hosted cloud rendering and `auth` sign-in"
    ),
    "skills/hyperframes-cli/references/lambda.md": "AWS Lambda rendering",
    "skills/hyperframes-cli/references/cloudrun.md": "Google Cloud Run rendering",
    "skills/hyperframes/references/skill-lifecycle.md": (
        "Skill installation, update, and freshness commands"
    ),
    "skills/hyperframes/references/plugin-installation.md": (
        "Plugin-manager installation and update"
    ),
}

# Subcommands that reach an external service, mutate an account, update the
# toolchain, or send data off the machine. Every command-form mention in the
# derived docs is rewritten to an inert marker, the launcher refuses them, and
# config.yaml denies them at the Hermes approval floor.
PROHIBITED_SUBCOMMANDS = [
    "skills",
    "upgrade",
    "publish",
    "cloud",
    "lambda",
    "cloudrun",
    "auth",
    "feedback",
    "events",
    "telemetry",
    "open",
    "catch-up",
    "figma",
]

# Per-asset-group license records. Every non-text file in the derivative must
# match exactly one group or the build fails.
ASSET_LICENSES = [
    {
        "id": "sfx-pixabay",
        "glob": "skills/media-use/audio/assets/sfx/*.mp3",
        "count": 19,
        "license": "Pixabay Content License",
        "license_url": "https://pixabay.com/service/license-summary/",
        "source": "Pixabay sound effects, as recorded by upstream",
        "proof": "skills/media-use/audio/assets/sfx/CREDITS.md (upstream file)",
        "restrictions": (
            "No attribution required. May not be sold or redistributed on a "
            "standalone basis. Upstream does not record a per-file Pixabay "
            "URL, so the original uploader of each file is not identified."
        ),
    },
    {
        "id": "fonts-code-editorial",
        "glob": "skills/hyperframes-creative/frame-presets/code-editorial/fonts/*.woff2",
        "count": 6,
        "license": "OFL-1.1",
        "license_url": "https://openfontlicense.org",
        "source": "Inter, EB Garamond, JetBrains Mono",
        "proof": (
            "OFL-inter.txt, OFL-eb-garamond.txt, OFL-jetbrains-mono.txt beside "
            "the fonts (upstream files)"
        ),
        "restrictions": "May not be sold by themselves. Keep the license text with copies.",
    },
    {
        "id": "fonts-captions-standard-ofl",
        "glob": "skills/embedded-captions/modes/standard/fonts/files/*.woff2",
        "exclude": [
            "permanent-marker-latin-400-normal.woff2",
            "special-elite-latin-400-normal.woff2",
        ],
        "count": 42,
        "license": "OFL-1.1",
        "license_url": "https://openfontlicense.org",
        "source": (
            "Latin subsets of 22 Google Fonts families, taken by upstream from "
            "@fontsource packages"
        ),
        "proof": (
            "`npm view @fontsource/<family> license` for each family returned "
            "OFL-1.1 on 2026-10-06, and each file's embedded name table carries "
            "an OFL license URL (Monoton's name table has a copyright line but "
            "no license URL; its license rests on the fontsource record). "
            "Per-file copyright lines are in licenses/FONT-COPYRIGHTS.md."
        ),
        "restrictions": "May not be sold by themselves. Keep the license text with copies.",
    },
    {
        "id": "fonts-captions-standard-apache",
        "glob": "skills/embedded-captions/modes/standard/fonts/files/*.woff2",
        "only": [
            "permanent-marker-latin-400-normal.woff2",
            "special-elite-latin-400-normal.woff2",
        ],
        "count": 2,
        "license": "Apache-2.0",
        "license_url": "https://www.apache.org/licenses/LICENSE-2.0",
        "source": "Permanent Marker and Special Elite, via @fontsource",
        "proof": (
            "`npm view @fontsource/permanent-marker license` and "
            "`npm view @fontsource/special-elite license` returned Apache-2.0 "
            "on 2026-10-06."
        ),
        "restrictions": "Keep the license text and notices with copies.",
    },
    {
        "id": "fonts-captions-inlined",
        "glob": "skills/embedded-captions/modes/standard/fonts/fonts.css",
        "count": 1,
        "license": "OFL-1.1 AND Apache-2.0",
        "license_url": "https://openfontlicense.org",
        "source": (
            "Generated by upstream build-fonts-css.cjs: the 44 files above, "
            "base64-inlined"
        ),
        "proof": "Same records as the two font groups above.",
        "restrictions": "Same as the fonts it embeds.",
    },
    {
        "id": "fonts-talking-head",
        "glob": "skills/talking-head-recut/assets/fonts/*.woff2",
        "count": 5,
        "license": "OFL-1.1",
        "license_url": "https://openfontlicense.org",
        "source": "Caveat, Inter, LXGW WenKai TC (Latin subsets)",
        "proof": (
            "Each file's embedded name table carries an OFL license URL, and "
            "`npm view @fontsource/{caveat,inter,lxgw-wenkai-tc} license` "
            "returned OFL-1.1 on 2026-10-06. Virgil.woff2 is withheld; see "
            "removed_files."
        ),
        "restrictions": "May not be sold by themselves. Keep the license text with copies.",
    },
    {
        "id": "stroke-fonts-hershey",
        "glob": "skills/embedded-captions/assets/strokefonts/*.svg",
        "count": 2,
        "license": "Hershey Fonts license (permissive, attribution required)",
        "license_url": "https://emergent.unpythonic.net/software/hershey",
        "source": "Hershey Fonts in SVG, by way of Marty McGuire's conversion",
        "proof": "License text embedded in the metadata block of each SVG file.",
        "restrictions": (
            "Must acknowledge the Hershey Fonts' origin (Dr. A. V. Hershey, "
            "U.S. National Bureau of Standards) and may not be redistributed "
            "in the original NTIS format."
        ),
    },
]

# Binary or media extensions that must be covered by ASSET_LICENSES.
ASSET_EXTENSIONS = {
    ".woff2", ".woff", ".ttf", ".otf", ".mp3", ".wav", ".ogg", ".m4a", ".aac",
    ".flac", ".mp4", ".mov", ".webm", ".png", ".jpg", ".jpeg", ".webp", ".gif",
    ".svg", ".onnx", ".bin", ".cube", ".pdf", ".zip",
}
ASSET_EXTRA_FILES = {"skills/embedded-captions/modes/standard/fonts/fonts.css"}
