from typing import Protocol

from vibration_meter.convert import SCALE_8G, bytes_to_raw20, raw20_to_g
from vibration_meter.errors import HardwareError, format_ok, hint_for_devid
from vibration_meter.logutil import get_logger

DEVID_AD = 0x00
RANGE = 0x2C
FILTER = 0x28
POWER_CTL = 0x2D
XDATA3 = 0x08

RANGE_MASK = 0x03
RANGE_8G_SEL = 0x03
FILTER_ODR_MASK = 0x0F
ODR_1000HZ = 0x02
STANDBY = 0x01
RANGE_8G = 0x83
EXPECTED_DEVID_AD = 0xAD
SPI_READ = 1


class SpiDevice(Protocol):
    def xfer2(self, data: list[int]) -> list[int]: ...


class Adxl355Error(HardwareError):
    pass


def spi_command(register: int, read: bool) -> int:
    return (register << 1) | (SPI_READ if read else 0)


class Adxl355:
    def __init__(self, spi: SpiDevice, lsb_per_g: float = SCALE_8G) -> None:
        self._spi = spi
        self._lsb_per_g = lsb_per_g

    def begin(self) -> None:
        log = get_logger()
        device_id = self._read(DEVID_AD)
        if device_id != EXPECTED_DEVID_AD:
            raise Adxl355Error(
                "SENSOR_ID",
                f"DEVID_AD=0x{device_id:02X} expected=0xAD",
                hint_for_devid(device_id),
            )
        log.info(format_ok("SENSOR_ID", "DEVID_AD=0xAD"))
        self.set_range_8g()
        self.set_odr_1000hz()
        self.enable_measurement()
        log.info(
            format_ok(
                "SENSOR_CFG",
                f"RANGE=0x{RANGE_8G:02X} FILTER=0x{ODR_1000HZ:02X} POWER=0x00",
            )
        )

    def set_range_8g(self) -> None:
        current = self._read(RANGE)
        self._write(RANGE, (current & ~RANGE_MASK) | RANGE_8G_SEL)

    def set_odr_1000hz(self) -> None:
        current = self._read(FILTER)
        self._write(FILTER, (current & ~FILTER_ODR_MASK) | ODR_1000HZ)

    def enable_measurement(self) -> None:
        current = self._read(POWER_CTL)
        self._write(POWER_CTL, current & ~STANDBY)

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
        reply = self._spi.xfer2([spi_command(register, True)] + [0] * count)
        return reply[1:]

    def _write(self, register: int, value: int) -> None:
        self._spi.xfer2([spi_command(register, False), value])
