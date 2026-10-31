"""clipforge command line."""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config as config_mod
from .db import DB
from .util import ClipForgeError, fmt_ts, log, which

CAPTION_LIMIT = 2200


# ── helpers ──────────────────────────────────────────────────────────────────

def _ctx(args):
    cfg = config_mod.load(args.config)
    return cfg, DB(cfg.workspace / "clipforge.db")


def _render_one(cfg, db: DB, clip_id: int) -> None:
    from .render import render_clip
    from .transcribe import load_transcript

    clip = db.clip(clip_id)
    src = db.source(clip["source_id"])
    source_path = Path(src["path"])
    out = cfg.workspace / "clips" / f"{clip_id:05d}.mp4"
    render_clip(source_path, load_transcript(source_path), clip["start"], clip["end"], clip["hook"],
                out, cfg.section("render"))
    status = clip["status"] if clip["status"] in ("approved", "rejected") else "rendered"
    db.update_clip(clip_id, path=str(out), status=status, error=None)


def _process(cfg, db: DB, source_id: int, mode: str | None, force: bool) -> list[int]:
    from .pick import pick
    from .transcribe import transcribe

    src = db.source(source_id)
    campaign = cfg.campaign(src["campaign"])
    source_path = Path(src["path"])
    transcript = transcribe(source_path, cfg.section("whisper"), force=force)
    picks = pick(transcript, campaign, cfg.section("picker"), src["title"] or "", source_path.parent,
                 mode=mode, force=force)

    existing = {(round(c["start"], 1), round(c["end"], 1)) for c in db.clips(source_id=source_id)}
    for p in picks:
        if (round(p.start, 1), round(p.end, 1)) not in existing:
            db.add_clip(source_id, p.start, p.end, p.hook, p.caption, p.score, p.reason)

    # Render anything unfinished, so an interrupted run resumes where it stopped.
    ids = [c["id"] for c in db.clips(source_id=source_id) if c["status"] in ("candidate", "failed")]
    for n, clip_id in enumerate(ids, 1):
        c = db.clip(clip_id)
        log(f"rendering {n}/{len(ids)}  {fmt_ts(c['start'])}–{fmt_ts(c['end'])}  “{c['hook']}”")
        try:
            _render_one(cfg, db, clip_id)
        except ClipForgeError as e:
            db.update_clip(clip_id, status="failed", error=str(e))
            log(f"  failed: {str(e).splitlines()[0]}")
    return ids


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_init(args):
    dest = Path(args.path or "clipforge.toml")
    if dest.exists():
        raise ClipForgeError(f"{dest} already exists")
    shutil.copy(Path(__file__).parent / "clipforge.example.toml", dest)
    print(f"Created {dest}. Edit your campaigns, then run: clipforge doctor")


def cmd_add(args):
    from .ingest import ingest
    cfg, db = _ctx(args)
    sid = ingest(db, cfg.workspace, cfg.campaign(args.campaign), args.source, i_have_rights=args.i_have_rights)
    print(sid)


def cmd_run(args):
    from .ingest import ingest
    cfg, db = _ctx(args)
    sid = ingest(db, cfg.workspace, cfg.campaign(args.campaign), args.source, i_have_rights=args.i_have_rights)
    ids = _process(cfg, db, sid, args.mode, force=False)
    ok = sum(db.clip(i)["status"] == "rendered" for i in ids)
    print(f"\n{ok} clip(s) ready for review. Next: clipforge review")


def cmd_process(args):
    cfg, db = _ctx(args)
    ids = _process(cfg, db, args.source_id, args.mode, force=args.force)
    ok = sum(db.clip(i)["status"] == "rendered" for i in ids)
    print(f"{ok} clip(s) rendered. Next: clipforge review")


def cmd_rerender(args):
    cfg, db = _ctx(args)
    for cid in args.clip_ids:
        _render_one(cfg, db, cid)
        log(f"clip #{cid} re-rendered")


def cmd_review(args):
    from .review.server import serve
    cfg, db = _ctx(args)
    serve(db, lambda cid: _render_one(cfg, db, cid), port=args.port, open_browser=not args.no_browser)


def cmd_post(args):
    from .instagram import TOKEN_KEY, Instagram
    cfg, db = _ctx(args)
    ig_cfg = cfg.section("instagram")

    if args.clip:
        clip = db.clip(args.clip)
    else:
        since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
        recent = db.posts_since(since)
        if len(recent) >= ig_cfg["max_posts_per_day"]:
            print(f"Daily cap reached ({len(recent)}/{ig_cfg['max_posts_per_day']}). Nothing posted.")
            return
        if recent:
            last = datetime.fromisoformat(recent[0]["posted_at"])
            wait = last + timedelta(minutes=ig_cfg["min_gap_minutes"]) - datetime.now(timezone.utc)
            if wait.total_seconds() > 0:
                print(f"Next slot in {int(wait.total_seconds() // 60)} min. Nothing posted.")
                return
        queue = sorted(db.clips(status="approved"), key=lambda c: (-c["score"], c["updated_at"]))
        if not queue:
            print("Post queue is empty. Approve clips in `clipforge review`.")
            return
        clip = queue[0]

    caption = clip["caption"][:CAPTION_LIMIT]
    if args.dry_run:
        print(f"[dry run] would post clip #{clip['id']}: {clip['path']}\n---\n{caption}")
        return

    ig = Instagram(ig_cfg, db)
    stored = db.get(TOKEN_KEY) or {}
    if stored.get("refreshed_at") and time.time() - stored["refreshed_at"] > 7 * 86400:
        try:
            ig.refresh_token()
            log("instagram token refreshed")
        except ClipForgeError as e:
            log(f"token refresh skipped: {e}")

    log(f"posting clip #{clip['id']} “{clip['hook']}”")
    try:
        media_id, permalink = ig.publish_reel(Path(clip["path"]), caption)
    except ClipForgeError as e:
        db.update_clip(clip["id"], error=str(e))
        raise
    db.add_post(clip["id"], media_id, permalink)
    db.update_clip(clip["id"], status="posted", error=None)
    campaign = cfg.campaign(db.source(clip["source_id"])["campaign"])
    print(f"Posted → {permalink or media_id}")
    if campaign.submit_url:
        print(f"Submit it for payout: {campaign.submit_url}")


def cmd_stats(args):
    cfg, db = _ctx(args)
    posts = db.posts()
    if args.sync and posts:
        from .instagram import Instagram
        ig = Instagram(cfg.section("instagram"), db)
        for p in posts:
            try:
                s = ig.insights(p["media_id"])
                db.update_post(p["id"], views=s.get("views"), likes=s.get("likes"), comments=s.get("comments"),
                               permalink=s.get("permalink") or p["permalink"],
                               synced_at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
            except ClipForgeError as e:
                log(f"post {p['id']}: {e}")
        posts = db.posts()

    cpm = {c.slug: c.cpm for c in cfg.campaigns()}
    counts = {s: len(db.clips(status=s)) for s in ("rendered", "approved", "posted", "rejected", "failed")}
    print("Pipeline  " + "  ".join(f"{k}:{v}" for k, v in counts.items()))
    if not posts:
        print("No posts yet.")
        return
    total_views = total_est = 0.0
    print(f"\n{'id':>4}  {'campaign':<14} {'views':>9} {'est $':>8}  {'sent':<4}  hook")
    for p in posts:
        views = p["views"] or 0
        est = views / 1000 * cpm.get(p["campaign"], 0)
        total_views += views
        total_est += est
        print(f"{p['id']:>4}  {p['campaign'][:14]:<14} {views:>9,} {est:>8.2f}  {'yes' if p['submitted'] else '—':<4}  "
              f"{p['hook'][:40]}")
    print(f"\n{len(posts)} posts · {int(total_views):,} views · ~${total_est:,.2f} at campaign CPMs (estimate, before approval/fees)")


def cmd_submitted(args):
    _, db = _ctx(args)
    for pid in args.post_ids:
        db.update_post(pid, submitted=1)
    print("Marked as submitted.")


def cmd_auth(args):
    from .instagram import TOKEN_KEY, USER_KEY, Instagram
    cfg, db = _ctx(args)
    if args.user_id:
        db.set(USER_KEY, args.user_id)
        print("Instagram user ID saved.")
    if args.token:
        db.set(TOKEN_KEY, {"token": args.token, "refreshed_at": int(time.time())})
        print("Token saved to the workspace database.")
    if args.refresh:
        Instagram(cfg.section("instagram"), db).refresh_token()
        print("Token refreshed (valid ~60 days).")


def cmd_list(args):
    _, db = _ctx(args)
    for s in db.sources():
        clips = db.clips(source_id=s["id"])
        summary = ", ".join(f"{st}:{sum(c['status'] == st for c in clips)}"
                            for st in ("rendered", "approved", "posted", "rejected", "failed")
                            if any(c["status"] == st for c in clips))
        print(f"#{s['id']:<4} {s['campaign']:<14} {(s['title'] or '')[:44]:<44} {summary}")


def cmd_doctor(args):
    cfg, db = _ctx(args)
    ok = lambda b: "✓" if b else "✗"  # noqa: E731

    def has(mod):
        try:
            __import__(mod)
            return True
        except ImportError:
            return False

    rows = [
        ("config", bool(cfg.path), str(cfg.path or "not found, using defaults (run `clipforge init`)")),
        ("workspace", True, str(cfg.workspace)),
        ("ffmpeg", bool(which("ffmpeg")), "required"),
        ("yt-dlp", bool(which("yt-dlp")), "optional, only for campaigns that allow URL downloads"),
        ("faster-whisper", has("faster_whisper"), "required for transcription"),
        ("opencv", has("cv2"), "face tracking; without it clips use blur layout"),
        ("anthropic creds", bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
         "optional; without it the free local picker runs"),
        ("instagram", bool((os.environ.get("IG_ACCESS_TOKEN") or db.get("ig_token"))
                           and (cfg.section("instagram")["user_id"] or os.environ.get("IG_USER_ID")
                                or db.get("ig_user_id"))),
         "needed only for `clipforge post`"),
        ("campaigns", bool(cfg.raw["campaigns"]), ", ".join(cfg.raw["campaigns"]) or "add one to clipforge.toml"),
    ]
    for name, good, note in rows:
        print(f"{ok(good)} {name:<16} {note}")


# ── parser ───────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="clipforge", description="Campaign videos in, captioned reels out.")
    p.add_argument("--config", help="path to clipforge.toml")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="create clipforge.toml")
    s.add_argument("path", nargs="?")
    s.set_defaults(fn=cmd_init)

    for name, fn, helptext in (("run", cmd_run, "add a source and make clips end to end"),
                               ("add", cmd_add, "add a source only")):
        s = sub.add_parser(name, help=helptext)
        s.add_argument("source", help="video file, or URL if the campaign allows downloads")
        s.add_argument("-c", "--campaign", required=True)
        s.add_argument("--i-have-rights", action="store_true", help="override allow_download for this URL")
        if name == "run":
            s.add_argument("--mode", choices=("auto", "llm", "local"))
        s.set_defaults(fn=fn)

    s = sub.add_parser("process", help="transcribe, pick and render an existing source")
    s.add_argument("source_id", type=int)
    s.add_argument("--mode", choices=("auto", "llm", "local"))
    s.add_argument("--force", action="store_true", help="ignore cached transcript/picks")
    s.set_defaults(fn=cmd_process)

    s = sub.add_parser("rerender", help="re-render clips after changing render settings")
    s.add_argument("clip_ids", type=int, nargs="+")
    s.set_defaults(fn=cmd_rerender)

    s = sub.add_parser("review", help="open the review queue in your browser")
    s.add_argument("--port", type=int, default=8787)
    s.add_argument("--no-browser", action="store_true")
    s.set_defaults(fn=cmd_review)

    s = sub.add_parser("post", help="post the next approved clip if a slot is free")
    s.add_argument("--clip", type=int, help="post this clip now, ignoring the schedule")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(fn=cmd_post)

    s = sub.add_parser("stats", help="views and estimated earnings")
    s.add_argument("--sync", action="store_true", help="pull fresh insights from Instagram")
    s.set_defaults(fn=cmd_stats)

    s = sub.add_parser("submitted", help="mark posts as submitted to the campaign")
    s.add_argument("post_ids", type=int, nargs="+")
    s.set_defaults(fn=cmd_submitted)

    s = sub.add_parser("auth", help="store or refresh the Instagram token")
    s.add_argument("--token")
    s.add_argument("--user-id")
    s.add_argument("--refresh", action="store_true")
    s.set_defaults(fn=cmd_auth)

    sub.add_parser("list", help="sources and clip counts").set_defaults(fn=cmd_list)
    sub.add_parser("doctor", help="check your setup").set_defaults(fn=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
        return 0
    except ClipForgeError as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
