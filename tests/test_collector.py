import time

from vibration_meter.collector import collect_window, read_window
from vibration_meter.hardware import MockSensor
from vibration_meter.metrics import WindowMetrics


class StampSensor:
    """읽힌 시각을 남긴다. 표본이 창에 펴졌는지 보려면 시각이 필요하다."""

    def __init__(self) -> None:
        self.stamps: list[float] = []

    def read_xyz_g(self) -> tuple[float, float, float]:
        self.stamps.append(time.monotonic())
        return (0.0, 0.0, 1.0)


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


def test_collect_window_spreads_reads_across_the_window():
    # ODR 1000 Hz 는 1 ms 마다 새 표본을 낸다. 몰아 읽으면 SPI 가 더 빨라서
    # 같은 표본을 여러 번 집고 창 앞쪽 수십 ms 만 담긴다. 창을 대표하려면
    # 읽기가 창 길이에 펴져 있어야 한다.
    sensor = StampSensor()
    collect_window(sensor, samples=5, duration_s=0.25)
    assert len(sensor.stamps) == 5
    span = sensor.stamps[-1] - sensor.stamps[0]
    assert span >= 0.15, f"표본이 {span:.4f}초 안에 몰렸다 — 창에 펴지지 않았다"


def test_read_window_without_interval_does_not_sleep():
    # read_window 는 페이싱 없는 원시 읽기로도 쓰인다. 기본값이 창을 늘리면 안 된다.
    sensor = StampSensor()
    started = time.monotonic()
    read_window(sensor, count=50)
    assert time.monotonic() - started < 0.05
    assert len(sensor.stamps) == 50
