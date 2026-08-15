import re

from vibration_meter.errors import HINT_LCD, HardwareError, format_fail, hint_for_devid


def _has_pin(text: str, pin: str) -> bool:
    return re.search(rf"핀{pin}(?!\d)", text) is not None


def test_format_fail_has_stage_and_hint():
    text = format_fail("SENSOR_ID", "DEVID_AD=0x00", "check MISO")
    assert text.startswith("[SENSOR_ID] FAIL ")
    assert "DEVID_AD=0x00" in text
    assert "HINT check MISO" in text


def test_hardware_error_exposes_stage():
    err = HardwareError("SPI_OPEN", "missing device", "enable SPI")
    assert err.stage == "SPI_OPEN"
    assert "SPI_OPEN" in str(err)
    assert "HINT enable SPI" in str(err)


def test_devid_zero_points_to_miso_or_cs():
    hint = hint_for_devid(0x00)
    assert _has_pin(hint, "21")
    assert _has_pin(hint, "24")


def test_devid_ff_points_to_power():
    hint = hint_for_devid(0xFF)
    assert _has_pin(hint, "1")
    assert _has_pin(hint, "25")
    assert not _has_pin(hint, "11")
    assert "5V" in hint


def test_devid_other_points_to_mosi_miso_cs():
    hint = hint_for_devid(0x12)
    assert _has_pin(hint, "19")
    assert _has_pin(hint, "21")
    assert _has_pin(hint, "24")


def test_lcd_hint_pins_and_forbids_5v():
    assert _has_pin(HINT_LCD, "3")
    assert _has_pin(HINT_LCD, "5")
    assert _has_pin(HINT_LCD, "6")
    assert _has_pin(HINT_LCD, "17")
    assert "5V" in HINT_LCD
