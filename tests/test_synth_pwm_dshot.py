"""Tests for the synthetic PWM/servo and DShot generators (tests/synth.py)."""

from itertools import pairwise

import pytest

from tests.synth import (
    DSHOT_TIMING_NS,
    SimpleDShotGenerator,
    SimplePWMGenerator,
    dshot_checksum,
)


def test_pwm_pulse_width_matches_ground_truth():
    capture, ground_truth = SimplePWMGenerator(
        freq_hz=50, pulse_us=1500, num_pulses=4
    ).generate()
    channel = capture.channels["pwm"]

    rising = [
        i + 1 for i in range(len(channel) - 1) if not channel[i] and channel[i + 1]
    ]
    assert len(rising) == 4

    pulse_samples = ground_truth.parameters["pulse_samples"]
    for start in rising:
        end = start
        while end < len(channel) and channel[end]:
            end += 1
        assert end - start == pulse_samples


def test_pwm_period_matches_frequency():
    capture, ground_truth = SimplePWMGenerator(
        freq_hz=50, pulse_us=1000, num_pulses=3
    ).generate()
    channel = capture.channels["pwm"]
    rising = [
        i + 1 for i in range(len(channel) - 1) if not channel[i] and channel[i + 1]
    ]
    period_samples = ground_truth.parameters["period_samples"]
    for a, b in pairwise(rising):
        assert b - a == period_samples


def _decode_dshot(channel, t0h_samples, t1h_samples):
    rising = [
        i + 1 for i in range(len(channel) - 1) if not channel[i] and channel[i + 1]
    ]
    threshold = (t0h_samples + t1h_samples) / 2
    bits = []
    for start in rising:
        end = start
        while end < len(channel) and channel[end]:
            end += 1
        bits.append((end - start) > threshold)
    return bits


@pytest.mark.parametrize("rate", [150, 300, 600])
def test_dshot_bit_timing_matches_spec_table(rate):
    capture, ground_truth = SimpleDShotGenerator(rate=rate, value=1000).generate()
    sample_ns = 1e9 / capture.samplerate_hz
    timing = DSHOT_TIMING_NS[rate]

    assert ground_truth.parameters["bit_period_samples"] * sample_ns == pytest.approx(
        timing["bit_period_ns"], abs=sample_ns
    )
    assert ground_truth.parameters["t0h_samples"] * sample_ns == pytest.approx(
        timing["t0h_ns"], abs=sample_ns
    )
    assert ground_truth.parameters["t1h_samples"] * sample_ns == pytest.approx(
        timing["t1h_ns"], abs=sample_ns
    )


@pytest.mark.parametrize("rate", [150, 300, 600])
@pytest.mark.parametrize(
    ("value", "telemetry"), [(0, False), (1000, False), (2047, True), (48, True)]
)
def test_dshot_frame_decodes_to_ground_truth_with_valid_checksum(
    rate, value, telemetry
):
    capture, ground_truth = SimpleDShotGenerator(
        rate=rate, value=value, telemetry=telemetry
    ).generate()
    channel = capture.channels["dshot"]

    bits = _decode_dshot(
        channel,
        ground_truth.parameters["t0h_samples"],
        ground_truth.parameters["t1h_samples"],
    )
    assert len(bits) == 16

    frame16 = 0
    for b in bits:
        frame16 = (frame16 << 1) | int(b)

    assert frame16 == ground_truth.parameters["frame16"]

    data12 = frame16 >> 4
    crc = frame16 & 0xF
    assert dshot_checksum(data12) == crc

    decoded_value = data12 >> 1
    decoded_telemetry = bool(data12 & 1)
    assert decoded_value == value
    assert decoded_telemetry == telemetry
