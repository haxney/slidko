"""
Sigrok backend for Slidko decode module.

This implements the requirements from design.md:
- invoke sigrok-cli subprocess with inferred decoder options
- parse decoder output into common event schema
- exact, verified invocation from design.md
"""

from typing import Protocol

from slidko.capture import Capture
from slidko.decode.backend import DecodeBackend, ProtocolHypothesis
from slidko.decode.events import DecodedEvent

# Default path for libsigrokdecode decoders - adjust for system as needed
DEFAULT_DECODER_PATH = "/usr/share/libsigrokdecode/decoders/"


class _SigrokInputSource(Protocol):
    """Minimal shape needed to build a sigrok-cli invocation.

    `Capture` (src/slidko/capture/__init__.py) has no `filename` field yet —
    resolving the capture-to-.sr-path handoff is tracked in the
    fix-regression-suite change. This narrower Protocol lets the arg-builders
    stay type-checked without preempting that design decision.
    """

    filename: str


class SigrokBackend(DecodeBackend):
    """
    Backend that uses the sigrok decoder corpus via subprocess.

    This wraps the exact invocation confirmed in design.md against
    sigrok-cli 0.7.2 / libsigrokdecode 0.5.3.
    """

    def __init__(self, decoder_path: str = DEFAULT_DECODER_PATH):
        """
        Initialize the SigrokBackend.

        Args:
            decoder_path: Path to libsigrokdecode directory (default Debian/Ubuntu)
        """
        self.decoder_path = decoder_path

    def decode(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """
        Decode a capture using sigrok subprocess backend.

        Args:
            capture: A Capture object with channels, samplerate, and provenance
            hypothesis: A ProtocolHypothesis describing what the capture contains

        Returns:
            List of DecodedEvent objects
        """
        # Select decoder based on protocol
        if hypothesis.protocol == "uart":
            return self._decode_uart(capture, hypothesis)
        elif hypothesis.protocol == "i2c":
            return self._decode_i2c(capture, hypothesis)
        elif hypothesis.protocol == "spi":
            return self._decode_spi(capture, hypothesis)
        else:
            raise ValueError(f"Unsupported protocol {hypothesis.protocol}")

    def _decode_uart(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """Decode UART protocol using sigrok."""
        # Build the arguments
        # TODO(fix-regression-suite): capture has no .filename; see _SigrokInputSource
        self._build_uart_args(capture, hypothesis)  # type: ignore[arg-type]

        # Execute and parse output (placeholder - actual implementation pending)
        raise NotImplementedError("Sigrok UART decoder not implemented yet")

    def _decode_i2c(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """Decode I²C protocol using sigrok."""
        # Build the arguments
        # TODO(fix-regression-suite): capture has no .filename; see _SigrokInputSource
        self._build_i2c_args(capture, hypothesis)  # type: ignore[arg-type]

        # Execute and parse output (placeholder - actual implementation pending)
        raise NotImplementedError("Sigrok I²C decoder not implemented yet")

    def _decode_spi(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """Decode SPI protocol using sigrok."""
        # Build the arguments
        # TODO(fix-regression-suite): capture has no .filename; see _SigrokInputSource
        self._build_spi_args(capture, hypothesis)  # type: ignore[arg-type]

        # Execute and parse output (placeholder - actual implementation pending)
        raise NotImplementedError("Sigrok SPI decoder not implemented yet")

    def _build_uart_args(
        self, capture: _SigrokInputSource, hypothesis: ProtocolHypothesis
    ) -> list[str]:
        """
        Build the exact sigrok-cli command line for UART protocol.

        Format from design.md confirmed:
        sigrok-cli -i cap.sr \
            -P uart:rx=D0:baudrate=115200:data_bits=8:parity=none:stop_bits=1 \
            -A uart=rx-data --protocol-decoder-samplenum
        """
        # Extract UART parameters
        baud = hypothesis.parameters["baud"]
        data_bits = hypothesis.parameters.get("data_bits", 8)
        parity = hypothesis.parameters.get("parity", "none")
        stop_bits = hypothesis.parameters.get("stop_bits", 1.0)
        rx_channel = hypothesis.channel_assignments["rx"]

        # Build the command
        args = [
            "sigrok-cli",
            "-i",
            capture.filename,
            "-P",
            f"uart:rx={rx_channel}:baudrate={baud}:data_bits={data_bits}:parity={parity}:stop_bits={stop_bits}",
            "-A",
            "uart=rx-data",
            "--protocol-decoder-samplenum",
        ]

        return args

    def _build_i2c_args(
        self, capture: _SigrokInputSource, hypothesis: ProtocolHypothesis
    ) -> list[str]:
        """
        Build the exact sigrok-cli command line for I²C protocol.

        Format from design.md confirmed:
        sigrok-cli -i cap.sr -P i2c:scl=D0:sda=D1 \
            -A i2c=addr-data --protocol-decoder-samplenum
        """
        scl_channel = hypothesis.channel_assignments["scl"]
        sda_channel = hypothesis.channel_assignments["sda"]

        # Build the command
        args = [
            "sigrok-cli",
            "-i",
            capture.filename,
            "-P",
            f"i2c:scl={scl_channel}:sda={sda_channel}",
            "-A",
            "i2c=addr-data",
            "--protocol-decoder-samplenum",
        ]

        return args

    def _build_spi_args(
        self, capture: _SigrokInputSource, hypothesis: ProtocolHypothesis
    ) -> list[str]:
        """
        Build the exact sigrok-cli command line for SPI protocol.

        Format from design.md confirmed:
        sigrok-cli -i cap.sr \
            -P spi:clk=D0:mosi=D1:miso=D2:cs=D3:cpol=0:cpha=0:wordsize=8 \
            -A spi=mosi-data --protocol-decoder-samplenum
        """
        clk_channel = hypothesis.channel_assignments["clk"]
        mosi_channel = hypothesis.channel_assignments.get("mosi")
        miso_channel = hypothesis.channel_assignments.get("miso")
        cs_channel = hypothesis.channel_assignments.get("cs")

        # Extract SPI parameters
        cpol = hypothesis.parameters.get("cpol", 0)
        cpha = hypothesis.parameters.get("cpha", 0)
        wordsize = hypothesis.parameters.get("wordsize", 8)

        # Build the parameter string for SPI
        params = [
            f"clk={clk_channel}",
            f"cpol={cpol}",
            f"cpha={cpha}",
            f"wordsize={wordsize}",
        ]
        if mosi_channel:
            params.append(f"mosi={mosi_channel}")
        if miso_channel:
            params.append(f"miso={miso_channel}")
        if cs_channel:
            params.append(f"cs={cs_channel}")

        param_str = ":".join(params)

        # Build the command
        args = [
            "sigrok-cli",
            "-i",
            capture.filename,
            "-P",
            f"spi:{param_str}",
            "-A",
            "spi=mosi-data",  # or "spi=miso-data" depending on needs
            "--protocol-decoder-samplenum",
        ]

        return args


# Parser functions for stdout lines (these would be used post-subprocess)
def _parse_uart_output(stdout_lines: list[str]) -> list[DecodedEvent]:
    """
    Parse UART output from sigrok-cli.

    Line format: "4368-6036 uart-1: 41"
    Parse to: uart.byte {value=0x41}

    Args:
        stdout_lines: List of lines from sigrok output

    Returns:
        List of DecodedEvent objects
    """
    # Placeholder implementation - actual parsing needed
    raise NotImplementedError("UART output parser not implemented yet")


def _parse_i2c_output(stdout_lines: list[str]) -> list[DecodedEvent]:
    """
    Parse I²C output from sigrok-cli.

    Line format examples:
    "780-3300 i2c-1: Address write: 68"
    "3660-4020 i2c-1: ACK"
    "4020-6900 i2c-1: Data write: AA"
    "Start", "Stop", "NACK"

    Args:
        stdout_lines: List of lines from sigrok output

    Returns:
        List of DecodedEvent objects
    """
    # Placeholder implementation - actual parsing needed
    raise NotImplementedError("I²C output parser not implemented yet")


def _parse_spi_output(stdout_lines: list[str]) -> list[DecodedEvent]:
    """
    Parse SPI output from sigrok-cli.

    Line format per design.md: One line per word; parse to spi.transfer.

    Args:
        stdout_lines: List of lines from sigrok output

    Returns:
        List of DecodedEvent objects
    """
    # Placeholder implementation - actual parsing needed
    raise NotImplementedError("SPI output parser not implemented yet")
