import pytest

from vibration_meter.detect import (
    DEFAULT_THRESHOLD_G,
    THRESHOLDS_G,
    DetectMode,
    parse_threshold,
)


def test_parse_threshold_accepts_allowed_values():
    assert parse_threshold(0.7) == 0.7
    assert parse_threshold(8) == 8.0
    assert parse_threshold(8.0) == 8.0
    assert parse_threshold("0.7") == 0.7


def test_parse_threshold_rejects_invalid_values():
    with pytest.raises(ValueError, match="not one of"):
        parse_threshold(2)
    with pytest.raises(ValueError, match="not a number"):
        parse_threshold("nope")
    with pytest.raises(ValueError, match="not a number"):
        parse_threshold(None)


def test_set_threshold_and_is_alert():
    detect = DetectMode()
    assert detect.threshold_g == DEFAULT_THRESHOLD_G
    assert detect.is_alert(0.69) is False
    assert detect.is_alert(0.7) is True
    assert detect.set_threshold(8.0) == 8.0
    assert detect.threshold_g == 8.0
    assert detect.is_alert(7.99) is False
    assert detect.is_alert(8.0) is True
    detect.set_threshold(0.7)
    assert detect.threshold_g == 0.7


def test_thresholds_are_the_two_units():
    assert THRESHOLDS_G == (0.7, 8.0)
