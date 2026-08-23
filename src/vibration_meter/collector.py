import time
from collections.abc import Callable
from typing import Protocol

from vibration_meter.metrics import WindowMetrics, window_metrics

OverrunHandler = Callable[[float], None]


class XyzSensor(Protocol):
    def read_xyz_g(self) -> tuple[float, float, float]: ...


def read_window(sensor: XyzSensor, count: int) -> WindowMetrics:
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    for _ in range(count):
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
    """창 하나를 읽고, 남는 시간만큼 재워 갱신 주기를 맞춘다.

    읽기가 창보다 오래 걸리면 잴 시간이 없다. 조용히 느려지는 대신
    on_overrun 으로 초과분을 알린다.
    """
    started = time.monotonic()
    metrics = read_window(sensor, samples)
    remaining = duration_s - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    elif on_overrun is not None:
        on_overrun(-remaining)
    return metrics
