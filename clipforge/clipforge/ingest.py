"""Bring a source video into the workspace: a local file, or a URL the campaign lets you download."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .config import Campaign
from .db import DB
from .util import ClipForgeError, log, probe, require_bin, run

URL_RE = re.compile(r"^https?://", re.I)


def ingest(db: DB, workspace: Path, campaign: Campaign, origin: str, *, i_have_rights: bool = False) -> int:
    for row in db.sources():
        if row["origin"] == origin and row["campaign"] == campaign.slug and Path(row["path"]).exists():
            log(f"already added as source #{row['id']}; reusing it")
            return row["id"]

    staging = workspace / "sources" / "_incoming"
    staging.mkdir(parents=True, exist_ok=True)

    if URL_RE.match(origin):
        if not (campaign.allow_download or i_have_rights):
            raise ClipForgeError(
                f"Campaign '{campaign.slug}' doesn't allow downloading from URLs.\n"
                "Use the source file the campaign gave you, or set allow_download = true "
                "for this campaign once you've confirmed the rules permit it."
            )
        path, title = _download(origin, staging)
    else:
        src = Path(origin).expanduser()
        if not src.is_file():
            raise ClipForgeError(f"File not found: {src}")
        path, title = staging / src.name, src.stem
        if path.resolve() != src.resolve():
            shutil.copy2(src, path)

    info = probe(path)
    source_id = db.add_source(campaign.slug, origin, path, title, info.duration)
    final_dir = workspace / "sources" / str(source_id)
    final_dir.mkdir(parents=True, exist_ok=True)
    final = final_dir / f"source{path.suffix.lower()}"
    shutil.move(path, final)
    db.conn.execute("UPDATE sources SET path=? WHERE id=?", (str(final), source_id))
    db.conn.commit()
    log(f"source #{source_id}: {title} ({info.width}x{info.height}, {info.duration/60:.1f} min)")
    return source_id


def _download(url: str, dest: Path) -> tuple[Path, str]:
    ytdlp = require_bin("yt-dlp")
    log("downloading…")
    out = run([
        ytdlp, "--no-playlist", "--restrict-filenames",
        "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b",
        "--merge-output-format", "mp4",
        "-o", str(dest / "%(id)s.%(ext)s"),
        "--print", "after_move:filepath", "--print", "title",
        url,
    ])
    lines = [ln for ln in out.strip().splitlines() if ln.strip()]
    if len(lines) < 2:
        raise ClipForgeError("yt-dlp gave no file path")
    title, filepath = lines[0], lines[-1]
    return Path(filepath), title
