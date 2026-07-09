"""
Parametrized tests showing backend compatibility.

Tests requirements from design.md:
- Write parametrized test running same UART assertions on both backends
- Prove abstraction works: native and sigrok paths produce equivalent results
"""

import pytest

from slidko.decode.backend import ProtocolHypothesis
from slidko.decode.native_uart import NativeUARTBackend
from slidko.decode.sigrok_backend import SigrokBackend
from tests.synth import SimpleUARTGenerator


def test_uart_backend_compatibility(monkeypatch):
    """Same UART assertions against both backends, proving the abstraction
    holds: native decodes for real; sigrok is exercised with its subprocess
    boundary mocked (canned stdout in the confirmed sigrok-cli line format)
    since unit tests must not require sigrok installed."""

    generator = SimpleUARTGenerator(baud=9600, payload=[0x41, 0x42])
    capture, _ground_truth = generator.generate()

    # Create hypothesis (what Measure would produce)
    hypothesis = ProtocolHypothesis(
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

    native_backend = NativeUARTBackend()
    sigrok_backend = SigrokBackend()

    native_events = native_backend.decode(capture, hypothesis)
    assert [e.kind for e in native_events] == ["uart.byte", "uart.byte"]
    assert [e.data["value"] for e in native_events] == [0x41, 0x42]

    canned_stdout = ["0-100 uart-1: 41", "100-200 uart-1: 42"]
    monkeypatch.setattr(sigrok_backend, "_run_sigrok", lambda args: canned_stdout)
    sigrok_events = sigrok_backend.decode(capture, hypothesis)
    assert [e.kind for e in sigrok_events] == ["uart.byte", "uart.byte"]
    assert [e.data["value"] for e in sigrok_events] == [0x41, 0x42]


if __name__ == "__main__":
    pytest.main([__file__])
