import pytest

from vibration_meter.detect import (
    DEFAULT_THRESHOLD_G,
    THRESHOLDS_G,
    DetectMode,
    mode,
    parse_threshold,
)


def test_thresholds_are_absolute_g():
    assert THRESHOLDS_G == (0.7, 8.0)
    assert DEFAULT_THRESHOLD_G == 0.7


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.7, 0.7),
        ("0.7", 0.7),
        (8, 8.0),
        ("8", 8.0),
        (8.0, 8.0),
    ],
)
def test_parse_threshold_accepts_canonical_forms(value, expected):
    assert parse_threshold(value) == expected
    assert parse_threshold(value) in THRESHOLDS_G


@pytest.mark.parametrize("value", [2, 1, "foo", None])
def test_parse_threshold_rejects_unknown(value):
    with pytest.raises(ValueError):
        parse_threshold(value)


def test_detect_mode_defaults_to_0_7g():
    detect = DetectMode()
    assert detect.threshold_g == DEFAULT_THRESHOLD_G == 0.7


def test_set_threshold_parses_stores_and_returns_canonical():
    detect = DetectMode()
    assert detect.set_threshold(8) == 8.0
    assert detect.threshold_g == 8.0
    assert detect.set_threshold("0.7") == 0.7
    assert detect.threshold_g == 0.7


def test_set_threshold_rejects_unknown():
    detect = DetectMode()
    with pytest.raises(ValueError):
        detect.set_threshold(2)
    assert detect.threshold_g == DEFAULT_THRESHOLD_G


def test_is_alert_at_default_0_7g():
    detect = DetectMode()
    assert detect.is_alert(0.699) is False
    assert detect.is_alert(0.7) is True
    assert detect.is_alert(8) is True


def test_is_alert_at_8g():
    detect = DetectMode()
    detect.set_threshold(8)
    assert detect.is_alert(0.699) is False
    assert detect.is_alert(0.7) is False
    assert detect.is_alert(8) is True


def test_process_wide_mode_defaults_to_0_7g():
    assert mode.threshold_g == DEFAULT_THRESHOLD_G
    assert isinstance(mode, DetectMode)
