from vibration_meter.collector import collect_second, read_window
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


def test_collect_second_can_skip_wait():
    samples = [(0.0, 0.0, 1.0)] * 4
    result = collect_second(SequenceSensor(samples), samples=4, duration_s=0.0)
    assert result.axis in {"X", "Y", "Z"}


def test_mock_sensor_selects_ac_axis():
    result = read_window(MockSensor(), count=200)
    assert result.axis == "Y"
