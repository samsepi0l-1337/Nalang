import logging

from vibration_meter.app import publish_reading
from vibration_meter.metrics import RmsHistory
from vibration_meter.outlier import MIN_BASELINE, PersistTracker


class SequenceSensor:
    def __init__(self, sample=(0.0, 0.4, 1.0)) -> None:
        self.sample = sample

    def read_xyz_g(self):
        return self.sample


class BoomSensor:
    def read_xyz_g(self):
        raise RuntimeError("bus nak")


class HighAcSensor:
    def __init__(self) -> None:
        self._n = 0

    def read_xyz_g(self):
        self._n += 1
        return (0.0, 4.0 if self._n % 2 else -4.0, 1.0)


class FakeBuzzer:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.states: list[bool] = []

    def set_alert(self, on: bool) -> None:
        if self.fail:
            raise OSError("pwm timeout")
        self.states.append(on)


class FakeSocket:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def emit(self, name: str, payload: dict) -> None:
        self.events.append((name, payload))


class FakeLcd:
    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.updates = 0
        self.line2 = ""

    def update(self, line1: str, line2: str) -> None:
        if self.fail:
            raise OSError("i2c timeout")
        self.updates += 1
        self.line2 = line2


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


def test_publish_reading_shows_outlier_on_sharp_jump(caplog):
    caplog.set_level(logging.INFO)
    lcd = FakeLcd()
    buzzer = FakeBuzzer()
    history = RmsHistory()
    for i in range(MIN_BASELINE):
        history.push(float(i), 0.01)
    ok = publish_reading(
        HighAcSensor(),
        lcd,
        history,
        FakeSocket(),
        samples=3,
        duration_s=0.0,
        buzzer=buzzer,
        tracker=PersistTracker(),
    )
    assert ok is True
    assert lcd.line2.startswith("OUTLIER")
    assert buzzer.states[-1] is True
    assert any("[ALERT] OK on" in rec.message for rec in caplog.records)


def test_publish_reading_logs_buzz_write_fail_and_keeps_web(caplog):
    caplog.set_level(logging.ERROR)
    socket = FakeSocket()
    ok = publish_reading(
        SequenceSensor(),
        None,
        RmsHistory(),
        socket,
        samples=3,
        duration_s=0.0,
        buzzer=FakeBuzzer(fail=True),
        tracker=PersistTracker(),
    )
    assert ok is True
    assert socket.events
    assert any("[BUZZ_WRITE] FAIL" in rec.message for rec in caplog.records)
