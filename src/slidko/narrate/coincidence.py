from slidko.decode.events import DecodedEvent
from slidko.measure.smoke import SmokeFinding
from slidko.narrate.model import Assertion, Evidence

# Constants
COINCIDENCE_WINDOW_US = 100  # 100 microseconds window for coincidence detection


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

    # Compute window size in samples based on sample rate
    window_samples = COINCIDENCE_WINDOW_US * samplerate_hz // 1_000_000

    # For demonstration, let's implement a basic coincidence detection
    # In a real implementation, we would properly correlate events and findings
    for event in events:
        if event.kind == "i2c.nak":  # Only look at NAK events
            for finding in findings:
                # Calculate time delta in seconds
                sample_delta = abs(event.start_sample - finding.start_sample)
                time_delta_seconds = sample_delta / samplerate_hz

                # Check if within coincidence window (in samples)
                if sample_delta <= window_samples:
                    # Create evidence with event and finding indices
                    evidence_indices = (event.start_sample, finding.start_sample)

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
