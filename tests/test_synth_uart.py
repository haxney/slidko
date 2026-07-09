"""Tests for the synthetic UART generator (tests/synth.py)."""

import numpy as np
import pytest

from tests.synth import SimpleUARTGenerator

STANDARD_TEST_BAUDS = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]


def _decode_uart_bytes(
    channel: np.ndarray,
    bit_samples: int,
    data_bits: int,
    parity: str,
    stop_bits: float,
) -> list[int]:
    """Minimal reference UART decoder used only to verify generator timing."""
    n = len(channel)
    bytes_out: list[int] = []
    i = 0
    while i < n - 1:
        if channel[i] and not channel[i + 1]:
            start = i + 1
            mid_offset = bit_samples // 2
            if start + mid_offset >= n or channel[start + mid_offset]:
                i += 1
                continue
            value = 0
            base = start + bit_samples
            for bit_idx in range(data_bits):
                sample_idx = base + bit_idx * bit_samples + mid_offset
                if sample_idx < n and channel[sample_idx]:
                    value |= 1 << bit_idx
            bytes_out.append(value)
            frame_bits = (
                1 + data_bits + (0 if parity == "none" else 1) + round(stop_bits)
            )
            i = start + frame_bits * bit_samples
        else:
            i += 1
    return bytes_out


@pytest.mark.parametrize("baud", STANDARD_TEST_BAUDS)
def test_uart_frame_timing_matches_baud(baud):
    payload = [0x00, 0xFF, 0x55, 0xAA, 0x41]
    capture, ground_truth = SimpleUARTGenerator(baud=baud, payload=payload).generate()

    channel = capture.channels["ch0"]
    bit_samples = ground_truth.parameters["bit_samples"]

    decoded = _decode_uart_bytes(
        channel, bit_samples, data_bits=8, parity="none", stop_bits=1.0
    )
    assert decoded == payload


def test_uart_sbus_frame_roundtrip():
    payload = [0x0F, 0xF0, 0x3C]
    capture, ground_truth = SimpleUARTGenerator.sbus(payload=payload).generate()

    assert ground_truth.parameters["baud"] == 100_000
    assert ground_truth.parameters["parity"] == "even"
    assert ground_truth.parameters["stop_bits"] == pytest.approx(2.0)

    channel = capture.channels["ch0"]
    bit_samples = ground_truth.parameters["bit_samples"]
    decoded = _decode_uart_bytes(
        channel, bit_samples, data_bits=8, parity="even", stop_bits=2.0
    )
    assert decoded == payload


def test_uart_idle_is_high():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55]).generate()
    channel = capture.channels["ch0"]
    assert bool(channel[0]) is True
    assert bool(channel[-1]) is True


def test_uart_ground_truth_is_self_describing():
    payload = [0x12, 0x34]
    _, ground_truth = SimpleUARTGenerator(baud=19200, payload=payload).generate()
    assert ground_truth.protocol == "UART"
    assert ground_truth.parameters["baud"] == 19200
    assert ground_truth.payload == payload
