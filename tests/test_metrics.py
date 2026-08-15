import numpy as np

from vibration_meter.metrics import RmsHistory, window_metrics


def test_window_metrics_drops_dc_and_picks_ac_axis():
    n = 1000
    t = np.arange(n) / 1000.0
    x = np.zeros(n)
    y = 0.2 * np.sin(2 * np.pi * 50 * t)
    z = np.ones(n)
    result = window_metrics(x, y, z)
    assert result.axis == "Y"
    assert abs(result.rms_g - (0.2 / np.sqrt(2))) < 0.01
    assert abs(result.peak_g - 0.2) < 0.01


def test_window_metrics_tie_prefers_x():
    n = 100
    ones = np.ones(n)
    result = window_metrics(ones, ones, ones)
    assert result.axis == "X"
    assert result.rms_g == 0.0
    assert result.peak_g == 0.0


def test_rms_history_keeps_last_sixty():
    history = RmsHistory(maxlen=60)
    for i in range(65):
        history.push(float(i), 0.1 * i)
    points = history.as_list()
    assert len(points) == 60
    assert points[0]["t"] == 5.0
    assert points[-1]["t"] == 64.0
    assert points[-1]["rms_g"] == 6.4
