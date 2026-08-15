import logging
import sys
import types

import pytest

from vibration_meter.errors import HardwareError
from vibration_meter.hardware import open_display, open_lcd, open_sensor, open_spi


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
    assert any("[MOCK] OK" in rec.message for rec in caplog.records)


def test_open_display_logs_fail_and_returns_none(caplog):
    caplog.set_level(logging.ERROR)

    def opener(_address: int):
        raise OSError("No such device")

    lcd = open_display(open_at=opener)
    assert lcd is None
    assert any("[LCD_OPEN] FAIL" in rec.message for rec in caplog.records)


def test_open_lcd_logs_addr_ok_and_fail_with_hint(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    class BoomLcd:
        def __init__(self, *_args, **_kwargs):
            raise OSError("No such device")

    fake_i2c = types.SimpleNamespace(CharLCD=BoomLcd)
    fake_pkg = types.SimpleNamespace(i2c=fake_i2c)
    monkeypatch.setitem(sys.modules, "RPLCD", fake_pkg)
    monkeypatch.setitem(sys.modules, "RPLCD.i2c", fake_i2c)

    with pytest.raises(HardwareError) as caught:
        open_lcd(0x27)
    assert caught.value.stage == "LCD_OPEN"
    messages = [rec.message for rec in caplog.records]
    assert any(msg.startswith("[LCD_ADDR] OK") for msg in messages)
    assert any(msg.startswith("[LCD_ADDR] FAIL") and "| HINT" in msg for msg in messages)


class BoomSpi:
    def xfer2(self, data: list[int]) -> list[int]:
        raise OSError("spi nak")


def test_open_sensor_begin_oserror_is_hardware_error():
    with pytest.raises(HardwareError) as caught:
        open_sensor(mock=False, spi=BoomSpi())
    assert caught.value.stage == "SENSOR_ID"
    assert "spi nak" in str(caught.value)
