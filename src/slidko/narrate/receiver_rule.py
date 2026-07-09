"""The receiver rule (design.md § Receiver-rule caveat, docs/DESIGN.md) -
the load-bearing correctness case: a capture that decodes cleanly at the
instrument's own logic threshold is not evidence the real receiver saw a
clean signal too, when that receiver's V_IH differs materially from the
instrument's threshold. Decode-clean does not mean bus-healthy.
"""

from slidko.capture import Capture
from slidko.corpus.sidecar import Sidecar
from slidko.narrate.model import Assertion, Evidence

RECEIVER_THRESHOLD_MARGIN_V = 0.5  # EMPIRICAL: instrument-vs-receiver V_IH
# difference considered "material" (docs/DESIGN.md's WS2812 killer case:
# 1.4 V instrument vs ~3.5 V receiver V_IH)

# Recognized affirmative receiver_verdict.observed strings (docs/CORPUS.md:
# "Looks noisy/clean" is the field-notes framing this schema formalizes).
# Anything else ("flicker", "glitch", "nak", ...) is treated as an anomaly
# report, not enumerated exhaustively - free text is the sidecar's contract.
CLEAN_VERDICT_VALUES = frozenset({"clean"})


def _whole_capture_evidence(capture: Capture) -> Evidence:
    """The caveat is a statement about the whole capture, not a specific
    decoded event - its evidence window is the full sample range, still a
    valid, traceable window into the source capture."""
    if not capture.channels:
        return Evidence()
    n = len(next(iter(capture.channels.values())))
    if n == 0:
        return Evidence()
    return Evidence(sample_ranges=((0, n - 1),))


def receiver_rule_caveat(
    capture: Capture, sidecar: Sidecar | None, decoded_ok: bool
) -> list[Assertion]:
    """Emit a `receiver_rule.caveat` assertion when the instrument threshold
    differs materially from the receiver's V_IH AND the receiver verdict
    contradicts a clean decode. Never fabricates a verdict when receiver
    metadata is absent - it may note the instrument-threshold limitation,
    but makes no receiver health claim either way.
    """
    instrument_threshold_v = capture.provenance.get("threshold_v")
    evidence = _whole_capture_evidence(capture)

    if sidecar is None or sidecar.receiver is None or sidecar.receiver_verdict is None:
        if instrument_threshold_v is None:
            return []
        text = (
            f"Decode used the instrument's {instrument_threshold_v:.1f} V logic "
            "threshold; no receiver-side verdict is available, so this does not "
            "confirm what a receiver with a different V_IH actually saw."
        )
        return [
            Assertion(
                kind="receiver_rule.caveat",
                text=text,
                evidence=evidence,
                confidence=1.0,
            )
        ]

    if instrument_threshold_v is None or not decoded_ok:
        return []

    receiver_vih_v = sidecar.receiver.vih_v
    margin_v = abs(instrument_threshold_v - receiver_vih_v)
    verdict_clean = (
        sidecar.receiver_verdict.observed.strip().lower() in CLEAN_VERDICT_VALUES
    )

    if margin_v < RECEIVER_THRESHOLD_MARGIN_V or verdict_clean:
        return []

    text = (
        f"Decode succeeded cleanly at the instrument's {instrument_threshold_v:.1f} V "
        f'threshold, but the receiver verdict was "{sidecar.receiver_verdict.observed}"'
        f" ({sidecar.receiver.part}, V_IH ≈ {receiver_vih_v:.1f} V) - a clean decode "
        "here does not mean the bus is healthy; the instrument's threshold does not "
        "represent what this receiver saw."
    )
    return [
        Assertion(
            kind="receiver_rule.caveat", text=text, evidence=evidence, confidence=1.0
        )
    ]
