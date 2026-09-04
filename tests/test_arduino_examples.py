import pytest

from vibration_meter.adxl355 import DEVID_AD, EXPECTED_DEVID_AD, spi_command
from vibration_meter.buzzer_diag import SWEEP_HZ
from vibration_meter.hardware import (
    BUZZER_BCM,
    BUZZER_OCTAVES,
    BUZZER_PIN,
    TONE_HZ,
    tone_range_hz,
)
from vibration_meter.detect import DEFAULT_THRESHOLD_G, THRESHOLDS_G


def test_device_info_matches_pl_adxl355_vendor_id():
    assert EXPECTED_DEVID_AD == 0xAD
    assert spi_command(DEVID_AD, True) == 0x01


def test_buzzer_is_pin32_bcm12_1khz_like_tone():
    # gpiozero 가 GPIO 18(물리 핀 12)에서 PWM 을 거절한다.
    # 하드웨어 PWM 은 핀 32(BCM 12, PWM0)와 핀 33(BCM 13).
    assert BUZZER_PIN == 32
    assert BUZZER_BCM == 12
    assert TONE_HZ == 1000


def test_default_tonalbuzzer_octave_cannot_reach_the_alert_tone():
    # gpiozero 기본값은 A4/1옥타브라 220~880 Hz 다. 1 kHz 경보음이 범위 밖이라
    # 배선이 멀쩡해도 play() 가 거절한다. 이 한 줄이 그 회귀를 막는다.
    low, high = tone_range_hz(octaves=1)
    assert (low, high) == (220, 880)
    assert TONE_HZ > high


@pytest.mark.parametrize("hz", (TONE_HZ, *SWEEP_HZ))
def test_configured_octave_covers_every_tone_we_play(hz):
    low, high = tone_range_hz()
    assert low <= hz <= high, f"{hz} Hz 가 {low}~{high} Hz 밖이다"


def test_buzzer_octaves_is_pinned():
    assert BUZZER_OCTAVES == 2


def test_alert_thresholds_match_readme_rule():
    assert THRESHOLDS_G == (0.7, 8.0)
    assert DEFAULT_THRESHOLD_G == 0.7
