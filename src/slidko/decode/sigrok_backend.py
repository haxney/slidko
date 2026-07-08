"""
Sigrok backend for Slidko decode module.

This implements the requirements from design.md:
- invoke sigrok-cli subprocess with inferred decoder options
- parse decoder output into common event schema
- exact, verified invocation from design.md
"""

import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from slidko.capture import Capture
from slidko.capture.srfile import write_sr
from slidko.decode.backend import DecodeBackend, ProtocolHypothesis
from slidko.decode.events import DecodedEvent

# Default path for libsigrokdecode decoders - adjust for system as needed
DEFAULT_DECODER_PATH = "/usr/share/libsigrokdecode/decoders/"

_UART_LINE_RE = re.compile(r"^(\d+)-(\d+) uart-1: ([0-9A-Fa-f]+)$")
_I2C_LINE_RE = re.compile(r"^(\d+)-(\d+) i2c-1: (.+)$")
# EMPIRICAL, unconfirmed against real sigrok-cli output (unlike the UART/I2C
# formats above): inferred from the spi decoder's pd.py, which annotates
# mosi/miso words as a plain hex byte via the same samplenum-range mechanism
# as uart ('%02X' % word), so by analogy the line shape should match uart's
# "START-END spi-1: XX".
_SPI_LINE_RE = re.compile(r"^(\d+)-(\d+) spi-1: ([0-9A-Fa-f]+)$")


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

    def _run_sigrok(self, args: list[str]) -> list[str]:
        """Run sigrok-cli and return its stdout as a list of lines."""
        result = subprocess.run(args, capture_output=True, text=True, check=True)
        return [line for line in result.stdout.splitlines() if line]

    def _decode_uart(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """Decode UART protocol using sigrok."""
        with tempfile.NamedTemporaryFile(suffix=".sr", delete=False) as tmp:
            sr_path = tmp.name
        try:
            write_sr(capture, sr_path)
            args = self._build_uart_args(sr_path, hypothesis)
            stdout_lines = self._run_sigrok(args)
        finally:
            Path(sr_path).unlink(missing_ok=True)
        return _parse_uart_output(stdout_lines)

    def _decode_i2c(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """Decode I²C protocol using sigrok."""
        with tempfile.NamedTemporaryFile(suffix=".sr", delete=False) as tmp:
            sr_path = tmp.name
        try:
            write_sr(capture, sr_path)
            args = self._build_i2c_args(sr_path, hypothesis)
            stdout_lines = self._run_sigrok(args)
        finally:
            Path(sr_path).unlink(missing_ok=True)
        return _parse_i2c_output(stdout_lines)

    def _decode_spi(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """Decode SPI protocol using sigrok."""
        with tempfile.NamedTemporaryFile(suffix=".sr", delete=False) as tmp:
            sr_path = tmp.name
        try:
            write_sr(capture, sr_path)
            args = self._build_spi_args(sr_path, hypothesis)
            stdout_lines = self._run_sigrok(args)
        finally:
            Path(sr_path).unlink(missing_ok=True)
        return _parse_spi_output(stdout_lines)

    def _build_uart_args(
        self, sr_path: str, hypothesis: ProtocolHypothesis
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
        stop_bits = _format_stop_bits(hypothesis.parameters.get("stop_bits", 1.0))
        rx_channel = hypothesis.channel_assignments["rx"]

        # Build the command
        uart_opts = (
            f"uart:rx={rx_channel}:baudrate={baud}:data_bits={data_bits}"
            f":parity={parity}:stop_bits={stop_bits}"
        )
        return [
            "sigrok-cli",
            "-i",
            sr_path,
            "-P",
            uart_opts,
            "-A",
            "uart=rx-data",
            "--protocol-decoder-samplenum",
        ]

    def _build_i2c_args(
        self, sr_path: str, hypothesis: ProtocolHypothesis
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
        return [
            "sigrok-cli",
            "-i",
            sr_path,
            "-P",
            f"i2c:scl={scl_channel}:sda={sda_channel}",
            "-A",
            "i2c=addr-data",
            "--protocol-decoder-samplenum",
        ]

    def _build_spi_args(
        self, sr_path: str, hypothesis: ProtocolHypothesis
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
        return [
            "sigrok-cli",
            "-i",
            sr_path,
            "-P",
            f"spi:{param_str}",
            "-A",
            "spi=mosi-data",  # or "spi=miso-data" depending on needs
            "--protocol-decoder-samplenum",
        ]


def _format_stop_bits(stop_bits: float) -> str:
    """Render whole-number stop_bits without a trailing .0.

    Sigrok wants "1", not "1.0".
    """
    if stop_bits == int(stop_bits):
        return str(int(stop_bits))
    return str(stop_bits)


# Parser functions for stdout lines (used post-subprocess)
def _parse_uart_output(stdout_lines: list[str]) -> list[DecodedEvent]:
    """
    Parse UART output from sigrok-cli.

    Line format: "4368-6036 uart-1: 41"
    Parse to: uart.byte {value=0x41}
    """
    events = []
    for line in stdout_lines:
        match = _UART_LINE_RE.match(line)
        if not match:
            continue
        start_sample, end_sample, hex_value = match.groups()
        value = int(hex_value, 16)
        events.append(
            DecodedEvent(
                kind="uart.byte",
                start_sample=int(start_sample),
                end_sample=int(end_sample),
                data={
                    "value": value,
                    "ascii": chr(value) if 32 <= value < 127 else None,
                },
                channel=None,
            )
        )
    return events


def _parse_i2c_output(stdout_lines: list[str]) -> list[DecodedEvent]:
    """
    Parse I²C output from sigrok-cli.

    Line format examples:
    "780-3300 i2c-1: Address write: 68"
    "3660-4020 i2c-1: ACK"
    "4020-6900 i2c-1: Data write: AA"
    "Start", "Stop", "NACK"
    """
    events = []
    for line in stdout_lines:
        match = _I2C_LINE_RE.match(line)
        if not match:
            continue
        start_sample, end_sample, text = match.groups()
        start_sample_i, end_sample_i = int(start_sample), int(end_sample)

        data: dict[str, Any]
        if text == "Start":
            kind, data = "i2c.start", {}
        elif text == "Stop":
            kind, data = "i2c.stop", {}
        elif text == "ACK":
            kind, data = "i2c.ack", {}
        elif text == "NACK":
            kind, data = "i2c.nak", {}
        elif text.startswith("Address write: "):
            kind = "i2c.address"
            data = {
                "address": int(text.removeprefix("Address write: "), 16),
                "rw": "write",
            }
        elif text.startswith("Address read: "):
            kind = "i2c.address"
            data = {
                "address": int(text.removeprefix("Address read: "), 16),
                "rw": "read",
            }
        elif text.startswith("Data write: "):
            kind = "i2c.data"
            data = {"value": int(text.removeprefix("Data write: "), 16)}
        elif text.startswith("Data read: "):
            kind = "i2c.data"
            data = {"value": int(text.removeprefix("Data read: "), 16)}
        else:
            continue

        events.append(
            DecodedEvent(
                kind=kind,
                start_sample=start_sample_i,
                end_sample=end_sample_i,
                data=data,
                channel=None,
            )
        )
    return events


def _parse_spi_output(stdout_lines: list[str]) -> list[DecodedEvent]:
    """
    Parse SPI output from sigrok-cli.

    Line format per design.md: One line per word; parse to spi.transfer.
    EMPIRICAL/unconfirmed line shape - see _SPI_LINE_RE.
    """
    events = []
    for line in stdout_lines:
        match = _SPI_LINE_RE.match(line)
        if not match:
            continue
        start_sample, end_sample, hex_value = match.groups()
        events.append(
            DecodedEvent(
                kind="spi.transfer",
                start_sample=int(start_sample),
                end_sample=int(end_sample),
                data={"mosi": int(hex_value, 16), "miso": None},
                channel=None,
            )
        )
    return events
