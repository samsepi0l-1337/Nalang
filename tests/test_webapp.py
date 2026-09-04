import pytest

from vibration_meter.detect import THRESHOLDS_G, mode
from vibration_meter.metrics import RmsHistory, WindowMetrics
from vibration_meter.webapp import create_app, reading_payload


@pytest.fixture(autouse=True)
def restore_detect_mode():
    mode.set_threshold(0.7)
    try:
        yield
    finally:
        mode.set_threshold(0.7)


def test_index_contains_chart_and_socket():
    app, _socketio = create_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Chart.js" in body or "chart.js" in body
    assert "socket.io" in body
    assert "chart.data.datasets[0].data = msg.history.map((p) => p.rms_g)" in body
    assert "socket.on(\"reading\"" in body or "socket.on('reading'" in body
    assert "0.7" in body
    assert "8" in body
    assert "/api/detect" in body


def test_reading_payload_includes_history():
    history = RmsHistory(maxlen=60)
    history.push(1.0, 0.2)
    payload = reading_payload(
        WindowMetrics(axis="Y", rms_g=0.2, peak_g=0.3),
        history,
    )
    assert payload["axis"] == "Y"
    assert payload["history"] == [{"t": 1.0, "rms_g": 0.2}]
    assert payload["threshold_g"] == 0.7
    assert payload["alert"] is False
    assert set(payload) == {"rms_g", "peak_g", "axis", "history", "threshold_g", "alert"}
    assert "x" not in payload
    assert "samples" not in payload


def test_get_detect_defaults_to_0_7():
    app, _socketio = create_app()
    client = app.test_client()
    response = client.get("/api/detect")
    assert response.status_code == 200
    assert response.get_json() == {
        "threshold_g": 0.7,
        "thresholds_g": [0.7, 8.0],
    }
    assert list(response.get_json()["thresholds_g"]) == list(THRESHOLDS_G)


def test_post_detect_8_then_get_is_8():
    app, _socketio = create_app()
    client = app.test_client()
    posted = client.post("/api/detect", json={"threshold_g": 8})
    assert posted.status_code == 200
    assert posted.get_json()["threshold_g"] == 8.0
    got = client.get("/api/detect")
    assert got.status_code == 200
    assert got.get_json() == {
        "threshold_g": 8.0,
        "thresholds_g": [0.7, 8.0],
    }


def test_post_detect_0_7_switches_back():
    app, _socketio = create_app()
    client = app.test_client()
    client.post("/api/detect", json={"threshold_g": 8.0})
    posted = client.post("/api/detect", json={"threshold_g": 0.7})
    assert posted.status_code == 200
    assert posted.get_json()["threshold_g"] == 0.7
    got = client.get("/api/detect")
    assert got.get_json()["threshold_g"] == 0.7


def test_post_detect_rejects_invalid_and_missing():
    app, _socketio = create_app()
    client = app.test_client()
    bad = client.post("/api/detect", json={"threshold_g": 2})
    assert bad.status_code == 400
    assert "error" in bad.get_json()
    empty = client.post("/api/detect", json={})
    assert empty.status_code == 400
    assert "error" in empty.get_json()
    assert mode.threshold_g == 0.7
