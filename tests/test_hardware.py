import logging

import pytest

from vibration_meter.errors import HINT_BUZZ, HINT_BUZZ_BUSY, HardwareError
from vibration_meter.hardware import (
    buzz_open_hint,
    open_buzzer,
    open_display,
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
