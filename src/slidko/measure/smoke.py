from dataclasses import dataclass


@dataclass(frozen=True)
class SmokeFinding:
    check: str  # "edge_chatter" | "runt_pulse" |
    # "timing_violation" | "protocol_incoherence"
    channel: str  # source channel/role
    start_sample: int  # evidence window, inclusive
    end_sample: int
    severity: str  # "info" | "warn" | "smoke"
    summary: str  # human-readable, quantitative, with units
    escalation: str  # "smoke → scope: <what to capture>, expect <X>"
    evidence: dict  # check-specific numbers backing the summary


# Constants for edge chatter detection
CHATTER_FRACTION = 0.25  # EMPIRICAL, n=synthetic-only: intervals below a
# quarter of a bit are not legal signaling
CHATTER_MIN_EDGES = 3  # EMPIRICAL: need a burst, not one fast edge

# Constant for runt pulse detection
RUNT_MAX_SAMPLES = 2  # EMPIRICAL: 1-2 sample pulses illegal at 24 MS/s
# for the v1 protocol universe (<= ~1 MHz symbol rate)

# Constants for WS2812 timing detection
WS2812_T0H_NS, WS2812_T1H_NS = 400, 800  # Datasheet nominal high times (ns)
WS2812_WINDOW_NS = 150  # Datasheet ± tolerance (ns)


def detect_edge_chatter(
    edges: list[int], t_bit: float, channel: str
) -> list[SmokeFinding]:
    """
    Detect edge chatter - bursts of toggles with intervals far below bit period.

    Args:
        edges: List of edge timestamps
        t_bit: Bit period in samples
        channel: Source channel

    Returns:
        List of SmokeFinding objects for detected chatter bursts
    """
    if len(edges) < 2:
        return []

    findings = []

    # Calculate intervals between consecutive edges
    intervals = [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]

    # Find runs of fast edges (intervals < CHATTER_FRACTION * t_bit)
    i = 0
    while i < len(intervals):
        if intervals[i] < CHATTER_FRACTION * t_bit:
            # Start counting consecutive fast edges
            start_idx = i
            count = 1

            # Continue counting while edges remain fast
            while (
                i + count < len(intervals)
                and intervals[i + count] < CHATTER_FRACTION * t_bit
            ):
                count += 1

            # Check if we have enough consecutive fast edges
            if count >= CHATTER_MIN_EDGES:
                # Create finding for this chatter burst
                start_sample = edges[start_idx]
                end_sample = edges[i + count]
                finding = SmokeFinding(
                    check="edge_chatter",
                    channel=channel,
                    start_sample=start_sample,
                    end_sample=end_sample,
                    severity="warn",
                    summary=(
                        f"Detected edge chatter with {count} consecutive fast edges"
                    ),
                    escalation=(
                        "smoke → scope: capture this line with an oscilloscope; "
                        "expect ringing"
                    ),
                    evidence={
                        "instances": count,
                        "avg_interval": sum(intervals[start_idx : start_idx + count])
                        / count,
                    },
                )
                findings.append(finding)

            # Skip to the end of this burst
            i += count
        else:
            i += 1

    return findings


def detect_runt_pulses(edges: list[int], channel: str) -> list[SmokeFinding]:
    """
    Detect runt/glitch pulses - pulses of 1-2 samples which are illegal for any symbol.

    Args:
        edges: List of edge timestamps
        channel: Source channel

    Returns:
        List of SmokeFinding objects for detected runt pulses
    """
    if len(edges) < 2:
        return []

    findings = []

    # Calculate intervals between consecutive edges
    intervals = [edges[i + 1] - edges[i] for i in range(len(edges) - 1)]

    # Check for intervals that are <= RUNT_MAX_SAMPLES (1-2 samples)
    for i, interval in enumerate(intervals):
        if interval <= RUNT_MAX_SAMPLES:
            # Create finding for this runt pulse
            start_sample = edges[i]
            end_sample = edges[i + 1]
            finding = SmokeFinding(
                check="runt_pulse",
                channel=channel,
                start_sample=start_sample,
                end_sample=end_sample,
                severity="warn",
                summary=f"Detected runt pulse of {interval} samples",
                escalation=(
                    "smoke → scope: capture this line with an oscilloscope; "
                    "expect glitch/shorting"
                ),
                evidence={"pulse_samples": interval},
            )
            findings.append(finding)

    return findings


def detect_ws2812_timing(
    edges: list[int], samplerate_hz: float, channel: str
) -> list[SmokeFinding]:
    """
    Detect WS2812 timing violations - bits with high-pulses outside of T0H or T1H specs.

    Args:
        edges: List of edge timestamps (bit transitions with high+low pulses)
        samplerate_hz: Sampling rate in Hz
        channel: Source channel

    Returns:
        List of SmokeFinding objects for detected timing violations
    """
    findings: list[SmokeFinding] = []

    # Sample timing calculation: at 24 MHz, 1 sample = ~41.67 ns
    sample_ns = 1e9 / samplerate_hz

    # Determine T0H and T1H in samples based on sample rate
    t0h_samples = WS2812_T0H_NS / sample_ns
    t1h_samples = WS2812_T1H_NS / sample_ns
    window_samples = WS2812_WINDOW_NS / sample_ns

    # This is a simplified model - the real algorithm needs more careful parsing.
    # Treat edges as [start_bit0_high, start_bit0_low, start_bit1_high, ...]: each
    # bit is a pair of edges, and its high time is edge[i+1] - edge[i].
    if len(edges) < 4:
        return findings  # Not enough edges to represent at least one full bit

    num_bits = len(edges) // 2  # Each bit has 2 edges in sequence
    if num_bits < 1:
        return findings

    for i in range(0, len(edges) - 1, 2):  # Process pairs
        if i + 1 >= len(edges):
            break

        # The high time for this bit is between consecutive edges
        bit_high_time = edges[i + 1] - edges[i]

        # Check if the timing is valid
        t0h_min = t0h_samples - window_samples
        t0h_max = t0h_samples + window_samples
        t1h_min = t1h_samples - window_samples
        t1h_max = t1h_samples + window_samples

        # Valid bit types:
        # 0: T0H = 0.4us = ~9.6 samples (+/-150 ns)
        # 1: T1H = 0.8us = ~19.2 samples (+/-150 ns)
        is_valid_0 = t0h_min <= bit_high_time <= t0h_max
        is_valid_1 = t1h_min <= bit_high_time <= t1h_max

        if not (is_valid_0 or is_valid_1):
            # Flag as timing violation
            finding = SmokeFinding(
                check="timing_violation",
                channel=channel,
                start_sample=edges[i],
                end_sample=edges[i + 1],
                severity="warn",
                summary=f"WS2812 timing violation: high={bit_high_time} samples",
                escalation=(
                    "smoke → scope: capture this line with an oscilloscope; "
                    "expect WS2812 timing error"
                ),
                evidence={"high_samples": bit_high_time, "bit_position": i // 2},
            )
            findings.append(finding)

    return findings
