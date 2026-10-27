#!/usr/bin/env python3
"""Copy detection: prove no expression from a studied project entered this repository.

    # During a clean-room study, outside this repository:
    python3 scripts/copy_check.py fingerprint --source <studied-tree> --commit <sha> \\
        --out tests/fixtures/concat-fingerprints.json

    # In CI and before every commit:
    python3 scripts/copy_check.py check

`fingerprint` reads every shader and manifest file in the studied tree, turns
each into normalized token shingles, and stores only salted SHA-256 hashes of
those shingles, plus the SHA-256 of every image file. No text is stored, and
none is printed.

`check` computes the same shingles over every shader, script, style, manifest,
markup, and catalog file in this repository and fails when one file shares more
than the recorded threshold of shingles with the studied project, when an image
matches a studied image hash, or when the studied project's name appears
outside the files allowed to name it.

Standard library only. No network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FINGERPRINTS = REPO / "tests/fixtures/concat-fingerprints.json"
SHINGLE = 8
# Shingles a file may share by chance before it fails. Measured on this
# repository at the time the fingerprints were made: see docs/effects/clean-room-process.md.
DEFAULT_THRESHOLD = 3

STUDIED_SUFFIXES = {".wgsl", ".toml"}
CHECKED_SUFFIXES = {".wgsl", ".glsl", ".frag", ".vert", ".js", ".mjs", ".cjs", ".ts", ".css", ".html", ".htm",
                    ".svg", ".toml", ".yaml", ".yml", ".json", ".py"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".avif"}
SKIP_PARTS = {".git", "node_modules", "__pycache__", "vendor"}
# Files allowed to name the studied project. Everything else fails on the name.
NAME_ALLOWED = {
    "README.md", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md", "docs/effects/reference-study.md",
    "docs/effects/clean-room-process.md", "docs/concat-safety-review.md", "docs/hyperframes-integration.md",
    "docs/permissions-and-security.md", "docs/effects/verification.md", "scripts/copy_check.py",
    "scripts/validate.py", "tests/fixtures/concat-fingerprints.json", "tests/test_effects.py",
    "skills/video-effects-core/reference-editor-study/SKILL.md", "SOUL.md", "SECURITY.md",
    "scripts/run_evals.py", "CONTRIBUTING.md", "docs/evaluations.md", "docs/research-sources-and-platform-terms.md",
}
NAME_ALLOWED_PREFIXES = ("evals/",)
# Third-party HyperFrames text, verified byte-for-byte against its upstream tag
# by `hyperframes_vendor.py verify` (plus recorded patches). Upstream uses the
# word for FFmpeg's concat step; it is not a reference to the studied project.
# The shingle check still runs on these files.
NAME_SKIP_PREFIXES = ("vendor/upstream/hyperframes/", "skills/hyperframes-video/")
NAME_RE = re.compile(r"\bconcat\b(?!\w)", re.IGNORECASE)
# The word "concat" is also an ordinary programming term (FFmpeg's concat
# filter, Array.concat). Only a capitalized use or a link to the project counts.
PROJECT_NAME_RE = re.compile(r"\bConcat\b|jub0t/concat|concat-effects|concat --mcp|\bCONCAT\b")

TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|\S")


def strip_comments(text: str, suffix: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    text = re.sub(r"(?m)//[^\n]*", " ", text)
    if suffix in {".toml", ".yaml", ".yml", ".py"}:
        text = re.sub(r"(?m)#[^\n]*", " ", text)
    return text


# A shingle made only of punctuation, keywords, one- or two-letter names, and
# the literals 0, 1 and 2 is syntax every C-family language shares (a WGSL loop
# header reads exactly like a JavaScript one). It carries no expression, so it
# is not counted. Anything with a real identifier or constant in it is.
KEYWORDS = {"for", "var", "let", "const", "if", "else", "return", "while", "function", "fn", "true", "false",
            "new", "in", "of", "do", "break", "continue", "loop", "i32", "u32", "f32", "null", "this"}
TRIVIAL_NUMBERS = {str(n) for n in range(10)} | {"0.0", "1.0", "2.0", "0.5"}
# Position and direction words: an enum of them is vocabulary, not expression.
KEYWORDS_POSITION = {"left", "right", "up", "down", "top", "bottom", "center", "centre", "width", "height", "none", "auto"}


def trivial(shingle: tuple[str, ...]) -> bool:
    for tok in shingle:
        if not tok[0].isalnum() and tok[0] != "_":
            continue
        if tok in KEYWORDS or tok in TRIVIAL_NUMBERS or tok in KEYWORDS_POSITION:
            continue
        if tok[0].isalpha() and len(tok) <= 2:
            continue
        return False
    return True


def shingles(text: str, suffix: str) -> set[tuple[str, ...]]:
    tokens = [t.lower() for t in TOKEN_RE.findall(strip_comments(text, suffix))]
    every = {tuple(tokens[i:i + SHINGLE]) for i in range(max(0, len(tokens) - SHINGLE + 1))}
    return {s for s in every if not trivial(s)}


def digest(salt: str, shingle: tuple[str, ...]) -> str:
    return hashlib.sha256((salt + "\x1f" + "\x1f".join(shingle)).encode("utf-8")).hexdigest()[:20]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cmd_fingerprint(args) -> int:
    source = Path(args.source).resolve()
    if REPO in source.parents or source == REPO:
        print("refusing: the studied tree must sit outside this repository")
        return 1
    salt = secrets.token_hex(16)
    hashes: set[str] = set()
    files = 0
    images: set[str] = set()
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            images.add(sha256_file(path))
        if suffix not in STUDIED_SUFFIXES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files += 1
        hashes.update(digest(salt, s) for s in shingles(text, suffix))
    payload = {
        "studied_project": "concat",
        "repository": args.repository,
        "commit": args.commit,
        "made_at": args.date,
        "algorithm": f"lowercased tokens after comment removal, {SHINGLE}-token shingles, sha256(salt, shingle)[:20]",
        "shingle_tokens": SHINGLE,
        "threshold_shared_shingles_per_file": DEFAULT_THRESHOLD,
        "files_fingerprinted": files,
        "salt": salt,
        "shingle_hashes": sorted(hashes),
        "image_sha256": sorted(images),
        "note": "Hashes only. No text from the studied project is stored here.",
    }
    Path(args.out).write_text(json.dumps(payload, indent=1) + "\n", encoding="utf-8")
    print(f"fingerprinted {files} files: {len(hashes)} shingle hashes, {len(images)} image hashes")
    return 0


def repo_files(root: Path) -> list[Path]:
    import subprocess
    try:
        out = subprocess.run(["git", "-C", str(root), "ls-files", "-co", "--exclude-standard", "-z"],
                             capture_output=True, check=True).stdout.decode()
        files = [root / p for p in out.split("\0") if p]
        if files:
            return [f for f in files if f.is_file()]
    except Exception:
        pass
    return [p for p in root.rglob("*") if p.is_file() and not (set(p.relative_to(root).parts) & SKIP_PARTS)]


def check(root: Path, fingerprint_path: Path, threshold: int | None = None) -> list[str]:
    data = json.loads(fingerprint_path.read_text(encoding="utf-8"))
    salt, known = data["salt"], set(data["shingle_hashes"])
    images = set(data.get("image_sha256", []))
    limit = data.get("threshold_shared_shingles_per_file", DEFAULT_THRESHOLD) if threshold is None else threshold
    problems = []
    fingerprint_resolved = fingerprint_path.resolve()
    for path in repo_files(root):
        rel = path.relative_to(root).as_posix()
        if set(Path(rel).parts) & SKIP_PARTS or path.resolve() == fingerprint_resolved:
            continue
        suffix = path.suffix.lower()
        if suffix in IMAGE_SUFFIXES and sha256_file(path) in images:
            problems.append(f"image matches a studied-project image: {rel}")
        if suffix in CHECKED_SUFFIXES and path.stat().st_size < 4_000_000:
            text = path.read_text(encoding="utf-8", errors="ignore")
            shared = {digest(salt, s) for s in shingles(text, suffix)} & known
            if len(shared) > limit:
                problems.append(f"{len(shared)} shingles shared with the studied project (limit {limit}): {rel}")
        if suffix in {".md", ".yaml", ".yml", ".json", ".html", ".js", ".mjs", ".css", ".py", ".txt"} \
                and rel not in NAME_ALLOWED and not rel.startswith(NAME_ALLOWED_PREFIXES + NAME_SKIP_PREFIXES):
            text = path.read_text(encoding="utf-8", errors="ignore")
            m = PROJECT_NAME_RE.search(text)
            if m:
                problems.append(f"studied project named outside the allowed files: {rel} ({m.group(0)!r})")
    return problems


def cmd_check(args) -> int:
    path = Path(args.fingerprints)
    if not path.is_file():
        print(f"FAIL  fingerprint file missing: {path}")
        return 1
    problems = check(REPO if not args.root else Path(args.root).resolve(), path.resolve() if args.root else path)
    for p in problems:
        print(f"  FAIL  {p}")
    data = json.loads(path.read_text(encoding="utf-8"))
    print(f"copy check: {len(data['shingle_hashes'])} fingerprints from {data['files_fingerprinted']} studied files "
          f"at {data['commit'][:12]}, {len(problems)} problems")
    return 1 if problems else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("fingerprint")
    p.add_argument("--source", required=True)
    p.add_argument("--commit", required=True)
    p.add_argument("--repository", default="https://github.com/jub0t/concat")
    p.add_argument("--date", required=True)
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_fingerprint)
    p = sub.add_parser("check")
    p.add_argument("--fingerprints", default=str(FINGERPRINTS))
    p.add_argument("--root", default="")
    p.set_defaults(fn=cmd_check)
    args = parser.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
