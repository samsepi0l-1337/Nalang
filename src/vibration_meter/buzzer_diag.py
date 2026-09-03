"""부저 자가 진단. 배선 문제인지 코드 문제인지 가른다.

    python -m vibration_meter.buzzer_diag

서비스가 도는 중이면 BCM 12 를 이미 쥐고 있어 열리지 않는다.
먼저 `sudo systemctl stop vibration-meter` 를 한다.
"""

import argparse
import logging
import time
from collections.abc import Callable

from vibration_meter.errors import (
    HINT_BUZZ_WRITE,
    format_fail,
    format_ok,
)
from vibration_meter.hardware import (
    BUZZER_BCM,
    BUZZER_PIN,
    TONE_HZ,
    BuzzerFactory,
    open_buzzer,
)
from vibration_meter.logutil import get_logger, setup_logging

# 세 음이 확실히 다르게 들리도록 한 옥타브씩 띄웠다.
SWEEP_HZ = (262, 523, 1047)
STEP_S = 0.6
GAP_S = 0.3
BEEP_COUNT = 3
BEEP_S = 0.3

VERDICT = (
    "판정표 — 위 로그와 실제로 들린 소리를 맞춰 본다",
    "1) [BUZZ_OPEN] FAIL      코드·권한·점유다. 배선이 아니다. "
    "서비스 정지, gpiozero 설치, gpio 그룹을 본다.",
    f"2) 열렸는데 무음         배선이다. S↔핀{BUZZER_PIN}(BCM {BUZZER_BCM}), −↔핀14 GND, 점퍼 접촉을 본다.",
    "3) 소리는 나되 음정 불변  부품이다. KY-012 액티브다. KY-006 패시브로 바꾼다.",
    "4) 음정이 3단 올라감      배선·코드 정상이다. 앱에서 안 울리면 이상치 판정 쪽이다.",
)


def _log_verdict() -> None:
    log = get_logger()
    for line in VERDICT:
        log.info("[BUZZ_DIAG] %s", line)


def run(
    create: BuzzerFactory | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """진단 순서를 돈다. 0 이면 순서를 끝까지 돌았다는 뜻이다."""
    log = get_logger()
    log.info(format_ok("BUZZ_DIAG", f"시작 BCM {BUZZER_BCM} 경보음 {TONE_HZ} Hz"))
    buzzer = open_buzzer(create=create)
    if buzzer is None:
        _log_verdict()
        return 2

    try:
        for hz in SWEEP_HZ:
            log.info(format_ok("BUZZ_TONE", f"{hz} Hz {STEP_S}초 — 음정이 올라가야 한다"))
            buzzer.play_hz(hz)
            sleep(STEP_S)
        buzzer.stop()
        sleep(GAP_S)
        # 여기서부터는 앱의 경보와 완전히 같은 경로다.
        for beat in range(1, BEEP_COUNT + 1):
            log.info(format_ok("BUZZ_ALERT", f"{beat}/{BEEP_COUNT} set_alert(True)"))
            buzzer.set_alert(True)
            sleep(BEEP_S)
            buzzer.set_alert(False)
            sleep(BEEP_S)
    except Exception as exc:
        log.error(format_fail("BUZZ_WRITE", str(exc), HINT_BUZZ_WRITE), exc_info=True)
        _log_verdict()
        return 2

    log.info(format_ok("BUZZ_DIAG", "순서 완료"))
    _log_verdict()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="부저 배선/코드 자가 진단")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args(argv)
    setup_logging(getattr(logging, args.log_level.upper(), logging.INFO))
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
