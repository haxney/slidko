"""
Protocol incoherence check (design.md § Check 4). Tests requirements:
- coherent UART/I2C decoded event streams yield no incoherence finding
- a UART stream with an injected framing error yields a finding
- an I2C ack/data event with no preceding addressed device ("ACK from
  nobody") yields a finding
"""

import pytest

from slidko.capture import Capture
from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.events import DecodedEvent
from slidko.decode.native_uart import NativeUARTBackend
from slidko.measure.smoke import detect_incoherence
from tests.synth import SimpleUARTGenerator

UART_HYPOTHESIS = ProtocolHypothesis(
    protocol="uart",
    parameters={
        "baud": 9600,
        "data_bits": 8,
        "parity": "none",
        "stop_bits": 1.0,
        "rx_channel": "ch0",
    },
    channel_assignments={"rx": "ch0"},
)

I2C_HYPOTHESIS = ProtocolHypothesis(
    protocol="i2c",
    parameters={"scl_channel": "scl", "sda_channel": "sda"},
    channel_assignments={"scl": "scl", "sda": "sda"},
)


def test_uart_coherent_stream_is_silent():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x11, 0x22, 0x33])
    capture, _ground_truth = generator.generate()
    events = NativeUARTBackend().decode(capture, UART_HYPOTHESIS)

    findings = detect_incoherence(events, UART_HYPOTHESIS)

    assert findings == []


def test_uart_framing_error_yields_finding():
    generator = SimpleUARTGenerator(baud=9600, payload=[0x11, 0x22, 0x33])
    capture, ground_truth = generator.generate()
    backend = NativeUARTBackend()
    clean_events = backend.decode(capture, UART_HYPOTHESIS)
    bit_samples = ground_truth.parameters["bit_samples"]

    # Force the whole stop-bit segment of frame 1 low - a real framing
    # error - without touching the byte's data bits.
    channel = capture.channels["ch0"].copy()
    frame = clean_events[1]
    channel[frame.end_sample - bit_samples + 1 : frame.end_sample + 1] = False
    corrupted_capture = Capture(
        channels={"ch0": channel},
        samplerate_hz=capture.samplerate_hz,
        provenance=capture.provenance,
    )
    dirty_events = backend.decode(corrupted_capture, UART_HYPOTHESIS)

    findings = detect_incoherence(dirty_events, UART_HYPOTHESIS)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "protocol_incoherence"
    assert finding.channel == "ch0"
    assert finding.escalation.startswith("smoke → scope")
    assert finding.evidence["framing_error_count"] == 1
    assert finding.evidence["total_frames"] == 3


def test_i2c_coherent_stream_is_silent():
    events = [
        DecodedEvent(kind="i2c.start", start_sample=0, end_sample=0, data={}),
        DecodedEvent(
            kind="i2c.address",
            start_sample=10,
            end_sample=100,
            data={"address": 0x55, "rw": "write"},
        ),
        DecodedEvent(kind="i2c.ack", start_sample=101, end_sample=110, data={}),
        DecodedEvent(
            kind="i2c.data", start_sample=111, end_sample=200, data={"value": 0xAA}
        ),
        DecodedEvent(kind="i2c.ack", start_sample=201, end_sample=210, data={}),
        DecodedEvent(kind="i2c.stop", start_sample=211, end_sample=211, data={}),
    ]

    findings = detect_incoherence(events, I2C_HYPOTHESIS)

    assert findings == []


def test_i2c_ack_from_nobody_yields_finding():
    """An ACK with no preceding i2c.start/i2c.address - a phantom device or
    bus contention."""
    events = [
        DecodedEvent(kind="i2c.ack", start_sample=50, end_sample=60, data={}),
    ]

    findings = detect_incoherence(events, I2C_HYPOTHESIS)

    assert len(findings) == 1
    finding = findings[0]
    assert finding.check == "protocol_incoherence"
    assert finding.channel == "sda"
    assert finding.start_sample == 50
    assert finding.end_sample == 60
    assert finding.escalation.startswith("smoke → scope")
    assert finding.evidence["kind"] == "i2c.ack"


def test_i2c_data_outside_envelope_yields_finding():
    """A data byte after i2c.stop closed the transaction - outside any
    start/stop envelope."""
    events = [
        DecodedEvent(kind="i2c.start", start_sample=0, end_sample=0, data={}),
        DecodedEvent(
            kind="i2c.address",
            start_sample=10,
            end_sample=100,
            data={"address": 0x55, "rw": "write"},
        ),
        DecodedEvent(kind="i2c.ack", start_sample=101, end_sample=110, data={}),
        DecodedEvent(kind="i2c.stop", start_sample=111, end_sample=111, data={}),
        DecodedEvent(
            kind="i2c.data", start_sample=200, end_sample=290, data={"value": 0xFF}
        ),
    ]

    findings = detect_incoherence(events, I2C_HYPOTHESIS)

    assert len(findings) == 1
    assert findings[0].evidence["kind"] == "i2c.data"
    assert findings[0].start_sample == 200


if __name__ == "__main__":
    pytest.main([__file__])
