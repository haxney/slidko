"""
Deliberate, hand-verified scenario builders for the golden-file harness
(design.md § Golden-file harness, task 7.2). Shared between the golden
generator and test_golden.py so both run the exact same scenario.

Each builder returns (capture, events, findings, sidecar) ready to pass to
narrate().
"""

import numpy as np

from slidko.capture import Capture
from slidko.corpus.sidecar import Sidecar
from slidko.decode.events import DecodedEvent
from slidko.decode.from_measure import hypothesis_from_claim
from slidko.decode.sigrok_backend import SigrokBackend
from slidko.measure.classify import classify
from slidko.measure.smoke import SmokeFinding
from tests.synth import I2CBuilder, SimpleI2CGenerator

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


def healthy_i2c_imu_bus():
    """(a) Healthy I2C IMU bus: a real synthetic capture, classified and
    decoded through the real Measure -> Decode pipeline (sigrok-cli), zero
    manual configuration - a plain transaction.summary, nothing else."""
    generator = SimpleI2CGenerator(address=0x68, payload=[0x3B, 0x00, 0x01])
    capture, _ground_truth = generator.generate()

    claims = classify(capture.channels, capture.samplerate_hz)
    i2c_claim = next(c for c in claims if c.protocol == "I2C")
    hypothesis = hypothesis_from_claim(i2c_claim)
    events = SigrokBackend().decode(capture, hypothesis)

    return capture, events, [], None


def i2c_nak_with_coincident_finding():
    """(b) I2C bus with a NAK on the payload byte, real-decoded, coincident
    with a smoke finding on another channel within the coincidence
    window - one transaction.summary, one coincidence assertion."""
    q = 60
    builder = I2CBuilder(q)
    builder.idle(q * 4)
    builder.start()
    addr_rw = (0x68 << 1) | 0
    builder.byte(addr_rw, ack=True)
    builder.byte(0xAA, ack=False)  # NAK
    builder.stop()
    builder.idle(q * 4)
    capture = builder.build(24_000_000, "I2C")

    claims = classify(capture.channels, capture.samplerate_hz)
    i2c_claim = next(c for c in claims if c.protocol == "I2C")
    hypothesis = hypothesis_from_claim(i2c_claim)
    events = SigrokBackend().decode(capture, hypothesis)

    nak_event = next(e for e in events if e.kind == "i2c.nak")
    finding = SmokeFinding(
        check="timing_violation",
        channel="scl",
        start_sample=nak_event.start_sample + 30,
        end_sample=nak_event.start_sample + 80,
        severity="warn",
        summary="Timing violation coincident with the NAK",
        escalation=(
            "smoke → scope: capture SCL with an oscilloscope; expect a rail dip"
        ),
        evidence={},
    )

    return capture, events, [finding], None


def ws2812_receiver_rule_killer_case():
    """(c) The WS2812 receiver-rule killer case (docs/DESIGN.md): decode
    looks clean at the instrument's 1.4V threshold, but the receiver
    verdict is "flicker" (5V WS2812 driven at V_IH=3.5V) - a
    receiver_rule.caveat, and NO health claim anywhere in the set.

    Decode does not cover WS2812 (phase-2's explicit non-goal), so
    "decode succeeded" is represented by a placeholder decoded event - the
    receiver rule only needs decoded_ok=True, not real WS2812 framing.
    """
    capture = Capture(
        channels={"din": np.zeros(10, dtype=bool)},
        samplerate_hz=24_000_000,
        provenance={"threshold_v": 1.4},
    )
    events = [DecodedEvent(kind="ws2812.frame", start_sample=0, end_sample=9, data={})]
    sidecar = Sidecar.from_json(KILLER_CASE_SIDECAR)

    return capture, events, [], sidecar


SCENARIOS = {
    "healthy_i2c_imu": healthy_i2c_imu_bus,
    "i2c_nak_coincidence": i2c_nak_with_coincident_finding,
    "ws2812_receiver_rule_killer_case": ws2812_receiver_rule_killer_case,
}
