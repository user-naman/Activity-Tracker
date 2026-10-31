"""Instagram and Claude integrations, with the network mocked out."""

import json
from types import SimpleNamespace

import pytest

from clipforge.config import DEFAULTS, Campaign
from clipforge.db import DB
from clipforge.instagram import Instagram
from clipforge.util import ClipForgeError

from test_core import SENTENCES, _transcript


@pytest.fixture
def db(tmp_path):
    return DB(tmp_path / "t.db")


def test_publish_reel_follows_container_upload_poll_publish(db, tmp_path, monkeypatch):
    monkeypatch.setenv("IG_ACCESS_TOKEN", "tok")
    ig = Instagram(dict(DEFAULTS["instagram"], user_id="42"), db)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x" * 1234)
    calls, polls = [], iter(["IN_PROGRESS", "FINISHED"])
    monkeypatch.setattr("time.sleep", lambda _: None)

    def fake(method, url, params=None, *, data=None, headers=None):
        calls.append((method, url, params, headers))
        if url.endswith("/42/media"):
            return {"id": "C1"}
        if "rupload.facebook.com" in url:
            assert headers["file_size"] == "1234" and headers["Authorization"] == "OAuth tok"
            return {"success": True}
        if url.endswith("/C1"):
            return {"status_code": next(polls)}
        if url.endswith("/media_publish"):
            assert params == {"creation_id": "C1"}
            return {"id": "M9"}
        if url.endswith("/M9"):
            return {"permalink": "https://instagram.com/reel/abc"}
        raise AssertionError(url)

    monkeypatch.setattr(ig, "_call", fake)
    assert ig.publish_reel(video, "cap") == ("M9", "https://instagram.com/reel/abc")
    assert calls[0][2]["media_type"] == "REELS" and calls[0][2]["upload_type"] == "resumable"


def test_publish_surfaces_processing_error(db, tmp_path, monkeypatch):
    monkeypatch.setenv("IG_ACCESS_TOKEN", "tok")
    ig = Instagram(dict(DEFAULTS["instagram"], user_id="42"), db)
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    monkeypatch.setattr(ig, "_call", lambda m, url, *a, **k: (
        {"id": "C1"} if url.endswith("/media") else
        {"status_code": "ERROR", "status": "bad codec"} if url.endswith("/C1") else {}))
    with pytest.raises(ClipForgeError, match="bad codec"):
        ig.publish_reel(video, "cap")


def test_instagram_requires_credentials(db, monkeypatch):
    monkeypatch.delenv("IG_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("IG_USER_ID", raising=False)
    with pytest.raises(ClipForgeError, match="not connected"):
        Instagram(DEFAULTS["instagram"], db)


def test_llm_picker_parses_snaps_and_tags(monkeypatch, tmp_path):
    import anthropic
    from clipforge import pick as pick_mod

    tr = _transcript(SENTENCES)
    seg = tr["segments"]
    payload = {"clips": [
        {"start": seg[1]["start"], "end": seg[6]["end"], "hook": "Why you stay broke",
         "caption": "The trap nobody explains.", "score": 8.5, "why": "question hook"},
        {"start": 0, "end": 3, "hook": "too short", "caption": "x", "score": 9, "why": "x"},
    ]}
    seen = {}

    class FakeMessages:
        def create(self, **kw):
            seen.update(kw)
            return SimpleNamespace(
                stop_reason="end_turn",
                usage=SimpleNamespace(input_tokens=1000, output_tokens=200),
                content=[SimpleNamespace(type="text", text=json.dumps(payload))],
            )

    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace(beta=SimpleNamespace(messages=FakeMessages())))
    camp = Campaign(slug="c", name="C", mention="@c")
    picks = pick_mod.pick(tr, camp, DEFAULTS["picker"], "Title", tmp_path, mode="llm")

    assert [p.hook for p in picks] == ["Why you stay broke"]
    assert picks[0].caption.endswith("@c")
    assert "<transcript>" in seen["messages"][0]["content"]
    assert seen["output_config"]["effort"] == "low"
    # second call is served from the on-disk cache: zero API spend
    monkeypatch.setattr(anthropic, "Anthropic", lambda: (_ for _ in ()).throw(AssertionError("API called")))
    assert pick_mod.pick(tr, camp, DEFAULTS["picker"], "Title", tmp_path, mode="llm")[0].hook == "Why you stay broke"
