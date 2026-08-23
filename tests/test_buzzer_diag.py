import logging

import pytest

from vibration_meter.buzzer_diag import BEEP_COUNT, SWEEP_HZ, main, run
from vibration_meter.hardware import TONE_HZ, ToneBuzzer


class FakeDevice:
    """gpiozero TonalBuzzer 자리. 실제로 어떤 음이 갔는지 남긴다."""

    def __init__(self, fail_on_play: bool = False) -> None:
        self.fail_on_play = fail_on_play
        self.played: list[float] = []
        self.stops = 0

    def play(self, tone) -> None:
        if self.fail_on_play:
            raise OSError("pwm timeout")
        self.played.append(tone)

    def stop(self) -> None:
        self.stops += 1


def buzzer_with(device: FakeDevice) -> ToneBuzzer:
    # Tone.from_frequency 자리에 항등 함수를 둬서 주파수를 그대로 본다.
    return ToneBuzzer(device, lambda hz: hz)


def test_run_sweeps_three_tones_then_beeps_alert_path():
    device = FakeDevice()
    code = run(create=lambda: buzzer_with(device), sleep=lambda _s: None)
    assert code == 0
    # 스윕 3음 + 경보 3회. 경보는 앱과 같은 set_alert 경로다.
    assert device.played[: len(SWEEP_HZ)] == list(SWEEP_HZ)
    assert device.played[len(SWEEP_HZ) :] == [TONE_HZ] * BEEP_COUNT


def test_sweep_uses_distinct_rising_tones():
    # 음정이 안 변하면 KY-012 액티브를 가려낼 수 없다. 진단의 핵심 단서다.
    assert len(set(SWEEP_HZ)) == len(SWEEP_HZ)
    assert list(SWEEP_HZ) == sorted(SWEEP_HZ)


def test_open_failure_returns_two_and_prints_verdict(caplog):
    caplog.set_level(logging.INFO)

    def boom():
        raise OSError("No such device")

    code = run(create=boom, sleep=lambda _s: None)
    assert code == 2
    assert any("[BUZZ_OPEN] FAIL" in rec.message for rec in caplog.records)
    assert any("판정표" in rec.getMessage() for rec in caplog.records)


def test_write_failure_is_reported_and_still_prints_verdict(caplog):
    caplog.set_level(logging.INFO)
    device = FakeDevice(fail_on_play=True)
    code = run(create=lambda: buzzer_with(device), sleep=lambda _s: None)
    assert code == 2
    assert any("[BUZZ_WRITE] FAIL" in rec.message for rec in caplog.records)
    assert any("판정표" in rec.getMessage() for rec in caplog.records)


def test_verdict_names_wiring_and_code_branches(caplog):
    caplog.set_level(logging.INFO)
    run(create=lambda: buzzer_with(FakeDevice()), sleep=lambda _s: None)
    text = "\n".join(rec.getMessage() for rec in caplog.records)
    assert "배선" in text
    assert "KY-012" in text
    assert "핀12" in text


@pytest.mark.parametrize("hz", SWEEP_HZ)
def test_tone_buzzer_play_hz_passes_frequency_through(hz):
    device = FakeDevice()
    buzzer_with(device).play_hz(hz)
    assert device.played == [hz]


def test_main_wires_argv_to_run_and_returns_its_code(monkeypatch):
    # CLI 자체가 도는지 본다. 진단이 import 에러로 죽으면 아무 판정도 못 한다.
    monkeypatch.setattr("vibration_meter.buzzer_diag.run", lambda: 2)
    assert main(["--log-level", "DEBUG"]) == 2


def test_alert_path_survives_a_preceding_sweep():
    # play_hz 가 내부 상태를 켜 둔 채 끝나면 set_alert(True) 가 조용히 무시된다.
    device = FakeDevice()
    buzzer = buzzer_with(device)
    buzzer.play_hz(SWEEP_HZ[0])
    buzzer.stop()
    buzzer.set_alert(True)
    assert device.played[-1] == TONE_HZ
