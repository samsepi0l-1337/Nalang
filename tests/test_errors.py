from vibration_meter.errors import (
    HINT_WEB_BIND,
    HardwareError,
    format_fail,
    hint_for_devid,
)


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
    assert "beginSPI" in hint
    assert "I2C" in hint


def test_devid_ff_points_to_power():
    hint = hint_for_devid(0xFF)
    assert "VCC" in hint or "3.3" in hint


def test_web_bind_hint_says_not_wiring():
    # 포트 점유는 배선 문제로 오독되기 쉽다. 힌트가 그걸 먼저 끊어야 한다.
    assert "배선" in HINT_WEB_BIND
    assert "5000" in HINT_WEB_BIND


def test_devid_other_points_to_mosi_miso_cs():
    hint = hint_for_devid(0x12)
    assert "MOSI" in hint and "MISO" in hint
    assert "CE0" in hint or "핀24" in hint
