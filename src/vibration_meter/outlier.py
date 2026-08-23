import numpy as np

# 아래 둘은 창 개수가 아니라 초다. 창이 1초일 때만 두 값이 같았다.
# 창을 짧게 만들면 windows_for 로 환산해야 판정 기준이 그대로 남는다.
BASELINE_S = 10
PERSIST_S = 5
SOFT_RATIO = 0.05
SHARP_RATIO = 0.10

# 초를 개수로 바꾸는 기준 창. 예전 1초 창의 값이 그대로 나오게 하는 앵커다.
REFERENCE_WINDOW_S = 1.0


def windows_for(seconds: float, window_s: float) -> int:
    """초 단위 기준을 창 개수로 바꾼다. 창이 짧아져도 시간 기준은 유지된다."""
    return max(1, round(seconds / window_s))


MIN_BASELINE = windows_for(BASELINE_S, REFERENCE_WINDOW_S)


def mean_shift_ratio(
    rms_g: float, baseline: list[float], min_count: int = MIN_BASELINE
) -> float | None:
    if len(baseline) < min_count:
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
