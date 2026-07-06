"""Interval analysis functions for Slidko protocol detection."""

import numpy as np


def compute_interval_histogram(
    edges: list[int], bin_width: int = 1
) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute histogram of intervals between consecutive edges.

    Args:
        edges: List of edge timestamps
        bin_width: Width of histogram bins

    Returns:
        Tuple of (bin_edges, counts) arrays
    """
    if len(edges) < 2:
        return np.array([]), np.array([])

    # Calculate intervals between consecutive edges
    intervals = np.diff(edges)

    # Create histogram bins based on interval range and bin_width
    min_interval = int(np.min(intervals))
    max_interval = int(np.max(intervals))

    # Handle edge case where all intervals are the same value
    if min_interval == max_interval:
        # Add one more bin so that we can get a meaningful histogram
        bin_edges = np.array([min_interval, max_interval + bin_width])
        counts = np.array([len(intervals)])
    else:
        bin_edges = np.arange(min_interval, max_interval + bin_width, bin_width)
        # Compute histogram
        counts, _ = np.histogram(intervals, bins=bin_edges)

    return bin_edges[:-1], counts


def estimate_period_from_intervals(edges: list[int]) -> float | None:
    """
    Estimate signal period from edge timestamps.

    Args:
        edges: List of edge timestamps

    Returns:
        Estimated period in samples, or None if insufficient data
    """
    if len(edges) < 3:
        return None

    # Compute intervals between consecutive edges
    intervals = np.diff(edges)

    # Return median interval (more robust than mean)
    return float(np.median(intervals))


def detect_square_wave_frequency(edges: list[int], sample_rate_hz: int) -> float | None:
    """
    Detect frequency of a square wave from edge timestamps.

    Args:
        edges: List of edge timestamps
        sample_rate_hz: Sample rate in Hz

    Returns:
        Frequency in Hz, or None if insufficient data
    """
    period = estimate_period_from_intervals(edges)
    if period is None:
        return None

    # Convert period (in samples) to frequency (Hz)
    return sample_rate_hz / period


def compute_autocorrelation(edges: list[int], max_lag: int | None = None) -> np.ndarray:
    """
    Compute autocorrelation of edge intervals.

    Args:
        edges: List of edge timestamps
        max_lag: Maximum lag to consider

    Returns:
        Autocorrelation values
    """
    if len(edges) < 2:
        return np.array([])

    # Convert to intervals first
    intervals = np.diff(edges)

    if max_lag is None:
        max_lag = len(intervals) // 2

    # Compute autocorrelation
    autocorr = []
    for lag in range(max_lag):
        if lag >= len(intervals):
            break

        # Calculate correlation at this lag
        if len(intervals[lag:]) > 0:
            corr = np.corrcoef(
                intervals[:-lag] if lag > 0 else intervals, intervals[lag:]
            )[0, 1]
        else:
            corr = 0.0

        autocorr.append(corr)

    return np.array(autocorr)
