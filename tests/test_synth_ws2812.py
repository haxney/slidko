"""Tests for the synthetic WS2812 generator (tests/synth.py)."""

from tests.synth import SimpleWS2812Generator

WINDOW_NS = 150


def test_ws2812_bit_windows_are_spec_exact():
    payload = [0x5A, 0xC3]
    capture, _ = SimpleWS2812Generator(payload=payload).generate()

    sample_ns = 1e9 / capture.samplerate_hz
    channel = capture.channels["din"]

    rising = [
        i + 1 for i in range(len(channel) - 1) if not channel[i] and channel[i + 1]
    ]

    high_durations_ns = []
    for start in rising:
        end = start
        while end < len(channel) and channel[end]:
            end += 1
        high_durations_ns.append((end - start) * sample_ns)

    assert len(high_durations_ns) == len(payload) * 8

    t0h_lo, t0h_hi = 400 - WINDOW_NS, 400 + WINDOW_NS
    t1h_lo, t1h_hi = 800 - WINDOW_NS, 800 + WINDOW_NS
    for high_ns in high_durations_ns:
        assert (t0h_lo <= high_ns <= t0h_hi) or (t1h_lo <= high_ns <= t1h_hi)


def test_ws2812_bits_decode_to_payload():
    payload = [0x96]
    capture, ground_truth = SimpleWS2812Generator(payload=payload).generate()
    channel = capture.channels["din"]

    rising = [
        i + 1 for i in range(len(channel) - 1) if not channel[i] and channel[i + 1]
    ]
    t1h = ground_truth.parameters["t1h_samples"]

    bits = []
    for start in rising:
        end = start
        while end < len(channel) and channel[end]:
            end += 1
        bits.append(
            (end - start) >= (t1h + ground_truth.parameters["t0h_samples"]) // 2
        )

    value = 0
    for b in bits:
        value = (value << 1) | int(b)
    assert value == payload[0]


def test_ws2812_frame_starts_and_ends_low():
    capture, _ = SimpleWS2812Generator(payload=[0xFF]).generate()
    channel = capture.channels["din"]
    assert bool(channel[0]) is False
    assert bool(channel[-1]) is False
