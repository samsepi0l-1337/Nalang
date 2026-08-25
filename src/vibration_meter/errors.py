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
            "beginSPI처럼 CS를 CE0에 연결한다. SCLK/MISO를 GND에 묶는 I2C 배선은 쓰지 않는다. "
            "아두이노 D2는 Pi 핀2(5V)가 아니다. README 배선 표: MISO 핀21, CS 핀24."
        )
    if value == 0xFF:
        return (
            "VCC 3.3V(핀1)·GND(핀25) 또는 윗줄 미납땜. 센서에 5V 금지. "
            "README 배선 표: VCC 핀1, GND 핀25, 윗줄 납땜. 센서 5V 금지."
        )
    return (
        "MOSI(핀19)/MISO(핀21) 교차, CS가 CE0(핀24)인지, "
        "CL-SCL/DA-SDA를 쓰지 않았는지 확인. README 배선."
    )


HINT_SPI_MISSING = (
    "/dev/spidev0.0 없음. raspi-config에서 SPI Enable 후 재부팅. "
    "ls -l /dev/spidev0.0. README Pi 절."
)
HINT_SPI_PERM = (
    "sudo usermod -aG spi,i2c,gpio $USER 후 재로그인. README 로그 표."
)
HINT_SPIDEV_PKG = "Pi에서 pip install -r requirements-pi.txt (spidev). README Pi 절."
HINT_LCD = (
    "i2cdetect -y 1 에 0x27 또는 0x3F가 있는지 확인. "
    "SDA(핀3) SCL(핀5) GND(핀6) 백팩 VCC=3.3V(핀17, 5V 금지). README 배선 LCD."
)
HINT_SAMPLE = "센서 SPI 배선·납땜과 DEVID 로그를 확인. README 배선 센서."
HINT_LCD_WRITE = "I2C 커넥터·백팩 3.3V·주소 0x27/0x3F. README 배선 LCD."
HINT_BUZZ = (
    "패시브 KY-006: S→핀12(BCM 18), -→핀14 GND. "
    "아두이노 tone(8)의 8은 D8이지 Pi 핀8(TXD)이 아니다. "
    "KY-012 액티브는 쓰지 않는다. sudo usermod -aG gpio $USER. README 부저."
)
HINT_BUZZ_WRITE = "핀12 PWM·KY-006 S·패시브. README 부저."
HINT_RATE = (
    "표본 읽기가 창보다 오래 걸린다. --interval 을 늘려 창을 길게 잡는다. "
    "README 갱신 주기."
)
HINT_BUZZ_BUSY = (
    "BCM 18 을 이미 다른 프로세스가 쥐고 있다. 서비스가 도는 중이면 "
    "sudo systemctl stop vibration-meter 후 다시 실행한다."
)
HINT_WEB_BIND = (
    "그 포트를 이미 다른 프로세스가 쥐고 있다. 배선이 아니다. "
    "서비스가 도는 중이면 sudo systemctl stop vibration-meter, "
    "또는 --port 로 다른 포트를 준다. 기본 포트는 5000. README 로그 표."
)
