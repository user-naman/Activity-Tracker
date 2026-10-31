"""Local review server: watch each clip, fix hook/caption, approve or reject. Keyboard-first."""

from __future__ import annotations

import json
import re
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

from ..db import DB

INDEX = Path(__file__).with_name("index.html")
EDITABLE = {"status", "caption", "hook"}
REVIEW_STATUSES = {"rendered", "approved", "rejected"}


def _clip_json(row, campaign: str) -> dict:
    return {
        "id": row["id"], "source_id": row["source_id"], "campaign": campaign,
        "start": row["start"], "end": row["end"], "hook": row["hook"], "caption": row["caption"],
        "score": row["score"], "reason": row["reason"], "status": row["status"],
        "video": f"/media/{row['id']}?v={row['updated_at']}",
    }


def make_handler(db: DB, rerender: Callable[[int], None]):
    lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):  # quiet
            pass

        def _json(self, data, code: int = 200):
            body = json.dumps(data).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = INDEX.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif self.path == "/api/clips":
                with lock:
                    campaigns = {s["id"]: s["campaign"] for s in db.sources()}
                    rows = [r for r in db.clips() if r["status"] in REVIEW_STATUSES and r["path"]]
                self._json([_clip_json(r, campaigns.get(r["source_id"], "")) for r in rows])
            elif m := re.fullmatch(r"/media/(\d+)(\?.*)?", self.path):
                self._serve_video(int(m.group(1)))
            else:
                self.send_error(404)

        def do_POST(self):
            m = re.fullmatch(r"/api/clips/(\d+)", self.path)
            if not m:
                return self.send_error(404)
            clip_id = int(m.group(1))
            length = int(self.headers.get("Content-Length", 0))
            patch = {k: v for k, v in json.loads(self.rfile.read(length) or b"{}").items() if k in EDITABLE}
            if "status" in patch and patch["status"] not in REVIEW_STATUSES:
                return self._json({"error": "bad status"}, 400)
            with lock:
                old = db.clip(clip_id)
                if patch:
                    db.update_clip(clip_id, **patch)
            if "hook" in patch and patch["hook"] != old["hook"]:
                try:
                    rerender(clip_id)
                except Exception as e:  # surface render errors to the UI
                    return self._json({"error": str(e)}, 500)
            with lock:
                row = db.clip(clip_id)
                campaign = db.source(row["source_id"])["campaign"]
            self._json(_clip_json(row, campaign))

        def _serve_video(self, clip_id: int):
            with lock:
                path = db.clip(clip_id)["path"]
            if not path or not Path(path).exists():
                return self.send_error(404)
            size = Path(path).stat().st_size
            start, end = 0, size - 1
            rng = self.headers.get("Range")
            if rng and (m := re.match(r"bytes=(\d*)-(\d*)", rng)):
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else end
                else:
                    start = size - int(m.group(2))
            end = min(end, size - 1)
            self.send_response(206 if rng else 200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Length", str(end - start + 1))
            if rng:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with open(path, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                try:
                    while remaining > 0:
                        chunk = f.read(min(1 << 16, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    pass

    return Handler


def serve(db: DB, rerender: Callable[[int], None], port: int = 8787, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(db, rerender))
    url = f"http://127.0.0.1:{port}"
    print(f"Review queue → {url}   (Ctrl+C to stop)")
    if open_browser:
        threading.Timer(0.4, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
