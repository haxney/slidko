"""WS2812 signature recognition - interval-histogram match against
fixed-by-spec T0H/T1H timing, not estimation."""

import numpy as np

from slidko.measure.edges import high_pulse_durations_ns
from slidko.measure.smoke import WS2812_T0H_NS, WS2812_T1H_NS, WS2812_WINDOW_NS

# EMPIRICAL, n=synthetic-only: recognized once this fraction of high pulses
# lands inside a spec window.
RECOGNITION_THRESHOLD = 0.9


def recognize(channel: np.ndarray, samplerate_hz: int) -> tuple[bool, float]:
    """(recognized, confidence): confidence is the fraction of high pulses
    that land inside the T0H or T1H +/- window - a signature match, not a
    decode."""
    durations_ns = high_pulse_durations_ns(channel, samplerate_hz)
    if not durations_ns:
        return False, 0.0

    t0h_lo, t0h_hi = WS2812_T0H_NS - WS2812_WINDOW_NS, WS2812_T0H_NS + WS2812_WINDOW_NS
    t1h_lo, t1h_hi = WS2812_T1H_NS - WS2812_WINDOW_NS, WS2812_T1H_NS + WS2812_WINDOW_NS
    matches = sum(
        1 for d in durations_ns if (t0h_lo <= d <= t0h_hi) or (t1h_lo <= d <= t1h_hi)
    )
    confidence = matches / len(durations_ns)
    return confidence >= RECOGNITION_THRESHOLD, confidence
