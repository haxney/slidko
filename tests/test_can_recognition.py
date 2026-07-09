"""Tests for CAN bit-stuffing + bitrate recognition (measure/can.py)."""

from slidko.measure import can
from tests.synth import SimpleUARTGenerator, expand_segments

SAMPLE_RATE_HZ = 24_000_000


def _bit_stuff(bits: list[bool]) -> list[bool]:
    stuffed: list[bool] = []
    run_level = None
    run_len = 0
    for b in bits:
        stuffed.append(b)
        if b == run_level:
            run_len += 1
        else:
            run_level = b
            run_len = 1
        if run_len == 5:
            stuffed.append(not b)
            run_level = not b
            run_len = 1
    return stuffed


def _can_like_channel(bitrate_hz: int, sample_rate_hz: int = SAMPLE_RATE_HZ):
    # Deliberately includes runs of >=5 identical bits pre-stuffing so the
    # stuffed output actually exercises the stuff-bit insertion.
    raw_bits = [
        bool(b)
        for b in [
            0,
            0,
            0,
            0,
            0,
            1,
            1,
            0,
            1,
            0,
            1,
            1,
            1,
            1,
            1,
            0,
            0,
            1,
            0,
            1,
            1,
            0,
            0,
            0,
            1,
            1,
            0,
            1,
        ]
    ]
    bits = _bit_stuff(raw_bits)
    bit_period = round(sample_rate_hz / bitrate_hz)
    segments = [(bit, bit_period) for bit in bits]
    return expand_segments(segments)


def test_recognizes_bit_stuffed_can_at_standard_bitrate():
    channel = _can_like_channel(bitrate_hz=500_000)
    recognized, confidence, bitrate = can.recognize(channel, SAMPLE_RATE_HZ)
    assert recognized is True
    assert bitrate == 500_000
    assert confidence >= 0.7


def test_recognizes_can_at_each_standard_bitrate():
    for bitrate_hz in can.STANDARD_CAN_BITRATES:
        channel = _can_like_channel(bitrate_hz=bitrate_hz)
        recognized, _confidence, detected = can.recognize(channel, SAMPLE_RATE_HZ)
        assert recognized is True
        assert detected == bitrate_hz


def test_does_not_recognize_uart_as_can():
    capture, _ = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x3C]).generate()
    recognized, _confidence, _bitrate = can.recognize(
        capture.channels["ch0"], capture.samplerate_hz
    )
    assert recognized is False
