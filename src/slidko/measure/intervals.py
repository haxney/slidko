"""Interval-domain and autocorrelation primitives shared by every Phase 1
discriminator (SCL regularity, SPI clock burst detection, PWM base rate).
Deterministic DSP only - no ML."""

import numpy as np
from scipy.signal import fftconvolve


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

    intervals = np.diff(edges)

    min_interval = int(np.min(intervals))
    max_interval = int(np.max(intervals))

    if min_interval == max_interval:
        bin_edges = np.array([min_interval, max_interval + bin_width])
        counts = np.array([len(intervals)])
    else:
        bin_edges = np.arange(min_interval, max_interval + bin_width, bin_width)
        counts, _ = np.histogram(intervals, bins=bin_edges)

    return bin_edges[:-1], counts


def dominant_interval(edges: list[int], bin_width: int = 1) -> tuple[float, float]:
    """Dominant interval-histogram cluster and its confidence.

    Confidence is the dominant bin's share of all intervals - a simple,
    closed-form concentration score in [0, 1]: 1.0 for a perfectly clean
    square wave (every interval falls in one bin), lower as intervals spread
    across bins (jitter, mixed data).
    """
    if len(edges) < 2:
        return 0.0, 0.0
    intervals = np.diff(edges)
    bin_edges, counts = compute_interval_histogram(edges, bin_width=bin_width)
    if len(counts) == 0:
        return 0.0, 0.0
    peak_idx = int(np.argmax(counts))
    dominant_value = float(bin_edges[peak_idx]) + bin_width / 2.0
    confidence = float(counts[peak_idx]) / float(len(intervals))
    return dominant_value, confidence


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
    intervals = np.diff(edges)
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
    return sample_rate_hz / period


def compute_autocorrelation(
    signal: np.ndarray, max_lag: int | None = None
) -> np.ndarray:
    """
    Normalized autocorrelation of a sampled signal for lags 0..max_lag
    (ac[0] == 1.0 by construction).

    Args:
        signal: Sample array (boolean or numeric)
        max_lag: Maximum lag to consider; defaults to half the signal length

    Returns:
        Autocorrelation values indexed by lag, ac[0] first
    """
    x = np.asarray(signal, dtype=float)
    n = len(x)
    if n < 2:
        return np.array([])
    x = x - x.mean()

    if max_lag is None:
        max_lag = n // 2
    max_lag = max(1, min(max_lag, n - 1))

    # FFT-based convolution: O(n log n) instead of np.correlate's O(n^2),
    # which is catastrophic on realistic captures (a low-baud UART channel
    # at 24 MS/s easily runs to hundreds of thousands of samples).
    full = fftconvolve(x, x[::-1], mode="full")
    zero_idx = len(full) // 2
    ac0 = full[zero_idx]
    if ac0 <= 0:
        return np.zeros(max_lag + 1)
    return np.asarray(full[zero_idx : zero_idx + max_lag + 1] / ac0)


def estimate_dominant_period(
    signal: np.ndarray, max_lag: int | None = None
) -> tuple[float, float]:
    """
    Estimate the dominant clock period of a channel via autocorrelation.

    Long flat runs (a slowly-toggling square wave sampled at high rate) make
    the autocorrelation trivially high near lag 0 - this is not the period,
    just the signal's own smoothness. The standard pitch-detection fix: skip
    the initial monotonic decay from lag 0 until autocorrelation starts
    climbing again (a trough), then take the peak after that trough as the
    fundamental period. Confidence is the normalized autocorrelation value at
    that peak, in [0, 1].

    Returns:
        (period_samples, confidence). (0.0, 0.0) if no periodicity is found.
    """
    ac = compute_autocorrelation(signal, max_lag=max_lag)
    if len(ac) < 3:
        return 0.0, 0.0

    deriv = np.diff(ac)
    recovering = np.flatnonzero(deriv > 0)
    if len(recovering) == 0:
        return 0.0, 0.0
    search_start = int(recovering[0]) + 1

    search_region = ac[search_start:]
    if len(search_region) == 0:
        return 0.0, 0.0
    peak_offset = int(np.argmax(search_region))
    peak_lag = search_start + peak_offset
    confidence = float(np.clip(ac[peak_lag], 0.0, 1.0))
    return float(peak_lag), confidence


def periodicity_strength(signal: np.ndarray, max_lag: int | None = None) -> float:
    """[0, 1] periodicity score shared by discriminators (SCL regularity,
    SPI clock burst detection, PWM base rate) - the confidence half of
    `estimate_dominant_period`."""
    _, confidence = estimate_dominant_period(signal, max_lag=max_lag)
    return confidence
