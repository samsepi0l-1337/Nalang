import pytest

from vibration_meter.detect import DEFAULT_THRESHOLD_G, DetectMode, parse_threshold


def test_parse_threshold_accepts_0_7_and_8():
    assert parse_threshold(0.7) == 0.7
    assert parse_threshold(8) == 8.0
    assert parse_threshold("0.7") == 0.7


def test_parse_threshold_rejects_other_values():
    with pytest.raises(ValueError):
        parse_threshold(2)
    with pytest.raises(ValueError):
        parse_threshold("nope")


def test_detect_mode_defaults_to_0_7():
    assert DEFAULT_THRESHOLD_G == 0.7
    assert DetectMode().threshold_g == 0.7


def test_is_alert_trips_at_or_above_threshold():
    low = DetectMode(0.7)
    assert low.is_alert(0.69) is False
    assert low.is_alert(0.7) is True
    high = DetectMode(8.0)
    assert high.is_alert(4.0) is False
    assert high.is_alert(8.0) is True
