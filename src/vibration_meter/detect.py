"""Switchable absolute-g error detection.

Alert when window RMS reaches the selected threshold: 0.7 g or 8 g.
"""

THRESHOLDS_G = (0.7, 8.0)
DEFAULT_THRESHOLD_G = 0.7


def parse_threshold(value: object) -> float:
    """Accept 0.7 or 8 (int/float/str). Return the canonical float from THRESHOLDS_G.
    Raise ValueError otherwise."""
    # 8 은 int·"8" 로 들어와도 표의 8.0 이어야 한다.
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        as_float = float(value)
    elif isinstance(value, str):
        try:
            as_float = float(value)
        except ValueError:
            raise ValueError(f"unknown threshold: {value!r}") from None
    else:
        raise ValueError(f"unknown threshold: {value!r}")
    for canonical in THRESHOLDS_G:
        if as_float == canonical:
            return canonical
    raise ValueError(f"unknown threshold: {value!r}")


class DetectMode:
    def __init__(self, threshold_g: float = DEFAULT_THRESHOLD_G) -> None:
        self._threshold_g = parse_threshold(threshold_g)

    @property
    def threshold_g(self) -> float:
        return self._threshold_g

    def set_threshold(self, threshold_g: object) -> float:
        """Parse, store, return canonical threshold."""
        self._threshold_g = parse_threshold(threshold_g)
        return self._threshold_g

    def is_alert(self, rms_g: float) -> bool:
        """True iff rms_g >= threshold_g."""
        # 비율·지속이 아니다. 창 RMS 가 임계값에 닿는 즉시 켠다.
        return rms_g >= self._threshold_g


# CLI·웹·측정 루프가 같은 판정값을 본다.
mode = DetectMode()
