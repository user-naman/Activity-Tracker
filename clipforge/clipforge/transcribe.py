"""Local word-level transcription with faster-whisper. Free, cached per source."""

from __future__ import annotations

import json
import os
import wave
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

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")  # harmless on Windows, just noisy
    os.environ.setdefault("HF_HUB_VERBOSITY", "error")
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:
        raise ClipForgeError("faster-whisper is not installed. Run: pip install -e .") from e

    audio = source_path.parent / "audio.wav"
    run([require_bin("ffmpeg"), "-y", "-v", "error", "-i", str(source_path),
         "-vn", "-ac", "1", "-ar", "16000", str(audio)])

    samples = load_wav(audio)

    log(f"transcribing with whisper '{cfg['model']}' (first run downloads the model)…")

    def _run(device: str):
        model = WhisperModel(cfg["model"], device=device, compute_type=cfg["compute_type"])
        segs, inf = model.transcribe(
            samples, language=cfg.get("language") or None, word_timestamps=True, vad_filter=True,
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


def load_wav(path: Path):
    """16 kHz mono s16 WAV (made by our ffmpeg call) -> float32 samples.

    Passing samples instead of a path skips faster-whisper's PyAV decoder, whose
    API changes between versions (e.g. PyAV 15 dropped `metadata_errors`).
    """
    import numpy as np

    with wave.open(str(path), "rb") as w:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ClipForgeError(f"Unexpected audio format in {path.name}")
        frames = w.readframes(w.getnframes())
    return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0


def words_between(transcript: dict, start: float, end: float) -> list[dict]:
    return [
        w for seg in transcript["segments"] for w in seg["words"]
        if w["end"] > start and w["start"] < end
    ]
