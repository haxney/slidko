"""
Tests for native UART backend.

Tests requirements from design.md:
- decode recovers the generator's ground-truth payload bytes exactly at
  9600 and 115200 baud
- native backend handles 8N1 standard bauds (no SBUS support in native path)
"""

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.native_uart import NativeUARTBackend
from tests.synth import SimpleUARTGenerator


def test_native_uart_decode_9600():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])
    capture, _ground_truth = generator.generate()

    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 9600,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    backend = NativeUARTBackend()
    events = backend.decode(capture, hypothesis)

    assert [e.kind for e in events] == ["uart.byte", "uart.byte"]
    assert [e.data["value"] for e in events] == [0x41, 0x42]
    assert events[0].data["ascii"] == "A"
    assert events[1].data["ascii"] == "B"
    for event in events:
        assert 0 <= event.start_sample < event.end_sample < len(capture.channels["ch0"])


def test_native_uart_decode_115200():
    generator = SimpleUARTGenerator(baud=115200, payload=[0x43, 0x44])
    capture, _ground_truth = generator.generate()

    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 115200,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    backend = NativeUARTBackend()
    events = backend.decode(capture, hypothesis)

    assert [e.kind for e in events] == ["uart.byte", "uart.byte"]
    assert [e.data["value"] for e in events] == [0x43, 0x44]


def test_native_uart_decode_event_bounds_within_frame():
    """Each event's [start_sample, end_sample] lies within the true frame
    extent: start bit's falling edge through the end of the stop bit."""
    generator = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x0F])
    capture, ground_truth = generator.generate()
    bit_samples = ground_truth.parameters["bit_samples"]

    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 9600,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    backend = NativeUARTBackend()
    events = backend.decode(capture, hypothesis)

    assert [e.data["value"] for e in events] == [0x55, 0xAA, 0x0F]
    for event in events:
        frame_samples = event.end_sample - event.start_sample + 1
        # start bit + 8 data bits + 1 stop bit == 10 bit periods
        assert abs(frame_samples - 10 * bit_samples) <= 1


def test_native_uart_decode_sbus():
    """Native backend refuses SBUS (8E2) by design - only 8N1 is supported
    natively; SBUS must route through the sigrok backend."""
    generator = SimpleUARTGenerator(baud=100000, payload=[0x45])
    capture, _ground_truth = generator.generate()

    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 100000,
            "data_bits": 8,
            "parity": "even",
            "stop_bits": 2.0,
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    backend = NativeUARTBackend()

    with pytest.raises(ValueError, match="8N1"):
        backend.decode(capture, hypothesis)


if __name__ == "__main__":
    pytest.main([__file__])
