"""SQLite store: sources, clips, posts. One file in the workspace."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id          INTEGER PRIMARY KEY,
    campaign    TEXT NOT NULL,
    origin      TEXT NOT NULL,
    path        TEXT NOT NULL,
    title       TEXT,
    duration    REAL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS clips (
    id          INTEGER PRIMARY KEY,
    source_id   INTEGER NOT NULL REFERENCES sources(id),
    start       REAL NOT NULL,
    end         REAL NOT NULL,
    hook        TEXT NOT NULL,
    caption     TEXT NOT NULL,
    score       REAL NOT NULL DEFAULT 0,
    reason      TEXT,
    status      TEXT NOT NULL DEFAULT 'candidate',
    -- candidate -> rendered -> approved -> posted   (or rejected / failed)
    path        TEXT,
    error       TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS posts (
    id          INTEGER PRIMARY KEY,
    clip_id     INTEGER NOT NULL REFERENCES clips(id),
    media_id    TEXT NOT NULL,
    permalink   TEXT,
    posted_at   TEXT NOT NULL,
    views       INTEGER,
    likes       INTEGER,
    comments    INTEGER,
    synced_at   TEXT,
    submitted   INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kv (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

STATUSES = ("candidate", "rendered", "approved", "rejected", "posted", "failed")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class DB:
    def __init__(self, path: Path):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # sources
    def add_source(self, campaign: str, origin: str, path: Path, title: str, duration: float) -> int:
        cur = self.conn.execute(
            "INSERT INTO sources (campaign, origin, path, title, duration, created_at) VALUES (?,?,?,?,?,?)",
            (campaign, origin, str(path), title, duration, now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def source(self, source_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if row is None:
            from .util import ClipForgeError
            raise ClipForgeError(f"No source #{source_id}")
        return row

    def sources(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM sources ORDER BY id DESC").fetchall()

    # clips
    def add_clip(self, source_id: int, start: float, end: float, hook: str, caption: str,
                 score: float, reason: str) -> int:
        ts = now()
        cur = self.conn.execute(
            "INSERT INTO clips (source_id, start, end, hook, caption, score, reason, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (source_id, start, end, hook, caption, score, reason, ts, ts),
        )
        self.conn.commit()
        return cur.lastrowid

    def clip(self, clip_id: int) -> sqlite3.Row:
        row = self.conn.execute("SELECT * FROM clips WHERE id=?", (clip_id,)).fetchone()
        if row is None:
            from .util import ClipForgeError
            raise ClipForgeError(f"No clip #{clip_id}")
        return row

    def clips(self, status: str | None = None, source_id: int | None = None) -> list[sqlite3.Row]:
        q, args = "SELECT * FROM clips WHERE 1=1", []
        if status:
            q += " AND status=?"
            args.append(status)
        if source_id:
            q += " AND source_id=?"
            args.append(source_id)
        return self.conn.execute(q + " ORDER BY source_id DESC, score DESC, id", args).fetchall()

    def update_clip(self, clip_id: int, **fields) -> None:
        if "status" in fields and fields["status"] not in STATUSES:
            raise ValueError(fields["status"])
        fields["updated_at"] = now()
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE clips SET {cols} WHERE id=?", (*fields.values(), clip_id))
        self.conn.commit()

    # posts
    def add_post(self, clip_id: int, media_id: str, permalink: str | None) -> int:
        cur = self.conn.execute(
            "INSERT INTO posts (clip_id, media_id, permalink, posted_at) VALUES (?,?,?,?)",
            (clip_id, media_id, permalink, now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def posts(self) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT p.*, c.hook, c.source_id, s.campaign FROM posts p"
            " JOIN clips c ON c.id=p.clip_id JOIN sources s ON s.id=c.source_id"
            " ORDER BY p.posted_at DESC"
        ).fetchall()

    def update_post(self, post_id: int, **fields) -> None:
        cols = ", ".join(f"{k}=?" for k in fields)
        self.conn.execute(f"UPDATE posts SET {cols} WHERE id=?", (*fields.values(), post_id))
        self.conn.commit()

    def posts_since(self, iso: str) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT * FROM posts WHERE posted_at >= ? ORDER BY posted_at DESC", (iso,)
        ).fetchall()

    # kv (tokens, etc.)
    def get(self, key: str, default=None):
        row = self.conn.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set(self, key: str, value) -> None:
        self.conn.execute(
            "INSERT INTO kv (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, json.dumps(value)),
        )
        self.conn.commit()
