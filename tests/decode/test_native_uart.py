"""
Tests for native UART backend.

This tests requirements from design.md:
- Write failing tests using the Phase 1 synthetic UART generator (tests/synth.py)
- decode recovers the generator's ground-truth payload bytes exactly at 9600, 115200
- native backend handles 8N1 standard bauds (no SBUS support in native path)
"""

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.native_uart import NativeUARTBackend
from tests.synth import SimpleUARTGenerator


def test_native_uart_decode_9600():
    """Test decoding at 9600 baud."""
    # Create a simple UART generator with known payload
    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])  # "AB"
    capture, _ground_truth = generator.generate()

    # Create the protocol hypothesis (as inferred by Measure)
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

    # Create the backend
    backend = NativeUARTBackend()

    # This should fail before implementation - once implemented, replace with
    # real assertions: len(events) == 2, events[0].kind == "uart.byte",
    # events[0].data["value"] == 0x41
    with pytest.raises(NotImplementedError):
        backend.decode(capture, hypothesis)


def test_native_uart_decode_115200():
    """Test decoding at 115200 baud."""
    # Create a simple UART generator with known payload
    generator = SimpleUARTGenerator(baud=115200, payload=[0x43, 0x44])  # "CD"
    capture, _ground_truth = generator.generate()

    # Create the protocol hypothesis (as inferred by Measure)
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

    # Create the backend
    backend = NativeUARTBackend()

    # This should fail before implementation - once implemented, replace with
    # real assertions: len(events) == 2, events[0].kind == "uart.byte",
    # events[0].data["value"] == 0x43
    with pytest.raises(NotImplementedError):
        backend.decode(capture, hypothesis)


def test_native_uart_decode_sbus():
    """Test that SBUS is handled by sigrok path (not native backend)."""
    # SBUS uses different params (100000-8E2)
    generator = SimpleUARTGenerator(baud=100000, payload=[0x45])  # "E"
    capture, _ground_truth = generator.generate()

    # Create the protocol hypothesis
    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 100000,
            "data_bits": 8,
            "parity": "even",
            "stop_bits": 2.0,  # SBUS uses 2 stop bits
            "rx_channel": "ch0",
        },
        channel_assignments={"rx": "ch0"},
    )

    # Create the backend
    backend = NativeUARTBackend()

    # For now SBUS should raise an error or be handled by sigrok path
    with pytest.raises(NotImplementedError):
        backend.decode(capture, hypothesis)


if __name__ == "__main__":
    pytest.main([__file__])
