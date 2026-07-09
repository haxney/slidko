"""
Runt/glitch pulse check (design.md § Check 2). Tests requirements:
- a clean protocol capture yields no runt finding
- a capture with an injected 1-2 sample glitch (tests/synth.py's
  inject_glitches) yields a runt finding windowed on the glitch
"""

import pytest

from slidko.measure.edges import extract_edges
from slidko.measure.smoke import detect_runt_pulses
from tests.synth import SimpleUARTGenerator, inject_glitches


def test_runt_pulses_clean_capture():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x33])
    capture, _ground_truth = generator.generate()
    edges = extract_edges(capture.channels["ch0"])

    findings = detect_runt_pulses(edges, "ch0")

    assert findings == []


def test_runt_pulses_with_one_sample_glitch():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x33])
    capture, ground_truth = generator.generate()
    capture, ground_truth = inject_glitches(
        capture, ground_truth, "ch0", count=1, pulse_samples=1, seed=3
    )
    edges = extract_edges(capture.channels["ch0"])
    assert ground_truth.injected_faults is not None
    fault = ground_truth.injected_faults[-1]
    glitch_sample = fault["affected_indices"][0]

    findings = detect_runt_pulses(edges, "ch0")

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "runt_pulse"
    assert finding.channel == "ch0"
    assert finding.start_sample <= glitch_sample <= finding.end_sample
    assert finding.evidence["pulse_samples"] <= 2
    assert finding.escalation.startswith("smoke → scope")


def test_runt_pulses_with_two_sample_glitch():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x55, 0xAA, 0x33])
    capture, ground_truth = generator.generate()
    capture, ground_truth = inject_glitches(
        capture, ground_truth, "ch0", count=1, pulse_samples=2, seed=3
    )
    edges = extract_edges(capture.channels["ch0"])
    assert ground_truth.injected_faults is not None
    fault = ground_truth.injected_faults[-1]
    glitch_sample = fault["affected_indices"][0]

    findings = detect_runt_pulses(edges, "ch0")

    assert len(findings) >= 1
    assert any(
        f.start_sample <= glitch_sample <= f.end_sample and f.check == "runt_pulse"
        for f in findings
    )


if __name__ == "__main__":
    pytest.main([__file__])
