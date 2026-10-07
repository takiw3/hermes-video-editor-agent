"""Shared helpers for the test suite.

Synthetic media only. Every source clip is generated here with FFmpeg, so the
ground truth is known: second N of a "timecode" clip is one solid colour from
PALETTE with a sine tone at tone_hz(N). A rendered frame's colour and a
window's tone frequency therefore say exactly which source second is on the
timeline, for picture and for sound independently.
"""

from __future__ import annotations

import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
LAUNCHER_REL = "skills/integrations/editor-hyperframes/scripts/hf.py"
TOOLS_REL = "skills/integrations/editor-hyperframes/scripts/editor_tools.py"

PALETTE = [
    (230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200), (245, 130, 48), (145, 30, 180),
    (70, 240, 240), (240, 50, 230), (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255),
    (170, 110, 40), (128, 0, 0), (170, 255, 195), (0, 0, 128),
]


def tone_hz(second: int) -> int:
    return 300 + 110 * second


def have(tool: str) -> bool:
    return shutil.which(tool) is not None


def run(cmd, **kw) -> subprocess.CompletedProcess:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)


# ---------------------------------------------------------------- profiles

def owned_paths() -> list[str]:
    return yaml.safe_load((REPO / "distribution.yaml").read_text(encoding="utf-8"))["distribution_owned"]


def copy_payload(profile: Path) -> Path:
    """Copy exactly the distribution_owned allowlist, as Hermes does.

    Used where Hermes itself is not on the machine (CI). The install tests
    compare this against a real `hermes profile install`."""
    profile.mkdir(parents=True, exist_ok=True)
    for rel in owned_paths():
        src, dest = REPO / rel, profile / rel
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
        elif src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    return profile


def hermes_bin() -> str | None:
    return os.environ.get("VE_TEST_HERMES") or shutil.which("hermes")


def install_profile(base: Path, use_hermes: bool | None = None) -> Path:
    """Install into <base>/home/.hermes/profiles/video-editor and return it."""
    home = base / "home"
    hermes_home = home / ".hermes"
    home.mkdir(parents=True, exist_ok=True)
    profile = hermes_home / "profiles" / "video-editor"
    want = os.environ.get("VE_TEST_USE_HERMES") == "1" if use_hermes is None else use_hermes
    if want:
        binary = hermes_bin()
        if not binary:
            raise RuntimeError("VE_TEST_USE_HERMES=1 but no hermes binary found")
        proc = run([binary, "profile", "install", REPO, "--alias", "--yes"],
                   env={**os.environ, "HOME": str(home), "HERMES_HOME": str(hermes_home)})
        if proc.returncode != 0 or not profile.is_dir():
            raise RuntimeError(f"hermes profile install failed: {proc.stdout}\n{proc.stderr}")
    else:
        copy_payload(profile)
    return profile


def profile_env(profile: Path, extra: dict | None = None) -> dict:
    env = {**os.environ, "HOME": str(profile.parents[2]), "HERMES_HOME": str(profile)}
    env.pop("EDITOR_HF_LAUNCHER", None)
    env.update(extra or {})
    return env


def hf(profile: Path, *args, cwd: Path | None = None, env: dict | None = None, timeout: int = 3600):
    return run([sys.executable, profile / LAUNCHER_REL, *args], cwd=cwd, env=profile_env(profile, env), timeout=timeout)


def tools(profile: Path, *args, cwd: Path | None = None, env: dict | None = None, timeout: int = 3600):
    return run([sys.executable, profile / TOOLS_REL, *args], cwd=cwd, env=profile_env(profile, env), timeout=timeout)


def parse_json(text: str):
    """The launcher prints a JSON object last; the pinned CLI may print above it."""
    start = text.rfind("\n{\n")
    start = 0 if text.startswith("{") and start < 0 else start + 1
    return json.loads(text[start:])


def engine_file(profile: Path) -> Path:
    return profile / "local" / "video-editor" / "video-engine" / "engine.json"


def write_engine(profile: Path, **fields) -> None:
    path = engine_file(profile)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    data.update(fields)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def make_workspace(profile: Path, ws: Path) -> Path:
    proc = hf(profile, "setup", "--workspace", ws)
    assert proc.returncode == 0, proc.stderr
    return ws


# ---------------------------------------------------------------- toolchain

def toolchain_requested() -> bool:
    return os.environ.get("VE_TEST_TOOLCHAIN") == "1"


def setup_toolchain(profile: Path, ws: Path) -> None:
    """Owner-run setup, as the README documents it. Uses a headless Chrome that
    is already on the machine (VE_TEST_BROWSER); the tests never download one."""
    browser = os.environ.get("VE_TEST_BROWSER")
    if not browser or not Path(browser).is_file():
        raise RuntimeError("set VE_TEST_BROWSER to an existing chrome-headless-shell executable")
    make_workspace(profile, ws)
    proc = hf(profile, "setup", "--install-cli", "--yes")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = hf(profile, "setup", "--use-browser", browser)
    assert proc.returncode == 0, proc.stderr


# ---------------------------------------------------------------- media

def ffmpeg(*args, timeout: int = 900) -> subprocess.CompletedProcess:
    proc = run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args], timeout=timeout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {proc.stderr[-800:]}")
    return proc


def make_timecode_clip(dest: Path, seconds: int = 12, size: str = "640x360", fps: int = 30,
                       silent_seconds: tuple[int, ...] = (), audio: bool = True, start_index: int = 0) -> Path:
    """Second i is PALETTE[start_index + i] with a tone at tone_hz(start_index + i).
    A white 80x80 box sits at the centre so a punch-in can be measured."""
    w, h = (int(x) for x in size.split("x"))
    inputs, parts = [], []
    for i in range(seconds):
        r, g, b = PALETTE[(start_index + i) % len(PALETTE)]
        inputs += ["-f", "lavfi", "-i", f"color=c=0x{r:02x}{g:02x}{b:02x}:s={size}:r={fps}:d=1"]
    for i in range(seconds):
        if audio:
            vol = "0" if i in silent_seconds else "1"
            inputs += ["-f", "lavfi", "-i", f"sine=frequency={tone_hz(start_index + i)}:sample_rate=48000:duration=1,volume={vol}"]
    v = "".join(f"[{i}:v]" for i in range(seconds))
    graph = f"{v}concat=n={seconds}:v=1:a=0[vc];[vc]drawbox=x={w // 2 - 40}:y={h // 2 - 40}:w=80:h=80:color=white:t=fill[vo]"
    maps = ["-map", "[vo]"]
    if audio:
        a = "".join(f"[{seconds + i}:a]" for i in range(seconds))
        graph += f";{a}concat=n={seconds}:v=0:a=1[ao]"
        maps += ["-map", "[ao]", "-c:a", "aac", "-b:a", "192k"]
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(*inputs, "-filter_complex", graph, *maps, "-c:v", "libx264", "-preset", "veryfast", "-crf", "12",
           "-pix_fmt", "yuv420p", "-g", str(fps), "-movflags", "+faststart", dest)
    return dest


def make_long_timecode_clip(dest: Path, seconds: int, size: str = "1280x720", fps: int = 30) -> Path:
    """A long timecode clip: second N is PALETTE[N % 16] with tone_hz(N % 16).

    Picture and sound each come from one expression of time, in one encode,
    so there is no drift. Looping a finished clip with stream copy adds about
    one audio frame of drift per loop, which is enough to move a ground-truth
    check off by a second in a ten-minute file."""
    w, h = (int(x) for x in size.split("x"))

    def channel(k: int) -> str:
        return "+".join(f"eq(mod(floor(T)\\,16)\\,{i})*{PALETTE[i][k]}" for i in range(16))

    video = (f"color=c=black:s=16x16:r={fps}:d={seconds},format=rgb24,"
             f"geq=r='{channel(0)}':g='{channel(1)}':b='{channel(2)}',"
             f"scale={w}:{h}:flags=neighbor,"
             f"drawbox=x={w // 2 - 40}:y={h // 2 - 40}:w=80:h=80:color=white:t=fill")
    tone = "0.125*sin(2*PI*(300+110*mod(floor(t)\\,16))*t)"
    dest.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-f", "lavfi", "-i", video, "-f", "lavfi", "-i", f"aevalsrc={tone}:s=48000:d={seconds}",
           "-t", str(seconds), "-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
           "-g", str(fps), "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", dest, timeout=3600)
    return dest


def frame_rgb(path: Path, t: float, crop: str = "100:100:20:20") -> tuple[int, int, int]:
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(path),
                           "-frames:v", "1", "-vf", f"crop={crop},scale=1:1:flags=area", "-f", "rawvideo",
                           "-pix_fmt", "rgb24", "-"], capture_output=True, timeout=120)
    if len(proc.stdout) < 3:
        raise RuntimeError(f"no frame at {t}s in {path}: {proc.stderr.decode()[-300:]}")
    return tuple(proc.stdout[:3])  # type: ignore[return-value]


def frame_rgba(path: Path, t: float, crop: str, decoder: str | None = None) -> tuple[int, int, int, int]:
    pre = ["-c:v", decoder] if decoder else []
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", *pre, "-ss", f"{t:.3f}", "-i", str(path),
                           "-frames:v", "1", "-vf", f"crop={crop},scale=1:1:flags=area", "-f", "rawvideo",
                           "-pix_fmt", "rgba", "-"], capture_output=True, timeout=120)
    if len(proc.stdout) < 4:
        raise RuntimeError(f"no frame at {t}s in {path}: {proc.stderr.decode()[-300:]}")
    return tuple(proc.stdout[:4])  # type: ignore[return-value]


def colour_distance(a, b) -> float:
    return sum((x - y) ** 2 for x, y in zip(a[:3], b[:3])) ** 0.5


def palette_index(rgb, tolerance: float = 60.0) -> int | None:
    best = min(range(len(PALETTE)), key=lambda i: colour_distance(rgb, PALETTE[i]))
    return best if colour_distance(rgb, PALETTE[best]) <= tolerance else None


def source_second_at(path: Path, t: float) -> int | None:
    """Which source second is on screen at output time t."""
    return palette_index(frame_rgb(path, t))


def tone_at(path: Path, start: float, end: float) -> float | None:
    """Dominant frequency in [start, end) from zero crossings, or None when silent."""
    proc = subprocess.run(["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", f"{start:.3f}",
                           "-t", f"{end - start:.3f}", "-i", str(path), "-vn", "-ac", "1", "-ar", "48000",
                           "-f", "s16le", "-"], capture_output=True, timeout=120)
    n = len(proc.stdout) // 2
    if n < 480:
        return None
    samples = struct.unpack(f"<{n}h", proc.stdout[: n * 2])
    rms = (sum(s * s for s in samples) / n) ** 0.5
    if rms < 60:
        return None
    crossings = sum(1 for a, b in zip(samples, samples[1:]) if (a < 0) != (b < 0))
    return crossings / 2 / (n / 48000)


def audio_second_at(path: Path, start: float, end: float) -> int | None:
    """Which source second is being heard in [start, end)."""
    hz = tone_at(path, start, end)
    if hz is None:
        return None
    return round((hz - 300) / 110)


def probe(path: Path) -> dict:
    proc = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", path])
    return json.loads(proc.stdout)


def video_stream(path: Path) -> dict:
    return next(s for s in probe(path)["streams"] if s["codec_type"] == "video")


def has_audio(path: Path) -> bool:
    return any(s["codec_type"] == "audio" for s in probe(path)["streams"])


def sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------- projects

def html_document(width: int, height: int, duration: float, body: str, script: str = "", css: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={width}, height={height}" />
    <script src="assets/vendor/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: {width}px; height: {height}px; overflow: hidden; background: #000; }}
      #root {{ position: relative; width: {width}px; height: {height}px; overflow: hidden; }}
      .inner {{ position: absolute; inset: 0; overflow: hidden; }}
      video, img.fill {{ position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }}
      {css}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{duration}" data-width="{width}" data-height="{height}">
{body}
    </div>
    <script>
      const tl = gsap.timeline({{ paused: true }});
{script}
      window.__timelines["main"] = tl;
      tl.seek(0);
    </script>
  </body>
</html>
"""


def video_clip(cid: str, src: str, start: float, duration: float, media_start: float, track: int = 0,
               audio: bool = True, extra: str = "") -> str:
    has = ' data-has-audio="true"' if audio else " muted"
    return (f'      <video id="{cid}" src="{src}" data-start="{start}" data-duration="{duration}" '
            f'data-media-start="{media_start}" data-track-index="{track}" playsinline{has}{extra}></video>')


STYLE_DECISION = """decision_id: SD-TEST-001
project_id: {project}
decision: hybrid
study_id: OS-TEST-001
blueprint_id: SB-TEST-001
blueprint_version: 1
blueprint_valid_until: {valid_until}
decided_by: owner (synthetic test fixture)
decided_by_role: owner
decided_at: 2026-10-06T12:00:00Z
waiver_reason:
waiver_scope:
stale_blueprint_accepted_by:
"""


def new_project(profile: Path, ws: Path, name: str, version: str = "v1") -> Path:
    """Scaffold projects/<name>/<version> through the launcher, as the agent does."""
    video_dir = ws / "projects" / name
    video_dir.mkdir(parents=True, exist_ok=True)
    proc = hf(profile, "init", version, cwd=video_dir)
    project = video_dir / version
    assert proc.returncode == 0 and (project / "index.html").is_file(), proc.stdout + proc.stderr
    return project


def record_style_decision(project: Path, valid_until: str = "2099-01-01") -> Path:
    path = project.parent / "style-decision.yaml"
    path.write_text(STYLE_DECISION.format(project=project.parent.name, valid_until=valid_until), encoding="utf-8")
    return path


def register_assets(project: Path, assets: list[str]) -> None:
    """Record a complete licence entry for each synthetic asset."""
    path = project / "asset-rights-register.yaml"
    text = path.read_text(encoding="utf-8").replace("assets: []", "assets:")
    for rel in assets:
        text += (f"  - asset: {rel}\n    source: generated by the test suite with FFmpeg lavfi sources\n"
                 "    license: synthetic test media, no third-party rights\n    proof: tests/harness.py\n")
    path.write_text(text, encoding="utf-8")


def render(profile: Path, project: Path, stage: str = "draft", *extra, timeout: int = 7200) -> dict:
    args = ["render", "--stage", stage, "--fps", "30", *extra]
    proc = hf(profile, *args, cwd=project, timeout=timeout)
    if proc.returncode != 0:
        raise AssertionError(f"render failed ({proc.returncode}):\n{proc.stdout[-1500:]}\n{proc.stderr[-1500:]}")
    return parse_json(proc.stdout)
