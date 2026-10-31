"""Local word-level transcription with faster-whisper. Free, cached per source."""

from __future__ import annotations

import json
from pathlib import Path

from .util import ClipForgeError, log, require_bin, run


def transcript_path(source_path: Path) -> Path:
    return source_path.parent / "transcript.json"


def load_transcript(source_path: Path) -> dict:
    path = transcript_path(source_path)
    if not path.exists():
        raise ClipForgeError(f"No transcript yet for {source_path.parent.name}. Run `clipforge process <source id>`.")
    return json.loads(path.read_text(encoding="utf-8"))


def transcribe(source_path: Path, cfg: dict, *, force: bool = False) -> dict:
    out = transcript_path(source_path)
    if out.exists() and not force:
        log("transcript cached")
        return json.loads(out.read_text(encoding="utf-8"))

    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ClipForgeError("faster-whisper is not installed. Run: pip install -e .") from e

    audio = source_path.parent / "audio.wav"
    run([require_bin("ffmpeg"), "-y", "-v", "error", "-i", str(source_path),
         "-vn", "-ac", "1", "-ar", "16000", str(audio)])

    log(f"transcribing with whisper '{cfg['model']}' (first run downloads the model)…")
    def _run(device: str):
        model = WhisperModel(cfg["model"], device=device, compute_type=cfg["compute_type"])
        segs, inf = model.transcribe(
            str(audio), language=cfg.get("language") or None, word_timestamps=True, vad_filter=True,
        )
        return list(segs), inf  # materialise so GPU/driver errors surface here

    try:
        segments, info = _run(cfg["device"])
    except (RuntimeError, OSError) as e:
        if cfg["device"] == "cpu":
            raise
        # Common on Windows laptops: a GPU is visible but CUDA/cuDNN DLLs are missing.
        log(f"GPU transcription failed ({str(e).splitlines()[0][:80]}); using CPU")
        segments, info = _run("cpu")
    result = {"language": info.language, "segments": []}
    for seg in segments:
        words = [
            {"start": round(w.start, 3), "end": round(w.end, 3), "word": w.word.strip()}
            for w in (seg.words or []) if w.word.strip()
        ]
        if words:
            result["segments"].append({
                "start": round(seg.start, 3), "end": round(seg.end, 3),
                "text": seg.text.strip(), "words": words,
            })
    out.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    audio.unlink(missing_ok=True)
    log(f"transcript: {len(result['segments'])} segments, language={info.language}")
    return result


def words_between(transcript: dict, start: float, end: float) -> list[dict]:
    return [
        w for seg in transcript["segments"] for w in seg["words"]
        if w["end"] > start and w["start"] < end
    ]
