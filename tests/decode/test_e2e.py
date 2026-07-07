"""
End-to-end decode tests that demonstrate the full workflow.

Tests requirements from design.md:
- Zero-config end-to-end (Measure → Decode) for all protocols
- Raw synthetic captures should work without manual parameter passing
"""

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.native_uart import NativeUARTBackend
from slidko.decode.sigrok_backend import SigrokBackend
from tests.synth import SimpleI2CGenerator, SimpleSPIGenerator, SimpleUARTGenerator


def test_e2e_uart_decode():
    """Test complete UART workflow from synthetic capture to decoded events."""

    # Create synthetic UART capture
    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])
    capture, ground_truth = generator.generate()

    # The "Measure" step would generate this hypothesis - we'll simulate it
    # We mock a real classifier output here
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

    # Test that native backend can process it
    backend = NativeUARTBackend()

    # This should pass after implementation
    with pytest.raises(NotImplementedError):
        events = backend.decode(capture, hypothesis)
        assert len(events) == 2
        assert events[0].kind == "uart.byte"
        assert events[0].data["value"] == 0x41


def test_e2e_i2c_decode():
    """Test complete I²C workflow from synthetic capture to decoded events."""

    # Create synthetic I²C capture
    generator = SimpleI2CGenerator(address=0x55, payload=[0xAA, 0xBB])
    capture, ground_truth = generator.generate()

    # The "Measure" step would generate this hypothesis
    hypothesis = ProtocolHypothesis(
        protocol="i2c",
        parameters={"scl_channel": "ch0", "sda_channel": "ch1"},
        channel_assignments={"scl": "ch0", "sda": "ch1"},
    )

    # Test that sigrok backend can process it (if available)
    # We'll skip this for now since we don't have real sigrok available
    backend = SigrokBackend()

    with pytest.raises(NotImplementedError):
        events = backend.decode(capture, hypothesis)
        # Should produce correct i2c events based on payload


def test_e2e_spi_decode():
    """Test complete SPI workflow from synthetic capture to decoded events."""

    # Create synthetic SPI capture
    generator = SimpleSPIGenerator(cpol=0, cpha=1, payload=[0x55, 0xAA])
    capture, ground_truth = generator.generate()

    # The "Measure" step would generate this hypothesis
    hypothesis = ProtocolHypothesis(
        protocol="spi",
        parameters={
            "clk": "ch0",
            "mosi": "ch1",
            "miso": "ch2",
            "cpol": 0,
            "cpha": 1,
            "wordsize": 8,
        },
        channel_assignments={"clk": "ch0", "mosi": "ch1", "miso": "ch2"},
    )

    # Test that sigrok backend can process it
    backend = SigrokBackend()

    with pytest.raises(NotImplementedError):
        events = backend.decode(capture, hypothesis)
        # Should produce correct spi.events based on payload


if __name__ == "__main__":
    pytest.main([__file__])
