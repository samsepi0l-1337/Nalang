# 배선·납땜

사양 핀맵은 `docs/prototype-spec.md` 3절. 사진은
`docs/assets/adxl355-front.png`, `docs/assets/pi-zero-2w-gpio.png`.
로그 코드는 `docs/logs.md`.

전원 켜기 전에 이 문서를 끝까지 본다. **센서와 LCD 백팩에 5 V를 넣지 않는다.**

## 1. 납땜 전에

- 헤더는 전면 실크가 보이게 꽂는다.
- 동봉 7핀은 **윗줄 전용**. SPI 데이터는 아랫줄이라 **두 줄 모두** 납땜한다.
- 아랫줄 5홀(`DRDY`, `INT1`, `MISO`, `MOSI`, `CS`)에 5핀 헤더 또는 전선을 단다.
- 이번 빌드에서 납땜만 하고 전선은 빼 두는 핀: `CL-SCL`, `DA-SDA`, `SA0`,
  `INT2`, `DRDY`, `INT1`. 패드끼리 숏나지 않게만 본다.
- LCD I2C 백팩은 1602에 밀착 납땜. 핀 1개라도 뜨면 주소가 안 뜬다.

## 2. 납땜 품질

각 핀에 대해:

- 패드와 핀이 **shiny cone**(윤기 있는 원뿔). 뭉친 구슬, 크랙, 한쪽만 붙은
  냉납은 실패.
- 옆 패드와 **브리지 금지**. 특히 SPI 아랫줄 `MISO`-`MOSI`-`CS`.
- 전선은 스트랜드가 패드 밖으로 튀지 않게. 3.3 V와 GND가 붙으면 Pi·센서 손상.
- 돋보기 또는 휴대폰 접사로 전면·후면을 찍어서 보관하면 원격 소통이 쉽다.

## 3. 연결표 (반드시 이 핀)

GPIO 17(핀 11) “Chip Enable”은 쓰지 않는다. CS는 **핀 24**.

### 센서 ADXL355B → Pi Zero 2 W

| 센서 실크 | 줄    | Pi 물리 핀 | 신호        | 빠지면 나오는 로그      |
| --------- | ----- | ---------- | ----------- | ----------------------- |
| VCC       | 윗줄  | 1          | 3.3 V       | `SENSOR_ID` `0xFF`      |
| GND       | 윗줄  | 25         | GND         | `SENSOR_ID` `0xFF`      |
| SCK       | 윗줄  | 23         | SPI0 SCLK   | `SENSOR_ID` `0x00`/`0xFF` |
| MOSI      | 아랫줄 | 19        | SPI0 MOSI   | `SENSOR_ID` 이상한 ID   |
| MISO      | 아랫줄 | 21        | SPI0 MISO   | `SENSOR_ID` `0x00`      |
| CS        | 아랫줄 | 24        | SPI0 CE0    | `SENSOR_ID` `0x00`      |

센서 `CL-SCL` / `DA-SDA` / `SA0`는 **LCD I2C(핀 3·5)에 연결하지 않는다.**

### LCD 1602 I2C 백팩 → Pi

| 백팩 | Pi 물리 핀 | 신호     | 빠지면 나오는 로그 |
| ---- | ---------- | -------- | ------------------ |
| VCC  | 17         | 3.3 V    | `LCD_OPEN`         |
| GND  | 6          | GND      | `LCD_OPEN`         |
| SDA  | 3          | I2C1 SDA | `LCD_OPEN`         |
| SCL  | 5          | I2C1 SCL | `LCD_OPEN`         |

백팩 VCC를 핀 2·4(5 V)에 넣지 않는다. SDA/SCL이 5 V로 뜨면 Pi GPIO가 죽는다.

## 4. 납땜 후 전원 넣기 전

멀티미터 연속성(비프):

1. 센서 VCC ↔ Pi 핀 1, 센서 GND ↔ Pi 핀 25.
2. SCK/MOSI/MISO/CS 각각 표의 Pi 핀.
3. **핀 1(3.3 V)과 핀 25(GND) 사이는 비프가 나면 숏. 전원 금지.**
4. LCD VCC ↔ 핀 17, GND ↔ 핀 6, SDA ↔ 핀 3, SCL ↔ 핀 5.
5. LCD VCC와 5 V(핀 2)는 통하면 안 된다.

## 5. 전원 넣은 뒤 OS 확인

```
ls -l /dev/spidev0.0
sudo i2cdetect -y 1
```

- `spidev0.0` 없음 → SPI 미활성. 로그 `SPI_OPEN`. `raspi-config` Interface → SPI.
- `i2cdetect`가 전부 `--` → LCD 배선/3.3 V/백팩 납땜. 로그 `LCD_OPEN`.
- `0x27` 또는 `0x3F` 하나면 LCD 버스는 된 것.

## 6. 제작자·개발자 소통용 사진

문제 보고 시 아래를 같이 보낸다.

1. 센서 전면(실크와 납땜).
2. 센서 아랫줄 확대(MISO/MOSI/CS).
3. Pi 40핀에 꽂힌 점퍼 전체.
4. LCD 백팩 VCC가 어느 핀인지.
5. 로그 중 `[STAGE] FAIL` 한 줄 (`docs/logs.md`).
