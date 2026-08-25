from collections import deque
from dataclasses import dataclass

import numpy as np

AXES = ("X", "Y", "Z")


@dataclass(frozen=True)
class WindowMetrics:
    axis: str
    rms_g: float
    peak_g: float


def window_metrics(x, y, z) -> WindowMetrics:
    series = {
        "X": np.asarray(x, dtype=float),
        "Y": np.asarray(y, dtype=float),
        "Z": np.asarray(z, dtype=float),
    }
    best_axis = "X"
    best_rms = -1.0
    best_peak = 0.0
    for axis in AXES:
        data = series[axis]
        ac = data - data.mean()
        rms = float(np.sqrt(np.mean(ac * ac)))
        peak = float(np.max(np.abs(ac))) if data.size else 0.0
        if rms > best_rms:
            best_axis = axis
            best_rms = rms
            best_peak = peak
    return WindowMetrics(axis=best_axis, rms_g=best_rms, peak_g=best_peak)


class RmsHistory:
    def __init__(self, maxlen: int = 60, window_s: float = 60.0) -> None:
        self._points: deque[dict[str, float]] = deque(maxlen=maxlen)
        self._window_s = window_s

    def push(self, t: float, rms_g: float) -> None:
        self._points.append({"t": t, "rms_g": rms_g})
        cutoff = t - self._window_s
        while self._points and self._points[0]["t"] < cutoff:
            self._points.popleft()

    def as_list(self) -> list[dict[str, float]]:
        return list(self._points)
