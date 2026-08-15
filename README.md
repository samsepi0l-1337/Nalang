# 진동 측정기

Raspberry Pi Zero 2 W + ADXL355B + I2C 1602. 사양·배선·납땜·로그는 이 파일만 본다.

벨트/윤활 자동 판정, FFT, 부저, 저장, AP, 여러 대는 하지 않는다. 목적: 평소와 다른 진동을 **측정·표시**.

| 항목       | 결정                                    |
| ---------- | --------------------------------------- |
| OS         | Raspberry Pi OS 64-bit                  |
| 센서       | ADXL355B, SPI, 3.3 V. 전면 실크 기준    |
| 디스플레이 | I2C 1602, 백팩 VCC **3.3 V** (5 V 금지) |
| 부저       | 이번 소프트웨어·배선 없음               |
| 대수       | 1대, 기존 Wi-Fi                         |

센서는 EVAL 보드가 아니다. 칩 각인 `ADXL355B`. 윗줄 7홀(왼쪽→오른쪽): `CL-SCL`, `DA-SDA`, `SA0`, `SCK`, `INT2`, `VCC`, `GND`. 아랫줄 5홀: `DRDY`, `INT1`, `MISO`, `MOSI`, `CS`. 동봉 7핀은 **윗줄 전용**. SPI 데이터는 아랫줄이라 **두 줄 모두** 납땜한다.

## 배선

센서·LCD 백팩에 **5 V 금지**. GPIO 17(핀 11) “Chip Enable”은 CS가 아니다. CS는 **핀 24** (SPI0 CE0 → `/dev/spidev0.0`).

센서 I2C 핀(`CL-SCL`, `DA-SDA`, `SA0`)은 LCD 버스(핀 3·5)에 붙이지 않는다. `DRDY`, `INT1`, `INT2`는 연결하지 않는다.

### 센서 ADXL355B → Pi

| 센서 실크 | 줄     | BCM | Pi 핀 | 신호      | 빠지면 로그               |
| --------- | ------ | --- | ----- | --------- | ------------------------- |
| VCC       | 윗줄   | —   | 1     | 3.3 V     | `SENSOR_ID` `0xFF`        |
| GND       | 윗줄   | —   | 25    | GND       | `SENSOR_ID` `0xFF`        |
| SCK       | 윗줄   | 11  | 23    | SPI0 SCLK | `SENSOR_ID` `0x00`/`0xFF` |
| MOSI      | 아랫줄 | 10  | 19    | SPI0 MOSI | `SENSOR_ID` 이상한 ID     |
| MISO      | 아랫줄 | 9   | 21    | SPI0 MISO | `SENSOR_ID` `0x00`        |
| CS        | 아랫줄 | 8   | 24    | SPI0 CE0  | `SENSOR_ID` `0x00`        |

### LCD 1602 I2C 백팩 → Pi

| 백팩 | Pi 핀 | 신호     | 빠지면 로그 |
| ---- | ----- | -------- | ----------- |
| VCC  | 17    | 3.3 V    | `LCD_OPEN`  |
| GND  | 6     | GND      | `LCD_OPEN`  |
| SDA  | 3     | I2C1 SDA | `LCD_OPEN`  |
| SCL  | 5     | I2C1 SCL | `LCD_OPEN`  |

백팩 VCC를 핀 2·4(5 V)에 넣으면 SDA/SCL이 5 V가 되어 Pi GPIO가 손상된다.

### 납땜

- 헤더는 전면 실크가 보이게. 아랫줄 5홀에도 헤더 또는 전선.
- 이번 빌드에서 전선을 빼 두는 핀: `CL-SCL`, `DA-SDA`, `SA0`, `INT2`, `DRDY`,
  `INT1`. 숏만 피한다.
- LCD 백팩은 1602에 밀착. 핀 하나라도 뜨면 주소가 안 뜬다.
- 윤기 있는 원뿔 납땜. `MISO`-`MOSI`-`CS` 브리지 금지.
- 3.3 V와 GND가 붙으면 전원 금지.

전원 넣기 전 연속성: 센서 VCC↔핀1, GND↔핀25, SCK/MOSI/MISO/CS↔표의 핀. **핀1과 핀25가 통하면 숏.** LCD VCC↔17, GND↔6, SDA↔3, SCL↔5. LCD VCC와 5 V(핀2)는 통하면 안 된다.

문제 보고 시: 센서 전면, 아랫줄(MISO/MOSI/CS) 확대, Pi 점퍼 전체, LCD 백팩 VCC가 어느 핀인지, 로그 `[STAGE] FAIL` 한 줄.

## 측정

- ODR 1000 Hz, ±8.192 g. 1초 창에서 축별 평균(중력 DC)을 뺀 뒤 RMS·피크.
- 축: 그 창에서 AC RMS가 가장 큰 축. 동점이면 X→Y→Z.
- 1602 1초 갱신: `RMS 0.123 g` / `PK  0.456 g X` (각 16자).
- 폰: 포트 5000, 최근 60초 RMS 그래프. 원시 파형은 보내지 않는다.
- 알람·인증 없음.

스택: Python 3, `spidev`, `RPLCD`+`smbus2`, `numpy`, `Flask`+`Flask-SocketIO` (threading), Chart.js CDN. SPI `/dev/spidev0.0` 1 MHz mode 0. DEVID_AD=`0xAD`, RANGE=`0x83`, FILTER=`0x02`, POWER_CTL=`0x00`.

## 로그

stderr. 형식: `[SENSOR_ID] FAIL DEVID_AD=0x00 expected=0xAD | HINT ...`

`journalctl -u vibration-meter -f`. `--log-level INFO`. SAMPLE은 1초마다 OK.

| 순서 | 코드         | OK 의미                     |
| ---- | ------------ | --------------------------- |
| 1    | `BOOT`       | 프로세스 시작               |
| 2    | `MOCK`       | `--mock` 합성 센서          |
| 3    | `SPI_OPEN`   | `/dev/spidev0.0` 열림       |
| 4    | `SENSOR_ID`  | DEVID_AD=`0xAD`             |
| 5    | `SENSOR_CFG` | ±8 g, 1000 Hz               |
| 6    | `LCD_ADDR`   | 0x27 또는 0x3F 시도         |
| 7    | `LCD_OPEN`   | 1602. 실패해도 웹 계속      |
| 8    | `LOOP`       | 측정 스레드                 |
| 9    | `WEB_BIND`   | 포트 5000                   |
| 10   | `SAMPLE`     | 1초 RMS 성공                |
| 11   | `LCD_WRITE`  | 1602 갱신. 실패해도 웹 계속 |

`SPI_OPEN` / `SENSOR_ID` 실패는 종료 코드 2. LCD 실패는 종료하지 않는다.

| 코드        | 대표 메시지            | 볼 곳                         |
| ----------- | ---------------------- | ----------------------------- |
| `SPI_OPEN`  | spidev 없음            | raspi-config SPI, 재부팅      |
| `SPI_OPEN`  | Permission denied      | `usermod -aG spi,i2c $USER`   |
| `SPI_OPEN`  | No module named spidev | `requirements-pi.txt`         |
| `SENSOR_ID` | `DEVID_AD=0x00`        | MISO 핀21, CS 핀24, 아랫줄    |
| `SENSOR_ID` | `DEVID_AD=0xFF`        | VCC 핀1, GND 핀25, 윗줄, 5 V  |
| `SENSOR_ID` | 그 외 ID               | MOSI/MISO 교차, 센서 I2C 혼선 |
| `LCD_OPEN`  | I2C / no device        | 백팩 3.3 V 핀17, SDA/SCL      |
| `LCD_WRITE` | i2c timeout            | 커넥터 헐거움                 |
| `SAMPLE`    | bus nak                | 측정 중 SPI 단선              |
| `WEB_BIND`  | address in use         | 포트 5000 점유. 배선 아님     |

원격에는 FAIL 한 줄 전체를 복사한다.

## PC에서 테스트

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
PYTHONPATH=src .venv/bin/python -m vibration_meter.app --mock
```

mock 웹: `http://127.0.0.1:5000`.

## Pi

```
sudo raspi-config   # SPI, I2C Enable
python3 -m venv .venv
.venv/bin/pip install -r requirements-pi.txt
PYTHONPATH=src .venv/bin/python -m vibration_meter.app
```

```
ls -l /dev/spidev0.0
sudo i2cdetect -y 1
```

`spidev0.0` 없음 → 로그 `SPI_OPEN`. `i2cdetect`가 전부 `--` → `LCD_OPEN`. `0x27`
또는 `0x3F`면 LCD 버스는 된 것.

```
sudo cp deploy/vibration-meter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now vibration-meter
journalctl -u vibration-meter -f
```

`WorkingDirectory`와 `ExecStart`를 클론 경로에 맞춘다. 폰:
`http://<pi-ip>:5000`.
