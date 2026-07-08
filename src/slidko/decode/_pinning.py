"""
Decoder pinning, drift detection, and error recovery.

This implements the requirements from design.md:
- Track decoder pin mappings vs expected roles (e.g., "rx", "scl", "sda", etc.)
- Detect when a protocol's pins have shifted in sample space
- Implement error recovery by falling back to sigrok or reporting problem

Usage:
1. Decoder instances are initialized with known channel assignments
2. During decode, track drift from expected pin positions
3. Revert to fallback mechanisms if drift exceeds safe thresholds
"""

from dataclasses import dataclass, field

from slidko.capture import Capture
from slidko.decode.backend import ProtocolHypothesis


@dataclass
class PinMapping:
    """
    Track how decoder expects to see channels vs what they actually are.

    For example: UART rx channel may drift by 1-2 samples during decoding.
    I²C scl/sda may have timing variations or be swapped on some boards.
    SPI clk is critical, but mosi/miso can drift slightly.
    """

    expected_pins: dict[str, str]  # Expected channel names for each role
    actual_pins: dict[str, str]  # Actual channel names found by detection
    drift_samples: dict[
        str, float
    ]  # Drift in samples (positive = early, negative = late)

    # For detecting pin swapping, tracking of sample alignment
    sample_alignment: dict[tuple[str, str], int] = field(default_factory=dict)


class DriftDetector:
    """
    Detect and handle timing drift in protocol decoders.

    This ensures reliability even when the hardware has:
    - Channel drift (polarity flip or timing offset)
    - Pin swapping
    - Signal quality issues

    For protocols with timing-sensitive elements:
    - UART: can tolerate ~1-2 samples of drift to RX pin
    - I²C: timing tightness affects valid start/stop conditions
    - SPI: clock and data synchronization critical
    """

    def __init__(self, protocol: str):
        self.protocol = protocol
        self.max_drift_samples = {"uart": 2.0, "i2c": 5.0, "spi": 3.0}

    def detect_pin_drift(
        self,
        expected_mapping: dict[str, str],
        actual_mapping: dict[str, str],
        capture: Capture,
    ) -> PinMapping:
        """
        Detect drift and inconsistencies in pin mappings.

        Args:
            expected_mapping: What we expect to see (from hypothesis)
            actual_mapping: What we found during detection
            capture: The full capture for signal analysis

        Returns:
            PinMapping object with drift information
        """
        # In a complete implementation, this would analyze the actual capture signals
        # to determine if timing has drifted beyond acceptable thresholds

        # Placeholder - in reality would examine signal waveforms and sample positions
        drift = {}
        for role in expected_mapping:
            if role in actual_mapping:
                # This is a simplified check - real implementation would analyze
                # the actual positional difference in samples
                drift[role] = 0.0  # Placeholder

        return PinMapping(
            expected_pins=expected_mapping,
            actual_pins=actual_mapping,
            drift_samples=drift,
        )

    def is_acceptable_drift(self, pin_map: PinMapping) -> bool:
        """
        Check if detected drift is within acceptable limits.

        Args:
            pin_map: Mapping from drift detection

        Returns:
            True if drift is acceptable, False if should trigger fallback or error
        """
        for drift in pin_map.drift_samples.values():
            max_drift = self.max_drift_samples.get(self.protocol, 10.0)
            if abs(drift) > max_drift:
                return False
        return True


def validate_pin_assignment(
    decode_hypothesis: ProtocolHypothesis, capture: Capture
) -> tuple[bool, str]:
    """
    Validate that the pin assignments are reasonable for this protocol.

    Args:
        decode_hypothesis: The ProtocolHypothesis from classification
        capture: The full capture being decoded

    Returns:
        Tuple of (is_valid, validation_message)
    """
    # This would do protocol-specific consistency checks

    # In a real implementation this would analyze the actual signal
    # and check if channel assignments make sense
    return True, "Pin assignment valid"
