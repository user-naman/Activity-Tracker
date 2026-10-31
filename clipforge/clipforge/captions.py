"""Build an ASS subtitle file: word-highlighted captions plus a boxed hook title."""

from __future__ import annotations

import re
import textwrap

W, H = 1080, 1920


def ass_color(hex_rgb: str, alpha: int = 0) -> str:
    """'#RRGGBB' -> ASS '&HAABBGGRR'."""
    h = hex_rgb.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(text: str) -> str:
    return text.replace("\\", "").replace("{", "(").replace("}", ")")


def chunk_words(words: list[dict], per_chunk: int, max_gap: float = 0.6) -> list[list[dict]]:
    """Group words into short on-screen phrases; break on punctuation and pauses."""
    chunks: list[list[dict]] = []
    cur: list[dict] = []
    for i, w in enumerate(words):
        if cur and (len(cur) >= per_chunk or w["start"] - cur[-1]["end"] > max_gap):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.?!,;:]$", w["word"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(words: list[dict], clip_start: float, clip_end: float, hook: str, cfg: dict,
              caption_y: float | None = None) -> str:
    """`words` carry absolute source timestamps; output is relative to clip_start."""
    font = cfg["font"]
    size = int(cfg["font_size"])
    accent = ass_color(cfg["accent"])
    white, black = ass_color("#FFFFFF"), ass_color("#000000")
    y = int(H * (caption_y if caption_y is not None else cfg["caption_y"]))
    upper = cfg.get("uppercase", True)
    dur = clip_end - clip_start

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,{font},{size},{white},{white},{black},{ass_color('#000000', 0x80)},-1,0,0,0,100,100,0,0,1,7,3,5,60,60,0,1
Style: Hook,{font},{int(size * 0.72)},{black},{black},{white},{white},-1,0,0,0,100,100,0,0,3,22,0,8,90,90,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []

    hook_end = min(float(cfg["hook_seconds"]), dur)
    if hook and hook_end > 0:
        hook_txt = _clean(hook.upper() if upper else hook)
        wrapped = r"\N".join(textwrap.wrap(hook_txt, width=20)[:3])
        events.append(
            f"Dialogue: 2,{ass_time(0)},{ass_time(hook_end)},Hook,,0,0,0,,"
            f"{{\\pos({W // 2},300)\\fad(120,180)}}{wrapped}"
        )

    rel = [
        {**w, "start": w["start"] - clip_start, "end": w["end"] - clip_start}
        for w in words if w["end"] > clip_start and w["start"] < clip_end
    ]
    chunks = chunk_words(rel, int(cfg["words_per_chunk"]))
    for k, chunk in enumerate(chunks):
        tokens = [_clean(w["word"].upper() if upper else w["word"]) for w in chunk]
        chunk_end = chunk[-1]["end"] + 0.12
        if k + 1 < len(chunks):  # never overlap the next phrase
            chunk_end = min(chunk_end, chunks[k + 1][0]["start"])
        for i, w in enumerate(chunk):
            start = max(0.0, w["start"])
            end = chunk[i + 1]["start"] if i + 1 < len(chunk) else chunk_end
            if end <= start:
                continue
            parts = [
                f"{{\\c{accent}\\fscx108\\fscy108}}{t}{{\\c{white}\\fscx100\\fscy100}}" if j == i else t
                for j, t in enumerate(tokens)
            ]
            pop = r"\fscx92\fscy92\t(0,90,\fscx100\fscy100)" if i == 0 else ""
            events.append(
                f"Dialogue: 1,{ass_time(start)},{ass_time(min(end, dur))},Cap,,0,0,0,,"
                f"{{\\pos({W // 2},{y}){pop}}}" + " ".join(parts)
            )
    return header + "\n".join(events) + "\n"
