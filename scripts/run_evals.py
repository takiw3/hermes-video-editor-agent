#!/usr/bin/env python3
"""Validate the behavior evaluation fixtures, and report model-backed status.

    python3 scripts/run_evals.py            # fixture validation (CI)
    python3 scripts/run_evals.py --list     # print every scenario

Fixture validation checks that every required scenario exists, is well formed,
is synthetic, and points at real skills. It does not run a model.

A model-backed run needs runtime credentials for a Hermes profile. This
repository ships none and CI has none, so that run is reported `not run`.
It is never reported as passed. docs/evaluations.md explains how to run the
fixtures by hand against an installed profile.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
EVALS = REPO / "evals"
FIELDS = ["id", "name", "category", "skills", "scenario", "input", "context", "must_include",
          "must_not_include", "pass_criteria", "zero_tolerance", "synthetic"]

REQUIRED = """first-run-onboarding paused-and-resumed-onboarding complete-social-media-brief-bypasses-onboarding
edit-with-no-outlier-study edit-with-stale-blueprint owner-waives-study-for-one-edit
owner-asks-to-skip-study-permanently outlier-study-one-account top-outlier-is-boosted-post
outlier-defined-as-million-views explain-why-reference-went-viral promise-similar-results guarantee-views
style-feature-in-contrast-set outlier-style-conflicts-with-brand social-media-instructs-unapproved-style
recreate-video-shot-for-shot reuse-reference-music reuse-reference-graphic-or-caption-wording
place-reference-clip-on-timeline download-video-from-platform scrape-logged-in-page
reference-link-not-accessible metadata-only-asked-for-caption-findings missing-brand-identity-before-edit
missing-script hook-footage-does-not-deliver script-too-long-for-duration cut-sentence-to-change-meaning
add-text-speaker-did-not-say add-unapproved-claim-on-screen remove-disclosure
transcript-uncertain-name-or-number footage-private-document-visible footage-with-minor
person-no-consent-record asset-no-license-record trending-commercial-song voice-clone-request
edit-before-toolchain-verified skip-draft-render edit-source-file-in-place delete-source-footage
write-outside-workspace cloud-render-request upload-footage-to-provider fetch-registry-item-without-approval
update-hyperframes-mid-edit workflow-not-bundled operation-not-supported long-form-beyond-tested-duration
render-exits-zero-silent-audio render-exits-zero-broken-captions render-failure-memory-pressure
call-draft-final call-rendered-file-approved call-file-posted revision-contradicts-paper-edit
fourth-revision-round conflicting-notes-owner-and-social request-to-post request-to-write-script
request-to-pick-topic request-to-write-caption-and-hashtags request-for-performance-analysis
measured-results-three-video-sample measured-results-contradict-blueprint injection-in-transcript
injection-in-video-title injection-in-reference-captions injection-in-registry-item
injection-in-kanban-comment ads-cutdown-unknown-rights handoff-would-place-footage-in-kanban
structured-kanban-completion structured-review-request structured-approval-request
kanban-block-one-missing-fact sensitive-executive-escalation copyright-claim-on-past-edit
user-correction-conflicts-with-memory weekly-edit-review""".split()
# Effects library scenarios (1.1.0).
REQUIRED += """list-verified-effects effect-count-honesty request-unverified-effect parameter-outside-range
apply-before-plan-approved effect-approver-is-delegate flash-check-fails owner-insists-on-strobe
flash-warn-needs-human invented-flash-threshold certify-epilepsy-safe hdr-source-with-effects green-screen-uneven
background-removal-model-request two-camera-moves-one-layer shader-and-original-transition-same-scene
stack-over-budget save-recipe recipe-with-retired-effect owner-local-effect edit-verification-record-by-hand
use-concat-code build-or-run-studied-editor connect-to-other-editor-mcp studied-name-in-effect
reference-video-look-analysis copy-reference-lut match-look-frame-for-frame injection-in-effect-description
injection-in-recipe-notes injection-in-lower-third-text registry-overlay-request network-in-effect random-in-effect
preview-before-apply remove-effect animate-parameter text-effect-on-wrong-element placeholder-text-left-in
face-distorting-effect-on-person pitch-shift-disguise audio-effect-silent-element audio-counted-as-visual
limited-release-wording contrast-fails-over-effect effect-on-timed-video-element effect-window-outside-composition
social-media-requests-effects result-fields-complete update-keeps-local-effects retired-skill-question
hyperframes-update-mid-edit-effects png-sequence-with-shader glitch-on-brand-video effect-promise-engagement
key-blue-wardrobe copy-check-question flash-check-on-real-render fourth-effect-revision""".split()
# Featured set (1.2.0).
REQUIRED += ["prefer-featured-effects"]

# Scenarios where a single wrong behavior fails the release.
ZERO_TOLERANCE_REQUIRED = {
    # fabricated figures, thresholds, causes, and promised results
    "outlier-defined-as-million-views", "explain-why-reference-went-viral", "promise-similar-results", "guarantee-views",
    "reference-link-not-accessible", "metadata-only-asked-for-caption-findings", "measured-results-three-video-sample",
    # copied expression, reference assets, downloads
    "recreate-video-shot-for-shot", "reuse-reference-music", "reuse-reference-graphic-or-caption-wording",
    "place-reference-clip-on-timeline", "download-video-from-platform", "scrape-logged-in-page",
    # meaning, on-screen words, disclosure
    "cut-sentence-to-change-meaning", "add-text-speaker-did-not-say", "add-unapproved-claim-on-screen", "remove-disclosure",
    # source footage, rights, consent, likeness
    "edit-source-file-in-place", "delete-source-footage", "asset-no-license-record", "person-no-consent-record",
    "footage-with-minor", "voice-clone-request", "trending-commercial-song",
    # false status and unapproved external action
    "call-draft-final", "call-rendered-file-approved", "call-file-posted", "render-exits-zero-silent-audio",
    "render-exits-zero-broken-captions", "cloud-render-request", "upload-footage-to-provider",
    "fetch-registry-item-without-approval", "request-to-post", "social-media-instructs-unapproved-style",
    "handoff-would-place-footage-in-kanban",
    # effects: verified-only, honest counts, photosensitivity, clean room, injection through effect data
    "effect-count-honesty", "request-unverified-effect", "apply-before-plan-approved", "flash-check-fails",
    "owner-insists-on-strobe", "invented-flash-threshold", "certify-epilepsy-safe",
    "background-removal-model-request", "edit-verification-record-by-hand", "use-concat-code",
    "build-or-run-studied-editor", "connect-to-other-editor-mcp", "match-look-frame-for-frame",
    "injection-in-effect-description", "injection-in-recipe-notes", "injection-in-lower-third-text",
    "registry-overlay-request", "placeholder-text-left-in", "pitch-shift-disguise", "audio-counted-as-visual",
    "limited-release-wording", "hyperframes-update-mid-edit-effects", "effect-promise-engagement",
    "copy-check-question", "flash-check-on-real-render",
}
COMMUNITY_MARKERS = ("skool.com", "agentic ai academy", "$97")


def skill_names() -> set[str]:
    names = set()
    for skill_md in (REPO / "skills").rglob("SKILL.md"):
        front = skill_md.read_text(encoding="utf-8").split("\n---\n", 1)[0][4:]
        names.add(yaml.safe_load(front)["name"])
    return names


def main() -> int:
    errors: list[str] = []
    docs = {}
    for path in sorted(EVALS.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"{path.name}: invalid YAML: {exc}")
            continue
        docs[doc.get("name")] = (path, doc)
        missing = [f for f in FIELDS if f not in doc]
        if missing:
            errors.append(f"{path.name}: missing fields {missing}")
            continue
        if path.stem != f"{doc['id']}-{doc['name']}":
            errors.append(f"{path.name}: file name does not match id and name")
        if doc["synthetic"] is not True:
            errors.append(f"{path.name}: fixtures must be synthetic")
        for field in ("scenario", "input", "pass_criteria"):
            if not str(doc[field]).strip():
                errors.append(f"{path.name}: empty {field}")
        if not doc["must_include"] or not doc["must_not_include"]:
            errors.append(f"{path.name}: must_include and must_not_include cannot be empty")
        blob = path.read_text(encoding="utf-8").lower()
        if any(m in blob for m in COMMUNITY_MARKERS):
            errors.append(f"{path.name}: community promotion in a fixture")

    known = skill_names()
    for name, (path, doc) in docs.items():
        for skill in doc.get("skills", []):
            if skill not in known:
                errors.append(f"{path.name}: unknown skill {skill}")
    for name in REQUIRED:
        if name not in docs:
            errors.append(f"required scenario missing: {name}")
    for name in ZERO_TOLERANCE_REQUIRED:
        if name in docs and docs[name][1].get("zero_tolerance") is not True:
            errors.append(f"{name}: must be zero tolerance")
    ids = [d["id"] for _, d in docs.values()]
    if len(ids) != len(set(ids)):
        errors.append("duplicate eval ids")

    if "--list" in sys.argv:
        for name, (path, doc) in docs.items():
            print(f"{doc['id']}  {'ZT ' if doc['zero_tolerance'] else '   '} {doc['category']:<11} {name}")

    for e in errors:
        print(f"  FAIL  {e}")
    zt = sum(1 for _, d in docs.values() if d.get("zero_tolerance"))
    print(f"eval fixtures: {len(docs)} scenarios, {zt} zero tolerance, {len(errors)} problems")
    print("model-backed evaluation: not run (no runtime model credentials in this environment)")
    print("end-to-end Kanban evaluation: not run (needs temporary Executive, social-media and video-editor "
          "profiles, model access, and a dispatcher)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
