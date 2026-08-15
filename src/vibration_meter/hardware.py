import math
from collections.abc import Callable

from vibration_meter.adxl355 import Adxl355, SpiDevice
from vibration_meter.display import LcdDevice
from vibration_meter.errors import (
    HINT_LCD,
    HINT_SPI_MISSING,
    HINT_SPI_PERM,
    HINT_SPIDEV_PKG,
    HardwareError,
    format_fail,
    format_ok,
)
from vibration_meter.logutil import get_logger

SpiFactory = Callable[[], SpiDevice]
LcdFactory = Callable[[int], LcdDevice]


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


def open_spi(create: SpiFactory | None = None) -> SpiDevice:
    log = get_logger()
    try:
        if create is None:
            import spidev

            spi = spidev.SpiDev()
            spi.open(0, 0)
            spi.max_speed_hz = 1_000_000
            spi.mode = 0
        else:
            spi = create()
    except FileNotFoundError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPI_MISSING) from exc
    except PermissionError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPI_PERM) from exc
    except ModuleNotFoundError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPIDEV_PKG) from exc
    log.info(format_ok("SPI_OPEN", "/dev/spidev0.0 1MHz mode0"))
    return spi


def open_lcd(address: int = 0x27) -> LcdDevice:
    from RPLCD.i2c import CharLCD

    log = get_logger()
    log.info("[LCD_ADDR] trying 0x%02X", address)
    try:
        lcd = RplcdAdapter(CharLCD("PCF8574", address))
    except Exception as exc:
        log.warning("[LCD_ADDR] FAIL address=0x%02X %s", address, exc)
        if address != 0x3F:
            return open_lcd(0x3F)
        raise HardwareError("LCD_OPEN", str(exc), HINT_LCD) from exc
    log.info(format_ok("LCD_OPEN", f"address=0x{address:02X}"))
    return lcd


def open_sensor(mock: bool) -> Adxl355 | MockSensor:
    log = get_logger()
    if mock:
        log.info(format_ok("MOCK", "synthetic sine on Y, no SPI"))
        return MockSensor()
    sensor = Adxl355(open_spi())
    sensor.begin()
    return sensor


def open_display(open_at: LcdFactory | None = None) -> LcdDevice | None:
    log = get_logger()
    try:
        lcd = open_at(0x27) if open_at is not None else open_lcd()
    except Exception as exc:
        message = str(exc)
        hint = exc.hint if isinstance(exc, HardwareError) else HINT_LCD
        log.error(format_fail("LCD_OPEN", message, hint))
        return None
    if open_at is not None:
        log.info(format_ok("LCD_OPEN", "injected"))
    return lcd
