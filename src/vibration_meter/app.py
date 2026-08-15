import argparse
import threading
import time

from vibration_meter.collector import collect_second
from vibration_meter.display import show
from vibration_meter.hardware import open_display, open_sensor
from vibration_meter.metrics import RmsHistory
from vibration_meter.webapp import create_app, reading_payload


def measure_loop(sensor, lcd, socketio, stop: threading.Event) -> None:
    history = RmsHistory(maxlen=60)
    while not stop.is_set():
        metrics = collect_second(sensor)
        history.push(time.time(), metrics.rms_g)
        if lcd is not None:
            show(lcd, metrics.rms_g, metrics.peak_g, metrics.axis)
        socketio.emit("reading", reading_payload(metrics, history))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args(argv)

    sensor = open_sensor(mock=args.mock)
    lcd = None if args.mock else open_display()
    app, socketio = create_app()
    stop = threading.Event()
    worker = threading.Thread(
        target=measure_loop,
        args=(sensor, lcd, socketio, stop),
        daemon=True,
    )
    worker.start()
    socketio.run(app, host=args.host, port=args.port, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
