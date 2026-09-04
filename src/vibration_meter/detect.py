"""Switchable absolute-g error detection.

Alert when window RMS reaches the selected threshold: 0.7 g or 8 g.
"""

THRESHOLDS_G = (0.7, 8.0)
DEFAULT_THRESHOLD_G = 0.7


def parse_threshold(value: object) -> float:
    try:
        threshold = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"detect threshold {value!r} is not a number") from exc
    for allowed in THRESHOLDS_G:
        if abs(threshold - allowed) < 1e-9:
            return allowed
    raise ValueError(
        f"detect threshold {threshold} is not one of {THRESHOLDS_G}"
    )


class DetectMode:
    def __init__(self, threshold_g: float = DEFAULT_THRESHOLD_G) -> None:
        self._threshold_g = parse_threshold(threshold_g)

    @property
    def threshold_g(self) -> float:
        return self._threshold_g

    def set_threshold(self, threshold_g: object) -> float:
        self._threshold_g = parse_threshold(threshold_g)
        return self._threshold_g

    def is_alert(self, rms_g: float) -> bool:
        return rms_g >= self._threshold_g


mode = DetectMode()
