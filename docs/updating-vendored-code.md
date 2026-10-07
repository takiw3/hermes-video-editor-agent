# Updating the vendored HyperFrames code

HyperFrames ships several releases a week. This profile pins one. An update is a reviewed pull request made by a person. CI may report that upstream moved. It never merges, pushes, or replaces vendored code.

## Steps

1. Pick the new stable release. Record its tag, its commit, its publish date, and the matching npm version and integrity hash.
2. Check out that tag locally, with Git LFS smudging off:

   ```bash
   GIT_LFS_SKIP_SMUDGE=1 git clone --depth 1 --branch <tag> https://github.com/heygen-com/hyperframes.git
   ```

3. Edit `scripts/hf_vendor_config.py`: the tag, commit, dates, npm version, and integrity. Review the include and exclude lists against the new release.
4. Regenerate the toolchain lockfile in a scratch folder with `npm install --package-lock-only --ignore-scripts`, and copy `package.json` and `package-lock.json` into `skills/integrations/editor-hyperframes/toolchain/`.
5. Import, derive, and lock:

   ```bash
   python3 scripts/hyperframes_vendor.py import --upstream <checkout>
   python3 scripts/hyperframes_vendor.py derive
   python3 scripts/hyperframes_vendor.py lock
   python3 scripts/hyperframes_vendor.py verify
   ```

   `derive` fails loudly when a patch no longer matches upstream text. Fix the patch rule. Never hand-edit a derived file: `verify` rebuilds the derivative and requires a byte-identical match.
6. Update `tests/fixtures/` with a new baseline and run `python3 scripts/check_upstream_contract.py`.

## What the pull request must show

1. The upstream diff between the old and new tags for the vendored paths.
2. The local patch changes: the diff of `scripts/hyperframes_vendor.py` and of `MODIFICATIONS.md`.
3. Skill-load tests rerun in an installed profile: `tests/test_install.py` against each supported Hermes release.
4. Cross-link and name-collision checks: part of `hyperframes_vendor.py verify` and `tests/test_install.py`.
5. Self-update and network-reach tests: `tests/test_gates.py`.
6. Footage-recipe tests, because composition attributes can change between releases: `tests/test_renders.py`.
7. The short-form and long-form render tests at the new pin, with new measurements.
8. Security and secret scans: `python3 scripts/validate.py --history`.
9. Updated checksums and the asset license inventory. A new binary asset with no license record fails the build.
10. `THIRD_PARTY_NOTICES.md` updated when licenses, counts, or withheld files changed.
11. `CHANGELOG.md` updated, with a new profile version.

## Rules

- Do not pin `main`, and do not ship an unpinned command anywhere in a runtime file.
- If upstream adds a `NOTICE` file, reproduce it. `verify` fails when one appears.
- If a new asset has no identifiable license, withhold it, record the removal, and test that the workflow still works or is reported as limited.
- Re-read every restated fact in `skills/integrations/editor-hyperframes/references/upstream-facts.md` at the new tag.
- Re-evaluate the internal upstream skill. Upstream may change or remove it without notice.
