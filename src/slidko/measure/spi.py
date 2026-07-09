"""SPI discriminator - clock/CS/data role assignment, CPOL from idle level,
CPHA via coherent double-decode. Deterministic DSP only - no ML."""

from dataclasses import dataclass

import numpy as np

from slidko.measure.edges import active_window, extract_edges
from slidko.measure.intervals import periodicity_strength


@dataclass(frozen=True)
class SPIRoleAssignment:
    clock_channel: str
    cs_channel: str
    data_channel: str
    confidence: float


@dataclass(frozen=True)
class SPIModeEstimate:
    cpol: int
    cpha: int
    confidence: float


@dataclass(frozen=True)
class SPIClaim:
    protocol: str
    clock_channel: str
    cs_channel: str
    data_channel: str
    cpol: int
    cpha: int
    confidence: float
    cpha_confidence: float


def _transition_count(signal: np.ndarray) -> int:
    return int(np.count_nonzero(np.diff(signal.astype(int))))


def assign_roles(channels: dict[str, np.ndarray]) -> SPIRoleAssignment:
    """CS frames bursts (fewest transitions: assert once, deassert once);
    clock is the bursty-but-regular line (highest periodicity strength among
    the rest); the remainder is data."""
    if len(channels) != 3:
        raise ValueError("SPI role assignment expects exactly three channels")

    names = list(channels)
    transition_counts = {name: _transition_count(channels[name]) for name in names}
    cs_name = min(transition_counts, key=lambda n: transition_counts[n])

    remaining = [n for n in names if n != cs_name]
    start, end = active_window([channels[n] for n in remaining])
    strengths = {n: periodicity_strength(channels[n][start:end]) for n in remaining}
    clock_name = max(strengths, key=lambda n: strengths[n])
    data_name = next(n for n in remaining if n != clock_name)

    spread = strengths[clock_name] - strengths[data_name]
    confidence = max(0.0, min(1.0, spread))
    return SPIRoleAssignment(
        clock_channel=clock_name,
        cs_channel=cs_name,
        data_channel=data_name,
        confidence=confidence,
    )


def clock_confined_to_cs(clock: np.ndarray, cs: np.ndarray) -> float:
    """How CS-like the candidate CS channel really is, combining two
    structural checks real SPI satisfies and coincidental channel pairings
    usually don't:

    - CS toggles exactly twice for a single framed burst (one assert, one
      deassert) - a channel with many more transitions (e.g. a PWM line
      that merely happens to be low most of the time) is not really CS even
      if it won "fewest transitions" among the candidates.
    - every clock edge lands while CS is asserted (low) - the clock never
      runs outside the framed burst.
    """
    cs_transitions = int(np.count_nonzero(np.diff(cs.astype(int))))
    # EMPIRICAL, n=synthetic-only: a single-burst capture's CS toggles
    # exactly twice; treat higher counts as evidence this isn't really CS.
    transition_term = 1.0 if cs_transitions <= 2 else 2.0 / cs_transitions

    clock_edges = extract_edges(clock)
    if not clock_edges:
        return 0.0
    confined = sum(1 for idx, _ in clock_edges if not cs[idx])
    edge_confinement = confined / len(clock_edges)

    return transition_term * edge_confinement


def detect_cpol(clock: np.ndarray, cs: np.ndarray) -> int:
    """CPOL = clock's idle level, sampled while CS is deasserted (high)."""
    idle_mask = cs.astype(bool)
    if not np.any(idle_mask):
        idle_mask = np.ones_like(cs, dtype=bool)
    return int(np.mean(clock[idle_mask]) > 0.5)


def _decode_bits(
    clock: np.ndarray, data: np.ndarray, cpol: int, cpha: int
) -> list[bool]:
    """Sample `data` on the sample-defining edge for the given (cpol, cpha)."""
    clock_idle = bool(cpol)
    sample_on_leading = cpha == 0
    bits: list[bool] = []
    prev = clock_idle
    for i in range(1, len(clock)):
        level = bool(clock[i])
        if level != prev:
            is_leading = level != clock_idle
            if is_leading == sample_on_leading:
                bits.append(bool(data[i]))
        prev = level
    return bits


def _coherence_score(bits: list[bool]) -> float:
    """Fraction of decoded bytes that are printable ASCII.

    EMPIRICAL, n=synthetic-only: a heuristic for picking the correct CPHA
    when both candidate decodes are structurally valid (design.md risk).
    """
    if len(bits) < 8:
        return 0.0
    n_bytes = len(bits) // 8
    printable = 0
    for i in range(n_bytes):
        value = 0
        for b in bits[i * 8 : i * 8 + 8]:
            value = (value << 1) | int(b)
        if 0x20 <= value <= 0x7E:
            printable += 1
    return printable / n_bytes


def detect_cpha(clock: np.ndarray, data: np.ndarray, cpol: int) -> SPIModeEstimate:
    """Decode both CPHA candidates and keep the coherent one. Confidence is
    the coherence-score gap between the two candidates; LOW when both decodes
    look equally coherent (design.md risk)."""
    bits0 = _decode_bits(clock, data, cpol, cpha=0)
    bits1 = _decode_bits(clock, data, cpol, cpha=1)
    score0 = _coherence_score(bits0)
    score1 = _coherence_score(bits1)

    if score0 >= score1:
        cpha, confidence = 0, score0 - score1
    else:
        cpha, confidence = 1, score1 - score0
    return SPIModeEstimate(
        cpol=cpol, cpha=cpha, confidence=max(0.0, min(1.0, confidence))
    )


def classify_spi(channels: dict[str, np.ndarray]) -> SPIClaim:
    """Classify a 3-channel capture as SPI: role-assign clock/CS/data, infer
    CPOL from idle level, then CPHA via coherent double-decode.

    `confidence` (is this group genuinely SPI, via role-assignment spread)
    and `cpha_confidence` (how decisively one CPHA candidate beat the other)
    are kept separate: a correct-but-modest CPHA coherence gap should not
    make the classifier doubt that the group is SPI at all.
    """
    roles = assign_roles(channels)
    clock = channels[roles.clock_channel]
    cs = channels[roles.cs_channel]
    data = channels[roles.data_channel]

    cpol = detect_cpol(clock, cs)
    mode = detect_cpha(clock, data, cpol)
    containment = clock_confined_to_cs(clock, cs)

    return SPIClaim(
        protocol="SPI",
        clock_channel=roles.clock_channel,
        cs_channel=roles.cs_channel,
        data_channel=roles.data_channel,
        cpol=cpol,
        cpha=mode.cpha,
        confidence=max(0.0, min(1.0, roles.confidence * containment)),
        cpha_confidence=mode.confidence,
    )
