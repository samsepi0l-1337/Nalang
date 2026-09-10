import pytest

from vibration_meter.detect import (
    DEFAULT_THRESHOLD_G,
    DEFAULT_VISIBLE_G,
    PRODUCTS,
    THRESHOLDS_G,
    DetectMode,
    format_thresholds,
    mode,
    parse_threshold,
    product_name,
    products_payload,
)


def test_thresholds_are_absolute_g():
    assert THRESHOLDS_G == (0.1, 0.7, 3.0, 8.0, 10.0)
    assert DEFAULT_THRESHOLD_G == 0.7
    assert DEFAULT_VISIBLE_G == (0.7, 8.0)
    assert PRODUCTS == (
        (0.1, "제품 1"),
        (0.7, "제품 2"),
        (3.0, "제품 3"),
        (8.0, "제품 4"),
        (10.0, "제품 5"),
    )


def test_product_names_follow_catalog_order():
    assert [product_name(g) for g in THRESHOLDS_G] == [
        "제품 1",
        "제품 2",
        "제품 3",
        "제품 4",
        "제품 5",
    ]
    assert products_payload() == [
        {"name": "제품 1", "threshold_g": 0.1},
        {"name": "제품 2", "threshold_g": 0.7},
        {"name": "제품 3", "threshold_g": 3.0},
        {"name": "제품 4", "threshold_g": 8.0},
        {"name": "제품 5", "threshold_g": 10.0},
    ]


def test_format_thresholds_lists_catalog():
    assert format_thresholds() == "0.1, 0.7, 3, 8, 10"
    assert format_thresholds(suffix="g") == "0.1g, 0.7g, 3g, 8g, 10g"


@pytest.mark.parametrize(
    "value, expected",
    [
        (0.1, 0.1),
        ("0.1", 0.1),
        (0.7, 0.7),
        ("0.7", 0.7),
        (3, 3.0),
        ("3", 3.0),
        (8, 8.0),
        ("8", 8.0),
        (8.0, 8.0),
        (10, 10.0),
        ("10", 10.0),
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
    assert detect.visible_g == [0.7, 8.0]


def test_set_threshold_parses_stores_and_returns_canonical():
    detect = DetectMode()
    assert detect.set_threshold(8) == 8.0
    assert detect.threshold_g == 8.0
    assert detect.set_threshold("0.7") == 0.7
    assert detect.threshold_g == 0.7


def test_set_threshold_adds_missing_product_to_visible():
    detect = DetectMode()
    detect.set_threshold(0.1)
    assert detect.threshold_g == 0.1
    assert detect.visible_g == [0.1, 0.7, 8.0]


def test_set_threshold_rejects_unknown():
    detect = DetectMode()
    with pytest.raises(ValueError):
        detect.set_threshold(2)
    assert detect.threshold_g == DEFAULT_THRESHOLD_G


def test_add_visible_inserts_in_catalog_order():
    detect = DetectMode()
    assert detect.add_visible(10) == [0.7, 8.0, 10.0]
    assert detect.add_visible("0.1") == [0.1, 0.7, 8.0, 10.0]
    assert detect.add_visible(3) == [0.1, 0.7, 3.0, 8.0, 10.0]


def test_add_visible_rejects_already_visible():
    detect = DetectMode()
    with pytest.raises(ValueError, match="already visible"):
        detect.add_visible(0.7)


def test_remove_visible_drops_product():
    detect = DetectMode()
    assert detect.remove_visible(8) == [0.7]
    assert detect.threshold_g == 0.7


def test_remove_visible_switches_selected_to_remaining():
    detect = DetectMode()
    detect.set_threshold(0.7)
    assert detect.remove_visible(0.7) == [8.0]
    assert detect.threshold_g == 8.0


def test_remove_visible_rejects_last_product():
    detect = DetectMode()
    detect.remove_visible(8)
    with pytest.raises(ValueError, match="cannot remove last product"):
        detect.remove_visible(0.7)
    assert detect.visible_g == [0.7]


def test_remove_visible_rejects_not_visible():
    detect = DetectMode()
    with pytest.raises(ValueError, match="not visible"):
        detect.remove_visible(0.1)


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
    assert mode.visible_g == [0.7, 8.0]
