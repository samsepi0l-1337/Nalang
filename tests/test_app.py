import logging

import pytest

from vibration_meter.app import (
    DEFAULT_INTERVAL_S,
    HISTORY_S,
    MIN_INTERVAL_S,
    MeasureConfig,
    RateWatch,
    main,
    publish_reading,
)
from vibration_meter.adxl355 import ODR_HZ
from vibration_meter.display import UpdateThrottle
from vibration_meter.metrics import RmsHistory
from vibration_meter.outlier import BASELINE_S, MIN_BASELINE, PERSIST_S, PersistTracker


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


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def test_default_interval_is_faster_than_one_second():
    assert MIN_INTERVAL_S <= DEFAULT_INTERVAL_S < 1.0


def test_one_second_config_matches_the_old_behaviour():
    # 회귀 기준선. 예전 1초 창의 값이 그대로 나와야 한다.
    config = MeasureConfig.from_interval(1.0)
    assert config.samples == 1000
    assert config.baseline_windows == MIN_BASELINE
    assert config.persist_windows == PERSIST_S
    assert config.history_len == HISTORY_S


@pytest.mark.parametrize("interval_s", [1.0, 0.5, DEFAULT_INTERVAL_S, MIN_INTERVAL_S])
def test_config_keeps_seconds_based_rules_at_every_rate(interval_s):
    config = MeasureConfig.from_interval(interval_s)
    # 표본은 ODR 이 그 창에서 실제로 내는 개수여야 한다.
    assert config.samples == pytest.approx(ODR_HZ * interval_s, abs=1)
    # 판정 기준과 그래프 길이는 초로 고정이다.
    assert config.persist_windows * interval_s == pytest.approx(PERSIST_S)
    assert config.baseline_windows * interval_s == pytest.approx(BASELINE_S)
    assert config.history_len * interval_s == pytest.approx(HISTORY_S)


def test_interval_below_floor_exits_two():
    # 창이 너무 짧으면 20 Hz 한 주기도 안 들어가 RMS 가 요동친다.
    with pytest.raises(SystemExit) as caught:
        main(["--interval", str(MIN_INTERVAL_S / 2)])
    assert caught.value.code == 2


def test_throttle_skips_lcd_but_never_stops_the_web():
    clock = FakeClock()
    throttle = UpdateThrottle(min_interval_s=0.5, now=clock)
    lcd = FakeLcd()
    socket = FakeSocket()
    for _ in range(3):
        publish_reading(
            SequenceSensor(),
            lcd,
            RmsHistory(),
            socket,
            samples=3,
            duration_s=0.0,
            lcd_throttle=throttle,
        )
    assert lcd.updates == 1
    assert len(socket.events) == 3


def test_alert_transition_bypasses_the_lcd_throttle():
    clock = FakeClock()
    throttle = UpdateThrottle(min_interval_s=60.0, now=clock)
    lcd = FakeLcd()
    history = RmsHistory()
    for i in range(MIN_BASELINE):
        history.push(float(i), 0.01)
    # 첫 창이 스로틀 시계를 찍고, 두 번째 창은 이상치 전환으로 뚫어야 한다.
    publish_reading(
        SequenceSensor(), lcd, RmsHistory(), FakeSocket(), samples=3, duration_s=0.0,
        lcd_throttle=throttle,
    )
    publish_reading(
        HighAcSensor(), lcd, history, FakeSocket(), samples=3, duration_s=0.0,
        tracker=PersistTracker(), lcd_throttle=throttle,
    )
    assert lcd.updates == 2
    assert lcd.line2.startswith("OUTLIER")


def test_rate_watch_logs_once_on_entry_and_once_on_recovery(caplog):
    caplog.set_level(logging.INFO)
    watch = RateWatch(0.2)
    watch.on_overrun(0.05)
    watch.settle()
    watch.on_overrun(0.06)
    watch.settle()
    watch.settle()
    fails = [r for r in caplog.records if "[RATE] FAIL" in r.message]
    recovered = [r for r in caplog.records if "[RATE] OK" in r.message]
    assert len(fails) == 1
    assert len(recovered) == 1
