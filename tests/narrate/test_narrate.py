"""
The narrate() orchestrator (design.md § Module composition, task group 6):
composes transaction summaries, coincidences, and the receiver-rule caveat
into one assertion set, and every assertion's evidence survives a JSON
round trip and still indexes valid events/sample ranges in the source
capture.
"""

import pytest

from slidko.capture import Capture
from slidko.corpus.sidecar import Sidecar
from slidko.decode.events import DecodedEvent
from slidko.measure.smoke import SmokeFinding
from slidko.narrate.model import Assertion
from slidko.narrate.narrate import narrate
from tests.synth import SimpleI2CGenerator

KILLER_CASE_SIDECAR: dict = {
    "id": "cell-ws2812-cat6-len/entry-0042",
    "capture_file": "entry-0042.sr",
    "instrument": {
        "model": "fx2lafw-clone",
        "samplerate_hz": 24000000,
        "threshold_v": 1.4,
        "channels": {"0": "DATA", "7": "SYNC"},
    },
    "driver": {"chip": "...", "vdd_v": 3.3, "series_r_ohm": 0},
    "transport": {
        "cable": "cat6-utp",
        "length_m": 10,
        "twisted": True,
        "shielded": False,
        "termination": "none",
    },
    "receiver": {"part": "WS2812B", "vdd_v": 5.0, "vih_v": 3.5},
    "protocol": {"name": "ws2812", "nominal": {"bitrate_hz": 800000}},
    "fault_injected": {"class": "level-mismatch", "params": {}},
    "receiver_verdict": {
        "observed": "flicker",
        "notes": "",
        "contemporaneous": True,
    },
    "sweep_cell": None,
    "referee": None,
}


def _mixed_scenario():
    """A capture + events + findings exercising every assertion kind
    narrate() composes: transaction.summary, coincidence, and (via the
    killer-case sidecar) receiver_rule.caveat."""
    capture, _ground_truth = SimpleI2CGenerator(
        address=0x68, payload=[0x12, 0x34]
    ).generate()
    capture = Capture(
        channels=capture.channels,
        samplerate_hz=capture.samplerate_hz,
        provenance={**capture.provenance, "threshold_v": 1.4},
    )
    events = [
        DecodedEvent(
            kind="i2c.start", start_sample=0, end_sample=0, data={"address": 0x68}
        ),
        DecodedEvent(
            kind="i2c.address",
            start_sample=10,
            end_sample=100,
            data={"address": 0x68, "rw": "write"},
        ),
        DecodedEvent(kind="i2c.ack", start_sample=101, end_sample=110, data={}),
        DecodedEvent(
            kind="i2c.nak", start_sample=200, end_sample=210, data={"address": 0x68}
        ),
        DecodedEvent(kind="i2c.stop", start_sample=211, end_sample=211, data={}),
    ]
    findings = [
        SmokeFinding(
            check="timing_violation",
            channel="scl",
            start_sample=205,
            end_sample=209,
            severity="warn",
            summary="test finding coincident with the NAK",
            escalation="smoke → scope: test",
            evidence={},
        )
    ]
    sidecar = Sidecar.from_json(KILLER_CASE_SIDECAR)
    return capture, events, findings, sidecar


def test_narrate_composes_all_three_groups():
    capture, events, findings, sidecar = _mixed_scenario()

    assertions = narrate(capture, events, findings, sidecar=sidecar)

    kinds = {a.kind for a in assertions}
    assert "transaction.summary" in kinds
    assert "coincidence" in kinds
    assert "receiver_rule.caveat" in kinds


def test_narrate_every_assertion_has_non_empty_evidence():
    capture, events, findings, sidecar = _mixed_scenario()

    assertions = narrate(capture, events, findings, sidecar=sidecar)

    assert assertions
    for assertion in assertions:
        evidence = assertion.evidence
        assert evidence.event_indices or evidence.sample_ranges or evidence.finding_refs


def _asserts_positive_health_claim(text: str) -> bool:
    """True if `text` claims the bus/receiver IS healthy - i.e. contains
    "healthy" without a nearby negation ("not", "n't", "no ")."""
    lowered = text.lower()
    idx = lowered.find("healthy")
    while idx != -1:
        window = lowered[max(0, idx - 25) : idx]
        if not any(neg in window for neg in ("not ", "n't ", "no ")):
            return True
        idx = lowered.find("healthy", idx + 1)
    return False


def test_narrate_assertion_set_contains_no_bus_healthy_claim():
    """The killer case: decode looks clean, but no assertion in the full
    set may claim the bus is healthy."""
    capture, events, findings, sidecar = _mixed_scenario()

    assertions = narrate(capture, events, findings, sidecar=sidecar)

    for assertion in assertions:
        assert not _asserts_positive_health_claim(assertion.text)


def test_traceability_survives_serialization():
    """Serialize the assertion set, reload, and confirm each assertion's
    evidence still indexes valid events/sample ranges in the source
    capture."""
    capture, events, findings, sidecar = _mixed_scenario()
    n_samples = len(next(iter(capture.channels.values())))

    assertions = narrate(capture, events, findings, sidecar=sidecar)
    assert assertions

    reloaded = [Assertion.from_json(a.to_json()) for a in assertions]
    assert reloaded == assertions

    for assertion in reloaded:
        for event_idx in assertion.evidence.event_indices:
            assert 0 <= event_idx < len(events)
        for finding_idx in assertion.evidence.finding_refs:
            assert 0 <= finding_idx < len(findings)
        for start, end in assertion.evidence.sample_ranges:
            assert 0 <= start <= end < n_samples


if __name__ == "__main__":
    pytest.main([__file__])
