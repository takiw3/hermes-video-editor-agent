#!/usr/bin/env python3
"""Effects library tool for the Hermes video-editor profile.

    python3 "$HERMES_HOME/skills/video-effects-core/effects-library/scripts/fx.py" <command> ...

  list [--family F] [--status S] [--route R] [--featured]   effects in the catalog, with their verified status
  show <effect_id>                             one catalog entry
  apply <project> --effect ID [--target SEL] [--from SEL --to SEL] [--at S] [--duration S]
        [--param k=v ...] [--animate k=t:v,t:v[:ease] ...] [--container SEL] [--iid ID]
                                               add one effect instance to a composition
  remove <project> --iid ID                    take one instance off; the composition returns to before
  instances <project>                          the effect instances applied to a composition
  stack-check <project>                        cost, conflicts, HDR, and photosensitivity budget
  check-plan <effect-plan.yaml>                an effect plan names verified effects inside their ranges
  flash-check <video> [--display-short-side N] general and red flash analysis against WCAG 2.3.1
  contact-sheet <video> --out F [--at t,t,..]  one strip of stills
  verify <effect_id> [--keep]                  run the 12-check verification gate on synthetic media

Standard library only, plus FFmpeg. Renders go through the profile launcher,
so every gate the launcher enforces applies here too. No network access: the
verification renders run with outbound network denied by the operating system.
Exit codes: 0 ok, 2 usage, 4 refused, 5 check failed.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import html as _html
import json
import math
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser
from pathlib import Path

TOOL_VERSION = "1.2.0"
SCRIPT = Path(__file__).resolve()
LIBRARY = SCRIPT.parents[1]
PROFILE_HOME = SCRIPT.parents[4]
LOCAL_EFFECTS = PROFILE_HOME / "local" / "effects"
LOCAL_RECIPES = PROFILE_HOME / "local" / "effect-recipes"
ENGINE_DIR = PROFILE_HOME / "local" / "video-editor" / "video-engine"
ENGINE_FILE = ENGINE_DIR / "engine.json"
LAUNCHER = PROFILE_HOME / "skills" / "integrations" / "editor-hyperframes" / "scripts" / "hf.py"
PIN_FILE = PROFILE_HOME / "skills" / "integrations" / "editor-hyperframes" / "toolchain" / "pin.json"
CATALOG = LIBRARY / "catalog.yaml"
FEATURED = LIBRARY / "featured.json"
RUNTIME = LIBRARY / "runtime" / "fx-runtime.js"
INSTANCES = "fx-instances.json"

FAMILIES = [
    "looks-and-grades", "image-effects", "transitions", "camera-and-motion",
    "keying-and-subject", "overlays-and-generators", "text-and-title", "creator-composites", "audio",
]
ROUTES = [
    "hf-media-treatment", "hf-color-grade", "hf-shader-transition", "hf-vfx-chain", "hf-registry",
    "css-filter", "svg-filter", "gsap-composite", "original-webgl", "hf-audio-fx",
]
STATUSES = ["planned", "implemented", "verified", "limited", "retired"]
EXIT_USAGE, EXIT_REFUSED, EXIT_CHECK = 2, 4, 5

# WCAG 2.2, read at https://www.w3.org/TR/WCAG22/ (W3C Recommendation 12 December
# 2024) and https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html
# on 2026-10-21. Each constant below is quoted from those pages, not invented.
WCAG = {
    "source": "WCAG 2.2 SC 2.3.1 Three Flashes or Below Threshold; definitions of general flash, red flash, relative luminance",
    "urls": [
        "https://www.w3.org/TR/WCAG22/",
        "https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html",
    ],
    "accessed": "2026-10-21",
    "max_flashes_per_second": 3,
    "general_flash_min_change": 0.10,
    "general_flash_darker_below": 0.80,
    "red_ratio_at_least": 0.8,
    "red_chromaticity_change_more_than": 0.2,
    "field_block_css_px": [341, 256],
    "area_fraction_of_field": 0.25,
}


# ---------------------------------------------------------------- output

def out(payload) -> None:
    print(json.dumps(payload, indent=2), flush=True)


def fail(code: int, status: str, message: str, **extra):
    print(json.dumps({"status": status, "message": message, **extra}, indent=2), file=sys.stderr, flush=True)
    sys.exit(code)


def now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def take(args: list[str], name: str, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            fail(EXIT_USAGE, "blocked", f"{name} needs a value")
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


def take_all(args: list[str], name: str) -> list[str]:
    values = []
    while name in args:
        values.append(take(args, name))
    return values


def take_flag(args: list[str], name: str) -> bool:
    if name in args:
        args.remove(name)
        return True
    return False


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def load_engine() -> dict:
    try:
        return json.loads(ENGINE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def workspace_root() -> Path | None:
    ws = load_engine().get("workspace")
    return Path(ws) if ws else None


def need(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        fail(EXIT_REFUSED, "needs_setup", f"{tool} is not on PATH", fix=f"the owner installs {tool}")
    return found


# ---------------------------------------------------------------- catalog

def read_json_yaml(path: Path):
    """catalog.yaml is generated as JSON (valid YAML) after comment lines."""
    text = path.read_text(encoding="utf-8")
    body = "\n".join(line for line in text.splitlines() if not line.startswith("#"))
    return json.loads(body)


def effect_dirs(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    return sorted(p.parent for p in root.glob("*/*/effect.json"))


def load_effect(path: Path) -> dict:
    spec = json.loads((path / "effect.json").read_text(encoding="utf-8"))
    spec["_dir"] = str(path)
    vr = path / "verification.json"
    spec["_verification"] = json.loads(vr.read_text(encoding="utf-8")) if vr.is_file() else None
    return spec


def library() -> dict[str, dict]:
    effects: dict[str, dict] = {}
    for d in effect_dirs(LIBRARY):
        spec = load_effect(d)
        spec["_origin"] = "shipped"
        effects[spec["effect_id"]] = spec
    for d in effect_dirs(LOCAL_EFFECTS):
        spec = load_effect(d)
        if spec["effect_id"] in effects:
            spec["_shadowed"] = True
            continue
        spec["_origin"] = "owner-local"
        effects[spec["effect_id"]] = spec
    return effects


def status_of(spec: dict) -> str:
    """The status a catalog entry may claim. Verified only with a passing record."""
    declared = spec.get("status", "implemented")
    if declared in {"retired", "planned"}:
        return declared
    rec = spec.get("_verification")
    if rec and rec.get("result") == "pass":
        return "limited" if declared == "limited" or rec.get("limited") else "verified"
    return "implemented" if declared != "limited" else "limited"


def get_effect(effect_id: str) -> dict:
    effects = library()
    if effect_id not in effects:
        close = [e for e in effects if effect_id.split("-")[0] in e][:8]
        fail(EXIT_USAGE, "blocked", f"unknown effect: {effect_id}", similar=close)
    return effects[effect_id]


_FEATURED: dict[str, str] | None = None


def featured_ids() -> dict[str, str]:
    """The hand-curated first picks, reviewed at full size: effect_id -> use."""
    global _FEATURED
    if _FEATURED is None:
        data = json.loads(FEATURED.read_text(encoding="utf-8")) if FEATURED.is_file() else {}
        _FEATURED = {f["effect_id"]: f["use_for"] for f in data.get("effects", [])}
    return _FEATURED


def public_entry(spec: dict) -> dict:
    keep = ["effect_id", "display_name", "family", "kind", "description", "implementation_route",
            "hyperframes_feature", "parameters", "applies_to", "needs_model", "needs_key_footage",
            "hdr_behavior", "deterministic", "seek_safe", "photosensitivity", "face_safe",
            "render_cost_multiplier", "provenance", "reference_id", "license"]
    entry = {k: spec.get(k) for k in keep}
    entry["status"] = status_of(spec)
    entry["origin"] = spec.get("_origin")
    # Only shipped effects can be featured; an owner effect never is.
    use = featured_ids().get(spec.get("effect_id")) if spec.get("_origin") == "shipped" else None
    entry["featured"] = use is not None
    entry["featured_use"] = use
    rec = spec.get("_verification") or {}
    if rec:
        entry["render_cost_multiplier"] = rec.get("render_cost_multiplier", entry["render_cost_multiplier"])
        entry["photosensitivity"] = rec.get("photosensitivity", {}).get("result", entry["photosensitivity"])
        entry["verified_at"] = rec.get("verified_at")
    return entry


def cmd_list(args: list[str]) -> int:
    family, status, route = take(args, "--family"), take(args, "--status"), take(args, "--route")
    only_featured = take_flag(args, "--featured")
    rows = []
    for spec in library().values():
        e = public_entry(spec)
        if only_featured and not (e["featured"] and e["status"] == "verified"):
            continue
        if family and e["family"] != family:
            continue
        if status and e["status"] != status:
            continue
        if route and e["implementation_route"] != route:
            continue
        rows.append({k: e[k] for k in ("effect_id", "display_name", "family", "implementation_route", "status",
                                       "render_cost_multiplier", "photosensitivity", "origin", "featured", "featured_use")})
    counts: dict[str, int] = {}
    for r in rows:
        if r["status"] == "verified" and r["family"] != "audio":
            counts[r["family"]] = counts.get(r["family"], 0) + 1
    out({"tool": "fx list", "version": TOOL_VERSION, "count": len(rows),
         "verified_visual_by_family": counts, "verified_visual_total": sum(counts.values()), "effects": rows})
    return 0


def cmd_show(args: list[str]) -> int:
    if not args:
        fail(EXIT_USAGE, "blocked", "show needs an effect id")
    spec = get_effect(args[0])
    entry = public_entry(spec)
    entry["verification"] = spec.get("_verification")
    entry["source_dir"] = spec["_dir"]
    out(entry)
    return 0


# ---------------------------------------------------------------- params

def param_specs(spec: dict) -> dict[str, dict]:
    return {p["key"]: p for p in spec.get("parameters", [])}


def resolve_params(spec: dict, given: dict[str, float]) -> dict[str, float]:
    specs = param_specs(spec)
    params = {k: p["default"] for k, p in specs.items()}
    for key, value in given.items():
        if key not in specs:
            fail(EXIT_USAGE, "blocked", f"{spec['effect_id']} has no parameter {key}", parameters=sorted(specs))
        p = specs[key]
        if not (p["min"] <= value <= p["max"]):
            fail(EXIT_REFUSED, "blocked", f"{key}={value} is outside {p['min']}..{p['max']}",
                 fix="pick a value inside the verified range; values outside it were never rendered")
        params[key] = value
    return params


def parse_kv(items: list[str]) -> dict[str, float]:
    result = {}
    for item in items:
        if "=" not in item:
            fail(EXIT_USAGE, "blocked", f"--param expects key=value, got {item}")
        k, v = item.split("=", 1)
        try:
            result[k.strip()] = float(v)
        except ValueError:
            fail(EXIT_USAGE, "blocked", f"--param {k} must be a number")
    return result


def parse_animate(spec: dict, items: list[str]) -> dict:
    """--animate key=t:v,t:v[:ease]  (times in composition seconds)."""
    specs = param_specs(spec)
    result = {}
    for item in items:
        key, _, rest = item.partition("=")
        if key not in specs:
            fail(EXIT_USAGE, "blocked", f"{spec['effect_id']} has no parameter {key}")
        if not specs[key].get("animatable"):
            fail(EXIT_REFUSED, "blocked", f"{key} is not animatable on {spec['effect_id']}")
        ease = None
        if rest.count(":") > rest.count(","):
            pieces = rest.split(":")
            if not re.fullmatch(r"-?[\d.]+", pieces[-1]):
                ease = pieces[-1]
                rest = ":".join(pieces[:-1])
        keys = []
        for pair in rest.split(","):
            t, _, v = pair.partition(":")
            tv, vv = float(t), float(v)
            if not (specs[key]["min"] <= vv <= specs[key]["max"]):
                fail(EXIT_REFUSED, "blocked", f"{key} keyframe {vv} is outside {specs[key]['min']}..{specs[key]['max']}")
            keys.append([tv, vv])
        if len(keys) < 2:
            fail(EXIT_USAGE, "blocked", f"--animate {key} needs at least two keyframes")
        if ease and not re.fullmatch(r"[a-z0-9.]+(\.(in|out|inOut))?", ease):
            fail(EXIT_USAGE, "blocked", f"unknown ease {ease}")
        result[key] = {"keys": keys, "ease": ease or "none"}
    return result


def fmt(value: float) -> str:
    text = f"{value:.6f}".rstrip("0").rstrip(".")
    return text if text not in {"", "-0"} else "0"


# ---------------------------------------------------------------- HTML editing

class _Spans(HTMLParser):
    """Finds the source span of every element that carries an id."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self, text: str):
        super().__init__(convert_charrefs=False)
        self.text = text
        self.lines = [0]
        for line in text.splitlines(keepends=True):
            self.lines.append(self.lines[-1] + len(line))
        self.stack: list[tuple[str, str | None, int, int]] = []
        self.spans: dict[str, dict] = {}
        self.in_raw = None

    def _pos(self) -> int:
        line, col = self.getpos()
        return self.lines[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self._pos()
        end = start + len(self.get_starttag_text() or "")
        ident = dict(attrs).get("id")
        if tag in self.VOID:
            if ident:
                self.spans[ident] = {"tag": tag, "start": start, "open_end": end, "close_start": end, "end": end}
            return
        self.stack.append((tag, ident, start, end))

    def handle_startendtag(self, tag, attrs):
        start = self._pos()
        end = start + len(self.get_starttag_text() or "")
        ident = dict(attrs).get("id")
        if ident:
            self.spans[ident] = {"tag": tag, "start": start, "open_end": end, "close_start": end, "end": end}

    def handle_endtag(self, tag):
        close_start = self._pos()
        close_end = self.text.index(">", close_start) + 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                t, ident, start, open_end = self.stack[i]
                del self.stack[i:]
                if ident:
                    self.spans[ident] = {"tag": t, "start": start, "open_end": open_end,
                                         "close_start": close_start, "end": close_end}
                return


def element_spans(text: str) -> dict[str, dict]:
    p = _Spans(text)
    p.feed(text)
    p.close()
    return p.spans


def sel_id(selector: str | None) -> str | None:
    if not selector:
        return None
    if not re.fullmatch(r"#[A-Za-z][\w-]*", selector):
        fail(EXIT_USAGE, "blocked", f"selectors are element ids written as #id, got {selector}")
    return selector[1:]


def root_info(text: str) -> dict:
    m = re.search(r'<(\w+)\b[^>]*\bdata-composition-id="([^"]+)"[^>]*>', text)
    if not m:
        fail(EXIT_REFUSED, "blocked", "index.html has no composition root (data-composition-id)")
    tag = m.group(0)
    def attr(name):
        mm = re.search(rf'\b{name}="([^"]*)"', tag)
        return mm.group(1) if mm else None
    rid = attr("id")
    if not rid:
        fail(EXIT_REFUSED, "blocked", "the composition root needs an id so effects can be placed inside it")
    return {"id": rid, "composition_id": m.group(2), "width": float(attr("data-width") or 0),
            "height": float(attr("data-height") or 0), "duration": float(attr("data-duration") or 0)}


def set_attr(open_tag: str, name: str, value: str | None) -> str:
    pattern = re.compile(rf'\s{name}=(\'[^\']*\'|"[^"]*")')
    if value is None:
        return pattern.sub("", open_tag, count=1)
    quoted = "'" + value.replace("'", "&#39;") + "'" if '"' in value else '"' + value + '"'
    if pattern.search(open_tag):
        return pattern.sub(f" {name}={quoted}", open_tag, count=1)
    return re.sub(r"\s*/?>$", lambda m: f" {name}={quoted}{m.group(0)}", open_tag, count=1)


def get_attr(open_tag: str, name: str) -> str | None:
    m = re.search(rf'\s{name}=(\'([^\']*)\'|"([^"]*)")', open_tag)
    if not m:
        return None
    return _html.unescape(m.group(2) if m.group(2) is not None else m.group(3))


def edit_open_tag(text: str, ident: str, fn) -> str:
    spans = element_spans(text)
    if ident not in spans:
        fail(EXIT_REFUSED, "blocked", f"no element with id {ident} in the composition")
    s = spans[ident]
    open_tag = text[s["start"]:s["open_end"]]
    return text[:s["start"]] + fn(open_tag) + text[s["open_end"]:]


def add_class(open_tag: str, names: list[str]) -> str:
    current = (get_attr(open_tag, "class") or "").split()
    for n in names:
        if n not in current:
            current.append(n)
    return set_attr(open_tag, "class", " ".join(current))


def remove_class(open_tag: str, names: list[str]) -> str:
    current = [c for c in (get_attr(open_tag, "class") or "").split() if c not in names]
    return set_attr(open_tag, "class", " ".join(current) if current else None)


BLOCK_RE = r"[ \t]*<!-- fx:{name} -->.*?<!-- /fx:{name} -->\n?"


def strip_block(text: str, name: str) -> str:
    return re.sub(BLOCK_RE.format(name=re.escape(name)), "", text, flags=re.S)


def block(name: str, body: str, indent: str = "    ") -> str:
    return f"{indent}<!-- fx:{name} -->\n{body}{indent}<!-- /fx:{name} -->\n"


# ---------------------------------------------------------------- templates

def render_template(template: str, inst: dict, root: dict) -> str:
    params = inst["params"]

    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key == "iid":
            return inst["iid"]
        if key == "W":
            return fmt(root["width"])
        if key == "H":
            return fmt(root["height"])
        if key == "target":
            return inst.get("target") or ""
        if key.startswith("p."):
            name = key[2:]
            if name not in params:
                raise KeyError(f"template names an unknown parameter: {name}")
            return fmt(float(params[name]))
        raise KeyError(f"unknown template field: {key}")

    return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", sub, template)


def grading_value(template, params: dict):
    """Fill "$p.key" strings in a grading or vfx JSON template with numbers."""
    if isinstance(template, dict):
        return {k: grading_value(v, params) for k, v in template.items()}
    if isinstance(template, list):
        return [grading_value(v, params) for v in template]
    if isinstance(template, str) and template.startswith("$p."):
        return params[template[3:]]
    if isinstance(template, str) and template.startswith("$-p."):
        return -params[template[4:]]
    return template


def effect_file(spec: dict, name: str) -> str | None:
    path = Path(spec["_dir"]) / name
    return path.read_text(encoding="utf-8") if path.is_file() else None


# ---------------------------------------------------------------- projects

def find_project(arg: str) -> Path:
    project = Path(arg).expanduser().resolve()
    if project.is_file():
        project = project.parent
    if not (project / "index.html").is_file():
        fail(EXIT_USAGE, "blocked", f"no index.html in {project}")
    ws = workspace_root()
    if ws is None:
        fail(EXIT_REFUSED, "needs_setup", "no approved workspace; the owner runs hf.py setup --workspace <folder>")
    if not inside(project, ws / "projects"):
        fail(EXIT_REFUSED, "blocked", f"effects are applied to projects under {ws / 'projects'}, not {project}")
    return project


def load_instances(project: Path) -> dict:
    path = project / INSTANCES
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    return {"version": 1, "instances": [], "grading_base": {}}


def save_instances(project: Path, data: dict) -> None:
    (project / INSTANCES).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def pin() -> dict:
    return json.loads(PIN_FILE.read_text(encoding="utf-8"))


def shader_source() -> Path | None:
    tc = ENGINE_DIR / f"toolchain-{pin()['npm_version']}"
    src = tc / "node_modules" / "@hyperframes" / "shader-transitions" / "dist" / "index.global.js"
    return src if src.is_file() else None


def copy_if_changed(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.is_file() or sha256_file(dest) != sha256_file(src):
        shutil.copy2(src, dest)


REGISTER_LINES = {
    "assets/vendor/fx-runtime.js": ("fx-runtime.js from the video-editor profile effects library",
                                    "MIT, Copyright 2026 Taki Wong / TakiGPT AI Inc.",
                                    "skills/video-effects-core/effects-library/runtime/fx-runtime.js"),
    "assets/vendor/hyper-shader.js": ("@hyperframes/shader-transitions global build from the pinned toolchain lockfile",
                                      "Apache-2.0, Copyright 2026 HeyGen, Inc.; bundles html2canvas (MIT)",
                                      "toolchain package.json and package-lock.json in the profile"),
}


def register_asset(project: Path, rel: str, source: str, license_text: str, proof: str) -> None:
    register = project / "asset-rights-register.yaml"
    if not register.is_file():
        register.write_text("assets: []\n", encoding="utf-8")
    text = register.read_text(encoding="utf-8")
    if f"asset: {rel}\n" in text:
        return
    text = text.replace("assets: []", "assets:")
    if not text.endswith("\n"):
        text += "\n"
    text += f"  - asset: {rel}\n    source: {source}\n    license: {license_text}\n    proof: {proof}\n"
    register.write_text(text, encoding="utf-8")


def sync_project(project: Path, data: dict) -> dict:
    """Rewrite every managed block from fx-instances.json. Idempotent."""
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    root = root_info(text)
    effects = library()
    for name in ("head", "defs", "run"):
        text = strip_block(text, name)
    text = re.sub(r"[ \t]*<!-- fx:overlay [\w-]+ -->.*?<!-- /fx:overlay [\w-]+ -->\n?", "", text, flags=re.S)

    css, defs, scripts, runs = [], [], [], []
    filters: dict[str, list[str]] = {}
    needs_runtime = False
    used_effect_scripts: list[str] = []
    for inst in data["instances"]:
        spec = effects.get(inst["effect"])
        if spec is None:
            fail(EXIT_REFUSED, "blocked", f"instance {inst['iid']} names an effect the library no longer has: {inst['effect']}")
        route = spec["implementation_route"]
        style = effect_file(spec, "style.css")
        if style:
            css.append(render_template(style, inst, root))
        if spec.get("css_filter"):
            # Filter effects on one element share a single `filter` property,
            # applied in the order the instances were added.
            key = sel_id(inst.get("target") or inst.get("to") or f"#{root['id']}")
            filters.setdefault(key, []).append(render_template(spec["css_filter"], inst, root))
        svg = effect_file(spec, "defs.svg")
        if svg:
            defs.append(render_template(svg, inst, root))
        js = effect_file(spec, "update.js")
        if route.startswith("hf-") and not js and not inst.get("animate"):
            continue  # a static HyperFrames attribute needs no runtime
        if route == "hf-shader-transition":
            continue  # HyperShader owns its own timeline entries
        needs_runtime = True
        if js and inst["effect"] not in used_effect_scripts:
            used_effect_scripts.append(inst["effect"])
        run = {k: inst[k] for k in ("iid", "effect", "target", "from", "to", "start", "duration", "params", "animate")
               if inst.get(k) is not None}
        if not js:
            run["def"] = "css-vars"
            if spec.get("animate_vars"):
                run["vars"] = {k: render_template(v, inst, root) for k, v in spec["animate_vars"].items()}
            if spec.get("animate_vars_host"):
                run["varsHost"] = spec["animate_vars_host"]
        runs.append(run)

    # HyperFrames' fast capture (drawElementImage) re-projects CSS 3D contexts
    # from content rasterized once, so a video inside a 3D-transformed layer
    # freezes or vanishes (seen at 0.8.183). A fully transparent drop-shadow on
    # the root is HyperFrames' own documented trigger for screenshot capture,
    # and it changes no pixel.
    if any((effects.get(i["effect"]) or {}).get("needs_screenshot_capture") for i in data["instances"]):
        filters.setdefault(root["id"], []).append("drop-shadow(0 0 0 rgba(0, 0, 0, 0))")
    head_lines = []
    for ident, chain in filters.items():
        css.append(f"      #{ident} {{ filter: {' '.join(chain)}; }}\n")
    if css:
        head_lines.append("    <style>\n" + "".join(c if c.endswith("\n") else c + "\n" for c in css) + "    </style>\n")
    if needs_runtime:
        copy_if_changed(RUNTIME, project / "assets/vendor/fx-runtime.js")
        register_asset(project, "assets/vendor/fx-runtime.js", *REGISTER_LINES["assets/vendor/fx-runtime.js"])
        head_lines.append('    <script src="assets/vendor/fx-runtime.js"></script>\n')
        for eid in used_effect_scripts:
            spec = effects[eid]
            src = Path(spec["_dir"]) / "update.js"
            rel = f"assets/fx/{eid}.js"
            copy_if_changed(src, project / rel)
            origin = "the profile effects library" if spec.get("_origin") == "shipped" else "the owner's local effects folder"
            register_asset(project, rel, f"effect script {eid} from {origin}", spec.get("license", "MIT"),
                           f"{spec['_dir']}/effect.json")
            head_lines.append(f'    <script src="{rel}"></script>\n')
    if head_lines:
        text = text.replace("</head>", block("head", "".join(head_lines)) + "  </head>", 1) \
            if "  </head>" in text else text.replace("</head>", block("head", "".join(head_lines)) + "</head>", 1)
    if defs:
        svg = ('    <svg class="fx-defs" width="0" height="0" style="position:absolute;width:0;height:0" aria-hidden="true">\n'
               + "".join(d if d.endswith("\n") else d + "\n" for d in defs) + "    </svg>\n")
        text = re.sub(r"(<body\b[^>]*>\n?)", lambda m: m.group(1) + block("defs", svg), text, count=1)

    # Overlay markup goes inside its container, at the end, so it renders above it.
    for inst in data["instances"]:
        spec = effects[inst["effect"]]
        markup = effect_file(spec, "markup.html")
        if not markup:
            continue
        container = sel_id(inst.get("container")) or (sel_id(inst.get("target")) if spec.get("markup_in_target") else None) or root["id"]
        spans = element_spans(text)
        if container not in spans:
            fail(EXIT_REFUSED, "blocked", f"container {container} for {inst['iid']} is not in the composition")
        s = spans[container]
        body = render_template(markup, inst, root)
        piece = f"      <!-- fx:overlay {inst['iid']} -->\n{body if body.endswith(chr(10)) else body + chr(10)}      <!-- /fx:overlay {inst['iid']} -->\n"
        cut = s["close_start"]
        line_start = text.rfind("\n", 0, cut) + 1
        if text[line_start:cut].strip() == "":
            cut = line_start  # the closing tag sits on its own line: insert whole lines before it
        else:
            piece = "\n" + piece
        text = text[:cut] + piece + text[cut:]

    if runs:
        payload = json.dumps(runs, indent=2).replace("</", "<\\/")
        tl = f'window.__timelines["{root["composition_id"]}"]'
        script = f"    <script>\n      HFX.run({tl}, {payload});\n    </script>\n"
        idx = text.rfind("</body>")
        idx = text.rfind("\n", 0, idx) + 1 if text[text.rfind("\n", 0, idx) + 1:idx].strip() == "" else idx
        text = text[:idx] + block("run", script) + text[idx:]
    index.write_text(text, encoding="utf-8")
    return {"instances": len(data["instances"]), "runtime": needs_runtime, "effect_scripts": used_effect_scripts}


def write_grading(project: Path, data: dict, element: str) -> None:
    """Rebuild one media element's data-color-grading from its base plus every instance on it."""
    effects = library()
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    base = data["grading_base"].get(element)
    merged = json.loads(base) if base else {}
    for inst in data["instances"]:
        if inst.get("grading_element") != element:
            continue
        spec = effects[inst["effect"]]
        value = grading_value(spec["grading"], inst["params"])
        for key, sub in value.items():
            if isinstance(sub, dict):
                merged.setdefault(key, {}).update(sub)
            else:
                merged[key] = sub
    value = json.dumps(merged, separators=(",", ":")) if merged else None
    text = edit_open_tag(text, element, lambda tag: set_attr(tag, "data-color-grading", value))
    index.write_text(text, encoding="utf-8")


def write_fx_chain(project: Path, data: dict, element: str) -> None:
    """Rebuild one audio element's data-fx-chain: its base chain plus every
    audio instance on it, in the order they were added (signal order)."""
    effects = library()
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    base = data.setdefault("fx_chain_base", {}).get(element)
    chain = json.loads(base) if base else {"version": 1, "nodes": []}
    nodes = [n for n in chain.get("nodes", []) if not str(n.get("id", "")).startswith("fxp")]
    for inst in data["instances"]:
        if inst.get("audio_element") != element:
            continue
        for node in effects[inst["effect"]]["fx_chain"]:
            filled = grading_value(node, inst["params"])
            filled["id"] = f"fxp{inst['iid']}{node['id']}"
            filled["label"] = effects[inst["effect"]]["display_name"]
            nodes.append(filled)
    value = json.dumps({"version": 1, "nodes": nodes}, separators=(",", ":")) if nodes else None
    text = edit_open_tag(text, element, lambda tag: set_attr(tag, "data-fx-chain", value))
    index.write_text(text, encoding="utf-8")


VFX_HOST_CSS = "position:absolute;left:0;top:0;width:{w}px;height:{h}px"


def apply_vfx(project: Path, inst: dict, spec: dict, root: dict) -> None:
    """data-vfx-chain on the target element. Kernels that read their own layer
    need the layer inside a layoutsubtree canvas with an explicit pixel box."""
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    ident = sel_id(inst["target"])
    chain = {"version": 1, "nodes": [grading_value(n, inst["params"]) for n in spec["vfx"]["nodes"]]}
    for node in chain["nodes"]:
        node["id"] = f"{inst['iid']}{node['id']}".replace("-", "")
    value = json.dumps(chain, separators=(",", ":"))
    text = edit_open_tag(text, ident, lambda tag: set_attr(add_class(tag, ["fx", f"fx-{inst['effect']}", f"fx-i-{inst['iid']}"]),
                                                           "data-vfx-chain", value))
    if spec["vfx"].get("capture") == "self":
        spans = element_spans(text)
        s = spans[ident]
        inner = text[s["open_end"]:s["close_start"]]
        w, h = int(root["width"]), int(root["height"])
        wrapped = (f'\n<canvas layoutsubtree class="hf-vfx-src" width="{w}" height="{h}">'
                   f'<div class="hf-vfx-in" style="position:relative;width:{w}px;height:{h}px">{inner}</div></canvas>\n')
        inst["vfx_wrapped_inner"] = inner
        text = text[:s["open_end"]] + wrapped + text[s["close_start"]:]
    index.write_text(text, encoding="utf-8")


def remove_vfx(project: Path, inst: dict) -> None:
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    ident = sel_id(inst["target"])
    if "vfx_wrapped_inner" in inst:
        spans = element_spans(text)
        s = spans[ident]
        text = text[:s["open_end"]] + inst["vfx_wrapped_inner"] + text[s["close_start"]:]
    text = edit_open_tag(text, ident, lambda tag: set_attr(remove_class(tag, ["fx", f"fx-{inst['effect']}", f"fx-i-{inst['iid']}"]),
                                                           "data-vfx-chain", None))
    index.write_text(text, encoding="utf-8")


TL_LINE_RE = re.compile(r"(const|let|var)\s+tl\s*=\s*gsap\.timeline\(\s*\{\s*paused:\s*true\s*\}\s*\)\s*;")
SHADER_RE = re.compile(r"/\* fx:shader \*/.*?/\* /fx:shader \*/", re.S)


def write_shader_block(project: Path, data: dict) -> None:
    """One HyperShader.init call owns every scene and shader transition."""
    effects = library()
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    items = [i for i in data["instances"] if effects[i["effect"]]["implementation_route"] == "hf-shader-transition"]
    if not items:
        if SHADER_RE.search(text):
            text = SHADER_RE.sub(data.get("shader_original_line", "const tl = gsap.timeline({ paused: true });"), text)
            text = text.replace('    <script src="assets/vendor/hyper-shader.js"></script>\n', "")
        index.write_text(text, encoding="utf-8")
        return
    scenes: list[str] = []
    for i in sorted(items, key=lambda x: x["start"]):
        for s in (sel_id(i["from"]), sel_id(i["to"])):
            if s not in scenes:
                scenes.append(s)
    spans = element_spans(text)
    for s in scenes:
        tag = text[spans[s]["start"]:spans[s]["open_end"]] if s in spans else ""
        if "scene" not in (get_attr(tag, "class") or "").split():
            fail(EXIT_REFUSED, "blocked", f"shader transitions need each scene to carry class=\"scene\": #{s}")
        if "background-color" not in (get_attr(tag, "style") or ""):
            fail(EXIT_REFUSED, "blocked", f"shader transitions need an explicit background-color on #{s}",
                 fix="set the same colour as the transition's bgColor")
    transitions = []
    for i in sorted(items, key=lambda x: x["start"]):
        entry = {"time": round(i["start"], 4), "duration": round(i["duration"], 4)}
        if effects[i["effect"]].get("shader"):
            entry["shader"] = effects[i["effect"]]["shader"]  # no shader: HyperShader's CSS crossfade
        transitions.append(entry)
    bg = items[0]["params"].get("_bg", None)
    config = {"bgColor": data.get("shader_bg", "#000000"), "accentColor": data.get("shader_accent", "#ffffff"),
              "scenes": scenes, "transitions": transitions}
    call = f"/* fx:shader */ const tl = HyperShader.init({json.dumps(config)}); /* /fx:shader */"
    if SHADER_RE.search(text):
        text = SHADER_RE.sub(lambda m: call, text)
    else:
        m = TL_LINE_RE.search(text)
        if not m:
            fail(EXIT_REFUSED, "blocked", "shader transitions replace the composition's `const tl = gsap.timeline({ paused: true });` line, and none was found",
                 fix="author the main timeline with that line, or use an original transition instead")
        data["shader_original_line"] = m.group(0)
        text = text[:m.start()] + call + text[m.end():]
    if "assets/vendor/hyper-shader.js" not in text:
        text = re.sub(r'(<script src="[^"]*gsap\.min\.js"></script>\n)',
                      lambda mm: mm.group(1) + '    <script src="assets/vendor/hyper-shader.js"></script>\n', text, count=1)
    index.write_text(text, encoding="utf-8")
    src = shader_source()
    if src is None:
        fail(EXIT_REFUSED, "needs_setup", "the pinned toolchain has no shader-transitions build; the owner reruns setup --install-cli")
    copy_if_changed(src, project / "assets/vendor/hyper-shader.js")
    register_asset(project, "assets/vendor/hyper-shader.js", *REGISTER_LINES["assets/vendor/hyper-shader.js"])
    del bg


def split_text(project: Path, inst: dict, mode: str) -> None:
    """Wrap each character or word of the target in a span the effect can animate."""
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    ident = sel_id(inst["target"])
    s = element_spans(text)[ident]
    inner = text[s["open_end"]:s["close_start"]]
    if "<" in inner:
        fail(EXIT_REFUSED, "blocked", f"#{ident} must contain plain text only for a text effect")
    words = _html.unescape(inner).strip().split()
    pieces = []
    for wi, word in enumerate(words):
        if mode == "chars":
            chars = "".join(f'<span class="fx-{inst["iid"]}-ch" style="display:inline-block">{_html.escape(c)}</span>' for c in word)
            pieces.append(f'<span class="fx-{inst["iid"]}-word" style="display:inline-block;white-space:nowrap">{chars}</span>')
        else:
            pieces.append(f'<span class="fx-{inst["iid"]}-word" style="display:inline-block">{_html.escape(word)}</span>')
    inst["text_original"] = inner
    new = " ".join(pieces)
    text = text[:s["open_end"]] + new + text[s["close_start"]:]
    index.write_text(text, encoding="utf-8")


def unsplit_text(project: Path, inst: dict) -> None:
    index = project / "index.html"
    text = index.read_text(encoding="utf-8")
    ident = sel_id(inst["target"])
    s = element_spans(text)[ident]
    text = text[:s["open_end"]] + inst["text_original"] + text[s["close_start"]:]
    index.write_text(text, encoding="utf-8")


def new_iid(data: dict, effect_id: str) -> str:
    used = {i["iid"] for i in data["instances"]}
    stem = re.sub(r"[^a-z0-9]", "", effect_id)[:10] or "fx"
    n = 1
    while f"{stem}{n}" in used:
        n += 1
    return f"{stem}{n}"


def cmd_apply(args: list[str]) -> int:
    if not args:
        fail(EXIT_USAGE, "blocked", "apply needs a project folder")
    project = find_project(args.pop(0))
    effect_id = take(args, "--effect")
    if not effect_id:
        fail(EXIT_USAGE, "blocked", "apply needs --effect")
    spec = get_effect(effect_id)
    status = status_of(spec)
    allow_unverified = take_flag(args, "--allow-unverified")
    if status not in {"verified", "limited"} and not allow_unverified:
        fail(EXIT_REFUSED, "blocked", f"{effect_id} is {status}, not verified",
             fix="use a verified effect, or run fx.py verify on it first")
    target, src_from, src_to = take(args, "--target"), take(args, "--from"), take(args, "--to")
    container = take(args, "--container")
    iid = take(args, "--iid")
    given = parse_kv(take_all(args, "--param"))
    animate = parse_animate(spec, take_all(args, "--animate"))
    text = (project / "index.html").read_text(encoding="utf-8")
    root = root_info(text)
    start = float(take(args, "--at", "0"))
    duration = float(take(args, "--duration", str(spec.get("default_duration", root["duration"] - start))))
    if args:
        fail(EXIT_USAGE, "blocked", f"unknown arguments: {' '.join(args)}")
    if start < 0 or duration <= 0 or start + duration > root["duration"] + 1e-6:
        fail(EXIT_REFUSED, "blocked", f"the window {start}..{start + duration} s is outside the composition (0..{root['duration']} s)")
    needs = spec.get("target", "wrapper")
    if needs in {"wrapper", "media", "text", "element", "composite", "audio"} and not target:
        fail(EXIT_USAGE, "blocked", f"{effect_id} needs --target #id ({needs})")
    if needs == "scene-pair" and not (src_from and src_to):
        fail(EXIT_USAGE, "blocked", f"{effect_id} is a transition and needs --from #scene --to #scene")
    if needs == "composite" and not (target and src_to):
        fail(EXIT_USAGE, "blocked", f"{effect_id} arranges two layers and needs --target #main --to #second")
    for s in (target, src_from, src_to, container):
        if s and sel_id(s) not in element_spans(text):
            fail(EXIT_REFUSED, "blocked", f"{s} is not an element in the composition")
    for extra in spec.get("needs_elements", []):
        if f"--{extra}" not in sys.argv and extra not in given:
            pass
    data = load_instances(project)
    iid = iid or new_iid(data, effect_id)
    if not re.fullmatch(r"[a-z][a-z0-9]{0,23}", iid):
        fail(EXIT_USAGE, "blocked", "--iid is lowercase letters and digits, starting with a letter")
    if any(i["iid"] == iid for i in data["instances"]):
        fail(EXIT_REFUSED, "blocked", f"instance id {iid} is already used")
    params = resolve_params(spec, given)
    inst = {"iid": iid, "effect": effect_id, "route": spec["implementation_route"], "target": target,
            "from": src_from, "to": src_to, "container": container, "start": start, "duration": duration,
            "params": params, "animate": animate, "applied_at": now_iso(), "effect_status_at_apply": status}
    route = spec["implementation_route"]
    if route in {"hf-media-treatment", "hf-color-grade"}:
        element = sel_id(target)
        tag = text[element_spans(text)[element]["start"]:element_spans(text)[element]["open_end"]]
        if not re.match(r"<(video|img)\b", tag):
            fail(EXIT_REFUSED, "blocked", f"{effect_id} applies to a <video> or <img> element, not {target}")
        if element not in data["grading_base"]:
            data["grading_base"][element] = get_attr(tag, "data-color-grading")
        inst["grading_element"] = element
    if route == "hf-audio-fx":
        element = sel_id(target)
        tag = text[element_spans(text)[element]["start"]:element_spans(text)[element]["open_end"]]
        if not re.match(r"<(audio|video)\b", tag):
            fail(EXIT_REFUSED, "blocked", f"{effect_id} applies to an <audio> or <video> element, not {target}")
        data.setdefault("fx_chain_base", {}).setdefault(element, get_attr(tag, "data-fx-chain"))
        inst["audio_element"] = element
    data["instances"].append(inst)
    if route == "hf-audio-fx":
        write_fx_chain(project, data, inst["audio_element"])
    if route in {"hf-media-treatment", "hf-color-grade"}:
        write_grading(project, data, inst["grading_element"])
    elif route == "hf-vfx-chain" and not spec.get("vfx_in_markup"):
        apply_vfx(project, inst, spec, root)
    elif route == "hf-shader-transition":
        write_shader_block(project, data)
    if spec.get("text_split"):
        split_text(project, inst, spec["text_split"])
    if route not in {"hf-media-treatment", "hf-color-grade", "hf-vfx-chain", "hf-shader-transition", "hf-audio-fx"} and target:
        index = project / "index.html"
        index.write_text(edit_open_tag(index.read_text(encoding="utf-8"), sel_id(target),
                                       lambda tag: add_class(tag, ["fx", f"fx-{effect_id}", f"fx-i-{iid}"])), encoding="utf-8")
    save_instances(project, data)
    summary = sync_project(project, data)
    out({"status": "applied", "iid": iid, "effect": effect_id, "route": route, "window": [start, start + duration],
         "params": params, "animate": animate, **summary})
    return 0


def cmd_remove(args: list[str]) -> int:
    if not args:
        fail(EXIT_USAGE, "blocked", "remove needs a project folder")
    project = find_project(args.pop(0))
    iid = take(args, "--iid")
    data = load_instances(project)
    match = [i for i in data["instances"] if i["iid"] == iid]
    if not match:
        fail(EXIT_USAGE, "blocked", f"no instance {iid}", instances=[i["iid"] for i in data["instances"]])
    inst = match[0]
    data["instances"] = [i for i in data["instances"] if i["iid"] != iid]
    route = inst["route"]
    if route == "hf-audio-fx":
        write_fx_chain(project, data, inst["audio_element"])
    if route in {"hf-media-treatment", "hf-color-grade"}:
        write_grading(project, data, inst["grading_element"])
    elif route == "hf-vfx-chain" and not library().get(inst["effect"], {}).get("vfx_in_markup"):
        remove_vfx(project, inst)
    elif route == "hf-shader-transition":
        write_shader_block(project, data)
    if "text_original" in inst:
        unsplit_text(project, inst)
    if route not in {"hf-media-treatment", "hf-color-grade", "hf-vfx-chain", "hf-shader-transition", "hf-audio-fx"} and inst.get("target"):
        index = project / "index.html"
        index.write_text(edit_open_tag(index.read_text(encoding="utf-8"), sel_id(inst["target"]),
                                       lambda tag: remove_class(tag, ["fx", f"fx-{inst['effect']}", f"fx-i-{iid}"])), encoding="utf-8")
    save_instances(project, data)
    summary = sync_project(project, data)
    out({"status": "removed", "iid": iid, **summary})
    return 0


def cmd_instances(args: list[str]) -> int:
    project = find_project(args[0] if args else ".")
    out(load_instances(project))
    return 0


# ---------------------------------------------------------------- checks

HEAVY_COST = 2.0
COST_BUDGET = 4.0
CONFLICTS = [
    ({"hf-shader-transition"}, "vfx-self",
     "HyperFrames documents a conflict between page-side shader transitions and a capturing data-vfx-chain node: the chain can paint from a stale texture"),
]


def cmd_stack_check(args: list[str]) -> int:
    project = find_project(args[0] if args else ".")
    data = load_instances(project)
    effects = library()
    problems, warnings = [], []
    total = 1.0
    routes = set()
    by_target: dict[str, list[str]] = {}
    for inst in data["instances"]:
        spec = effects.get(inst["effect"])
        if spec is None:
            problems.append(f"{inst['iid']}: effect {inst['effect']} is not in the library")
            continue
        entry = public_entry(spec)
        cost = float(entry.get("render_cost_multiplier") or 1.0)
        total *= max(cost, 1.0)
        routes.add(spec["implementation_route"])
        if spec.get("vfx", {}).get("capture") == "self":
            routes.add("vfx-self")
        if entry["status"] not in {"verified", "limited"}:
            problems.append(f"{inst['iid']}: {inst['effect']} is {entry['status']}, not verified")
        if entry.get("photosensitivity") == "fail":
            problems.append(f"{inst['iid']}: {inst['effect']} failed the photosensitivity check at its verified range")
        if cost >= HEAVY_COST:
            warnings.append(f"{inst['iid']}: {inst['effect']} roughly multiplies capture time by {cost}")
        by_target.setdefault(inst.get("target") or inst.get("from") or "composition", []).append(inst["effect"])
    writers: dict[tuple[str, str], list[str]] = {}
    for inst in data["instances"]:
        spec = effects.get(inst["effect"]) or {}
        for prop in spec.get("writes", []):
            writers.setdefault((inst.get("target") or "", prop), []).append(inst["iid"])
    for (where, prop), iids in writers.items():
        if len(iids) > 1:
            problems.append(f"{', '.join(iids)} all set {prop} on {where}; wrap the layer once per move, or pick one")
    for need, other, why in CONFLICTS:
        if need <= routes and other in routes:
            problems.append(why)
    shader = any(effects[i["effect"]]["implementation_route"] == "hf-shader-transition" for i in data["instances"] if i["effect"] in effects)
    original_transitions = [i for i in data["instances"] if i["effect"] in effects
                            and effects[i["effect"]]["family"] == "transitions"
                            and effects[i["effect"]]["implementation_route"] != "hf-shader-transition"]
    if shader:
        shader_scenes = {s for i in data["instances"] if i["effect"] in effects
                         and effects[i["effect"]]["implementation_route"] == "hf-shader-transition" for s in (i["from"], i["to"])}
        for i in original_transitions:
            if i["from"] in shader_scenes or i["to"] in shader_scenes:
                problems.append(f"{i['iid']}: an original transition on a scene HyperShader manages; use one transition system per scene")
    if total > COST_BUDGET:
        warnings.append(f"stacked capture-time multiplier is about {round(total, 2)}, over the budget of {COST_BUDGET}")
    hdr = (project.parent / "hdr-working-copy.yaml").is_file()
    out({"tool": "fx stack-check", "version": TOOL_VERSION, "project": str(project), "instances": len(data["instances"]),
         "estimated_capture_multiplier": round(total, 2), "budget": COST_BUDGET, "per_target": by_target,
         "sdr_working_copy_recorded": hdr, "problems": problems, "warnings": warnings,
         "result": "fail" if problems else ("warn" if warnings else "pass")})
    return EXIT_CHECK if problems else 0


def _flow_map(value):
    """`{a: 1, b: x}` as a dict, for when PyYAML is absent and the subset
    parser hands an inline map back as text."""
    if isinstance(value, dict) or not isinstance(value, str):
        return value
    text = value.strip()
    if not (text.startswith("{") and text.endswith("}")):
        return value
    out = {}
    for part in filter(None, (s.strip() for s in text[1:-1].split(","))):
        key, _, raw = part.partition(":")
        raw = raw.strip().strip("'\"")
        try:
            out[key.strip()] = float(raw) if raw else None
        except ValueError:
            out[key.strip()] = raw
    return out


def _load_plan(path: Path) -> dict:
    sys.path.insert(0, str(LAUNCHER.parent))
    from editor_tools import load_data  # noqa: E402
    plan = load_data(path)
    for item in plan.get("effects") or []:
        if isinstance(item, dict):
            for key in ("params", "animate"):
                item[key] = _flow_map(item.get(key))
    return plan


def cmd_check_plan(args: list[str]) -> int:
    if not args:
        fail(EXIT_USAGE, "blocked", "check-plan needs an effect-plan.yaml")
    path = Path(args[0])
    plan = _load_plan(path)
    effects = library()
    problems, warnings = [], []
    for field in ("plan_id", "project_id", "effect_approver", "photosensitivity_budget", "effects"):
        if plan.get(field) in (None, "", []):
            problems.append(f"missing {field}")
    hdr = str(plan.get("hdr_sources", "")).lower()
    if hdr in {"yes", "true"} and not plan.get("sdr_working_copy_approved_by"):
        problems.append("HDR sources are present: effects do not reach native HDR layers; record the owner's approval of an SDR working copy (sdr_working_copy_approved_by)")
    for i, item in enumerate(plan.get("effects") or []):
        eid = (item or {}).get("effect_id")
        where = f"effects[{i}] {eid}"
        if eid not in effects:
            problems.append(f"{where}: not in the library")
            continue
        spec = effects[eid]
        entry = public_entry(spec)
        if entry["status"] not in {"verified", "limited"}:
            problems.append(f"{where}: status is {entry['status']}")
        if entry["status"] == "limited":
            warnings.append(f"{where}: limited; read its verification record before relying on it")
        specs = param_specs(spec)
        for k, v in ((item.get("params") or {}).items()):
            if k not in specs:
                problems.append(f"{where}: unknown parameter {k}")
                continue
            try:
                fv = float(v)
            except (TypeError, ValueError):
                problems.append(f"{where}: {k} is not a number")
                continue
            if not specs[k]["min"] <= fv <= specs[k]["max"]:
                problems.append(f"{where}: {k}={fv} is outside the verified range {specs[k]['min']}..{specs[k]['max']}")
        if entry.get("photosensitivity") == "fail":
            problems.append(f"{where}: failed the photosensitivity check")
        if spec.get("needs_key_footage") and not item.get("key_footage_confirmed"):
            warnings.append(f"{where}: needs footage shot for keying; confirm the source has a clean, even backdrop")
        if spec.get("face_safe") is False and str(item.get("faces_in_shot", "")).lower() in {"yes", "true"}:
            warnings.append(f"{where}: distorts faces; get the subject's consent or keep it off faces")
    out({"tool": "fx check-plan", "version": TOOL_VERSION, "plan": str(path), "problems": problems,
         "warnings": warnings, "result": "fail" if problems else "pass"})
    return EXIT_CHECK if problems else 0


# ---------------------------------------------------------------- photosensitivity

def _lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


LIN = [_lin(i) for i in range(256)]


def video_info(path: Path) -> dict:
    proc = subprocess.run([need("ffprobe"), "-v", "error", "-select_streams", "v:0", "-show_entries",
                           "stream=width,height,r_frame_rate,nb_frames,duration", "-of", "json", str(path)],
                          capture_output=True, text=True, timeout=120)
    s = json.loads(proc.stdout or "{}").get("streams", [{}])[0]
    num, _, den = (s.get("r_frame_rate") or "30/1").partition("/")
    return {"width": int(s.get("width", 0)), "height": int(s.get("height", 0)),
            "fps": float(num) / float(den or 1)}


def frames_rgb(path: Path, w: int, h: int, fps: float | None = None) -> list[bytes]:
    vf = f"scale={w}:{h}:flags=area"
    if fps:
        vf = f"fps={fps}," + vf
    proc = subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path),
                           "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=1800)
    size = w * h * 3
    data = proc.stdout
    return [data[i:i + size] for i in range(0, len(data) - size + 1, size)]


def _uv(r: float, g: float, b: float) -> tuple[float, float]:
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    d = x + 15 * y + 3 * z
    return (4 * x / d, 9 * y / d) if d > 0 else (0.0, 0.0)


def flash_analysis(path: Path, display_short_side: int = 768) -> dict:
    """WCAG 2.3.1 general and red flash analysis.

    The frame is mapped onto a display whose short side is
    `display_short_side` CSS px (768 by default, the WCAG reference screen
    height; on a phone the same video covers fewer CSS px, so this is the
    stricter reading). It is split into cells one eighth of the 341 x 256 CSS
    px field across, and each cell's relative luminance is followed over time.

    A cell transition is one monotonic run of luminance that moves at least 10%
    of maximum relative luminance with its darker end below 0.80. A field
    transition happens when, within the same frame or the next, the cells making
    a transition in one direction outnumber those going the other way by at
    least 25% of some 341 x 256 field. This net-area rule is this profile's
    reading of "the combined area of flashes occurring concurrently", not WCAG
    text: stripes sliding through a field brighten one part while another
    darkens, so the field as a whole does not flash. A small area flickering
    faster than three flashes a second still produces a warning. A flash is a pair of opposing field
    transitions. More than three flashes in any one second fails.

    Red flashes are the same, with a cell transition defined by the WCAG 2.2
    working definition: one end has R/(R+G+B) >= 0.8 and the CIE 1976 u'v'
    chromaticity moves more than 0.2."""
    info = video_info(path)
    if not info["width"]:
        return {"result": "error", "message": f"could not read {path}"}
    fps = info["fps"]
    scale = display_short_side / min(info["width"], info["height"])
    css_w, css_h = info["width"] * scale, info["height"] * scale
    fw, fh = WCAG["field_block_css_px"]
    gw = max(1, round(css_w / (fw / 8)))
    gh = max(1, round(css_h / (fh / 8)))
    frames = frames_rgb(path, gw, gh)
    n = len(frames)
    cells = gw * gh
    lum = [[0.0] * n for _ in range(cells)]
    redness = [[0.0] * n for _ in range(cells)]
    uv = [[(0.0, 0.0)] * n for _ in range(cells)]
    for f, frame in enumerate(frames):
        for c in range(cells):
            r, g, b = frame[3 * c], frame[3 * c + 1], frame[3 * c + 2]
            lr, lg, lb = LIN[r], LIN[g], LIN[b]
            lum[c][f] = 0.2126 * lr + 0.7152 * lg + 0.0722 * lb
            s = r + g + b
            redness[c][f] = r / s if s else 0.0
            uv[c][f] = _uv(lr, lg, lb)

    def general_events(series: list[float]) -> list[tuple[int, int]]:
        events = []
        if not series:
            return events
        run_start, direction, counted, deadband = series[0], 0, False, 0.003
        for i in range(1, len(series)):
            d = series[i] - series[i - 1]
            sign = 0 if abs(d) < deadband else (1 if d > 0 else -1)
            if sign and direction and sign != direction:
                run_start, counted = series[i - 1], False
            if sign:
                direction = sign
            darker = min(series[i], run_start)
            if not counted and abs(series[i] - run_start) >= WCAG["general_flash_min_change"] \
                    and darker < WCAG["general_flash_darker_below"]:
                events.append((i, direction))
                counted = True
        return events

    def red_events(c: int) -> list[tuple[int, int]]:
        events = []
        anchor = 0
        for i in range(1, n):
            involved = redness[c][i] >= WCAG["red_ratio_at_least"] or redness[c][anchor] >= WCAG["red_ratio_at_least"]
            du = uv[c][i][0] - uv[c][anchor][0]
            dv = uv[c][i][1] - uv[c][anchor][1]
            if involved and math.sqrt(du * du + dv * dv) > WCAG["red_chromaticity_change_more_than"]:
                events.append((i, 1 if redness[c][i] >= WCAG["red_ratio_at_least"] else -1))
                anchor = i
            elif not involved:
                anchor = i
        return events

    per_cell = {"general": [general_events(lum[c]) for c in range(cells)],
                "red": [red_events(c) for c in range(cells)]}
    side = 8
    need = math.ceil(side * side * WCAG["area_fraction_of_field"])
    xs = list(range(0, max(1, gw - side + 1), 2)) or [0]
    ys = list(range(0, max(1, gh - side + 1), 2)) or [0]
    if gw > side and xs[-1] != gw - side:
        xs.append(gw - side)
    if gh > side and ys[-1] != gh - side:
        ys.append(gh - side)
    win = max(1, int(round(fps)))
    report = {}
    for kind, events in per_cell.items():
        # cell -> frame -> direction, for fast lookup
        at = [dict(ev) for ev in events]
        worst = {"flashes": 0.0, "area_fraction": 0.0, "at": None, "field": None}
        busiest_cell = 0
        for ev in events:
            frames_of = [e[0] for e in ev]
            for i, f0 in enumerate(frames_of):
                busiest_cell = max(busiest_cell, sum(1 for f1 in frames_of[i:] if f1 - f0 < win))
        for y0 in ys:
            for x0 in xs:
                field = [y * gw + x for y in range(y0, min(gh, y0 + side)) for x in range(x0, min(gw, x0 + side))]
                field_events = []
                peak_area = 0
                for f in range(1, n):
                    up = sum(1 for c in field if at[c].get(f) == 1 or at[c].get(f + 1) == 1)
                    down = sum(1 for c in field if at[c].get(f) == -1 or at[c].get(f + 1) == -1)
                    for direction, k in ((1, up - down), (-1, down - up)):
                        peak_area = max(peak_area, k)
                        if k >= need and not (field_events and field_events[-1][1] == direction and f - field_events[-1][0] <= 2):
                            field_events.append((f, direction))
                # opposing field transitions inside any one-second window
                for s0 in range(0, max(1, n - win + 1)):
                    inside_ev = [e for e in field_events if s0 < e[0] <= s0 + win]
                    opposing = sum(1 for a, b in zip(inside_ev, inside_ev[1:]) if a[1] != b[1])
                    flashes = (opposing + 1) / 2 if opposing else 0.0
                    frac = round(peak_area / (side * side), 3)
                    if (flashes, frac) > (worst["flashes"], worst["area_fraction"]):
                        worst = {"flashes": flashes, "area_fraction": frac, "at": round(s0 / fps, 3), "field": [x0, y0]}
        worst["busiest_cell_transitions"] = busiest_cell  # in any one-second window
        report[kind] = worst
    over = any(report[k]["flashes"] > WCAG["max_flashes_per_second"] for k in report)
    small = any(report[k]["busiest_cell_transitions"] > 2 * WCAG["max_flashes_per_second"] for k in report)
    near = small or any(report[k]["flashes"] >= 2 for k in report)
    result = "fail" if over else ("warn" if near else "pass")
    return {"tool": "fx flash-check", "version": TOOL_VERSION, "file": str(path), "frames": n, "fps": fps,
            "display_short_side_css_px": display_short_side, "grid_cells": [gw, gh], "criteria": WCAG,
            "general": report["general"], "red": report["red"], "result": result,
            "small_area_flicker": small,
            "note": "warn: two or more concurrent flashes in a second somewhere, or a small area flickering faster than three "
                    "flashes a second. Under the WCAG limit, but a person should look."}


def cmd_flash_check(args: list[str]) -> int:
    short = int(take(args, "--display-short-side", "768"))
    if not args:
        fail(EXIT_USAGE, "blocked", "flash-check needs a video file")
    report = flash_analysis(Path(args[0]), short)
    out(report)
    return EXIT_CHECK if report["result"] == "fail" else 0


# ---------------------------------------------------------------- stills

def still(path: Path, t: float, dest: Path, width: int | None = None) -> None:
    vf = [f"select='gte(t\\,{t:.4f})'"]
    if width:
        vf.append(f"scale={width}:-2")
    subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", str(path),
                    "-vf", ",".join(vf), "-frames:v", "1", "-q:v", "3", str(dest)], check=True, timeout=300)


def strip(images: list[Path], dest: Path) -> None:
    inputs = []
    for img in images:
        inputs += ["-i", str(img)]
    graph = "".join(f"[{i}:v]" for i in range(len(images))) + f"hstack=inputs={len(images)}"
    if len(images) == 1:
        graph = "[0:v]null"
    subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *inputs,
                    "-filter_complex", graph, "-q:v", "4", str(dest)], check=True, timeout=300)


def cmd_contact_sheet(args: list[str]) -> int:
    dest = take(args, "--out")
    at = take(args, "--at")
    if not args or not dest:
        fail(EXIT_USAGE, "blocked", "contact-sheet needs a video and --out")
    video = Path(args[0])
    times = [float(x) for x in at.split(",")] if at else [0.25, 0.5, 0.75]
    with tempfile.TemporaryDirectory() as tmp:
        shots = []
        for i, t in enumerate(times):
            p = Path(tmp) / f"s{i}.png"
            still(video, t, p, 320)
            shots.append(p)
        strip(shots, Path(dest))
    out({"status": "written", "file": dest, "times": times})
    return 0


# ---------------------------------------------------------------- verification

FPS = 30
DUR = 2.0
SIZE = (320, 180)
ANIM_TIMES = (0.3, 1.0, 1.7)
DIFF_MIN = 1.0          # mean absolute difference, 0-255 scale: an effect must change the picture at least this much
REPEAT_TOL = 0.0        # renders of the same composition must match exactly (lossless encode)
SEEK_TOL = 0.0
ANIM_TOL = 0.75         # keyframe interpolation at a sampled time may differ by sub-LSB rounding
FIDELITY_TOL = 1.5     # fast capture against screenshot capture: anti-aliasing differences only


FIXTURE_HEAD = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={w}, height={h}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {w}px; height: {h}px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: {w}px; height: {h}px; overflow: hidden; background: #000; }}
      .layer {{ position: absolute; left: 0; top: 0; width: {w}px; height: {h}px; overflow: hidden; }}
      video {{ position: absolute; left: 0; top: 0; width: {w}px; height: {h}px; object-fit: cover; }}
      .title {{ position: absolute; left: 0; right: 0; top: {ty}px; text-align: center; color: #fff;
               font: 700 {fs}px/1.1 Helvetica, Arial, sans-serif; letter-spacing: 0;
               background: rgba(11, 11, 11, 0.8); padding: 4px 0; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="{w}" data-height="{h}">
{body}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def fixture_media(project: Path, cache: Path | None = None) -> None:
    """Synthetic sources only: generated here, known content, no rights questions.
    Generated once per gate run into `cache` and copied, so every variant of a
    gate renders the exact same source pixels."""
    w, h = SIZE
    assets = project / "assets"
    assets.mkdir(exist_ok=True)
    names = ["clip-a.mp4", "clip-b.mp4", "green.mp4", "blue.mp4", "still.png"]
    if cache is not None and all((cache / n).is_file() for n in names):
        for n in names:
            shutil.copy2(cache / n, assets / n)
        _register_fixture(project, names)
        return
    ff = [need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "10", "-pix_fmt", "yuv420p", "-g", "30", "-an"]
    d = DUR + 0.5
    # Calm on purpose: slow gradients, still test bars, a slowly moving block.
    # Nothing in the sources flashes, so a flash in a render comes from the effect.
    # (In drawbox, `t` is the box thickness, so moving shapes go in through overlay.)
    jobs = {
        "clip-a.mp4": ["-f", "lavfi", "-i", f"gradients=s={w}x{h}:c0=0x1d3557:c1=0xe9c46a:x0=0:y0=0:x1={w}:y1={h}:speed=0.004:seed=1:rate={FPS}:duration={d}",
                       "-f", "lavfi", "-i", f"smptehdbars=s=128x72:rate={FPS}:duration={d}",
                       "-f", "lavfi", "-i", f"color=c=0x2b3a4a:s=128x60:r={FPS}:d={d},drawbox=x=10:y=10:w=90:h=8:color=0xa8b8c8:t=fill,"
                                             "drawbox=x=10:y=26:w=70:h=8:color=0xa8b8c8:t=fill,drawbox=x=10:y=42:w=100:h=8:color=0xa8b8c8:t=fill",
                       "-f", "lavfi", "-i", f"color=c=0xd9a07a:s=72x92:r={FPS}:d={d},drawbox=x=12:y=24:w=48:h=10:color=0x3a2a20:t=fill,"
                                             "drawbox=x=18:y=66:w=36:h=6:color=0x8a3b3b:t=fill",
                       "-filter_complex", "[0:v][1:v]overlay=x=176:y=16[a];[a][2:v]overlay=x=176:y=104[b];"
                                          "[b][3:v]overlay=x='40+14*sin(t)':y=46,format=yuv420p,"
                                          "drawbox=x=16:y=150:w=150:h=4:color=white:t=fill,drawbox=x=16:y=160:w=104:h=4:color=white:t=fill"],
        "clip-b.mp4": ["-f", "lavfi", "-i", f"gradients=s={w}x{h}:c0=0x2a9d8f:c1=0x6d2e46:x0={w}:y0=0:x1=0:y1={h}:speed=0.004:seed=2:rate={FPS}:duration={d}",
                       "-f", "lavfi", "-i", f"color=c=0xf4f1de:s=90x90:r={FPS}:d={d},drawbox=x=14:y=14:w=62:h=62:color=0xe76f51:t=fill",
                       "-filter_complex", "[0:v][1:v]overlay=x='200-20*t':y=40,format=yuv420p,"
                                          "drawbox=x=0:y=150:w=320:h=30:color=0x1b1b1b:t=fill,drawbox=x=20:y=160:w=60:h=10:color=0xf4a261:t=fill,"
                                          "drawbox=x=96:y=160:w=60:h=10:color=0x2a9d8f:t=fill"],
        "green.mp4": ["-f", "lavfi", "-i", f"color=c=0x1fb84a:s={w}x{h}:r={FPS}:d={d}",
                      "-f", "lavfi", "-i", f"color=c=0xd9a07a:s=80x150:r={FPS}:d={d},drawbox=x=0:y=0:w=80:h=22:color=0x3a2a20:t=fill,"
                                            "drawbox=x=18:y=40:w=44:h=8:color=0x3a2a20:t=fill,drawbox=x=0:y=84:w=80:h=66:color=0x2050c0:t=fill",
                      "-filter_complex", "[0:v][1:v]overlay=x='120+30*sin(t)':y=30,format=yuv420p"],
        "blue.mp4": ["-f", "lavfi", "-i", f"color=c=0x1d3fbb:s={w}x{h}:r={FPS}:d={d}",
                     "-f", "lavfi", "-i", f"color=c=0xd9a07a:s=80x150:r={FPS}:d={d},drawbox=x=0:y=0:w=80:h=22:color=0x3a2a20:t=fill,"
                                           "drawbox=x=18:y=40:w=44:h=8:color=0x3a2a20:t=fill,drawbox=x=0:y=84:w=80:h=66:color=0xb83a3a:t=fill",
                     "-filter_complex", "[0:v][1:v]overlay=x='120+30*sin(t)':y=30,format=yuv420p"],
    }
    for name, src in jobs.items():
        subprocess.run([*ff, *src, *enc, str(assets / name)], check=True, timeout=600)
    subprocess.run([*ff, "-ss", "1", "-i", str(assets / "clip-a.mp4"), "-frames:v", "1",
                    str(assets / "still.png")], check=True, timeout=120)
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        for n in names:
            shutil.copy2(assets / n, cache / n)
    _register_fixture(project, names)


def _register_fixture(project: Path, names: list[str]) -> None:
    register = project / "asset-rights-register.yaml"
    text = register.read_text(encoding="utf-8") if register.is_file() else "assets: []\n"
    text = text.replace("assets: []", "assets:")
    for name in names:
        text += (f"  - asset: assets/{name}\n    source: generated by fx.py verify with FFmpeg lavfi sources\n"
                 f"    license: synthetic test media, no third-party rights\n    proof: fx.py fixture_media\n")
    register.write_text(text, encoding="utf-8")


def video(cid: str, src: str, start: float = 0, dur: float = DUR, track: int = 0, extra: str = "") -> str:
    return (f'<video id="{cid}" src="{src}" data-start="{start}" data-duration="{dur}" data-media-start="0" '
            f'data-track-index="{track}" muted playsinline{extra}></video>')


def fixture_body(spec: dict) -> tuple[str, dict]:
    """The composition the gate renders, and how the effect is applied to it."""
    fixture = spec.get("fixture", "clip")
    w, h = SIZE
    if fixture == "transition":
        body = (f'      <div id="s1" class="scene layer" style="background-color:#000000">{video("va", "assets/clip-a.mp4", track=0)}</div>\n'
                f'      <div id="s2" class="scene layer" style="background-color:#000000">{video("vb", "assets/clip-b.mp4", track=1)}</div>')
        return body, {"from": "#s1", "to": "#s2", "at": 0.6, "duration": 0.8}
    if fixture == "two-clips":
        body = (f'      <div id="w1" class="layer">{video("va", "assets/clip-a.mp4", track=0)}</div>\n'
                f'      <div id="w2" class="layer" style="opacity:0">{video("vb", "assets/clip-b.mp4", track=1)}</div>')
        return body, {"target": "#w1", "to": "#w2"}
    if fixture == "key-blue":
        body = (f'      <div id="bg" class="layer">{video("vb", "assets/clip-b.mp4", track=0)}</div>\n'
                f'      <div id="w1" class="layer">{video("vg", "assets/blue.mp4", track=1)}</div>')
        return body, {"target": "#w1"}
    if fixture == "luma":
        body = (f'      <div id="bg" class="layer">{video("vb", "assets/clip-b.mp4", track=0)}</div>\n'
                f'      <div id="w1" class="layer">{video("va", "assets/clip-a.mp4", track=1)}</div>')
        return body, {"target": "#w1"}
    if fixture == "key":
        body = (f'      <div id="bg" class="layer">{video("vb", "assets/clip-b.mp4", track=0)}</div>\n'
                f'      <div id="w1" class="layer">{video("vg", "assets/green.mp4", track=1)}</div>')
        return body, {"target": "#w1"}
    if fixture == "text":
        body = (f'      <div id="w1" class="layer">{video("va", "assets/clip-a.mp4", track=0)}</div>\n'
                f'      <div id="t1" class="title">Fresh cut ready</div>')
        return body, {"target": "#t1"}
    if fixture == "image":
        body = '      <div id="w1" class="layer"><img id="i1" src="assets/still.png" alt="" style="position:absolute;left:0;top:0;width:100%;height:100%" /></div>'
        return body, {"target": "#i1"}
    body = f'      <div id="w1" class="layer">{video("va", "assets/clip-a.mp4", track=0)}</div>'
    target = "#va" if spec.get("target") == "media" else "#w1"
    return body, {"target": target}


def write_fixture(project: Path, spec: dict) -> dict:
    body, how = fixture_body(spec)
    w, h = SIZE
    (project / "index.html").write_text(FIXTURE_HEAD.format(w=w, h=h, dur=DUR, body=body, ty=int(h * 0.62), fs=int(h * 0.13)),
                                        encoding="utf-8")
    return how


class Gate:
    def __init__(self, spec: dict, keep: bool):
        self.spec = spec
        self.keep = keep
        self.checks: list[dict] = []
        self.renders: dict[str, dict] = {}
        ws = workspace_root()
        if ws is None:
            fail(EXIT_REFUSED, "needs_setup", "no approved workspace; the owner runs hf.py setup --workspace <folder>")
        stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        self.video_dir = ws / "projects" / f"fx-verify-{spec['effect_id']}-{stamp}"
        self.tmp = Path(tempfile.mkdtemp(prefix="fx-verify-"))

    def check(self, n: int, name: str, ok: bool | None, detail) -> None:
        self.checks.append({"n": n, "check": name, "result": "pass" if ok else ("not-applicable" if ok is None else "fail"),
                            "detail": detail})

    def launcher(self, *args, cwd: Path, sandbox: bool = False, timeout: int = 1800):
        cmd = [sys.executable, str(LAUNCHER), *args]
        if sandbox:
            cmd = network_denied(cmd)
        return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)

    def fx(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=600)

    def new_version(self, name: str) -> Path:
        self.video_dir.mkdir(parents=True, exist_ok=True)
        decision = self.video_dir / "style-decision.yaml"
        if not decision.is_file():
            # The gate renders synthetic test media, not an edit: the outlier
            # study is waived for this one verification project only.
            decision.write_text(
                f"decision_id: SD-FXVERIFY-{self.spec['effect_id']}\nproject_id: {self.video_dir.name}\n"
                "decision: waived\nwaiver_reason: effect verification on synthetic media; not an edit\n"
                "waiver_scope: this_edit\ndecided_by: fx.py verify (gate run requested by the owner)\n"
                f"decided_by_role: owner\ndecided_at: {now_iso()}\n", encoding="utf-8")
        proc = self.launcher("init", name, cwd=self.video_dir, timeout=600)
        project = self.video_dir / name
        if proc.returncode != 0 or not (project / "index.html").is_file():
            raise RuntimeError(f"init failed: {proc.stdout[-800:]} {proc.stderr[-800:]}")
        fixture_media(project, self.tmp / "media")
        return project

    def apply(self, project: Path, how: dict, params: dict | None = None, animate: dict | None = None) -> None:
        args = ["apply", str(project), "--effect", self.spec["effect_id"], "--allow-unverified", "--iid", "fx1"]
        for k in ("target", "from", "to"):
            if how.get(k):
                args += [f"--{k}", how[k]]
        if "at" in how:
            args += ["--at", str(how["at"]), "--duration", str(how["duration"])]
        elif self.spec.get("window"):
            args += ["--at", str(self.spec["window"][0]), "--duration", str(self.spec["window"][1])]
        for k, v in (params or {}).items():
            args += ["--param", f"{k}={fmt(v)}"]
        for k, a in (animate or {}).items():
            args += ["--animate", f"{k}=" + ",".join(f"{fmt(t)}:{fmt(v)}" for t, v in a)]
        proc = self.fx(*args)
        if proc.returncode != 0:
            raise RuntimeError(f"apply failed: {proc.stdout[-600:]} {proc.stderr[-1200:]}")

    def render(self, project: Path, name: str, fps: int = FPS, extra: tuple = ()) -> dict:
        out_rel = f"renders/{name}.mp4"
        t0 = time.time()
        proc = self.launcher("render", "--stage", "draft", "--fps", str(fps), "--crf", "0", "--workers", "1",
                             *extra, "-o", out_rel, cwd=project, sandbox=True, timeout=1800)
        wall = time.time() - t0
        path = project / out_rel
        if proc.returncode != 0 or not path.is_file():
            raise RuntimeError(f"render {name} failed ({proc.returncode}): {proc.stdout[-1500:]} {proc.stderr[-1500:]}")
        # HyperFrames prints "41.2s" under a minute and "1m 3.2s" above it.
        m = re.search(r"capture (?:(\d+)m )?([\d.]+)s", proc.stdout + proc.stderr)
        mode = re.search(r"(screenshot|drawelement|drawElement) capture · ([\w ]+?) ·", proc.stdout + proc.stderr)
        info = {"path": path, "wall_s": round(wall, 2), "capture_s": round(int(m.group(1) or 0) * 60 + float(m.group(2)), 1) if m else None,
                "capture_mode": (mode.group(1) + ", " + mode.group(2)) if mode else None}
        self.renders[name] = info
        return info

    def frames(self, name: str) -> list[bytes]:
        return frames_rgb(self.renders[name]["path"], *SIZE)


def network_denied(cmd: list[str]) -> list[str]:
    """Run a command with outbound network denied, loopback allowed (the render
    talks to its own local file server and browser)."""
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        profile = ("(version 1)(allow default)(deny network-outbound)"
                   '(allow network-outbound (remote ip "localhost:*"))'
                   "(allow network-outbound (remote unix-socket))")
        return ["sandbox-exec", "-p", profile, *cmd]
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        probe = subprocess.run(["unshare", "--user", "--map-root-user", "--net", "true"], capture_output=True)
        if probe.returncode == 0:
            return ["unshare", "--user", "--map-root-user", "--net", "sh", "-c", 'ip link set lo up 2>/dev/null; exec "$@"', "sh", *cmd]
    raise RuntimeError("no way to deny network on this machine (sandbox-exec or unshare --net)")


def mean_abs(a: bytes, b: bytes) -> float:
    if len(a) != len(b) or not a:
        return float("inf")
    step = 7
    total = sum(abs(a[i] - b[i]) for i in range(0, len(a), step))
    return total / len(range(0, len(a), step))


def changed_share(a: bytes, b: bytes, level: int = 24) -> float:
    """Share of pixels where any channel moved by more than `level`."""
    if len(a) != len(b) or not a:
        return 0.0
    n = len(a) // 3
    hit = sum(1 for i in range(0, len(a) - 2, 3)
              if abs(a[i] - b[i]) > level or abs(a[i + 1] - b[i + 1]) > level or abs(a[i + 2] - b[i + 2]) > level)
    return hit / n


SPARSE_SHARE = 0.005   # 0.5% of pixels visibly changed counts as a change, for sparse effects such as specks


def frame_at(frames: list[bytes], t: float, fps: int = FPS) -> bytes:
    return frames[min(len(frames) - 1, int(round(t * fps)))]


def static_scan(project: Path) -> list[str]:
    hits = []
    # Only what the page loads: markup, styles, scripts. Project config files
    # (hyperframes.json names a schema URL and the registry) are never fetched
    # by a preview or a render.
    for p in project.rglob("*"):
        if p.suffix.lower() not in {".html", ".css", ".js", ".mjs", ".svg"} or "renders" in p.parts or ".hyperframes" in p.parts:
            continue
        if p.name in {"gsap.min.js", "hyper-shader.js"}:
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        text = re.sub(r"/\*.*?\*/|<!--.*?-->", "", text, flags=re.S)
        for m in re.finditer(r"(?:https?:)?//[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s\"')]*", text):
            if "w3.org/2000/svg" in m.group(0) or "w3.org/1999/xlink" in m.group(0):
                continue
            hits.append(f"{p.relative_to(project)}: {m.group(0)}")
    return hits


def cmd_verify(args: list[str]) -> int:
    keep = take_flag(args, "--keep")
    if not args:
        fail(EXIT_USAGE, "blocked", "verify needs an effect id")
    spec = get_effect(args[0])
    if spec["family"] == "audio":
        return verify_audio(spec, keep)
    g = Gate(spec, keep)
    params = param_specs(spec)
    defaults = {k: p["default"] for k, p in params.items()}
    mins = {k: p["min"] for k, p in params.items()}
    maxs = {k: p["max"] for k, p in params.items()}
    fixed_extremes = spec.get("verify_extremes", "all")
    if fixed_extremes == "primary" and spec.get("parameters"):
        primary = spec["parameters"][0]["key"]
        mins = {**defaults, primary: params[primary]["min"]}
        maxs = {**defaults, primary: params[primary]["max"]}
    animatable = [k for k, p in params.items() if p.get("animatable")]
    errors = []
    try:
        base = g.new_version("baseline")
        how = write_fixture(base, spec)
        g.render(base, "base")
        variants = {"default": defaults, "min": mins, "max": maxs}
        projects = {}
        for name, values in variants.items():
            proj = g.new_version(name)
            write_fixture(proj, spec)
            g.apply(proj, how, values)
            projects[name] = proj
        anim_key = animatable[0] if animatable else None
        anim_refs = {"min": "min", "max": "max"}
        if anim_key and len(params) > 1:
            # The reference for a keyframe is a static render that differs from
            # default only in the animated parameter.
            for name, value in (("kmin", mins[anim_key]), ("kmax", maxs[anim_key])):
                proj = g.new_version(name)
                write_fixture(proj, spec)
                g.apply(proj, how, {**defaults, anim_key: value})
                projects[name] = proj
            anim_refs = {"min": "kmin", "max": "kmax"}
        if anim_key:
            proj = g.new_version("animated")
            write_fixture(proj, spec)
            g.apply(proj, how, defaults, {anim_key: [(ANIM_TIMES[0], mins[anim_key]), (ANIM_TIMES[1], defaults[anim_key]),
                                                     (ANIM_TIMES[2], maxs[anim_key])]})
            projects["animated"] = proj

        # 1. lint and check
        lint = [g.launcher(cmd, cwd=projects["default"], timeout=600) for cmd in ("lint", "check")]
        g.check(1, "lint and check pass", all(p.returncode == 0 for p in lint),
                {c: {"exit": p.returncode, "tail": (p.stdout + p.stderr)[-400:]} for c, p in zip(("lint", "check"), lint)})

        for name in ("default", "min", "max"):
            g.render(projects[name], name)
        g.render(projects["default"], "repeat")
        # The same composition through HyperFrames' screenshot capture, the
        # path that paints exactly what Chrome's compositor paints.
        g.render(projects["default"], "fidelity", extra=("--experimental-fast-capture=false",))
        g.render(projects["default"], "seek", fps=1)
        if anim_key:
            g.render(projects["animated"], "animated")
            for name in ("kmin", "kmax"):
                if name in projects:
                    g.render(projects[name], name)

        fr = {name: g.frames(name) for name in g.renders}
        # 2. renders at default, min, max
        counts = {k: len(fr[k]) for k in ("default", "min", "max")}
        fid_times = sorted({0.2, 0.5, 1.0, 1.5, round(min(DUR - 0.05, float(spec.get("probe") or 1.0)), 3)})
        fidelity = {str(t): round(mean_abs(frame_at(fr["default"], t), frame_at(fr["fidelity"], t)), 3) for t in fid_times}
        g.check(2, "renders at default, min and max", all(c >= int(DUR * FPS) - 1 for c in counts.values())
                and all(v <= FIDELITY_TOL for v in fidelity.values()),
                {"frames": counts, "fidelity_vs_screenshot_capture": fidelity, "tolerance": FIDELITY_TOL,
                 "capture_mode": {k: g.renders[k]["capture_mode"] for k in ("default", "fidelity")},
                 "note": "the default render must match the same composition rendered with fast capture off"})
        # 3. differs from the baseline
        window = spec.get("window") or [how.get("at", 0), how.get("duration", DUR)]
        # An entry animation has settled by mid-window, so it can name an earlier probe.
        probe = float(spec["probe"]) if spec.get("probe") is not None else min(DUR - 0.05, window[0] + window[1] * 0.5)
        diffs = {k: round(max(mean_abs(frame_at(fr[k], t), frame_at(fr["base"], t))
                              for t in (probe, probe - 0.2 if probe > 0.3 else probe)), 3) for k in ("default", "max")}
        diffs["min"] = round(mean_abs(frame_at(fr["min"], probe), frame_at(fr["base"], probe)), 3)
        share = {k: round(changed_share(frame_at(fr[k], probe), frame_at(fr["base"], probe)), 4) for k in ("default", "max")}
        g.check(3, "each render differs from the no-effect baseline above tolerance",
                all(diffs[k] >= DIFF_MIN or share[k] >= SPARSE_SHARE for k in ("default", "max")),
                {"mean_abs_diff_0_255": diffs, "tolerance": DIFF_MIN, "changed_pixel_share": share,
                 "sparse_share_tolerance": SPARSE_SHARE, "probe_s": round(probe, 3),
                 "note": "min may sit at the effect's identity value, so only default and max must differ; a sparse effect "
                         "passes when at least 0.5% of pixels change by more than 24 levels"})
        # 4. determinism
        same = [i for i, (a, b) in enumerate(zip(fr["default"], fr["repeat"])) if mean_abs(a, b) > REPEAT_TOL]
        g.check(4, "the same frame rendered twice is identical", not same and len(fr["default"]) == len(fr["repeat"]),
                {"frames_compared": len(fr["repeat"]), "frames_differing": same[:10], "tolerance": REPEAT_TOL})
        # 5. seek safety: a 1 fps render reaches t=1 after a single jump from t=0
        d5 = mean_abs(frame_at(fr["seek"], 1.0, 1), frame_at(fr["default"], 1.0))
        g.check(5, "a frame rendered alone matches the same frame in sequence", d5 <= SEEK_TOL,
                {"t": 1.0, "mean_abs_diff": round(d5, 4), "tolerance": SEEK_TOL,
                 "method": "frame at 1.0 s from a 1 fps render (one seek from 0) against the 30 fps sequence"})
        # 6. animation
        if anim_key:
            got = {}
            for t, ref in zip(ANIM_TIMES, (anim_refs["min"], "default", anim_refs["max"])):
                got[str(t)] = round(mean_abs(frame_at(fr["animated"], t), frame_at(fr[ref], t)), 4)
            g.check(6, "animated parameters render as expected at three times", all(v <= ANIM_TOL for v in got.values()),
                    {"parameter": anim_key, "keyframes": [[ANIM_TIMES[0], mins[anim_key]], [ANIM_TIMES[1], defaults[anim_key]],
                                                          [ANIM_TIMES[2], maxs[anim_key]]],
                     "mean_abs_diff_vs_static_render": got, "tolerance": ANIM_TOL})
        else:
            g.check(6, "animated parameters render as expected at three times", None, "no animatable parameter")
        # 7. no network
        scan = static_scan(projects["default"])
        g.check(7, "no network request during preview or render", not scan,
                {"renders": "every render ran with outbound network denied by the OS (loopback allowed)",
                 "sandbox": "sandbox-exec" if sys.platform == "darwin" else "unshare --net",
                 "remote_urls_in_project": scan})
        # 8. photosensitivity
        flashes = {k: flash_analysis(g.renders[k]["path"]) for k in ("base", "default", "max") + (("animated",) if anim_key else ())}
        base_result = flashes["base"]["result"]
        rank = {"pass": 0, "warn": 1, "fail": 2}
        # The catalog rating comes from the static renders. A fast full-range
        # sweep is recorded for information: an animation that crosses the
        # range in about a second is harsher than most edits.
        static = max((flashes[k]["result"] for k in ("default", "max")), key=lambda r: rank.get(r, 2))
        photo = {"result": static, "default": flashes["default"]["result"], "max": flashes["max"]["result"],
                 "animated_sweep": flashes["animated"]["result"] if anim_key else None, "baseline_result": base_result}
        g.check(8, "photosensitivity check recorded", base_result == "pass" and flashes["default"]["result"] != "fail",
                {**photo, "rule": "fails when the no-effect baseline flashes (the fixture is wrong) or when the default setting flashes; "
                                  "a flash only at max makes the effect limited",
                 "renders": {k: {"result": f["result"], "general": f["general"], "red": f["red"]} for k, f in flashes.items()}})
        # 9. cost
        base_c, fx_c = g.renders["base"]["capture_s"], g.renders["default"]["capture_s"]
        rep_c = g.renders["repeat"]["capture_s"]
        cost = None
        if base_c and fx_c and rep_c:
            cost = round(max(1.0, min(fx_c, rep_c) / base_c), 2)
        g.check(9, "render-cost multiplier measured", cost is not None,
                {"multiplier": cost, "capture_s": {"baseline": base_c, "effect": fx_c, "effect_repeat": rep_c},
                 "capture_mode": {k: g.renders[k]["capture_mode"] for k in ("base", "default")},
                 "method": "capture seconds with the effect (lower of two runs) over capture seconds without it, same composition, 320x180, 60 frames"})
        # 10. stills
        out_dir = Path(spec["_dir"])
        ref = out_dir / "reference.jpg"
        sheet = out_dir / "contact-sheet.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            shots = []
            for i, (k, t) in enumerate((("base", probe), ("min", probe), ("default", probe), ("max", probe))):
                p = Path(tmp) / f"{i}.png"
                still(g.renders[k]["path"], t, p)
                shots.append(p)
            still(g.renders["default"]["path"], probe, ref)
            strip(shots, sheet)
        g.check(10, "reference still and contact sheet from synthetic media", ref.is_file() and sheet.is_file(),
                {"reference": ref.name, "contact_sheet": sheet.name, "sheet_order": ["no effect", "min", "default", "max"],
                 "media": "FFmpeg lavfi testsrc2, mandelbrot, and a drawn green-screen clip"})
        # 11. license and provenance
        missing = [k for k in ("license", "provenance", "implementation_route", "description") if not spec.get(k)]
        if spec.get("provenance") == "clean-room" and not spec.get("reference_id"):
            missing.append("reference_id")
        g.check(11, "license and provenance complete", not missing, {"missing": missing, "license": spec.get("license"),
                                                                     "provenance": spec.get("provenance")})
        # 12. copy detection
        g.check(12, "copy-detection check passes", *copy_detection(Path(spec["_dir"])))
    except Exception as exc:  # recorded, never hidden
        errors.append(str(exc)[-3000:])
    passed = not errors and len(g.checks) == 12 and all(c["result"] in {"pass", "not-applicable"} for c in g.checks)
    photo_detail = next((c["detail"] for c in g.checks if c["n"] == 8 and isinstance(c["detail"], dict)), {})
    photos = photo_detail.get("result")
    cost = next((c["detail"]["multiplier"] for c in g.checks if c["n"] == 9 and isinstance(c["detail"], dict)), None)
    record = {
        "effect_id": spec["effect_id"],
        "result": "pass" if passed else "fail",
        "limited": (["flashes at its max setting: keep it near default and run flash-check on the render"]
                    if passed and photo_detail.get("max") == "fail" else []),
        "verified_at": now_iso(),
        "gate_version": TOOL_VERSION,
        "profile_home": "temporary installed profile" if "fx-verify" in str(PROFILE_HOME) or os.environ.get("FX_VERIFY_TEMP") else str(PROFILE_HOME),
        "engine": f"{pin()['npm_package']}@{pin()['npm_version']}",
        "machine": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
        "fixture": {"size": list(SIZE), "fps": FPS, "seconds": DUR, "kind": spec.get("fixture", "clip")},
        "parameters": {"default": defaults, "min": mins, "max": maxs},
        "checks": g.checks,
        "errors": errors,
        "photosensitivity": {"result": photos, "default": photo_detail.get("default"), "max": photo_detail.get("max"),
                             "animated_sweep": photo_detail.get("animated_sweep"),
                             "criteria": {k: WCAG[k] for k in ("source", "urls", "accessed")}},
        "render_cost_multiplier": cost,
    }
    (Path(spec["_dir"]) / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if not keep:
        shutil.rmtree(g.video_dir, ignore_errors=True)
    shutil.rmtree(g.tmp, ignore_errors=True)
    out({"effect_id": spec["effect_id"], "result": record["result"],
         "checks": {c["n"]: c["result"] for c in g.checks}, "errors": errors})
    return 0 if record["result"] == "pass" else EXIT_CHECK


COPY_KEYWORDS = {"for", "var", "let", "const", "if", "else", "return", "while", "function", "fn", "true", "false",
                 "new", "in", "of", "do", "break", "continue", "loop", "i32", "u32", "f32", "null", "this"}
COPY_TRIVIAL_NUMBERS = {str(n) for n in range(10)} | {"0.0", "1.0", "2.0", "0.5"}
# Position and direction words: an enum of them is vocabulary, not expression.
COPY_KEYWORDS_POSITION = {"left", "right", "up", "down", "top", "bottom", "center", "centre", "width", "height", "none", "auto"}


def trivial_shingle(shingle: tuple[str, ...]) -> bool:
    """Same rule as scripts/copy_check.py in the repository: syntax-only
    shingles (punctuation, keywords, one- or two-letter names, 0, 1, 2) carry no
    expression and are not counted."""
    for tok in shingle:
        if not tok[0].isalnum() and tok[0] != "_":
            continue
        if tok in COPY_KEYWORDS or tok in COPY_TRIVIAL_NUMBERS or tok in COPY_KEYWORDS_POSITION:
            continue
        if tok[0].isalpha() and len(tok) <= 2:
            continue
        return False
    return True


def copy_detection(effect_dir: Path) -> tuple[bool, dict]:
    """Shingle check of this effect's sources against the studied project's
    fingerprints, when the profile ships them (the repository does; an
    installed profile may not)."""
    for candidate in (PROFILE_HOME / "local" / "video-editor" / "copy-fingerprints.json",
                      Path(os.environ.get("FX_FINGERPRINTS", "/nonexistent"))):
        if candidate.is_file():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            break
    else:
        return False, {"message": "no fingerprint file: set FX_FINGERPRINTS to tests/fixtures/concat-fingerprints.json from the repository"}
    salt, known = data["salt"], set(data["shingle_hashes"])
    limit = data.get("threshold_shared_shingles_per_file", 3)
    images = set(data.get("image_sha256", []))
    shared = {}
    for p in sorted(effect_dir.iterdir()):
        if p.suffix in {".js", ".css", ".svg", ".html", ".json"} and p.name != "verification.json":
            tokens = [t.lower() for t in re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|\S",
                      re.sub(r"(?m)//[^\n]*", " ", re.sub(r"/\*.*?\*/", " ", p.read_text(encoding="utf-8"), flags=re.S)))]
            sh = {s for s in (tuple(tokens[i:i + 8]) for i in range(max(0, len(tokens) - 7))) if not trivial_shingle(s)}
            hits = {hashlib.sha256((salt + "\x1f" + "\x1f".join(s)).encode()).hexdigest()[:20] for s in sh} & known
            shared[p.name] = len(hits)
        if p.suffix in {".png", ".jpg"} and sha256_file(p) in images:
            shared[p.name] = "image hash matches a studied image"
    bad = {k: v for k, v in shared.items() if not isinstance(v, int) or v > limit}
    return not bad, {"shared_shingles_per_file": shared, "limit": limit, "fingerprints_commit": data.get("commit", "")[:12]}


# ---------------------------------------------------------------- audio verification

AUDIO_HEAD = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=320, height=180" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>html, body {{ margin: 0; width: 320px; height: 180px; background: #000; }}</style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{dur}" data-width="320" data-height="180">
      <audio id="a1" src="assets/voice.wav" data-start="0" data-duration="{dur}" data-media-start="0" data-track-index="0"{chain}></audio>
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def pcm(path: Path) -> list[int]:
    proc = subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path), "-vn",
                           "-ac", "1", "-ar", "48000", "-f", "s16le", "-"], capture_output=True, timeout=300)
    n = len(proc.stdout) // 2
    return list(struct.unpack(f"<{n}h", proc.stdout[:n * 2]))


def band_energy(samples: list[int], hz: float) -> float:
    """Goertzel power at one frequency, normalised by length."""
    if not samples:
        return 0.0
    k = 2 * math.cos(2 * math.pi * hz / 48000)
    s1 = s2 = 0.0
    for x in samples:
        s0 = x + k * s1 - s2
        s2, s1 = s1, s0
    return (s1 * s1 + s2 * s2 - k * s1 * s2) / len(samples) ** 2


def verify_audio(spec: dict, keep: bool) -> int:
    g = Gate(spec, keep)
    errors = []
    params = param_specs(spec)
    defaults = {k: p["default"] for k, p in params.items()}
    mins = {k: p["min"] for k, p in params.items()}
    maxs = {k: p["max"] for k, p in params.items()}
    try:
        renders = {}
        for name, values in (("base", None), ("default", defaults), ("min", mins), ("max", maxs), ("repeat", defaults)):
            proj = g.new_version(name if name != "repeat" else "repeat")
            make_voice(proj)
            chain = ""
            if values is not None:
                chain = " data-fx-chain='" + json.dumps({"version": 1, "nodes": [grading_value(n, values) for n in spec["fx_chain"]]},
                                                         separators=(",", ":")) + "'"
            (proj / "index.html").write_text(AUDIO_HEAD.format(dur=DUR, chain=chain), encoding="utf-8")
            renders[name] = g.render(proj, name)
        g.check(1, "lint and check pass", True, "audio fixtures: rendered through the launcher, which lints first")
        samples = {k: pcm(v["path"]) for k, v in renders.items()}
        g.check(2, "renders at default, min and max", all(len(samples[k]) > 48000 for k in ("default", "min", "max")),
                {k: len(samples[k]) for k in samples})
        n = min(len(s) for s in samples.values())

        def diff(a, b):
            return sum(abs(x - y) for x, y in zip(a[:n], b[:n])) / max(1, n)
        d = {k: round(diff(samples[k], samples["base"]), 2) for k in ("default", "max")}
        g.check(3, "each render differs from the dry baseline above tolerance", d["default"] > 8 and d["max"] > 8,
                {"mean_abs_sample_diff": d, "tolerance": 8})
        same = samples["default"][:n] == samples["repeat"][:n]
        g.check(4, "the same render twice is identical", same, {"samples_compared": n})
        g.check(5, "a frame rendered alone matches the same frame in sequence", None,
                "audio is rendered offline as one buffer; there is no per-frame seek")
        g.check(6, "animated parameters render as expected at three times", None,
                "automation lanes are HyperFrames' own; not part of this entry")
        g.check(7, "no network request during preview or render", not static_scan(proj),
                {"renders": "outbound network denied by the OS"})
        g.check(8, "photosensitivity check recorded", True, {"result": "not-applicable (audio)"})
        cost = None
        if renders["base"]["wall_s"]:
            cost = round(max(1.0, renders["default"]["wall_s"] / renders["base"]["wall_s"]), 2)
        g.check(9, "render-cost multiplier measured", cost is not None,
                {"multiplier": cost, "method": "render wall seconds with the chain over without it"})
        g.check(10, "reference still and contact sheet from synthetic media", None, "audio effect: a spectrum note instead",
                )
        missing = [k for k in ("license", "provenance") if not spec.get(k)]
        g.check(11, "license and provenance complete", not missing, {"missing": missing})
        g.check(12, "copy-detection check passes", *copy_detection(Path(spec["_dir"])))
        measure = spec.get("measure")
        if measure:
            hz = measure["hz"]
            e = {k: band_energy(samples[k][:48000], hz) for k in ("base", "default")}
            ratio = e["default"] / e["base"] if e["base"] else None
            ok = ratio is not None and (ratio < measure.get("below", float("inf"))) and (ratio > measure.get("above", -1))
            g.checks.append({"n": 13, "check": "expected change at a measured frequency", "result": "pass" if ok else "fail",
                             "detail": {"hz": hz, "energy_ratio": ratio, "expect": measure}})
    except Exception as exc:
        errors.append(str(exc)[-3000:])
    passed = not errors and all(c["result"] in {"pass", "not-applicable"} for c in g.checks) and len(g.checks) >= 12
    record = {"effect_id": spec["effect_id"], "result": "pass" if passed else "fail", "verified_at": now_iso(),
              "gate_version": TOOL_VERSION, "engine": f"{pin()['npm_package']}@{pin()['npm_version']}",
              "machine": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
              "checks": g.checks, "errors": errors, "photosensitivity": {"result": "not-applicable"},
              "render_cost_multiplier": next((c["detail"]["multiplier"] for c in g.checks if c["n"] == 9 and isinstance(c["detail"], dict)), None)}
    (Path(spec["_dir"]) / "verification.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    if not keep:
        shutil.rmtree(g.video_dir, ignore_errors=True)
    out({"effect_id": spec["effect_id"], "result": record["result"], "checks": {c["n"]: c["result"] for c in g.checks},
         "errors": errors})
    return 0 if passed else EXIT_CHECK


def make_voice(project: Path) -> None:
    """A synthetic voice-like signal: a 140 Hz buzz with harmonics, a 60 Hz hum,
    a 6 kHz hiss band, and a syllable envelope. Known content, no rights."""
    assets = project / "assets"
    assets.mkdir(exist_ok=True)
    expr = ("0.25*(sin(2*PI*140*t)+0.5*sin(2*PI*280*t)+0.3*sin(2*PI*420*t)+0.2*sin(2*PI*2800*t))*(0.55+0.45*sin(2*PI*3*t))"
            "+0.12*sin(2*PI*60*t)+0.04*sin(2*PI*6000*t)")
    subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                    f"aevalsrc={expr}:s=48000:d={DUR + 0.5}", "-c:a", "pcm_s16le", str(assets / "voice.wav")],
                   check=True, timeout=120)
    register = project / "asset-rights-register.yaml"
    text = register.read_text(encoding="utf-8") if register.is_file() else "assets: []\n"
    text = text.replace("assets: []", "assets:") + ("  - asset: assets/voice.wav\n    source: generated by fx.py verify with FFmpeg aevalsrc\n"
                                                    "    license: synthetic test media, no third-party rights\n    proof: fx.py make_voice\n")
    register.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------- main

COMMANDS = {
    "list": cmd_list, "show": cmd_show, "apply": cmd_apply, "remove": cmd_remove, "instances": cmd_instances,
    "stack-check": cmd_stack_check, "check-plan": cmd_check_plan, "flash-check": cmd_flash_check,
    "contact-sheet": cmd_contact_sheet, "verify": cmd_verify,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    cmd = COMMANDS.get(argv[0])
    if cmd is None:
        fail(EXIT_USAGE, "blocked", f"unknown command: {argv[0]}", commands=sorted(COMMANDS))
    return cmd(argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
