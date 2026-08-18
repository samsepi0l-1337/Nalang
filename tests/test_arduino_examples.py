from vibration_meter.adxl355 import DEVID_AD, EXPECTED_DEVID_AD, spi_command
from vibration_meter.hardware import BUZZER_BCM, TONE_HZ
from vibration_meter.outlier import PERSIST_S, SHARP_RATIO, SOFT_RATIO


def test_device_info_matches_pl_adxl355_vendor_id():
    assert EXPECTED_DEVID_AD == 0xAD
    assert spi_command(DEVID_AD, True) == 0x01


def test_buzzer_is_bcm18_1khz_like_tone():
    assert BUZZER_BCM == 18
    assert TONE_HZ == 1000


def test_alert_thresholds_match_readme_rule():
    assert SOFT_RATIO == 0.05
    assert SHARP_RATIO == 0.10
    assert PERSIST_S == 5
