"""
Orchestrator (`run_smoke`) and the false-positive gate - the headline
acceptance criterion (docs/ROADMAP.md Phase 3): silent on every clean
synthetic entry, fires on every dirty one, and every finding is traceable
to its evidence window.
"""

import pytest

from slidko.capture import Capture
from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.from_measure import hypothesis_from_claim
from slidko.decode.native_uart import NativeUARTBackend
from slidko.measure.classify import classify
from slidko.measure.edges import extract_edges
from slidko.measure.smoke import (
    detect_edge_chatter,
    detect_incoherence,
    detect_runt_pulses,
    detect_ws2812_timing,
    run_smoke,
)
from tests.synth import (
    Generator,
    SimpleDShotGenerator,
    SimpleI2CGenerator,
    SimplePWMGenerator,
    SimpleSPIGenerator,
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


def _hypothesis_for_capture(capture, protocol: str) -> ProtocolHypothesis | None:
    """Real Measure classify() -> Decode ProtocolHypothesis, zero manual
    configuration - the same seam production code uses. Protocols Decode
    doesn't cover (WS2812, PWM, DShot, ...) get a hypothesis built directly
    from Measure's Claim, since they're recognition-only in Decode."""
    claims = classify(capture.channels, capture.samplerate_hz)
    matches = [c for c in claims if c.protocol.upper() == protocol.upper()]
    if not matches:
        return None
    claim = matches[0]
    try:
        return hypothesis_from_claim(claim)
    except ValueError:
        return ProtocolHypothesis(
            protocol=claim.protocol.lower(),
            parameters=claim.parameters,
            channel_assignments=claim.channels,
        )


def _clean_matrix():
    """(protocol, generator) pairs across the shared synthetic generator
    matrix - every protocol tests/synth.py supports, swept over parameters,
    no injected faults."""
    cases: list[tuple[str, Generator]] = []
    for baud in (9600, 19200, 115200):
        for payload in ([0x55, 0xAA], [0x00, 0xFF, 0x12]):
            cases.append(("UART", SimpleUARTGenerator(baud=baud, payload=payload)))
    for address in (0x1A, 0x55, 0x68):
        # Non-alternating payloads: SPI/I2C role-assignment confidence is
        # periodicity-based, and a highly alternating payload (e.g. 0x55)
        # can coincidentally depress a data line's score below the
        # classifier's threshold (see phase-2-decode-backend's test_e2e.py).
        for payload in ([0x12, 0x34], [0x11, 0x22, 0x33]):
            cases.append(("I2C", SimpleI2CGenerator(address=address, payload=payload)))
    for cpol in (0, 1):
        for cpha in (0, 1):
            cases.append((
                "SPI",
                SimpleSPIGenerator(
                    cpol=cpol, cpha=cpha, payload=[0x12, 0x34, 0x56, 0x78]
                ),
            ))
    for payload in ([0x00], [0xFF], [0x12, 0x34, 0x56]):
        cases.append(("WS2812", SimpleWS2812Generator(payload=payload)))
    cases.append((
        "PWM",
        SimplePWMGenerator(freq_hz=50.0, pulse_us=1500.0, num_pulses=3),
    ))
    for rate in (150, 300, 600):
        cases.append(("DShot", SimpleDShotGenerator(rate=rate, value=1000)))
    return cases


def test_clean_synthetic_suite_is_silent():
    """The false-positive gate (task 6.2, headline metric): zero findings
    across the entire clean synthetic matrix."""
    total_findings = 0
    checked = 0
    for protocol, generator in _clean_matrix():
        capture, _ground_truth = generator.generate()
        hypothesis = _hypothesis_for_capture(capture, protocol)
        if hypothesis is None:
            # Measure didn't confidently classify this instance - nothing
            # for the smoke detector to run against, not a smoke-detector
            # false positive.
            continue
        findings = run_smoke(capture, hypothesis)
        total_findings += len(findings)
        checked += 1
        assert findings == [], f"false positive on clean {protocol}: {findings}"

    print(
        f"\nclean-suite finding count: {total_findings} (0 expected, "
        f"{checked} captures checked)"
    )
    assert total_findings == 0
    assert checked >= 15  # sanity: the sweep actually classified most cases


def test_dirty_uart_chatter_produces_edge_chatter_finding():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x0F]
    ).generate()
    capture, ground_truth = inject_chatter(
        capture, ground_truth, "ch0", num_toggles=4, seed=1
    )

    findings = run_smoke(capture, UART_HYPOTHESIS)

    assert any(f.check == "edge_chatter" for f in findings)


def test_dirty_uart_glitch_produces_runt_pulse_finding():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x33]
    ).generate()
    capture, ground_truth = inject_glitches(
        capture, ground_truth, "ch0", count=1, pulse_samples=1, seed=3
    )

    findings = run_smoke(capture, UART_HYPOTHESIS)

    assert any(f.check == "runt_pulse" for f in findings)


def test_dirty_ws2812_violation_produces_timing_violation_finding():
    capture, ground_truth = SimpleWS2812Generator(
        payload=[0x12, 0x34, 0x56, 0x78]
    ).generate()
    capture, ground_truth = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=3
    )
    hypothesis = ProtocolHypothesis(
        protocol="ws2812", parameters={}, channel_assignments={"din": "din"}
    )

    findings = run_smoke(capture, hypothesis)

    assert any(f.check == "timing_violation" for f in findings)


def test_dirty_uart_framing_error_produces_incoherence_finding():
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

    findings = run_smoke(corrupted_capture, UART_HYPOTHESIS, events=dirty_events)

    assert any(f.check == "protocol_incoherence" for f in findings)


def _sliced_capture(
    capture: Capture, channel_name: str, start: int, end: int
) -> Capture:
    channel = capture.channels[channel_name]
    lo, hi = max(0, start - 1), min(len(channel), end + 2)
    return Capture(
        channels={channel_name: channel[lo:hi]},
        samplerate_hz=capture.samplerate_hz,
        provenance=capture.provenance,
    )


def test_traceability_edge_chatter():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x0F]
    ).generate()
    capture, ground_truth = inject_chatter(
        capture, ground_truth, "ch0", num_toggles=4, seed=1
    )
    t_bit = ground_truth.parameters["bit_samples"]
    edges = extract_edges(capture.channels["ch0"])
    finding = detect_edge_chatter(edges, t_bit, "ch0")[0]

    sliced = _sliced_capture(capture, "ch0", finding.start_sample, finding.end_sample)
    reproduced = detect_edge_chatter(
        extract_edges(sliced.channels["ch0"]), t_bit, "ch0"
    )

    assert len(reproduced) == 1
    assert reproduced[0].check == "edge_chatter"
    assert reproduced[0].evidence["instances"] == finding.evidence["instances"]


def test_traceability_runt_pulse():
    capture, ground_truth = SimpleUARTGenerator(
        baud=9600, payload=[0x55, 0xAA, 0x33]
    ).generate()
    capture, ground_truth = inject_glitches(
        capture, ground_truth, "ch0", count=1, pulse_samples=1, seed=3
    )
    edges = extract_edges(capture.channels["ch0"])
    finding = detect_runt_pulses(edges, "ch0")[0]

    sliced = _sliced_capture(capture, "ch0", finding.start_sample, finding.end_sample)
    reproduced = detect_runt_pulses(extract_edges(sliced.channels["ch0"]), "ch0")

    assert len(reproduced) == 1
    assert reproduced[0].check == "runt_pulse"
    assert reproduced[0].evidence["pulse_samples"] == finding.evidence["pulse_samples"]


def test_traceability_ws2812_timing():
    capture, ground_truth = SimpleWS2812Generator(
        payload=[0x12, 0x34, 0x56, 0x78]
    ).generate()
    capture, ground_truth = inject_ws2812_violation(
        capture, ground_truth, "din", bit_index=3
    )
    edges = extract_edges(capture.channels["din"])
    finding = detect_ws2812_timing(edges, capture.samplerate_hz, "din")[0]

    sliced = _sliced_capture(capture, "din", finding.start_sample, finding.end_sample)
    reproduced = detect_ws2812_timing(
        extract_edges(sliced.channels["din"]), capture.samplerate_hz, "din"
    )

    assert len(reproduced) == 1
    assert reproduced[0].check == "timing_violation"
    assert reproduced[0].evidence["high_samples"] == finding.evidence["high_samples"]


def test_traceability_protocol_incoherence():
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
    finding = detect_incoherence(dirty_events, UART_HYPOTHESIS)[0]

    windowed_events = [
        e
        for e in dirty_events
        if finding.start_sample <= e.start_sample and e.end_sample <= finding.end_sample
    ]
    reproduced = detect_incoherence(windowed_events, UART_HYPOTHESIS)

    assert len(reproduced) == 1
    assert reproduced[0].check == "protocol_incoherence"
    assert (
        reproduced[0].evidence["framing_error_count"]
        == finding.evidence["framing_error_count"]
    )


if __name__ == "__main__":
    pytest.main([__file__])
