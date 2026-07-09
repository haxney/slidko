"""Tests for interval/autocorrelation primitives in measure/intervals.py."""

import numpy as np
import pytest

from slidko.measure.intervals import (
    compute_interval_histogram,
    dominant_interval,
    estimate_dominant_period,
    periodicity_strength,
)
from tests.synth import SimpleI2CGenerator, expand_segments


def _square_wave(half_period: int, cycles: int) -> np.ndarray:
    return np.tile(np.array([True] * half_period + [False] * half_period), cycles)


def test_compute_interval_histogram_single_cluster():
    half = 15
    wave = _square_wave(half, cycles=30)
    edges = [int(i) for i in np.flatnonzero(np.diff(wave.astype(int)) != 0) + 1]

    bin_edges, counts = compute_interval_histogram(edges)
    assert len(counts) == 1  # every interval is the half-period: one bin
    assert bin_edges[0] == half

    value, confidence = dominant_interval(edges)
    assert value == pytest.approx(half, abs=1)
    assert confidence == pytest.approx(1.0)


def test_estimate_dominant_period_known_period_recovery():
    half = 15
    wave = _square_wave(half, cycles=30)

    period, confidence = estimate_dominant_period(wave)

    assert period == 2 * half
    assert confidence >= 0.9


def test_estimate_dominant_period_confidence_degrades_under_jitter():
    half = 15
    cycles = 30
    clean = _square_wave(half, cycles)
    clean_period, clean_confidence = estimate_dominant_period(clean)
    assert clean_confidence >= 0.9

    rng = np.random.default_rng(0)
    segments = []
    for _ in range(cycles):
        h_high = max(1, half + int(rng.integers(-4, 5)))
        h_low = max(1, half + int(rng.integers(-4, 5)))
        segments.append((True, h_high))
        segments.append((False, h_low))
    jittered = expand_segments(segments)

    jittered_period, jittered_confidence = estimate_dominant_period(jittered)

    # Never confidently wrong: either the period survives, or confidence fell.
    if abs(jittered_period - clean_period) > 2:
        assert jittered_confidence < 0.5
    else:
        assert jittered_confidence < clean_confidence


def test_periodicity_strength_separates_scl_from_sda():
    capture, _ = SimpleI2CGenerator(
        address=0x42, payload=[0xDE, 0xAD, 0xBE, 0xEF]
    ).generate()
    scl = capture.channels["scl"]
    sda = capture.channels["sda"]

    scl_strength = periodicity_strength(scl)
    sda_strength = periodicity_strength(sda)

    assert scl_strength > sda_strength
