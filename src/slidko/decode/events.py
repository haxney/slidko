"""
Normalized decoded event schema for Slidko.

This implements the requirements from design.md:
- DecodedEvent is a frozen dataclass with kind, start_sample, end_sample, data, channel
- seconds() helper method to compute time in seconds
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DecodedEvent:
    """
    A decoded event from protocol analysis.

    This is the normalized, protocol-agnostic envelope for all decoded events.
    Protocol-specific data is stored in the `data` field with predefined schemas
    that Narrate depends on.

    Kind vocabulary and per-kind data conventions (exact strings):
    - 'uart.byte': {'value': int, 'ascii': str|None}
    - 'i2c.start': {}
    - 'i2c.address': {'address': int, 'rw': 'read'|'write'}
    - 'i2c.ack': {}
    - 'i2c.nak': {}
    - 'i2c.data': {'value': int}
    - 'i2c.stop': {}
    - 'spi.transfer': {'mosi': int|None, 'miso': int|None}

    Rationale: Phase 4 traceability requires every assertion to point at
    sample ranges (ROADMAP Phase 4 acceptance).
    """

    kind: str  # e.g. "uart.byte", "i2c.start", "i2c.address",
    # "i2c.ack", "i2c.nak", "i2c.data", "i2c.stop",
    # "spi.transfer"
    start_sample: int  # inclusive, in capture sample indices
    end_sample: int  # inclusive
    data: dict[str, Any]  # kind-specific payload, see above
    channel: str | None = None  # source role/line where meaningful

    def seconds(self, samplerate_hz: float) -> float:
        """
        Compute the time in seconds of this event's start sample.

        Args:
            samplerate_hz: The sample rate of the capture

        Returns:
            Time in seconds from start_sample
        """
        return self.start_sample / samplerate_hz


# The module docstring above describes exactly the kind vocabulary and data conventions
# that Narrate depends on. This is the exact text to match as per design.md.
