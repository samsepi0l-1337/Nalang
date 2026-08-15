import logging
import socket

import pytest

from vibration_meter.app import check_web_bind, main, publish_reading
from vibration_meter.errors import HardwareError
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
    assert any("| HINT" in rec.message for rec in caplog.records)


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


def test_publish_reading_logs_lcd_write_ok(caplog):
    caplog.set_level(logging.INFO)
    lcd = FakeLcd()
    ok = publish_reading(
        SequenceSensor(),
        lcd,
        RmsHistory(),
        FakeSocket(),
        samples=3,
        duration_s=0.0,
    )
    assert ok is True
    assert lcd.updates == 1
    assert any("[LCD_WRITE] OK" in rec.message for rec in caplog.records)


def test_check_web_bind_fails_when_port_in_use():
    occupied = socket.socket()
    occupied.bind(("127.0.0.1", 0))
    occupied.listen(1)
    port = occupied.getsockname()[1]
    try:
        with pytest.raises(HardwareError) as caught:
            check_web_bind("127.0.0.1", port)
        assert caught.value.stage == "WEB_BIND"
        assert "HINT" in str(caught.value)
    finally:
        occupied.close()


def test_main_mock_logs_lcd_open_ok(monkeypatch, caplog):
    caplog.set_level(logging.INFO)

    class FakeSocketIO:
        def run(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr("vibration_meter.app.check_web_bind", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "vibration_meter.app.create_app",
        lambda: (object(), FakeSocketIO()),
    )
    main(["--mock", "--port", "59999"])
    messages = [rec.message for rec in caplog.records]
    assert any("[MOCK] OK" in msg for msg in messages)
    assert any("[LCD_OPEN] OK" in msg for msg in messages)
    assert any("[WEB_BIND] OK" in msg for msg in messages)
    assert any("[BOOT] OK" in msg for msg in messages)
    assert any("[LOOP] OK" in msg for msg in messages)


def test_main_sensor_failure_exits_2(monkeypatch):
    monkeypatch.setattr(
        "vibration_meter.app.open_sensor",
        lambda *_a, **_k: (_ for _ in ()).throw(
            HardwareError("SENSOR_ID", "bad id", "hint")
        ),
    )
    with pytest.raises(SystemExit) as caught:
        main([])
    assert caught.value.code == 2


def test_main_web_bind_failure_exits_1(monkeypatch):
    class FakeSocketIO:
        def run(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr("vibration_meter.app.measure_loop", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "vibration_meter.app.check_web_bind",
        lambda *_a, **_k: (_ for _ in ()).throw(
            HardwareError("WEB_BIND", "in use", "hint")
        ),
    )
    monkeypatch.setattr(
        "vibration_meter.app.create_app",
        lambda: (object(), FakeSocketIO()),
    )
    with pytest.raises(SystemExit) as caught:
        main(["--mock"])
    assert caught.value.code == 1


def test_main_lcd_open_fail_does_not_exit(monkeypatch):
    class FakeSocketIO:
        def run(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr(
        "vibration_meter.app.open_sensor",
        lambda *_a, **_k: SequenceSensor(),
    )
    monkeypatch.setattr("vibration_meter.app.open_display", lambda: None)
    monkeypatch.setattr("vibration_meter.app.measure_loop", lambda *_a, **_k: None)
    monkeypatch.setattr("vibration_meter.app.check_web_bind", lambda *_a, **_k: None)
    monkeypatch.setattr(
        "vibration_meter.app.create_app",
        lambda: (object(), FakeSocketIO()),
    )
    main(["--port", "59999"])


def test_publish_reading_history_caps_at_sixty():
    history = RmsHistory(maxlen=60)
    socket = FakeSocket()
    for _ in range(61):
        publish_reading(
            SequenceSensor(),
            None,
            history,
            socket,
            samples=1,
            duration_s=0.0,
        )
    assert len(history.as_list()) == 60
    assert len(socket.events) == 61
    payload = socket.events[-1][1]
    assert set(payload) == {"rms_g", "peak_g", "axis", "history"}
    assert "samples" not in payload
