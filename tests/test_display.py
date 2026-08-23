from vibration_meter.display import (
    UpdateThrottle,
    format_outlier_line,
    format_peak_line,
    format_rms_line,
    show,
)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


class FakeLcd:
    def __init__(self) -> None:
        self.lines: tuple[str, str] | None = None

    def update(self, line1: str, line2: str) -> None:
        self.lines = (line1, line2)


def test_rms_line_is_16_chars():
    line = format_rms_line(0.123)
    assert len(line) == 16
    assert line.startswith("RMS 0.123 g")


def test_peak_line_includes_axis():
    line = format_peak_line(0.456, "Y")
    assert len(line) == 16
    assert "0.456" in line
    assert "Y" in line


def test_show_writes_both_lines():
    lcd = FakeLcd()
    show(lcd, 0.123, 0.456, "Z")
    assert lcd.lines is not None
    assert lcd.lines[0].startswith("RMS")
    assert "Z" in lcd.lines[1]


def test_outlier_line_is_16_chars_and_show_swaps_line2():
    line = format_outlier_line("Y")
    assert len(line) == 16
    assert line.startswith("OUTLIER")
    assert line.endswith("Y")
    lcd = FakeLcd()
    show(lcd, 0.123, 0.456, "Y", alert=True)
    assert lcd.lines is not None
    assert lcd.lines[1].startswith("OUTLIER")


def test_throttle_skips_writes_inside_the_interval():
    clock = FakeClock()
    throttle = UpdateThrottle(min_interval_s=0.5, now=clock)
    assert throttle.due() is True
    clock.t = 0.2
    assert throttle.due() is False
    clock.t = 0.5
    assert throttle.due() is True


def test_throttle_force_bypasses_and_restarts_the_clock():
    # 이상치 전환은 즉시 띄운다. 솎아내기가 경보를 늦추면 진단이 어긋난다.
    clock = FakeClock()
    throttle = UpdateThrottle(min_interval_s=0.5, now=clock)
    assert throttle.due() is True
    clock.t = 0.1
    assert throttle.due(force=True) is True
    clock.t = 0.4
    assert throttle.due() is False
