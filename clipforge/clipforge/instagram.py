"""Instagram Graph API: publish a local Reel (resumable upload), read insights, refresh tokens.

Flow (Meta docs, v26.0):
  1. POST /{ig-user-id}/media  media_type=REELS upload_type=resumable  -> container id
  2. POST https://rupload.facebook.com/ig-api-upload/{ver}/{container}  (raw bytes)
  3. GET  /{container}?fields=status_code   until FINISHED
  4. POST /{ig-user-id}/media_publish creation_id={container}  -> media id
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .db import DB
from .util import ClipForgeError, log

TOKEN_KEY = "ig_token"
USER_KEY = "ig_user_id"


class Instagram:
    def __init__(self, cfg: dict, db: DB):
        self.cfg = cfg
        self.db = db
        self.base = f"https://{cfg['graph_host']}/{cfg['api_version']}"
        self.user_id = cfg["user_id"] or os.environ.get("IG_USER_ID", "") or db.get(USER_KEY, "")
        stored = db.get(TOKEN_KEY) or {}
        self.token = os.environ.get("IG_ACCESS_TOKEN") or stored.get("token", "")
        if not self.token or not self.user_id:
            raise ClipForgeError(
                "Instagram not connected. Set IG_ACCESS_TOKEN and instagram.user_id "
                "(or run `clipforge auth --token ... --user-id ...`). See README → Instagram setup."
            )

    # ── http ──
    def _call(self, method: str, url: str, params: dict | None = None, *,
              data: bytes | None = None, headers: dict | None = None) -> dict:
        params = dict(params or {})
        if data is None:
            params.setdefault("access_token", self.token)
        if method == "GET" and params:
            url += "?" + urllib.parse.urlencode(params)
            body = None
        else:
            body = data if data is not None else urllib.parse.urlencode(params).encode()
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")
            try:
                err = json.loads(detail).get("error", {})
                detail = f"{err.get('message')} (code {err.get('code')}, subcode {err.get('error_subcode')})"
            except (json.JSONDecodeError, AttributeError):
                pass
            raise ClipForgeError(f"Instagram API {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise ClipForgeError(f"Network error talking to Instagram: {e.reason}") from e

    # ── publishing ──
    def publishing_quota(self) -> int | None:
        try:
            r = self._call("GET", f"{self.base}/{self.user_id}/content_publishing_limit",
                           {"fields": "quota_usage"})
            return r.get("data", [{}])[0].get("quota_usage")
        except ClipForgeError:
            return None

    def publish_reel(self, video: Path, caption: str) -> tuple[str, str | None]:
        container = self._call("POST", f"{self.base}/{self.user_id}/media", {
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": caption,
            "share_to_feed": "true" if self.cfg["share_to_feed"] else "false",
        })["id"]
        log(f"container {container}; uploading {video.stat().st_size / 1e6:.1f} MB…")

        data = video.read_bytes()
        self._call(
            "POST", f"https://rupload.facebook.com/ig-api-upload/{self.cfg['api_version']}/{container}",
            data=data,
            headers={"Authorization": f"OAuth {self.token}", "offset": "0", "file_size": str(len(data))},
        )

        for _ in range(60):  # up to ~5 min of processing
            status = self._call("GET", f"{self.base}/{container}", {"fields": "status_code,status"})
            code = status.get("status_code")
            if code == "FINISHED":
                break
            if code in ("ERROR", "EXPIRED"):
                raise ClipForgeError(f"Instagram processing failed: {status.get('status')}")
            time.sleep(5)
        else:
            raise ClipForgeError("Instagram is still processing after 5 minutes; try `clipforge post` again later.")

        media_id = self._call("POST", f"{self.base}/{self.user_id}/media_publish",
                              {"creation_id": container})["id"]
        permalink = None
        try:
            permalink = self._call("GET", f"{self.base}/{media_id}", {"fields": "permalink"}).get("permalink")
        except ClipForgeError:
            pass
        return media_id, permalink

    # ── insights ──
    def insights(self, media_id: str) -> dict:
        out: dict = {}
        basic = self._call("GET", f"{self.base}/{media_id}", {"fields": "like_count,comments_count,permalink"})
        out["likes"] = basic.get("like_count")
        out["comments"] = basic.get("comments_count")
        out["permalink"] = basic.get("permalink")
        for metric in ("views", "plays"):  # 'plays' is the older name on some API versions
            try:
                r = self._call("GET", f"{self.base}/{media_id}/insights", {"metric": metric})
                out["views"] = r["data"][0]["values"][0]["value"]
                break
            except (ClipForgeError, KeyError, IndexError):
                continue
        return out

    # ── tokens ──
    def refresh_token(self) -> str:
        """Instagram-Login long-lived tokens last 60 days; refresh any time after 24h."""
        if "graph.instagram.com" not in self.cfg["graph_host"]:
            raise ClipForgeError("Token refresh here supports Instagram Login (graph.instagram.com) only.")
        r = self._call("GET", "https://graph.instagram.com/refresh_access_token",
                       {"grant_type": "ig_refresh_token", "access_token": self.token})
        self.token = r["access_token"]
        self.db.set(TOKEN_KEY, {"token": self.token, "refreshed_at": int(time.time()),
                                "expires_in": r.get("expires_in")})
        return self.token
