from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class Capture:
    """A capture of logic signals with provenance information."""

    channels: dict[str, np.ndarray]
    samplerate_hz: int
    provenance: dict[str, Any]
