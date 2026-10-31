"""Cut, reframe to 1080x1920, burn captions + hook + progress bar, normalise loudness."""

from __future__ import annotations

from pathlib import Path

from .captions import build_ass
from .reframe import crop_x_expr, plan as reframe_plan
from .transcribe import words_between
from .util import probe, require_bin, run

OUT_W, OUT_H = 1080, 1920


def _filter_escape(path: Path) -> str:
    return str(path).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def _video_chain(p, info) -> tuple[str, float]:
    """Return (filter graph producing [v0], caption_y fraction)."""
    if p.layout == "blur":
        fg_h = round(OUT_W * info.height / info.width / 2) * 2
        caption_y = min(0.84, (OUT_H + fg_h) / 2 / OUT_H + 0.06)
        return (
            "[0:v]split=2[a][b];"
            f"[a]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=increase,crop={OUT_W}:{OUT_H},"
            "boxblur=24:2,eq=brightness=-0.10:saturation=1.1[bg];"
            f"[b]scale={OUT_W}:-2[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2[v0]",
            caption_y,
        )
    if p.layout == "native":
        return (
            f"[0:v]scale={OUT_W}:{OUT_H}:force_original_aspect_ratio=decrease,"
            f"pad={OUT_W}:{OUT_H}:(ow-iw)/2:(oh-ih)/2:black[v0]",
            None,
        )
    return (
        f"[0:v]crop={p.crop_w}:{info.height}:x='{crop_x_expr(p.shots)}':y=0,"
        f"scale={OUT_W}:{OUT_H}:flags=lanczos[v0]",
        None,
    )


def render_clip(source: Path, transcript: dict, start: float, end: float, hook: str,
                out: Path, cfg: dict) -> Path:
    ffmpeg = require_bin("ffmpeg")
    info = probe(source)
    dur = end - start
    out.parent.mkdir(parents=True, exist_ok=True)

    p = reframe_plan(source, start, end, info, cfg["layout"])
    graph, caption_y = _video_chain(p, info)

    ass = out.with_suffix(".ass")
    ass.write_text(build_ass(words_between(transcript, start, end), start, end, hook, cfg, caption_y),
                   encoding="utf-8")
    subs = f"subtitles='{_filter_escape(ass)}'"
    if cfg.get("fonts_dir"):
        subs += f":fontsdir='{_filter_escape(Path(cfg['fonts_dir']).expanduser())}'"

    bar = ""
    if cfg.get("progress_bar", True):
        accent = cfg["accent"].lstrip("#")
        bar = f",drawbox=x=0:y=0:w='iw*t/{dur:.3f}':h=10:color=0x{accent}@0.95:t=fill"

    graph += f";[v0]fps=30,{subs}{bar},format=yuv420p[v]"
    cmd = [
        ffmpeg, "-y", "-v", "error",
        "-ss", f"{start:.3f}", "-i", str(source), "-t", f"{dur:.3f}",
        "-filter_complex", graph, "-map", "[v]",
    ]
    if info.has_audio:
        cmd += ["-map", "0:a:0", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000",
                "-c:a", "aac", "-b:a", "160k"]
    cmd += [
        "-c:v", "libx264", "-preset", cfg["preset"], "-crf", str(cfg["crf"]),
        "-profile:v", "high", "-movflags", "+faststart", str(out),
    ]
    run(cmd)
    return out
