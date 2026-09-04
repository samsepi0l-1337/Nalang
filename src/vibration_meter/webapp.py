from pathlib import Path

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

from vibration_meter.detect import THRESHOLDS_G, mode
from vibration_meter.metrics import RmsHistory, WindowMetrics

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _detect_payload() -> dict:
    return {
        "threshold_g": mode.threshold_g,
        "thresholds_g": list(THRESHOLDS_G),
    }


def create_app() -> tuple[Flask, SocketIO]:
    app = Flask(__name__, template_folder=str(TEMPLATE_DIR))
    socketio = SocketIO(app, async_mode="threading", cors_allowed_origins="*")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/detect")
    def get_detect():
        return jsonify(_detect_payload())

    @app.post("/api/detect")
    def set_detect():
        body = request.get_json(silent=True)
        if not isinstance(body, dict) or "threshold_g" not in body:
            return jsonify({"error": "missing threshold_g"}), 400
        try:
            mode.set_threshold(body["threshold_g"])
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(_detect_payload())

    return app, socketio


def reading_payload(
    metrics: WindowMetrics,
    history: RmsHistory,
    *,
    threshold_g: float | None = None,
    alert: bool = False,
) -> dict:
    return {
        "rms_g": metrics.rms_g,
        "peak_g": metrics.peak_g,
        "axis": metrics.axis,
        "history": history.as_list(),
        "threshold_g": mode.threshold_g if threshold_g is None else threshold_g,
        "alert": alert,
    }
