from vibration_meter.metrics import RmsHistory, WindowMetrics
from vibration_meter.webapp import create_app, reading_payload


def test_index_contains_chart_and_socket():
    app, _socketio = create_app()
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Chart.js" in body or "chart.js" in body
    assert "socket.io" in body
    assert "msg.history.map((p) => p.rms_g)" in body
    assert "socket.on(\"reading\"" in body or "socket.on('reading'" in body


def test_reading_payload_includes_history():
    history = RmsHistory(maxlen=60)
    history.push(1.0, 0.2)
    payload = reading_payload(
        WindowMetrics(axis="Y", rms_g=0.2, peak_g=0.3),
        history,
    )
    assert payload["axis"] == "Y"
    assert payload["history"] == [{"t": 1.0, "rms_g": 0.2}]
    assert set(payload) == {"rms_g", "peak_g", "axis", "history"}
    assert "x" not in payload
    assert "samples" not in payload
