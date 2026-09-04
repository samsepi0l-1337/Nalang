import argparse
import logging
import socket
import threading
import time
from dataclasses import dataclass

from vibration_meter.adxl355 import ODR_HZ
from vibration_meter.collector import OverrunHandler, collect_window
from vibration_meter.detect import DEFAULT_THRESHOLD_G, DetectMode, mode
from vibration_meter.display import UpdateThrottle, show
from vibration_meter.errors import (
    HINT_BUZZ_WRITE,
    HINT_LCD_WRITE,
    HINT_RATE,
    HINT_SAMPLE,
    HINT_WEB_BIND,
    HardwareError,
    format_fail,
    format_ok,
)
from vibration_meter.hardware import open_buzzer, open_display, open_sensor
from vibration_meter.logutil import get_logger, setup_logging
from vibration_meter.metrics import RmsHistory
from vibration_meter.outlier import BASELINE_S, PERSIST_S, windows_for
from vibration_meter.webapp import create_app, reading_payload

HINT_DETECT = "0.7g 또는 8g 를 --detect 로 고른다"

# 창 하나가 곧 갱신 주기다. 0.2초면 초당 5회.
DEFAULT_INTERVAL_S = 0.2
# 20 Hz 진동이 창 안에 두 주기는 들어가야 RMS 가 흔들리지 않는다.
MIN_INTERVAL_S = 0.1
# 그래프가 담는 시간. 주기가 바뀌어도 이 길이는 유지한다.
HISTORY_S = 60


@dataclass(frozen=True)
class MeasureConfig:
    """갱신 주기 하나에서 파생되는 값들. 초 기준을 창 개수로 환산해 둔다."""

    interval_s: float
    samples: int
    baseline_windows: int
    persist_windows: int
    history_len: int

    @classmethod
    def from_interval(cls, interval_s: float) -> "MeasureConfig":
        return cls(
            interval_s=interval_s,
            samples=max(1, round(ODR_HZ * interval_s)),
            baseline_windows=windows_for(BASELINE_S, interval_s),
            persist_windows=windows_for(PERSIST_S, interval_s),
            history_len=windows_for(HISTORY_S, interval_s),
        )


class AlertState:
    """경보 on/off 가 바뀌었는지 기억한다. LCD 강제 갱신과 [ALERT] 로그에 쓴다."""

    def __init__(self) -> None:
        self.on = False
        self.changed = False

    def update(self, on: bool) -> bool:
        self.changed = on != self.on
        self.on = on
        return on


class RateWatch:
    """창이 밀리는지 본다. 상태가 바뀔 때만 남긴다 — 매 창 남기면 로그가 폭주한다."""

    def __init__(self, interval_s: float) -> None:
        self._interval_s = interval_s
        self._over = False
        self._hit = False

    def on_overrun(self, over_s: float) -> None:
        self._hit = True
        if self._over:
            return
        self._over = True
        get_logger().error(
            format_fail("RATE", f"창이 {over_s:.3f}초 밀린다", HINT_RATE)
        )

    def settle(self) -> None:
        if self._over and not self._hit:
            self._over = False
            get_logger().info(format_ok("RATE", f"창 {self._interval_s:.2f}초 회복"))
        self._hit = False


def publish_reading(
    sensor,
    lcd,
    history: RmsHistory,
    socketio,
    samples: int = 1000,
    duration_s: float = 1.0,
    buzzer=None,
    detect: DetectMode | None = None,
    alert_state: AlertState | None = None,
    *,
    lcd_throttle: UpdateThrottle | None = None,
    on_overrun: OverrunHandler | None = None,
) -> bool:
    log = get_logger()
    detector = mode if detect is None else detect
    try:
        metrics = collect_window(
            sensor, samples=samples, duration_s=duration_s, on_overrun=on_overrun
        )
    except Exception as exc:
        log.error(format_fail("SAMPLE", str(exc), HINT_SAMPLE), exc_info=True)
        return False
    history.push(time.time(), metrics.rms_g)
    alert = detector.is_alert(metrics.rms_g)
    if alert_state is not None:
        alert_state.update(alert)
        if alert_state.changed:
            log.info(format_ok("ALERT", "on" if alert else "off"))
    log.info(
        format_ok(
            "SAMPLE",
            f"rms={metrics.rms_g:.4f} peak={metrics.peak_g:.4f} axis={metrics.axis}",
        )
    )
    lcd_due = True
    if lcd_throttle is not None:
        lcd_due = lcd_throttle.due(
            force=alert_state is not None and alert_state.changed
        )
    if lcd is not None and lcd_due:
        try:
            show(lcd, metrics.rms_g, metrics.peak_g, metrics.axis, alert=alert)
            log.info(format_ok("LCD_WRITE", f"axis={metrics.axis} alert={alert}"))
        except Exception as exc:
            log.error(format_fail("LCD_WRITE", str(exc), HINT_LCD_WRITE), exc_info=True)
    if buzzer is not None:
        try:
            buzzer.set_alert(alert)
        except Exception as exc:
            log.error(format_fail("BUZZ_WRITE", str(exc), HINT_BUZZ_WRITE), exc_info=True)
    # reading_payload 는 창 값만 담는다. 임계값·경보는 여기서 붙인다.
    payload = reading_payload(metrics, history)
    payload["threshold_g"] = detector.threshold_g
    payload["alert"] = alert
    socketio.emit("reading", payload)
    return True


def check_web_bind(host: str, port: int) -> None:
    """포트를 미리 잡아 본다. 안 잡히면 socketio.run 이 raw 트레이스백으로
    죽는 대신 [WEB_BIND] FAIL 한 줄을 남긴다."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host, port))
    except OSError as exc:
        raise HardwareError("WEB_BIND", str(exc), HINT_WEB_BIND) from exc
    finally:
        probe.close()


def measure_loop(
    sensor,
    lcd,
    socketio,
    stop: threading.Event,
    buzzer=None,
    config: MeasureConfig | None = None,
) -> None:
    settings = config if config is not None else MeasureConfig.from_interval(1.0)
    history = RmsHistory(maxlen=settings.history_len)
    alert_state = AlertState()
    throttle = UpdateThrottle()
    watch = RateWatch(settings.interval_s)
    while not stop.is_set():
        publish_reading(
            sensor,
            lcd,
            history,
            socketio,
            samples=settings.samples,
            duration_s=settings.interval_s,
            buzzer=buzzer,
            alert_state=alert_state,
            lcd_throttle=throttle,
            on_overrun=watch.on_overrun,
        )
        watch.settle()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_S,
        help=f"갱신 주기(초). 기본 {DEFAULT_INTERVAL_S}, 최소 {MIN_INTERVAL_S}",
    )
    parser.add_argument(
        "--detect",
        type=float,
        default=DEFAULT_THRESHOLD_G,
        help="경보 임계값(g). 0.7 또는 8",
    )
    return parser.parse_args(argv)


def apply_detect(value: object) -> float:
    """싱글톤 임계값을 고른다. 0.7/8 이 아니면 [BOOT] FAIL 후 종료한다."""
    try:
        return mode.set_threshold(value)
    except ValueError as exc:
        get_logger().error(
            format_fail(
                "BOOT",
                f"--detect {value} 은 0.7 또는 8 만 된다",
                HINT_DETECT,
            )
        )
        raise SystemExit(2) from exc


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)

    setup_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    log = get_logger()
    if args.interval < MIN_INTERVAL_S:
        log.error(
            format_fail(
                "BOOT",
                f"--interval {args.interval} 이 최소 {MIN_INTERVAL_S}초보다 짧다",
                HINT_RATE,
            )
        )
        raise SystemExit(2)
    apply_detect(args.detect)
    config = MeasureConfig.from_interval(args.interval)
    log.info(format_ok("BOOT", f"mock={args.mock} host={args.host} port={args.port}"))
    log.info(format_ok("DETECT", f"threshold={mode.threshold_g:g}g"))
    log.info(
        format_ok(
            "RATE",
            f"창 {config.interval_s:.2f}초 표본 {config.samples}개 "
            f"기준 {config.baseline_windows}창 연속 {config.persist_windows}창",
        )
    )

    try:
        sensor = open_sensor(mock=args.mock)
    except HardwareError as exc:
        log.error(str(exc), exc_info=True)
        raise SystemExit(2) from exc

    if args.mock:
        lcd = None
        buzzer = None
        log.info("[LCD_OPEN] skip (--mock)")
        log.info("[BUZZ_OPEN] skip (--mock)")
    else:
        lcd = open_display()
        buzzer = open_buzzer()

    app, socketio = create_app()
    stop = threading.Event()
    worker = threading.Thread(
        target=measure_loop,
        args=(sensor, lcd, socketio, stop, buzzer, config),
        daemon=True,
    )
    worker.start()
    log.info(format_ok("LOOP", "measure thread started"))
    try:
        check_web_bind(args.host, args.port)
    except HardwareError as exc:
        log.error(str(exc), exc_info=True)
        raise SystemExit(1) from exc
    log.info(format_ok("WEB_BIND", f"http://{args.host}:{args.port}"))
    socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
