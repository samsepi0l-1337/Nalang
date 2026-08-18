# 설정

Raspberry Pi Zero 2 W 한 대, 기존 Wi-Fi. 센서 ADXL355B(SPI) + I2C 1602.
사양·핀 표의 원본은 `README.md`.

벨트/윤활 판정, FFT, 저장, AP는 하지 않는다. 평균 대비 5% 연속 5초 또는 10% 급변이면 1602 `OUTLIER`와 패시브 부저.

## 전원·핀 (먼저)

센서와 LCD 백팩은 **3.3 V만**. 5 V 금지.

GPIO 17(핀 11)은 CS가 아니다. CS는 **핀 24** (SPI0 CE0 → `/dev/spidev0.0`).
아두이노 `spiCsPin = 2`는 D2이지 Pi 핀 2(5 V)가 아니다.

센서 I2C 핀(`CL-SCL`, `DA-SDA`, `SA0`)은 LCD 버스(핀 3·5)에 붙이지 않는다.
`DRDY`, `INT1`, `INT2`는 연결하지 않는다. `beginI2C` 열(SCLK/MISO→GND)은 쓰지 않는다.

### 센서 ADXL355B → Pi

PL_ADXL355 `beginSPI`와 같은 4선. 동봉 7핀 헤더는 윗줄만 덮는다. SPI 데이터는 아랫줄이라 **두 줄 모두** 납땜한다.

| ADXL355    | 아두이노 SPI | Pi 핀 | 신호      |
| ---------- | ------------ | ----- | --------- |
| VCC        | 3.3 V        | 1     | 3.3 V     |
| GND        | GND          | 25    | GND       |
| SCLK/Vssio | SCLK         | 23    | SPI0 SCLK |
| MOSI/SDA   | MOSI         | 19    | SPI0 MOSI |
| MISO/ASEL  | MISO         | 21    | SPI0 MISO |
| CS/SCL     | D2 (GPIO CS) | 24    | SPI0 CE0  |

### LCD 1602 I2C 백팩 → Pi

| 백팩 | Pi 핀 | 신호     |
| ---- | ----- | -------- |
| VCC  | 17    | 3.3 V    |
| GND  | 6     | GND      |
| SDA  | 3     | I2C1 SDA |
| SCL  | 5     | I2C1 SCL |

백팩 VCC를 핀 2·4(5 V)에 넣으면 SDA/SCL이 5 V가 되어 Pi GPIO가 손상된다.

### 패시브 부저 KY-006 → Pi

Arduino `tone(8, 1000)`과 같다. 예제 `8`은 D8이지 Pi 핀 8(TXD)이 아니다.

| KY-006 | 아두이노 | Pi 핀 | 신호 |
| ------ | -------- | ----- | ---- |
| S      | D8       | 12    | PWM (BCM 18) |
| 가운데 | NC       | NC    | 비움 |
| −      | GND      | 14    | GND  |

KY-012 액티브 금지. `+`/가운데를 5 V에 넣지 않는다.

### 납땜·연속성

- 헤더는 전면 실크가 보이게. 아랫줄 5홀에도 헤더 또는 전선.
- 전선을 빼 두는 핀: `CL-SCL`, `DA-SDA`, `SA0`, `INT2`, `DRDY`, `INT1`.
- LCD 백팩은 1602에 밀착. `MISO`-`MOSI`-`CS` 브리지 금지.
- 전원 전: 센서 VCC↔핀1, GND↔핀25. **핀1과 핀25가 통하면 숏. 켜지 않는다.**
- LCD VCC↔17, GND↔6, SDA↔3, SCL↔5. LCD VCC와 5 V(핀2)는 통하면 안 된다.
- 부저 S↔핀12, −↔핀14. 부저 S와 5 V(핀2)는 통하면 안 된다.

## PC (센서 없이)

소프트웨어만 확인할 때.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
PYTHONPATH=src .venv/bin/python -m vibration_meter.app --mock
```

브라우저: `http://127.0.0.1:5000`. `--mock`은 SPI/LCD/부저를 열지 않는다.

## Pi

1. Raspberry Pi OS 64-bit.
2. `sudo raspi-config` → Interface Options에서 SPI, I2C Enable → 재부팅.
3. 저장소 클론. 아래는 `/home/pi/Nalang` 기준. 경로가 다르면 systemd 파일도 맞춘다.
4. 그룹:

```
sudo usermod -aG spi,i2c,gpio $USER
```

재로그인한다.

5. 버스 확인:

```
ls -l /dev/spidev0.0
sudo i2cdetect -y 1
```

- `spidev0.0` 없음 → 로그 `SPI_OPEN`. raspi-config SPI 후 재부팅.
- `i2cdetect`가 전부 `--` → LCD 버스. 로그 `LCD_OPEN`.
- `0x27` 또는 `0x3F`면 LCD I2C는 된 것.

6. 실행:

```
python3 -m venv .venv
.venv/bin/pip install -r requirements-pi.txt
PYTHONPATH=src .venv/bin/python -m vibration_meter.app
```

폰은 같은 Wi-Fi에서 `http://<pi-ip>:5000`. 차트(Chart.js / Socket.IO)는 CDN이라 Pi에 인터넷이 필요하다.

옵션: `--host 0.0.0.0 --port 5000 --log-level INFO`.

## 자동 시작 (systemd)

`deploy/vibration-meter.service`의 `WorkingDirectory`, `Environment=PYTHONPATH=…`, `ExecStart`를 클론 경로에 맞춘다. 기본값은 `/home/pi/Nalang`.

```
sudo cp deploy/vibration-meter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vibration-meter
journalctl -u vibration-meter -f
```

## 로그로 배선 보기

형식: `[STAGE] FAIL … | HINT …`. 원격에는 그 한 줄을 그대로 보낸다.

`SPI_OPEN` / `SENSOR_ID` 실패는 종료 코드 2. LCD·부저 실패는 웹을 계속한다.

| 로그                         | 볼 곳                                      |
| ---------------------------- | ------------------------------------------ |
| `SPI_OPEN` spidev 없음       | raspi-config SPI, 재부팅                   |
| `SPI_OPEN` Permission denied | `usermod -aG spi,i2c,gpio $USER` 후 재로그인 |
| `SPI_OPEN` No module named spidev | `requirements-pi.txt`                 |
| `SENSOR_ID` `0x00`           | MISO 핀21, CS 핀24, beginSPI               |
| `SENSOR_ID` `0xFF`           | VCC 핀1, GND 핀25, 윗줄, 5 V 여부          |
| `SENSOR_ID` 그 외 ID         | MOSI/MISO 교차, CL-SCL/DA-SDA 연결         |
| `LCD_OPEN`                   | 백팩 3.3 V 핀17, SDA 핀3, SCL 핀5          |
| `BUZZ_OPEN`                  | 핀12 BCM18, KY-006 S, D8는 Pi 핀8이 아님   |
| `LCD_WRITE`                  | I2C 커넥터 헐거움                          |
| `BUZZ_WRITE`                 | 핀12 PWM, 패시브, GND 핀14                 |
| `SAMPLE` bus nak             | 측정 중 SPI 단선                           |
| `WEB_BIND` address in use    | 포트 5000 점유. 배선 아님                  |

문제 보고: 센서 전면, 아랫줄(MISO/MOSI/CS) 확대, Pi 점퍼 전체, LCD 백팩 VCC가 어느 핀인지, 부저 S가 핀 12인지, `[STAGE] FAIL` 한 줄.
