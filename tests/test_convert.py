from vibration_meter.convert import SCALE_8G, bytes_to_raw20, raw20_to_g


def test_bytes_to_raw20_positive():
    assert bytes_to_raw20(0x01, 0x00, 0x00) == 0x1000


def test_bytes_to_raw20_negative_one_lsb_nibble():
    assert bytes_to_raw20(0xFF, 0xFF, 0xF0) == -1


def test_raw20_to_g_one_g_at_8g_range():
    assert raw20_to_g(int(SCALE_8G), SCALE_8G) == 1.0


def test_raw20_to_g_negative():
    assert raw20_to_g(-int(SCALE_8G), SCALE_8G) == -1.0
