"""Tests for fault/jitter injection (tests/synth.py)."""

import numpy as np

from tests.synth import (
    SimpleUARTGenerator,
    SimpleWS2812Generator,
    inject_glitches,
    inject_jitter,
    inject_ws2812_violation,
)

WINDOW_NS = 150


def test_jitter_injection_is_seed_reproducible():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x3C]
    ).generate()

    a_capture, a_gt = inject_jitter(
        capture, ground_truth, "ch0", jitter_frac=0.1, seed=42
    )
    b_capture, b_gt = inject_jitter(
        capture, ground_truth, "ch0", jitter_frac=0.1, seed=42
    )

    assert np.array_equal(a_capture.channels["ch0"], b_capture.channels["ch0"])
    assert a_gt.injected_faults == b_gt.injected_faults


def test_jitter_injection_differs_with_different_seed():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x3C, 0x12, 0x99]
    ).generate()

    a_capture, _ = inject_jitter(capture, ground_truth, "ch0", jitter_frac=0.15, seed=1)
    b_capture, _ = inject_jitter(capture, ground_truth, "ch0", jitter_frac=0.15, seed=2)

    assert not np.array_equal(a_capture.channels["ch0"], b_capture.channels["ch0"])


def test_jitter_injection_records_fault_in_label():
    capture, ground_truth = SimpleUARTGenerator(baud=9600, payload=[0x55]).generate()
    _, gt = inject_jitter(capture, ground_truth, "ch0", jitter_frac=0.1, seed=7)

    assert gt.injected_faults is not None
    assert len(gt.injected_faults) == 1
    fault = gt.injected_faults[0]
    assert fault["kind"] == "jitter"
    assert fault["channel"] == "ch0"
    assert fault["seed"] == 7
    # Original label is untouched (functional update).
    assert ground_truth.injected_faults == []


def test_glitch_injection_reproducible_and_labeled():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x3C]
    ).generate()

    a_capture, a_gt = inject_glitches(
        capture, ground_truth, "ch0", count=5, pulse_samples=1, seed=3
    )
    b_capture, b_gt = inject_glitches(
        capture, ground_truth, "ch0", count=5, pulse_samples=1, seed=3
    )

    assert np.array_equal(a_capture.channels["ch0"], b_capture.channels["ch0"])
    assert a_gt.injected_faults is not None
    fault = a_gt.injected_faults[0]
    assert fault["kind"] == "glitch"
    assert len(fault["affected_indices"]) == 5
    assert a_gt.injected_faults == b_gt.injected_faults

    # The glitched channel actually differs from clean at the recorded indices.
    clean = capture.channels["ch0"]
    for idx in fault["affected_indices"]:
        assert bool(a_capture.channels["ch0"][idx]) != bool(clean[idx])


def test_ws2812_violation_is_labeled_and_actually_violates_window():
    capture, ground_truth = SimpleWS2812Generator(payload=[0x55]).generate()
    sample_ns = 1e9 / capture.samplerate_hz

    violated_capture, violated_gt = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=2, violation_ns=600
    )

    assert violated_gt.injected_faults is not None
    fault = violated_gt.injected_faults[0]
    assert fault["kind"] == "ws2812_timing_violation"
    assert fault["bit_index"] == 2
    assert ground_truth.injected_faults == []  # original untouched

    channel = violated_capture.channels["din"]
    rising = [
        i + 1 for i in range(len(channel) - 1) if not channel[i] and channel[i + 1]
    ]
    start = rising[2]
    end = start
    while end < len(channel) and channel[end]:
        end += 1
    high_ns = (end - start) * sample_ns

    t0h_lo, t0h_hi = 400 - WINDOW_NS, 400 + WINDOW_NS
    t1h_lo, t1h_hi = 800 - WINDOW_NS, 800 + WINDOW_NS
    assert not (t0h_lo <= high_ns <= t0h_hi)
    assert not (t1h_lo <= high_ns <= t1h_hi)
