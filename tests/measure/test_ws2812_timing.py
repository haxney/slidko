"""
WS2812 timing-window violation check (design.md § Check 3, the exact case).
Tests requirements:
- a spec-exact WS2812 train yields no timing finding
- a train with deliberately violated bits flags EXACTLY the injected-fault
  bit indices, index-for-index against the generator's fault label (tasks
  4.1, 4.3)
"""

import pytest

from slidko.measure.edges import extract_edges
from slidko.measure.smoke import detect_ws2812_timing
from tests.synth import SimpleWS2812Generator, inject_ws2812_violation


def test_ws2812_timing_spec_exact_train_is_silent():
    generator = SimpleWS2812Generator(payload=[0x12, 0x34, 0x56, 0x78])
    capture, _ground_truth = generator.generate()
    edges = extract_edges(capture.channels["din"])

    findings = detect_ws2812_timing(edges, capture.samplerate_hz, "din")

    assert findings == []


def test_ws2812_timing_flags_exactly_the_violated_bits():
    generator = SimpleWS2812Generator(payload=[0x12, 0x34, 0x56, 0x78])
    capture, ground_truth = generator.generate()

    capture, ground_truth = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=3
    )
    capture, ground_truth = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=10
    )
    capture, ground_truth = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=21
    )

    edges = extract_edges(capture.channels["din"])
    findings = detect_ws2812_timing(edges, capture.samplerate_hz, "din")

    flagged_bits = {f.evidence["bit_index"] for f in findings}
    assert ground_truth.injected_faults is not None
    injected_bits = {
        fault["bit_index"]
        for fault in ground_truth.injected_faults
        if fault["kind"] == "ws2812_timing_violation"
    }

    assert flagged_bits == injected_bits  # no extras, no misses
    for finding in findings:
        assert finding.check == "timing_violation"
        assert finding.channel == "din"
        assert finding.escalation.startswith("smoke → scope")
        assert "high_ns" in finding.evidence


if __name__ == "__main__":
    pytest.main([__file__])
