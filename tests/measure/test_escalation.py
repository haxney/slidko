"""
Structured findings + escalation (design.md § Finding schema). Every
finding, from every one of the four checks, must carry a non-empty
`escalation` string of the form `smoke → scope: ...` and an `evidence`
dict with the numbers backing `summary`.
"""

import pytest

from slidko.capture import Capture
from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.events import DecodedEvent
from slidko.decode.native_uart import NativeUARTBackend
from slidko.measure.edges import extract_edges
from slidko.measure.smoke import (
    detect_edge_chatter,
    detect_incoherence,
    detect_runt_pulses,
    detect_ws2812_timing,
)
from tests.synth import (
    SimpleUARTGenerator,
    SimpleWS2812Generator,
    inject_chatter,
    inject_glitches,
    inject_ws2812_violation,
)

UART_HYPOTHESIS = ProtocolHypothesis(
    protocol="uart",
    parameters={
        "baud": 9600,
        "data_bits": 8,
        "parity": "none",
        "stop_bits": 1.0,
        "rx_channel": "ch0",
    },
    channel_assignments={"rx": "ch0"},
)


def _assert_well_formed(findings):
    assert findings, "expected at least one finding to check"
    for finding in findings:
        assert finding.escalation
        assert finding.escalation.startswith("smoke → scope:")
        assert isinstance(finding.evidence, dict)
        assert finding.evidence  # non-empty
        assert finding.summary  # non-empty, human-readable


def test_edge_chatter_finding_is_well_formed():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x0F]
    ).generate()
    capture, ground_truth = inject_chatter(
        capture, ground_truth, "ch0", num_toggles=4, seed=1
    )
    edges = extract_edges(capture.channels["ch0"])
    findings = detect_edge_chatter(edges, ground_truth.parameters["bit_samples"], "ch0")
    _assert_well_formed(findings)


def test_runt_pulse_finding_is_well_formed():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x33]
    ).generate()
    capture, ground_truth = inject_glitches(
        capture, ground_truth, "ch0", count=1, pulse_samples=1, seed=3
    )
    edges = extract_edges(capture.channels["ch0"])
    findings = detect_runt_pulses(edges, "ch0")
    _assert_well_formed(findings)


def test_timing_violation_finding_is_well_formed():
    capture, ground_truth = SimpleWS2812Generator(
        payload=[0x12, 0x34, 0x56, 0x78]
    ).generate()
    capture, ground_truth = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=3
    )
    edges = extract_edges(capture.channels["din"])
    findings = detect_ws2812_timing(edges, capture.samplerate_hz, "din")
    _assert_well_formed(findings)


def test_protocol_incoherence_finding_is_well_formed():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x11, 0x22, 0x33]
    ).generate()
    backend = NativeUARTBackend()
    clean_events = backend.decode(capture, UART_HYPOTHESIS)
    bit_samples = ground_truth.parameters["bit_samples"]

    channel = capture.channels["ch0"].copy()
    frame = clean_events[1]
    channel[frame.end_sample - bit_samples + 1 : frame.end_sample + 1] = False
    corrupted_capture = Capture(
        channels={"ch0": channel},
        samplerate_hz=capture.samplerate_hz,
        provenance=capture.provenance,
    )
    dirty_events = backend.decode(corrupted_capture, UART_HYPOTHESIS)
    findings = detect_incoherence(dirty_events, UART_HYPOTHESIS)
    _assert_well_formed(findings)

    # I2C orphan-ack path too.
    orphan_events = [
        DecodedEvent(kind="i2c.ack", start_sample=50, end_sample=60, data={})
    ]
    i2c_hypothesis = ProtocolHypothesis(
        protocol="i2c",
        parameters={"scl_channel": "scl", "sda_channel": "sda"},
        channel_assignments={"scl": "scl", "sda": "sda"},
    )
    _assert_well_formed(detect_incoherence(orphan_events, i2c_hypothesis))


if __name__ == "__main__":
    pytest.main([__file__])
