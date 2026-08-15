# 진동 측정기 구현 문서

기준 사양: `docs/prototype-spec.md`. 이 문서만 구현한다.

브랜치: `feat/vibration-meter` ← `main`. 커밋은 논리 단위로 나눈다.

## 1. 목표

Pi Zero 2 W에서 ADXL355B를 SPI로 읽고, 1초 RMS/피크를 1602와
모바일 웹(60초 RMS 그래프)에 표시한다. 부저·알람·저장은 없다.

개발 PC(macOS)에서는 하드웨어 없이 `pytest`와 `--mock`으로 검증한다.

## 2. 디렉터리

```
src/vibration_meter/   패키지
  convert.py           20-bit → g
  metrics.py           DC 제거, 축 선택, RMS/피크, 60점 버퍼
  adxl355.py           SPI 드라이버 (버스 주입)
  display.py           1602 문자열·출력
  collector.py         1초 창 수집
  webapp.py            Flask + SocketIO
  logutil.py           stderr 로그
  errors.py            [STAGE] FAIL/OK, 배선 HINT
  app.py               엔트리
src/vibration_meter/templates/index.html
tests/
deploy/vibration-meter.service
requirements.txt       PC·공통
requirements-pi.txt    + spidev
```

하드웨어 모듈(`spidev`, `RPLCD`)은 팩토리에서만 import 한다. 테스트와 mock은
주입된 버스로 동작한다.

## 3. 모듈 계약

### convert

- `bytes_to_raw20(msb, mid, lsb) -> int` : 20-bit two's complement.
  `(msb << 12) | (mid << 4) | (lsb >> 4)`, 부호 확장.
- `raw20_to_g(raw, lsb_per_g=64000.0) -> float` : ±8.192 g 스케일.

### metrics

- 창 안에서 축별 평균을 뺀 뒤 RMS·피크(|AC|)를 구한다.
  (중력 DC를 남기면 항상 Z≈1 g가 되어 진동 그래프가 무의미하다.)
- 축: 그 창에서 AC RMS가 가장 큰 축. 동점이면 X→Y→Z.
- `WindowMetrics(axis: str, rms_g: float, peak_g: float)`
- `RmsHistory(maxlen=60)` : 1 Hz 점, 최근 60초.

### adxl355

- SPI: 주소 전송 바이트 `(reg << 1) | 1`(읽기), `| 0`(쓰기). Mode 0.
- 버스: `/dev/spidev0.0`, 1 MHz.
- 기동: DEVID_AD `0x00` == `0xAD`. RANGE `0x2C` = `0x83` (±8 g).
  FILTER `0x28` = `0x02` (ODR 1000 Hz). POWER_CTL `0x2D` = `0x00` (측정).
- `read_xyz_g() -> tuple[float, float, float]`
- 테스트는 FakeSpi로 레지스터 맵을 흉내 낸다.

### display

- 1행 16자: `RMS 0.123 g`
- 2행 16자: `PK  0.456 g X`
- I2C 주소는 생성 인자. 기본 `0x27`, 실패 시 `0x3F`.
- 테스트는 포맷 함수만. LCD 객체는 프로토콜로 주입.

### collector

- 목표 1000 샘플/초, 1초마다 `WindowMetrics` 콜백.
- 실제 샘플 수가 부족해도 모은 샘플로 계산한다.
- `--mock`이면 합성 사인파(선택된 축에 AC).

### webapp

- `GET /` : 차트 페이지. 포트 5000.
- 이벤트 `reading`: `{t, rms_g, peak_g, axis, history: [{t, rms_g}, ...]}`
- `async_mode=threading` (Python 3.14·Pi 공통). Chart.js는 CDN.

### app

- 수집 스레드 → LCD + SocketIO.
- 로그: stderr, `[STAGE] OK` / `[STAGE] FAIL ... | HINT ...`. 코드표는
  `docs/logs.md`. 배선 HINT는 `docs/wiring.md`를 가리킨다.
- LCD 실패는 로그 후 웹만 유지. 센서 기동 실패는 exit 2.
- `python -m vibration_meter.app` / `--mock` / `--log-level INFO`

## 4. 테스트

PC에서 하드웨어 없이 돌린다.

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
```

필수 케이스:

- 20-bit 양수/음수 변환, 64000 LSB = 1 g
- DC 1 g + AC → RMS는 AC만, 축은 AC가 큰 쪽
- 60점 버퍼 길이 제한
- SPI 읽기 프레임·RANGE/FILTER/POWER 쓰기
- LCD 16자 정렬
- `GET /` 200, 템플릿에 Chart.js·socket.io
- `[STAGE] FAIL` 형식, DEVID 0x00/0xFF HINT, SAMPLE/LCD_WRITE 실패 로그

## 5. Pi 실행

```
sudo raspi-config   # SPI, I2C 활성
pip install -r requirements-pi.txt
cd /home/pi/Nalang && PYTHONPATH=src python3 -m vibration_meter.app
```

systemd: `deploy/vibration-meter.service`를 `/etc/systemd/system/`에 복사 후
`enable --now`. WorkingDirectory는 클론 경로.

폰: `http://<pi-ip>:5000`

## 6. 작업 단위

1. 저장소 초기화, `main`에 사양, `feat/vibration-meter` 생성
2. convert + metrics + 테스트
3. adxl355 + FakeSpi 테스트
4. display 포맷 테스트
5. collector + webapp + app + systemd + README
6. 전체 pytest

커밋 메시지: `feat:` / `test:` / `docs:` 왜 했는지만.
