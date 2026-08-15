import time
from typing import Protocol

from vibration_meter.metrics import WindowMetrics, window_metrics


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


def collect_second(
    sensor: XyzSensor, samples: int = 1000, duration_s: float = 1.0
) -> WindowMetrics:
    started = time.monotonic()
    xs: list[float] = []
    ys: list[float] = []
    zs: list[float] = []
    interval = duration_s / samples if samples else 0.0
    for index in range(samples):
        wait = started + index * interval - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        x, y, z = sensor.read_xyz_g()
        xs.append(x)
        ys.append(y)
        zs.append(z)
    remaining = duration_s - (time.monotonic() - started)
    if remaining > 0:
        time.sleep(remaining)
    return window_metrics(xs, ys, zs)
