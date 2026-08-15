import math

from vibration_meter.adxl355 import Adxl355, SpiDevice
from vibration_meter.display import LcdDevice


class MockSensor:
    def __init__(self, dt: float = 0.001) -> None:
        self._t = 0.0
        self._dt = dt

    def read_xyz_g(self) -> tuple[float, float, float]:
        y = 0.1 * math.sin(2 * math.pi * 20 * self._t)
        self._t += self._dt
        return (0.0, y, 1.0)


class RplcdAdapter:
    def __init__(self, lcd: object) -> None:
        self._lcd = lcd

    def update(self, line1: str, line2: str) -> None:
        self._lcd.cursor_pos = (0, 0)
        self._lcd.write_string(line1)
        self._lcd.cursor_pos = (1, 0)
        self._lcd.write_string(line2)


def open_spi() -> SpiDevice:
    import spidev

    spi = spidev.SpiDev()
    spi.open(0, 0)
    spi.max_speed_hz = 1_000_000
    spi.mode = 0
    return spi


def open_lcd(address: int = 0x27) -> LcdDevice:
    from RPLCD.i2c import CharLCD

    try:
        return RplcdAdapter(CharLCD("PCF8574", address))
    except Exception:
        if address != 0x3F:
            return open_lcd(0x3F)
        raise


def open_sensor(mock: bool) -> Adxl355 | MockSensor:
    if mock:
        return MockSensor()
    sensor = Adxl355(open_spi())
    sensor.begin()
    return sensor


def open_display() -> LcdDevice | None:
    try:
        return open_lcd()
    except Exception as exc:
        print(f"LCD unavailable: {exc}", flush=True)
        return None
