"""
Backend abstraction for Slidko decode module.

This implements:
- ProtocolHypothesis dataclass with protocol parameters inferred by Measure
- DecodeBackend protocol declaring the interface

See design.md for detailed specification.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .events import DecodedEvent


# ProtocolHypothesis represents a hypothesis about what protocol is present,
# including parameters inferred by Measure and channel/role assignments
@dataclass(frozen=True)
class ProtocolHypothesis:
    """
    A hypothesis from measurement about what protocol is present with its parameters.

    This is the handoff object from Measure to Decode. Fields are as required
    by the Decode backend interface for each protocol type:

    - UART: {"baud": int, "data_bits": 8, "parity": "none", "stop_bits": 1.0,
      "rx_channel": "D0"}
    - I²C: {"scl_channel": "D0", "sda_channel": "D1"}
    - SPI: {"clk": "D0", "mosi": "D1"|None, "miso": "D2"|None, "cs": "D3"|None,
      "cpol": 0, "cpha": 0, "wordsize": 8}
    """

    # Basic protocol information
    protocol: str  # "uart", "i2c", "spi"

    # Protocol-specific parameters inferred by Measure (see design.md)
    parameters: dict[str, Any]

    # Channel role assignments (e.g., which capture channels are used for what)
    channel_assignments: dict[str, str]


class DecodeBackend(ABC):
    """
    Abstract base class for decode backends.

    Each backend implements decode() taking a Capture and its protocol hypothesis,
    and returning a list of decoded events in the normalized schema.
    """

    @abstractmethod
    def decode(self, capture, hypothesis: ProtocolHypothesis) -> list[DecodedEvent]:
        """
        Decode a capture using the given protocol hypothesis.

        Args:
            capture: A Capture object with channels, samplerate, and provenance
            hypothesis: A ProtocolHypothesis describing what the capture contains

        Returns:
            List of DecodedEvent objects
        """


# This is only for testing that a backend implements the Protocol interface
# The actual test will be added in task 2.3
def test_backend_protocol_compliance():
    """Test that any backend satisfies the structural typing of DecodeBackend."""
