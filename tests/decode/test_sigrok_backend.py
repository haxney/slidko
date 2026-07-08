"""
Tests for sigrok backend arguments and parsing.

This tests requirements from design.md:
- Write failing unit tests mocking subprocess to assert exact argument list
- Build sigrok-cli command string with correct channel map, pinning options
- Parser tests with canned stdout lines to produce DecodedEvent objects
"""

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.sigrok_backend import (
    SigrokBackend,
    _parse_i2c_output,
    _parse_uart_output,
)


def test_sigrok_uart_args_building():
    """Test that UART backend builds correct sigrok-cli arguments."""

    # Create a protocol hypothesis for UART
    hypothesis = ProtocolHypothesis(
        protocol="uart",
        parameters={
            "baud": 115200,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1.0,
            "rx_channel": "D0",
        },
        channel_assignments={"rx": "D0"},
    )

    # Create a mock capture object
    class MockCapture:
        filename = "test_capture.sr"

    capture = MockCapture()

    # Create backend instance
    backend = SigrokBackend()

    # This should fail before implementation
    with pytest.raises(NotImplementedError):
        args = backend._build_uart_args(capture, hypothesis)
        expected = [
            "sigrok-cli",
            "-i",
            "test_capture.sr",
            "-P",
            "uart:rx=D0:baudrate=115200:data_bits=8:parity=none:stop_bits=1",
            "-A",
            "uart=rx-data",
            "--protocol-decoder-samplenum",
        ]
        assert args == expected


def test_sigrok_i2c_args_building():
    """Test that I²C backend builds correct sigrok-cli arguments."""

    # Create a protocol hypothesis for I2C
    hypothesis = ProtocolHypothesis(
        protocol="i2c",
        parameters={"scl_channel": "D0", "sda_channel": "D1"},
        channel_assignments={"scl": "D0", "sda": "D1"},
    )

    # Create a mock capture object
    class MockCapture:
        filename = "test_capture.sr"

    capture = MockCapture()

    # Create backend instance
    backend = SigrokBackend()

    # This should fail before implementation
    with pytest.raises(NotImplementedError):
        args = backend._build_i2c_args(capture, hypothesis)
        expected = [
            "sigrok-cli",
            "-i",
            "test_capture.sr",
            "-P",
            "i2c:scl=D0:sda=D1",
            "-A",
            "i2c=data",
            "--protocol-decoder-samplenum",
        ]
        assert args == expected


def test_sigrok_spi_args_building():
    """Test that SPI backend builds correct sigrok-cli arguments."""

    # Create a protocol hypothesis for SPI
    hypothesis = ProtocolHypothesis(
        protocol="spi",
        parameters={
            "clk": "D0",
            "mosi": "D1",
            "miso": "D2",
            "cs": "D3",
            "cpol": 0,
            "cpha": 1,
            "wordsize": 8,
        },
        channel_assignments={"clk": "D0", "mosi": "D1", "miso": "D2", "cs": "D3"},
    )

    # Create a mock capture object
    class MockCapture:
        filename = "test_capture.sr"

    capture = MockCapture()

    # Create backend instance
    backend = SigrokBackend()

    # This should fail before implementation
    with pytest.raises(NotImplementedError):
        args = backend._build_spi_args(capture, hypothesis)
        expected = [
            "sigrok-cli",
            "-i",
            "test_capture.sr",
            "-P",
            "spi:clk=D0:mosi=D1:miso=D2:cs=D3:cpol=0:cpha=1:wordsize=8",
            "-A",
            "spi=data",
            "--protocol-decoder-samplenum",
        ]
        assert args == expected


def test_sigrok_uart_stdout_parsing():
    """Test parsing of UART stdout from sigrok-cli."""

    # Mock stdout data (format as example outputs from design.md)
    stdout_lines = [
        "0.012345 0x41",  # Byte A at 12.345ms (time in seconds)
        "0.013456 0x42",  # Byte B
        "0.014567 0x43",  # Byte C
    ]

    # This should fail before implementation
    with pytest.raises(NotImplementedError):
        events = _parse_uart_output(stdout_lines)
        assert len(events) == 3
        assert events[0].kind == "uart.byte"
        assert events[0].data["value"] == 0x41


def test_sigrok_i2c_stdout_parsing():
    """Test parsing of I²C stdout from sigrok-cli."""

    # Mock stdout data
    stdout_lines = [
        "0.001234 START",
        "0.001345 0x55",  # Address + R/W
        "0.002456 0xAA",  # Data byte
        "0.003567 STOP",
    ]

    # This should fail before implementation
    with pytest.raises(NotImplementedError):
        events = _parse_i2c_output(stdout_lines)
        assert len(events) >= 2  # Should have at least address and data
        # Add more specific assertions as parsing is completed


if __name__ == "__main__":
    pytest.main([__file__])
