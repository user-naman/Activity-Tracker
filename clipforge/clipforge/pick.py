"""Choose the moments worth clipping.

Two pickers:
  local  free, offline heuristics over the transcript
  llm    Claude reads the transcript TEXT only (never video), once per source, cached to disk
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import Campaign
from .util import ClipForgeError, log

HOOK_WORDS = {
    "never", "always", "secret", "mistake", "biggest", "truth", "why", "how", "actually",
    "nobody", "stop", "million", "billion", "best", "worst", "crazy", "insane", "wrong",
    "everyone", "nothing", "only", "first", "last", "hate", "love", "money", "rich", "broke",
    "fired", "quit", "died", "learned", "regret", "honestly", "problem", "real",
}
FILLER_STARTS = ("and ", "so ", "um", "uh", "but ", "like ", "yeah", "okay", "right", "because ")


@dataclass
class Pick:
    start: float
    end: float
    hook: str
    caption: str
    score: float
    reason: str


# ── shared helpers ───────────────────────────────────────────────────────────

def _all_words(transcript: dict) -> list[dict]:
    return [w for seg in transcript["segments"] for w in seg["words"]]


def snap(transcript: dict, start: float, end: float) -> tuple[float, float]:
    """Snap to word boundaries so clips never cut mid-word; pad slightly for breath."""
    words = _all_words(transcript)
    if not words:
        return start, end
    first = min(words, key=lambda w: abs(w["start"] - start))
    last = min(words, key=lambda w: abs(w["end"] - end))
    s, e = max(0.0, first["start"] - 0.08), last["end"] + 0.25
    return round(s, 3), round(max(e, s + 1), 3)


def _overlaps(a: Pick, b: Pick) -> bool:
    return a.start < b.end and b.start < a.end


def _dedupe(picks: list[Pick], limit: int) -> list[Pick]:
    chosen: list[Pick] = []
    for p in sorted(picks, key=lambda p: p.score, reverse=True):
        if not any(_overlaps(p, c) for c in chosen):
            chosen.append(p)
        if len(chosen) == limit:
            break
    return sorted(chosen, key=lambda p: p.start)


def build_caption(body: str, campaign: Campaign) -> str:
    parts = [body.strip()]
    if campaign.mention:
        parts.append(campaign.mention.strip())
    if campaign.hashtags:
        parts.append(" ".join(h if h.startswith("#") else f"#{h}" for h in campaign.hashtags))
    return "\n\n".join(p for p in parts if p)


def _short_hook(text: str, max_words: int = 8) -> str:
    text = re.split(r"(?<=[.?!])\s", text.strip())[0]
    words = text.split()
    hook = " ".join(words[:max_words]).rstrip(",;:")
    return hook + ("…" if len(words) > max_words else "")


# ── local picker ─────────────────────────────────────────────────────────────

def _hook_score(text: str) -> float:
    t = text.lower()
    tokens = set(re.findall(r"[a-z']+", t))
    score = 1.5 * len(tokens & HOOK_WORDS)
    score += 2.0 if "?" in text[:120] else 0
    score += 1.0 if re.search(r"\d", text[:120]) else 0
    score += 1.0 if re.search(r"\b(you|your)\b", t[:120]) else 0
    score -= 2.0 if t.startswith(FILLER_STARTS) else 0
    return score


def pick_local(transcript: dict, campaign: Campaign, cfg: dict) -> list[Pick]:
    segs = transcript["segments"]
    lo, hi, n = cfg["min_seconds"], cfg["max_seconds"], cfg["clips_per_video"]
    candidates: list[Pick] = []
    for i, first in enumerate(segs):
        text, j = first["text"], i
        while j + 1 < len(segs) and segs[j + 1]["end"] - first["start"] <= hi:
            j += 1
            text += " " + segs[j]["text"]
            dur = segs[j]["end"] - first["start"]
            if dur < lo:
                continue
            words = sum(len(s["words"]) for s in segs[i:j + 1])
            density = words / dur                                  # fast talkers retain better
            ends_clean = segs[j]["text"].rstrip().endswith((".", "!", "?"))
            score = _hook_score(first["text"]) * 2 + _hook_score(text) * 0.3 \
                + min(density, 4) + (1.5 if ends_clean else -1) - abs(dur - 40) / 20
            start, end = snap(transcript, first["start"], segs[j]["end"])
            candidates.append(Pick(
                start=start, end=end,
                hook=_short_hook(first["text"]),
                caption=build_caption(_short_hook(first["text"], 14), campaign),
                score=round(score, 2),
                reason=f"local: hook={_hook_score(first['text']):.1f} density={density:.1f}w/s",
            ))
    return _dedupe(candidates, n)


# ── LLM picker ───────────────────────────────────────────────────────────────

SYSTEM = """You are a senior short-form video editor. You pick the moments from a long video \
that will hold attention as standalone 9:16 Reels.

A great clip:
- opens on a hook in its first 3 seconds: a bold claim, a question, a number, conflict, or a surprise
- makes sense with zero context and lands a payoff (punchline, insight, reveal) before it ends
- starts at the beginning of a sentence and ends at the end of one
- is something the speaker clearly said; never invent or distort meaning

For each clip write:
- hook: an on-screen title, at most 8 words, punchy, true to what is said, no clickbait lies, no emojis
- caption: 1-2 short lines for the Instagram caption that make people want to watch; no hashtags
- score: 1-10 for predicted retention
- why: one short phrase on why it works

Timestamps in the transcript are seconds. Return start/end in seconds that align with the line timestamps."""

SCHEMA = {
    "type": "object",
    "properties": {
        "clips": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "hook": {"type": "string"},
                    "caption": {"type": "string"},
                    "score": {"type": "number"},
                    "why": {"type": "string"},
                },
                "required": ["start", "end", "hook", "caption", "score", "why"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["clips"],
    "additionalProperties": False,
}


def compact_transcript(transcript: dict) -> str:
    """One line per segment, timestamps at 0.1s. Smallest faithful form = fewest tokens."""
    return "\n".join(f"[{s['start']:.1f}-{s['end']:.1f}] {s['text']}" for s in transcript["segments"])


def pick_llm(transcript: dict, campaign: Campaign, cfg: dict, title: str) -> list[Pick]:
    try:
        import anthropic
    except ImportError as e:
        raise ClipForgeError("anthropic SDK missing. Run: pip install -e .") from e

    client = anthropic.Anthropic()
    want = cfg["clips_per_video"]
    user = (
        f"Video: {title}\nCampaign: {campaign.name}\n"
        + (f"Campaign notes: {campaign.notes}\n" if campaign.notes else "")
        + f"\nPick the best {want + 2} clips, each {cfg['min_seconds']}-{cfg['max_seconds']} seconds, "
        "no overlaps, best first.\n\n<transcript>\n" + compact_transcript(transcript) + "\n</transcript>"
    )
    log(f"asking {cfg['model']} (effort={cfg['effort']}) to pick moments…")
    try:
        resp = client.beta.messages.create(
            model=cfg["model"],
            max_tokens=16000,
            system=SYSTEM,
            messages=[{"role": "user", "content": user}],
            output_config={"effort": cfg["effort"], "format": {"type": "json_schema", "schema": SCHEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
    except anthropic.AuthenticationError as e:
        raise ClipForgeError("Anthropic auth failed. Set ANTHROPIC_API_KEY or use --mode local.") from e
    except anthropic.RateLimitError as e:
        raise ClipForgeError("Anthropic rate limit hit. Retry in a minute or use --mode local.") from e
    except anthropic.APIStatusError as e:
        raise ClipForgeError(f"Anthropic API error {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise ClipForgeError("Can't reach the Anthropic API. Check your connection or use --mode local.") from e

    if resp.stop_reason == "refusal":
        raise ClipForgeError("Model declined this transcript. Use --mode local for this source.")
    if resp.stop_reason == "max_tokens":
        raise ClipForgeError("Model response was cut off. Lower clips_per_video and retry.")

    u = resp.usage
    log(f"tokens: in={u.input_tokens} out={u.output_tokens}")
    text = next(b.text for b in resp.content if b.type == "text")
    raw = json.loads(text)["clips"]

    picks = []
    for c in raw:
        start, end = snap(transcript, float(c["start"]), float(c["end"]))
        dur = end - start
        if dur < cfg["min_seconds"] * 0.8 or dur > cfg["max_seconds"] + 5:
            continue
        picks.append(Pick(
            start=start, end=end, hook=c["hook"].strip(),
            caption=build_caption(c["caption"], campaign),
            score=float(c["score"]), reason=f"llm: {c['why']}",
        ))
    return _dedupe(picks, want)


# ── entry point ──────────────────────────────────────────────────────────────

def _has_anthropic_creds() -> bool:
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return Path(os.path.expanduser("~/.config/anthropic")).exists()


def pick(transcript: dict, campaign: Campaign, cfg: dict, title: str, cache: Path,
         *, mode: str | None = None, force: bool = False) -> list[Pick]:
    mode = mode or cfg["mode"]
    if mode == "auto":
        mode = "llm" if _has_anthropic_creds() else "local"
    cache_file = cache / f"picks.{mode}.json"
    if cache_file.exists() and not force:
        log(f"picks cached ({mode}); no API call")
        return [Pick(**p) for p in json.loads(cache_file.read_text(encoding="utf-8"))]

    picks = pick_llm(transcript, campaign, cfg, title) if mode == "llm" else pick_local(transcript, campaign, cfg)
    if not picks:
        raise ClipForgeError("No usable moments found. Try a lower min_seconds or the other --mode.")
    cache_file.write_text(json.dumps([asdict(p) for p in picks], indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"{len(picks)} moments picked ({mode})")
    return picks
