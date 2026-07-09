"""I2C discriminator - structural start/stop detection and SCL/SDA role
assignment. Deterministic DSP only - no ML."""

from dataclasses import dataclass

import numpy as np

from slidko.measure.edges import active_window, extract_edges
from slidko.measure.intervals import periodicity_strength

# Standard I2C bus speeds (recognition table; not required for detection).
STANDARD_I2C_SPEEDS_HZ = [100_000, 400_000, 1_000_000]


@dataclass(frozen=True)
class I2CStartStop:
    starts: list[int]  # sample indices where a START condition begins
    stops: list[int]  # sample indices where a STOP condition begins


@dataclass(frozen=True)
class I2CRoleAssignment:
    scl_channel: str
    sda_channel: str
    confidence: float


@dataclass(frozen=True)
class I2CClaim:
    protocol: str
    scl_channel: str
    sda_channel: str
    confidence: float
    start_count: int
    stop_count: int


def detect_start_stop(scl: np.ndarray, sda: np.ndarray) -> I2CStartStop:
    """Structural start/stop detection: SDA transitions while SCL is held
    high. A falling SDA edge while SCL is high is a START; a rising SDA edge
    while SCL is high is a STOP (I2C's structurally unique signature - see
    docs/ROADMAP.md Phase 1)."""
    sda_edges = extract_edges(sda)
    starts: list[int] = []
    stops: list[int] = []
    for idx, rising in sda_edges:
        if idx >= len(scl):
            continue
        if scl[idx - 1] and scl[idx]:
            if rising:
                stops.append(idx)
            else:
                starts.append(idx)
    return I2CStartStop(starts=starts, stops=stops)


def assign_roles(channels: dict[str, np.ndarray]) -> I2CRoleAssignment:
    """Assign SCL/SDA roles to two candidate channels via periodicity
    strength: SCL is the more regularly-toggling (clock) line; SDA transitions
    far less often. Confidence is the periodicity-strength spread between the
    two, clamped to [0, 1]."""
    if len(channels) != 2:
        raise ValueError("I2C role assignment expects exactly two channels")
    (name_a, sig_a), (name_b, sig_b) = channels.items()
    start, end = active_window([sig_a, sig_b])
    strength_a = periodicity_strength(sig_a[start:end])
    strength_b = periodicity_strength(sig_b[start:end])

    if strength_a >= strength_b:
        scl_name, sda_name = name_a, name_b
        spread = strength_a - strength_b
    else:
        scl_name, sda_name = name_b, name_a
        spread = strength_b - strength_a

    confidence = max(0.0, min(1.0, spread))
    return I2CRoleAssignment(
        scl_channel=scl_name, sda_channel=sda_name, confidence=confidence
    )


def classify_i2c(channels: dict[str, np.ndarray]) -> I2CClaim:
    """Classify a 2-channel capture as I2C: role-assign SCL/SDA by
    periodicity, then corroborate with structural start/stop detection.
    Confidence combines the role-assignment spread with structural presence
    - never a confidently wrong role assignment on a channel pair with no
    start/stop structure at all."""
    roles = assign_roles(channels)
    scl = channels[roles.scl_channel]
    sda = channels[roles.sda_channel]
    start_stop = detect_start_stop(scl, sda)

    # Real I2C traffic is well-formed: every start is eventually followed by
    # a stop, so a coherent capture always has starts == stops. Coincidental
    # start/stop-*looking* transitions on an unrelated pair of signals (e.g.
    # two unrelated bursts sharing a capture window) tend to scatter instead
    # of pairing up exactly - a much stronger signal than mere presence, so
    # this gates confidence to ~0 rather than just halving it.
    has_structure = (
        bool(start_stop.starts)
        and bool(start_stop.stops)
        and len(start_stop.starts) == len(start_stop.stops)
    )
    structure_term = 1.0 if has_structure else 0.0
    confidence = max(0.0, min(1.0, roles.confidence * structure_term))

    return I2CClaim(
        protocol="I2C",
        scl_channel=roles.scl_channel,
        sda_channel=roles.sda_channel,
        confidence=confidence,
        start_count=len(start_stop.starts),
        stop_count=len(start_stop.stops),
    )
