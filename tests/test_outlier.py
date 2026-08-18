from vibration_meter.outlier import (
    MIN_BASELINE,
    PERSIST_S,
    SHARP_RATIO,
    SOFT_RATIO,
    PersistTracker,
    mean_shift_ratio,
)


def test_mean_shift_ratio_needs_baseline():
    assert mean_shift_ratio(10.0, [0.1] * (MIN_BASELINE - 1)) is None


def test_mean_shift_ratio_against_average():
    baseline = [1.0] * MIN_BASELINE
    assert mean_shift_ratio(1.0, baseline) == 0.0
    assert abs(mean_shift_ratio(1.05, baseline) - SOFT_RATIO) < 1e-9
    assert abs(mean_shift_ratio(1.10, baseline) - SHARP_RATIO) < 1e-9


def test_persist_five_soft_shifts():
    tracker = PersistTracker(needed=PERSIST_S)
    for _ in range(PERSIST_S - 1):
        assert tracker.update(SOFT_RATIO) is False
        assert tracker.changed is False
    assert tracker.update(SOFT_RATIO) is True
    assert tracker.changed is True
    assert tracker.update(SOFT_RATIO) is True
    assert tracker.changed is False
    assert tracker.update(0.0) is False
    assert tracker.changed is True


def test_sharp_shift_alerts_immediately():
    tracker = PersistTracker(needed=PERSIST_S)
    assert tracker.update(0.04) is False
    assert tracker.update(SHARP_RATIO) is True
    assert tracker.changed is True
