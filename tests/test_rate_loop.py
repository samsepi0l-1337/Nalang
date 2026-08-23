"""갱신 속도는 벽시계로만 증명된다. 상수 검사는 여기서 하지 않는다."""

import threading
import time

from vibration_meter.app import MeasureConfig, measure_loop
from vibration_meter.hardware import MockSensor

INTERVAL_S = 0.1
BUDGET_S = 0.55


class CountingSocket:
    def __init__(self) -> None:
        self.count = 0

    def emit(self, name: str, payload: dict) -> None:
        self.count += 1


def run_loop_for(budget_s: float, config: MeasureConfig) -> int:
    socket = CountingSocket()
    stop = threading.Event()
    worker = threading.Thread(
        target=measure_loop,
        args=(MockSensor(), None, socket, stop, None, config),
        daemon=True,
    )
    worker.start()
    time.sleep(budget_s)
    stop.set()
    worker.join(timeout=2.0)
    return socket.count


def test_loop_emits_faster_than_once_per_second():
    # 예전 1초 창이면 이 예산 안에 많아야 1건이다. 4건 이상이어야 빨라진 것이다.
    count = run_loop_for(BUDGET_S, MeasureConfig.from_interval(INTERVAL_S))
    assert count >= 4, f"{BUDGET_S}초에 {count}건 — 갱신이 빨라지지 않았다"


def test_loop_does_not_free_run_past_the_requested_rate():
    # 창을 안 지키면 SPI 를 쉬지 않고 두드린다. 상한도 함께 잡는다.
    count = run_loop_for(BUDGET_S, MeasureConfig.from_interval(INTERVAL_S))
    assert count <= int(BUDGET_S / INTERVAL_S) + 2
