from vibration_meter.display import format_peak_line, format_rms_line, show


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
