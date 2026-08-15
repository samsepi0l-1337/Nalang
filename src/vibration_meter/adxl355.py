from typing import Protocol

from vibration_meter.convert import SCALE_8G, bytes_to_raw20, raw20_to_g

DEVID_AD = 0x00
RANGE = 0x2C
FILTER = 0x28
POWER_CTL = 0x2D
XDATA3 = 0x08

RANGE_8G = 0x83
ODR_1000HZ = 0x02
MEASURE = 0x00
EXPECTED_DEVID_AD = 0xAD


class SpiDevice(Protocol):
    def xfer2(self, data: list[int]) -> list[int]: ...


class Adxl355Error(RuntimeError):
    pass


class Adxl355:
    def __init__(self, spi: SpiDevice, lsb_per_g: float = SCALE_8G) -> None:
        self._spi = spi
        self._lsb_per_g = lsb_per_g

    def begin(self) -> None:
        device_id = self._read(DEVID_AD)
        if device_id != EXPECTED_DEVID_AD:
            raise Adxl355Error(f"unexpected DEVID_AD 0x{device_id:02X}")
        self._write(RANGE, RANGE_8G)
        self._write(FILTER, ODR_1000HZ)
        self._write(POWER_CTL, MEASURE)

    def read_xyz_g(self) -> tuple[float, float, float]:
        raw = self._read_bytes(XDATA3, 9)
        return (
            self._axis_g(raw[0:3]),
            self._axis_g(raw[3:6]),
            self._axis_g(raw[6:9]),
        )

    def _axis_g(self, data: list[int]) -> float:
        return raw20_to_g(bytes_to_raw20(data[0], data[1], data[2]), self._lsb_per_g)

    def _read(self, register: int) -> int:
        return self._read_bytes(register, 1)[0]

    def _read_bytes(self, register: int, count: int) -> list[int]:
        reply = self._spi.xfer2([(register << 1) | 1] + [0] * count)
        return reply[1:]

    def _write(self, register: int, value: int) -> None:
        self._spi.xfer2([(register << 1) | 0, value])
