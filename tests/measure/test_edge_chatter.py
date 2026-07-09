"""
Edge chatter check (design.md § Check 1). Tests requirements:
- a clean protocol capture yields no chatter finding
- a capture with an injected multi-crossing chatter burst (tests/synth.py's
  inject_chatter) yields a finding whose window covers the injected burst
"""

import pytest

from slidko.measure.edges import extract_edges
from slidko.measure.smoke import detect_edge_chatter
from tests.synth import SimpleUARTGenerator, inject_chatter


def test_edge_chatter_clean_capture():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x0F])
    capture, ground_truth = generator.generate()
    edges = extract_edges(capture.channels["ch0"])
    t_bit = ground_truth.parameters["bit_samples"]

    findings = detect_edge_chatter(edges, t_bit, "ch0")

    assert findings == []


def test_edge_chatter_with_injected_burst():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x0F])
    capture, ground_truth = generator.generate()
    capture, ground_truth = inject_chatter(
        capture, ground_truth, "ch0", num_toggles=4, seed=1
    )
    edges = extract_edges(capture.channels["ch0"])
    t_bit = ground_truth.parameters["bit_samples"]
    assert ground_truth.injected_faults is not None
    fault = ground_truth.injected_faults[-1]

    findings = detect_edge_chatter(edges, t_bit, "ch0")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "edge_chatter"
    assert finding.channel == "ch0"
    # The window must cover the injected burst.
    assert finding.start_sample <= fault["start_sample"]
    assert finding.end_sample >= fault["start_sample"] + fault["num_toggles"] - 1
    assert finding.severity in ("info", "warn", "smoke")
    assert finding.escalation.startswith("smoke → scope")
    assert finding.evidence["instances"] >= 3


if __name__ == "__main__":
    pytest.main([__file__])
