import time
from collections.abc import Callable
from typing import Protocol

from vibration_meter.metrics import WindowMetrics, window_metrics

OverrunHandler = Callable[[float], None]


class XyzSensor(Protocol):
    def read_xyz_g(self) -> tuple[float, float, float]: ...


def read_window(
    sensor: XyzSensor,
    count: int,
    interval_s: float = 0.0,
    started: float | None = None,
) -> WindowMetrics:
    """표본 count 개를 읽는다. interval_s 를 주면 그 간격으로 고르게 벌린다.

    ODR 1000 Hz 는 1 ms 마다 새 표본을 낸다. 간격 없이 몰아 읽으면 SPI 쪽이
    훨씬 빨라서 같은 표본을 여러 번 집고, 창 전체가 아니라 앞쪽 수십 ms 만
    담긴다. RMS 가 창을 대표하려면 읽기를 창 길이에 펴야 한다.
    """
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    base = time.monotonic() if started is None else started
    for index in range(count):
        if interval_s > 0:
            wait = base + index * interval_s - time.monotonic()
            if wait > 0:
                time.sleep(wait)
        x, y, z = sensor.read_xyz_g()
        xs.append(x)
        ys.append(y)
        zs.append(z)
    return window_metrics(xs, ys, zs)


def collect_window(
    sensor: XyzSensor,
    samples: int = 1000,
    duration_s: float = 1.0,
    on_overrun: OverrunHandler | None = None,
) -> WindowMetrics:
    """창 하나를 ODR 간격에 맞춰 읽고, 남는 시간만큼 재워 갱신 주기를 맞춘다.

    읽기가 창보다 오래 걸리면 잴 시간이 없다. 조용히 느려지는 대신
    on_overrun 으로 초과분을 알린다.
    """
    started = time.monotonic()
    interval = duration_s / samples if samples else 0.0
    metrics = read_window(sensor, samples, interval_s=interval, started=started)
    remaining = duration_s - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    elif on_overrun is not None:
        on_overrun(-remaining)
    return metrics
