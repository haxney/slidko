"""UART auto-baud discriminator.

Per docs/ROADMAP.md Phase 1: baud = min/GCD of inter-edge intervals snapped
to the standard baud table; SBUS is a data-driven exception, not branching
logic. Deterministic DSP only - no ML.
"""

from dataclasses import dataclass

import numpy as np

from slidko.measure.edges import extract_edges, inter_edge_intervals

# Standard UART baud rates a bench UART might run at.
STANDARD_BAUDS = [
    110,
    300,
    600,
    1200,
    2400,
    4800,
    9600,
    14400,
    19200,
    28800,
    38400,
    57600,
    76800,
    115200,
    230400,
    250000,
    460800,
    500000,
    921600,
    1000000,
]

# SBUS runs at a non-standard baud with a non-8N1 frame; treated as an
# explicit exception rather than snapped generically.
SBUS_BAUD = 100_000
SBUS_FRAME = {"data_bits": 8, "parity": "even", "stop_bits": 2.0}
DEFAULT_FRAME = {"data_bits": 8, "parity": "none", "stop_bits": 1.0}

# EMPIRICAL, n=synthetic-only: a snap within 3% of a table entry is treated
# as a clean match; wider deviations degrade confidence rather than being
# rejected outright.
BAUD_SNAP_TOLERANCE = 0.03

# EMPIRICAL, n=synthetic-only: a start-bit low-run within 15% of an integer
# number of bit periods counts as correctly framed.
FRAMING_ERROR_TOLERANCE = 0.15


@dataclass(frozen=True)
class BaudEstimate:
    baud: int
    frame: dict
    confidence: float
    idle_high: bool


def estimate_bit_period(edges: list[tuple[int, bool]]) -> float | None:
    """Closed-form bit-period estimate.

    Takes the minimum inter-edge interval as an initial guess (a lone-bit
    transition is the shortest legal interval), then refines by averaging
    every interval divided by its nearest-integer multiple of that guess -
    an approximate GCD that tolerates sampling-grid rounding.
    """
    intervals = inter_edge_intervals(edges)
    if len(intervals) == 0:
        return None
    candidate = float(np.min(intervals))
    if candidate <= 0:
        return None
    multiples = np.maximum(1, np.round(intervals / candidate)).astype(np.int64)
    return float(np.mean(intervals / multiples))


def detect_idle_level(channel: np.ndarray) -> bool:
    """Majority sample level; UART idles high (True) in the v1 protocol universe."""
    return bool(np.mean(channel) > 0.5)


def snap_to_baud_table(raw_baud: float) -> tuple[int, dict, float]:
    """Snap a raw baud estimate to the nearest standard baud or the SBUS
    exception, returning (baud, frame_params, relative_error)."""
    candidates = [(b, DEFAULT_FRAME) for b in STANDARD_BAUDS] + [
        (SBUS_BAUD, SBUS_FRAME)
    ]
    best_baud, best_frame = min(candidates, key=lambda c: abs(c[0] - raw_baud) / c[0])
    rel_error = abs(best_baud - raw_baud) / best_baud
    return best_baud, best_frame, rel_error


def check_start_bit_framing(
    channel: np.ndarray,
    edges: list[tuple[int, bool]],
    bit_period: float,
    idle_high: bool,
) -> float:
    """Fraction of idle-departure edges whose active-level run rounds
    cleanly to an integer number of bit periods (a coarse framing sanity
    check - not a full start/stop/parity decode, which is Decode's job)."""
    if bit_period <= 0:
        return 0.0
    active_level = not idle_high
    departures = [idx for idx, polarity in edges if polarity == active_level]
    if not departures:
        return 0.0

    n = len(channel)
    scored = 0
    for start in departures:
        end = start
        while end < n and channel[end] == active_level:
            end += 1
        run_len = end - start
        nearest_multiple = round(run_len / bit_period)
        if nearest_multiple < 1:
            continue
        err = abs(run_len - nearest_multiple * bit_period) / bit_period
        if err < FRAMING_ERROR_TOLERANCE:
            scored += 1
    return scored / len(departures)


def infer_uart(channel: np.ndarray, samplerate_hz: int) -> BaudEstimate:
    """Auto-baud: infer baud + frame parameters from a single UART channel
    with zero manually supplied parameters."""
    edges = extract_edges(channel)
    idle_high = detect_idle_level(channel)

    bit_period = estimate_bit_period(edges)
    if bit_period is None or bit_period <= 0:
        return BaudEstimate(
            baud=0, frame=DEFAULT_FRAME, confidence=0.0, idle_high=idle_high
        )

    raw_baud = samplerate_hz / bit_period
    baud, frame, rel_error = snap_to_baud_table(raw_baud)
    framing_score = check_start_bit_framing(channel, edges, bit_period, idle_high)

    snap_confidence = max(0.0, 1.0 - rel_error / BAUD_SNAP_TOLERANCE)
    confidence = max(0.0, min(1.0, snap_confidence * (0.5 + 0.5 * framing_score)))

    return BaudEstimate(
        baud=baud, frame=frame, confidence=confidence, idle_high=idle_high
    )
