SCALE_8G = 64000.0


def bytes_to_raw20(msb: int, mid: int, lsb: int) -> int:
    raw = (msb << 12) | (mid << 4) | (lsb >> 4)
    if raw & 0x80000:
        return raw - 0x100000
    return raw


def raw20_to_g(raw: int, lsb_per_g: float = SCALE_8G) -> float:
    return raw / lsb_per_g
