from vibration_meter.errors import HINT_LCD, HardwareError, format_fail, hint_for_devid


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
    assert "핀21" in hint
    assert "핀24" in hint


def test_devid_ff_points_to_power():
    hint = hint_for_devid(0xFF)
    assert "핀1" in hint
    assert "핀25" in hint
    assert "5V" in hint


def test_devid_other_points_to_mosi_miso_cs():
    hint = hint_for_devid(0x12)
    assert "핀19" in hint
    assert "핀21" in hint
    assert "핀24" in hint


def test_lcd_hint_pins_and_forbids_5v():
    assert "핀3" in HINT_LCD
    assert "핀5" in HINT_LCD
    assert "핀6" in HINT_LCD
    assert "핀17" in HINT_LCD
    assert "5V" in HINT_LCD
