"""Tests for the analog-video recognition stub (measure/analog_video.py)."""

import numpy as np

from slidko.measure import analog_video
from tests.synth import SimpleUARTGenerator, expand_segments

SAMPLE_RATE_HZ = 24_000_000


def _sync_pulse_train(
    line_hz: float, cycles: int = 20, sync_us: float = 4.7
) -> np.ndarray:
    period_samples = round(SAMPLE_RATE_HZ / line_hz)
    sync_samples = round(sync_us * 1e-6 * SAMPLE_RATE_HZ)
    segments = []
    for _ in range(cycles):
        segments.append((False, sync_samples))
        segments.append((True, period_samples - sync_samples))
    return expand_segments(segments)


def test_recognizes_ntsc_line_rate_sync_train():
    channel = _sync_pulse_train(analog_video.NTSC_LINE_HZ)
    recognized, confidence = analog_video.recognize(channel, SAMPLE_RATE_HZ)
    assert recognized is True
    assert confidence > 0.0


def test_recognizes_pal_line_rate_sync_train():
    channel = _sync_pulse_train(analog_video.PAL_LINE_HZ)
    recognized, confidence = analog_video.recognize(channel, SAMPLE_RATE_HZ)
    assert recognized is True
    assert confidence > 0.0


def test_does_not_recognize_uart_as_analog_video():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x3C]).generate()
    recognized, _confidence = analog_video.recognize(
        capture.channels["ch0"], capture.samplerate_hz
    )
    assert recognized is False
