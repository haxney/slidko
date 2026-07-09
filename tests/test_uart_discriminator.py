"""Tests for UART auto-baud (measure/uart.py) against synthetic ground truth."""

import numpy as np
import pytest

from slidko.measure.uart import (
    DEFAULT_FRAME,
    SBUS_FRAME,
    detect_idle_level,
    infer_uart,
)
from tests.synth import SimpleUARTGenerator, byte_bits_lsb_first, expand_segments

STANDARD_TEST_BAUDS = [1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200, 230400]


@pytest.mark.parametrize("baud", STANDARD_TEST_BAUDS)
def test_infer_uart_exact_on_standard_bauds(baud):
    payload = [0x00, 0xFF, 0x55, 0xAA, 0x3C, 0x81]
    capture, ground_truth = SimpleUARTGenerator(baud=baud, payload=payload).generate()

    result = infer_uart(capture.channels["ch0"], capture.samplerate_hz)

    assert result.baud == ground_truth.parameters["baud"]
    assert result.frame == DEFAULT_FRAME
    assert result.confidence >= 0.9


def test_infer_uart_exact_on_sbus():
    payload = [0x0F, 0xF0, 0x3C, 0x99]
    capture, ground_truth = SimpleUARTGenerator.sbus(payload=payload).generate()

    result = infer_uart(capture.channels["ch0"], capture.samplerate_hz)

    assert result.baud == ground_truth.parameters["baud"]
    assert result.frame == SBUS_FRAME
    assert result.confidence >= 0.9


def test_detect_idle_level_high():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA]).generate()
    assert detect_idle_level(capture.channels["ch0"]) is True


def _jittered_uart_channel(baud, payload, jitter_frac, sample_rate=24_000_000, seed=1):
    """Ad-hoc per-bit timing jitter, local to this test only. Superseded by
    the general fault-injection system landing in tasks.md 1.7."""
    rng = np.random.default_rng(seed)
    nominal = sample_rate / baud

    def period():
        return max(1, round(nominal * (1 + rng.uniform(-jitter_frac, jitter_frac))))

    segments = [(True, round(nominal) * 4)]
    for byte in payload:
        segments.append((False, period()))
        for bit in byte_bits_lsb_first(byte, 8):
            segments.append((bit, period()))
        segments.append((True, period()))
        segments.append((True, round(nominal) * 3))
    segments.append((True, round(nominal) * 4))
    return expand_segments(segments)


def test_confidence_degrades_under_jitter_never_wrong_but_confident():
    baud = 9600
    payload = [0x00, 0xFF, 0x55, 0xAA, 0x3C, 0x81, 0x18, 0x27]
    clean_capture, _ = SimpleUARTGenerator(baud=baud, payload=payload).generate()
    clean_result = infer_uart(
        clean_capture.channels["ch0"], clean_capture.samplerate_hz
    )
    assert clean_result.baud == baud
    assert clean_result.confidence >= 0.9

    jittered_channel = _jittered_uart_channel(baud, payload, jitter_frac=0.12)
    jittered_result = infer_uart(jittered_channel, 24_000_000)

    if jittered_result.baud != baud:
        assert jittered_result.confidence < 0.5
    else:
        assert jittered_result.confidence < clean_result.confidence
