"""Switchable absolute-g error detection.

Alert when window RMS reaches the selected product threshold.
Catalog: 0.1 g, 0.7 g, 3 g, 8 g, 10 g (제품 1–5).
Default visible buttons: 0.7 g and 8 g.
"""

from collections.abc import Iterable

PRODUCTS = (
    (0.1, "제품 1"),
    (0.7, "제품 2"),
    (3.0, "제품 3"),
    (8.0, "제품 4"),
    (10.0, "제품 5"),
)
THRESHOLDS_G = tuple(g for g, _name in PRODUCTS)
DEFAULT_THRESHOLD_G = 0.7
DEFAULT_VISIBLE_G = (0.7, 8.0)


def parse_threshold(value: object) -> float:
    """Accept a catalog g value (int/float/str). Return the canonical float.
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


def product_name(threshold_g: float) -> str:
    for g, name in PRODUCTS:
        if g == threshold_g:
            return name
    raise ValueError(f"unknown threshold: {threshold_g!r}")


def products_payload() -> list[dict]:
    return [{"name": name, "threshold_g": g} for g, name in PRODUCTS]


def format_thresholds(*, suffix: str = "") -> str:
    return ", ".join(f"{g:g}{suffix}" for g in THRESHOLDS_G)


def _ordered_visible(values: Iterable[object]) -> tuple[float, ...]:
    wanted = {parse_threshold(value) for value in values}
    ordered = tuple(g for g in THRESHOLDS_G if g in wanted)
    if not ordered:
        raise ValueError("visible products cannot be empty")
    return ordered


class DetectMode:
    def __init__(
        self,
        threshold_g: float = DEFAULT_THRESHOLD_G,
        visible_g: Iterable[object] = DEFAULT_VISIBLE_G,
    ) -> None:
        self._visible_g = _ordered_visible(visible_g)
        self._threshold_g = parse_threshold(threshold_g)
        self._ensure_selected_visible()

    @property
    def threshold_g(self) -> float:
        return self._threshold_g

    @property
    def visible_g(self) -> list[float]:
        return list(self._visible_g)

    def reset(self) -> None:
        self._visible_g = DEFAULT_VISIBLE_G
        self._threshold_g = DEFAULT_THRESHOLD_G

    def set_threshold(self, threshold_g: object) -> float:
        """Parse, store, return canonical threshold. Add it to visible if missing."""
        self._threshold_g = parse_threshold(threshold_g)
        self._ensure_selected_visible()
        return self._threshold_g

    def is_alert(self, rms_g: float) -> bool:
        """True iff rms_g >= threshold_g."""
        # 비율·지속이 아니다. 창 RMS 가 임계값에 닿는 즉시 켠다.
        return rms_g >= self._threshold_g

    def add_visible(self, threshold_g: object) -> list[float]:
        g = parse_threshold(threshold_g)
        if g in self._visible_g:
            raise ValueError(f"already visible: {g:g}")
        self._visible_g = _ordered_visible((*self._visible_g, g))
        return self.visible_g

    def remove_visible(self, threshold_g: object) -> list[float]:
        g = parse_threshold(threshold_g)
        if g not in self._visible_g:
            raise ValueError(f"not visible: {g:g}")
        if len(self._visible_g) == 1:
            raise ValueError("cannot remove last product")
        remaining = tuple(value for value in self._visible_g if value != g)
        self._visible_g = remaining
        if self._threshold_g == g:
            self._threshold_g = remaining[0]
        return self.visible_g

    def _ensure_selected_visible(self) -> None:
        if self._threshold_g not in self._visible_g:
            self._visible_g = _ordered_visible((*self._visible_g, self._threshold_g))


# CLI·웹·측정 루프가 같은 판정값을 본다.
mode = DetectMode()
