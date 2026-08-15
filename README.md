# 진동 측정기

Raspberry Pi Zero 2 W + ADXL355B + I2C 1602.

- 사양: `docs/prototype-spec.md`
- 구현: `docs/implementation.md`
- 배선·납땜 상세: `docs/wiring.md`
- 로그 코드: `docs/logs.md`

`docs/`는 git에 포함한다. `.gitignore`로 빼지 않는다.

## 배선

센서·LCD 백팩에 **5 V 금지**. 둘 다 3.3 V. GPIO 17(핀 11)은 CS가 아니다.
CS는 **핀 24**. 사진: `docs/assets/adxl355-front.png`,
`docs/assets/pi-zero-2w-gpio.png`.

동봉 7핀은 센서 **윗줄**만 덮는다. SPI 데이터는 아랫줄이라 **두 줄 모두**
납땜한다. 센서 I2C 핀(`CL-SCL`, `DA-SDA`, `SA0`)은 LCD 버스에 붙이지 않는다.

### 센서 ADXL355B → Pi Zero 2 W

| 센서 실크 | 줄     | Pi 핀 | 신호      |
| --------- | ------ | ----- | --------- |
| VCC       | 윗줄   | 1     | 3.3 V     |
| GND       | 윗줄   | 25    | GND       |
| SCK       | 윗줄   | 23    | SPI0 SCLK |
| MOSI      | 아랫줄 | 19    | SPI0 MOSI |
| MISO      | 아랫줄 | 21    | SPI0 MISO |
| CS        | 아랫줄 | 24    | SPI0 CE0  |

`DRDY`, `INT1`, `INT2`는 연결하지 않는다.

### LCD 1602 I2C 백팩 → Pi

| 백팩 | Pi 핀 | 신호     |
| ---- | ----- | -------- |
| VCC  | 17    | 3.3 V    |
| GND  | 6     | GND      |
| SDA  | 3     | I2C1 SDA |
| SCL  | 5     | I2C1 SCL |

백팩 VCC를 핀 2·4(5 V)에 넣으면 SDA/SCL이 5 V가 되어 Pi GPIO가 손상된다.

전원 넣기 전: 핀 1(3.3 V)과 핀 25(GND)가 통하면 숏이므로 켜지 않는다.
납땜 품질·연속성 검사·실패 로그 매핑은 `docs/wiring.md`.

## PC에서 테스트

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
PYTHONPATH=src .venv/bin/python -m vibration_meter.app --mock
```

mock 웹은 `http://127.0.0.1:5000`.

## Pi

```
sudo raspi-config   # SPI, I2C Enable
sudo apt update
sudo apt install -y python3-pip python3-venv
python3 -m venv .venv
.venv/bin/pip install -r requirements-pi.txt
PYTHONPATH=src .venv/bin/python -m vibration_meter.app
```

```
ls -l /dev/spidev0.0
sudo i2cdetect -y 1
```

`i2cdetect`에 `0x27` 또는 `0x3F`가 있어야 LCD 버스가 산 것이다.

자동 시작:

```
sudo cp deploy/vibration-meter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vibration-meter
```

`WorkingDirectory`와 `ExecStart`를 클론 경로에 맞춘다.
폰: `http://<pi-ip>:5000`.

```
journalctl -u vibration-meter -f
```

`[STAGE] FAIL` 한 줄을 복사해 `docs/logs.md`와 맞춘다.
