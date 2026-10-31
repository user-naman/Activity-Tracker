"""Load clipforge.toml (the single source of truth) and merge it over defaults."""

from __future__ import annotations

import copy
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from .util import ClipForgeError

DEFAULTS: dict = {
    "workspace": "~/ClipForge",
    "whisper": {"model": "small", "device": "auto", "compute_type": "int8", "language": ""},
    "picker": {
        "mode": "auto",            # auto | llm | local
        "model": "claude-opus-5-5",
        "effort": "low",
        "clips_per_video": 6,
        "min_seconds": 20,
        "max_seconds": 59,
    },
    "render": {
        "layout": "auto",          # auto | face | blur | center
        "font": "Arial Black",
        "fonts_dir": "",
        "font_size": 84,
        "accent": "#FFE14D",
        "words_per_chunk": 3,
        "uppercase": True,
        "progress_bar": True,
        "hook_seconds": 3.0,
        "caption_y": 0.64,         # fraction of height; keeps clear of IG's bottom UI
        "crf": 20,
        "preset": "medium",
    },
    "instagram": {
        "graph_host": "graph.instagram.com",
        "api_version": "v26.0",
        "user_id": "",
        "max_posts_per_day": 3,
        "min_gap_minutes": 180,
        "share_to_feed": True,
    },
    "campaigns": {},
}


@dataclass
class Campaign:
    slug: str
    name: str
    cpm: float = 0.0
    allow_download: bool = False
    mention: str = ""
    hashtags: list[str] = field(default_factory=list)
    submit_url: str = ""
    notes: str = ""


@dataclass
class Config:
    raw: dict
    path: Path | None

    @property
    def workspace(self) -> Path:
        ws = Path(os.path.expanduser(self.raw["workspace"]))
        if not ws.is_absolute() and self.path is not None:
            ws = self.path.parent / ws
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def section(self, name: str) -> dict:
        return self.raw[name]

    def campaign(self, slug: str) -> Campaign:
        data = self.raw["campaigns"].get(slug)
        if data is None:
            known = ", ".join(self.raw["campaigns"]) or "none yet"
            raise ClipForgeError(
                f"Unknown campaign '{slug}'. Add [campaigns.{slug}] to clipforge.toml (known: {known})."
            )
        return Campaign(slug=slug, **{k: v for k, v in data.items() if k in Campaign.__annotations__})

    def campaigns(self) -> list[Campaign]:
        return [self.campaign(s) for s in self.raw["campaigns"]]


def _merge(base: dict, override: dict) -> dict:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def find_config(explicit: str | None) -> Path | None:
    candidates = [explicit] if explicit else [
        os.environ.get("CLIPFORGE_CONFIG"),
        "clipforge.toml",
        os.path.expanduser("~/ClipForge/clipforge.toml"),
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c).resolve()
    if explicit:
        raise ClipForgeError(f"Config not found: {explicit}")
    return None


def load(explicit: str | None = None) -> Config:
    path = find_config(explicit)
    user = tomllib.loads(path.read_text()) if path else {}
    return Config(raw=_merge(DEFAULTS, user), path=path)
