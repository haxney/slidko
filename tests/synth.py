"""
Synthetic capture generators for Slidko - ground-truth labeled
in-memory signal generation (the program's test infrastructure).

Each generator function returns a (Capture, GroundTruth) tuple.
The GroundTruth label dataclass contains protocol metadata and
fault information that can be used to verify the correctness of
auto-detection algorithms.
"""

from dataclasses import dataclass

import numpy as np

from slidko.capture import Capture


@dataclass
class GroundTruth:
    """Label for a synthetic capture - contains ground-truth protocol info."""

    # Protocol identification
    protocol: str  # "UART", "I2C", "SPI", "WS2812", etc.

    # Protocol-specific parameters
    parameters: dict

    # Payload data (if applicable)
    payload: list[int] | None = None

    # Injected faults
    injected_faults: list[str] = None

    # Random seed for reproducibility
    seed: int = 0

    def __post_init__(self):
        if self.injected_faults is None:
            self.injected_faults = []


class Generator:
    """Base class for synthetic capture generators."""

    def __init__(self, seed: int = 0):
        self.seed = seed
        np.random.seed(seed)

    def generate(self) -> tuple[Capture, GroundTruth]:
        """Generate a synthetic capture with ground truth label.

        Returns:
            Tuple of (Capture, GroundTruth)
        """
        raise NotImplementedError("Subclasses must implement generate()")
