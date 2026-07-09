"""PWM/servo signature recognition - period + pulse-width envelope match
against the conventional RC servo/ESC range, not full parameter estimation."""

import numpy as np

from slidko.measure.edges import (
    extract_edges,
    high_pulse_durations_ns,
    same_polarity_intervals,
)

# EMPIRICAL, n=synthetic-only: conventional RC servo/ESC PWM envelope - 50 Hz
# nominal frame rate (up to ~490 Hz for fast ESC PWM), 1000-2000 us nominal
# pulse width with margin for trims/extended range.
PWM_FREQ_HZ_RANGE = (40.0, 500.0)
PWM_PULSE_US_RANGE = (700.0, 2300.0)
RECOGNITION_THRESHOLD = 0.9


def recognize(channel: np.ndarray, samplerate_hz: int) -> tuple[bool, float]:
    """(recognized, confidence): checks the pulse-repeat frequency falls in
    the servo/ESC band and pulse widths land in the nominal envelope."""
    edges = extract_edges(channel)
    if len(edges) < 2:
        return False, 0.0

    periods = same_polarity_intervals(edges)
    durations_ns = high_pulse_durations_ns(channel, samplerate_hz)
    if len(periods) == 0 or not durations_ns:
        return False, 0.0

    freq_hz = samplerate_hz / float(np.median(periods))
    if not (PWM_FREQ_HZ_RANGE[0] <= freq_hz <= PWM_FREQ_HZ_RANGE[1]):
        return False, 0.0

    pulses_us = [d / 1000.0 for d in durations_ns]
    in_range = [PWM_PULSE_US_RANGE[0] <= p <= PWM_PULSE_US_RANGE[1] for p in pulses_us]
    confidence = sum(in_range) / len(in_range)
    return confidence >= RECOGNITION_THRESHOLD, confidence
