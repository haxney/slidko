"""Analog-video recognition stub - recognize composite-video-like sync
pulse trains (NTSC/PAL horizontal line rate), never decode. Per
docs/ARCHITECTURE.md's v1 guardrail against a vision/photo pipeline: this is
recognition only, so Diagnose can say "that's analog video, escalate to
scope" instead of misreading it as a digital protocol."""

import numpy as np

from slidko.measure.intervals import estimate_dominant_period

NTSC_LINE_HZ = 15_734.26
PAL_LINE_HZ = 15_625.0

# EMPIRICAL, n=synthetic-only.
LINE_RATE_TOLERANCE = 0.02
RECOGNITION_THRESHOLD = 0.5


def recognize(channel: np.ndarray, samplerate_hz: int) -> tuple[bool, float]:
    """(recognized, confidence): does the channel's dominant periodicity
    match an NTSC/PAL horizontal sync line rate? No frame/field decode."""
    period_samples, strength = estimate_dominant_period(channel)
    if period_samples <= 0 or strength <= 0:
        return False, 0.0

    freq_hz = samplerate_hz / period_samples
    nearest = min([NTSC_LINE_HZ, PAL_LINE_HZ], key=lambda f: abs(f - freq_hz) / f)
    rel_error = abs(nearest - freq_hz) / nearest
    if rel_error > LINE_RATE_TOLERANCE:
        return False, 0.0

    confidence = max(0.0, min(1.0, strength * (1.0 - rel_error / LINE_RATE_TOLERANCE)))
    return confidence >= RECOGNITION_THRESHOLD, confidence
