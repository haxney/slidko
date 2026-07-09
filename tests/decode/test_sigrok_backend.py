"""
Tests for sigrok backend arguments and parsing.

This tests requirements from design.md:
- Write failing unit tests mocking subprocess to assert exact argument list
- Build sigrok-cli command string with correct channel map, pinning options
- Parser tests with canned stdout lines to produce DecodedEvent objects
"""

from slidko.decode import sigrok_backend
from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.sigrok_backend import SigrokBackend


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

    # Create backend instance
    backend = SigrokBackend()

    args = backend._build_uart_args("test_capture.sr", hypothesis)
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

    # Create backend instance
    backend = SigrokBackend()

    args = backend._build_i2c_args("test_capture.sr", hypothesis)
    expected = [
        "sigrok-cli",
        "-i",
        "test_capture.sr",
        "-P",
        "i2c:scl=D0:sda=D1",
        "-A",
        "i2c=addr-data",
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

    # Create backend instance
    backend = SigrokBackend()

    args = backend._build_spi_args("test_capture.sr", hypothesis)
    expected = [
        "sigrok-cli",
        "-i",
        "test_capture.sr",
        "-P",
        "spi:clk=D0:cpol=0:cpha=1:wordsize=8:mosi=D1:miso=D2:cs=D3",
        "-A",
        "spi=mosi-data",
        "--protocol-decoder-samplenum",
    ]
    assert args == expected


def test_sigrok_uart_stdout_parsing():
    """Test parsing of UART stdout from sigrok-cli."""

    # Real confirmed sigrok-cli output format (design.md)
    stdout_lines = [
        "4368-6036 uart-1: 41",
        "6036-7704 uart-1: 42",
        "7704-9372 uart-1: 43",
    ]

    events = sigrok_backend._parse_uart_output(stdout_lines)
    assert len(events) == 3
    assert events[0].kind == "uart.byte"
    assert events[0].start_sample == 4368
    assert events[0].end_sample == 6036
    assert events[0].data["value"] == 0x41
    assert events[0].data["ascii"] == "A"


def test_sigrok_i2c_stdout_parsing():
    """Test parsing of I²C stdout from sigrok-cli."""

    # Real confirmed sigrok-cli output format (design.md)
    stdout_lines = [
        "0-100 i2c-1: Start",
        "780-3300 i2c-1: Address write: 68",
        "3660-4020 i2c-1: ACK",
        "4020-6900 i2c-1: Data write: AA",
        "7260-7260 i2c-1: Stop",
    ]

    events = sigrok_backend._parse_i2c_output(stdout_lines)
    assert len(events) == 5
    assert events[0].kind == "i2c.start"
    assert events[1].kind == "i2c.address"
    assert events[1].data == {"address": 0x68, "rw": "write"}
    assert events[2].kind == "i2c.ack"
    assert events[3].kind == "i2c.data"
    assert events[3].data == {"value": 0xAA}
    assert events[4].kind == "i2c.stop"
