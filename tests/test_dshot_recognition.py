"""Tests for DShot signature recognition + frame decode (measure/dshot.py)."""

import pytest

from slidko.measure import dshot
from tests.synth import SimpleDShotGenerator, SimpleUARTGenerator


@pytest.mark.parametrize("rate", [150, 300, 600])
def test_recognize_rate_matches_ground_truth(rate):
    capture, ground_truth = SimpleDShotGenerator(rate=rate, value=1200).generate()
    recognized_rate, confidence = dshot.recognize_rate(
        capture.channels["dshot"], capture.samplerate_hz
    )
    assert recognized_rate == ground_truth.parameters["rate"]
    assert confidence >= 0.9


@pytest.mark.parametrize("rate", [150, 300, 600])
@pytest.mark.parametrize(
    ("value", "telemetry"), [(0, False), (1000, False), (2047, True), (48, True)]
)
def test_decode_frame_recovers_value_and_checksum(rate, value, telemetry):
    capture, ground_truth = SimpleDShotGenerator(
        rate=rate, value=value, telemetry=telemetry
    ).generate()
    decoded_value, decoded_telemetry, checksum_ok = dshot.decode_frame(
        capture.channels["dshot"], capture.samplerate_hz, rate
    )
    assert decoded_value == value
    assert decoded_telemetry == telemetry
    assert checksum_ok is True
    assert ground_truth.parameters["value"] == value


def test_does_not_recognize_uart_as_dshot():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA]).generate()
    _recognized_rate, confidence = dshot.recognize_rate(
        capture.channels["ch0"], capture.samplerate_hz
    )
    assert confidence < 0.9
