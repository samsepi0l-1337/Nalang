import argparse
import logging
import threading
import time
from dataclasses import dataclass

from vibration_meter.adxl355 import ODR_HZ
from vibration_meter.collector import OverrunHandler, collect_window
from vibration_meter.display import UpdateThrottle, show
from vibration_meter.errors import (
    HINT_BUZZ_WRITE,
    HINT_LCD_WRITE,
    HINT_RATE,
    HINT_SAMPLE,
    HardwareError,
    format_fail,
    format_ok,
)
from vibration_meter.hardware import open_buzzer, open_display, open_sensor
from vibration_meter.logutil import get_logger, setup_logging
from vibration_meter.metrics import RmsHistory
from vibration_meter.outlier import (
    BASELINE_S,
    MIN_BASELINE,
    PERSIST_S,
    PersistTracker,
    mean_shift_ratio,
    windows_for,
)
from vibration_meter.webapp import create_app, reading_payload

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
    tracker: PersistTracker | None = None,
    *,
    baseline_windows: int = MIN_BASELINE,
    lcd_throttle: UpdateThrottle | None = None,
    on_overrun: OverrunHandler | None = None,
) -> bool:
    log = get_logger()
    try:
        metrics = collect_window(
            sensor, samples=samples, duration_s=duration_s, on_overrun=on_overrun
        )
    except Exception as exc:
        log.error(format_fail("SAMPLE", str(exc), HINT_SAMPLE), exc_info=True)
        return False
    baseline = [point["rms_g"] for point in history.as_list()]
    history.push(time.time(), metrics.rms_g)
    alert = False
    if tracker is not None:
        alert = tracker.update(mean_shift_ratio(metrics.rms_g, baseline, baseline_windows))
        if tracker.changed:
            log.info(format_ok("ALERT", "on" if alert else "off"))
    log.info(
        format_ok(
            "SAMPLE",
            f"rms={metrics.rms_g:.4f} peak={metrics.peak_g:.4f} axis={metrics.axis}",
        )
    )
    lcd_due = True
    if lcd_throttle is not None:
        lcd_due = lcd_throttle.due(force=tracker is not None and tracker.changed)
    if lcd is not None and lcd_due:
        try:
            show(lcd, metrics.rms_g, metrics.peak_g, metrics.axis, alert=alert)
        except Exception as exc:
            log.error(format_fail("LCD_WRITE", str(exc), HINT_LCD_WRITE), exc_info=True)
    if buzzer is not None:
        try:
            buzzer.set_alert(alert)
        except Exception as exc:
            log.error(format_fail("BUZZ_WRITE", str(exc), HINT_BUZZ_WRITE), exc_info=True)
    socketio.emit("reading", reading_payload(metrics, history))
    return True


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
    tracker = PersistTracker(needed=settings.persist_windows)
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
            tracker=tracker,
            baseline_windows=settings.baseline_windows,
            lcd_throttle=throttle,
            on_overrun=watch.on_overrun,
        )
        watch.settle()


def main(argv: list[str] | None = None) -> None:
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
    args = parser.parse_args(argv)

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
    config = MeasureConfig.from_interval(args.interval)
    log.info(format_ok("BOOT", f"mock={args.mock} host={args.host} port={args.port}"))
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
    log.info(format_ok("WEB_BIND", f"http://{args.host}:{args.port}"))
    socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
