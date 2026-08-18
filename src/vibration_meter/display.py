from typing import Protocol


class LcdDevice(Protocol):
    def update(self, line1: str, line2: str) -> None: ...


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
