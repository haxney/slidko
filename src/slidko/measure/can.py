"""CAN recognition - bit-stuffing signature + standard bitrate table.
Recognition only (docs/ROADMAP.md Phase 1 scope) - no frame decode."""

from itertools import pairwise

import numpy as np

from slidko.measure.edges import extract_edges, inter_edge_intervals

STANDARD_CAN_BITRATES = [125_000, 250_000, 500_000, 1_000_000]

# EMPIRICAL, n=synthetic-only.
BITRATE_SNAP_TOLERANCE = 0.05
MAX_LEGAL_RUN_BITS = 5  # bit-stuffing forbids 6+ identical consecutive bits
RECOGNITION_THRESHOLD = 0.7


def estimate_bit_period(edges: list[tuple[int, bool]]) -> float | None:
    """Same closed-form min + integer-multiple-refine estimate used by UART
    auto-baud (measure/uart.py)."""
    intervals = inter_edge_intervals(edges)
    if len(intervals) == 0:
        return None
    candidate = float(np.min(intervals))
    if candidate <= 0:
        return None
    multiples = np.maximum(1, np.round(intervals / candidate)).astype(np.int64)
    return float(np.mean(intervals / multiples))


def _run_lengths_in_bits(channel: np.ndarray, bit_period: float) -> list[int]:
    if len(channel) == 0 or bit_period <= 0:
        return []
    change_idx = np.flatnonzero(np.diff(channel.astype(int)) != 0) + 1
    boundaries = np.concatenate([[0], change_idx, [len(channel)]])
    return [round((end - start) / bit_period) for start, end in pairwise(boundaries)]


def recognize(
    channel: np.ndarray, samplerate_hz: int
) -> tuple[bool, float, int | None]:
    """(recognized, confidence, bitrate). Confidence combines: the inferred
    bit period snapping cleanly to a standard CAN bitrate, and no run
    exceeding the bit-stuffing structural limit (5 identical consecutive
    bits)."""
    edges = extract_edges(channel)
    bit_period = estimate_bit_period(edges)
    if bit_period is None or bit_period <= 0:
        return False, 0.0, None

    raw_bitrate = samplerate_hz / bit_period
    bitrate = min(STANDARD_CAN_BITRATES, key=lambda b: abs(b - raw_bitrate) / b)
    rel_error = abs(bitrate - raw_bitrate) / bitrate
    bitrate_confidence = max(0.0, 1.0 - rel_error / BITRATE_SNAP_TOLERANCE)

    run_lengths = _run_lengths_in_bits(channel, bit_period)
    legal = [r <= MAX_LEGAL_RUN_BITS for r in run_lengths]
    stuffing_confidence = sum(legal) / len(legal) if legal else 0.0

    confidence = max(0.0, min(1.0, bitrate_confidence * stuffing_confidence))
    return confidence >= RECOGNITION_THRESHOLD, confidence, bitrate
