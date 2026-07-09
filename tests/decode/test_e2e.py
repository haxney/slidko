"""
End-to-end decode tests: raw synthetic capture -> real Measure classify() ->
Decode, with zero manually supplied parameters (design.md's zero-config
requirement). I2C/SPI route through the real sigrok-cli subprocess
(skipped when sigrok-cli isn't installed); UART routes through the native
backend, which is always available.
"""

import shutil

import pytest

from slidko.decode.from_measure import hypothesis_from_claim
from slidko.decode.native_uart import NativeUARTBackend
from slidko.decode.sigrok_backend import SigrokBackend
from slidko.measure.classify import classify
from tests.synth import SimpleI2CGenerator, SimpleSPIGenerator, SimpleUARTGenerator

sigrok_available = pytest.mark.skipif(
    shutil.which("sigrok-cli") is None, reason="sigrok-cli not installed"
)


def test_e2e_uart_decode():
    """Raw synthetic UART capture -> Measure -> native backend -> decoded
    bytes equal ground truth, zero manual parameters passed."""
    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])
    capture, ground_truth = generator.generate()

    claims = classify(capture.channels, capture.samplerate_hz)
    (uart_claim,) = [c for c in claims if c.protocol == "UART"]
    hypothesis = hypothesis_from_claim(uart_claim)

    events = NativeUARTBackend().decode(capture, hypothesis)

    assert [e.kind for e in events] == ["uart.byte", "uart.byte"]
    assert [e.data["value"] for e in events] == ground_truth.payload


@sigrok_available
def test_e2e_i2c_decode():
    """Raw synthetic I2C capture -> Measure -> sigrok backend (real
    sigrok-cli) -> correct address + ACK/NAK + data events vs ground truth."""
    generator = SimpleI2CGenerator(address=0x55, payload=[0xAA, 0xBB])
    capture, ground_truth = generator.generate()

    claims = classify(capture.channels, capture.samplerate_hz)
    (i2c_claim,) = [c for c in claims if c.protocol == "I2C"]
    hypothesis = hypothesis_from_claim(i2c_claim)

    events = SigrokBackend().decode(capture, hypothesis)

    assert [e.kind for e in events] == [
        "i2c.start",
        "i2c.address",
        "i2c.ack",
        "i2c.data",
        "i2c.ack",
        "i2c.data",
        "i2c.ack",
        "i2c.stop",
    ]
    address_event = next(e for e in events if e.kind == "i2c.address")
    assert address_event.data == {
        "address": ground_truth.parameters["address"],
        "rw": "write",
    }
    data_values = [e.data["value"] for e in events if e.kind == "i2c.data"]
    assert data_values == ground_truth.payload


@sigrok_available
def test_e2e_spi_decode():
    """Raw synthetic SPI capture -> Measure -> sigrok backend (real
    sigrok-cli) -> correct spi.transfer bytes for the generator's CPOL/CPHA.

    Payload is chosen to be non-alternating: Measure's SPI role-assignment
    confidence is periodicity-based, and a highly alternating payload (e.g.
    0x55) makes the data line look almost as periodic as the clock, which
    coincidentally depresses confidence below the classifier's threshold.
    """
    generator = SimpleSPIGenerator(cpol=0, cpha=0, payload=[0x12, 0x34, 0x56, 0x78])
    capture, ground_truth = generator.generate()

    claims = classify(capture.channels, capture.samplerate_hz)
    (spi_claim,) = [c for c in claims if c.protocol == "SPI"]
    hypothesis = hypothesis_from_claim(spi_claim)

    events = SigrokBackend().decode(capture, hypothesis)

    payload = ground_truth.payload
    assert payload is not None
    assert [e.kind for e in events] == ["spi.transfer"] * len(payload)
    assert [e.data["mosi"] for e in events] == payload


if __name__ == "__main__":
    pytest.main([__file__])
