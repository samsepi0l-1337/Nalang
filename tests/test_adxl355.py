import pytest

from vibration_meter.adxl355 import (
    DEVID_AD,
    FILTER,
    POWER_CTL,
    RANGE,
    Adxl355,
    Adxl355Error,
)


class FakeSpi:
    def __init__(self, registers: dict[int, int] | None = None) -> None:
        self.registers = {i: 0 for i in range(0x40)}
        self.registers[DEVID_AD] = 0xAD
        if registers:
            self.registers.update(registers)
        self.writes: list[tuple[int, int]] = []

    def xfer2(self, data: list[int]) -> list[int]:
        cmd = data[0]
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


def test_begin_configures_8g_1khz_measurement():
    spi = FakeSpi()
    Adxl355(spi).begin()
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
