# 진동 측정기

Raspberry Pi Zero 2 W + ADXL355B + I2C 1602. 사양: `docs/prototype-spec.md`.
구현: `docs/implementation.md`.

## PC에서 테스트

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
.venv/bin/python -m vibration_meter.app --mock
```

`PYTHONPATH=src`가 필요하면 `src`를 path에 넣는다. pytest는 `pytest.ini`가
처리한다. mock 웹은 `http://127.0.0.1:5000`.

## Pi

SPI·I2C를 켠다. 배선은 사양 3절.

```
sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m venv .venv
.venv/bin/pip install -r requirements-pi.txt
PYTHONPATH=src .venv/bin/python -m vibration_meter.app
```

자동 시작:

```
sudo cp deploy/vibration-meter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vibration-meter
```

서비스의 `WorkingDirectory`와 `ExecStart` 파이썬 경로를 클론 위치에 맞춘다.
폰에서 `http://<pi-ip>:5000`.
