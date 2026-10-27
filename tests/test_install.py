#!/usr/bin/env python3
"""Profile installation, payload, isolation, update, deny-rule, and Kanban tests.

Runs in a throwaway HOME and HERMES_HOME. Never touches a real profile and
never uses --force. Steps that need the Hermes CLI report `not run` when it
is unavailable; they are never counted as passed.

    HERMES_SRC=/path/to/hermes-agent HERMES_PYTHON=/path/to/venv/python \\
        python3 tests/test_install.py [--json results.json]
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sandbox import (PROFILE, REPO, Results, Sandbox, expected_payload, hermes_command,  # noqa: E402
                     hermes_python, hermes_version, install_profile, manifest, no_network_wrapper,
                     run_hermes, sha256_file, tree)

GITHUB = "github.com/takiw3/hermes-video-editor-agent"
EXPECTED_OWNED = [
    "distribution.yaml", "profile.yaml", "SOUL.md", "config.yaml", "LICENSE",
    "THIRD_PARTY_NOTICES.md", "templates", "skills/video-editor-core",
    "skills/integrations/editor-hyperframes", "skills/hyperframes-video", "skills/video-effects-core",
]
REPO_ONLY = ["README.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md", "docs", "tests",
             "evals", "examples", "scripts", "vendor", ".github", ".gitignore", ".git"]
CORE_SKILLS = 25
VENDORED_SKILLS = 16          # 15 published plus the internal captions-overlay
EFFECT_SKILLS = 17            # skills/video-effects-core; effects-library/ beside them is data, not a skill
HF = "skills/integrations/editor-hyperframes/scripts/hf.py"
VERSION = "1.1.0"  # the release under test; the manifest must say the same

# Command forms the profile's deny rules must block at the Hermes approval
# floor, and sanctioned forms they must leave alone.
L = 'python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/hf.py"'
MUST_DENY = [
    "npx hyperframes render", "npx --yes hyperframes@latest init demo", "npx hyperframes skills update general-video",
    "bunx hyperframes render", "npm install -g hyperframes", "npm i hyperframes", "hyperframes render --output x.mp4",
    "cd projects/a/v1 && hyperframes publish",
    "node local/video-editor/video-engine/toolchain-0.8.183/node_modules/hyperframes/bin/hyperframes.mjs render",
    "node $HERMES_HOME/skills/hyperframes-video/skills/hyperframes/scripts/plugin-cli.mjs cloud render",
    f"{L} setup --install-cli --yes", f"{L} setup --workspace /tmp/x", f"{L} setup --allow-host cdn.example.com",
    f"{L} setup --add-registry-item lower-third --project v1", f"{L} add lower-third",
    f"{L} publish", f"{L} cloud render", f"{L} lambda render", f"{L} auth login", f"{L} skills update",
    f"{L} upgrade", f"{L} feedback", f"{L} capture https://example.com", f"{L} media-use resolve", f"{L} tts hello",
    "npx skills add heygen-com/hyperframes", "heygen auth login --oauth", "npm run render", "npm run publish",
    "hermes -p video-editor skills install official/creative/hyperframes --yes",
    "yt-dlp https://example.com/watch?v=1", "youtube-dl https://example.com/v", "gallery-dl https://example.com/p",
    "instaloader someprofile", "streamlink https://example.com best",
    "rm ws/footage/take.mp4", "rm -rf /Users/x/ws/footage/", "mv ws/footage/take.mp4 /tmp/", "truncate -s 0 ws/footage/take.mp4",
    "ffmpeg -i in.mp4 > ws/footage/take.mp4", "cp ws/references/outlier.mp4 ws/projects/a/v1/assets/",
    "ln -s ../../references/outlier.mp4 assets/b.mp4", "cat local/video-editor/video-engine/engine.json",
    "echo '{}' > ws/.video-editor/footage-manifest.json", "echo $HEYGEN_API_KEY", "cat ~/.heygen/credentials",
]
MUST_ALLOW = [
    f"{L} status", f"{L} doctor --deep", f"{L} init v1", f"{L} lint", f"{L} check", f"{L} timeline --json",
    f"{L} render --stage draft --comparison hybrid", f"{L} render --stage final --output renders/publish-ready.mp4",
    f"{L} snapshot --at 1,2,3", f"{L} compare v1 v2 --at 1 --out compare.png", f"{L} footage-add footage/take.mp4",
    f"{L} footage-verify", f"{L} rights-check", f"{L} style-check", f"{L} references-check", f"{L} preview-stop",
    f"{L} handoff renders/a.mp4", f"{L} plan-workers", f"{L} limits", f"{L} media-treatment --capabilities --json",
    'python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" probe footage/take.mp4',
    'python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" cuts references/outlier.mp4',
    'python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" frames references/outlier.mp4',
    "ls footage/", "hermes kanban create \"Rough cut review\" --assignee social-media --body-file review.yaml",
]


def main() -> int:
    json_out = sys.argv[sys.argv.index("--json") + 1] if "--json" in sys.argv else None
    r = Results("installation tests")
    m = manifest()

    print("== 1. manifest ==")
    known = {"name", "version", "description", "hermes_requires", "author", "license",
             "env_requires", "distribution_owned"}
    r.check("manifest uses only fields the tested Hermes schema parses", set(m) <= known, str(set(m) - known))
    r.check("name is video-editor", m.get("name") == PROFILE)
    r.check(f"version is {VERSION}", str(m.get("version")) == VERSION)
    r.check("license is MIT", m.get("license") == "MIT")
    r.check("author is set", m.get("author") == "Taki Wong / TakiGPT AI Inc.")
    r.check("no environment variable is required", not m.get("env_requires"))
    r.check("distribution_owned is the exact narrow allowlist",
            m.get("distribution_owned") == EXPECTED_OWNED, str(m.get("distribution_owned")))
    r.check("the whole skills/ directory is never owned", "skills" not in m["distribution_owned"])
    r.check("no cron definitions ship", not (REPO / "cron").exists())
    r.check("no symlinks anywhere in the repository",
            not any(p.is_symlink() for p in REPO.rglob("*") if ".git" not in p.parts))

    if not hermes_command():
        for name in ("install", "profile info", "skills load", "deny rules", "alias", "update",
                     "network-denied install", "Kanban exchange"):
            r.notrun(name, "Hermes CLI not available (set HERMES_SRC or install hermes)")
        return r.finish(json_out)

    version = hermes_version()
    print(f"\nHermes under test: {version}")
    r.record(f"Hermes under test: {version}", "pass")

    print("\n== 2. local install ==")
    sb = Sandbox()
    proc = install_profile(sb)
    if not r.check("`hermes profile install <repo> --alias --yes` succeeds",
                   proc.returncode == 0 and sb.profile_dir.is_dir(), (proc.stdout + proc.stderr)[-400:]):
        return r.finish(json_out)
    P = sb.profile_dir

    print("\n== 3. profile info ==")
    info = run_hermes(sb, ["profile", "info", PROFILE]).stdout
    r.check("profile info reports the name", "video-editor" in info, info[:200])
    r.check(f"profile info reports version {VERSION}", VERSION in info)
    r.check("profile info reports the source", str(REPO) in info)
    r.check("profile info reports the Hermes requirement", m["hermes_requires"] in info)

    print("\n== 4. identity and routing description ==")
    import yaml
    prof = yaml.safe_load((P / "profile.yaml").read_text(encoding="utf-8"))
    r.check("profile.yaml carries a routing description", len(prof.get("description", "")) > 200)
    r.check("profile.yaml display name is Video Editor", prof.get("display_name") == "Video Editor")
    r.check("installed profile.yaml carries no backend-assigned role", "role" not in prof)
    r.check("SOUL.md installed and identical", sha256_file(P / "SOUL.md") == sha256_file(REPO / "SOUL.md"))
    listing = run_hermes(sb, ["profile", "list"]).stdout
    r.check("profile list shows the profile and its distribution", f"video-editor@{VERSION}" in listing, listing[-300:])

    print("\n== 5-7. skills load in the installed profile ==")
    if os.environ.get("HERMES_SRC"):
        code = (
            "import json\n"
            "from tools.skills_tool import skills_list, skill_view\n"
            "r = json.loads(skills_list())\n"
            "names = [s['name'] for s in r['skills']]\n"
            "bad = [n for n in names if not json.loads(skill_view(n)).get('success')]\n"
            "cats = {}\n"
            "for s in r['skills']: cats.setdefault(s.get('category'), []).append(s['name'])\n"
            "ref = json.loads(skill_view('hyperframes-core', 'references/creator-editing-recipes.md'))\n"
            "wrap = json.loads(skill_view('editor-hyperframes', 'references/capabilities.md'))\n"
            "print(json.dumps({'names': names, 'bad': bad, 'cats': cats, 'ref': ref.get('success'), 'wrap': wrap.get('success')}))\n"
        )
        out = hermes_python(sb, code)
        try:
            data = json.loads(out.stdout.strip().splitlines()[-1])
        except Exception:
            data = None
        if r.check("Hermes skill index builds for the profile", data is not None, out.stderr[-400:]):
            names = data["names"]
            r.check(f"{CORE_SKILLS} core skills are indexed",
                    len(data["cats"].get("video-editor-core", [])) == CORE_SKILLS,
                    str(len(data["cats"].get("video-editor-core", []))))
            r.check("the wrapper skill is indexed", "editor-hyperframes" in data["cats"].get("integrations", []))
            r.check(f"{VENDORED_SKILLS} vendored HyperFrames skills are indexed",
                    len(data["cats"].get("hyperframes-video", [])) == VENDORED_SKILLS,
                    str(len(data["cats"].get("hyperframes-video", []))))
            r.check(f"{EFFECT_SKILLS} effects skills are indexed",
                    len(data["cats"].get("video-effects-core", [])) == EFFECT_SKILLS,
                    str(len(data["cats"].get("video-effects-core", []))))
            r.check("the effects library is not indexed as a skill",
                    not any("effects-library" in n for n in names), str([n for n in names if "library" in n]))
            r.check("the internal upstream skill captions-overlay is indexed", "captions-overlay" in names)
            r.check("every skill loads through skill_view", not data["bad"], str(data["bad"]))
            r.check("a cross-skill reference file loads through skill_view", data["ref"] is True)
            r.check("the wrapper's capability reference loads through skill_view", data["wrap"] is True)
            r.check("no duplicate skill names", len(names) == len(set(names)))
            r.check("exactly one skill is named hyperframes", names.count("hyperframes") == 1)

        attempt = run_hermes(sb, ["-p", PROFILE, "skills", "install", "official/creative/hyperframes", "--yes"],
                             timeout=180)
        code2 = (
            "import json\n"
            "from tools.skills_tool import skills_list, skill_view\n"
            "names = [s['name'] for s in json.loads(skills_list())['skills']]\n"
            "v = json.loads(skill_view('hyperframes'))\n"
            "print(json.dumps({'count': names.count('hyperframes'), 'path': v.get('path'), "
            "'success': v.get('success'), 'error': v.get('error')}))\n"
        )
        after = hermes_python(sb, code2)
        try:
            a = json.loads(after.stdout.strip().splitlines()[-1])
        except Exception:
            a = {"count": None, "path": None, "success": None, "error": None}
        optional_present = (P / "skills" / "creative" / "hyperframes" / "SKILL.md").is_file()
        print(f"       observed: install exit {attempt.returncode}; optional skill files present: "
              f"{optional_present}; index entries named hyperframes: {a['count']}; "
              f"skill_view('hyperframes') success: {a['success']}")
        if optional_present:
            # Observed on Hermes 0.21.4 and 0.21.5: the install succeeds and loading
            # `hyperframes` by name then fails as ambiguous, so the vendored router is no
            # longer reachable by name. A change in this behavior fails here so the
            # integration gets re-audited.
            r.check("documented collision reproduced: with the optional skill installed, `hyperframes` no longer loads the vendored router",
                    a["success"] is False and "mbiguous" in (a["error"] or ""), str(a))
            import shutil
            shutil.rmtree(P / "skills" / "creative", ignore_errors=True)
            shutil.rmtree(P / "skills" / ".hub", ignore_errors=True)
            again = hermes_python(sb, code2)
            b = json.loads(again.stdout.strip().splitlines()[-1])
            r.check("removing the optional skill restores the vendored router",
                    b["success"] is True and b["path"] == "hyperframes-video/skills/hyperframes/SKILL.md", str(b))
        else:
            r.check("the optional skill could not be installed beside the vendored router", a["count"] == 1, str(a))

        # Its own HERMES_HOME: importing agent and model_tools writes state.db, which the
        # payload checks below would find in the profile.
        probe_home = sb.root / "import-probe"
        probe_home.mkdir(exist_ok=True)
        where = subprocess.run(
            [os.environ.get("HERMES_PYTHON") or sys.executable, "-c",
             "import json, sys, hermes_cli, tools, agent, model_tools\n"
             "print(json.dumps({'files': [m.__file__ for m in (hermes_cli, tools, agent, model_tools)],"
             " 'editable': [str(getattr(f, '__module__', '')) for f in sys.meta_path + sys.path_hooks"
             " if str(getattr(f, '__module__', '')).startswith('__editable__')]}))\n"],
            cwd=os.environ["HERMES_SRC"], env=sb.env(HERMES_HOME=str(probe_home)),
            capture_output=True, text=True, timeout=300)
        try:
            wd = json.loads(where.stdout.strip().splitlines()[-1])
        except Exception:
            wd = None
        src_root = str(Path(os.environ["HERMES_SRC"]).resolve())
        r.check("Hermes modules load only from the source under test",
                wd is not None and not wd["editable"] and all(str(Path(f).resolve()).startswith(src_root) for f in wd["files"]),
                str(wd)[:300] if wd else (where.stdout + where.stderr)[-300:])

        print("\n== deny rules at the Hermes approval floor ==")
        probe = ("import json, sys\n"
                 "from tools.approval_floors import _match_user_deny_rule as m\n"
                 "cmds = json.loads(sys.stdin.read())\n"
                 "print(json.dumps({c: m(c) for c in cmds}))\n")
        src = os.environ["HERMES_SRC"]
        py = os.environ.get("HERMES_PYTHON") or sys.executable
        res = subprocess.run([py, "-c", probe], cwd=src, env=sb.env(HERMES_HOME=str(P)),
                             input=json.dumps(MUST_DENY + MUST_ALLOW), capture_output=True, text=True)
        try:
            verdict = json.loads(res.stdout.strip().splitlines()[-1])
        except Exception:
            verdict = None
        if r.check("the profile's deny rules load in the tested Hermes release", verdict is not None, res.stderr[-300:]):
            leaked = [c for c in MUST_DENY if not verdict.get(c)]
            r.check(f"{len(MUST_DENY)} route-around, external, download, and footage-destroying command forms are denied",
                    not leaked, "; ".join(leaked[:4]))
            blocked = [c for c in MUST_ALLOW if verdict.get(c)]
            r.check(f"{len(MUST_ALLOW)} sanctioned launcher and tool commands are not denied", not blocked,
                    "; ".join(f"{c} <- {verdict[c]}" for c in blocked[:3]))
            # Recorded honestly: a command hidden inside a script file is not matched.
            r.check("observed limit: a deny rule matches the command text, so a script file that calls the CLI is not matched",
                    json.loads(subprocess.run([py, "-c", probe], cwd=src, env=sb.env(HERMES_HOME=str(P)),
                                              input=json.dumps(["bash ./run-it.sh"]), capture_output=True,
                                              text=True).stdout.strip().splitlines()[-1])["bash ./run-it.sh"] is None)
    else:
        r.notrun("skills load through Hermes", "HERMES_SRC not set; needs importable Hermes source")
        r.notrun("deny rules at the Hermes approval floor", "HERMES_SRC not set; needs importable Hermes source")

    print("\n== 8-12. installed payload ==")
    expected = expected_payload()
    installed = tree(P)
    missing = sorted(k for k in expected if k not in installed)
    r.check("every allowlisted file is installed", not missing, ", ".join(missing[:5]))
    changed = sorted(k for k in expected if k in installed and k != "distribution.yaml"
                     and expected[k] != installed[k])
    r.check("installed files are byte-identical to the repository", not changed, ", ".join(changed[:5]))
    owned_dirs = [d for d in EXPECTED_OWNED if (REPO / d).is_dir()]
    extra = sorted(k for k in installed
                   if any(k.startswith(d + "/") for d in owned_dirs) and k not in expected)
    r.check("no unexpected file inside owned paths", not extra, ", ".join(extra[:5]))
    stray_top = sorted(p.name for p in P.iterdir() if p.is_file()
                       and p.name not in {"distribution.yaml", "profile.yaml", "SOUL.md", "config.yaml",
                                          "LICENSE", "THIRD_PARTY_NOTICES.md"})
    r.check("no unexpected top-level file in the profile", not stray_top, ", ".join(stray_top))
    present = [name for name in REPO_ONLY if (P / name).exists()]
    r.check("repository-only files are not installed", not present, ", ".join(present))
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "skills/hyperframes-video/LICENSE",
                 "skills/hyperframes-video/CREDITS.md", "skills/hyperframes-video/MODIFICATIONS.md",
                 "skills/hyperframes-video/ASSET-LICENSES.md",
                 "skills/hyperframes-video/licenses/OFL-1.1.txt"):
        r.check(f"license notice installed: {name}", (P / name).is_file())
    lic = (P / "skills/hyperframes-video/LICENSE").read_text(encoding="utf-8")
    r.check("Apache-2.0 text and HeyGen copyright travel with the vendored skills",
            "Apache License" in lic and "Copyright 2026 HeyGen, Inc." in lic)
    forbidden = [k for k in installed if Path(k).name in {".env", "auth.json", "engine.json"}
                 or k.endswith((".db", ".pem", ".key", ".mp4", ".mov", ".webm", ".wav"))
                 or "node_modules" in Path(k).parts]
    r.check("no credentials, state, footage, reference material, renders, or node_modules installed",
            not forbidden, ", ".join(forbidden[:5]))
    r.check("no symlinks installed", not any(p.is_symlink() for p in P.rglob("*")))
    lfs = [k for k in installed if (P / k).stat().st_size < 400
           and (P / k).read_bytes().startswith(b"version https://git-lfs.github.com/spec/")]
    r.check("no Git LFS pointer files installed", not lfs, ", ".join(lfs[:3]))

    print("\n== 13. alias ==")
    alias = sb.home / ".local" / "bin" / PROFILE
    if r.check("alias wrapper created", alias.is_file(), str(alias)):
        body = alias.read_text(encoding="utf-8")
        r.check("alias wrapper targets `-p video-editor`", "-p video-editor" in body, body)

    print("\n== 14. README command ==")
    readme = (REPO / "README.md").read_text(encoding="utf-8") if (REPO / "README.md").is_file() else ""
    r.check("README primary command is the confirmation-enabled install with --alias",
            f"hermes profile install {GITHUB} --alias\n" in readme)

    print("\n== 15-16. a new profile reports the engine as not configured and research as owner-supplied ==")
    hf = P / HF
    doc = subprocess.run([sys.executable, str(hf), "doctor", "--json"], capture_output=True, text=True,
                         env=sb.env(HERMES_HOME=str(P)))
    try:
        d = json.loads(doc.stdout)
    except Exception:
        d = {}
    r.check("doctor reports `not configured` with exit code 3",
            d.get("video_engine") == "not configured" and doc.returncode == 3, doc.stdout[:200])
    r.check("doctor names the missing pieces", {"cli", "browser", "workspace"} <= set(d.get("missing", [])),
            str(d.get("missing")))
    r.check("research reports `owner-supplied only`", d.get("research") == "owner-supplied only", str(d.get("research")))
    r.check("install created no engine state, toolchain, browser, or workspace",
            not (P / "local" / "video-editor").exists())

    print("\n== 17. install with all network access denied ==")
    wrap = no_network_wrapper()
    if wrap:
        sb2 = Sandbox()
        probe_net = subprocess.run(wrap + [sys.executable, "-c",
                                   "import socket;socket.create_connection(('registry.npmjs.org',443),3)"],
                                   capture_output=True)
        r.check("the network-deny wrapper really blocks outbound connections", probe_net.returncode != 0)
        p2 = install_profile(sb2, wrap=wrap)
        r.check("profile installs with network denied (no download, no network write)",
                p2.returncode == 0 and (sb2.profile_dir / "SOUL.md").is_file(),
                (p2.stdout + p2.stderr)[-300:])
        t2 = tree(sb2.profile_dir)
        r.check("network-denied install matches the repository payload exactly",
                all(t2.get(k) == v for k, v in expected.items() if k != "distribution.yaml")
                and not [k for k in t2 if k not in expected])
        r.check("no node_modules, browser, or model appeared",
                not any("node_modules" in p.parts or "chrome-headless-shell" in p.name
                        or p.suffix in {".onnx", ".bin"} for p in sb2.root.rglob("*")))
        ps = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True).stdout
        r.check("install started no server, preview, or render process from the sandbox",
                str(sb2.root) not in ps and str(sb.root) not in ps)
    else:
        r.notrun("install with network denied", "no sandbox-exec or unprivileged unshare on this machine")

    print("\n== 18. launcher resolves the profile from its own location ==")
    plan = subprocess.run([sys.executable, str(hf), "setup", "--plan"], capture_output=True, text=True,
                          env=sb.env())
    r.check("`setup --plan` names the sandbox profile, not the developer's home",
            str(P) in plan.stdout and str(sb.real_home / ".hermes") not in plan.stdout, plan.stdout[:300])
    r.check("`setup --plan` lists each download with source, size, and license",
            plan.stdout.count("source:") >= 3 and plan.stdout.count("license:") >= 3
            and plan.stdout.count("size:") >= 3)
    r.check("`setup --plan` changed nothing", not (P / "local" / "video-editor").exists())
    test_ws = sb.root / "external-workspace"
    made = subprocess.run([sys.executable, str(hf), "setup", "--workspace", str(test_ws)], capture_output=True,
                          text=True, env=sb.env(HERMES_HOME=str(P)))
    engine = P / "local" / "video-editor" / "video-engine" / "engine.json"
    r.check("`setup --workspace` writes engine state inside the test profile only",
            made.returncode == 0 and engine.is_file() and str(engine).startswith(str(sb.root))
            and json.loads(engine.read_text())["workspace"] == str(test_ws), made.stderr[-200:])
    r.check("the workspace has footage, working-copies, references, and projects folders",
            all((test_ws / d).is_dir() for d in ("footage", "working-copies", "references", "projects")))

    print("\n== 19-20. update preserves user state and refreshes owned files ==")
    sentinels = {
        P / ".env": "SENTINEL_ENV=synthetic\n",
        P / "auth.json": '{"sentinel": "synthetic"}\n',
        P / "memories" / "MEMORY.md": "sentinel memory\n",
        P / "sessions" / "s1.json": '{"sentinel": true}\n',
        P / "local" / "editor-profile.md": "sentinel editor profile\n",
        P / "local" / "brand-and-visual-identity.md": "sentinel brand identity\n",
        P / "local" / "style-library" / "SB-SENTINEL-001.v1.yaml": "blueprint_id: SB-SENTINEL-001\n",
        P / "local" / "style-library" / "SB-SENTINEL-001.v2.yaml": "blueprint_id: SB-SENTINEL-001\nblueprint_version: 2\n",
        P / "workspace" / "projects" / "demo" / "v1" / "index.html": "<!-- sentinel profile-workspace project -->\n",
        test_ws / "projects" / "demo" / "style-decision.yaml": "decision: hybrid\n",
        test_ws / "projects" / "demo" / "v1" / "index.html": "<!-- sentinel project version 1 -->\n",
        test_ws / "projects" / "demo" / "v2" / "index.html": "<!-- sentinel project version 2 -->\n",
        test_ws / "footage" / "take.txt": "sentinel stand-in for footage\n",
        test_ws / "references" / "ref.txt": "sentinel stand-in for a reference\n",
        P / "local" / "effects" / "looks-and-grades" / "brand-duotone" / "effect.json": '{"effect_id": "brand-duotone"}\n',
        P / "local" / "effect-recipes" / "cinematic-portrait.yaml": "recipe_id: R-SENTINEL\n",
        P / "skills" / "my-own" / "my-skill" / "SKILL.md": "---\nname: my-skill\ndescription: user skill\n---\nuser\n",
        P / "skills" / "integrations" / "my-integration" / "SKILL.md": "---\nname: my-integration\ndescription: user integration\n---\nuser\n",
    }
    for path, body in sentinels.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    cfg = P / "config.yaml"
    cfg.write_text(cfg.read_text(encoding="utf-8") + "\n# sentinel local override\nmodel:\n  default: sentinel-model\n",
                   encoding="utf-8")
    cfg_hash = sha256_file(cfg)
    engine_hash = sha256_file(engine)
    before = {p: sha256_file(p) for p in sentinels}
    (P / "SOUL.md").write_text("tampered\n", encoding="utf-8")
    (P / "skills/video-editor-core/render-and-export/SKILL.md").write_text("tampered\n", encoding="utf-8")
    (P / HF).write_text("tampered\n", encoding="utf-8")
    stale = P / "skills/video-editor-core/retired-skill/SKILL.md"
    stale.parent.mkdir(parents=True)
    stale.write_text("---\nname: retired-skill\ndescription: stale\n---\n", encoding="utf-8")

    up = run_hermes(sb, ["profile", "update", PROFILE, "--yes"])
    r.check("`hermes profile update video-editor` succeeds", up.returncode == 0, (up.stdout + up.stderr)[-300:])
    for path in sentinels:
        rel = path.relative_to(sb.root).as_posix()
        r.check(f"preserved: {rel}", path.is_file() and sha256_file(path) == before[path])
    r.check("config.yaml overrides preserved", sha256_file(cfg) == cfg_hash)
    r.check("video engine state (workspace approval) preserved", sha256_file(engine) == engine_hash)
    r.check("owned SOUL.md restored", sha256_file(P / "SOUL.md") == sha256_file(REPO / "SOUL.md"))
    r.check("owned skill restored",
            sha256_file(P / "skills/video-editor-core/render-and-export/SKILL.md")
            == sha256_file(REPO / "skills/video-editor-core/render-and-export/SKILL.md"))
    r.check("owned launcher restored", sha256_file(P / HF) == sha256_file(REPO / HF))
    # Hermes changed how update treats owned skill folders: 0.21.x replaces an
    # owned directory wholesale, so a skill the distribution no longer ships is
    # removed; 0.22.x merges per skill, so it stays. Record what this version
    # did and hold it to the documented behaviour (docs/upgrade-notes in README).
    version = (hermes_version() or "")
    m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", version)
    merges = bool(m) and (int(m.group(1)), int(m.group(2))) >= (0, 22)
    if merges:
        r.check("retired skill on update (0.22 and later): kept, as documented", stale.exists(),
                "Hermes 0.22 merges owned skill folders per skill")
    else:
        r.check("retired skill on update (before 0.22): removed, as documented", not stale.exists())
    r.check("owner effects and recipes in local/ survive update",
            (P / "local/effects/looks-and-grades/brand-duotone/effect.json").is_file()
            and (P / "local/effect-recipes/cinematic-portrait.yaml").is_file())

    print("\n== 21. vendor checksums ==")
    v = subprocess.run([sys.executable, str(REPO / "scripts/hyperframes_vendor.py"), "verify"],
                       capture_output=True, text=True)
    r.check("vendor verification passes", v.returncode == 0, v.stdout[-300:])

    print("\n== 22. git history secret scan ==")
    if (REPO / ".git").exists() and subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                                                   capture_output=True).returncode == 0:
        h = subprocess.run([sys.executable, str(REPO / "scripts/validate.py"), "--history", "--only-history"],
                           capture_output=True, text=True)
        r.check("git history passes the secret scan", h.returncode == 0, h.stdout[-300:])
    else:
        r.notrun("git history secret scan", "repository has no commits yet")

    print("\n== 23. Kanban exchange with a temporary social-media profile ==")
    made = run_hermes(sb, ["profile", "create", "social-media"])
    if r.check("a second temporary profile named social-media is created",
               made.returncode == 0 and (sb.hermes_home / "profiles" / "social-media").is_dir(),
               (made.stdout + made.stderr)[-200:]):
        run_hermes(sb, ["kanban", "init"])
        brief = sb.root / "edit-task.yaml"
        fields = [line.split(":")[0] for line in (REPO / "templates/edit-task.yaml").read_text().splitlines()
                  if re.match(r"^[a-z_]+:", line)]
        body = {f: "" for f in fields}
        body.update(task_id="SYN-TASK-001", source_profile="social-media", objective="Cut the synthetic talking-head clip",
                    platform="synthetic-platform", format="short-form vertical",
                    footage_reference="footage/take.mp4 (path in the approved workspace)",
                    footage_sha256="0" * 64, hook="synthetic hook line", style_approver="owner")
        brief.write_text("".join(f"{k}: {v}\n" for k, v in body.items()), encoding="utf-8")
        created = run_hermes(sb, ["kanban", "create", "Edit: synthetic talking-head clip", "--assignee", PROFILE,
                                  "--created-by", "social-media", "--body-file", str(brief), "--json"])
        match = re.search(r'"id":\s*"([^"]+)"', created.stdout)
        if r.check("`hermes kanban create ... --assignee video-editor` creates the task",
                   created.returncode == 0 and bool(match), (created.stdout + created.stderr)[-300:]):
            task_id = match.group(1)
            shown = run_hermes(sb, ["-p", PROFILE, "kanban", "show", task_id, "--json"]).stdout
            r.check("the video-editor profile reads the task and its brief",
                    "SYN-TASK-001" in shown and "synthetic hook line" in shown and '"assignee": "video-editor"' in shown,
                    shown[-300:])
            mine = run_hermes(sb, ["kanban", "list", "--assignee", PROFILE, "--json"]).stdout
            r.check("the task is listed for the video-editor assignee", task_id in mine)
            result_fields = [line.split(":")[0] for line in (REPO / "templates/edit-result.yaml").read_text().splitlines()
                             if re.match(r"^[a-z_]+:", line)]
            result = {f: "" for f in result_fields}
            result.update(status="review_requested", task_id="SYN-TASK-001", project_id="SYN-PROJ-001", version="v1",
                          edit_state="review_requested", style_option_chosen="hybrid",
                          deliverables="handoff/SYN-PROJ-001/v1/draft.mp4 sha256=" + "a" * 64)
            comment = run_hermes(sb, ["kanban", "comment", task_id, "--author", PROFILE,
                                      "".join(f"{k}: {v}\n" for k, v in result.items())])
            r.check("the video-editor profile answers with a structured result", comment.returncode == 0,
                    (comment.stdout + comment.stderr)[-200:])
            review = sb.root / "review-request.yaml"
            review.write_text("status: review_requested\ntask_id: SYN-TASK-001\nfile_sha256: " + "a" * 64
                              + "\nquestions:\n  - Does the opening deliver the hook as written?\n", encoding="utf-8")
            req = run_hermes(sb, ["kanban", "create", "Rough cut review: SYN-PROJ-001 v1", "--assignee", "social-media",
                                  "--created-by", PROFILE, "--parent", task_id, "--body-file", str(review), "--json"])
            m2 = re.search(r'"id":\s*"([^"]+)"', req.stdout)
            r.check("`hermes kanban create ... --assignee social-media` creates the review request",
                    req.returncode == 0 and bool(m2), (req.stdout + req.stderr)[-300:])
            if m2:
                seen = run_hermes(sb, ["-p", "social-media", "kanban", "show", m2.group(1), "--json"]).stdout
                r.check("the social-media profile reads the review request and its checksum",
                        "Does the opening deliver the hook" in seen and "a" * 64 in seen, seen[-300:])
                back = run_hermes(sb, ["-p", "social-media", "kanban", "show", task_id, "--json"]).stdout
                r.check("the social-media profile reads the editor's result on the original task",
                        "review_requested" in back and "SYN-PROJ-001" in back, back[-300:])
            done = run_hermes(sb, ["kanban", "complete", task_id, "--result", "delivered by reference; see handoff record"])
            r.check("the task completes", done.returncode == 0, (done.stdout + done.stderr)[-200:])
            board = (sb.hermes_home / "kanban.db")
            dump = b"".join(p.read_bytes() for p in sb.hermes_home.rglob("kanban*.db*") if p.is_file())
            r.check("the board holds references and checksums, and no media bytes",
                    b"ftypisom" not in dump and b"ftypmp42" not in dump and (b"SYN-TASK-001" in dump or not board.exists()))
            attach_help = run_hermes(sb, ["kanban", "attach", "--help"])
            r.check("observed: this Hermes release supports Kanban attachments (policy still passes references only)",
                    attach_help.returncode == 0 and "attach" in attach_help.stdout, attach_help.stderr[-200:])
            r.check("the second profile cannot be assumed to read this profile's files: the profiles have separate homes",
                    not (sb.hermes_home / "profiles" / "social-media" / "skills" / "video-editor-core").exists()
                    and not (sb.hermes_home / "profiles" / "social-media" / "local").exists())

    print("\n== 24. install from the published GitHub URL ==")
    url = os.environ.get("VE_TEST_PUBLISHED_URL")
    if url:
        # Runs the README's primary command form, answering the confirmation prompt.
        # A private repository needs GH_TOKEN or GITHUB_TOKEN in the environment;
        # Hermes reads it for the clone and stores nothing.
        sb3 = Sandbox()
        cmd, cwd = hermes_command()
        p3 = subprocess.run(cmd + ["profile", "install", url, "--alias"], cwd=cwd, env=sb3.env(),
                            input="y\n", capture_output=True, text=True, timeout=900)
        r.check(f"`hermes profile install {url} --alias` succeeds with the confirmation prompt",
                p3.returncode == 0 and (sb3.profile_dir / "SOUL.md").is_file(), (p3.stdout + p3.stderr)[-300:])
        t3 = tree(sb3.profile_dir) if sb3.profile_dir.is_dir() else {}
        r.check("published install matches this checkout's payload byte for byte",
                bool(t3) and all(t3.get(k) == v for k, v in expected.items() if k != "distribution.yaml"))
        r.check("published install copies no repository-only file",
                not [n for n in REPO_ONLY if (sb3.profile_dir / n).exists()])
        info3 = run_hermes(sb3, ["profile", "info", PROFILE]).stdout
        r.check("profile info records the published source", url in info3, info3[:200])
    else:
        r.notrun(f"install from {GITHUB}",
                 "set VE_TEST_PUBLISHED_URL after publication (and GH_TOKEN while the repository is private)")

    return r.finish(json_out)


if __name__ == "__main__":
    sys.exit(main())
