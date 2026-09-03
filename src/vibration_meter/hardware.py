import math
from collections.abc import Callable
from typing import Protocol

from vibration_meter.adxl355 import Adxl355, SpiDevice
from vibration_meter.display import LcdDevice
from vibration_meter.errors import (
    HINT_BUZZ,
    HINT_BUZZ_BUSY,
    HINT_LCD,
    HINT_SAMPLE,
    HINT_SPI_MISSING,
    HINT_SPI_PERM,
    HINT_SPIDEV_PKG,
    HardwareError,
    format_fail,
    format_ok,
)
from vibration_meter.logutil import get_logger


class BuzzerDevice(Protocol):
    def set_alert(self, on: bool) -> None: ...


class ToneCapableBuzzer(BuzzerDevice, Protocol):
    """진단이 요구하는 확장. 앱은 set_alert 만 쓴다."""

    def play_hz(self, hz: float) -> None: ...
    def stop(self) -> None: ...


SpiFactory = Callable[[], SpiDevice]
LcdFactory = Callable[[int], LcdDevice]
BuzzerFactory = Callable[[], BuzzerDevice]
ToneFactory = Callable[[float], object]

# gpiozero/lgpio 는 GPIO 18(물리 핀 12)에서 PWM 을 거절한다
# ("pwm is not supported on pin gpio18"). 하드웨어 PWM 은 핀 32(BCM 12,
# PWM0)와 핀 33(BCM 13, PWM1). 부저는 PWM0 을 쓴다.
BUZZER_PIN = 32
BUZZER_BCM = 12
TONE_HZ = 1000

# TonalBuzzer 는 mid_tone 을 중심으로 ±octaves 만 낸다. 기본값 A4(440 Hz)/1
# 옥타브면 220~880 Hz 라서 1 kHz 경보음이 아예 범위 밖이다. 2 옥타브로
# 110~1760 Hz 를 확보한다.
MID_TONE_HZ = 440
BUZZER_OCTAVES = 2


def tone_range_hz(
    mid_hz: float = MID_TONE_HZ, octaves: int = BUZZER_OCTAVES
) -> tuple[float, float]:
    """이 설정으로 실제로 낼 수 있는 주파수 구간."""
    span = 2**octaves
    return (mid_hz / span, mid_hz * span)


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


class ToneBuzzer:
    def __init__(
        self, device: object, tone_for: ToneFactory, alert_hz: float = TONE_HZ
    ) -> None:
        self._device = device
        self._tone_for = tone_for
        self._alert_hz = alert_hz
        self._on = False

    def set_alert(self, on: bool) -> None:
        if on == self._on:
            return
        self._on = on
        if on:
            self._device.play(self._tone_for(self._alert_hz))
        else:
            self._device.stop()

    def play_hz(self, hz: float) -> None:
        """진단용. 음정을 바꿔 패시브(KY-006)와 액티브(KY-012)를 가른다."""
        self._on = True
        self._device.play(self._tone_for(hz))

    def stop(self) -> None:
        self._on = False
        self._device.stop()


def open_spi(create: SpiFactory | None = None) -> SpiDevice:
    log = get_logger()
    try:
        if create is None:
            import spidev

            spi = spidev.SpiDev()
            spi.open(0, 0)
            spi.max_speed_hz = 1_000_000
            spi.mode = 0
            spi.lsbfirst = False
            spi.bits_per_word = 8
        else:
            spi = create()
    except FileNotFoundError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPI_MISSING) from exc
    except PermissionError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPI_PERM) from exc
    except ModuleNotFoundError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPIDEV_PKG) from exc
    except OSError as exc:
        raise HardwareError("SPI_OPEN", str(exc), HINT_SPI_MISSING) from exc
    log.info(format_ok("SPI_OPEN", "/dev/spidev0.0 1MHz mode0"))
    return spi


def open_lcd(address: int = 0x27) -> LcdDevice:
    from RPLCD.i2c import CharLCD

    log = get_logger()
    log.info(format_ok("LCD_ADDR", f"trying 0x{address:02X}"))
    try:
        lcd = RplcdAdapter(CharLCD("PCF8574", address))
    except Exception as exc:
        log.warning(format_fail("LCD_ADDR", f"address=0x{address:02X} {exc}", HINT_LCD))
        if address != 0x3F:
            return open_lcd(0x3F)
        raise HardwareError("LCD_OPEN", str(exc), HINT_LCD) from exc
    log.info(format_ok("LCD_OPEN", f"address=0x{address:02X}"))
    return lcd


def open_sensor(mock: bool, spi: SpiDevice | None = None) -> Adxl355 | MockSensor:
    log = get_logger()
    if mock:
        log.info(format_ok("MOCK", "synthetic sine on Y, no SPI"))
        return MockSensor()
    sensor = Adxl355(spi if spi is not None else open_spi())
    try:
        sensor.begin()
    except HardwareError:
        raise
    except Exception as exc:
        raise HardwareError("SENSOR_ID", str(exc), HINT_SAMPLE) from exc
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


def buzz_open_hint(exc: Exception) -> str:
    """핀 점유는 배선 문제로 읽히기 쉽다. 서비스가 도는 중이라는 뜻이다."""
    if type(exc).__name__ == "GPIOPinInUse" or "in use" in str(exc).lower():
        return HINT_BUZZ_BUSY
    return HINT_BUZZ


def open_buzzer(create: BuzzerFactory | None = None) -> BuzzerDevice | None:
    log = get_logger()
    try:
        if create is None:
            from gpiozero import TonalBuzzer
            from gpiozero.tones import Tone

            buzzer = ToneBuzzer(
                TonalBuzzer(BUZZER_BCM, octaves=BUZZER_OCTAVES),
                Tone.from_frequency,
            )
        else:
            buzzer = create()
    except Exception as exc:
        log.error(format_fail("BUZZ_OPEN", str(exc), buzz_open_hint(exc)))
        return None
    low, high = tone_range_hz()
    log.info(
        format_ok(
            "BUZZ_OPEN",
            f"BCM {BUZZER_BCM} {TONE_HZ}Hz tone() 음역 {low:.0f}~{high:.0f}Hz",
        )
    )
    return buzzer
