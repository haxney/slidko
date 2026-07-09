"""Tests for the classifier tree (measure/classify.py): eval matrix accuracy,
mixed multi-channel role assignment, and confidence serialization."""

from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Callable

from slidko.measure.classify import classify
from tests.synth import (
    SimpleDShotGenerator,
    SimpleI2CGenerator,
    SimplePWMGenerator,
    SimpleSPIGenerator,
    SimpleUARTGenerator,
    SimpleWS2812Generator,
)

SAMPLE_RATE_HZ = 24_000_000


def _uart_case(baud: int) -> "Callable[[], dict[str, np.ndarray]]":
    payload = [0x00, 0xFF, 0x55, 0xAA, 0x3C]
    return lambda: (
        SimpleUARTGenerator(baud=baud, payload=payload).generate()[0].channels
    )


def _spi_case(cpol: int, cpha: int) -> "Callable[[], dict[str, np.ndarray]]":
    payload = [0x41, 0x42, 0x43]
    return lambda: (
        SimpleSPIGenerator(cpol=cpol, cpha=cpha, payload=payload).generate()[0].channels
    )


def _dshot_case(rate: int) -> "Callable[[], dict[str, np.ndarray]]":
    return lambda: SimpleDShotGenerator(rate=rate, value=1200).generate()[0].channels


def _eval_matrix() -> list[tuple["Callable[[], dict[str, np.ndarray]]", str]]:
    """(build_channels_fn, expected_protocol) pairs covering every closed-list
    protocol at clean synthetic settings, zero manually supplied parameters."""
    cases: list[tuple[Callable[[], dict[str, np.ndarray]], str]] = []

    for baud in [1200, 9600, 19200, 57600, 115200, 230400]:
        cases.append((_uart_case(baud), "UART"))
    cases.append((
        lambda: (
            SimpleUARTGenerator.sbus(payload=[0x0F, 0xF0, 0x3C]).generate()[0].channels
        ),
        "UART",
    ))

    cases.append((
        lambda: (
            SimpleI2CGenerator(address=0x42, payload=[0xDE, 0xAD, 0xBE])
            .generate()[0]
            .channels
        ),
        "I2C",
    ))

    for cpol in (0, 1):
        for cpha in (0, 1):
            cases.append((_spi_case(cpol, cpha), "SPI"))

    cases.append((
        lambda: SimpleWS2812Generator(payload=[0x5A, 0xC3]).generate()[0].channels,
        "WS2812",
    ))

    cases.append((
        lambda: (
            SimplePWMGenerator(freq_hz=50, pulse_us=1500, num_pulses=4)
            .generate()[0]
            .channels
        ),
        "PWM",
    ))
    cases.append((
        lambda: (
            SimplePWMGenerator(freq_hz=400, pulse_us=1200, num_pulses=4)
            .generate()[0]
            .channels
        ),
        "PWM",
    ))

    for rate in (150, 300, 600):
        cases.append((_dshot_case(rate), "DShot"))

    return cases


def test_eval_matrix_accuracy_on_clean_synthetics():
    cases = _eval_matrix()
    correct = 0
    failures = []
    for build_channels, expected_protocol in cases:
        channels = build_channels()
        claims = classify(channels, SAMPLE_RATE_HZ)
        protocols = [c.protocol for c in claims]
        if protocols == [expected_protocol]:
            correct += 1
        else:
            failures.append((expected_protocol, protocols))

    accuracy = correct / len(cases)
    total = len(cases)
    print(f"eval matrix accuracy: {accuracy:.4f} ({correct}/{total})")
    print(f"failures: {failures}")
    assert accuracy >= 0.99, f"failures: {failures}"


def _pad(channel: np.ndarray, length: int, pad_level: bool) -> np.ndarray:
    if len(channel) >= length:
        return channel[:length]
    pad = np.full(length - len(channel), pad_level, dtype=bool)
    return np.concatenate([channel, pad])


def test_mixed_four_channel_capture_no_cross_contamination():
    i2c_capture, _ = SimpleI2CGenerator(address=0x50, payload=[0x11, 0x22]).generate()
    uart_capture, _ = SimpleUARTGenerator(
        baud=115200, payload=[0x55, 0xAA, 0x3C]
    ).generate()
    pwm_capture, _ = SimplePWMGenerator(
        freq_hz=50, pulse_us=1500, num_pulses=4
    ).generate()

    length = max(
        len(i2c_capture.channels["scl"]),
        len(uart_capture.channels["ch0"]),
        len(pwm_capture.channels["pwm"]),
    )

    channels = {
        "D0": _pad(i2c_capture.channels["scl"], length, True),
        "D1": _pad(i2c_capture.channels["sda"], length, True),
        "D2": _pad(uart_capture.channels["ch0"], length, True),
        "D3": _pad(pwm_capture.channels["pwm"], length, False),
    }

    claims = classify(channels, SAMPLE_RATE_HZ)
    by_protocol = {c.protocol: c for c in claims}

    assert set(by_protocol) == {"I2C", "UART", "PWM"}

    i2c_claim = by_protocol["I2C"]
    assert {i2c_claim.channels["scl"], i2c_claim.channels["sda"]} == {"D0", "D1"}

    uart_claim = by_protocol["UART"]
    assert uart_claim.channels["rx"] == "D2"

    pwm_claim = by_protocol["PWM"]
    assert pwm_claim.channels["pwm"] == "D3"

    # No channel appears in more than one claim.
    used = [ch for claim in claims for ch in claim.channels.values()]
    assert len(used) == len(set(used))


def test_every_claim_has_float_confidence_in_unit_interval():
    channels = SimpleWS2812Generator(payload=[0x5A]).generate()[0].channels
    claims = classify(channels, SAMPLE_RATE_HZ)
    assert len(claims) >= 1
    for claim in claims:
        assert isinstance(claim.confidence, float)
        assert 0.0 <= claim.confidence <= 1.0
