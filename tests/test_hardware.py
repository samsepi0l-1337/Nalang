import logging
import sys
import types

import pytest

from vibration_meter.errors import HINT_BUZZ, HINT_BUZZ_BUSY, HardwareError
from vibration_meter.hardware import (
    buzz_open_hint,
    open_buzzer,
    open_display,
    open_lcd,
    open_sensor,
    open_spi,
)


def test_open_spi_missing_device_uses_spi_open_stage():
    def create():
        raise FileNotFoundError("/dev/spidev0.0")

    with pytest.raises(HardwareError) as caught:
        open_spi(create=create)
    assert caught.value.stage == "SPI_OPEN"
    assert "spidev" in caught.value.hint.lower() or "SPI" in caught.value.hint


def test_open_sensor_mock_logs_ok(caplog):
    caplog.set_level(logging.INFO)
    sensor = open_sensor(mock=True)
    assert sensor is not None
    assert any("MOCK" in rec.message for rec in caplog.records)


def test_open_display_logs_fail_and_returns_none(caplog):
    caplog.set_level(logging.ERROR)

    def opener(_address: int):
        raise OSError("No such device")

    lcd = open_display(open_at=opener)
    assert lcd is None
    assert any("LCD_OPEN" in rec.message for rec in caplog.records)


def test_open_buzzer_logs_fail_and_returns_none(caplog):
    caplog.set_level(logging.ERROR)

    def opener():
        raise OSError("No such device")

    buzzer = open_buzzer(create=opener)
    assert buzzer is None
    assert any("BUZZ_OPEN" in rec.message for rec in caplog.records)


class BoomSpi:
    def xfer2(self, data: list[int]) -> list[int]:
        raise OSError("spi nak")


def test_open_sensor_begin_oserror_is_hardware_error():
    with pytest.raises(HardwareError) as caught:
        open_sensor(mock=False, spi=BoomSpi())
    assert caught.value.stage == "SENSOR_ID"
    assert "spi nak" in str(caught.value)


class GPIOPinInUse(Exception):
    """gpiozero 예외 이름을 그대로 흉내 낸다. Pi 밖에서는 import 할 수 없다."""


def test_pin_in_use_points_at_the_running_service_not_the_wiring():
    # 이 오진이 진단 도구의 존재 이유를 없앤다. 서비스 정지를 먼저 말해야 한다.
    hint = buzz_open_hint(GPIOPinInUse("GPIO 18 is already in use"))
    assert hint == HINT_BUZZ_BUSY
    assert "systemctl stop" in hint


def test_plain_failure_keeps_the_wiring_hint():
    assert buzz_open_hint(OSError("No such device")) == HINT_BUZZ


def test_open_buzzer_busy_hint_reaches_the_log(caplog):
    caplog.set_level(logging.ERROR)

    def busy():
        raise GPIOPinInUse("GPIO 18 is already in use")

    assert open_buzzer(create=busy) is None
    assert any("systemctl stop" in rec.message for rec in caplog.records)


def test_open_spi_oserror_is_spi_open():
    # FileNotFoundError/PermissionError 만 잡으면 EIO·EBUSY 가 raw 로 샌다.
    def create():
        raise OSError("EIO")

    with pytest.raises(HardwareError) as caught:
        open_spi(create=create)
    assert caught.value.stage == "SPI_OPEN"
    assert "EIO" in str(caught.value)


def test_open_spi_uses_bus0_ce0_1mhz_mode0(monkeypatch, caplog):
    # README 배선 표가 CS=핀24(CE0)라고 못박는다. 버스/속도/모드를 고정한다.
    caplog.set_level(logging.INFO)

    class FakeSpiDev:
        def __init__(self) -> None:
            self.bus = None
            self.device = None
            self.max_speed_hz = 0
            self.mode = -1

        def open(self, bus: int, device: int) -> None:
            self.bus = bus
            self.device = device

    fake = FakeSpiDev()
    monkeypatch.setitem(
        sys.modules, "spidev", types.SimpleNamespace(SpiDev=lambda: fake)
    )
    spi = open_spi()
    assert spi is fake
    assert (fake.bus, fake.device) == (0, 0)
    assert fake.max_speed_hz == 1_000_000
    assert fake.mode == 0


def test_open_lcd_falls_back_from_0x27_to_0x3f(monkeypatch):
    # 백팩은 0x27 아니면 0x3F 다. 한쪽만 보고 포기하면 멀쩡한 LCD 를 놓친다.
    tried: list[int] = []

    class SelectiveLcd:
        def __init__(self, _interface: str, address: int) -> None:
            tried.append(address)
            if address == 0x27:
                raise OSError("missing")

    fake_i2c = types.SimpleNamespace(CharLCD=SelectiveLcd)
    monkeypatch.setitem(sys.modules, "RPLCD", types.SimpleNamespace(i2c=fake_i2c))
    monkeypatch.setitem(sys.modules, "RPLCD.i2c", fake_i2c)
    lcd = open_lcd(0x27)
    assert tried == [0x27, 0x3F]
    assert lcd is not None
