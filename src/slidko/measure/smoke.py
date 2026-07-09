"""Smoke detector - deterministic edge-math anomaly checks (design.md).

Pure edge math over Phase 0 edges (and, for protocol incoherence, Phase 2
decoded events) to DETECT digital-abstraction contract breaches, never
diagnose. The false-positive rate on clean captures is the headline metric:
every threshold below is a named constant, doc-commented as EMPIRICAL
(n=synthetic-only per docs/CORPUS.md's overfitting guard), and biased toward
silence - a check that is unsure does not fire.
"""

from dataclasses import dataclass

import numpy as np

from slidko.capture import Capture
from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.events import DecodedEvent
from slidko.measure.edges import extract_edges
from slidko.measure.intervals import estimate_dominant_period

CHATTER_FRACTION = 0.25  # EMPIRICAL, n=synthetic-only: intervals below a
# quarter of a bit are not legal signaling
CHATTER_MIN_EDGES = 3  # EMPIRICAL: need a burst, not one fast edge

RUNT_MAX_SAMPLES = 2  # EMPIRICAL: 1-2 sample pulses illegal at 24 MS/s
# for the v1 protocol universe (<= ~1 MHz symbol rate)

WS2812_T0H_NS, WS2812_T1H_NS = 400, 800  # datasheet nominal high times (ns)
WS2812_WINDOW_NS = 150  # datasheet +/- tolerance (ns), confidence HIGH

INCOHERENCE_FRAME_ERR_RATE = 0.0  # EMPIRICAL: any framing error is
# incoherence for the clean-synth gate (default 0.0 - fires above this)


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


def detect_edge_chatter(
    edges: list[tuple[int, bool]], t_bit: float, channel: str
) -> list[SmokeFinding]:
    """Bursts of >= CHATTER_MIN_EDGES consecutive inter-edge intervals each
    < CHATTER_FRACTION * t_bit (ringing/slow edges crossing threshold
    multiple times)."""
    if len(edges) < 2 or t_bit <= 0:
        return []

    indices = [idx for idx, _ in edges]
    intervals = [indices[i + 1] - indices[i] for i in range(len(indices) - 1)]
    threshold = CHATTER_FRACTION * t_bit

    findings: list[SmokeFinding] = []
    i = 0
    while i < len(intervals):
        if intervals[i] < threshold:
            start_idx = i
            count = 1
            while i + count < len(intervals) and intervals[i + count] < threshold:
                count += 1

            if count >= CHATTER_MIN_EDGES:
                start_sample = indices[start_idx]
                end_sample = indices[start_idx + count]
                burst_intervals = intervals[start_idx : start_idx + count]
                findings.append(
                    SmokeFinding(
                        check="edge_chatter",
                        channel=channel,
                        start_sample=start_sample,
                        end_sample=end_sample,
                        severity="warn",
                        summary=(
                            f"Edge chatter: {count} consecutive intervals "
                            f"averaging {sum(burst_intervals) / count:.1f} "
                            f"samples (< {threshold:.1f}-sample threshold)"
                        ),
                        escalation=(
                            "smoke → scope: capture this line with an "
                            "oscilloscope; expect ringing"
                        ),
                        evidence={
                            "instances": count,
                            "avg_interval": sum(burst_intervals) / count,
                            "threshold_samples": threshold,
                        },
                    )
                )
            i += count
        else:
            i += 1

    return findings


def detect_runt_pulses(
    edges: list[tuple[int, bool]], channel: str
) -> list[SmokeFinding]:
    """Any inter-edge interval <= RUNT_MAX_SAMPLES samples: a pulse too
    narrow to be a legal symbol at any v1 protocol's rate, independent of
    protocol."""
    if len(edges) < 2:
        return []

    indices = [idx for idx, _ in edges]
    findings: list[SmokeFinding] = []
    for i in range(len(indices) - 1):
        interval = indices[i + 1] - indices[i]
        if interval <= RUNT_MAX_SAMPLES:
            findings.append(
                SmokeFinding(
                    check="runt_pulse",
                    channel=channel,
                    start_sample=indices[i],
                    end_sample=indices[i + 1],
                    severity="warn",
                    summary=f"Runt pulse: {interval} samples wide",
                    escalation=(
                        "smoke → scope: capture this line with an "
                        "oscilloscope; expect a glitch or short"
                    ),
                    evidence={"pulse_samples": interval},
                )
            )
    return findings


def detect_ws2812_timing(
    edges: list[tuple[int, bool]], samplerate_hz: float, channel: str
) -> list[SmokeFinding]:
    """WS2812 bit-timing violation: each bit is a (rising, falling) edge
    pair: high time outside both the T0H and T1H +/- window is a violation.
    Windows are derived from the capture's actual samplerate, never
    hardcoded sample counts (CLAUDE.md clock-parameterize discipline)."""
    if len(edges) < 2:
        return []

    sample_ns = 1e9 / samplerate_hz
    t0h_samples = WS2812_T0H_NS / sample_ns
    t1h_samples = WS2812_T1H_NS / sample_ns
    window_samples = WS2812_WINDOW_NS / sample_ns
    t0h_min, t0h_max = t0h_samples - window_samples, t0h_samples + window_samples
    t1h_min, t1h_max = t1h_samples - window_samples, t1h_samples + window_samples

    indices = [idx for idx, _ in edges]
    findings: list[SmokeFinding] = []
    num_bits = len(indices) // 2
    for bit_index in range(num_bits):
        rise_idx = indices[bit_index * 2]
        fall_idx = indices[bit_index * 2 + 1]
        high_samples = fall_idx - rise_idx

        is_valid_0 = t0h_min <= high_samples <= t0h_max
        is_valid_1 = t1h_min <= high_samples <= t1h_max
        if is_valid_0 or is_valid_1:
            continue

        findings.append(
            SmokeFinding(
                check="timing_violation",
                channel=channel,
                start_sample=rise_idx,
                end_sample=fall_idx,
                severity="smoke",
                summary=(
                    f"WS2812 bit {bit_index}: high time "
                    f"{high_samples * sample_ns:.0f} ns outside T0H/T1H "
                    f"+/-{WS2812_WINDOW_NS} ns windows"
                ),
                escalation=(
                    "smoke → scope: capture this line with an oscilloscope; "
                    "expect a marginal WS2812 timing/level issue"
                ),
                evidence={
                    "bit_index": bit_index,
                    "high_samples": high_samples,
                    "high_ns": high_samples * sample_ns,
                },
            )
        )
    return findings


def detect_incoherence(
    events: list[DecodedEvent], hypothesis: ProtocolHypothesis
) -> list[SmokeFinding]:
    """Decode "succeeding" into garbage: UART framing-error rate above
    INCOHERENCE_FRAME_ERR_RATE, or an I2C ack/nak/data event with no
    preceding addressed device on the bus."""
    protocol = hypothesis.protocol.lower()
    if protocol == "uart":
        return _detect_uart_framing_incoherence(events, hypothesis)
    if protocol == "i2c":
        return _detect_i2c_orphan_incoherence(events, hypothesis)
    return []


def _detect_uart_framing_incoherence(
    events: list[DecodedEvent], hypothesis: ProtocolHypothesis
) -> list[SmokeFinding]:
    uart_events = [e for e in events if e.kind == "uart.byte"]
    if not uart_events:
        return []

    bad = [e for e in uart_events if e.data.get("framing_error")]
    rate = len(bad) / len(uart_events)
    if rate <= INCOHERENCE_FRAME_ERR_RATE:
        return []

    channel = hypothesis.channel_assignments.get("rx", "")
    return [
        SmokeFinding(
            check="protocol_incoherence",
            channel=channel,
            start_sample=min(e.start_sample for e in bad),
            end_sample=max(e.end_sample for e in bad),
            severity="smoke",
            summary=(
                f"UART framing-error rate {rate:.1%} "
                f"({len(bad)}/{len(uart_events)} frames)"
            ),
            escalation=(
                "smoke → scope: capture RX with an oscilloscope; expect a "
                "marginal baud/noise/level issue"
            ),
            evidence={
                "framing_error_count": len(bad),
                "total_frames": len(uart_events),
                "rate": rate,
            },
        )
    ]


def _detect_i2c_orphan_incoherence(
    events: list[DecodedEvent], hypothesis: ProtocolHypothesis
) -> list[SmokeFinding]:
    channel = hypothesis.channel_assignments.get("sda", "")
    findings: list[SmokeFinding] = []
    addressed = False
    for event in events:
        if event.kind == "i2c.start":
            addressed = False
        elif event.kind == "i2c.address":
            addressed = True
        elif event.kind == "i2c.stop":
            addressed = False
        elif event.kind in ("i2c.ack", "i2c.nak", "i2c.data") and not addressed:
            findings.append(
                SmokeFinding(
                    check="protocol_incoherence",
                    channel=channel,
                    start_sample=event.start_sample,
                    end_sample=event.end_sample,
                    severity="smoke",
                    summary=(f"I2C {event.kind} with no preceding addressed device"),
                    escalation=(
                        "smoke → scope: capture SCL/SDA with an "
                        "oscilloscope; expect bus contention or a phantom "
                        "device"
                    ),
                    evidence={"kind": event.kind, "sample": event.start_sample},
                )
            )
    return findings


# Which hypothesis channel role has a well-defined, honestly-periodic rate
# to check for chatter against, per protocol. Data lines (I2C SDA, SPI
# MOSI/MISO) don't have a principled minimum legitimate inter-edge interval
# independent of the actual bytes on the wire - a data line's transition
# rate depends on the data, not just the clock - so they get the
# protocol-agnostic runt check only, never chatter. Only genuinely
# clock-like lines (or a single-channel protocol's own line) get chatter.
_CHATTER_CLOCK_ROLE = {"uart": "rx", "i2c": "scl", "spi": "clk"}


def _chatter_eligible_channels(hypothesis: ProtocolHypothesis) -> set[str]:
    protocol = hypothesis.protocol.lower()
    clock_role = _CHATTER_CLOCK_ROLE.get(protocol)
    if clock_role is not None:
        channel = hypothesis.channel_assignments.get(clock_role)
        return {channel} if channel else set()
    # Single-channel protocols (WS2812, PWM, DShot, ...): every assigned
    # channel IS the signal.
    return set(hypothesis.channel_assignments.values())


def _channel_t_bit(
    channel_name: str,
    channel_signal: np.ndarray,
    samplerate_hz: int,
    hypothesis: ProtocolHypothesis,
) -> float:
    """Established bit/symbol period in samples, for a chatter-eligible
    channel. Prefers a directly-known rate from the hypothesis (UART baud);
    falls back to the autocorrelation period estimate already used
    elsewhere in Measure (SPI/I2C role assignment - intervals.py). Returns
    0.0 (chatter check stays silent) when neither yields a rate - unsure
    means don't fire."""
    if (
        hypothesis.protocol.lower() == "uart"
        and hypothesis.channel_assignments.get("rx") == channel_name
    ):
        baud = hypothesis.parameters.get("baud")
        if baud:
            return float(samplerate_hz) / float(baud)
    period, _confidence = estimate_dominant_period(channel_signal)
    return period


def run_smoke(
    capture: Capture,
    hypothesis: ProtocolHypothesis,
    events: list[DecodedEvent] | None = None,
) -> list[SmokeFinding]:
    """Orchestrate all four checks: edge chatter (clock-like channels only)
    + runt pulses (every channel, protocol-agnostic), WS2812 timing (only
    when the hypothesis is WS2812), protocol incoherence (only when decoded
    events are supplied)."""
    findings: list[SmokeFinding] = []
    chatter_channels = _chatter_eligible_channels(hypothesis)

    for channel_name, channel_signal in capture.channels.items():
        edges = extract_edges(channel_signal)
        findings.extend(detect_runt_pulses(edges, channel_name))
        if channel_name in chatter_channels:
            t_bit = _channel_t_bit(
                channel_name, channel_signal, capture.samplerate_hz, hypothesis
            )
            findings.extend(detect_edge_chatter(edges, t_bit, channel_name))

    if hypothesis.protocol.lower() == "ws2812":
        for channel_name in hypothesis.channel_assignments.values():
            channel_signal = capture.channels[channel_name]
            edges = extract_edges(channel_signal)
            findings.extend(
                detect_ws2812_timing(edges, capture.samplerate_hz, channel_name)
            )

    if events is not None:
        findings.extend(detect_incoherence(events, hypothesis))

    return findings
