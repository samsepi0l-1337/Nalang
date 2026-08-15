class HardwareError(RuntimeError):
    def __init__(self, stage: str, message: str, hint: str) -> None:
        self.stage = stage
        self.message = message
        self.hint = hint
        super().__init__(format_fail(stage, message, hint))


def format_fail(stage: str, message: str, hint: str) -> str:
    return f"[{stage}] FAIL {message} | HINT {hint}"


def format_ok(stage: str, message: str) -> str:
    return f"[{stage}] OK {message}"


def hint_for_devid(value: int) -> str:
    if value == 0x00:
        return (
            "MISO(핀21) 단선, CS(핀24) 미연결, 또는 아랫줄(MISO/MOSI/CS) 미납땜. "
            "README 배선 표: MISO 핀21, CS 핀24, 아랫줄 납땜."
        )
    if value == 0xFF:
        return (
            "VCC 3.3V(핀1)·GND(핀25) 또는 윗줄 미납땜. 센서에 5V 금지. "
            "README 배선 표: VCC 핀1, GND 핀25, 윗줄 납땜. 센서 5V 금지."
        )
    return (
        "MOSI(핀19)/MISO(핀21) 교차, CS가 CE0(핀24)인지, "
        "센서 I2C 핀을 Pi I2C에 붙이지 않았는지 확인. README 배선."
    )


HINT_SPI_MISSING = (
    "/dev/spidev0.0 없음. raspi-config에서 SPI Enable 후 재부팅. "
    "ls -l /dev/spidev0.0. README Pi 절."
)
HINT_SPI_PERM = "sudo usermod -aG spi,i2c $USER 후 재로그인. README 로그 표."
HINT_SPIDEV_PKG = "Pi에서 pip install -r requirements-pi.txt (spidev). README Pi 절."
HINT_LCD = (
    "i2cdetect -y 1 에 0x27 또는 0x3F가 있는지 확인. "
    "SDA(핀3) SCL(핀5) GND(핀6) 백팩 VCC=3.3V(핀17, 5V 금지). README 배선 LCD."
)
HINT_SAMPLE = "센서 SPI 배선·납땜과 DEVID 로그를 확인. README 배선 센서."
HINT_LCD_WRITE = "I2C 커넥터·백팩 3.3V·주소 0x27/0x3F. README 배선 LCD."
