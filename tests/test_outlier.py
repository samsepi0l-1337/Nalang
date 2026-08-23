import pytest

from vibration_meter.outlier import (
    BASELINE_S,
    MIN_BASELINE,
    PERSIST_S,
    SHARP_RATIO,
    SOFT_RATIO,
    PersistTracker,
    mean_shift_ratio,
    windows_for,
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


def test_one_second_window_reproduces_the_old_counts():
    # 상수는 초다. 1초 창에서만 개수와 같았다.
    assert windows_for(BASELINE_S, 1.0) == MIN_BASELINE == 10
    assert windows_for(PERSIST_S, 1.0) == 5


@pytest.mark.parametrize("interval_s", [1.0, 0.5, 0.2, 0.1])
def test_window_counts_hold_the_time_rule_at_any_rate(interval_s):
    # "연속 5초"·"기준 10초"가 갱신 주기를 올려도 그대로 5초·10초여야 한다.
    assert windows_for(PERSIST_S, interval_s) * interval_s == pytest.approx(PERSIST_S)
    assert windows_for(BASELINE_S, interval_s) * interval_s == pytest.approx(BASELINE_S)


def test_windows_for_never_returns_zero():
    # 창이 기준보다 길면 반올림이 0을 낸다. 0이면 판정이 늘 켜진다.
    assert windows_for(PERSIST_S, 100.0) == 1


def test_mean_shift_ratio_honours_injected_min_count():
    # 창이 짧아지면 기준선에 필요한 표본 수도 같이 늘어야 한다.
    baseline = [1.0] * 20
    assert mean_shift_ratio(1.0, baseline, min_count=50) is None
    assert mean_shift_ratio(1.0, baseline, min_count=20) == 0.0
