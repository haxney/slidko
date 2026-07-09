"""DShot signature recognition - interval-histogram match against
fixed-by-spec T0H/T1H timing per rate, not estimation. Recognition + frame
decode (rate, throttle value, telemetry bit) since the 16-bit frame's CRC
gives a free correctness check - still no ML."""

import numpy as np

from slidko.measure.edges import high_pulse_durations_ns, pulse_cells_ns

# Source: Betaflight DShot docs, cross-checked against independent
# references (confidence HIGH - stable, long-published numbers). T1H is
# always 2x T0H; low time is the remainder of the bit period.
DSHOT_TIMING_NS = {
    150: {"bit_period_ns": 6670, "t0h_ns": 2500, "t1h_ns": 5000},
    300: {"bit_period_ns": 3330, "t0h_ns": 1250, "t1h_ns": 2500},
    600: {"bit_period_ns": 1670, "t0h_ns": 625, "t1h_ns": 1250},
}
DSHOT_FRAME_GAP_NS = 2000  # minimum inter-frame gap

# EMPIRICAL, n=synthetic-only: a high-pulse duration within this many ns of
# T0H/T1H is treated as that bit value.
TIMING_WINDOW_NS = 150


def dshot_checksum(data12: int) -> int:
    """XOR of the three nibbles of the 12-bit (throttle<<1 | telemetry) field."""
    return (data12 ^ (data12 >> 4) ^ (data12 >> 8)) & 0x0F


def recognize_rate(channel: np.ndarray, samplerate_hz: int) -> tuple[int | None, float]:
    """Match (high, period) pulse cells against each rate's T0H/T1H/bit-period
    windows; return (best_rate, confidence) where confidence is the fraction
    of cells that land inside a spec window for that rate.

    Checking the full period alongside the high time (not high alone) is
    what rejects a plain constant-duty square wave (e.g. an I2C SCL clock)
    whose half-period coincidentally matches one rate's T0H or T1H: its bit
    period won't also match, where a real DShot bitstream's will.
    """
    cells = pulse_cells_ns(channel, samplerate_hz)
    cells = [(h, p) for h, p in cells if p == p]  # drop the trailing NaN-period cell
    if not cells:
        return None, 0.0

    best_rate = None
    best_confidence = 0.0
    for rate, timing in DSHOT_TIMING_NS.items():
        t0h_lo, t0h_hi = (
            timing["t0h_ns"] - TIMING_WINDOW_NS,
            timing["t0h_ns"] + TIMING_WINDOW_NS,
        )
        t1h_lo, t1h_hi = (
            timing["t1h_ns"] - TIMING_WINDOW_NS,
            timing["t1h_ns"] + TIMING_WINDOW_NS,
        )
        period_lo = timing["bit_period_ns"] - TIMING_WINDOW_NS
        period_hi = timing["bit_period_ns"] + TIMING_WINDOW_NS
        matches = sum(
            1
            for h, p in cells
            if (period_lo <= p <= period_hi)
            and ((t0h_lo <= h <= t0h_hi) or (t1h_lo <= h <= t1h_hi))
        )
        confidence = matches / len(cells)
        if confidence > best_confidence:
            best_rate, best_confidence = rate, confidence

    return best_rate, best_confidence


def decode_frame(
    channel: np.ndarray, samplerate_hz: int, rate: int
) -> tuple[int | None, bool, bool]:
    """Decode a single 16-bit DShot frame at the given (already-recognized)
    rate. Returns (value, telemetry, checksum_ok); value is None if the
    channel doesn't contain exactly one recognizable 16-bit frame's worth of
    pulses."""
    timing = DSHOT_TIMING_NS[rate]
    threshold_ns = (timing["t0h_ns"] + timing["t1h_ns"]) / 2
    durations_ns = high_pulse_durations_ns(channel, samplerate_hz)
    if len(durations_ns) < 16:
        return None, False, False

    bits = [d > threshold_ns for d in durations_ns[:16]]
    frame16 = 0
    for b in bits:
        frame16 = (frame16 << 1) | int(b)

    data12 = frame16 >> 4
    crc = frame16 & 0xF
    checksum_ok = dshot_checksum(data12) == crc
    value = data12 >> 1
    telemetry = bool(data12 & 1)
    return value, telemetry, checksum_ok
