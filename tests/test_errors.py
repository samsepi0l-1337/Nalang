from vibration_meter.errors import HardwareError, format_fail, hint_for_devid


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
    assert "MISO" in hint
    assert "CS" in hint


def test_devid_ff_points_to_power():
    hint = hint_for_devid(0xFF)
    assert "VCC" in hint or "3.3" in hint
