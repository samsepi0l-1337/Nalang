# 진동 측정기

Raspberry Pi Zero 2 W + ADXL355B + I2C 1602. 사양·배선·납땜·로그는 이 파일만 본다.

벨트/윤활 자동 판정, FFT, 저장, AP, 여러 대는 하지 않는다. 목적: 평소와 다른 진동을 **측정·표시**. 평균 대비 5%가 연속 5초이거나 10% 급변이면 1602에 `OUTLIER`를 띄우고 패시브 부저를 켠다.

| 항목       | 결정                                    |
| ---------- | --------------------------------------- |
| OS         | Raspberry Pi OS 64-bit                  |
| 센서       | ADXL355B, SPI, 3.3 V. 전면 실크 기준    |
| 디스플레이 | I2C 1602, 백팩 VCC **3.3 V** (5 V 금지) |
| 부저       | 패시브(KY-006). `tone()` PWM. 액티브(KY-012) 금지 |
| 대수       | 1대, 기존 Wi-Fi                         |

센서는 EVAL 보드가 아니다. 칩 각인 `ADXL355B`. 윗줄 7홀(왼쪽→오른쪽): `CL-SCL`, `DA-SDA`, `SA0`, `SCK`, `INT2`, `VCC`, `GND`. 아랫줄 5홀: `DRDY`, `INT1`, `MISO`, `MOSI`, `CS`. 동봉 7핀은 **윗줄 전용**. SPI 데이터는 아랫줄이라 **두 줄 모두** 납땜한다.

인터페이스는 PL_ADXL355 `beginSPI`와 같다. `beginI2C`(MISO/ASEL→GND, SCLK/Vssio→GND)는 쓰지 않는다. 아두이노 `spiCsPin = 2`는 **D2**이지, Pi 헤더 핀 2(5 V)가 아니다. Pi CS는 **핀 24**(SPI0 CE0).

## 배선

센서·LCD 백팩에 **5 V 금지**. GPIO 17(핀 11) “Chip Enable”은 CS가 아니다. CS는 **핀 24** (SPI0 CE0 → `/dev/spidev0.0`).

센서 I2C 핀(`CL-SCL`, `DA-SDA`, `SA0`)은 LCD 버스(핀 3·5)에 붙이지 않는다. `DRDY`, `INT1`, `INT2`는 연결하지 않는다.

### 센서 ADXL355B → Pi

PL_ADXL355 SPI 열과 같은 4선. I2C 열의 GND 묶기는 하지 않는다.

| ADXL355     | 아두이노 SPI | Pi 핀 | BCM | 신호      | 빠지면 로그               |
| ----------- | ------------ | ----- | --- | --------- | ------------------------- |
| VCC         | 3.3 V        | 1     | —   | 3.3 V     | `SENSOR_ID` `0xFF`        |
| GND         | GND          | 25    | —   | GND       | `SENSOR_ID` `0xFF`        |
| SCLK/Vssio  | SCLK         | 23    | 11  | SPI0 SCLK | `SENSOR_ID` `0x00`/`0xFF` |
| MOSI/SDA    | MOSI         | 19    | 10  | SPI0 MOSI | `SENSOR_ID` 이상한 ID     |
| MISO/ASEL   | MISO         | 21    | 9   | SPI0 MISO | `SENSOR_ID` `0x00`        |
| CS/SCL      | D2 (GPIO CS) | 24    | 8   | SPI0 CE0  | `SENSOR_ID` `0x00`        |

보드 실크: `SCLK/Vssio`=`SCK` 윗줄, `MOSI`/`MISO`/`CS` 아랫줄. `CL-SCL`은 아두이노 I2C의 SCL이지 SPI CS가 아니다.

### LCD 1602 I2C 백팩 → Pi

| 백팩 | Pi 핀 | 신호     | 빠지면 로그 |
| ---- | ----- | -------- | ----------- |
| VCC  | 17    | 3.3 V    | `LCD_OPEN`  |
| GND  | 6     | GND      | `LCD_OPEN`  |
| SDA  | 3     | I2C1 SDA | `LCD_OPEN`  |
| SCL  | 5     | I2C1 SCL | `LCD_OPEN`  |

백팩 VCC를 핀 2·4(5 V)에 넣으면 SDA/SCL이 5 V가 되어 Pi GPIO가 손상된다.

### 패시브 부저 KY-006 → Pi

Arduino `tone(8, 1000)` / `noTone(8)` 과 같다. `digitalWrite`만 하면 패시브는 안 울린다. KY-012 액티브는 쓰지 않는다.

아두이노 예제의 `8`은 **D8**이지, Pi 헤더 핀 8(GPIO 14 TXD)이 아니다. Pi는 하드웨어 PWM0인 **핀 12**(BCM 18).

| KY-006 | 아두이노 `tone()` | Pi 핀 | BCM | 신호 |
| ------ | ----------------- | ----- | --- | ---- |
| S      | D8                | 12    | 18  | PWM  |
| 가운데 | NC (대부분)       | NC    | —   | 연결하지 않음 |
| −      | GND               | 14    | —   | GND  |

2핀 피에조면 + → 핀 12(100 Ω 직렬 가능), − → 핀 14. 가운데/`+`를 핀 2·4(5 V)에 넣지 않는다. 3핀 모듈의 `+`가 전원으로 실크된 경우만 **핀 1 또는 17 (3.3 V)**.

빠지면 로그 `BUZZ_OPEN` / `BUZZ_WRITE`. 실패해도 웹·LCD는 계속한다.

### 납땜

- 헤더는 전면 실크가 보이게. 아랫줄 5홀에도 헤더 또는 전선.
- 이번 빌드에서 전선을 빼 두는 핀: `CL-SCL`, `DA-SDA`, `SA0`, `INT2`, `DRDY`,
  `INT1`. 숏만 피한다.
- LCD 백팩은 1602에 밀착. 핀 하나라도 뜨면 주소가 안 뜬다.
- 윤기 있는 원뿔 납땜. `MISO`-`MOSI`-`CS` 브리지 금지.
- 3.3 V와 GND가 붙으면 전원 금지.

전원 넣기 전 연속성: 센서 VCC↔핀1, GND↔핀25, SCK/MOSI/MISO/CS↔표의 핀. **핀1과 핀25가 통하면 숏.** LCD VCC↔17, GND↔6, SDA↔3, SCL↔5. LCD VCC와 5 V(핀2)는 통하면 안 된다. 부저 S↔핀12, −↔핀14. 부저 S와 5 V(핀2)는 통하면 안 된다.

문제 보고 시: 센서 전면, 아랫줄(MISO/MOSI/CS) 확대, Pi 점퍼 전체, LCD 백팩 VCC가 어느 핀인지, 부저 S가 핀 12인지, 로그 `[STAGE] FAIL` 한 줄.

## 측정

- ODR 1000 Hz, ±8.192 g. 1초 창에서 축별 평균(중력 DC)을 뺀 뒤 RMS·피크.
- 축: 그 창에서 AC RMS가 가장 큰 축. 동점이면 X→Y→Z.
- 1602 1초 갱신: `RMS 0.123 g` / `PK  0.456 g X` (각 16자).
- 이상치 표시: 직전 창 RMS 평균 대비 |Δ|≥5%가 **연속 5초**, 또는 |Δ|≥10%로 **급변**. 기준 10초 미만은 판정하지 않음. 걸리면 2행 `OUTLIER        X`, 패시브 부저 1 kHz (`tone()`).
- 폰: 포트 5000, 최근 60초 RMS 그래프. 원시 파형은 보내지 않는다.

스택: Python 3, `spidev`, `RPLCD`+`smbus2`, `gpiozero` `TonalBuzzer`, `numpy`, `Flask`+`Flask-SocketIO` (threading), Chart.js CDN. SPI `/dev/spidev0.0` 1 MHz mode 0. DEVID_AD=`0xAD`, RANGE=`0x83`, FILTER=`0x02`, POWER_CTL=`0x00`. 부저 BCM 18, 1000 Hz.

## 로그

stderr. 형식: `[SENSOR_ID] FAIL DEVID_AD=0x00 expected=0xAD | HINT ...`

`journalctl -u vibration-meter -f`. 또는 `sh scripts/collect-logs.sh`. `--log-level INFO`. SAMPLE은 1초마다 OK.

| 순서 | 코드         | OK 의미                     |
| ---- | ------------ | --------------------------- |
| 1    | `BOOT`       | 프로세스 시작               |
| 2    | `MOCK`       | `--mock` 합성 센서          |
| 3    | `SPI_OPEN`   | `/dev/spidev0.0` 열림       |
| 4    | `SENSOR_ID`  | DEVID_AD=`0xAD`             |
| 5    | `SENSOR_CFG` | ±8 g, 1000 Hz               |
| 6    | `LCD_ADDR`   | 0x27 또는 0x3F 시도         |
| 7    | `LCD_OPEN`   | 1602. 실패해도 웹 계속      |
| 8    | `BUZZ_OPEN`  | 핀12 PWM. 실패해도 웹 계속  |
| 9    | `LOOP`       | 측정 스레드                 |
| 10   | `WEB_BIND`   | 포트 5000                   |
| 11   | `SAMPLE`     | 1초 RMS 성공                |
| 12   | `ALERT`      | 지속 이상치 on/off          |
| 13   | `LCD_WRITE`  | 1602 갱신. 실패해도 웹 계속 |
| 14   | `BUZZ_WRITE` | 부저. 실패해도 웹 계속      |

`SPI_OPEN` / `SENSOR_ID` 실패는 종료 코드 2. LCD·부저 실패는 종료하지 않는다.

| 코드        | 대표 메시지            | 볼 곳                         |
| ----------- | ---------------------- | ----------------------------- |
| `SPI_OPEN`  | spidev 없음            | raspi-config SPI, 재부팅      |
| `SPI_OPEN`  | Permission denied      | `usermod -aG spi,i2c,gpio $USER` |
| (저널 없음) | 출력이 비어 있음       | `adm` 그룹 아님. `sudo journalctl` 또는 `usermod -aG adm $USER` |
| `SPI_OPEN`  | No module named spidev | `requirements-pi.txt`         |
| `SENSOR_ID` | `DEVID_AD=0x00`        | MISO 핀21, CS 핀24, beginSPI  |
| `SENSOR_ID` | `DEVID_AD=0xFF`        | VCC 핀1, GND 핀25, 윗줄, 5 V  |
| `SENSOR_ID` | 그 외 ID               | MOSI/MISO 교차, CL-SCL/DA-SDA |
| `LCD_OPEN`  | I2C / no device        | 백팩 3.3 V 핀17, SDA/SCL      |
| `BUZZ_OPEN` | gpiozero / PWM         | 핀12 BCM18, KY-006 S, D8≠핀8  |
| `LCD_WRITE` | i2c timeout            | 커넥터 헐거움                 |
| `BUZZ_WRITE`| pwm timeout            | 핀12, 패시브, GND 핀14        |
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
sh scripts/install-service.sh
```

폰: `http://<pi-ip>:5000`.
