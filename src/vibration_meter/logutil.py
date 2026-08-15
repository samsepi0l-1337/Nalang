import logging
import sys

LOGGER_NAME = "vibration_meter"


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    log = logging.getLogger(LOGGER_NAME)
    log.setLevel(level)
    return log


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
