"""Tests for the synthetic SPI generator (tests/synth.py)."""

import pytest

from tests.synth import SimpleSPIGenerator


def _decode_spi(sck, mosi, cpol, cpha, num_bits):
    """Minimal reference SPI decoder used only to verify generator correctness."""
    clock_idle = bool(cpol)
    sample_on_leading = cpha == 0
    bits: list[bool] = []
    prev = clock_idle
    for i in range(1, len(sck)):
        level = bool(sck[i])
        if level != prev:
            is_leading = level != clock_idle
            if is_leading == sample_on_leading:
                bits.append(bool(mosi[i]))
        prev = level
    value = 0
    for b in bits[:num_bits]:
        value = (value << 1) | int(b)
    return value, bits


@pytest.mark.parametrize(("cpol", "cpha"), [(0, 0), (0, 1), (1, 0), (1, 1)])
def test_spi_all_modes_recover_payload(cpol, cpha):
    payload = [0xA5]
    capture, ground_truth = SimpleSPIGenerator(
        cpol=cpol, cpha=cpha, payload=payload
    ).generate()

    sck = capture.channels["sck"]
    mosi = capture.channels["mosi"]
    cs = capture.channels["cs"]

    decoded, bits = _decode_spi(sck, mosi, cpol, cpha, num_bits=8)
    assert len(bits) == 8
    assert decoded == payload[0]

    assert bool(cs[0]) is True
    assert bool(cs[-1]) is True
    assert bool(cs[len(cs) // 2]) is False

    assert bool(sck[0]) == bool(cpol)
    assert bool(sck[-1]) == bool(cpol)
    assert ground_truth.parameters["cpol"] == cpol
    assert ground_truth.parameters["cpha"] == cpha


def test_spi_multi_byte_burst_recovers_all_bytes():
    payload = [0x12, 0x34, 0x56]
    capture, _ = SimpleSPIGenerator(cpol=0, cpha=0, payload=payload).generate()
    sck = capture.channels["sck"]
    mosi = capture.channels["mosi"]

    _, bits = _decode_spi(sck, mosi, cpol=0, cpha=0, num_bits=len(payload) * 8)
    assert len(bits) == len(payload) * 8
    decoded_bytes = []
    for i in range(0, len(bits), 8):
        value = 0
        for b in bits[i : i + 8]:
            value = (value << 1) | int(b)
        decoded_bytes.append(value)
    assert decoded_bytes == payload
