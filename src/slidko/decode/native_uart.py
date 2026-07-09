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

        rx_signal = capture.channels[rx_channel]
        baud = hypothesis.parameters["baud"]
        bit_period_samples = capture.samplerate_hz / baud
        if bit_period_samples < 1:
            raise ValueError(
                f"baud {baud} too high for sample rate {capture.samplerate_hz}"
            )

        events: list[DecodedEvent] = []
        idx = 1
        n = len(rx_signal)
        while idx < n:
            # Idle is high; a start bit is the falling edge out of idle.
            if rx_signal[idx - 1] and not rx_signal[idx]:
                decoded = _decode_uart_byte(
                    rx_signal, idx, bit_period_samples, data_bits
                )
                if decoded is not None:
                    value, end_sample, stop_bit_high = decoded
                    events.append(
                        DecodedEvent(
                            kind="uart.byte",
                            start_sample=idx,
                            end_sample=end_sample,
                            data={
                                "value": value,
                                "ascii": chr(value) if 32 <= value < 127 else None,
                                "framing_error": not stop_bit_high,
                            },
                            channel=None,
                        )
                    )
                    idx = end_sample + 1
                    continue
            idx += 1

        return events


def _decode_uart_byte(
    rx_signal: np.ndarray,
    start_sample: int,
    bit_period_samples: float,
    data_bits: int = 8,
) -> tuple[int, int, bool] | None:
    """Decode a single 8N1 UART byte starting at a detected start-bit edge.

    Samples each data bit at its midpoint, assembles LSB-first, and checks
    the stop bit is high. A framing error (stop bit not idle-high) still
    yields the byte - it's reported via the third element, not dropped, so
    Narrate/the smoke detector's incoherence check can see it. Returns None
    only when the frame runs past the end of the signal (truncated, not a
    real frame).

    Args:
        rx_signal: The RX signal array
        start_sample: Sample index of the start bit's falling edge
        bit_period_samples: Samples per bit (may be fractional)
        data_bits: Number of data bits (native backend only supports 8)

    Returns:
        (byte_value, end_sample, stop_bit_high) or None if truncated
    """
    n = len(rx_signal)

    def bit_center(bit_index_from_start_bit: float) -> int:
        offset = bit_period_samples * (bit_index_from_start_bit + 0.5)
        return start_sample + round(offset)

    stop_center = bit_center(data_bits + 1)
    if stop_center >= n:
        return None
    stop_bit_high = bool(rx_signal[stop_center])

    value = 0
    for i in range(data_bits):
        sample_idx = bit_center(i + 1)
        if bool(rx_signal[sample_idx]):
            value |= 1 << i

    end_sample = start_sample + round(bit_period_samples * (data_bits + 2)) - 1
    return value, end_sample, stop_bit_high
