import itertools

import numpy as np

from slidko.measure.edges import (
    extract_edges,
    inter_edge_intervals,
    same_polarity_intervals,
)


def _square_wave(
    period_samples: int, n_periods: int, start_high: bool = False
) -> np.ndarray:
    """Generate an alternating square wave with a fixed half-period in samples."""
    half = period_samples // 2
    level = start_high
    chunks = []
    for _ in range(n_periods * 2):
        chunks.append(np.full(half, level, dtype=bool))
        level = not level
    return np.concatenate(chunks)


def test_square_wave_interval_exactness():
    """1 kHz square wave at 24 MS/s: intervals exactly 12000 samples, strict
    polarity alternation."""
    sample_rate_hz = 24_000_000
    freq_hz = 1_000
    period_samples = sample_rate_hz // freq_hz  # 24000 samples/period
    half_period = period_samples // 2  # 12000

    data = _square_wave(period_samples, n_periods=10)
    edges = extract_edges(data)

    assert len(edges) > 1
    intervals = inter_edge_intervals(edges)
    assert np.all(intervals == half_period)

    polarities = [polarity for _, polarity in edges]
    for a, b in itertools.pairwise(polarities):
        assert a != b


def test_no_spurious_edge_at_start_when_array_begins_mid_level():
    """No edge is reported at index 0 even when the array begins high (no
    transition into the first sample)."""
    data = np.array([True, True, True, False, False, True], dtype=bool)
    edges = extract_edges(data)
    assert all(idx != 0 for idx, _ in edges)


def test_no_spurious_edge_at_end_when_array_ends_mid_level():
    """No edge is reported at the final index when the array ends mid-level
    (no transition after the last sample)."""
    data = np.array([False, True, True, False, False, False], dtype=bool)
    edges = extract_edges(data)
    last_index = len(data) - 1
    assert all(idx != last_index for idx, _ in edges)


def test_all_constant_channel_has_zero_edges():
    """A channel that never transitions yields zero edges."""
    assert extract_edges(np.zeros(100, dtype=bool)) == []
    assert extract_edges(np.ones(100, dtype=bool)) == []


def test_interval_helpers_match_generator_ground_truth():
    """Interval helpers match the exact spacing used to build the synthetic
    edge stream."""
    period_samples = 240
    data = _square_wave(period_samples, n_periods=5)
    edges = extract_edges(data)

    half_period = period_samples // 2
    inter_edge = inter_edge_intervals(edges)
    assert np.all(inter_edge == half_period)

    same_polarity = same_polarity_intervals(edges)
    assert np.all(same_polarity == period_samples)
