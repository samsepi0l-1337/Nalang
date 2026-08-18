import numpy as np

MIN_BASELINE = 10
PERSIST_S = 5
SOFT_RATIO = 0.05
SHARP_RATIO = 0.10


def mean_shift_ratio(rms_g: float, baseline: list[float]) -> float | None:
    if len(baseline) < MIN_BASELINE:
        return None
    mean = float(np.mean(baseline))
    if mean <= 1e-9:
        return float("inf") if rms_g > 0 else 0.0
    return abs(rms_g - mean) / mean


class PersistTracker:
    def __init__(self, needed: int = PERSIST_S) -> None:
        self._needed = needed
        self._streak = 0
        self._on = False
        self.changed = False

    def update(self, ratio: float | None) -> bool:
        sharp = ratio is not None and ratio >= SHARP_RATIO
        soft = ratio is not None and ratio >= SOFT_RATIO
        if sharp:
            self._streak = self._needed
            now = True
        elif soft:
            self._streak += 1
            now = self._streak >= self._needed
        else:
            self._streak = 0
            now = False
        self.changed = now != self._on
        self._on = now
        return now
