# ClipForge

Campaign videos in. Captioned 9:16 reels out. Posted on a schedule.

Runs on your laptop. Transcription, editing and posting are free.
The only optional cost is Claude picking the best moments, about a cent per clip.

```
long video ─▶ transcribe ─▶ pick moments ─▶ render ─▶ you review ─▶ auto-post ─▶ track views
            (whisper,     (Claude or      (face-tracked  (browser,    (IG API,     (insights,
             local)        free local)     crop, captions) keyboard)    cron)        est. $)
```

## What each clip gets

- **Reframe to 1080×1920.** Follows the speaker's face with jump cuts like a human editor. Falls back to a blurred background when there's no clear face.
- **Word-by-word captions.** 3-word phrases with the spoken word highlighted, placed clear of Instagram's UI.
- **Hook title.** Shown for the first 3 seconds.
- **Progress bar.** Thin, along the top.
- **Loudness.** Normalized to -14 LUFS.
- **Instagram-ready encoding.** H.264 / AAC, 30fps, fast-start.

These edits are what make a clip transformative instead of a raw re-upload.

---

## 1. Install (10 min, once)

**Windows 10/11:**

1. Double-click `setup.cmd`. If Windows warns you, click *More info*, then *Run anyway*.
2. It installs Python and ffmpeg if they're missing, then ClipForge itself.
3. It creates your config at `C:\Users\<you>\ClipForge\clipforge.toml`.
4. It adds a `clipforge` command you can use from any PowerShell window.

Open a **new** PowerShell window afterwards so the command is found.

**Mac / Linux:** run `./setup.sh` in this folder, then `source .venv/bin/activate` each session.

`clipforge edit` opens your config in a text editor.

Optional, for smarter moment picks: `export ANTHROPIC_API_KEY=...`. Without it, the free local picker runs.

**Nicer captions:** download [Montserrat](https://fonts.google.com/specimen/Montserrat) (free). Put the `.ttf` files in a folder, then set `font = "Montserrat ExtraBold"` and `fonts_dir = "/path/to/folder"`.

## 2. Join a campaign, add it to the config

Find campaigns on [Whop Content Rewards](https://whop.com/discover/) or Vyro. Check each one's rules on:

- Which platforms count
- Minimum length
- Required tags
- Whether you may download the source yourself

Then add it to `clipforge.toml`:

```toml
[campaigns.hormozi]
name = "Alex Hormozi"
cpm = 1.0
allow_download = false       # true only if the rules allow pulling the source from a URL
mention = "@hormozi"
hashtags = ["business", "entrepreneur"]
submit_url = "https://whop.com/..."
notes = "Business advice moments. Keep hooks clean."
```

`notes` are passed to Claude, so use them for campaign-specific guidance.

## 3. Daily loop (about 10 min of your time)

```bash
clipforge run ~/Downloads/episode-212.mp4 -c hormozi     # 6 clips, rendered
clipforge review                                         # opens the review queue
```

**Review keys:**

| Key | Action |
|---|---|
| `A` | Approve and go to next |
| `X` | Reject and go to next |
| `U` | Send back to review |
| `J` / `K` | Next / previous clip |
| `H` | Edit hook (Enter saves and re-renders) |
| `E` | Edit caption |
| `Space` | Play / pause |
| `M` | Mute |
| `?` | Show all shortcuts |

Approved clips go to the post queue.

```bash
clipforge post            # posts the best approved clip if a slot is free
clipforge stats --sync    # views, est. earnings, which posts you've submitted
clipforge submitted 3 4   # mark posts 3 and 4 as submitted for payout
```

Other commands:

```bash
clipforge list            # all sources and clip counts
clipforge process 7 --mode local --force    # redo picks for source 7
clipforge rerender 12 13  # after changing [render] settings
```

## 4. Automate posting

```bash
clipforge schedule            # turn on auto-posting
clipforge schedule --remove   # turn it off
```

- **On Windows:** this creates a hidden Task Scheduler job. It runs every 30 minutes while you're signed in, with no pop-up windows.
- **On Mac / Linux:** it prints a line for you to paste into `crontab -e`.

Each run posts at most one approved clip. It follows `max_posts_per_day` and `min_gap_minutes`, so posts spread out on their own. Output goes to `ClipForge/post.log`.

The Instagram token refreshes itself weekly. If the laptop is asleep, it just skips those slots.

## 5. Connect Instagram (free, once)

You use the official Instagram API, so the account isn't at risk from unofficial bots.

1. **Switch the account to Professional.** In the Instagram app, go to Settings → Account type → switch to Creator.
2. **Create a Meta app.** Go to developers.facebook.com → My Apps → Create app. Pick the Instagram use case, then choose **API setup with Instagram login**.
3. **Add your account.** Under that use case, click *Add account* and log in with your Instagram account. Accept the tester invite if asked.
4. **Generate a token.** Click *Generate token* with these permissions:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
   - `instagram_business_manage_insights`

   Copy the token and the account ID shown.
5. Save them:
   ```bash
   clipforge auth --token IGAA... --user-id 1784...
   clipforge post --dry-run
   ```

Meta renames dashboard buttons often. If a label differs, look for the "Instagram API with Instagram Login" section.
Your app stays in Development mode, which is fine because you're only posting to your own account. No App Review needed.

---

## What it costs per upload

| Step | Cost |
|---|---|
| Transcription (Whisper, local) | $0 |
| Moment picking, `mode = "local"` | $0 |
| Moment picking, Claude Opus 5.5 at low effort | ~$0.05–0.15 per source video, ~1–2¢ per clip (estimate) |
| Moment picking, Claude Haiku 5.5 | ~0.2¢ per source video (estimate) |
| Rendering (ffmpeg, local) | $0 |
| Posting and insights (Instagram API) | $0 |

**Why it stays cheap:**

- Claude only reads transcript text, never video.
- It reads it once per source.
- The result is cached in `picks.<mode>.json`, so re-runs never call the API again.

Switch models with `picker.model` in `clipforge.toml`.

## Growth playbook (new account)

- **Niche down.** Make one account per creator or topic so the algorithm learns who to show it to.
- **Warm up first.** Weeks 1–2: 1–2 posts a day, and use the account like a human (follow, watch, comment). Then raise `max_posts_per_day` to 3–5.
- **The hook is the product.** Rewrite weak hooks in review. The first 3 seconds decide almost everything.
- **Aim for 25–45 seconds.** Cut anything that needs outside context to make sense.
- **Submit fast.** Campaigns pay on tracked views, so submit each post's link right after it goes live.
- **Don't post the same clip on several of your own accounts.** That triggers duplicate-content flags.

## Rules that keep you safe

- Only clip creators who've given permission, like campaign participants.
- URL downloads are blocked unless the campaign sets `allow_download = true`. YouTube's terms forbid downloading without permission.
- Never post a clip that changes what the speaker meant. Review exists for this.
- Campaign terms, payouts and platform policies change. Read each campaign's rules. Get a human to check anything legal or tax-related.

## Layout

```
clipforge/
  cli.py         commands (incl. schedule: Task Scheduler / cron)
  ingest.py      file or permitted URL → workspace
  transcribe.py  faster-whisper, word timestamps, cached
  pick.py        Claude or local heuristics → moments, cached
  reframe.py     face tracking → crop "camera cuts"
  captions.py    ASS subtitles: highlighted words + hook box
  render.py      one ffmpeg pass per clip
  instagram.py   resumable Reel upload, insights, token refresh
  review/        local review server + single-page UI
  db.py          SQLite in the workspace
tests/           pytest (network mocked)
```

Run the tests with `pytest`.
