import time
from collections.abc import Callable
from typing import Protocol

# 1602 는 I2C 로 32자를 밀어 넣는 데 수십 ms 가 든다. 창이 0.2초까지
# 짧아지면 그 비용이 측정 시간을 갉아먹고 화면도 깜빡인다.
LCD_MIN_INTERVAL_S = 0.5


class LcdDevice(Protocol):
    def update(self, line1: str, line2: str) -> None: ...


class UpdateThrottle:
    """갱신 주기와 무관하게 1602 쓰기 간격에 하한을 둔다."""

    def __init__(
        self,
        min_interval_s: float = LCD_MIN_INTERVAL_S,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self._min_interval_s = min_interval_s
        self._now = now
        self._last: float | None = None

    def due(self, force: bool = False) -> bool:
        """force 는 이상치 전환용이다. 솎아내기가 경보를 늦추면 안 된다."""
        current = self._now()
        if not force and self._last is not None:
            if current - self._last < self._min_interval_s:
                return False
        self._last = current
        return True


def format_rms_line(rms_g: float) -> str:
    return f"RMS {rms_g:.3f} g".ljust(16)[:16]


def format_peak_line(peak_g: float, axis: str) -> str:
    return f"PK  {peak_g:.3f} g {axis}".ljust(16)[:16]


def format_outlier_line(axis: str) -> str:
    return ("OUTLIER" + " " * 8 + axis).ljust(16)[:16]


def show(
    lcd: LcdDevice,
    rms_g: float,
    peak_g: float,
    axis: str,
    alert: bool = False,
) -> None:
    line2 = format_outlier_line(axis) if alert else format_peak_line(peak_g, axis)
    lcd.update(format_rms_line(rms_g), line2)
