from pathlib import Path

from flask import Flask, render_template
from flask_socketio import SocketIO

from vibration_meter.metrics import RmsHistory, WindowMetrics

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def create_app() -> tuple[Flask, SocketIO]:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

    @app.get("/")
    def index():
        return render_template("index.html")

    return app, socketio


def reading_payload(metrics: WindowMetrics, history: RmsHistory) -> dict:
    return {
        "rms_g": metrics.rms_g,
        "peak_g": metrics.peak_g,
        "axis": metrics.axis,
        "history": history.as_list(),
    }
