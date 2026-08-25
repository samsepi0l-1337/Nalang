import pytest

from vibration_meter.adxl355 import (
    DEVID_AD,
    FILTER,
    POWER_CTL,
    RANGE,
    Adxl355,
    Adxl355Error,
    spi_command,
)


class FakeSpi:
    def __init__(self, registers: dict[int, int] | None = None) -> None:
        self.registers = {i: 0 for i in range(0x40)}
        self.registers[DEVID_AD] = 0xAD
        self.registers[RANGE] = 0x81
        self.registers[POWER_CTL] = 0x01
        if registers:
            self.registers.update(registers)
        self.writes: list[tuple[int, int]] = []
        self.commands: list[int] = []

    def xfer2(self, data: list[int]) -> list[int]:
        cmd = data[0]
        self.commands.append(cmd)
        reg = cmd >> 1
        if cmd & 1:
            out = [0]
            for offset in range(len(data) - 1):
                out.append(self.registers.get(reg + offset, 0))
            return out
        value = data[1]
        self.registers[reg] = value
        self.writes.append((reg, value))
        return [0, 0]


def test_spi_command_matches_pl_adxl355():
    assert spi_command(DEVID_AD, True) == 0x01
    assert spi_command(RANGE, False) == (RANGE << 1)


def test_begin_configures_8g_1khz_measurement():
    spi = FakeSpi()
    Adxl355(spi).begin()
    assert spi.commands[0] == spi_command(DEVID_AD, True)
    assert spi.registers[RANGE] == 0x83
    assert spi.registers[FILTER] == 0x02
    assert spi.registers[POWER_CTL] == 0x00


def test_begin_rejects_wrong_device_id():
    spi = FakeSpi({DEVID_AD: 0x00})
    with pytest.raises(Adxl355Error) as caught:
        Adxl355(spi).begin()
    assert caught.value.stage == "SENSOR_ID"
    assert "0x00" in str(caught.value)
    assert "HINT" in str(caught.value)
    assert "MISO" in caught.value.hint
    assert "beginSPI" in caught.value.hint


def test_read_xyz_g_one_g_on_z():
    spi = FakeSpi()
    spi.registers[0x0E] = 0x0F
    spi.registers[0x0F] = 0xA0
    spi.registers[0x10] = 0x00
    sensor = Adxl355(spi)
    sensor.begin()
    x, y, z = sensor.read_xyz_g()
    assert abs(x) < 1e-6
    assert abs(y) < 1e-6
    assert abs(z - 1.0) < 1e-6


def test_begin_write_failure_is_sensor_cfg_not_sensor_id():
    # ID 읽기는 됐는데 설정 쓰기가 깨진 경우다. 단계를 뭉개면 로그만 보고
    # 둘을 가를 수 없다. README 로그 표도 4번과 5번을 나눠 둔다.
    class WriteFailsSpi(FakeSpi):
        def xfer2(self, data: list[int]) -> list[int]:
            if not data[0] & 1:
                raise OSError("spi write nak")
            return super().xfer2(data)

    with pytest.raises(Adxl355Error) as caught:
        Adxl355(WriteFailsSpi()).begin()
    assert caught.value.stage == "SENSOR_CFG"
    assert "spi write nak" in str(caught.value)
