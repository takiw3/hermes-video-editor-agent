#!/usr/bin/env python3
"""Deterministic measurement tools for the Hermes video-editor profile.

    python3 "$HERMES_HOME/skills/integrations/editor-hyperframes/scripts/editor_tools.py" <tool> ...

Every tool here measures or computes. None of them judges. Each result names
the tool, its version, and the thresholds used, because a cut detector with a
different threshold gives a different count.

  probe <file...>                 container, codecs, frame rate, rotation, HDR, VFR flags
  working-copy <file> [--fps N]   constant-frame-rate SDR H.264 copy; the original is untouched
  cuts <file> [--threshold T]     cut times and shot-length distribution
  audio-profile <file>            integrated loudness, true peak, silence gaps, clipping
  duck-check <file> --speech ...  level in speech windows against the gaps, per band
  frames <file> [--schedule S]    sample frames on a recorded schedule (session-only)
  contact-sheet <file> --out F    one tiled image across the timeline
  session-clean                   delete sampled frames
  outlier-score <dataset.json>    views / account median, ranked, with exclusions kept
  dead-air <words.json>           keep-ranges from word timings (a proposal, not a cut)
  safe-zone <plan.json>           overlay boxes against a recorded safe zone
  check-study <file>              an outlier study follows the evidence rules
  check-blueprint <file>          a style blueprint follows the evidence rules
  check-proposal <file>           a style-match proposal promises nothing
  load <file>                     print a YAML or JSON file as JSON

Standard library only. PyYAML is used when present; otherwise a small parser
reads the YAML subset the profile's templates use. Exit codes: 0 ok, 2 usage,
4 refused, 5 check failed.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

TOOL_VERSION = "1.0.0"
SCRIPT = Path(__file__).resolve()
PROFILE_HOME = SCRIPT.parents[4]
ENGINE_FILE = PROFILE_HOME / "local" / "video-editor" / "video-engine" / "engine.json"
WS_META = ".video-editor"
UNAVAILABLE = "Unavailable"

EXIT_USAGE, EXIT_REFUSED, EXIT_CHECK = 2, 4, 5


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


def inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except (ValueError, OSError):
        return False


def workspace() -> Path:
    try:
        ws = json.loads(ENGINE_FILE.read_text(encoding="utf-8")).get("workspace")
    except Exception:
        ws = None
    if not ws or not Path(ws).is_dir():
        fail(3, "needs_setup", "no video workspace is approved",
             fix="owner runs: hf.py setup --workspace <folder>")
    return Path(ws).resolve()


def need(tool: str) -> str:
    found = shutil.which(tool)
    if not found:
        fail(3, "needs_setup", f"{tool} not found on PATH",
             fix="Install FFmpeg yourself (it provides ffmpeg and ffprobe). This profile never installs it.")
    return found


def tool_version(tool: str) -> str:
    try:
        first = subprocess.run([need(tool), "-version"], capture_output=True, text=True, timeout=20).stdout.splitlines()[0]
        return first.split(" Copyright")[0]
    except Exception:
        return UNAVAILABLE


def in_workspace(arg: str, must_exist: bool = True) -> Path:
    ws = workspace()
    path = Path(os.path.expanduser(arg))
    path = path if path.is_absolute() else Path.cwd() / path
    if not inside(path, ws):
        fail(EXIT_REFUSED, "blocked", f"path is outside the approved workspace: {arg}", workspace=str(ws))
    if must_exist and not path.is_file():
        fail(EXIT_CHECK, "blocked", f"not a file: {arg}")
    return path.resolve()


def take(args: list[str], name: str, default=None):
    if name in args:
        i = args.index(name)
        if i + 1 >= len(args):
            fail(EXIT_USAGE, "blocked", f"{name} needs a value")
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


# --------------------------------------------------------------------------
# YAML subset loader
# --------------------------------------------------------------------------

def _scalar(text: str):
    t = text.strip()
    if t == "" or t in {"~", "null", "Null", "NULL"}:
        return None
    if (t[0] == t[-1] == '"') and len(t) >= 2:
        return json.loads(t)
    if (t[0] == t[-1] == "'") and len(t) >= 2:
        return t[1:-1].replace("''", "'")
    if t in {"true", "True"}:
        return True
    if t in {"false", "False"}:
        return False
    if t.startswith("[") and t.endswith("]"):
        inner = t[1:-1].strip()
        return [] if not inner else [_scalar(x) for x in _split_flow(inner)]
    if t == "{}":
        return {}
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def _split_flow(inner: str) -> list[str]:
    parts, depth, quote, cur = [], 0, "", ""
    for ch in inner:
        if quote:
            cur += ch
            quote = "" if ch == quote else quote
        elif ch in "\"'":
            quote, cur = ch, cur + ch
        elif ch in "[{":
            depth, cur = depth + 1, cur + ch
        elif ch in "]}":
            depth, cur = depth - 1, cur + ch
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    parts.append(cur)
    return parts


def _strip_comment(line: str) -> str:
    quote = ""
    for i, ch in enumerate(line):
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def load_yaml_subset(text: str):
    """Block maps, block lists, scalars, flow lists, and `>`/`|` blocks.
    No anchors, tags, or multi-document streams."""
    lines = []
    for raw in text.splitlines():
        if raw.strip() == "---":
            continue
        lines.append(raw.rstrip())
    pos = 0

    def indent_of(s: str) -> int:
        return len(s) - len(s.lstrip(" "))

    def skip_blank() -> None:
        nonlocal pos
        while pos < len(lines) and not _strip_comment(lines[pos]).strip():
            pos += 1

    def block_scalar(parent_indent: int, style: str) -> str:
        nonlocal pos
        chunk = []
        while pos < len(lines) and (not lines[pos].strip() or indent_of(lines[pos]) > parent_indent):
            chunk.append(lines[pos])
            pos += 1
        while chunk and not chunk[-1].strip():
            chunk.pop()
        if not chunk:
            return ""
        base = min(indent_of(c) for c in chunk if c.strip())
        body = [c[base:] if c.strip() else "" for c in chunk]
        if style.startswith("|"):
            return "\n".join(body) + ("" if style.endswith("-") else "\n")
        folded = re.sub(r"(?<!\n)\n(?!\n)", " ", "\n".join(body))
        return folded + ("" if style.endswith("-") else "\n")

    def parse_value(rest: str, indent: int):
        nonlocal pos
        rest = _strip_comment(rest).strip()
        if rest in {">", ">-", "|", "|-"}:
            return block_scalar(indent, rest)
        if rest:
            return _scalar(rest)
        skip_blank()
        if pos < len(lines):
            nxt = indent_of(lines[pos])
            is_item = lines[pos].lstrip().startswith("- ") or lines[pos].strip() == "-"
            if nxt > indent or (is_item and nxt == indent):
                return parse_block(nxt)
        return None

    def parse_block(indent: int):
        nonlocal pos
        skip_blank()
        if pos >= len(lines):
            return None
        first = lines[pos].lstrip()
        if first.startswith("- ") or first == "-":
            items = []
            while True:
                skip_blank()
                if pos >= len(lines) or indent_of(lines[pos]) != indent:
                    break
                body = lines[pos].lstrip()
                if not (body.startswith("- ") or body == "-"):
                    break
                rest = body[1:].lstrip() if body != "-" else ""
                child_indent = indent + (len(body) - len(rest)) if rest else indent + 2
                m = re.match(r"^([A-Za-z_][\w .()/-]*):(\s|$)", _strip_comment(rest))
                if rest and m:
                    lines[pos] = " " * child_indent + rest
                    items.append(parse_block(child_indent))
                else:
                    pos += 1
                    items.append(parse_value(rest, indent))
            return items
        data = {}
        while True:
            skip_blank()
            if pos >= len(lines) or indent_of(lines[pos]) != indent:
                break
            line = _strip_comment(lines[pos])
            m = re.match(r"^\s*(\"[^\"]+\"|'[^']+'|[^:#]+?):(\s+(.*))?$", line)
            if not m:
                raise ValueError(f"line {pos + 1}: not a key: {lines[pos]!r}")
            key = m.group(1).strip().strip("\"'")
            pos += 1
            data[key] = parse_value(m.group(3) or "", indent)
        return data

    skip_blank()
    result = parse_block(indent_of(lines[pos])) if pos < len(lines) else None
    skip_blank()
    if pos < len(lines):
        raise ValueError(f"line {pos + 1}: unexpected indentation: {lines[pos]!r}")
    return result


def load_data(path: Path, force_subset: bool = False):
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text)
    if not force_subset:
        try:
            import yaml  # type: ignore
            return yaml.safe_load(text)
        except ImportError:
            pass
    return load_yaml_subset(text)


def is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "tbd", "unknown", "none", "null", "~"}
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


# --------------------------------------------------------------------------
# probe and working copies
# --------------------------------------------------------------------------

HDR_TRANSFERS = {"smpte2084", "arib-std-b67"}
LOG_HINTS = ("log", "slog", "vlog", "clog", "hlg")


def ratio(text: str | None) -> float | None:
    if not text or "/" not in text:
        return None
    num, den = text.split("/", 1)
    try:
        return float(num) / float(den) if float(den) else None
    except ValueError:
        return None


def probe_file(path: Path) -> dict:
    proc = subprocess.run(
        [need("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        capture_output=True, text=True, timeout=300,
    )
    base = {"file": str(path), "bytes": path.stat().st_size}
    if proc.returncode != 0:
        return {**base, "status": "probe failed", "probe_ok": False, "error": proc.stderr.strip()[:600],
                "rule": "Never edit from a file whose probe failed."}
    data = json.loads(proc.stdout or "{}")
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = [s for s in streams if s.get("codec_type") == "audio"]
    fmt = data.get("format") or {}
    if video is None and not audio:
        return {**base, "status": "probe failed", "probe_ok": False, "error": "no audio or video stream found",
                "rule": "Never edit from a file whose probe failed."}
    info: dict = {**base, "status": "footage probed", "probe_ok": True, "sha256": sha256_file(path),
                  "container": fmt.get("format_name"),
                  "duration_seconds": round(float(fmt.get("duration") or 0), 3)}
    flags: list[dict] = []
    if video:
        r, avg = ratio(video.get("r_frame_rate")), ratio(video.get("avg_frame_rate"))
        rotation = 0
        for sd in video.get("side_data_list") or []:
            if "rotation" in sd:
                rotation = int(float(sd["rotation"]))
        if not rotation and (video.get("tags") or {}).get("rotate"):
            rotation = int(float(video["tags"]["rotate"]))
        vfr = bool(r and avg and abs(r - avg) / max(r, avg) > 0.005)
        transfer = (video.get("color_transfer") or "").lower()
        info.update({
            "video_codec": video.get("codec_name"), "profile": video.get("profile"),
            "width": video.get("width"), "height": video.get("height"),
            "pixel_format": video.get("pix_fmt"),
            "r_frame_rate": round(r, 3) if r else None, "avg_frame_rate": round(avg, 3) if avg else None,
            "frame_rate_mode": "variable" if vfr else "constant",
            "color_transfer": video.get("color_transfer") or UNAVAILABLE,
            "color_primaries": video.get("color_primaries") or UNAVAILABLE,
            "color_space": video.get("color_space") or UNAVAILABLE,
            "rotation_degrees": rotation,
            "display_width": video.get("height") if abs(rotation) in {90, 270} else video.get("width"),
            "display_height": video.get("width") if abs(rotation) in {90, 270} else video.get("height"),
        })
        if vfr:
            flags.append({"flag": "variable_frame_rate",
                          "detail": f"r_frame_rate {info['r_frame_rate']} differs from avg_frame_rate {info['avg_frame_rate']}",
                          "action": "write a constant-frame-rate working copy; edit from the copy"})
        if video.get("codec_name") in {"hevc", "h265"}:
            flags.append({"flag": "hevc", "detail": "HEVC source",
                          "action": "confirm the pinned renderer decodes it on this machine, or write an H.264 working copy"})
        if transfer in HDR_TRANSFERS:
            flags.append({"flag": "hdr", "detail": f"color_transfer {transfer}",
                          "action": "decide HDR or SDR delivery with the owner; for SDR write a tone-mapped working copy"})
        elif any(h in transfer for h in LOG_HINTS) or any(
                h in ((video.get("tags") or {}).get("encoder") or "").lower() for h in ("slog", "vlog", "clog")):
            flags.append({"flag": "log", "detail": f"color_transfer {transfer or UNAVAILABLE}",
                          "action": "LOG footage needs a look applied; confirm the conversion with the owner"})
        if rotation:
            flags.append({"flag": "rotated", "detail": f"rotation metadata {rotation} degrees",
                          "action": "write a working copy with the rotation baked in; edit from the copy"})
        if (video.get("pix_fmt") or "").endswith(("10le", "10be", "12le", "12be")):
            flags.append({"flag": "high_bit_depth", "detail": video.get("pix_fmt"),
                          "action": "note for color work; a working copy converts to 8-bit"})
    else:
        flags.append({"flag": "no_video", "detail": "audio-only file", "action": "use as an audio source only"})
    if audio:
        a = audio[0]
        info.update({"audio_codec": a.get("codec_name"), "audio_channels": a.get("channels"),
                     "audio_sample_rate": int(a["sample_rate"]) if a.get("sample_rate") else None,
                     "audio_streams": len(audio), "has_audio": True})
    else:
        info.update({"has_audio": False, "audio_streams": 0})
        flags.append({"flag": "no_audio", "detail": "no audio track",
                      "action": "do not set data-has-audio on this clip; captions need another source"})
    info["flags"] = flags
    info["needs_working_copy"] = any(f["flag"] in {"variable_frame_rate", "rotated", "hdr", "log"} for f in flags)
    return info


def cmd_probe(args: list[str]) -> int:
    if not args:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py probe <file> [<file> ...]")
    files = [probe_file(in_workspace(a)) for a in args]
    failed = [f["file"] for f in files if not f["probe_ok"]]
    out({"tool": "probe", "tool_version": TOOL_VERSION, "ffprobe": tool_version("ffprobe"), "probed_at": now_iso(),
         "status": "probe failed" if failed else "footage probed", "failed": failed, "files": files})
    return EXIT_CHECK if failed else 0


def cmd_working_copy(args: list[str]) -> int:
    fps = take(args, "--fps")
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py working-copy <file> [--fps N]")
    src = in_workspace(args[0])
    ws = workspace()
    if inside(src, ws / "references"):
        fail(EXIT_REFUSED, "blocked", "a reference video is studied, not converted into project media")
    before = sha256_file(src)
    info = probe_file(src)
    if not info["probe_ok"]:
        fail(EXIT_CHECK, "probe failed", "footage unreadable; no working copy was written", probe=info)
    rate = fps or (str(round(info["avg_frame_rate"])) if info.get("avg_frame_rate") else None)
    if not rate:
        fail(EXIT_CHECK, "blocked", "no frame rate could be read; pass --fps")
    dest_dir = ws / "working-copies"
    dest_dir.mkdir(exist_ok=True)
    dest = dest_dir / f"{src.stem}.wc-{before[:8]}.cfr{rate}.mp4"
    if dest.exists():
        fail(EXIT_REFUSED, "blocked", f"working copy already exists and will not be overwritten: {dest}")
    vf = [f"fps={rate}"]
    if any(f["flag"] in {"hdr"} for f in info["flags"]):
        vf = ["zscale=t=linear:npl=100", "format=gbrpf32le", "zscale=p=bt709", "tonemap=tonemap=hable:desat=0",
              "zscale=t=bt709:m=bt709:r=tv", f"fps={rate}"]
    cmd = [need("ffmpeg"), "-hide_banner", "-nostdin", "-n", "-i", str(src), "-map", "0:v:0", "-map", "0:a:0?",
           "-vf", ",".join(vf), "-fps_mode", "cfr", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-movflags", "+faststart", str(dest)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    after = sha256_file(src)
    if after != before:
        fail(EXIT_CHECK, "blocked", "the original changed while the working copy was written", before=before, after=after)
    if proc.returncode != 0 or not dest.is_file():
        fail(EXIT_CHECK, "blocked", "the conversion failed; no working copy exists",
             ffmpeg_error=proc.stderr.strip()[-600:])
    copy = probe_file(dest)
    record = {"tool": "working-copy", "tool_version": TOOL_VERSION, "ffmpeg": tool_version("ffmpeg"),
              "status": "working copy written", "original": str(src), "original_sha256": before,
              "original_unchanged": True, "working_copy": str(dest), "working_copy_sha256": copy.get("sha256"),
              "reason": [f["flag"] for f in info["flags"]] or ["requested"], "command": cmd, "written_at": now_iso(),
              "working_copy_probe": {k: copy.get(k) for k in ("width", "height", "avg_frame_rate", "frame_rate_mode",
                                                              "duration_seconds", "video_codec", "rotation_degrees",
                                                              "color_transfer", "has_audio")}}
    Path(str(dest) + ".record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    out(record)
    return 0


# --------------------------------------------------------------------------
# style measurement: cuts, shots, audio, frames
# --------------------------------------------------------------------------

def percentile(values: list[float], pct: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    k = (len(ordered) - 1) * pct
    lo, hi = math.floor(k), math.ceil(k)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def detect_cuts(path: Path, threshold: float, min_shot: float) -> dict:
    info = probe_file(path)
    if not info["probe_ok"] or not info.get("width"):
        fail(EXIT_CHECK, "probe failed", "no video stream to measure", probe=info)
    proc = subprocess.run(
        [need("ffmpeg"), "-hide_banner", "-nostdin", "-i", str(path), "-map", "0:v:0", "-an",
         "-vf", f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
        capture_output=True, text=True, timeout=7200,
    )
    if proc.returncode != 0:
        fail(EXIT_CHECK, "blocked", "cut detection failed", ffmpeg_error=proc.stderr.strip()[-500:])
    raw = [float(m.group(1)) for m in re.finditer(r"pts_time:([\d.]+)", proc.stderr)]
    cuts: list[float] = []
    for t in raw:
        if t >= min_shot and (not cuts or t - cuts[-1] >= min_shot):
            cuts.append(round(t, 3))
    duration = info["duration_seconds"]
    edges = [0.0, *cuts, duration]
    shots = [round(b - a, 3) for a, b in zip(edges, edges[1:]) if b - a > 0]
    dist = {
        "count": len(shots), "mean": round(statistics.fmean(shots), 3), "median": round(statistics.median(shots), 3),
        "min": min(shots), "max": max(shots),
        "p10": round(percentile(shots, 0.10), 3), "p90": round(percentile(shots, 0.90), 3),
    }
    return {
        "tool": "cuts", "tool_version": TOOL_VERSION, "ffmpeg": tool_version("ffmpeg"),
        "method": "ffmpeg select=gt(scene,T) with showinfo; cuts closer than min_shot merged",
        "thresholds": {"scene_threshold": threshold, "min_shot_seconds": min_shot},
        "evidence_tag": "measured", "file": str(path), "sha256": info["sha256"],
        "duration_seconds": duration, "cut_count": len(cuts), "cut_times_seconds": cuts,
        "time_to_first_cut_seconds": cuts[0] if cuts else None,
        "cuts_per_minute": round(len(cuts) / duration * 60, 2) if duration else None,
        "shot_lengths_seconds": shots, "shot_length_distribution": dist, "measured_at": now_iso(),
        "limits": "Scene detection finds hard visual changes. It misses dissolves and cuts between similar frames, "
                  "and can count a flash or a fast whip as a cut. A different threshold gives a different count. "
                  "A punch-in on the same take may or may not register.",
    }


def cmd_cuts(args: list[str]) -> int:
    threshold = float(take(args, "--threshold", "0.30"))
    min_shot = float(take(args, "--min-shot", "0.20"))
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py cuts <file> [--threshold 0.30] [--min-shot 0.20]")
    out(detect_cuts(in_workspace(args[0]), threshold, min_shot))
    return 0


def audio_profile(path: Path, noise_db: float, min_silence: float) -> dict:
    info = probe_file(path)
    if not info["probe_ok"]:
        fail(EXIT_CHECK, "probe failed", "footage unreadable", probe=info)
    base = {"tool": "audio-profile", "tool_version": TOOL_VERSION, "ffmpeg": tool_version("ffmpeg"),
            "file": str(path), "sha256": info["sha256"], "evidence_tag": "measured", "measured_at": now_iso(),
            "thresholds": {"silence_noise_db": noise_db, "silence_min_seconds": min_silence}}
    if not info.get("has_audio"):
        return {**base, "has_audio": False, "status": "no audio track",
                "integrated_lufs": UNAVAILABLE, "true_peak_dbtp": UNAVAILABLE, "silence_gaps": []}
    proc = subprocess.run(
        [need("ffmpeg"), "-hide_banner", "-nostdin", "-nostats", "-i", str(path), "-map", "0:a:0",
         "-af", f"ebur128=peak=true,silencedetect=noise={noise_db}dB:d={min_silence},astats=metadata=0:measure_perchannel=none",
         "-f", "null", "-"], capture_output=True, text=True, timeout=7200,
    )
    err = proc.stderr
    summary = err[err.rfind("Summary:"):] if "Summary:" in err else ""
    lufs = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", summary)
    peak = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", err)]
    gaps = [{"start": round(max(s, 0.0), 3), "end": round(e, 3), "seconds": round(e - max(s, 0.0), 3)}
            for s, e in zip(starts, ends)]
    if len(starts) > len(ends):
        s = max(starts[-1], 0.0)
        gaps.append({"start": round(s, 3), "end": info["duration_seconds"],
                     "seconds": round(info["duration_seconds"] - s, 3)})
    astats_peak = re.search(r"Peak level dB:\s+(-?[\d.]+|-inf)", err)

    def num(m):
        return UNAVAILABLE if m is None else (None if m.group(1) == "-inf" else float(m.group(1)))

    true_peak = num(peak)
    sample_peak = num(astats_peak)
    silent = lufs is not None and lufs.group(1) == "-inf" or (isinstance(sample_peak, float) and sample_peak <= -80)
    silent = bool(silent) or sample_peak is None
    clipping = isinstance(true_peak, float) and true_peak >= 0.0
    return {**base, "has_audio": True, "duration_seconds": info["duration_seconds"],
            "integrated_lufs": num(lufs), "loudness_range_lu": num(lra), "true_peak_dbtp": true_peak,
            "sample_peak_dbfs": sample_peak, "silent": silent, "clipping": clipping,
            "clipping_rule": "true peak at or above 0 dBTP",
            "silence_gaps": gaps, "silence_total_seconds": round(sum(g["seconds"] for g in gaps), 3),
            "music_present": UNAVAILABLE,
            "limits": "Loudness and peaks are measured. Whether music is present, and whether speech is intelligible "
                      "over it, is not measured here: listen, or run duck-check with speech windows. "
                      "No loudness target ships with this profile; take one from the owner or a cited current source."}


def cmd_audio_profile(args: list[str]) -> int:
    noise = float(take(args, "--noise-db", "-35"))
    gap = float(take(args, "--min-silence", "0.40"))
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py audio-profile <file> [--noise-db -35] [--min-silence 0.40]")
    out(audio_profile(in_workspace(args[0]), noise, gap))
    return 0


def window_rms_db(path: Path, start: float, end: float, band: tuple[float, float] | None) -> float | None:
    filters = [f"atrim=start={start}:end={end}", "asetpts=PTS-STARTPTS"]
    if band:
        filters += [f"highpass=f={band[0]}:p=2", f"highpass=f={band[0]}:p=2",
                    f"lowpass=f={band[1]}:p=2", f"lowpass=f={band[1]}:p=2"]
    filters.append("astats=metadata=0:measure_perchannel=none")
    proc = subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-nostats", "-i", str(path), "-map", "0:a:0",
                           "-af", ",".join(filters), "-f", "null", "-"], capture_output=True, text=True, timeout=3600)
    m = re.search(r"RMS level dB:\s+(-?[\d.]+|-inf)", proc.stderr)
    return None if not m or m.group(1) == "-inf" else float(m.group(1))


def parse_band(text: str | None) -> tuple[float, float] | None:
    if not text:
        return None
    lo, hi = text.split("-", 1)
    return float(lo), float(hi)


def cmd_duck_check(args: list[str]) -> int:
    speech = take(args, "--speech")
    voice_band, music_band = parse_band(take(args, "--voice-band")), parse_band(take(args, "--music-band"))
    min_margin = take(args, "--min-margin-db")
    if len(args) != 1 or not speech:
        fail(EXIT_USAGE, "blocked",
             "usage: editor_tools.py duck-check <file> --speech <intervals.json> [--voice-band LO-HI] [--music-band LO-HI] [--min-margin-db N]")
    path = in_workspace(args[0])
    rows = json.loads(in_workspace(speech).read_text(encoding="utf-8"))
    windows = [(float(r["start"]), float(r["end"])) for r in (rows.get("speech") if isinstance(rows, dict) else rows)]
    duration = probe_file(path)["duration_seconds"]
    gaps, cur = [], 0.0
    for s, e in sorted(windows):
        if s - cur >= 0.3:
            gaps.append((cur, s))
        cur = max(cur, e)
    if duration - cur >= 0.3:
        gaps.append((cur, duration))

    def mean_db(spans, band):
        vals = [v for v in (window_rms_db(path, s + 0.05, e - 0.05, band) for s, e in spans if e - s > 0.2) if v is not None]
        return round(statistics.fmean(vals), 2) if vals else None

    result = {
        "tool": "duck-check", "tool_version": TOOL_VERSION, "ffmpeg": tool_version("ffmpeg"), "file": str(path),
        "evidence_tag": "measured", "speech_windows": len(windows), "gap_windows": len(gaps),
        "bands_hz": {"voice": voice_band, "music": music_band},
        "voice_band_rms_db_in_speech": mean_db(windows, voice_band),
        "music_band_rms_db_in_speech": mean_db(windows, music_band) if music_band else UNAVAILABLE,
        "music_band_rms_db_in_gaps": mean_db(gaps, music_band) if music_band else UNAVAILABLE,
        "full_mix_rms_db_in_speech": mean_db(windows, None), "full_mix_rms_db_in_gaps": mean_db(gaps, None),
        "limits": "A full mix cannot be separated into voice and music. The band figures are meaningful only when "
                  "the two sit in the bands named. On real music they are a guide; listening decides.",
    }
    v, m = result["voice_band_rms_db_in_speech"], result["music_band_rms_db_in_speech"]
    if isinstance(v, float) and isinstance(m, float):
        result["voice_over_music_margin_db"] = round(v - m, 2)
        g = result["music_band_rms_db_in_gaps"]
        if isinstance(g, float):
            result["music_carve_depth_db"] = round(g - m, 2)
    ok = True
    if min_margin is not None:
        margin = result.get("voice_over_music_margin_db")
        ok = isinstance(margin, float) and margin >= float(min_margin)
        result["min_margin_db_required"] = float(min_margin)
        result["margin_source"] = "supplied by the caller; this profile ships no masking threshold"
    result["status"] = "pass" if ok else "fail"
    out(result)
    return 0 if ok else EXIT_CHECK


SCHEDULES = {
    # name: list of (until_second, step_seconds). The last step runs to the end.
    "short-form": [(3.0, 0.25), (10.0, 0.5), (30.0, 1.0), (None, 2.0)],
    "long-form": [(10.0, 0.5), (60.0, 2.0), (600.0, 10.0), (None, 30.0)],
}


def schedule_times(name: str, duration: float, limit: int) -> list[float]:
    times, t = [], 0.0
    for until, step in SCHEDULES[name]:
        end = duration if until is None else min(until, duration)
        while t < end - 1e-6:
            times.append(round(t, 3))
            t = round(t + step, 6)
    return times[:limit]


def session_dir() -> Path:
    path = workspace() / WS_META / "session" / "frames"
    path.mkdir(parents=True, exist_ok=True)
    return path


def cmd_frames(args: list[str]) -> int:
    name = take(args, "--schedule", "short-form")
    limit = int(take(args, "--max-frames", "120"))
    width = int(take(args, "--width", "480"))
    if len(args) != 1 or name not in SCHEDULES:
        fail(EXIT_USAGE, "blocked", f"usage: editor_tools.py frames <file> [--schedule {'|'.join(SCHEDULES)}] [--max-frames 120]")
    path = in_workspace(args[0])
    info = probe_file(path)
    if not info["probe_ok"] or not info.get("width"):
        fail(EXIT_CHECK, "probe failed", "no video stream to sample", probe=info)
    times = schedule_times(name, info["duration_seconds"], limit)
    dest = session_dir() / info["sha256"][:12]
    dest.mkdir(parents=True, exist_ok=True)
    frames = []
    for t in times:
        target = dest / f"t{t:09.3f}.jpg"
        if not target.is_file():
            subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-ss", str(t), "-i", str(path),
                            "-frames:v", "1", "-vf", f"scale={width}:-2", "-q:v", "4", "-y", str(target)],
                           capture_output=True, text=True, timeout=120)
        if target.is_file():
            frames.append({"time_seconds": t, "path": str(target)})
    is_reference = inside(path, workspace() / "references")
    out({"tool": "frames", "tool_version": TOOL_VERSION, "ffmpeg": tool_version("ffmpeg"), "file": str(path),
         "sha256": info["sha256"], "schedule": name, "schedule_definition": SCHEDULES[name],
         "max_frames": limit, "frame_width": width, "frame_count": len(frames), "frames": frames,
         "session_only": True, "is_reference_material": is_reference,
         "rule": "Sampled frames are for analysis only. They are session-only, never enter a project, a deliverable, "
                 "memory, or Kanban, and are deleted with session-clean when the task ends. Looking at a frame sends "
                 "it to the configured model provider.",
         "evidence_note": "What is seen in these frames is tagged observed, not measured."})
    return 0


def cmd_contact_sheet(args: list[str]) -> int:
    dest_arg = take(args, "--out")
    count = int(take(args, "--count", "12"))
    cols = int(take(args, "--columns", "4"))
    if len(args) != 1 or not dest_arg:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py contact-sheet <file> --out <sheet.jpg> [--count 12] [--columns 4]")
    path = in_workspace(args[0])
    ws = workspace()
    if inside(path, ws / "references"):
        fail(EXIT_REFUSED, "blocked", "a contact sheet of a reference video would be a saved copy of its frames",
             fix="use the frames tool; its output is session-only")
    dest = in_workspace(dest_arg, must_exist=False)
    if dest.exists():
        fail(EXIT_REFUSED, "blocked", f"output already exists and will not be overwritten: {dest}")
    info = probe_file(path)
    duration = info["duration_seconds"]
    rows = math.ceil(count / cols)
    step = duration / count
    times = [round(step * (i + 0.5), 3) for i in range(count)]
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run([need("ffmpeg"), "-hide_banner", "-nostdin", "-loglevel", "error", "-i", str(path),
                           "-vf", f"fps={count}/{duration},scale=360:-2,tile={cols}x{rows}", "-frames:v", "1",
                           "-q:v", "3", str(dest)], capture_output=True, text=True, timeout=1800)
    if proc.returncode != 0 or not dest.is_file():
        fail(EXIT_CHECK, "blocked", "contact sheet failed", ffmpeg_error=proc.stderr.strip()[-400:])
    out({"tool": "contact-sheet", "tool_version": TOOL_VERSION, "file": str(path), "sheet": str(dest),
         "frames": count, "columns": cols, "approx_times_seconds": times, "sha256": sha256_file(dest)})
    return 0


def cmd_session_clean(args: list[str]) -> int:
    root = workspace() / WS_META / "session"
    removed = sum(1 for p in root.rglob("*") if p.is_file()) if root.is_dir() else 0
    shutil.rmtree(root, ignore_errors=True)
    out({"tool": "session-clean", "status": "session frames deleted", "files_removed": removed, "folder": str(root)})
    return 0


# --------------------------------------------------------------------------
# outlier scoring
# --------------------------------------------------------------------------

EXCLUSION_FLAGS = ("paid", "boosted", "repost", "compilation", "news_event")


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def score_outliers(data: dict) -> dict:
    """views / the publishing account's median views over a stated baseline.

    No threshold is applied. Candidates are ranked; the owner chooses how
    many to study."""
    required = ("platform", "format", "niche_or_keyword", "time_window", "accessed_at", "source_route", "videos")
    missing = [k for k in required if is_empty(data.get(k))]
    if missing:
        fail(EXIT_CHECK, "blocked", "the dataset is missing required study bounds", missing=missing)
    min_accounts = int(data.get("min_accounts") or 3)
    min_baseline = int(data.get("min_baseline") or 5)
    by_account: dict[str, list[dict]] = {}
    for video in data["videos"]:
        by_account.setdefault(str(video.get("account")), []).append(video)

    accounts, scored, unscored = {}, [], []
    for account, videos in sorted(by_account.items()):
        same_format = [v for v in videos if (v.get("format") or data["format"]) == data["format"]]
        baseline = [v["views"] for v in same_format if is_number(v.get("views")) and not v.get("candidate_only")]
        median = statistics.median(baseline) if baseline else None
        accounts[account] = {"baseline_sample_size": len(baseline),
                             "baseline_median_views": median if median is not None else UNAVAILABLE,
                             "baseline_thin": len(baseline) < min_baseline}
        for v in videos:
            row = {"video_id": v.get("video_id"), "account": account, "url": v.get("url") or UNAVAILABLE,
                   "format": v.get("format") or data["format"],
                   "views": v["views"] if is_number(v.get("views")) else UNAVAILABLE,
                   "published_at": v.get("published_at") or UNAVAILABLE,
                   "age_days": v["age_days"] if is_number(v.get("age_days")) else UNAVAILABLE,
                   "flags": [f for f in EXCLUSION_FLAGS if v.get(f) is True],
                   "flags_undetermined": [f for f in EXCLUSION_FLAGS if v.get(f) is None],
                   "baseline_sample_size": len(baseline), "baseline_thin": len(baseline) < min_baseline}
            if row["format"] != data["format"]:
                row.update(outlier_score=UNAVAILABLE, reason="different format from the study; not comparable")
                unscored.append(row)
            elif not is_number(v.get("views")) or not median:
                row.update(outlier_score=UNAVAILABLE,
                           reason="views unavailable" if not is_number(v.get("views")) else "no baseline median for this account")
                unscored.append(row)
            else:
                row["outlier_score"] = round(v["views"] / median, 3)
                row["excluded"] = bool(row["flags"])
                scored.append(row)
    ranked = sorted((r for r in scored if not r["excluded"]), key=lambda r: -r["outlier_score"])
    for i, r in enumerate(ranked, 1):
        r["rank"] = i
    excluded = sorted((r for r in scored if r["excluded"]), key=lambda r: -r["outlier_score"])
    ranked_accounts = sorted({r["account"] for r in ranked})
    warnings = []
    if len(ranked_accounts) < min_accounts:
        warnings.append({"flag": "too_few_accounts",
                         "detail": f"{len(ranked_accounts)} account(s) with scorable videos; {min_accounts} wanted",
                         "effect": "One creator's habits cannot be told apart from a style. Lower the blueprint's "
                                   "confidence and say so."})
    thin = [a for a, rec in accounts.items() if rec["baseline_thin"]]
    if thin:
        warnings.append({"flag": "thin_baseline", "detail": f"baseline under {min_baseline} videos for: {', '.join(thin)}",
                         "effect": "A median over a few videos is unstable. Treat these scores as weak."})
    if any(r["age_days"] == UNAVAILABLE for r in ranked):
        warnings.append({"flag": "age_unavailable", "detail": "video age missing for some candidates",
                         "effect": "A two-day-old video and a two-year-old video are not comparable on lifetime views."})
    if any(r["flags_undetermined"] for r in ranked):
        warnings.append({"flag": "exclusions_undetermined",
                         "detail": "paid, boosted, repost, compilation or news-event status could not be determined for some candidates",
                         "effect": "They are ranked, not cleared. Confirm with the owner before deep analysis."})
    return {
        "tool": "outlier-score", "tool_version": TOOL_VERSION, "computed_at": now_iso(),
        "platform": data["platform"], "format": data["format"], "niche_or_keyword": data["niche_or_keyword"],
        "time_window": data["time_window"], "accessed_at": data["accessed_at"], "source_route": data["source_route"],
        "baseline_method": "median views of the same account's videos in the same format within the dataset, "
                           "excluding rows marked candidate_only",
        "ranking_method": "outlier_score = views / account baseline median; ranked descending; no cutoff applied",
        "threshold": "none. The owner confirms how many to study.",
        "accounts": accounts, "candidates_reviewed": len(data["videos"]), "ranked": ranked,
        "excluded": excluded, "unscored": unscored, "warnings": warnings,
        "evidence_depth": "metadata_only",
        "limits": "Scores describe view counts relative to each account's own baseline at the access time. They say "
                  "nothing about why a video performed, and nothing about cuts, captions, or pacing. Public figures "
                  "change by the hour.",
    }


def cmd_outlier_score(args: list[str]) -> int:
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py outlier-score <dataset.json|yaml>")
    out(score_outliers(load_data(in_workspace(args[0]))))
    return 0


# --------------------------------------------------------------------------
# transcript timing: dead-air proposal
# --------------------------------------------------------------------------

def cmd_dead_air(args: list[str]) -> int:
    min_gap = float(take(args, "--min-gap", "0.60"))
    pad = float(take(args, "--pad", "0.10"))
    source = take(args, "--source", "take.mp4")
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py dead-air <words.json> [--min-gap 0.60] [--pad 0.10] [--source file]")
    data = json.loads(in_workspace(args[0]).read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data
    words = sorted(({"start": float(w["start"]), "end": float(w["end"]), "text": str(w.get("text") or w.get("word") or "")}
                    for w in words), key=lambda w: w["start"])
    if not words:
        fail(EXIT_CHECK, "blocked", "the transcript has no timed words")
    keeps, cuts = [], []
    start, last_end = words[0]["start"], words[0]["end"]
    for w in words[1:]:
        if w["start"] - last_end >= min_gap:
            keeps.append([max(0.0, start - pad), last_end + pad])
            cuts.append({"from": round(last_end + pad, 3), "to": round(w["start"] - pad, 3),
                         "seconds_removed": round(w["start"] - last_end - 2 * pad, 3), "reason": "dead air between words"})
            start = w["start"]
        last_end = max(last_end, w["end"])
    keeps.append([max(0.0, start - pad), last_end + pad])
    clips, t = [], 0.0
    for i, (a, b) in enumerate(keeps, 1):
        dur = round(b - a, 3)
        clips.append({"id": f"keep-{i:02d}", "src": source, "data-start": round(t, 3), "data-duration": dur,
                      "data-media-start": round(a, 3), "data-track-index": 0, "data-has-audio": True,
                      "first_words": " ".join(w["text"] for w in words if a <= w["start"] < b)[:60]})
        t = round(t + dur, 3)
    out({"tool": "dead-air", "tool_version": TOOL_VERSION, "status": "proposal",
         "thresholds": {"min_gap_seconds": min_gap, "pad_seconds": pad}, "evidence_tag": "measured",
         "source_duration_covered_seconds": round(words[-1]["end"] - words[0]["start"], 3),
         "timeline_duration_seconds": t, "seconds_removed": round(sum(c["seconds_removed"] for c in cuts), 3),
         "cuts": cuts, "clips": clips,
         "recipe": "hard cut / split and splice from creator-editing-recipes.md: data-start, data-duration, data-media-start, data-track-index",
         "rule": "This is a proposal for the paper edit. Apply it only after the paper edit is approved, and check "
                 "that no cut changes the meaning of a sentence. Timings are only as good as the transcript."})
    return 0


# --------------------------------------------------------------------------
# safe zones
# --------------------------------------------------------------------------

def cmd_safe_zone(args: list[str]) -> int:
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py safe-zone <plan.json|yaml>")
    plan = load_data(in_workspace(args[0]))
    canvas, zone = plan.get("canvas") or {}, plan.get("safe_zone") or {}
    for key in ("width", "height"):
        if not is_number(canvas.get(key)):
            fail(EXIT_CHECK, "blocked", f"canvas.{key} is missing")
    missing_source = [k for k in ("source_url", "accessed_at") if is_empty(zone.get(k))]
    if missing_source and zone.get("source") != "owner":
        fail(EXIT_CHECK, "blocked", "the safe zone has no recorded source",
             missing=missing_source,
             fix="record the official source URL and access date, or mark source: owner with the owner's confirmed values. "
                 "This profile ships no safe-zone numbers.")
    left, right = zone.get("left", 0), canvas["width"] - zone.get("right", 0)
    top, bottom = zone.get("top", 0), canvas["height"] - zone.get("bottom", 0)
    results, ok = [], True
    for el in plan.get("elements") or []:
        x, y, w, h = el["x"], el["y"], el["width"], el["height"]
        over = {"left": max(0, left - x), "top": max(0, top - y),
                "right": max(0, x + w - right), "bottom": max(0, y + h - bottom)}
        passed = not any(over.values())
        ok = ok and passed
        results.append({"id": el.get("id"), "pass": passed, "overflow_px": {k: v for k, v in over.items() if v}})
    out({"tool": "safe-zone", "tool_version": TOOL_VERSION, "status": "pass" if ok else "fail", "canvas": canvas,
         "safe_area_px": {"left": left, "top": top, "right": right, "bottom": bottom},
         "safe_zone_source": {k: zone.get(k) for k in ("source", "source_url", "accessed_at", "platform", "surface")},
         "elements": results,
         "limits": "Boxes come from the overlay plan, not from the render. Confirm on snapshots."})
    return 0 if ok else EXIT_CHECK


# --------------------------------------------------------------------------
# evidence-rule checks for studies, blueprints, proposals
# --------------------------------------------------------------------------

STUDY_FIELDS = ["study_id", "platform", "format", "niche_or_keyword", "query_terms", "time_window", "accessed_at",
                "source_route", "baseline_method", "baseline_sample_size", "candidates_reviewed", "outliers_selected",
                "contrast_set", "ranking_method", "exclusions", "evidence_depth", "limits", "valid_until"]
EVIDENCE_DEPTHS = {"metadata_only", "owner_supplied_reference", "observed_playback"}
BLUEPRINT_FIELDS = ["blueprint_id", "study_id", "platform", "format", "evidence_depth", "reference_count",
                    "duration_range", "opening_structure", "cut_rhythm", "shot_length_distribution",
                    "framing_and_reframes", "punch_ins_and_camera_moves", "caption_treatment", "on_screen_text",
                    "b_roll_and_cutaways", "graphics_and_overlays", "transitions", "music_and_sound_design",
                    "color_and_treatment", "pacing_curve", "pattern_interrupts", "ending_structure",
                    "features_shared_with_contrast_set", "features_distinct_to_outliers", "feature_evidence_tags",
                    "analysis_tools_and_thresholds", "hyperframes_mapping", "not_reproducible_with_bundled_tools",
                    "do_not_copy", "confidence", "valid_until"]
# Features a metadata-only study cannot support: they need the video itself.
PLAYBACK_FEATURES = ["opening_structure", "cut_rhythm", "shot_length_distribution", "framing_and_reframes",
                     "punch_ins_and_camera_moves", "caption_treatment", "on_screen_text", "b_roll_and_cutaways",
                     "graphics_and_overlays", "transitions", "music_and_sound_design", "color_and_treatment",
                     "pacing_curve", "pattern_interrupts", "ending_structure"]
MEASURABLE = {"duration_range", "cut_rhythm", "shot_length_distribution"}
EVIDENCE_TAGS = {"measured", "observed", "inferred"}
NOT_SUPPORTED = "not supported at this evidence depth"

PROMISE_PATTERNS = [
    r"\bguarantee[ds]?\b", r"\bwill (go|get|hit|reach|drive|double|triple|boost|increase|perform|outperform)\b",
    r"\bgo(es|ing)? viral\b", r"\bproven to\b", r"\bexpect(ed)? (similar|the same|more) (views|reach|followers|revenue|results)\b",
    r"\bsimilar (views|reach|results|performance)\b", r"\bwill (work|win)\b", r"\b\d+\s?[x%] more (views|reach|followers|revenue)\b",
    r"\bthe reason (it|this|that video) (went|performed|worked)\b", r"\bbecause of (the|its) (edit|cut|captions|pacing)\b",
]
NEGATION = re.compile(r"\b(no|not|never|cannot|can't|won't|does not|doesn't|do not|don't|without|nothing|neither|nor|unknown|isn't|is not)\b")


def parse_date(value) -> _dt.date | None:
    try:
        return _dt.date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def finish(kind: str, path: Path, problems: list[str], warnings: list[str], extra: dict | None = None) -> int:
    out({"tool": f"check-{kind}", "tool_version": TOOL_VERSION, "file": str(path),
         "status": "pass" if not problems else "fail", "problems": problems, "warnings": warnings, **(extra or {})})
    return 0 if not problems else EXIT_CHECK


def cmd_check_study(args: list[str]) -> int:
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py check-study <outlier-study.yaml>")
    path = in_workspace(args[0])
    d = load_data(path) or {}
    problems, warnings = [], []
    for key in STUDY_FIELDS:
        if key not in d:
            problems.append(f"missing field: {key}")
    for key in ("study_id", "platform", "format", "niche_or_keyword", "time_window", "accessed_at", "source_route",
                "baseline_method", "ranking_method", "limits", "valid_until"):
        if key in d and is_empty(d[key]):
            problems.append(f"{key} is empty")
    if d.get("evidence_depth") not in EVIDENCE_DEPTHS:
        problems.append("evidence_depth must be metadata_only, owner_supplied_reference, or observed_playback")
    outliers = d.get("outliers_selected") or []
    contrast = d.get("contrast_set") or []
    accounts = {str(o.get("account")) for o in outliers if isinstance(o, dict) and not is_empty(o.get("account"))}
    min_accounts = int(d.get("min_accounts") or 3)
    if len(accounts) < min_accounts:
        if is_empty(d.get("too_few_accounts_note")):
            problems.append(f"outliers come from {len(accounts)} account(s), fewer than {min_accounts}, and "
                            "too_few_accounts_note does not say so")
        else:
            warnings.append(f"too few accounts ({len(accounts)}): confidence must be lowered")
    if not contrast:
        problems.append("contrast_set is empty: ordinary videos from the same accounts are needed to tell a habit from a style")
    else:
        contrast_accounts = {str(c.get("account")) for c in contrast if isinstance(c, dict)}
        if accounts and not accounts & contrast_accounts:
            problems.append("contrast_set shares no account with the outliers")
    for o in outliers:
        if isinstance(o, dict):
            for key in ("views", "baseline_median_views", "outlier_score"):
                if key in o and is_empty(o[key]):
                    problems.append(f"outlier {o.get('video_id')}: {key} is blank; write Unavailable, never leave it empty or guess")
    if re.search(r"(?i)\b(over|above|more than|at least)\s+[\d,.]+\s*(k|m|million|thousand)?\s+views\b", str(d.get("ranking_method", ""))):
        problems.append("ranking_method states a raw view cutoff: an outlier is relative to the account's own baseline")
    valid = parse_date(d.get("valid_until"))
    stale = bool(valid and valid < _dt.date.today())
    if stale:
        warnings.append(f"study went stale on {valid}: flag it and ask whether to refresh or reuse")
    if d.get("evidence_depth") == "metadata_only":
        warnings.append("metadata_only supports findings about length, title and packaging only; no cut, caption or pacing finding")
    return finish("study", path, problems, warnings, {"stale": stale, "accounts": sorted(accounts),
                                                     "evidence_depth": d.get("evidence_depth")})


def cmd_check_blueprint(args: list[str]) -> int:
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py check-blueprint <style-blueprint.yaml>")
    path = in_workspace(args[0])
    d = load_data(path) or {}
    problems, warnings = [], []
    for key in BLUEPRINT_FIELDS:
        if key not in d:
            problems.append(f"missing field: {key}")
    depth = d.get("evidence_depth")
    if depth not in EVIDENCE_DEPTHS:
        problems.append("evidence_depth must be metadata_only, owner_supplied_reference, or observed_playback")
    tags = d.get("feature_evidence_tags") or {}
    if not isinstance(tags, dict):
        problems.append("feature_evidence_tags must map each described feature to measured, observed, or inferred")
        tags = {}
    described = [f for f in PLAYBACK_FEATURES + ["duration_range"]
                 if not is_empty(d.get(f)) and d.get(f) != NOT_SUPPORTED]
    if depth == "metadata_only":
        for f in PLAYBACK_FEATURES:
            if not is_empty(d.get(f)) and d.get(f) != NOT_SUPPORTED:
                problems.append(f"{f}: a metadata_only study cannot support a finding about cuts, captions, or pacing. "
                                f"Write '{NOT_SUPPORTED}'.")
    for f in described:
        tag = tags.get(f)
        if tag not in EVIDENCE_TAGS:
            problems.append(f"{f}: no evidence tag (measured, observed, or inferred)")
        elif tag == "measured" and f not in MEASURABLE:
            problems.append(f"{f}: tagged measured, but no bundled tool measures it. Tag it observed or inferred.")
        elif tag == "measured" and is_empty(d.get("analysis_tools_and_thresholds")):
            problems.append(f"{f}: tagged measured, but analysis_tools_and_thresholds is empty")
    if is_empty(d.get("do_not_copy")):
        problems.append("do_not_copy is empty: list what must not be copied from each reference")
    if is_empty(d.get("confidence")):
        problems.append("confidence is empty")
    if not is_number(d.get("reference_count")) or d.get("reference_count", 0) < 1:
        problems.append("reference_count must be a positive number")
    shared, distinct = d.get("features_shared_with_contrast_set"), d.get("features_distinct_to_outliers")
    if depth != "metadata_only" and shared is None and distinct is None:
        problems.append("no comparison against the contrast set is recorded")
    if isinstance(shared, list) and isinstance(distinct, list) and set(map(str, shared)) & set(map(str, distinct)):
        problems.append("a feature is listed as both shared with the contrast set and distinct to the outliers")
    valid = parse_date(d.get("valid_until"))
    if valid is None:
        problems.append("valid_until is missing or not an ISO date")
    stale = bool(valid and valid < _dt.date.today())
    if stale:
        warnings.append(f"blueprint went stale on {valid}: flag it and ask whether to refresh or reuse")
    blob = json.dumps({k: v for k, v in d.items() if k not in {"do_not_copy", "limits"}}, default=str).lower()
    for pattern in PROMISE_PATTERNS:
        for m in re.finditer(pattern, blob):
            window = blob[max(0, m.start() - 60):m.start()]
            if not NEGATION.search(window):
                problems.append(f"result or cause claim: '{m.group(0)}'. A blueprint describes technique; it explains and promises nothing.")
                break
    return finish("blueprint", path, problems, warnings, {"stale": stale, "evidence_depth": depth,
                                                         "features_described": described})


def cmd_check_proposal(args: list[str]) -> int:
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py check-proposal <style-match-proposal.md>")
    path = in_workspace(args[0])
    text = path.read_text(encoding="utf-8")
    low = text.lower()
    problems, warnings = [], []
    for option in ("house style", "outlier-matched", "hybrid"):
        if option not in low:
            problems.append(f"option missing: {option}")
    for needed, label in (("recommend", "a recommendation with its reason"), ("cannot show", "what the evidence cannot show"),
                          ("compar", "how the result will be compared after posting")):
        if needed not in low:
            problems.append(f"missing: {label}")
    for line_no, line in enumerate(text.splitlines(), 1):
        l = line.lower()
        for pattern in PROMISE_PATTERNS:
            m = re.search(pattern, l)
            if m and not NEGATION.search(l[:m.start()]):
                problems.append(f"line {line_no}: result or cause claim: '{m.group(0)}'. A style match is a test of a hypothesis.")
    return finish("proposal", path, problems, warnings)


def cmd_load(args: list[str]) -> int:
    subset = "--subset" in args
    args = [a for a in args if a != "--subset"]
    if len(args) != 1:
        fail(EXIT_USAGE, "blocked", "usage: editor_tools.py load <file> [--subset]")
    path = Path(args[0])
    out(load_data(path, force_subset=subset))
    return 0


TOOLS = {
    "probe": cmd_probe, "working-copy": cmd_working_copy, "cuts": cmd_cuts, "audio-profile": cmd_audio_profile,
    "duck-check": cmd_duck_check, "frames": cmd_frames, "contact-sheet": cmd_contact_sheet,
    "session-clean": cmd_session_clean, "outlier-score": cmd_outlier_score, "dead-air": cmd_dead_air,
    "safe-zone": cmd_safe_zone, "check-study": cmd_check_study, "check-blueprint": cmd_check_blueprint,
    "check-proposal": cmd_check_proposal, "load": cmd_load,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] in {"-h", "--help", "help"}:
        print(__doc__)
        return 0
    tool = TOOLS.get(argv[0])
    if tool is None:
        fail(EXIT_USAGE, "blocked", f"unknown tool: {argv[0]}", tools=sorted(TOOLS))
    return tool(list(argv[1:]))


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        sys.exit(130)
