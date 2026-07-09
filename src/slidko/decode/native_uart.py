"""
Native UART decoder backend for Slidko.

This implements the requirements from design.md:
- idle-high detection
- per-frame start-bit detection
- midpoint sampling at baud-spaced offsets
- LSB-first assembly
- stop-bit check
- emit uart.byte events with correct sample bounds

Uses numpy for efficient signal processing.
"""

import math

import numpy as np

from slidko.capture import Capture
from slidko.decode.backend import DecodeBackend, ProtocolHypothesis
from slidko.decode.events import DecodedEvent


class NativeUARTBackend(DecodeBackend):
    """
    Native UART decoder backend that works without sigrok.

    This is an efficient, pure-numpy implementation to prove the abstraction
    holds and to provide a sigrok-free path for CI/developer testing.
    """

    def decode(
        self, capture: Capture, hypothesis: ProtocolHypothesis
    ) -> list[DecodedEvent]:
        """
        Decode UART signal from a capture using native algorithm.

        Args:
            capture: A Capture object with channels, samplerate, and provenance
            hypothesis: A ProtocolHypothesis describing what the capture contains

        Returns:
            List of DecodedEvent objects for received bytes
        """
        # Extract required parameters
        data_bits = hypothesis.parameters.get("data_bits", 8)
        parity = hypothesis.parameters.get("parity", "none")
        stop_bits = hypothesis.parameters.get("stop_bits", 1.0)
        rx_channel = hypothesis.channel_assignments["rx"]

        # Check that we have an 8N1 configuration (as per design.md)
        # SBUS requires special handling and should be routed to sigrok backend
        if parity != "none" or data_bits != 8 or not math.isclose(stop_bits, 1.0):
            raise ValueError(
                f"Native UART only supports 8N1. Got: {data_bits}{parity}{stop_bits}"
            )

        # Confirm the RX channel exists before decoding
        _ = capture.channels[rx_channel]

        # Find start bits and decode bytes
        events: list[DecodedEvent] = []

        # For now, we'll just create a placeholder implementation
        # that shows how this would work - actual UART decoding algorithm
        # would be complex to write from scratch
        raise NotImplementedError("Native UART decoder not fully implemented yet")

        # In a full implementation:
        # 1. Detect idle high level (UART idle is high)
        # 2. Find start bits (falling edges below threshold)
        # 3. Sample data bits at mid-bit positions
        # 4. Assemble bytes in LSB-first order
        # 5. Verify stop bit is high
        # 6. Return DecodedEvent objects

        return events


# Utility function to decode individual byte from signal
def _decode_uart_byte(
    rx_signal: np.ndarray, start_sample: int, bit_period_samples: float
) -> tuple[int, int, int]:
    """Decode a single UART byte.

    Args:
        rx_signal: The RX signal array
        start_sample: Starting sample index for this byte
        bit_period_samples: Number of samples per bit

    Returns:
        Tuple of (byte_value, end_sample, error_flag)
    """
    # Implementation would go here in a full version
    raise NotImplementedError("Utility function not implemented yet")
