"""Small shared helpers: subprocess, ffprobe, logging."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


class ClipForgeError(RuntimeError):
    """An error we expect and can explain to the user in one line."""


def log(msg: str) -> None:
    print(f"› {msg}", file=sys.stderr, flush=True)


def require_bin(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise ClipForgeError(f"'{name}' not found on PATH. Install it first (see README).")
    return path


def run(cmd: list[str], *, quiet: bool = True) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise ClipForgeError(f"{Path(cmd[0]).name} failed:\n{tail}")
    if not quiet and proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return proc.stdout


@dataclass(frozen=True)
class MediaInfo:
    width: int
    height: int
    duration: float
    fps: float
    has_audio: bool


def probe(path: Path) -> MediaInfo:
    out = run([
        require_bin("ffprobe"), "-v", "error", "-print_format", "json",
        "-show_streams", "-show_format", str(path),
    ])
    data = json.loads(out)
    video = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if video is None:
        raise ClipForgeError(f"No video stream in {path}")
    num, _, den = video.get("avg_frame_rate", "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    # Rotated phone footage reports pre-rotation size.
    rotation = abs(int(video.get("tags", {}).get("rotate", 0) or 0))
    for sd in video.get("side_data_list", []):
        rotation = abs(int(sd.get("rotation", rotation) or rotation))
    w, h = int(video["width"]), int(video["height"])
    if rotation in (90, 270):
        w, h = h, w
    return MediaInfo(
        width=w,
        height=h,
        duration=float(data["format"].get("duration") or video.get("duration") or 0),
        fps=fps or 30.0,
        has_audio=any(s["codec_type"] == "audio" for s in data["streams"]),
    )


def fmt_ts(seconds: float) -> str:
    m, s = divmod(max(0.0, seconds), 60)
    return f"{int(m):02d}:{s:05.2f}"
