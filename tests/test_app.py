import logging

from vibration_meter.app import publish_reading
from vibration_meter.metrics import RmsHistory


class SequenceSensor:
    def __init__(self, sample=(0.0, 0.4, 1.0)) -> None:
        self.sample = sample

    def read_xyz_g(self):
        return self.sample


class BoomSensor:
    def read_xyz_g(self):
        raise RuntimeError("bus nak")


class FakeSocket:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, name: str, payload: dict) -> None:
        self.events.append((name, payload))


class FakeLcd:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.updates = 0

    def update(self, line1: str, line2: str) -> None:
        if self.fail:
            raise OSError("i2c timeout")
        self.updates += 1


def test_publish_reading_logs_sample_ok(caplog):
    caplog.set_level(logging.INFO)
    socket = FakeSocket()
    history = RmsHistory()
    ok = publish_reading(
        SequenceSensor(),
        None,
        history,
        socket,
        samples=3,
        duration_s=0.0,
    )
    assert ok is True
    assert socket.events[0][0] == "reading"
    assert any("[SAMPLE] OK" in rec.message for rec in caplog.records)


def test_publish_reading_logs_sample_fail(caplog):
    caplog.set_level(logging.ERROR)
    ok = publish_reading(
        BoomSensor(),
        None,
        RmsHistory(),
        FakeSocket(),
        samples=1,
        duration_s=0.0,
    )
    assert ok is False
    assert any("[SAMPLE] FAIL" in rec.message for rec in caplog.records)


def test_publish_reading_logs_lcd_write_fail_and_keeps_web(caplog):
    caplog.set_level(logging.ERROR)
    socket = FakeSocket()
    ok = publish_reading(
        SequenceSensor(),
        FakeLcd(fail=True),
        RmsHistory(),
        socket,
        samples=3,
        duration_s=0.0,
    )
    assert ok is True
    assert socket.events
    assert any("[LCD_WRITE] FAIL" in rec.message for rec in caplog.records)
