from vibration_meter.collector import collect_window, read_window
from vibration_meter.hardware import MockSensor
from vibration_meter.metrics import WindowMetrics


class SequenceSensor:
    def __init__(self, samples: list[tuple[float, float, float]]) -> None:
        self._samples = samples
        self.reads = 0

    def read_xyz_g(self) -> tuple[float, float, float]:
        sample = self._samples[self.reads]
        self.reads += 1
        return sample


def test_read_window_uses_all_samples():
    samples = [(0.0, 0.0, 1.0), (0.0, 0.4, 1.0), (0.0, -0.4, 1.0)]
    result = read_window(SequenceSensor(samples), count=3)
    assert isinstance(result, WindowMetrics)
    assert result.axis == "Y"
    assert result.peak_g > 0.3


def test_collect_window_can_skip_wait():
    samples = [(0.0, 0.0, 1.0)] * 4
    result = collect_window(SequenceSensor(samples), samples=4, duration_s=0.0)
    assert result.axis in {"X", "Y", "Z"}


def test_mock_sensor_selects_ac_axis():
    result = read_window(MockSensor(), count=200)
    assert result.axis == "Y"


def test_overrun_is_reported_not_swallowed():
    # 창보다 읽기가 오래 걸리면 갱신 주기가 조용히 늘어난다. 알려야 한다.
    seen: list[float] = []
    collect_window(
        SequenceSensor([(0.0, 0.0, 1.0)] * 4),
        samples=4,
        duration_s=0.0,
        on_overrun=seen.append,
    )
    assert len(seen) == 1
    assert seen[0] >= 0.0


def test_no_overrun_report_when_window_has_slack():
    seen: list[float] = []
    collect_window(
        SequenceSensor([(0.0, 0.0, 1.0)] * 2),
        samples=2,
        duration_s=0.05,
        on_overrun=seen.append,
    )
    assert seen == []
