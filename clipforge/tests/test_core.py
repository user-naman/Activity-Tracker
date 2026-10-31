from clipforge.captions import ass_color, ass_time, build_ass, chunk_words
from clipforge.config import DEFAULTS, Campaign
from clipforge.pick import _dedupe, Pick, build_caption, compact_transcript, pick_local, snap
from clipforge.reframe import crop_x_expr, shots_from_centers

CAMPAIGN = Campaign(slug="t", name="Test", mention="@host", hashtags=["podcast", "#clips"])


def _transcript(sentences: list[str], wps: float = 3.0) -> dict:
    t, segs = 0.0, []
    for s in sentences:
        words = []
        for w in s.split():
            words.append({"start": round(t, 3), "end": round(t + 1 / wps * 0.9, 3), "word": w})
            t += 1 / wps
        segs.append({"start": words[0]["start"], "end": words[-1]["end"], "text": s, "words": words})
        t += 0.3
    return {"language": "en", "segments": segs}


SENTENCES = [
    "So yeah we were talking about that earlier.",
    "Why do most people never get rich from their job?",
    "The biggest mistake is trading time for money and nothing else.",
    "You need to own something that earns while you sleep.",
    "I learned that the hard way after I got fired at twenty five.",
    "And that changed everything for me honestly.",
] * 4


def test_ass_color_and_time():
    assert ass_color("#FFE14D") == "&H004DE1FF"
    assert ass_time(3723.456) == "1:02:03.46"


def test_chunk_words_breaks_on_punctuation_and_size():
    words = [{"start": i, "end": i + 0.5, "word": w} for i, w in enumerate("one two three four. five six".split())]
    chunks = [[w["word"] for w in c] for c in chunk_words(words, per_chunk=3)]
    assert chunks == [["one", "two", "three"], ["four."], ["five", "six"]]


def test_build_ass_has_hook_and_relative_times():
    tr = _transcript(["Hello there friend.", "This is a test."])
    words = [w for s in tr["segments"] for w in s["words"]]
    ass = build_ass(words, 0.0, 5.0, "Big hook here", DEFAULTS["render"])
    assert "Style: Hook" in ass and "BIG HOOK HERE" in ass
    assert "Dialogue: 1,0:00:00.00" in ass
    assert "{" not in "".join(w["word"] for w in words)


def test_caption_events_never_overlap():
    tr = _transcript(SENTENCES[:4], wps=4.0)
    words = [w for s in tr["segments"] for w in s["words"]]
    ass = build_ass(words, 0.0, 20.0, "", DEFAULTS["render"])

    def secs(ts):
        h, m, s = ts.split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    lines = [ln.split(",") for ln in ass.splitlines() if ln.startswith("Dialogue: 1,")]
    spans = sorted((secs(f[1]), secs(f[2])) for f in lines)
    for (s1, e1), (s2, _) in zip(spans, spans[1:]):
        assert e1 <= s2 + 1e-6


def test_snap_hits_word_boundaries():
    tr = _transcript(SENTENCES[:3])
    s, e = snap(tr, 2.9, 7.1)
    starts = {w["start"] for seg in tr["segments"] for w in seg["words"]}
    assert round(s + 0.08, 3) in starts
    assert e > s


def test_local_picker_returns_non_overlapping_clips_in_range():
    tr = _transcript(SENTENCES)
    cfg = dict(DEFAULTS["picker"], clips_per_video=3)
    picks = pick_local(tr, CAMPAIGN, cfg)
    assert 1 <= len(picks) <= 3
    for a in picks:
        assert cfg["min_seconds"] - 1 <= a.end - a.start <= cfg["max_seconds"] + 1
        assert "@host" in a.caption and "#podcast #clips" in a.caption
    for a, b in zip(picks, picks[1:]):
        assert a.end <= b.start
    assert not picks[0].hook.lower().startswith("so yeah")


def test_dedupe_keeps_best_non_overlapping():
    picks = [Pick(0, 30, "a", "", 5, ""), Pick(10, 40, "b", "", 9, ""), Pick(41, 70, "c", "", 1, "")]
    assert [p.hook for p in _dedupe(picks, 5)] == ["b", "c"]


def test_compact_transcript_is_one_line_per_segment():
    tr = _transcript(SENTENCES[:3])
    assert len(compact_transcript(tr).splitlines()) == 3


def test_shots_hysteresis_and_expr():
    # speaker on the left for 3s, then right for 3s; one-frame blips are ignored
    centers = [0.3] * 6 + [0.9] + [0.3] * 1 + [0.7] * 6
    shots = shots_from_centers(centers, src_w=1920, crop_w=608)
    assert len(shots) == 2
    assert shots[0][1] < shots[1][1]
    expr = crop_x_expr(shots)
    assert expr.startswith("if(lt(t\\,") and expr.endswith(")")
    assert crop_x_expr([(0.0, 100)]) == "100"


def test_build_caption_formats_tags():
    assert build_caption("Line", Campaign(slug="x", name="X", hashtags=["a"])) == "Line\n\n#a"
