"""The Narrate orchestrator (design.md § Module composition): decoded
events + smoke findings + cross-channel alignment + receiver metadata ->
one assertion set. Deterministic assembly, no LLM.
"""

from slidko.capture import Capture
from slidko.corpus.sidecar import Sidecar
from slidko.decode.events import DecodedEvent
from slidko.measure.smoke import SmokeFinding
from slidko.narrate.coincidence import detect_coincidences
from slidko.narrate.model import Assertion
from slidko.narrate.receiver_rule import receiver_rule_caveat
from slidko.narrate.transaction_summary import summarize_transactions


def _decoded_cleanly(events: list[DecodedEvent], findings: list[SmokeFinding]) -> bool:
    """Decode "succeeded" iff it produced events and the smoke detector's
    protocol-incoherence check - which specifically detects "decode
    succeeding into garbage" - didn't fire."""
    if not events:
        return False
    return not any(f.check == "protocol_incoherence" for f in findings)


def narrate(
    capture: Capture,
    events: list[DecodedEvent],
    findings: list[SmokeFinding],
    sidecar: Sidecar | None = None,
) -> list[Assertion]:
    """Compose transaction summaries, cross-channel coincidences, and the
    receiver-rule caveat into one assertion set. Every emitted assertion
    carries non-empty evidence."""
    assertions: list[Assertion] = []
    assertions.extend(summarize_transactions(events))
    assertions.extend(detect_coincidences(events, findings, capture.samplerate_hz))

    decoded_ok = _decoded_cleanly(events, findings)
    assertions.extend(receiver_rule_caveat(capture, sidecar, decoded_ok))

    return assertions
