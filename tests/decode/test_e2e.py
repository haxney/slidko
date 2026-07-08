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
    capture, _ground_truth = generator.generate()

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

    # This should pass after implementation - once implemented, replace with
    # real assertions: len(events) == 2, events[0].kind == "uart.byte",
    # events[0].data["value"] == 0x41
    with pytest.raises(NotImplementedError):
        backend.decode(capture, hypothesis)


def test_e2e_i2c_decode(monkeypatch):
    """Test complete I²C workflow from synthetic capture to decoded events.

    The synthetic capture from tests/synth.py is not a protocol-accurate
    signal (it's a 3-sample placeholder), so real sigrok-cli cannot decode
    it. Per design.md's subprocess-mocking guidance, mock the sigrok-cli
    boundary with the confirmed real output format and assert on the
    resulting events instead.
    """
    # Create synthetic I²C capture
    generator = SimpleI2CGenerator(address=0x55, payload=[0xAA, 0xBB])
    capture, _ground_truth = generator.generate()

    # The "Measure" step would generate this hypothesis
    hypothesis = ProtocolHypothesis(
        protocol="i2c",
        parameters={"scl_channel": "ch0", "sda_channel": "ch1"},
        channel_assignments={"scl": "ch0", "sda": "ch1"},
    )

    backend = SigrokBackend()
    canned_stdout = [
        "0-100 i2c-1: Start",
        "100-400 i2c-1: Address write: 55",
        "400-500 i2c-1: ACK",
        "500-900 i2c-1: Data write: AA",
        "900-1000 i2c-1: ACK",
        "1000-1400 i2c-1: Data write: BB",
        "1400-1500 i2c-1: ACK",
        "1500-1600 i2c-1: Stop",
    ]
    monkeypatch.setattr(backend, "_run_sigrok", lambda args: canned_stdout)

    events = backend.decode(capture, hypothesis)
    assert [e.kind for e in events] == [
        "i2c.start",
        "i2c.address",
        "i2c.ack",
        "i2c.data",
        "i2c.ack",
        "i2c.data",
        "i2c.ack",
        "i2c.stop",
    ]
    assert events[1].data == {"address": 0x55, "rw": "write"}
    assert [e.data["value"] for e in events if e.kind == "i2c.data"] == [0xAA, 0xBB]


def test_e2e_spi_decode(monkeypatch):
    """Test complete SPI workflow from synthetic capture to decoded events.

    See test_e2e_i2c_decode's docstring: sigrok-cli is mocked at the
    subprocess boundary because the synthetic capture isn't a real signal.
    """
    # Create synthetic SPI capture
    generator = SimpleSPIGenerator(cpol=0, cpha=1, payload=[0x55, 0xAA])
    capture, _ground_truth = generator.generate()

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

    backend = SigrokBackend()
    canned_stdout = ["0-100 spi-1: 55", "100-200 spi-1: AA"]
    monkeypatch.setattr(backend, "_run_sigrok", lambda args: canned_stdout)

    events = backend.decode(capture, hypothesis)
    assert [e.kind for e in events] == ["spi.transfer", "spi.transfer"]
    assert [e.data["mosi"] for e in events] == [0x55, 0xAA]


if __name__ == "__main__":
    pytest.main([__file__])
