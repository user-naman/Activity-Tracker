"""Decide how a 16:9 frame becomes 9:16: follow the speaker's face, or blur-pad.

Face tracking samples a few frames per second with OpenCV's bundled detector
(no model download), then turns positions into "camera cuts": a piecewise-constant
crop that jumps when the speaker changes, like a human editor would.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .util import MediaInfo, log

SAMPLE_EVERY = 0.5     # seconds between detections
MOVE_THRESHOLD = 0.12  # fraction of source width before we cut to a new position
MIN_SHOT = 1.5         # seconds; never cut faster than this
MIN_HIT_RATE = 0.35    # below this, faces are unreliable: use blur layout


@dataclass
class Plan:
    layout: str                              # face | blur | center | native
    crop_w: int = 0
    shots: list[tuple[float, int]] | None = None   # (relative start time, crop x)


def _detect_centers(path: Path, start: float, end: float, info: MediaInfo) -> list[float | None]:
    import cv2

    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    if cascade.empty():
        raise ImportError("face cascade not bundled with this OpenCV build")
    cap = cv2.VideoCapture(str(path))
    scale = 640 / info.width if info.width > 640 else 1.0
    centers: list[float | None] = []
    t = start
    while t < end:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
        ok, frame = cap.read()
        if not ok:
            centers.append(None)
            t += SAMPLE_EVERY
            continue
        small = cv2.resize(frame, None, fx=scale, fy=scale) if scale != 1.0 else frame
        gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        min_side = max(24, int(small.shape[0] * 0.08))
        faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(min_side, min_side))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            centers.append(((x + w / 2) / scale) / info.width)
        else:
            centers.append(None)
        t += SAMPLE_EVERY
    cap.release()
    return centers


def shots_from_centers(centers: list[float | None], src_w: int, crop_w: int) -> list[tuple[float, int]]:
    """Pure function: normalised face centers -> [(t, crop_x)] with hysteresis."""
    filled: list[float] = []
    last = next((c for c in centers if c is not None), 0.5)
    for c in centers:
        last = c if c is not None else last
        filled.append(last)

    def to_x(cx: float) -> int:
        x = int(round(cx * src_w - crop_w / 2))
        return max(0, min(src_w - crop_w, x)) // 2 * 2

    shots = [(0.0, to_x(filled[0]))]
    anchor, anchor_t = filled[0], 0.0
    for i in range(1, len(filled)):
        t = i * SAMPLE_EVERY
        confirmed = i + 1 < len(filled) and abs(filled[i + 1] - anchor) > MOVE_THRESHOLD
        if abs(filled[i] - anchor) > MOVE_THRESHOLD and confirmed and t - anchor_t >= MIN_SHOT:
            anchor, anchor_t = filled[i], t
            shots.append((t, to_x(anchor)))
    return shots


def crop_x_expr(shots: list[tuple[float, int]]) -> str:
    """[(0,100),(3.5,620)] -> if(lt(t,3.5),100,620) for ffmpeg's per-frame crop x."""
    expr = str(shots[-1][1])
    for (_, x), (t_next, _) in reversed(list(zip(shots, shots[1:]))):
        expr = f"if(lt(t\\,{t_next:.2f})\\,{x}\\,{expr})"
    return expr


def plan(path: Path, start: float, end: float, info: MediaInfo, layout: str) -> Plan:
    if info.width / info.height <= 0.6:
        return Plan("native")
    crop_w = int(info.height * 9 / 16) // 2 * 2
    if layout == "center":
        return Plan("center", crop_w, [(0.0, (info.width - crop_w) // 2 // 2 * 2)])
    if layout == "blur":
        return Plan("blur")

    try:
        centers = _detect_centers(path, start, end, info)
    except ImportError:
        log("opencv not installed; using blur layout")
        return Plan("blur")
    hit_rate = sum(c is not None for c in centers) / max(1, len(centers))
    if hit_rate < MIN_HIT_RATE and layout == "auto":
        log(f"faces found in {hit_rate:.0%} of frames; using blur layout")
        return Plan("blur")
    shots = shots_from_centers(centers, info.width, crop_w)
    log(f"face tracking: {hit_rate:.0%} hit rate, {len(shots)} shot(s)")
    return Plan("face", crop_w, shots)
