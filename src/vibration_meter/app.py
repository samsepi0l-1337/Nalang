import argparse
import logging
import threading
import time

from vibration_meter.collector import collect_second
from vibration_meter.display import show
from vibration_meter.errors import HINT_LCD_WRITE, HINT_SAMPLE, HardwareError, format_fail, format_ok
from vibration_meter.hardware import open_display, open_sensor
from vibration_meter.logutil import get_logger, setup_logging
from vibration_meter.metrics import RmsHistory
from vibration_meter.webapp import create_app, reading_payload


def publish_reading(
    sensor,
    lcd,
    history: RmsHistory,
    socketio,
    samples: int = 1000,
    duration_s: float = 1.0,
) -> bool:
    log = get_logger()
    try:
        metrics = collect_second(sensor, samples=samples, duration_s=duration_s)
    except Exception as exc:
        log.error(format_fail("SAMPLE", str(exc), HINT_SAMPLE), exc_info=True)
        return False
    history.push(time.time(), metrics.rms_g)
    log.info(
        format_ok(
            "SAMPLE",
            f"rms={metrics.rms_g:.4f} peak={metrics.peak_g:.4f} axis={metrics.axis}",
        )
    )
    if lcd is not None:
        try:
            show(lcd, metrics.rms_g, metrics.peak_g, metrics.axis)
        except Exception as exc:
            log.error(format_fail("LCD_WRITE", str(exc), HINT_LCD_WRITE), exc_info=True)
    socketio.emit("reading", reading_payload(metrics, history))
    return True


def measure_loop(sensor, lcd, socketio, stop: threading.Event) -> None:
    history = RmsHistory(maxlen=60)
    while not stop.is_set():
        publish_reading(sensor, lcd, history, socketio)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)

    setup_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    log = get_logger()
    log.info(format_ok("BOOT", f"mock={args.mock} host={args.host} port={args.port}"))

    try:
        sensor = open_sensor(mock=args.mock)
    except HardwareError as exc:
        log.error(str(exc), exc_info=True)
        raise SystemExit(2) from exc

    if args.mock:
        lcd = None
        log.info("[LCD_OPEN] skip (--mock)")
    else:
        lcd = open_display()

    app, socketio = create_app()
    stop = threading.Event()
    worker = threading.Thread(
        target=measure_loop,
        args=(sensor, lcd, socketio, stop),
        daemon=True,
    )
    worker.start()
    log.info(format_ok("LOOP", "measure thread started"))
    log.info(format_ok("WEB_BIND", f"http://{args.host}:{args.port}"))
    socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
