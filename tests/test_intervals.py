"""Tests for interval analysis functions in measure/intervals.py."""

import numpy as np
import pytest

from slidko.measure.intervals import (
    compute_autocorrelation,
    compute_interval_histogram,
    detect_square_wave_frequency,
    estimate_period_from_intervals,
)


def test_compute_interval_histogram():
    """Test computation of interval histogram."""
    # Simple case - edges at 0, 10, 20, 30 (intervals of 10)
    edges = [0, 10, 20, 30]
    bin_edges, counts = compute_interval_histogram(edges)

    assert len(bin_edges) == len(counts)
    assert len(counts) > 0
    # Should have one interval of 10 with count 3 (4 edges -> 3 intervals)


def test_estimate_period_from_intervals():
    """Test period estimation from intervals."""
    # Regular interval case - edges at 0, 10, 20, 30 (period = 10)
    edges = [0, 10, 20, 30]
    period = estimate_period_from_intervals(edges)

    assert period == 10.0

    # Edge case - too few edges
    edges = [0, 10]
    period = estimate_period_from_intervals(edges)

    assert period is None


def test_detect_square_wave_frequency():
    """Test square wave frequency detection."""
    # Simulate square wave at sample rate of 24MHz with 100 samples period
    edges = [0, 100, 200, 300, 400]
    freq = detect_square_wave_frequency(edges, sample_rate_hz=24_000_000)

    # Should be 24MHz / 100 samples = 240kHz
    assert freq == 240000.0


def test_compute_autocorrelation():
    """Test autocorrelation computation."""
    edges = [0, 10, 20, 30, 40]
    autocorr = compute_autocorrelation(edges)

    # Should return array with some values
    assert isinstance(autocorr, np.ndarray)
    assert len(autocorr) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
