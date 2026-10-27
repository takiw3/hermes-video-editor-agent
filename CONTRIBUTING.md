# Contributing

## Before you open a pull request

```bash
python3 -m pip install pyyaml
python3 scripts/validate.py --history
python3 scripts/hyperframes_vendor.py verify
python3 scripts/check_upstream_contract.py
python3 scripts/run_evals.py
python3 tests/run.py tests.test_tools
python3 tests/run.py tests.test_gates
```

With a Hermes checkout available:

```bash
HERMES_SRC=/path/to/hermes-agent HERMES_PYTHON=/path/to/venv/python python3 tests/test_install.py
```

Render tests need the pinned toolchain and a headless Chrome already on your machine. The tests never download one:

```bash
VE_TEST_TOOLCHAIN=1 VE_TEST_USE_HERMES=1 \
VE_TEST_BROWSER=/path/to/chrome-headless-shell \
python3 tests/run.py tests.test_renders --json docs/test-results/renders.json
python3 scripts/update_test_status.py
```

## Rules

- **Synthetic fixtures only.** Test media is generated with FFmpeg. No real people, no real footage, no real reference videos, no real figures. A reference figure in an example is labeled synthetic.
- **No claim without a test.** An editing operation is marked `rendered and verified` only when a recorded render passed a ground-truth check. The validation script ties each such row to a recorded result.
- **No number without a source.** A platform spec carries its official URL and access date in `platform-facts.yaml`. A render figure comes from `docs/test-results/`. Run `scripts/update_test_status.py` and never type one by hand.
- **No promise.** Nothing in a skill, template, example, or doc says a style will produce a result, or why a video performed.
- **Never call an unrun test passed.** A skipped test is `not run`.
- **Do not hand-edit `skills/hyperframes-video/`.** It is generated from `vendor/upstream/hyperframes/` by `scripts/hyperframes_vendor.py`. Change the patch rules and regenerate. See `docs/updating-vendored-code.md`.
- **Keep `distribution_owned` narrow.** Never own the whole `skills/` directory.
- **No credentials, footage, renders, transcripts, studies, or blueprints in the repository.** The validation script checks the tree and the Git history.
- **Pin CI actions to a full commit SHA.**
- **Runtime instruction files name only composition attributes the pinned release documents.**

## Skills

Every custom skill keeps the same sections: when to use, when not to use, inputs, missing information, source handling, procedure, output contract, checks before completion, permission boundaries, blocked and failure behavior, templates, and a synthetic example. The description starts with "Use".

## Effects

- A new effect is a folder under `skills/video-effects-core/effects-library/<family>/<effect_id>/` with an `effect.json` and only the templates it needs. Its script must be a pure function of time and parameters: no `Math.random`, no clock, no network.
- Build in this order: an effect HyperFrames already ships, then an original effect, then behavior studied clean-room. Never copy code, shaders, preset values, images, or names from another project, and never paste from another editor's source into an issue or pull request. A clean-room effect names its study entry in `reference_id`.
- Run the gate: `python3 scripts/verify_effects.py <effect_id>` (it needs Hermes, Node.js 22, FFmpeg, and a headless Chrome in `VE_TEST_BROWSER`). Then `python3 scripts/build_catalog.py` and commit the record, the stills, and the regenerated catalog together. Never edit a verification record by hand.
- `python3 scripts/copy_check.py check` must pass. It runs in CI.

## Versioning

Semantic versioning. Update `CHANGELOG.md` and the manifest version with any change to a distributed file.
