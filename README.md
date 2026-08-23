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

### 부저가 안 울릴 때 (배선인지 코드인지)

서비스가 BCM 18을 쥐고 있으면 진단이 열리지 않는다. **먼저 멈춘다.**

```
sudo systemctl stop vibration-meter
PYTHONPATH=src .venv/bin/python -m vibration_meter.buzzer_diag
sudo systemctl start vibration-meter
```

262 → 523 → 1047 Hz를 0.6초씩 울린 뒤, 앱 경보와 **같은** `set_alert` 경로로 1 kHz를 세 번 끊어 낸다. 들린 소리를 로그와 맞춘다.

| 들린 것 | 원인 | 볼 곳 |
| ------- | ---- | ----- |
| `[BUZZ_OPEN] FAIL` | 코드·권한·점유. **배선이 아니다** | 서비스 정지, `pip install -r requirements-pi.txt`, `usermod -aG gpio $USER` |
| `[BUZZ_WRITE] FAIL` | 열린 뒤 PWM 거절 | 음역(`BUZZ_OPEN` 줄에 찍힌다) 밖 주파수이거나 핀12 PWM 충돌 |
| 열렸는데 무음 | 배선 | S↔핀12(BCM 18), −↔핀14, 점퍼 접촉 |
| 소리는 나되 음정 불변 | 부품 | KY-012 액티브다. KY-006 패시브로 바꾼다 |
| 음정이 3단 올라감 | 배선·코드 정상 | 앱에서만 안 울리면 이상치 판정 쪽(`ALERT` 로그) |

`--mock`은 부저를 열지 않으므로 이 진단으로만 확인된다.

`TonalBuzzer`는 `mid_tone` 기준 ±`octaves`만 낸다. gpiozero 기본값 A4·1옥타브는 **220~880 Hz**라 1 kHz 경보음이 범위 밖이다. 그래서 2옥타브(110~1760 Hz)로 연다. 음역은 `BUZZ_OPEN` 로그에 찍힌다.

### 납땜

- 헤더는 전면 실크가 보이게. 아랫줄 5홀에도 헤더 또는 전선.
- 이번 빌드에서 전선을 빼 두는 핀: `CL-SCL`, `DA-SDA`, `SA0`, `INT2`, `DRDY`,
  `INT1`. 숏만 피한다.
- LCD 백팩은 1602에 밀착. 핀 하나라도 뜨면 주소가 안 뜬다.
- 윤기 있는 원뿔 납땜. `MISO`-`MOSI`-`CS` 브리지 금지.
- 3.3 V와 GND가 붙으면 전원 금지.

전원 넣기 전 연속성: 센서 VCC↔핀1, GND↔핀25, SCK/MOSI/MISO/CS↔표의 핀. **핀1과 핀25가 통하면 숏.** LCD VCC↔17, GND↔6, SDA↔3, SCL↔5. LCD VCC와 5 V(핀2)는 통하면 안 된다. 부저 S↔핀12, −↔핀14. 부저 S와 5 V(핀2)는 통하면 안 된다.

문제 보고 시: 센서 전면, 아랫줄(MISO/MOSI/CS) 확대, Pi 점퍼 전체, LCD 백팩 VCC가 어느 핀인지, 부저 S가 핀 12인지, 로그 `[STAGE] FAIL` 한 줄. 부저 건이면 `PYTHONPATH=src .venv/bin/python -m vibration_meter.buzzer_diag` 출력 전체와 **실제로 들린 소리**를 같이 보낸다. 로그만으로는 2번과 4번을 가를 수 없다.

## 측정

- ODR 1000 Hz, ±8.192 g. 창 하나에서 축별 평균(중력 DC)을 뺀 뒤 RMS·피크.
- 축: 그 창에서 AC RMS가 가장 큰 축. 동점이면 X→Y→Z.
- **갱신 주기 = 창 길이.** 기본 0.2초(초당 5회). `--interval`로 바꾼다. 표본 수는 ODR × 창이라 0.2초면 200개다.
- 최소 0.1초. 그보다 짧으면 20 Hz 진동이 창에 두 주기도 안 들어가 RMS가 요동친다. 짧게 주면 `[BOOT] FAIL`로 막고 종료 코드 2.
- 1602는 최대 0.5초에 한 번만 쓴다. I2C로 32자 미는 데 수십 ms가 들어 매 창 쓰면 측정 시간을 갉아먹는다. **이상치 전환은 이 제한을 무시하고 즉시 뜬다.**
- 이상치 표시: 직전 창 RMS 평균 대비 |Δ|≥5%가 **연속 5초**, 또는 |Δ|≥10%로 **급변**. 기준 10초 미만은 판정하지 않음. 걸리면 2행 `OUTLIER        X`, 패시브 부저 1 kHz (`tone()`).
- 위 5초·10초·60초는 **초**다. 창 길이가 바뀌면 창 개수로 환산한다(0.2초 창이면 연속 25창). 갱신을 빨리해도 판정 기준은 그대로다.
- 폰: 포트 5000, 최근 60초 RMS 그래프. 원시 파형은 보내지 않는다.

스택: Python 3, `spidev`, `RPLCD`+`smbus2`, `gpiozero` `TonalBuzzer`, `numpy`, `Flask`+`Flask-SocketIO` (threading), Chart.js CDN. SPI `/dev/spidev0.0` 1 MHz mode 0. DEVID_AD=`0xAD`, RANGE=`0x83`, FILTER=`0x02`, POWER_CTL=`0x00`. 부저 BCM 18, 1000 Hz.

## 로그

stderr. 형식: `[SENSOR_ID] FAIL DEVID_AD=0x00 expected=0xAD | HINT ...`

`journalctl -u vibration-meter -f`. 또는 `sh scripts/collect-logs.sh`. `--log-level INFO`. SAMPLE은 창마다 OK(기본 0.2초).

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
| 11   | `SAMPLE`     | 창 하나 RMS 성공            |
| 12   | `ALERT`      | 지속 이상치 on/off          |
| 13   | `LCD_WRITE`  | 1602 갱신. 실패해도 웹 계속 |
| 14   | `BUZZ_WRITE` | 부저. 실패해도 웹 계속      |

`RATE`는 부팅 때 창·표본·판정 창수를 한 줄로 남긴다. 읽기가 창보다 오래 걸리면 `[RATE] FAIL`, 따라잡으면 `[RATE] OK`. 상태가 바뀔 때만 남기므로 매 창 뜨지 않는다.

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
