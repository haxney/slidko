"""Classifier tree - ranks per-channel/per-group protocol candidates from
discriminator scores and emits role assignments with confidences. A thin
decision layer over the hand-derived discriminators (design.md); no ML."""

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

from slidko.measure import analog_video, can, dshot, i2c, pwm, spi, uart, ws2812

SINGLE_CHANNEL_THRESHOLD = 0.5
# EMPIRICAL, n=synthetic-only: a genuine I2C pair's role-assignment spread
# (periodicity_strength(SCL) - periodicity_strength(SDA)) has landed as low
# as ~0.48 in testing even with real start/stop structure present, so 0.5
# would reject correct answers; false pairings gated by the structural
# checks in i2c.py/spi.py have stayed under 0.2.
MULTI_CHANNEL_THRESHOLD = 0.4


@dataclass(frozen=True)
class Claim:
    protocol: str
    channels: dict[str, str]  # role -> channel_name
    confidence: float
    parameters: dict = field(default_factory=dict)


def _classify_single_channel(
    name: str, channel: np.ndarray, samplerate_hz: int
) -> Claim | None:
    """Best single-channel protocol candidate for one channel, or None."""
    candidates: list[Claim] = []

    baud_estimate = uart.infer_uart(channel, samplerate_hz)
    if baud_estimate.baud > 0 and baud_estimate.confidence >= SINGLE_CHANNEL_THRESHOLD:
        candidates.append(
            Claim(
                protocol="UART",
                channels={"rx": name},
                confidence=baud_estimate.confidence,
                parameters={"baud": baud_estimate.baud, **baud_estimate.frame},
            )
        )

    recognized, confidence = ws2812.recognize(channel, samplerate_hz)
    if recognized:
        candidates.append(
            Claim(protocol="WS2812", channels={"din": name}, confidence=confidence)
        )

    recognized, confidence = pwm.recognize(channel, samplerate_hz)
    if recognized:
        candidates.append(
            Claim(protocol="PWM", channels={"pwm": name}, confidence=confidence)
        )

    rate, confidence = dshot.recognize_rate(channel, samplerate_hz)
    if rate is not None and confidence >= SINGLE_CHANNEL_THRESHOLD:
        candidates.append(
            Claim(
                protocol="DShot",
                channels={"dshot": name},
                confidence=confidence,
                parameters={"rate": rate},
            )
        )

    recognized, confidence, bitrate = can.recognize(channel, samplerate_hz)
    if recognized:
        candidates.append(
            Claim(
                protocol="CAN",
                channels={"can": name},
                confidence=confidence,
                parameters={"bitrate": bitrate},
            )
        )

    recognized, confidence = analog_video.recognize(channel, samplerate_hz)
    if recognized:
        candidates.append(
            Claim(
                protocol="AnalogVideo", channels={"video": name}, confidence=confidence
            )
        )

    if not candidates:
        return None
    return max(candidates, key=lambda c: c.confidence)


def _classify_pair(
    name_a: str, sig_a: np.ndarray, name_b: str, sig_b: np.ndarray
) -> Claim | None:
    claim = i2c.classify_i2c({name_a: sig_a, name_b: sig_b})
    if claim.confidence < MULTI_CHANNEL_THRESHOLD:
        return None
    return Claim(
        protocol="I2C",
        channels={"scl": claim.scl_channel, "sda": claim.sda_channel},
        confidence=claim.confidence,
        parameters={"start_count": claim.start_count, "stop_count": claim.stop_count},
    )


def _classify_triple(names_signals: dict[str, np.ndarray]) -> Claim | None:
    claim = spi.classify_spi(names_signals)
    if claim.confidence < MULTI_CHANNEL_THRESHOLD:
        return None
    return Claim(
        protocol="SPI",
        channels={
            "clk": claim.clock_channel,
            "cs": claim.cs_channel,
            "data": claim.data_channel,
        },
        confidence=claim.confidence,
        parameters={
            "cpol": claim.cpol,
            "cpha": claim.cpha,
            "cpha_confidence": claim.cpha_confidence,
        },
    )


def classify(channels: dict[str, np.ndarray], samplerate_hz: int) -> list[Claim]:
    """Rank protocol candidates across a whole multi-channel capture.

    Greedy: the best-scoring multi-channel claim consumes its channels
    first (3-channel SPI groups before 2-channel I2C pairs, largest group
    first so a real SPI triple isn't cannibalized by a coincidental I2C-pair
    match inside it); remaining channels are classified individually. No
    channel appears in more than one claim.
    """
    remaining = dict(channels)
    claims: list[Claim] = []

    while len(remaining) >= 3:
        best: Claim | None = None
        best_names: tuple[str, ...] = ()
        for names in combinations(remaining, 3):
            subset = {n: remaining[n] for n in names}
            claim = _classify_triple(subset)
            if claim is not None and (
                best is None or claim.confidence > best.confidence
            ):
                best, best_names = claim, names
        if best is None:
            break
        claims.append(best)
        for n in best_names:
            del remaining[n]

    while len(remaining) >= 2:
        best = None
        best_names = ()
        for name_a, name_b in combinations(remaining, 2):
            claim = _classify_pair(name_a, remaining[name_a], name_b, remaining[name_b])
            if claim is not None and (
                best is None or claim.confidence > best.confidence
            ):
                best, best_names = claim, (name_a, name_b)
        if best is None:
            break
        claims.append(best)
        for n in best_names:
            del remaining[n]

    for name, channel in remaining.items():
        claim = _classify_single_channel(name, channel, samplerate_hz)
        if claim is not None:
            claims.append(claim)

    return claims
