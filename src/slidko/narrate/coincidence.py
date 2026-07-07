from dataclasses import dataclass

from slidko.narrate.model import Assertion, Evidence

# Constants
COINCIDENCE_WINDOW_SAMPLES = 5000  # 5ms at 1MHz sample rate (arbitrary for demo)


@dataclass(frozen=True)
class DecodedEvent:
    """Decoded event from Phase 2"""

    kind: str
    address: int
    is_nak: bool = False
    channel: int = 0
    sample: int = 0
    # Other fields would be here in reality


@dataclass(frozen=True)
class SmokeFinding:
    """Smoke finding from Phase 3"""

    channel: int
    sample: int
    # Other fields would be here in reality


def detect_coincidences(
    events: list[DecodedEvent], findings: list[SmokeFinding], samplerate_hz: int
) -> list[Assertion]:
    """
    Detect coincident events and findings across different channels.

    Args:
        events: List of DecodedEvents
        findings: List of SmokeFindings
        samplerate_hz: Sample rate in Hz

    Returns:
        List of Assertion objects with kind="coincidence"
    """
    assertions: list[Assertion] = []

    if not events or not findings:
        return assertions

    # For demonstration, let's implement a basic coincidence detection
    # In a real implementation, we would properly correlate events and findings
    for event in events:
        if event.kind == "i2c.nak":  # Only look at NAK events
            for finding in findings:
                # Calculate time delta in seconds
                sample_delta = abs(event.sample - finding.sample)
                time_delta_seconds = sample_delta / samplerate_hz

                # Check if within coincidence window (in samples)
                if sample_delta <= COINCIDENCE_WINDOW_SAMPLES:
                    # Create evidence with event and finding indices
                    evidence_indices = (event.sample, finding.sample)

                    # Create time delta text
                    if (
                        time_delta_seconds >= 1e-6
                    ):  # If > 1 microsecond, use microseconds
                        time_text = f"{time_delta_seconds * 1e6:.0f}μs"
                    else:  # Use nanoseconds for very small values
                        time_text = f"{time_delta_seconds * 1e9:.0f}ns"

                    text = (
                        f"Coincidence detected between NAK on channel {event.channel} "
                        f"and finding on channel {finding.channel} at {time_text}"
                    )

                    evidence = Evidence(event_indices=evidence_indices)

                    assertion = Assertion(
                        kind="coincidence",
                        text=text,
                        evidence=evidence,
                        confidence=0.8,  # Moderate confidence for correlation
                    )

                    assertions.append(assertion)

    return assertions


# Test example
if __name__ == "__main__":
    events = [
        DecodedEvent(kind="i2c.nak", address=0x68, channel=0, sample=100),
    ]
    findings = [
        SmokeFinding(channel=1, sample=105),
    ]

    results = detect_coincidences(events, findings, 1000000)
    for result in results:
        print(f"Coincidence: {result.text}")
