# 로그로 실패 위치 말하기

모든 로그는 stderr. 형식:

```
2026-08-15 17:00:00,001 INFO [BOOT] OK mock=false host=0.0.0.0 port=5000
2026-08-15 17:00:00,020 ERROR [SENSOR_ID] FAIL DEVID_AD=0x00 expected=0xAD | HINT ...
```

스테이지 코드(`[BOOT]`, `[SENSOR_ID]`)만 말해도 된다. 배선 조치는
`docs/wiring.md`.

보기: `journalctl -u vibration-meter -f` 또는 포그라운드 실행 화면.

레벨: `--log-level INFO` (기본). SAMPLE은 1초마다 OK 한 줄.

## 기동 순서 (여기까지 찍히면 그 단계는 된 것)

| 순서 | 코드        | OK 의미                          |
| ---- | ----------- | -------------------------------- |
| 1    | `BOOT`      | 프로세스 시작                    |
| 2    | `MOCK`      | `--mock` 합성 센서 (SPI 없음)    |
| 3    | `SPI_OPEN`  | `/dev/spidev0.0` 열림            |
| 4    | `SENSOR_ID` | DEVID_AD=`0xAD`                  |
| 5    | `SENSOR_CFG`| ±8 g, 1000 Hz, 측정 모드         |
| 6    | `LCD_ADDR`  | 0x27 또는 0x3F 시도              |
| 7    | `LCD_OPEN`  | 1602 연결. 실패해도 웹은 계속    |
| 8    | `LOOP`      | 측정 스레드 시작                 |
| 9    | `WEB_BIND`  | 포트 5000                        |
| 10   | `SAMPLE`    | 1초 RMS 한 번 성공               |
| 11   | `LCD_WRITE` | 1602 갱신. 실패해도 웹은 계속    |

센서 기동 실패(`SPI_OPEN` / `SENSOR_ID`)는 종료 코드 2. LCD 실패는 종료하지
않는다.

## FAIL → 어디를 볼지

| 로그 코드     | 대표 메시지                    | 원인(우선순위)                                      | 문서            |
| ------------- | ------------------------------ | --------------------------------------------------- | --------------- |
| `SPI_OPEN`    | `/dev/spidev0.0` 없음          | SPI 미활성, 재부팅 안 함                            | wiring.md OS    |
| `SPI_OPEN`    | Permission denied              | 유저가 `spi` 그룹 아님                              | wiring.md OS    |
| `SPI_OPEN`    | No module named spidev         | `requirements-pi.txt` 미설치                        | README          |
| `SENSOR_ID`   | `DEVID_AD=0x00`                | MISO 단선, CS 핀24 아님, **아랫줄 미납땜**          | wiring.md 센서  |
| `SENSOR_ID`   | `DEVID_AD=0xFF`                | VCC/GND, 윗줄 미납땜, 5 V 오배선                    | wiring.md 전원  |
| `SENSOR_ID`   | 그 외 ID                       | MOSI/MISO 교차, 센서 I2C 핀을 Pi I2C에 연결         | wiring.md 센서  |
| `LCD_OPEN`    | No such device / I2C           | 백팩 3.3 V(핀17), SDA/SCL, 백팩 냉납                | wiring.md LCD   |
| `LCD_WRITE`   | i2c timeout                    | 커넥터 헐거움, 측정 중 접촉 불량                    | wiring.md LCD   |
| `SAMPLE`      | bus nak / timeout              | 기동은 됐으나 측정 중 SPI 단선                      | wiring.md 센서  |
| `WEB_BIND`    | Address already in use         | 5000 포트 점유. 소프트웨어. 배선 아님               | —               |

## 붙여 넣을 한 줄

원격에 보낼 때 FAIL 한 줄 전체를 복사한다.

```
[SENSOR_ID] FAIL DEVID_AD=0x00 expected=0xAD | HINT MISO(핀21)...
```

OK만 있고 SAMPLE이 없으면 측정 루프가 안 돈 것이다. LOOP/WEB_BIND 유무를
같이 본다.
