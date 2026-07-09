"""
The receiver rule (design.md § Receiver-rule caveat) - the killer case
(docs/DESIGN.md § The receiver rule): a capture that decodes cleanly at the
instrument's own threshold must not be taken as evidence the real receiver
saw a clean signal, when its V_IH differs materially and the receiver
verdict disagrees.
"""

import numpy as np
import pytest

from slidko.capture import Capture
from slidko.corpus.sidecar import Sidecar
from slidko.narrate.receiver_rule import receiver_rule_caveat

# The WS2812 killer case from docs/CORPUS.md verbatim.
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
        "notes": "5V strip driven at 3.3V over 10m cat6",
        "contemporaneous": True,
    },
    "sweep_cell": None,
    "referee": None,
}


def _capture(threshold_v: float) -> Capture:
    return Capture(
        channels={"din": np.zeros(10, dtype=bool)},
        samplerate_hz=24_000_000,
        provenance={"threshold_v": threshold_v},
    )


def test_killer_case_emits_caveat_naming_both_thresholds_no_health_claim():
    sidecar = Sidecar.from_json(KILLER_CASE_SIDECAR)
    capture = _capture(threshold_v=1.4)

    assertions = receiver_rule_caveat(capture, sidecar, decoded_ok=True)

    assert len(assertions) == 1
    caveat = assertions[0]
    assert caveat.kind == "receiver_rule.caveat"
    assert "1.4" in caveat.text  # instrument threshold
    assert "3.5" in caveat.text  # receiver V_IH
    assert "flicker" in caveat.text
    # The caveat explicitly negates health ("does not mean the bus is
    # healthy") - this is the opposite of a health claim. The full
    # "assertion set contains no bus-healthy claim" check belongs to the
    # narrate() orchestrator test (test_narrate.py), which is the one that
    # composes the complete assertion set the task description refers to.


def test_matching_thresholds_and_clean_verdict_emit_no_caveat():
    """When instrument threshold ~= receiver V_IH (within
    RECEIVER_THRESHOLD_MARGIN_V) and the verdict is clean, no caveat."""
    sidecar_data = dict(KILLER_CASE_SIDECAR)
    sidecar_data["receiver"] = {"part": "WS2812B", "vdd_v": 5.0, "vih_v": 1.5}
    sidecar_data["receiver_verdict"] = {
        "observed": "clean",
        "notes": "",
        "contemporaneous": True,
    }
    sidecar = Sidecar.from_json(sidecar_data)
    capture = _capture(threshold_v=1.4)  # within 0.5V of 1.5V receiver V_IH

    assertions = receiver_rule_caveat(capture, sidecar, decoded_ok=True)

    assert assertions == []


def test_bare_capture_emits_no_health_claim_and_no_fabricated_verdict():
    """With no receiver metadata, Narrate emits no receiver health claim and
    no fabricated verdict - it may state the instrument-threshold
    limitation."""
    capture = _capture(threshold_v=1.4)

    assertions = receiver_rule_caveat(capture, None, decoded_ok=True)

    for assertion in assertions:
        assert "healthy" not in assertion.text.lower()
        assert "clean" not in assertion.text.lower()
        assert "flicker" not in assertion.text.lower()
        # No fabricated verdict language - only a stated limitation.
        assert "1.4" in assertion.text


if __name__ == "__main__":
    pytest.main([__file__])
